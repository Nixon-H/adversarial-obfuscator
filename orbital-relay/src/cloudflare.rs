use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};

use anyhow::{anyhow, Context, Result};
use rand::Rng;
use reqwest::multipart::{Form, Part};
use serde::{Deserialize, Serialize};
use crate::config::{Config, ServiceRecord, WorkerConfig};

const API_BASE: &str = "https://api.cloudflare.com/client/v4";

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TestResult {
    pub success: bool,
    pub status_code: u16,
    pub response_length: usize,
    pub headers: HashMap<String, String>,
    pub error: Option<String>,
}

pub struct CloudflareClient {
    api_key: String,
    account_id: String,
    zone_id: Option<String>,
    http_client: reqwest::Client,
    _org_host_prefix: Option<String>,
}

impl CloudflareClient {
    pub fn new(api_key: String, account_id: String, zone_id: Option<String>) -> Self {
        Self {
            api_key,
            account_id,
            zone_id,
            http_client: reqwest::Client::builder()
                .timeout(std::time::Duration::from_secs(90))
                .build()
                .expect("Failed to build HTTP client"),
            _org_host_prefix: None,
        }
    }

    fn auth_headers(&self) -> reqwest::header::HeaderMap {
        let mut headers = reqwest::header::HeaderMap::new();
        headers.insert(
            reqwest::header::AUTHORIZATION,
            format!("Bearer {}", self.api_key).parse().unwrap(),
        );
        headers.insert(
            reqwest::header::CONTENT_TYPE,
            "application/json".parse().unwrap(),
        );
        headers
    }

    pub async fn service_host_prefix(&mut self) -> Result<String> {
        if let Some(ref prefix) = self._org_host_prefix {
            return Ok(prefix.clone());
        }

        let url = format!(
            "{}/accounts/{}/workers/subdomain",
            API_BASE, self.account_id
        );

        let resp = self
            .http_client
            .get(&url)
            .headers(self.auth_headers())
            .send()
            .await
            .context("Failed to fetch workers subdomain")?;

        if resp.status().is_success() {
            let json: serde_json::Value = resp
                .json()
                .await
                .context("Failed to parse subdomain response")?;
            if let Some(subdomain) = json["result"]["subdomain"].as_str() {
                let prefix = subdomain.to_string();
                self._org_host_prefix = Some(prefix.clone());
                return Ok(prefix);
            }
        }

        let fallback = self.account_id.to_lowercase();
        self._org_host_prefix = Some(fallback.clone());
        Ok(fallback)
    }

    fn generate_service_id() -> String {
        let ts = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs();
        let suffix: String = (0..6)
            .map(|_| rand::thread_rng().gen_range(b'a'..=b'z') as char)
            .collect();
        format!("orbital-relay-{}-{}", ts, suffix)
    }

    pub async fn create_worker(
        &mut self,
        name: &str,
        mode: &str,
        config: &WorkerConfig,
    ) -> Result<ServiceRecord> {
        let script = match mode {
            "socks" => Self::socks_worker_script(&config.auth_token, &config.socks_password),
            _ => Self::http_worker_script(),
        };

        let metadata = serde_json::json!({
            "main_module": "worker.js",
            "compatibility_date": config.compatibility_date,
            "compatibility_flags": config.compatibility_flags,
        });

        let metadata_part = Part::text(metadata.to_string())
            .mime_str("application/json")?;
        let script_part = Part::text(script)
            .file_name("worker.js")
            .mime_str("application/javascript+module")?;

        let form = Form::new()
            .part("metadata", metadata_part)
            .part("worker.js", script_part);

        let url = format!(
            "{}/accounts/{}/workers/scripts/{}",
            API_BASE, self.account_id, name
        );

        let resp = self
            .http_client
            .put(&url)
            .header("Authorization", format!("Bearer {}", self.api_key))
            .multipart(form)
            .send()
            .await
            .context("Failed to send worker upload request")?;

        if !resp.status().is_success() {
            let status = resp.status();
            let body = resp.text().await.unwrap_or_default();
            let err_msg = if let Ok(err_json) =
                serde_json::from_str::<serde_json::Value>(&body)
            {
                if let Some(errors) = err_json["errors"].as_array() {
                    serde_json::to_string(errors).unwrap_or(body.clone())
                } else {
                    body.clone()
                }
            } else {
                body
            };
            return Err(anyhow!("Failed to create worker ({}): {}", status, err_msg));
        }

        let sub_url = format!(
            "{}/accounts/{}/workers/scripts/{}/subdomain",
            API_BASE, self.account_id, name
        );
        let _ = self
            .http_client
            .post(&sub_url)
            .headers(self.auth_headers())
            .json(&serde_json::json!({"enabled": true}))
            .send()
            .await;

        let host_prefix = self.service_host_prefix().await?;
        let worker_url = format!("https://{}.{}.workers.dev", name, host_prefix);

        Ok(ServiceRecord {
            name: name.to_string(),
            url: worker_url,
            created_at: chrono::Local::now()
                .format("%Y-%m-%d %H:%M:%S")
                .to_string(),
            id: Some(name.to_string()),
            auth_token: Some(config.auth_token.clone()),
            socks_password: Some(config.socks_password.clone()),
        })
    }

