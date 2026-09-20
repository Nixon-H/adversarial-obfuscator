use crate::memguard::scrub_memory;
use crate::platform::PagePerm;
use crate::sw_attestation::AttestationEngine;
#[cfg(feature = "sgx")]
use crate::tee_sgx::SgxEnclave;
use std::ptr;

const ENCLAVE_PAGE_SIZE: usize = 4096;
const ENCLAVE_REGION_SIZE: usize = 64 * 1024;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TeeType {
    None,
    IntelSgx,
    AmdSev,
    AppleSecureEnclave,
}

pub struct TeePartition {
    tee_type: TeeType,
    enclave_initialized: bool,
    measurement: [u8; 32],
    region_ptr: *mut u8,
    region_len: usize,
    #[cfg(feature = "sgx")]
    sgx_enclave: Option<SgxEnclave>,
}

impl TeePartition {
    pub fn new(tee_type: TeeType) -> Self {
        let measurement = match tee_type {
            TeeType::IntelSgx => [
                0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
                0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f, 0x10,
                0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18,
                0x19, 0x1a, 0x1b, 0x1c, 0x1d, 0x1e, 0x1f, 0x20,
            ],
            TeeType::AmdSev => [
                0xaa, 0xbb, 0xcc, 0xdd, 0xee, 0xff, 0x00, 0x11,
                0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88, 0x99,
                0xaa, 0xbb, 0xcc, 0xdd, 0xee, 0xff, 0x00, 0x11,
                0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88, 0x99,
            ],
            TeeType::AppleSecureEnclave => [
                0xfe, 0xed, 0xfa, 0xce, 0xfe, 0xed, 0xfa, 0xce,
                0xfe, 0xed, 0xfa, 0xce, 0xfe, 0xed, 0xfa, 0xce,
                0xfe, 0xed, 0xfa, 0xce, 0xfe, 0xed, 0xfa, 0xce,
                0xfe, 0xed, 0xfa, 0xce, 0xfe, 0xed, 0xfa, 0xce,
            ],
            TeeType::None => [0u8; 32],
        };

        TeePartition {
            tee_type,
            enclave_initialized: false,
            measurement,
            region_ptr: ptr::null_mut(),
            region_len: 0,
            #[cfg(feature = "sgx")]
            sgx_enclave: None,
        }
    }

    pub fn init_enclave(&mut self, payload: &[u8]) -> Result<(), String> {
        if self.enclave_initialized {
            return Err("Enclave already initialized".to_string());
        }

        #[cfg(feature = "sgx")]
        {
            if self.tee_type == TeeType::IntelSgx {
                let enclave_path = std::str::from_utf8(payload)
                    .unwrap_or("enclave.signed.so");
                match SgxEnclave::new(enclave_path, true) {
                    Ok(enclave) => {
                        self.measurement = enclave.measurement;
                        self.sgx_enclave = Some(enclave);
                        self.enclave_initialized = true;
                        eprintln!(
                            "TEE: SGX enclave initialized — MRENCLAVE={:02x?}",
                            self.measurement
                        );
                        return Ok(());
                    }
                    Err(e) => {
                        eprintln!(
                            "TEE: SGX hardware path failed ({}), falling back to software",
                            e
                        );
                    }
                }
            }
        }

        match self.tee_type {
            TeeType::IntelSgx | TeeType::AmdSev | TeeType::AppleSecureEnclave => {
                eprintln!("TEE: using software fallback — no hardware enclave detected");
            }
            TeeType::None => {
                eprintln!("TEE: TEE type is None, using software fallback");
            }
        }

        let region_size = ENCLAVE_REGION_SIZE.max(payload.len() + ENCLAVE_PAGE_SIZE);
        let page_size = crate::platform::page_size();
        let alloc_size = (region_size + page_size - 1) & !(page_size - 1);

        let ptr = crate::platform::alloc_pages(alloc_size);

        if ptr.is_null() {
            return Err("mmap failed to allocate enclave region".to_string());
        }

        let prot_result = crate::platform::protect_pages(ptr, alloc_size, PagePerm::ReadWrite);
        if prot_result.is_err() {
            crate::platform::free_pages(ptr, alloc_size);
            return Err("mprotect failed to set enclave region permissions".to_string());
        }

        if !payload.is_empty() {
            unsafe {
                ptr::copy_nonoverlapping(payload.as_ptr(), ptr, payload.len());
            }
        }

        let lock_result = crate::platform::lock_pages(ptr as *const u8, alloc_size);
        if lock_result.is_err() {
            eprintln!("TEE: warning — mlock failed, memory may be paged out");
        }

        self.region_ptr = ptr;
        self.region_len = alloc_size;

        let hasher = sha256_digest(payload);
        self.measurement.copy_from_slice(&hasher);

        self.enclave_initialized = true;

        eprintln!(
            "TEE: enclave initialized — region at {:p}, size {} bytes",
            self.region_ptr, self.region_len
        );

        Ok(())
    }

