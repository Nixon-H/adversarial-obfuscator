use std::path::{Path, PathBuf};
use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::fs;
use crate::cli::ConfigAction;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Config {
    #[serde(skip)]
    pub config_path: PathBuf,
    pub cloudflare: CloudflareConfig,
    pub worker: WorkerConfig,
    pub client: ClientConfig,
    pub cached_services: Vec<ServiceRecord>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct CloudflareConfig {
    pub api_token: Option<String>,
    pub account_id: Option<String>,
    pub zone_id: Option<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct WorkerConfig {
    pub mode: String,
    pub auth_token: String,
    pub socks_password: String,
    pub compatibility_date: String,
    pub compatibility_flags: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ClientConfig {
    pub bind_host: String,
    pub base_port: u16,
    pub auto_random_ports: bool,
    pub cf_override_ip: String,
    pub cf_hostnames: Vec<String>,
    pub handshake_timeout: f64,
    pub use_doh: bool,
    pub doh_timeout: f64,
    pub relay: FallbackConfig,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct FallbackConfig {
    pub enabled: bool,
    pub url: String,
    pub auth_token: String,
    pub socks_password: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ServiceRecord {
    pub name: String,
    pub url: String,
    pub created_at: String,
    pub id: Option<String>,
    pub auth_token: Option<String>,
    pub socks_password: Option<String>,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            config_path: PathBuf::new(),
            cloudflare: CloudflareConfig {
                api_token: None,
                account_id: None,
                zone_id: None,
            },
            worker: WorkerConfig {
                mode: "http".into(),
                auth_token: String::new(),
                socks_password: String::new(),
                compatibility_date: "2023-09-04".into(),
                compatibility_flags: vec!["nodejs_compat".into()],
            },
            client: ClientConfig {
                bind_host: "127.0.0.1".into(),
                base_port: 1080,
                auto_random_ports: true,
                cf_override_ip: String::new(),
                cf_hostnames: Vec::new(),
                handshake_timeout: 5.0,
                use_doh: true,
                doh_timeout: 5.0,
                relay: FallbackConfig {
                    enabled: false,
                    url: String::new(),
                    auth_token: String::new(),
                    socks_password: String::new(),
                },
            },
            cached_services: Vec::new(),
        }
    }
}

impl Config {
    pub fn load() -> Result<Self> {
        let paths = [
            "orbital-relay.json",
            "cloudproxy.json",
            &format!("{}/.orbital-relay.json", std::env::var("HOME").unwrap_or_default()),
        ];

        for p in &paths {
            let path = Path::new(p);
            if path.exists() {
                let mut cfg: Self = serde_json::from_str(
                    &fs::read_to_string(path).context("Failed to read config")?
                ).context("Failed to parse config")?;
                cfg.config_path = path.to_path_buf();
                return Ok(cfg);
            }
        }

        let mut cfg = Config::default();
        cfg.config_path = PathBuf::from("orbital-relay.json");
        cfg.save()?;
        Ok(cfg)
    }

    pub fn save(&self) -> Result<()> {
        let json = serde_json::to_string_pretty(self)?;
        fs::write(&self.config_path, json)?;
        Ok(())
    }

    pub fn has_credentials(&self) -> bool {
        self.cloudflare.api_token.is_some()
            && self.cloudflare.account_id.is_some()
    }

    pub fn generate_token() -> String {
        use rand::Rng;
        let mut rng = rand::rngs::OsRng;
        let bytes: [u8; 24] = rng.r#gen();
        base64::Engine::encode(&base64::engine::general_purpose::URL_SAFE_NO_PAD, bytes)
    }
}

pub async fn cmd_config(action: Option<ConfigAction>) -> Result<()> {
    let cfg = Config::load()?;

    match action {
        None | Some(ConfigAction::Show) => {
            println!("{}", serde_json::to_string_pretty(&cfg)?);
        }
        Some(ConfigAction::Wizard) => {
            println!("Interactive setup wizard not yet implemented in Rust port.");
            println!("Edit orbital-relay.json directly for now.");
        }
    }
    Ok(())
}
