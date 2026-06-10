mod antidbg;
mod cli;
mod cloudflare;
mod config;
mod dns;
mod socks5;
mod tunnel;

use anyhow::Result;
use clap::Parser;
use cli::Cli;

#[tokio::main]
async fn main() -> Result<()> {
    env_logger::init();
    antidbg::run_checks();
    let cli = Cli::parse();
    cli::dispatch(cli).await
}