    pub fn seal_data(&self, data: &[u8]) -> Result<Vec<u8>, String> {
        if !self.enclave_initialized {
            return Err("Enclave not initialized".to_string());
        }

        #[cfg(feature = "sgx")]
        {
            if let Some(ref enclave) = self.sgx_enclave {
                return enclave.seal(data);
            }
        }

        let key = derive_sealing_key(&self.measurement);
        let iv = self.measurement[..16].try_into().unwrap_or(&[0u8; 16]);
        let mut sealed = data.to_vec();
        crate::decrypt::aes_256_ctr_decrypt(&mut sealed, &key, iv);
        let mut result = Vec::with_capacity(sealed.len() + 32);
        result.extend_from_slice(&self.measurement);
        result.extend_from_slice(&sealed);
        scrub_memory(key.as_ptr() as *mut u8, key.len());
        Ok(result)
    }

    pub fn unseal_data(&self, sealed: &[u8]) -> Result<Vec<u8>, String> {
        if !self.enclave_initialized {
            return Err("Enclave not initialized".to_string());
        }

        #[cfg(feature = "sgx")]
        {
            if let Some(ref enclave) = self.sgx_enclave {
                return enclave.unseal(sealed);
            }
        }

        if sealed.len() < 32 {
            return Err("Invalid sealed data — too short".to_string());
        }

        let key = derive_sealing_key(&self.measurement);
        let iv = self.measurement[..16].try_into().unwrap_or(&[0u8; 16]);
        let encrypted = &sealed[32..];
        let mut data = encrypted.to_vec();
        crate::decrypt::aes_256_ctr_decrypt(&mut data, &key, iv);
        scrub_memory(key.as_ptr() as *mut u8, key.len());
        Ok(data)
    }

    pub fn execute_in_enclave(&self, fn_id: u32, input: &[u8]) -> Result<Vec<u8>, String> {
        if !self.enclave_initialized {
            return Err("Enclave not initialized".to_string());
        }

        #[cfg(feature = "sgx")]
        {
            if self.sgx_enclave.is_some() {
                eprintln!("TEE: SGX ECALL dispatch not implemented — using software simulation");
            }
        }

        if self.region_ptr.is_null() {
            return Err("Enclave region is null".to_string());
        }

        let result = format!(
            "TEE: executed fn_id={} with {} bytes of input (software fallback)",
            fn_id,
            input.len(),
        );
        eprintln!("{}", result);

        let mut output = Vec::new();
        output.extend_from_slice(&fn_id.to_le_bytes());
        output.extend_from_slice(&input.len().to_le_bytes());
        output.extend_from_slice(input);

        Ok(output)
    }

    pub fn get_measurement(&self) -> [u8; 32] {
        #[cfg(feature = "sgx")]
        {
            if let Some(ref enclave) = self.sgx_enclave {
                return enclave.measurement;
            }
        }
        self.measurement
    }