    pub async fn list_workers(&mut self) -> Result<Vec<ServiceRecord>> {
        let url = format!(
            "{}/accounts/{}/workers/scripts",
            API_BASE, self.account_id
        );

        let resp = self
            .http_client
            .get(&url)
            .headers(self.auth_headers())
            .send()
            .await
            .context("Failed to list workers")?;

        if !resp.status().is_success() {
            return Err(anyhow!(
                "Failed to list workers: {}",
                resp.status()
            ));
        }

        let json: serde_json::Value = resp
            .json()
            .await
            .context("Failed to parse workers list response")?;

        let host_prefix = self.service_host_prefix().await?;
        let mut services = Vec::new();

        if let Some(results) = json["result"].as_array() {
            for entry in results {
                if let Some(id) = entry["id"].as_str() {
                    if id.starts_with("orbital-relay-") {
                        services.push(ServiceRecord {
                            name: id.to_string(),
                            url: format!("https://{}.{}.workers.dev", id, host_prefix),
                            created_at: entry["created_on"]
                                .as_str()
                                .unwrap_or("unknown")
                                .to_string(),
                            id: Some(id.to_string()),
                            auth_token: None,
                            socks_password: None,
                        });
                    }
                }
            }
        }

        Ok(services)
    }

    pub async fn delete_worker(&self, name: &str) -> Result<()> {
        let url = format!(
            "{}/accounts/{}/workers/scripts/{}",
            API_BASE, self.account_id, name
        );

        let resp = self
            .http_client
            .delete(&url)
            .header("Authorization", format!("Bearer {}", self.api_key))
            .send()
            .await
            .context("Failed to send delete request")?;

        if resp.status().is_success() || resp.status().as_u16() == 404 {
            Ok(())
        } else {
            Err(anyhow!(
                "Failed to delete worker {}: {}",
                name,
                resp.status()
            ))
        }
    }

    pub async fn test_endpoint(&self, url: &str, target_url: &str) -> Result<TestResult> {
        let full_url = format!("{}?url={}", url, target_url);
        let resp = self
            .http_client
            .get(&full_url)
            .send()
            .await
            .context("Failed to test endpoint")?;

        let status_code = resp.status().as_u16();
        let headers: HashMap<String, String> = resp
            .headers()
            .iter()
            .map(|(k, v)| (k.to_string(), v.to_str().unwrap_or("").to_string()))
            .collect();
        let body = resp.bytes().await.unwrap_or_default();
        let response_length = body.len();

        Ok(TestResult {
            success: status_code == 200,
            status_code,
            response_length,
            headers,
            error: None,
        })
    }

    // ── JS Worker Scripts ──────────────────────────────────────────────

