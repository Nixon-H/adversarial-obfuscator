use crate::memguard::scrub_memory;

// Pure Rust AES-256-CTR implementation (no external dependencies)

const SBOX: [u8; 256] = [
    0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5, 0x30, 0x01, 0x67, 0x2b, 0xfe, 0xd7, 0xab, 0x76,
    0xca, 0x82, 0xc9, 0x7d, 0xfa, 0x59, 0x47, 0xf0, 0xad, 0xd4, 0xa2, 0xaf, 0x9c, 0xa4, 0x72, 0xc0,
    0xb7, 0xfd, 0x93, 0x26, 0x36, 0x3f, 0xf7, 0xcc, 0x34, 0xa5, 0xe5, 0xf1, 0x71, 0xd8, 0x31, 0x15,
    0x04, 0xc7, 0x23, 0xc3, 0x18, 0x96, 0x05, 0x9a, 0x07, 0x12, 0x80, 0xe2, 0xeb, 0x27, 0xb2, 0x75,
    0x09, 0x83, 0x2c, 0x1a, 0x1b, 0x6e, 0x5a, 0xa0, 0x52, 0x3b, 0xd6, 0xb3, 0x29, 0xe3, 0x2f, 0x84,
    0x53, 0xd1, 0x00, 0xed, 0x20, 0xfc, 0xb1, 0x5b, 0x6a, 0xcb, 0xbe, 0x39, 0x4a, 0x4c, 0x58, 0xcf,
    0xd0, 0xef, 0xaa, 0xfb, 0x43, 0x4d, 0x33, 0x85, 0x45, 0xf9, 0x02, 0x7f, 0x50, 0x3c, 0x9f, 0xa8,
    0x51, 0xa3, 0x40, 0x8f, 0x92, 0x9d, 0x38, 0xf5, 0xbc, 0xb6, 0xda, 0x21, 0x10, 0xff, 0xf3, 0xd2,
    0xcd, 0x0c, 0x13, 0xec, 0x5f, 0x97, 0x44, 0x17, 0xc4, 0xa7, 0x7e, 0x3d, 0x64, 0x5d, 0x19, 0x73,
    0x60, 0x81, 0x4f, 0xdc, 0x22, 0x2a, 0x90, 0x88, 0x46, 0xee, 0xb8, 0x14, 0xde, 0x5e, 0x0b, 0xdb,
    0xe0, 0x32, 0x3a, 0x0a, 0x49, 0x06, 0x24, 0x5c, 0xc2, 0xd3, 0xac, 0x62, 0x91, 0x95, 0xe4, 0x79,
    0xe7, 0xc8, 0x37, 0x6d, 0x8d, 0xd5, 0x4e, 0xa9, 0x6c, 0x56, 0xf4, 0xea, 0x65, 0x7a, 0xae, 0x08,
    0xba, 0x78, 0x25, 0x2e, 0x1c, 0xa6, 0xb4, 0xc6, 0xe8, 0xdd, 0x74, 0x1f, 0x4b, 0xbd, 0x8b, 0x8a,
    0x70, 0x3e, 0xb5, 0x66, 0x48, 0x03, 0xf6, 0x0e, 0x61, 0x35, 0x57, 0xb9, 0x86, 0xc1, 0x1d, 0x9e,
    0xe1, 0xf8, 0x98, 0x11, 0x69, 0xd9, 0x8e, 0x94, 0x9b, 0x1e, 0x87, 0xe9, 0xce, 0x55, 0x28, 0xdf,
    0x8c, 0xa1, 0x89, 0x0d, 0xbf, 0xe6, 0x42, 0x68, 0x41, 0x99, 0x2d, 0x0f, 0xb0, 0x54, 0xbb, 0x16,
];

const RCON: [u8; 15] = [
    0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1b, 0x36, 0x6c, 0xd8, 0xab, 0x4d, 0x9a,
];

#[inline]
fn xtime(a: u8) -> u8 {
    let mut r = a << 1;
    if a & 0x80 != 0 {
        r ^= 0x1b;
    }
    r
}

#[inline]
fn gf_mul(a: u8, b: u8) -> u8 {
    let mut result = 0u8;
    let mut x = a;
    let mut y = b;
    for _ in 0..8 {
        if y & 1 != 0 {
            result ^= x;
        }
        x = xtime(x);
        y >>= 1;
    }
    result
}

fn sub_word(word: u32) -> u32 {
    let b0 = SBOX[(word >> 24) as usize] as u32;
    let b1 = SBOX[(word >> 16 & 0xFF) as usize] as u32;
    let b2 = SBOX[(word >> 8 & 0xFF) as usize] as u32;
    let b3 = SBOX[(word & 0xFF) as usize] as u32;
    (b0 << 24) | (b1 << 16) | (b2 << 8) | b3
}

fn rot_word(word: u32) -> u32 {
    (word << 8) | (word >> 24)
}

