//! SGX (Software Guard Extensions) hardware enclave support.
//!
//! Provides FFI bindings to the Intel SGX SDK for hardware-backed
//! enclave creation, destruction, sealing, and unsealing.
//!
//! All definitions are gated behind `#[cfg(feature = "sgx")]` and
//! link against `libsgx_urts.so` and `libsgx_uae_service.so`.
//!
//! # Usage
//!
//! This module is automatically used by [`crate::tee::TeePartition`]
//! when the `sgx` feature is enabled and [`TeeType::IntelSgx`] is selected.
//! Without the feature, a software fallback is used instead.

/// SGX return status code indicating success.
#[cfg(feature = "sgx")]
pub const SGX_SUCCESS: u32 = 0x0000;

/// SGX enclave identifier (opaque handle).
#[cfg(feature = "sgx")]
#[allow(non_camel_case_types)]
pub type sgx_enclave_id_t = u64;

/// SGX measurement (MRENCLAVE / MRSIGNER) — a SHA-256 hash of the enclave.
#[cfg(feature = "sgx")]
#[repr(C)]
#[derive(Debug, Clone, Copy)]
pub struct sgx_measurement_t {
    pub m: [u8; 32],
}

/// CPU attributes (flags + XFRM) associated with an enclave.
#[cfg(feature = "sgx")]
#[repr(C)]
#[derive(Debug, Clone, Copy)]
pub struct sgx_attributes_t {
    pub flags: u64,
    pub xfrm: u64,
}

/// Miscellaneous attributes populated by [`sgx_create_enclave`].
#[cfg(feature = "sgx")]
#[repr(C)]
#[derive(Debug, Clone, Copy)]
pub struct sgx_misc_attribute_t {
    pub mr_enclave: sgx_measurement_t,
    pub mr_signer: sgx_measurement_t,
    pub se_attributes: sgx_attributes_t,
}

// ---------------------------------------------------------------------------
// FFI: libsgx_urts — enclave lifecycle
// ---------------------------------------------------------------------------

#[cfg(feature = "sgx")]
#[link(name = "sgx_urts")]
extern "C" {
    pub fn sgx_create_enclave(
        file_name: *const i8,
        debug: i32,
        launch_token: *mut u8,
        launch_token_updated: *mut i32,
        enclave_id: *mut sgx_enclave_id_t,
        misc_attr: *mut sgx_misc_attribute_t,
    ) -> u32;

    pub fn sgx_destroy_enclave(enclave_id: sgx_enclave_id_t) -> u32;
}

// ---------------------------------------------------------------------------
// FFI: libsgx_uae_service — sealing & attestation services
// ---------------------------------------------------------------------------

#[cfg(feature = "sgx")]
#[link(name = "sgx_uae_service")]
extern "C" {
    pub fn sgx_seal_data(
        additional_text_length: u32,
        additional_text: *const u8,
        text_length: u32,
        text: *const u8,
        sealed_data_length: u32,
        sealed_data: *mut u8,
    ) -> u32;

    pub fn sgx_unseal_data(
        sealed_data: *const u8,
        sealed_data_length: u32,
        additional_text: *mut u8,
        additional_text_length: *mut u32,
        text: *mut u8,
        text_length: *mut u32,
    ) -> u32;
}

// ---------------------------------------------------------------------------
// Safe wrapper — SgxEnclave
// ---------------------------------------------------------------------------

/// An active SGX enclave instance.
///
/// Dropping the instance automatically calls [`sgx_destroy_enclave`].
#[cfg(feature = "sgx")]
pub struct SgxEnclave {
    /// Opaque SGX enclave identifier.
    pub enclave_id: sgx_enclave_id_t,
    /// MRENCLAVE measurement (SHA-256 of the enclave build).
    pub measurement: [u8; 32],
}

