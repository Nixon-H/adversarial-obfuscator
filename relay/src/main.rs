fn main() {
    env_logger::init();
    let cli = <orbital_relay::cli::Cli as clap::Parser>::parse();

    if !cli.no_init_runtime {
        nixon_runtime::init_runtime(&Default::default());
    }

    #[cfg(target_os = "linux")]
    if cli.antidebug {
        orbital_relay::antidbg::run_checks();
    }

    let payload_path = cli.payload.clone().unwrap_or_default();
    if let Err(e) = orbital_relay::payload::launch_payload(&payload_path) {
        eprintln!("Error: {e:#}");
        std::process::exit(1);
    }
}
