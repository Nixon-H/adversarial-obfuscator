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

    match ext {
        "py" => {
            let status = std::process::Command::new("python3")
                .arg(&path)
                .status()
                .context("Failed to launch Python payload")?;
            if !status.success() {
                anyhow::bail!("Python payload exited with: {}", status);
            }
        }
        "bin" | "elf" | "" => {
            let status = std::process::Command::new(&path)
                .status()
                .context("Failed to launch native payload")?;
            if !status.success() {
                anyhow::bail!("Native payload exited with: {}", status);
            }
        }
        _ => {
            let status = std::process::Command::new("python3")
                .arg(&path)
                .status()
                .context("Failed to launch payload")?;
            if !status.success() {
                anyhow::bail!("Payload exited with: {}", status);
            }
        }
    }

    Ok(())
}
