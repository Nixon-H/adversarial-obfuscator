use std::sync::Arc;
use std::time::Duration;
use anyhow::{Context, Result};
use futures_util::{SinkExt, StreamExt};
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::{TcpListener, TcpStream};
use tokio_tungstenite::tungstenite::Message;
use tokio_tungstenite::MaybeTlsStream;
use url::Url;

use crate::socks5::{socks5_handshake, socks5_success_response};

#[derive(Debug, Clone)]
pub struct GatewayConfig {
    pub service_name: String,
    pub ws_url: String,
    pub api_key: String,
    pub socks_password: String,
    pub bind_host: String,
    pub bind_port: Option<u16>,
    pub cf_override_ip: String,
    pub cf_hostnames: Vec<String>,
    pub fallback_enabled: bool,
    pub fallback_ws_url: String,
    pub fallback_api_key: String,
    pub fallback_password: String,
    pub handshake_timeout: Duration,
    pub retry_buffer_size: usize,
}

impl GatewayConfig {
    pub fn from_config(cfg: &crate::config::Config, service: &crate::config::ServiceRecord) -> Self {
        let c = &cfg.client;
        Self {
            service_name: service.name.clone(),
            ws_url: http_to_ws_url(&service.url),
            api_key: service.auth_token.clone().unwrap_or_default(),
            socks_password: service.socks_password.clone().unwrap_or_default(),
            bind_host: c.bind_host.clone(),
            bind_port: None,
            cf_override_ip: c.cf_override_ip.clone(),
            cf_hostnames: c.cf_hostnames.clone(),
            fallback_enabled: c.relay.enabled,
            fallback_ws_url: c.relay.url.clone(),
            fallback_api_key: c.relay.auth_token.clone(),
            fallback_password: c.relay.socks_password.clone(),
            handshake_timeout: Duration::from_secs_f64(c.handshake_timeout),
            retry_buffer_size: 262144.max(0),
        }
    }
}

pub struct ConnectionState {
    max_size: usize,
    buffered: Vec<Vec<u8>>,
    buffered_bytes: usize,
    buffer_sent: bool,
    active: bool,
}

impl ConnectionState {
    pub fn new(max_size: usize) -> Self {
        Self { max_size, buffered: Vec::new(), buffered_bytes: 0, buffer_sent: false, active: false }
    }

    pub fn buffer_data(&mut self, data: &[u8]) {
        if self.active || self.buffer_sent || self.max_size == 0 || data.is_empty() {
            return;
        }
        let remaining = self.max_size.saturating_sub(self.buffered_bytes);
        if remaining == 0 { return; }
        let end = data.len().min(remaining);
        self.buffered.push(data[..end].to_vec());
        self.buffered_bytes += end;
    }

    pub fn set_active(&mut self) {
        if !self.active {
            self.active = true;
            self.buffered.clear();
        }
    }

    pub fn can_retry(&self) -> bool {
        !self.active && !self.buffer_sent && !self.buffered.is_empty()
    }

    pub fn get_buffered_data(&mut self) -> Vec<Vec<u8>> {
        if !self.can_retry() { return Vec::new(); }
        self.buffer_sent = true;
        std::mem::take(&mut self.buffered)
    }
}

pub fn http_to_ws_url(http_url: &str) -> String {
    if let Ok(parsed) = Url::parse(http_url) {
        let scheme = if parsed.scheme() == "https" { "wss" } else { "ws" };
        let host = parsed.host_str().unwrap_or("");
        let port = parsed.port().map(|p| format!(":{}", p)).unwrap_or_default();
        let path = parsed.path();
        let query = parsed.query().map(|q| format!("?{}", q)).unwrap_or_default();
        format!("{}://{}{}{}{}", scheme, host, port, path, query)
    } else {
        http_url.to_string()
    }
}

async fn connect_ws(url: &str, api_key: &str, timeout: Duration) -> Result<tokio_tungstenite::WebSocketStream<MaybeTlsStream<TcpStream>>> {
    use tokio_tungstenite::tungstenite::client::IntoClientRequest;
    let mut request = url.into_client_request()?;
    if !api_key.is_empty() {
        request.headers_mut().insert(
            "Authorization",
            api_key.parse().unwrap(),
        );
    }
    let (ws, _) = tokio::time::timeout(timeout, tokio_tungstenite::connect_async(request))
        .await
        .context("WebSocket connection timeout")??;
    Ok(ws)
}

async fn send_connect<S, E>(ws: &mut S, host: &str, port: u16, password: &str) -> Result<()>
where
    S: SinkExt<Message, Error = E> + Unpin,
    E: std::error::Error + Send + Sync + 'static,
{
    let cmd = serde_json::json!({"hostname": host, "port": port, "password": password});
    ws.send(Message::Text(cmd.to_string())).await?;
    Ok(())
}

