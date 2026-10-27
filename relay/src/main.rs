use std::path::PathBuf;

/// Start-up settings the build produces, next to the binary.
///
/// Only the fields the build can actually know live here. The rest of
/// `RuntimeConfig` keeps its defaults.
#[derive(serde::Deserialize)]
struct RuntimeConfigFile {
    integrity_expected_crc: Option<u32>,
}

/// Where to look: `NIXON_RUNTIME_CONFIG` if set, else next to the
/// executable (which is where `make relay` writes it).
fn runtime_config_path() -> Option<PathBuf> {
    if let Ok(p) = std::env::var("NIXON_RUNTIME_CONFIG") {
        if !p.is_empty() {
            return Some(PathBuf::from(p));
        }
    }
    std::env::current_exe()
        .ok()
        .and_then(|exe| exe.parent().map(|d| d.join("runtime_config.json")))
}

fn load_runtime_config() -> nixon_runtime::RuntimeConfig {
    let mut config = nixon_runtime::RuntimeConfig::default();
    let path = match runtime_config_path() {
        Some(p) => p,
        None => return config,
    };
    match std::fs::read_to_string(&path) {
        Ok(text) => match serde_json::from_str::<RuntimeConfigFile>(&text) {
            Ok(parsed) => {
                config.integrity_expected_crc = parsed.integrity_expected_crc;
                eprintln!(
                    "runtime: integrity baseline {}",
                    match config.integrity_expected_crc {
                        Some(crc) => format!("0x{crc:08x}"),
                        None => "absent (check disabled)".to_string(),
                    }
                );
            }
            Err(e) => eprintln!("runtime: {} is not valid: {e}", path.display()),
        },
        Err(_) => eprintln!(
            "runtime: no {} — integrity check disabled (run `make relay`)",
            path.display()
        ),
    }
    config
}

fn main() {
    env_logger::init();
    let cli = <orbital_relay::cli::Cli as clap::Parser>::parse();

    if !cli.no_init_runtime {
        nixon_runtime::init_runtime(&load_runtime_config());
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