    pub fn http_worker_script() -> String {
        r#"
export default {
  async fetch(req) {
    try {
      const reqUrl = new URL(req.url);
      const destinationUrl = getTargetUrl(reqUrl, req.headers);
      if (!destinationUrl) {
        return createErrorResponse('No target URL specified', {
          usage: {
            query_param: '?url=https://example.com',
            header: 'X-Target-URL: https://example.com',
            path: '/https://example.com'
          }
        }, 400);
      }

      let destinationUrlObj;
      try { destinationUrlObj = new URL(destinationUrl); }
      catch (e) { return createErrorResponse('Invalid target URL', { provided: destinationUrl }, 400); }

      const destinationParams = new URLSearchParams();
      for (const [key, value] of reqUrl.searchParams) {
        if (!['url', '_cb', '_t'].includes(key)) {
          destinationParams.append(key, value);
        }
      }
      if (destinationParams.toString()) {
        destinationUrlObj.search = destinationParams.toString();
      }

      const fwdReq = createProxyRequest(req, destinationUrlObj);
      const originResp = await fetch(fwdReq);
      return createProxyResponse(originResp, req.method);
    } catch (error) {
      return createErrorResponse('Proxy request failed', { message: error.message, timestamp: new Date().toISOString() }, 500);
    }
  }
}

function getTargetUrl(reqUrl, headers) {
  let destinationUrl = reqUrl.searchParams.get('url');
  if (!destinationUrl) destinationUrl = headers.get('X-Target-URL');
  if (!destinationUrl && reqUrl.pathname !== '/') {
    const pathUrl = reqUrl.pathname.slice(1);
    if (pathUrl.startsWith('http')) destinationUrl = pathUrl;
  }
  return destinationUrl;
}

function createProxyRequest(req, destinationUrlObj) {
  const fwdHeaders = new Headers();
  const passThroughHeaders = ['accept','accept-language','accept-encoding','authorization','cache-control','content-type','origin','referer','user-agent'];
  for (const [key, value] of req.headers) {
    if (passThroughHeaders.includes(key.toLowerCase())) fwdHeaders.set(key, value);
  }
  fwdHeaders.set('Host', destinationUrlObj.hostname);
  const customIp = req.headers.get('X-My-X-Forwarded-For');
  fwdHeaders.set('X-Forwarded-For', customIp || generateRandomIP());
  return new Request(destinationUrlObj.toString(), { method: req.method, headers: fwdHeaders, body: ['GET','HEAD'].includes(req.method) ? null : req.body });
}

function createProxyResponse(originResp, requestMethod) {
  const proxyRespHeaders = new Headers();
  for (const [key, value] of originResp.headers) {
    if (!['content-encoding','content-length','transfer-encoding'].includes(key.toLowerCase())) {
      proxyRespHeaders.set(key, value);
    }
  }
  proxyRespHeaders.set('Access-Control-Allow-Origin', '*');
  proxyRespHeaders.set('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD');
  proxyRespHeaders.set('Access-Control-Allow-Headers', '*');
  if (requestMethod === 'OPTIONS') return new Response(null, { status: 204, headers: proxyRespHeaders });
  return new Response(originResp.body, { status: originResp.status, statusText: originResp.statusText, headers: proxyRespHeaders });
}

function createErrorResponse(error, details, status) {
  return new Response(JSON.stringify({ error, ...details }), { status, headers: { 'Content-Type': 'application/json' } });
}

function generateRandomIP() {
  return [1,2,3,4].map(() => Math.floor(Math.random()*255)+1).join('.');
}
"#
        .trim()
        .to_string()
    }

    pub fn socks_worker_script(auth: &str, password: &str) -> String {
        let api_key_json = serde_json::to_string(auth).unwrap_or_else(|_| format!("\"{}\"", auth));
        let password_json =
            serde_json::to_string(password).unwrap_or_else(|_| format!("\"{}\"", password));

        let template = r#"
import { connect } from 'cloudflare:sockets';

const API_KEY = SECURE_KEY_HOLDER;
const TUNNEL_PASSWORD = TUNNEL_SECRET_HOLDER;
const textEncoder = new TextEncoder();

export default {
  async fetch(req) {
    if (API_KEY && req.headers.get('Authorization') !== API_KEY) {
      return new Response('Unauthorized', { status: 401 });
    }
    if (req.headers.get('Upgrade') !== 'websocket') {
      return new Response('Expected Upgrade: websocket', { status: 426 });
    }

    const pair = new WebSocketPair();
    const [client, server] = Object.values(pair);
    server.accept();
    server.binaryType = 'arraybuffer';

    server.addEventListener('message', async ({ data }) => {
      try {
        if (typeof data !== 'string') { server.close(1003, 'Invalid request'); return; }
        const connectArgs = JSON.parse(data);
        const targetHost = connectArgs.hostname;
        const targetPort = Number(connectArgs.port);
        const providedPsw = connectArgs.password ?? connectArgs.psw ?? '';
        if (!targetHost || !Number.isInteger(targetPort) || targetPort < 1 || targetPort > 65535) { server.close(1008, 'Invalid target'); return; }
        if (TUNNEL_PASSWORD && providedPsw !== TUNNEL_PASSWORD) { server.close(1008, 'Invalid credentials'); return; }

        let upstreamSocket;
        try { upstreamSocket = connect({ hostname: targetHost, port: targetPort }); }
        catch (e) { server.close(1011, 'Upstream connect failed'); return; }

        try { server.send(JSON.stringify({ type: 'ready' })); } catch (_) {}

        const clientDataStream = new ReadableStream({
          start(controller) {
            server.addEventListener('message', event => {
              const p = event.data;
              if (typeof p === 'string') controller.enqueue(textEncoder.encode(p));
              else if (p instanceof ArrayBuffer) controller.enqueue(new Uint8Array(p));
            });
            server.addEventListener('error', ev => controller.error(ev));
            server.addEventListener('close', () => controller.close());
          },
          cancel() { try { upstreamSocket && upstreamSocket.close && upstreamSocket.close(); } catch (_) {} }
        });

        clientDataStream.pipeTo(upstreamSocket.writable).catch(() => server.close(1011, 'Client error'));
        upstreamSocket.readable.pipeTo(new WritableStream({
          write(chunk) { server.send(chunk instanceof ArrayBuffer ? chunk : new Uint8Array(chunk)); },
          close() { server.close(); },
          abort() { server.close(1011, 'Upstream aborted'); }
        })).catch(() => server.close(1011, 'Upstream error'));
      } catch (e) { server.close(1003, 'Invalid request'); }
    }, { once: true });

    return new Response(null, { status: 101, webSocket: client });
  }
}
"#;
        template
            .replace("SECURE_KEY_HOLDER", &api_key_json)
            .replace("TUNNEL_SECRET_HOLDER", &password_json)
            .trim()
            .to_string()
    }
}