#[cfg(feature = "sgx")]
impl SgxEnclave {
    /// Create a new SGX enclave from a signed `.so` file.
    ///
    /// # Errors
    /// Returns `Err` if the path contains a nul byte or if
    /// [`sgx_create_enclave`] fails.
    pub fn new(enclave_path: &str, debug: bool) -> Result<Self, String> {
        let path_cstr = std::ffi::CString::new(enclave_path)
            .map_err(|_| "SGX: enclave path contains interior nul byte".to_string())?;

        let debug_flag: i32 = if debug { 1 } else { 0 };
        let mut enclave_id: sgx_enclave_id_t = 0;
        let mut misc_attr: sgx_misc_attribute_t = unsafe { std::mem::zeroed() };
        let mut launch_token: [u8; 1024] = [0u8; 1024];
        let mut launch_token_updated: i32 = 0;

        let status = unsafe {
            sgx_create_enclave(
                path_cstr.as_ptr(),
                debug_flag,
                launch_token.as_mut_ptr(),
                &mut launch_token_updated,
                &mut enclave_id,
                &mut misc_attr,
            )
        };

        if status != SGX_SUCCESS {
            return Err(format!(
                "SGX: sgx_create_enclave failed with status 0x{status:04x}"
            ));
        }

        eprintln!(
            "TEE: SGX enclave created — id={}, MRENCLAVE={:02x?}",
            enclave_id, misc_attr.mr_enclave.m
        );

        Ok(SgxEnclave {
            enclave_id,
            measurement: misc_attr.mr_enclave.m,
        })
    }

    /// Seal (encrypt + MAC) plaintext using the enclave's hardware sealing key.
    ///
    /// The MRENCLAVE measurement is included as associated data.
    ///
    /// # Errors
    /// Returns `Err` if [`sgx_seal_data`] fails.
    pub fn seal(&self, data: &[u8]) -> Result<Vec<u8>, String> {
        // SGX sealed-data overhead covers the header, IV, and MAC tag.
        // A generous margin ensures the call never fails due to buffer size.
        const SGX_OVERHEAD: usize = 256;
        let buf_len = data.len() + SGX_OVERHEAD;
        let mut sealed_buf = vec![0u8; buf_len];

        let aad: &[u8] = &self.measurement;

        let status = unsafe {
            sgx_seal_data(
                aad.len() as u32,
                aad.as_ptr(),
                data.len() as u32,
                data.as_ptr(),
                buf_len as u32,
                sealed_buf.as_mut_ptr(),
            )
        };

        if status != SGX_SUCCESS {
            return Err(format!(
                "SGX: sgx_seal_data failed with status 0x{status:04x}"
            ));
        }

        Ok(sealed_buf)
    }

    /// Unseal (verify MAC + decrypt) a blob previously produced by [`seal`].
    ///
    /// # Errors
    /// Returns `Err` if [`sgx_unseal_data`] fails, e.g. the blob was
    /// tampered with or was sealed by a different enclave.
    pub fn unseal(&self, sealed_data: &[u8]) -> Result<Vec<u8>, String> {
        let mut aad_buf = [0u8; 32];
        let mut aad_len: u32 = aad_buf.len() as u32;
        let mut text_buf = vec![0u8; sealed_data.len() * 2];
        let mut text_len: u32 = text_buf.len() as u32;

        let status = unsafe {
            sgx_unseal_data(
                sealed_data.as_ptr(),
                sealed_data.len() as u32,
                aad_buf.as_mut_ptr(),
                &mut aad_len,
                text_buf.as_mut_ptr(),
                &mut text_len,
            )
        };

        if status != SGX_SUCCESS {
            return Err(format!(
                "SGX: sgx_unseal_data failed with status 0x{status:04x}"
            ));
        }

        text_buf.truncate(text_len as usize);
        Ok(text_buf)
    }
}

#[cfg(feature = "sgx")]
impl Drop for SgxEnclave {
    fn drop(&mut self) {
        let status = unsafe { sgx_destroy_enclave(self.enclave_id) };
        if status != SGX_SUCCESS {
            eprintln!("TEE: sgx_destroy_enclave warning: status 0x{status:04x}");
        }
    }
}
