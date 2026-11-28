//! Operating-system randomness for nonces. This module is crate-internal:
//! nonce generation must fail closed rather than falling back to time or a
//! predictable counter when the OS CSPRNG is unavailable.

/// Fill `buf` with bytes from the operating-system CSPRNG.
pub(crate) fn fill_random(buf: &mut [u8]) -> Result<(), String> {
    if buf.is_empty() {
        return Ok(());
    }
    fill_random_os(buf)
}

#[cfg(target_os = "linux")]
fn fill_random_os(buf: &mut [u8]) -> Result<(), String> {
    let mut written = 0usize;
    while written < buf.len() {
        let ret = unsafe {
            libc::getrandom(
                buf.as_mut_ptr().add(written).cast::<libc::c_void>(),
                buf.len() - written,
                0,
            )
        };
        if ret > 0 {
            written += ret as usize;
            continue;
        }
        let err = std::io::Error::last_os_error();
        if ret < 0 && err.raw_os_error() == Some(libc::EINTR) {
            continue;
        }
        return Err(format!("getrandom failed: {err}"));
    }
    Ok(())
}

#[cfg(all(unix, not(target_os = "linux")))]
fn fill_random_os(buf: &mut [u8]) -> Result<(), String> {
    use std::io::Read;
    std::fs::File::open("/dev/urandom")
        .and_then(|mut file| file.read_exact(buf))
        .map_err(|err| format!("failed to read /dev/urandom: {err}"))
}

#[cfg(windows)]
fn fill_random_os(buf: &mut [u8]) -> Result<(), String> {
    // BCryptGenRandom with a null algorithm handle and
    // BCRYPT_USE_SYSTEM_PREFERRED_RNG uses the system-preferred RNG.
    const BCRYPT_USE_SYSTEM_PREFERRED_RNG: u32 = 0x0000_0002;
    #[link(name = "bcrypt")]
    extern "system" {
        fn BCryptGenRandom(
            algorithm: *mut core::ffi::c_void,
            buffer: *mut u8,
            buffer_len: u32,
            flags: u32,
        ) -> i32;
    }
    let len = u32::try_from(buf.len()).map_err(|_| "random buffer too large".to_string())?;
    let status = unsafe {
        BCryptGenRandom(
            core::ptr::null_mut(),
            buf.as_mut_ptr(),
            len,
            BCRYPT_USE_SYSTEM_PREFERRED_RNG,
        )
    };
    if status >= 0 {
        Ok(())
    } else {
        Err(format!("BCryptGenRandom failed: NTSTATUS 0x{status:08x}"))
    }
}

#[cfg(not(any(unix, windows)))]
fn fill_random_os(_buf: &mut [u8]) -> Result<(), String> {
    Err("no operating-system CSPRNG implementation for this target".to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn fill_random_fills_requested_length() {
        let mut bytes = [0u8; 32];
        fill_random(&mut bytes).expect("OS randomness");
        // Do not assert nonzero: all-zero is a valid, if improbable, output.
    }

    #[test]
    fn fill_random_empty_is_ok() {
        fill_random(&mut []).expect("empty random fill");
    }
}
