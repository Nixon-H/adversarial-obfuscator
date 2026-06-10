use clap::{Parser, Subcommand};
use anyhow::Result;



#[derive(Parser)]
#[command(name = "orbital-relay", version, about = "Cloudflare Tunnel Relay Manager")]
pub struct Cli {
    #[command(subcommand)]
    pub command: Commands,
}

#[derive(Subcommand)]
pub enum Commands {
    /// Deploy a new Cloudflare Worker
    Create {
        #[arg(short, long)]
        mode: Option<String>,
    },
    /// List deployed workers
    List,
    /// Test an HTTP worker endpoint
    TestHttp {
        #[arg(short, long)]
        url: String,
        #[arg(short, long)]
        target: Option<String>,
    },
    /// Test a SOCKS worker endpoint
    TestSocks {
        #[arg(short, long)]
        url: String,
        #[arg(short, long)]
        host: String,
        #[arg(short, long)]
        port: u16,
    },
    /// Start local SOCKS5 tunnel(s)
    Socks {
        #[arg(short, long)]
        port: Option<u16>,
        #[arg(short, long)]
        bind: Option<String>,
        #[arg(long)]
        profile: Option<String>,
    },
    /// Remove all deployed workers
    Cleanup,
    /// Show or edit config
    Config {
        #[command(subcommand)]
        action: Option<ConfigAction>,
    },
    /// Show relay status
    Status,
}

#[derive(Subcommand)]
pub enum ConfigAction {
    Show,
    Wizard,
}

pub async fn dispatch(cli: Cli) -> Result<()> {
    match cli.command {
        Commands::Create { mode } => crate::cloudflare::cmd_create(mode).await,
        Commands::List => crate::cloudflare::cmd_list().await,
        Commands::TestHttp { url, target } => crate::cloudflare::cmd_test_http(url, target).await,
        Commands::TestSocks { url, host, port } => crate::cloudflare::cmd_test_socks(url, host, port).await,
        Commands::Socks { port, bind, profile } => crate::tunnel::cmd_socks(port, bind, profile).await,
        Commands::Cleanup => crate::cloudflare::cmd_cleanup().await,
        Commands::Config { action } => crate::config::cmd_config(action).await,
        Commands::Status => cmd_status().await,
    }
}

async fn cmd_status() -> Result<()> {
    let cfg = crate::config::Config::load()?;
    println!("Config: {}", cfg.config_path.display());
    println!("Cloudflare: {}", if cfg.has_credentials() { "configured" } else { "missing" });
    println!("Workers: {} cached", cfg.cached_services.len());
    Ok(())
}