async fn wait_for_ack(ws: &mut (impl StreamExt<Item = Result<Message, tokio_tungstenite::tungstenite::Error>> + Unpin), timeout: Duration) -> Result<()> {
    let msg = tokio::time::timeout(timeout, ws.next())
        .await
        .context("Ack timeout")?
        .context("WebSocket closed")??;

    match msg {
        Message::Text(text) => {
            let parsed: serde_json::Value = serde_json::from_str(&text)?;
            if parsed.get("type").and_then(|v| v.as_str()) == Some("ready") {
                Ok(())
            } else {
                let err = parsed.get("message").and_then(|v| v.as_str()).unwrap_or("Worker rejected");
                anyhow::bail!("{}", err)
            }
        }
        _ => anyhow::bail!("Unexpected binary ack"),
    }
}

async fn relay_bidirectional(
    stream: TcpStream,
    ws: tokio_tungstenite::WebSocketStream<MaybeTlsStream<TcpStream>>,
) -> Result<()> {
    let (mut reader, mut writer) = tokio::io::split(stream);
    let (mut ws_sink, mut ws_stream) = ws.split();

    let client_to_ws = async {
        let mut buf = [0u8; 65536];
        loop {
            match reader.read(&mut buf).await {
                Ok(0) => break,
                Ok(n) => {
                    if ws_sink.send(Message::Binary(buf[..n].to_vec())).await.is_err() {
                        break;
                    }
                }
                Err(_) => break,
            }
        }
        Ok::<_, anyhow::Error>(())
    };

    let ws_to_client = async {
        loop {
            match ws_stream.next().await {
                Some(Ok(Message::Binary(data))) => {
                    if writer.write_all(&data).await.is_err() { break; }
                    if writer.flush().await.is_err() { break; }
                }
                Some(Ok(Message::Text(_))) => {}
                Some(Ok(Message::Close(_))) | None => break,
                _ => break,
            }
        }
        Ok::<_, anyhow::Error>(())
    };

    tokio::select! {
        r = client_to_ws => r,
        r = ws_to_client => r,
    }
}

pub async fn cmd_socks(port: Option<u16>, bind: Option<String>, _profile: Option<String>) -> Result<()> {
    let cfg = crate::config::Config::load()?;
    let services = cfg.cached_services.clone();

    if services.is_empty() {
        anyhow::bail!("No cached services. Run `orbital-relay create` first.");
    }

    let bind_host = bind.unwrap_or(cfg.client.bind_host.clone());
    let listen_port = port.unwrap_or(cfg.client.base_port);
    let service = services[0].clone();
    let gw_cfg = GatewayConfig::from_config(&cfg, &service);

    let listener = TcpListener::bind(format!("{}:{}", bind_host, listen_port)).await
        .context("Failed to bind SOCKS listener")?;

    println!("[+] SOCKS5 tunnel listening on {}:{}", bind_host, listen_port);
    println!("    Worker: {} ({})", service.name, service.url);
    println!("    Press Ctrl+C to stop.");

    let gw_cfg = Arc::new(gw_cfg);

    loop {
        let (stream, peer) = listener.accept().await?;
        log::info!("New connection from {}", peer);
        let cfg = gw_cfg.clone();
        tokio::spawn(async move {
            if let Err(e) = handle_connection(stream, cfg).await {
                log::error!("Connection error: {}", e);
            }
        });
    }
}

async fn handle_connection(mut stream: TcpStream, cfg: Arc<GatewayConfig>) -> Result<()> {
    let request = socks5_handshake(&mut stream).await?;
    let target_host = if !cfg.cf_override_ip.is_empty()
        && cfg.cf_hostnames.iter().any(|h| h == &request.host)
    { cfg.cf_override_ip.clone() } else { request.host.clone() };

    let mut ws = match connect_ws(&cfg.ws_url, &cfg.api_key, cfg.handshake_timeout).await {
        Ok(ws) => ws,
        Err(_) if cfg.fallback_enabled => {
            connect_ws(&cfg.fallback_ws_url, &cfg.fallback_api_key, cfg.handshake_timeout).await?
        }
        Err(e) => anyhow::bail!("Connection failed: {}", e),
    };

    send_connect(&mut ws, &target_host, request.port, &cfg.socks_password).await?;
    wait_for_ack(&mut ws, cfg.handshake_timeout).await?;

    let resp = socks5_success_response(&request);
    stream.write_all(&resp).await?;
    stream.flush().await?;

    relay_bidirectional(stream, ws).await
}

pub async fn test_socks_endpoint(url: &str, host: &str, port: u16, password: &str, timeout: Duration) -> Result<()> {
    let ws_url = http_to_ws_url(url);
    let mut ws = connect_ws(&ws_url, "", timeout).await?;
    send_connect(&mut ws, host, port, password).await?;
    wait_for_ack(&mut ws, timeout).await?;
    println!("[+] SOCKS endpoint OK: connected to {}:{} via {}", host, port, url);
    Ok(())
}
