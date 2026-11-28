use anyhow::{Context, Result};

pub fn launch_payload(payload_path: &str) -> Result<()> {
    if payload_path.is_empty() {
        anyhow::bail!("No payload specified. Use --payload <path>");
    }

    let path = std::path::PathBuf::from(payload_path);

    if !path.exists() {
        anyhow::bail!("Payload file not found: {}", payload_path);
    }

    let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("");
    // A bare relative filename contains no path separator. On Unix,
    // Command::new would search PATH instead of executing the file whose
    // existence was checked above, so anchor every relative path in the
    // current directory before spawning it.
    let launch_path = if path.is_absolute() {
        path.clone()
    } else {
        std::env::current_dir()
            .context("Failed to resolve current directory")?
            .join(&path)
    };

    match ext {
        "py" => {
            let status = std::process::Command::new("python3")
                .arg(&launch_path)
                .status()
                .context("Failed to launch Python payload")?;
            if !status.success() {
                anyhow::bail!("Python payload exited with: {}", status);
            }
        }
        "bin" | "elf" | "" => {
            let status = std::process::Command::new(&launch_path)
                .status()
                .context("Failed to launch native payload")?;
            if !status.success() {
                anyhow::bail!("Native payload exited with: {}", status);
            }
        }
        _ => {
            let status = std::process::Command::new("python3")
                .arg(&launch_path)
                .status()
                .context("Failed to launch payload")?;
            if !status.success() {
                anyhow::bail!("Payload exited with: {}", status);
            }
        }
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[cfg(unix)]
    #[test]
    fn bare_relative_native_payload_executes_the_checked_file() {
        use std::os::unix::fs::PermissionsExt;
        use std::time::{SystemTime, UNIX_EPOCH};

        struct CwdGuard(std::path::PathBuf);
        impl Drop for CwdGuard {
            fn drop(&mut self) {
                let _ = std::env::set_current_dir(&self.0);
            }
        }
        struct Scratch(std::path::PathBuf);
        impl Drop for Scratch {
            fn drop(&mut self) {
                let _ = std::fs::remove_dir_all(&self.0);
            }
        }

        let unique = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let root = std::env::temp_dir().join(format!(
            "orbital-relay-payload-test-{}-{unique}",
            std::process::id()
        ));
        std::fs::create_dir(&root).unwrap();
        let _scratch = Scratch(root.clone());
        let name = format!(
            "orbital-relay-bare-{}-{unique}.bin",
            std::process::id()
        );
        let payload = root.join(&name);
        std::fs::write(&payload, "#!/bin/sh\nexit 0\n").unwrap();
        std::fs::set_permissions(&payload, std::fs::Permissions::from_mode(0o700)).unwrap();

        let original_cwd = std::env::current_dir().unwrap();
        let _cwd_guard = CwdGuard(original_cwd);
        std::env::set_current_dir(&root).unwrap();
        let result = launch_payload(&name);
        assert!(result.is_ok(), "bare relative payload failed: {result:?}");
    }
}