    pub fn attest(&self, challenge: &[u8; 32]) -> Result<Vec<u8>, String> {
        if !self.enclave_initialized {
            return Err("Enclave not initialized".to_string());
        }

        #[cfg(feature = "sgx")]
        {
            if self.sgx_enclave.is_some() {
                eprintln!("TEE: SGX remote attestation not implemented — using software simulation");
            }
        }

        let mut response = Vec::with_capacity(96);
        response.extend_from_slice(&self.measurement);
        response.extend_from_slice(challenge);

        let engine = AttestationEngine::new();
        let sw_response = engine.handle_challenge(challenge);
        response.extend_from_slice(&sw_response);

        let hash = sha256_digest(&response);
        response.extend_from_slice(&hash);

        if !engine.verify_integrity() {
            return Err("SW attestation integrity check failed — possible tampering".to_string());
        }

        Ok(response)
    }
}

impl Drop for TeePartition {
    fn drop(&mut self) {
        if !self.region_ptr.is_null() && self.region_len > 0 {
            unsafe {
                ptr::write_bytes(self.region_ptr, 0u8, self.region_len);
            }
            let _ = crate::platform::unlock_pages(self.region_ptr as *const u8, self.region_len);
            crate::platform::free_pages(self.region_ptr, self.region_len);
        }
    }
}

fn sha256_digest(data: &[u8]) -> [u8; 32] {
    let mut hash = [0u8; 32];
    let mut h = [
        0x6a09e667u32, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
        0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
    ];
    let k = [
        0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
        0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
        0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
        0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
        0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
        0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
        0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
        0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
        0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
        0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
        0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
        0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
        0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
        0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
        0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
        0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
    ];

    let msg_len_bits = (data.len() as u64) * 8;
    let mut padded = data.to_vec();
    padded.push(0x80);
    while (padded.len() + 8) % 64 != 0 {
        padded.push(0);
    }
    padded.extend_from_slice(&msg_len_bits.to_be_bytes());

    for chunk in padded.chunks(64) {
        let mut w = [0u32; 64];
        for t in 0..16 {
            w[t] = u32::from_be_bytes([
                chunk[t * 4],
                chunk[t * 4 + 1],
                chunk[t * 4 + 2],
                chunk[t * 4 + 3],
            ]);
        }
        for t in 16..64 {
            let s0 = w[t - 15].rotate_right(7) ^ w[t - 15].rotate_right(18) ^ (w[t - 15] >> 3);
            let s1 = w[t - 2].rotate_right(17) ^ w[t - 2].rotate_right(19) ^ (w[t - 2] >> 10);
            w[t] = w[t - 16]
                .wrapping_add(s0)
                .wrapping_add(w[t - 7])
                .wrapping_add(s1);
        }

        let mut a = h[0];
        let mut b = h[1];
        let mut c = h[2];
        let mut d = h[3];
        let mut e = h[4];
        let mut f = h[5];
        let mut g = h[6];
        let mut h_val = h[7];

        for t in 0..64 {
            let s1 = e.rotate_right(6) ^ e.rotate_right(11) ^ e.rotate_right(25);
            let ch = (e & f) ^ ((!e) & g);
            let temp1 = h_val
                .wrapping_add(s1)
                .wrapping_add(ch)
                .wrapping_add(k[t])
                .wrapping_add(w[t]);
            let s0 = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
            let maj = (a & b) ^ (a & c) ^ (b & c);
            let temp2 = s0.wrapping_add(maj);

            h_val = g;
            g = f;
            f = e;
            e = d.wrapping_add(temp1);
            d = c;
            c = b;
            b = a;
            a = temp1.wrapping_add(temp2);
        }

        h[0] = h[0].wrapping_add(a);
        h[1] = h[1].wrapping_add(b);
        h[2] = h[2].wrapping_add(c);
        h[3] = h[3].wrapping_add(d);
        h[4] = h[4].wrapping_add(e);
        h[5] = h[5].wrapping_add(f);
        h[6] = h[6].wrapping_add(g);
        h[7] = h[7].wrapping_add(h_val);
    }

    for (i, val) in h.iter().enumerate() {
        hash[i * 4..(i + 1) * 4].copy_from_slice(&val.to_be_bytes());
    }
    hash
}