fn expand_key(key: &[u8; 32]) -> [u32; 60] {
    let mut w = [0u32; 60];
    for i in 0..8 {
        w[i] = u32::from_be_bytes([key[4 * i], key[4 * i + 1], key[4 * i + 2], key[4 * i + 3]]);
    }
    for i in 8..60 {
        let mut temp = w[i - 1];
        if i % 8 == 0 {
            temp = sub_word(rot_word(temp)) ^ (RCON[i / 8 - 1] as u32);
        } else if i % 8 == 4 {
            temp = sub_word(temp);
        }
        w[i] = w[i - 8] ^ temp;
    }
    w
}

fn add_round_key(state: &mut [u32; 4], round_key: &[u32; 4]) {
    for i in 0..4 {
        state[i] ^= round_key[i];
    }
}

fn sub_bytes(state: &mut [u32; 4]) {
    for i in 0..4 {
        let s = state[i];
        let b0 = SBOX[(s >> 24) as usize] as u32;
        let b1 = SBOX[(s >> 16 & 0xFF) as usize] as u32;
        let b2 = SBOX[(s >> 8 & 0xFF) as usize] as u32;
        let b3 = SBOX[(s & 0xFF) as usize] as u32;
        state[i] = (b0 << 24) | (b1 << 16) | (b2 << 8) | b3;
    }
}

fn shift_rows(state: &mut [u32; 4]) {
    let s0 = state[0];
    let s1 = state[1];
    let s2 = state[2];
    let s3 = state[3];
    state[0] = (s0 & 0xFF00_FFFF) | ((s1 >> 16) & 0xFF) << 16;
    state[1] = (s1 & 0xFFFF_00FF) | ((s2 >> 8) & 0xFF) << 8;
    state[2] = (s2 & 0xFFFF_FF00) | (s3 & 0xFF);
    state[3] = (s3 & 0x00FF_FFFF) | ((s0 >> 24) & 0xFF) << 24;
}

fn mix_columns(state: &mut [u32; 4]) {
    for i in 0..4 {
        let s = state[i];
        let a0 = (s >> 24) as u8;
        let a1 = (s >> 16) as u8;
        let a2 = (s >> 8) as u8;
        let a3 = s as u8;
        let b0 = gf_mul(a0, 2) ^ gf_mul(a1, 3) ^ a2 ^ a3;
        let b1 = a0 ^ gf_mul(a1, 2) ^ gf_mul(a2, 3) ^ a3;
        let b2 = a0 ^ a1 ^ gf_mul(a2, 2) ^ gf_mul(a3, 3);
        let b3 = gf_mul(a0, 3) ^ a1 ^ a2 ^ gf_mul(a3, 2);
        state[i] = u32::from_be_bytes([b0, b1, b2, b3]);
    }
}

fn aes_256_encrypt_block(block: &[u8; 16], w: &[u32; 60]) -> [u8; 16] {
    let mut state: [u32; 4] = [
        u32::from_be_bytes([block[0], block[1], block[2], block[3]]),
        u32::from_be_bytes([block[4], block[5], block[6], block[7]]),
        u32::from_be_bytes([block[8], block[9], block[10], block[11]]),
        u32::from_be_bytes([block[12], block[13], block[14], block[15]]),
    ];
    add_round_key(&mut state, &[w[0], w[1], w[2], w[3]]);
    for round in 1..=13 {
        sub_bytes(&mut state);
        shift_rows(&mut state);
        mix_columns(&mut state);
        add_round_key(&mut state, &[w[4 * round], w[4 * round + 1], w[4 * round + 2], w[4 * round + 3]]);
    }
    sub_bytes(&mut state);
    shift_rows(&mut state);
    add_round_key(&mut state, &[w[56], w[57], w[58], w[59]]);
    let mut out = [0u8; 16];
    for i in 0..4 {
        let bytes = state[i].to_be_bytes();
        out[4 * i] = bytes[0];
        out[4 * i + 1] = bytes[1];
        out[4 * i + 2] = bytes[2];
        out[4 * i + 3] = bytes[3];
    }
    out
}

pub fn aes_256_ctr_decrypt(data: &mut [u8], key: &[u8; 32], iv: &[u8; 16]) {
    let w = expand_key(key);
    let mut counter = *iv;
    for chunk in data.chunks_mut(16) {
        let keystream = aes_256_encrypt_block(&counter, &w);
        for (d, k) in chunk.iter_mut().zip(keystream.iter()) {
            *d ^= k;
        }
        for i in (0..16).rev() {
            counter[i] = counter[i].wrapping_add(1);
            if counter[i] != 0 {
                break;
            }
        }
    }
}

pub fn derive_block_key(seed: &[u8; 32], block_index: u32) -> [u8; 32] {
    let w = expand_key(seed);
    let mut input = [0u8; 16];
    input[..4].copy_from_slice(&block_index.to_le_bytes());
    let part1 = aes_256_encrypt_block(&input, &w);
    for b in input.iter_mut().take(16) {
        *b = b.wrapping_add(1);
    }
    let part2 = aes_256_encrypt_block(&input, &w);
    let mut key = [0u8; 32];
    key[..16].copy_from_slice(&part1);
    key[16..].copy_from_slice(&part2);
    key
}