// ── CLI Handler Functions ─────────────────────────────────────────────

pub async fn cmd_create(mode: Option<String>) -> Result<()> {
    let mut cfg = Config::load().context("Failed to load config")?;

    if !cfg.has_credentials() {
        anyhow::bail!("Cloudflare credentials not configured. Run `orbital-relay config` first.");
    }

    let api_key = cfg.cloudflare.api_token.clone().unwrap();
    let account_id = cfg.cloudflare.account_id.clone().unwrap();
    let zone_id = cfg.cloudflare.zone_id.clone();

    let mut client = CloudflareClient::new(api_key, account_id, zone_id);

    let actual_mode = mode
        .clone()
        .unwrap_or_else(|| cfg.worker.mode.clone());

    let service_name = CloudflareClient::generate_service_id();
    let record = client
        .create_worker(&service_name, &actual_mode, &cfg.worker)
        .await?;

    println!("  [1/1] {} -> {}", record.name, record.url);

    cfg.cached_services.push(record.clone());
    if let Err(e) = cfg.save() {
        eprintln!("Warning: failed to save config: {}", e);
    }

    if actual_mode == "http" {
        use std::io::Write;
        if let Ok(mut f) = std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open("http_proxies.txt")
        {
            let _ = writeln!(f, "{}", record.url);
        }
    }

    println!("\nCreated: 1, Failed: 0");
    Ok(())
}

pub async fn cmd_list() -> Result<()> {
    let mut cfg = Config::load().context("Failed to load config")?;

    if !cfg.has_credentials() {
        anyhow::bail!("Cloudflare credentials not configured.");
    }

    let api_key = cfg.cloudflare.api_token.clone().unwrap();
    let account_id = cfg.cloudflare.account_id.clone().unwrap();
    let zone_id = cfg.cloudflare.zone_id.clone();

    let mut client = CloudflareClient::new(api_key, account_id, zone_id);

    let remote = client.list_workers().await?;

    let merged = merge_service_lists(&cfg.cached_services, &remote);

    cfg.cached_services = merged.clone();
    cfg.save().ok();

    if merged.is_empty() {
        println!("No OrbitalRelay endpoints found");
        return Ok(());
    }

    println!("\nOrbitalRelay Endpoints ({} total):", merged.len());
    println!("{}", "-".repeat(80));
    println!("{:<35} {:<40} {:<8}", "Name", "URL", "Status");
    println!("{}", "-".repeat(80));

    for svc in &merged {
        println!("{:<35} {:<40} {:<8}", svc.name, svc.url, "Active");
    }

    Ok(())
}

pub async fn cmd_test_http(url: String, target: Option<String>) -> Result<()> {
    let target_url = target.unwrap_or_else(|| "https://ifconfig.me/ip".to_string());

    println!("Testing endpoint: {}", url);
    println!("Target: {}", target_url);

    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(45))
        .build()?;

    let full_url = format!("{}?url={}", url, target_url);
    let resp = client.get(&full_url).send().await?;

    let status = resp.status();
    let body = resp.bytes().await?;

    if status.is_success() {
        println!("Request successful! Status: {}", status);
        let text = String::from_utf8_lossy(&body);
        let body_str = text.trim();
        if body_str.len() < 100 {
            let ipv4 = body_str
                .split('.')
                .filter_map(|s| s.parse::<u16>().ok())
                .collect::<Vec<_>>();
            if ipv4.len() == 4 && ipv4.iter().all(|&o| o <= 255) {
                println!("    Origin IP: {}", body_str);
            } else {
                println!("    Response: {}", body_str);
            }
        } else {
            println!("    Response Length: {} bytes", body.len());
        }
    } else {
        println!("Request failed! Status: {}", status);
        if !body.is_empty() {
            let text = String::from_utf8_lossy(&body);
            println!("    Body: {}", &text[..text.len().min(500)]);
        }
    }

    Ok(())
}