fn derive_sealing_key(measurement: &[u8; 32]) -> [u8; 32] {
    let mut key = [0u8; 32];
    for i in 0..32 {
        key[i] = measurement[i] ^ 0x5c;
    }
    key
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_new_tee_none() {
        let tee = TeePartition::new(TeeType::None);
        assert!(!tee.enclave_initialized);
        assert_eq!(tee.tee_type, TeeType::None);
        assert_eq!(tee.measurement, [0u8; 32]);
    }

    #[test]
    fn test_new_tee_sgx() {
        let tee = TeePartition::new(TeeType::IntelSgx);
        assert_eq!(tee.tee_type, TeeType::IntelSgx);
        assert_ne!(tee.measurement, [0u8; 32]);
    }

    #[test]
    fn test_init_software_fallback() {
        let mut tee = TeePartition::new(TeeType::None);
        let payload = b"test enclave payload";
        let result = tee.init_enclave(payload);
        assert!(result.is_ok());
        assert!(tee.enclave_initialized);
    }

    #[test]
    fn test_init_twice_fails() {
        let mut tee = TeePartition::new(TeeType::None);
        assert!(tee.init_enclave(b"payload").is_ok());
        assert!(tee.init_enclave(b"payload").is_err());
    }

    #[test]
    fn test_seal_unseal_roundtrip() {
        let mut tee = TeePartition::new(TeeType::None);
        tee.init_enclave(b"payload").unwrap();
        let original = b"Hello TEE world!";
        let sealed = tee.seal_data(original).unwrap();
        assert!(sealed.len() > original.len());
        let unsealed = tee.unseal_data(&sealed).unwrap();
        assert_eq!(unsealed, original);
    }

    #[test]
    fn test_seal_before_init_fails() {
        let tee = TeePartition::new(TeeType::None);
        assert!(tee.seal_data(b"data").is_err());
    }

    #[test]
    fn test_unseal_before_init_fails() {
        let tee = TeePartition::new(TeeType::None);
        assert!(tee.unseal_data(b"data").is_err());
    }

    #[test]
    fn test_unseal_too_short() {
        let mut tee = TeePartition::new(TeeType::None);
        tee.init_enclave(b"payload").unwrap();
        assert!(tee.unseal_data(b"short").is_err());
    }

    #[test]
    fn test_execute_in_enclave() {
        let mut tee = TeePartition::new(TeeType::None);
        tee.init_enclave(b"payload").unwrap();
        let result = tee.execute_in_enclave(42, b"input data").unwrap();
        assert!(!result.is_empty());
    }

    #[test]
    fn test_execute_before_init_fails() {
        let tee = TeePartition::new(TeeType::None);
        assert!(tee.execute_in_enclave(0, b"").is_err());
    }

    #[test]
    fn test_get_measurement() {
        let mut tee = TeePartition::new(TeeType::IntelSgx);
        tee.init_enclave(b"payload").unwrap();
        let m = tee.get_measurement();
        assert_eq!(m.len(), 32);
        assert_ne!(m, [0u8; 32]);
    }

    #[test]
    fn test_attest() {
        let mut tee = TeePartition::new(TeeType::None);
        tee.init_enclave(b"payload").unwrap();
        let challenge = [0xabu8; 32];
        let response = tee.attest(&challenge).unwrap();
        assert!(response.len() > 96);
    }

    #[test]
    fn test_attest_before_init_fails() {
        let tee = TeePartition::new(TeeType::None);
        let challenge = [0u8; 32];
        assert!(tee.attest(&challenge).is_err());
    }

    #[test]
    fn test_drop_cleans_memory() {
        let mut tee = TeePartition::new(TeeType::None);
        tee.init_enclave(b"data").unwrap();
        drop(tee);
    }

    #[test]
    fn test_sha256_digest() {
        let hash = sha256_digest(b"hello");
        assert_ne!(hash, [0u8; 32]);
        let hash2 = sha256_digest(b"hello");
        assert_eq!(hash, hash2);
    }
}