pub fn aes_256_ctr_decrypt_slice(data: &mut [u8], key: &[u8; 32], iv: &[u8; 16]) {
    aes_256_ctr_decrypt(data, key, iv);
    scrub_memory(key.as_ptr() as *mut u8, key.len());
}

/// Decrypt a block and compile it via polymorphic JIT.
/// When microjit is enabled, the decrypted block is transformed before execution.
/// When accumulated_hash is provided, uses history-bound key derivation.
pub fn decrypt_and_jit(
    encrypted_block: &[u8],
    key: &[u8; 32],
    iv: &[u8; 16],
    seed: u64,
    enable_microjit: bool,
    accumulated_hash: Option<&[u8; 32]>,
) -> Result<*mut u8, String> {
    let effective_key: [u8; 32];
    let effective_iv: [u8; 16];

    let (used_key, used_iv) = if let Some(acc_hash) = accumulated_hash {
        let mut combined = Vec::with_capacity(64);
        combined.extend_from_slice(key);
        combined.extend_from_slice(acc_hash);
        combined.extend_from_slice(&seed.to_le_bytes());
        let derived = crate::ledger::sha256(&combined);
        let mut derived_iv = *iv;
        // Mix accumulated hash into IV
        for (d, a) in derived_iv.iter_mut().zip(acc_hash.iter()) {
            *d ^= a;
        }
        effective_key = derived;
        effective_iv = derived_iv;
        (&effective_key, &effective_iv)
    } else {
        (key, iv)
    };

    let mut decrypted = encrypted_block.to_vec();
    aes_256_ctr_decrypt(&mut decrypted, used_key, used_iv);

    let result = if enable_microjit {
        crate::jit::polymorphic_jit_compile(&decrypted, key, seed)
    } else {
        let mut mgr = crate::jit::JitMemoryManager::new();
        let ptr = mgr.allocate_executable(decrypted.len())?;
        unsafe {
            std::ptr::copy_nonoverlapping(decrypted.as_ptr(), ptr, decrypted.len());
        }
        #[cfg(target_arch = "x86_64")]
        unsafe {
            core::arch::asm!("mfence", options(nostack, nomem));
        }
        #[cfg(target_arch = "aarch64")]
        unsafe {
            core::arch::asm!("dmb sy", options(nostack, nomem));
        }
        let _ = mgr;
        Ok(ptr)
    };
    scrub_memory(key.as_ptr() as *mut u8, key.len());
    result
}

fn make_nonce(key: &[u8; 32], ctx: u64) -> [u8; 16] {
    let mut nonce = [0u8; 16];
    nonce[..8].copy_from_slice(&crate::ledger::sha256(key)[..8]);
    nonce[8..16].copy_from_slice(&ctx.to_le_bytes());
    nonce
}

pub fn decrypt_with_hpc_check(
    encrypted: &[u8],
    key: &[u8; 32],
    hpc_seed: u64,
) -> Result<Vec<u8>, String> {
    let derived = crate::hpc_key::derive_key_from_hpc(key, hpc_seed)?;
    let mut data = encrypted.to_vec();
    let iv = make_nonce(&derived, hpc_seed);
    aes_256_ctr_decrypt(&mut data, &derived, &iv);
    scrub_memory(derived.as_ptr() as *mut u8, derived.len());
    Ok(data)
}

pub fn decrypt_with_proof_check(
    encrypted_data: &[u8],
    key: &[u8; 32],
    proof: &super::ledger::IntegrityProof,
    text_section: &[u8],
) -> Result<Vec<u8>, String> {
    if !super::ledger::full_integrity_check(text_section, proof) {
        return Err("Integrity proof verification failed — decryption denied".to_string());
    }
    let derived_key = super::ledger::derive_decryption_key(key, proof);
    let mut data = encrypted_data.to_vec();
    let iv = make_nonce(&derived_key, proof.timestamp);
    aes_256_ctr_decrypt(&mut data, &derived_key, &iv);
    scrub_memory(derived_key.as_ptr() as *mut u8, derived_key.len());
    Ok(data)
}

/// History-bound decryption: uses accumulated SHA-256 hash of prior fragment
/// executions as additional entropy in key derivation.
/// The accumulated_hash should be loaded from the build-time persisted state.
pub fn decrypt_with_history_bound(
    encrypted_data: &[u8],
    key: &[u8; 32],
    accumulated_hash: &[u8; 32],
    fragment_id: u32,
) -> Result<Vec<u8>, String> {
    let mut combined = Vec::with_capacity(64);
    combined.extend_from_slice(key);
    combined.extend_from_slice(accumulated_hash);
    combined.extend_from_slice(&fragment_id.to_le_bytes());
    let derived = crate::ledger::sha256(&combined);
    let mut data = encrypted_data.to_vec();
    let iv = make_nonce(&derived, fragment_id as u64);
    aes_256_ctr_decrypt(&mut data, &derived, &iv);
    scrub_memory(derived.as_ptr() as *mut u8, derived.len());
    Ok(data)
}