pub async fn cmd_test_socks(url: String, host: String, port: u16) -> Result<()> {
    use futures_util::{SinkExt, StreamExt};
    use tokio_tungstenite::connect_async;
    use tokio_tungstenite::tungstenite::Message;

    let ws_url = url
        .replace("https://", "wss://")
        .replace("http://", "ws://");

    println!("Connecting to SOCKS tunnel via WebSocket...");
    println!("  Worker URL: {}", ws_url);
    println!("  Target: {}:{}", host, port);

    let (ws_stream, _) = connect_async(&ws_url)
        .await
        .context("Failed to connect to worker WebSocket")?;

    let (mut write, mut read) = ws_stream.split();

    let cmd = serde_json::json!({
        "hostname": host,
        "port": port,
    });

    write
        .send(Message::Text(cmd.to_string()))
        .await
        .context("Failed to send connect command")?;

    println!("  Handshake sent, waiting for acknowledgement...");

    let timeout_dur = std::time::Duration::from_secs(15);
    let result = tokio::time::timeout(timeout_dur, async {
        use futures_util::StreamExt;
        while let Some(msg) = read.next().await {
            let msg = msg.context("WebSocket error")?;
            match msg {
                Message::Text(text) => {
                    let resp: serde_json::Value =
                        serde_json::from_str(&text).context("Invalid JSON response")?;
                    if resp["type"] == "ready" {
                        return Ok(true);
                    }
                    if resp["type"] == "error" {
                        let err = resp["message"]
                            .as_str()
                            .unwrap_or("worker rejected connection");
                        anyhow::bail!("Worker error: {}", err);
                    }
                }
                Message::Close(_) => {
                    anyhow::bail!("WebSocket closed unexpectedly");
                }
                _ => {}
            }
        }
        anyhow::bail!("WebSocket stream ended without ready signal");
    })
    .await;

    match result {
        Ok(Ok(true)) => {
            println!("  SOCKS tunnel OK! Worker is functioning correctly.");
        }
        Ok(Ok(false)) => {
            println!("  SOCKS tunnel FAILED: unexpected false response");
        }
        Ok(Err(e)) => {
            println!("  SOCKS tunnel FAILED: {}", e);
        }
        Err(_) => {
            println!("  SOCKS tunnel FAILED: timed out waiting for acknowledgement");
        }
    }

    Ok(())
}

pub async fn cmd_cleanup() -> Result<()> {
    let mut cfg = Config::load().context("Failed to load config")?;

    if !cfg.has_credentials() {
        anyhow::bail!("Cloudflare credentials not configured.");
    }

    let api_key = cfg.cloudflare.api_token.clone().unwrap();
    let account_id = cfg.cloudflare.account_id.clone().unwrap();
    let zone_id = cfg.cloudflare.zone_id.clone();

    let client = CloudflareClient::new(api_key, account_id, zone_id);

    let mut client = client;
    let workers = client.list_workers().await?;

    if workers.is_empty() {
        println!("No OrbitalRelay endpoints to clean up.");
        return Ok(());
    }

    println!("\nCleaning up {} OrbitalRelay endpoint(s)...", workers.len());

    for svc in &workers {
        match client.delete_worker(&svc.name).await {
            Ok(()) => println!("  Deleted worker: {}", svc.name),
            Err(e) => eprintln!("  Could not delete worker {}: {}", svc.name, e),
        }
    }

    cfg.cached_services.clear();
    cfg.save().ok();

    println!("\nCleanup complete.");
    Ok(())
}

fn merge_service_lists(
    local: &[ServiceRecord],
    remote: &[ServiceRecord],
) -> Vec<ServiceRecord> {
    let mut map: HashMap<String, ServiceRecord> = HashMap::new();

    for svc in local {
        map.insert(svc.name.clone(), svc.clone());
    }

    for svc in remote {
        let entry = map.entry(svc.name.clone()).or_insert_with(|| svc.clone());
        entry.url = svc.url.clone();
        entry.created_at = svc.created_at.clone();
        entry.id = svc.id.clone();
    }

    let mut result: Vec<ServiceRecord> = map.into_values().collect();
    result.sort_by(|a, b| a.name.cmp(&b.name));
    result
}
