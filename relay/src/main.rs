use std::path::PathBuf;

/// Start-up settings the build produces, next to the binary.
///
/// Only the fields the build can actually know live here. The rest of
/// `RuntimeConfig` keeps its defaults.
#[derive(serde::Deserialize)]
struct RuntimeConfigFile {
    // Required deliberately: `{}` must not silently disable integrity.
    integrity_expected_crc: u32,
}

/// Where to look: `NIXON_RUNTIME_CONFIG` if set, else next to the
/// executable (which is where `make relay` writes it).
fn runtime_config_path() -> Result<PathBuf, String> {
    match std::env::var("NIXON_RUNTIME_CONFIG") {
        Ok(path) if !path.is_empty() => return Ok(PathBuf::from(path)),
        Ok(_) => {}
        Err(std::env::VarError::NotUnicode(_)) => {
            return Err("NIXON_RUNTIME_CONFIG is not valid Unicode".to_string())
        }
        Err(std::env::VarError::NotPresent) => {}
    }
    let executable = std::env::current_exe()
        .map_err(|error| format!("cannot locate relay executable: {error}"))?;
    executable
        .parent()
        .map(|directory| directory.join("runtime_config.json"))
        .ok_or_else(|| "cannot locate runtime_config.json next to relay".to_string())
}

fn load_runtime_config_from(
    path: &std::path::Path,
) -> Result<nixon_runtime::RuntimeConfig, String> {
    let text = std::fs::read_to_string(path)
        .map_err(|error| format!("cannot read {}: {error}", path.display()))?;
    let parsed: RuntimeConfigFile = serde_json::from_str(&text).map_err(|error| {
        format!(
            "{} is not a valid runtime baseline: {error}",
            path.display()
        )
    })?;
    let config = nixon_runtime::RuntimeConfig {
        integrity_expected_crc: Some(parsed.integrity_expected_crc),
        ..nixon_runtime::RuntimeConfig::default()
    };
    eprintln!(
        "runtime: integrity baseline 0x{:08x}",
        parsed.integrity_expected_crc
    );
    Ok(config)
}

fn load_runtime_config() -> Result<nixon_runtime::RuntimeConfig, String> {
    let path = runtime_config_path()?;
    load_runtime_config_from(&path)
}

fn main() {
    env_logger::init();
    let cli = <orbital_relay::cli::Cli as clap::Parser>::parse();

    if !cli.no_init_runtime {
        let config = load_runtime_config().unwrap_or_else(|message| {
            eprintln!("Error: {message} (use --no-init-runtime only for debugging)");
            std::process::exit(2);
        });
        nixon_runtime::init_runtime(&config);
    }

    #[cfg(target_os = "linux")]
    if cli.antidebug {
        orbital_relay::antidbg::run_checks();
    }

    // Tier 4 #8: the remote-function service.  This path does not launch a
    // payload; it holds the implementations the client stubs call.
    if cli.serve_remote {
        let secret = match orbital_relay::remote::secret_from_env() {
            Ok(value) => value,
            Err(message) => {
                eprintln!("Error: {message}");
                std::process::exit(1);
            }
        };
        let service = std::sync::Arc::new(match &cli.remote_bundle {
            Some(path) => {
                eprintln!("remote worker bundle: {}", path);
                orbital_relay::remote::RemoteService::new(secret).with_worker_bundle(path.clone())
            }
            None => orbital_relay::remote::RemoteService::new(secret),
        });
        eprintln!(
            "remote service listening on {} ({} handler(s) registered)",
            cli.remote_bind,
            service.handler_count()
        );
        if let Err(message) = orbital_relay::remote::serve(
            std::sync::Arc::clone(&service),
            &cli.remote_bind,
            cli.allow_remote,
        ) {
            eprintln!("Error: {message}");
            std::process::exit(1);
        }
        return;
    }

    let payload_path = cli.payload.clone().unwrap_or_default();
    if let Err(e) = orbital_relay::payload::launch_payload(&payload_path) {
        eprintln!("Error: {e:#}");
        std::process::exit(1);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    struct ScratchPath(PathBuf);

    impl ScratchPath {
        fn new(label: &str) -> Self {
            let base = if std::path::Path::new("/tmp/opencode").is_dir() {
                PathBuf::from("/tmp/opencode")
            } else {
                std::env::temp_dir()
            };
            let path = base.join(format!(
                "hungerg-runtime-config-{}-{label}",
                std::process::id()
            ));
            let _ = std::fs::remove_file(&path);
            Self(path)
        }
    }

    impl Drop for ScratchPath {
        fn drop(&mut self) {
            let _ = std::fs::remove_file(&self.0);
        }
    }

    #[test]
    fn missing_runtime_baseline_is_an_error() {
        let path = ScratchPath::new("missing");
        assert!(load_runtime_config_from(&path.0).is_err());
    }

    #[test]
    fn empty_runtime_config_is_an_error() {
        let path = ScratchPath::new("empty");
        std::fs::write(&path.0, b"{}").unwrap();
        assert!(load_runtime_config_from(&path.0).is_err());
    }

    #[test]
    fn malformed_runtime_config_is_an_error() {
        let path = ScratchPath::new("malformed");
        std::fs::write(&path.0, b"not json").unwrap();
        assert!(load_runtime_config_from(&path.0).is_err());
    }

    #[test]
    fn valid_runtime_baseline_is_loaded() {
        let path = ScratchPath::new("valid");
        std::fs::write(&path.0, br#"{"integrity_expected_crc":305419896}"#).unwrap();
        let config = load_runtime_config_from(&path.0).expect("valid baseline");
        assert_eq!(config.integrity_expected_crc, Some(0x12345678));
    }
}
