use std::fs;
use std::path::Path;

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    #[serde(default)]
    pub client: ClientConfig,
    #[serde(default)]
    pub cloudflare: CloudflareConfig,
    #[serde(default)]
    pub worker: WorkerConfig,
    #[serde(default)]
    pub cached_services: Vec<ServiceRecord>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClientConfig {
    #[serde(default = "default_bind_host")]
    pub bind_host: String,
    #[serde(default = "default_base_port")]
    pub base_port: u16,
    #[serde(default)]
    pub cf_override_ip: String,
    #[serde(default)]
    pub cf_hostnames: Vec<String>,
    #[serde(default)]
    pub relay: RelayConfig,
    #[serde(default = "default_handshake_timeout")]
    pub handshake_timeout: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RelayConfig {
    #[serde(default)]
    pub enabled: bool,
    #[serde(default)]
    pub url: String,
    #[serde(default)]
    pub auth_token: String,
    #[serde(default)]
    pub socks_password: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CloudflareConfig {
    #[serde(default)]
    pub api_token: Option<String>,
    #[serde(default)]
    pub account_id: Option<String>,
    #[serde(default)]
    pub zone_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkerConfig {
    #[serde(default = "default_worker_mode")]
    pub mode: String,
    #[serde(default)]
    pub auth_token: String,
    #[serde(default)]
    pub socks_password: String,
    #[serde(default = "default_compatibility_date")]
    pub compatibility_date: String,
    #[serde(default)]
    pub compatibility_flags: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServiceRecord {
    pub name: String,
    pub url: String,
    #[serde(default)]
    pub created_at: String,
    #[serde(default)]
    pub id: Option<String>,
    #[serde(default)]
    pub auth_token: Option<String>,
    #[serde(default)]
    pub socks_password: Option<String>,
}

pub struct AppConfig {
    pub payload_path: Option<String>,
    pub init_runtime: bool,
    pub antidebug: bool,
}

fn default_bind_host() -> String {
    "127.0.0.1".to_string()
}

fn default_base_port() -> u16 {
    1080
}

fn default_handshake_timeout() -> f64 {
    30.0
}

fn default_worker_mode() -> String {
    "socks".to_string()
}

fn default_compatibility_date() -> String {
    "2024-10-01".to_string()
}

fn config_path() -> Result<std::path::PathBuf> {
    let home = std::env::var("HOME")
        .map_err(|_| anyhow::anyhow!("HOME environment variable not set"))?;
    Ok(Path::new(&home).join(".config").join("orbital-relay").join("config.json"))
}

impl Config {
    pub fn load() -> Result<Self> {
        let path = config_path()?;
        if !path.exists() {
            return Ok(Config::default());
        }
        let content = fs::read_to_string(&path)
            .with_context(|| format!("Failed to read config from {}", path.display()))?;
        let config: Config = serde_json::from_str(&content)
            .with_context(|| format!("Failed to parse config from {}", path.display()))?;
        Ok(config)
    }

    pub fn save(&self) -> Result<()> {
        let path = config_path()?;
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }
        let content = serde_json::to_string_pretty(self)?;
        fs::write(&path, content)
            .with_context(|| format!("Failed to write config to {}", path.display()))?;
        Ok(())
    }

    pub fn has_credentials(&self) -> bool {
        self.cloudflare.api_token.is_some() && self.cloudflare.account_id.is_some()
    }
}

impl Default for Config {
    fn default() -> Self {
        Self {
            client: ClientConfig::default(),
            cloudflare: CloudflareConfig::default(),
            worker: WorkerConfig::default(),
            cached_services: Vec::new(),
        }
    }
}

impl Default for ClientConfig {
    fn default() -> Self {
        Self {
            bind_host: default_bind_host(),
            base_port: default_base_port(),
            cf_override_ip: String::new(),
            cf_hostnames: Vec::new(),
            relay: RelayConfig::default(),
            handshake_timeout: default_handshake_timeout(),
        }
    }
}

impl Default for RelayConfig {
    fn default() -> Self {
        Self {
            enabled: false,
            url: String::new(),
            auth_token: String::new(),
            socks_password: String::new(),
        }
    }
}

impl Default for CloudflareConfig {
    fn default() -> Self {
        Self {
            api_token: None,
            account_id: None,
            zone_id: None,
        }
    }
}

impl Default for WorkerConfig {
    fn default() -> Self {
        Self {
            mode: default_worker_mode(),
            auth_token: String::new(),
            socks_password: String::new(),
            compatibility_date: default_compatibility_date(),
            compatibility_flags: Vec::new(),
        }
    }
}

#[allow(dead_code)]
impl AppConfig {
    pub fn from_cli(cli: &crate::cli::Cli) -> Self {
        Self {
            payload_path: cli.payload.clone(),
            init_runtime: !cli.no_init_runtime,
            antidebug: cli.antidebug,
        }
    }
}
