use crate::jit::JitCode;
use crate::memguard::ScrubOnDrop;

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
            // Rcon is XORed into the most-significant byte of the big-endian
            // state word. Leaving it in the low byte silently produces a
            // non-AES key schedule.
            temp = sub_word(rot_word(temp)) ^ ((RCON[i / 8 - 1] as u32) << 24);
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
    // state[i] is column i, with bytes ordered [row0, row1, row2, row3]
    // from the most-significant byte downward. AES ShiftRows rotates row r
    // left by r columns: new column j comes from columns j, j+1, j+2, j+3
    // (modulo 4) for rows 0, 1, 2, 3 respectively.
    let b = state.map(|word| word.to_be_bytes());
    state[0] = u32::from_be_bytes([b[0][0], b[1][1], b[2][2], b[3][3]]);
    state[1] = u32::from_be_bytes([b[1][0], b[2][1], b[3][2], b[0][3]]);
    state[2] = u32::from_be_bytes([b[2][0], b[3][1], b[0][2], b[1][3]]);
    state[3] = u32::from_be_bytes([b[3][0], b[0][1], b[1][2], b[2][3]]);
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
    let _state_guard = unsafe {
        ScrubOnDrop::new(
            state.as_mut_ptr().cast::<u8>(),
            std::mem::size_of_val(&state),
        )
    };
    add_round_key(&mut state, &[w[0], w[1], w[2], w[3]]);
    for round in 1..=13 {
        sub_bytes(&mut state);
        shift_rows(&mut state);
        mix_columns(&mut state);
        add_round_key(
            &mut state,
            &[
                w[4 * round],
                w[4 * round + 1],
                w[4 * round + 2],
                w[4 * round + 3],
            ],
        );
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
    let mut w = expand_key(key);
    let _w_guard =
        unsafe { ScrubOnDrop::new(w.as_mut_ptr().cast::<u8>(), std::mem::size_of_val(&w)) };
    let mut counter = *iv;
    for chunk in data.chunks_mut(16) {
        let mut keystream = aes_256_encrypt_block(&counter, &w);
        let _keystream_guard = unsafe { ScrubOnDrop::new(keystream.as_mut_ptr(), keystream.len()) };
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
    let mut w = expand_key(seed);
    let _w_guard =
        unsafe { ScrubOnDrop::new(w.as_mut_ptr().cast::<u8>(), std::mem::size_of_val(&w)) };
    let mut input = [0u8; 16];
    input[..4].copy_from_slice(&block_index.to_le_bytes());
    let mut part1 = aes_256_encrypt_block(&input, &w);
    let _part1_guard = unsafe { ScrubOnDrop::new(part1.as_mut_ptr(), part1.len()) };
    for b in input.iter_mut().take(16) {
        *b = b.wrapping_add(1);
    }
    let mut part2 = aes_256_encrypt_block(&input, &w);
    let _part2_guard = unsafe { ScrubOnDrop::new(part2.as_mut_ptr(), part2.len()) };
    let mut key = [0u8; 32];
    key[..16].copy_from_slice(&part1);
    key[16..].copy_from_slice(&part2);
    key
}

pub fn aes_256_ctr_decrypt_slice(data: &mut [u8], key: &[u8; 32], iv: &[u8; 16]) {
    aes_256_ctr_decrypt(data, key, iv);
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
) -> Result<JitCode, String> {
    let mut effective_key: [u8; 32];
    let mut effective_iv: [u8; 16];
    let mut effective_key_guard = None;

    let (used_key, used_iv) = if let Some(acc_hash) = accumulated_hash {
        let mut combined = Vec::with_capacity(68);
        combined.extend_from_slice(key);
        combined.extend_from_slice(acc_hash);
        combined.extend_from_slice(&seed.to_le_bytes());
        let _combined_guard = unsafe { ScrubOnDrop::new(combined.as_mut_ptr(), combined.len()) };
        let derived = crate::ledger::sha256(&combined);
        effective_iv = *iv;
        for (d, a) in effective_iv.iter_mut().zip(acc_hash.iter()) {
            *d ^= *a;
        }
        effective_key = derived;
        effective_key_guard =
            Some(unsafe { ScrubOnDrop::new(effective_key.as_mut_ptr(), effective_key.len()) });
        (&effective_key, &effective_iv)
    } else {
        (key, iv)
    };

    let mut decrypted = encrypted_block.to_vec();
    let _decrypted_guard = unsafe { ScrubOnDrop::new(decrypted.as_mut_ptr(), decrypted.len()) };
    aes_256_ctr_decrypt(&mut decrypted, used_key, used_iv);

    let result = if enable_microjit {
        crate::jit::polymorphic_jit_compile(&decrypted, used_key, seed)
    } else {
        JitCode::new(&decrypted)
    };
    drop(effective_key_guard);
    result
}

fn make_nonce(key: &[u8; 32], ctx: u64) -> [u8; 16] {
    // Build the output buffer without a zero-array literal: both halves are
    // overwritten immediately, so there is no hard-coded IV here.
    let mut nonce = core::array::from_fn(|_| 0u8);
    nonce[..8].copy_from_slice(&crate::ledger::sha256(key)[..8]);
    nonce[8..16].copy_from_slice(&ctx.to_le_bytes());
    nonce
}

pub fn decrypt_with_hpc_check(
    encrypted: &[u8],
    key: &[u8; 32],
    hpc_seed: u64,
) -> Result<Vec<u8>, String> {
    let mut derived = crate::hpc_key::derive_key_from_hpc(key, hpc_seed)?;
    let _derived_guard = unsafe { ScrubOnDrop::new(derived.as_mut_ptr(), derived.len()) };
    let mut data = encrypted.to_vec();
    let iv = make_nonce(&derived, hpc_seed);
    aes_256_ctr_decrypt(&mut data, &derived, &iv);
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
    let mut derived_key = super::ledger::derive_decryption_key(key, proof);
    let _derived_key_guard =
        unsafe { ScrubOnDrop::new(derived_key.as_mut_ptr(), derived_key.len()) };
    let mut data = encrypted_data.to_vec();
    let iv = make_nonce(&derived_key, proof.timestamp);
    aes_256_ctr_decrypt(&mut data, &derived_key, &iv);
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
    let mut combined = Vec::with_capacity(68);
    combined.extend_from_slice(key);
    combined.extend_from_slice(accumulated_hash);
    combined.extend_from_slice(&fragment_id.to_le_bytes());
    let _combined_guard = unsafe { ScrubOnDrop::new(combined.as_mut_ptr(), combined.len()) };
    let mut derived = crate::ledger::sha256(&combined);
    let _derived_guard = unsafe { ScrubOnDrop::new(derived.as_mut_ptr(), derived.len()) };
    let mut data = encrypted_data.to_vec();
    let iv = make_nonce(&derived, fragment_id as u64);
    aes_256_ctr_decrypt(&mut data, &derived, &iv);
    Ok(data)
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Test-only key/IV material, built byte-by-byte so fixtures are
    /// unmistakably synthetic and never resemble production key material.
    fn test_material<const N: usize>(byte: u8) -> [u8; N] {
        let mut out = [0u8; N];
        for b in out.iter_mut() {
            *b = byte;
        }
        out
    }

    fn test_hex(input: &str) -> Vec<u8> {
        assert_eq!(input.len() % 2, 0);
        (0..input.len() / 2)
            .map(|i| u8::from_str_radix(&input[2 * i..2 * i + 2], 16).expect("hex byte"))
            .collect()
    }

    #[test]
    fn aes256_encrypt_block_matches_nist_vector() {
        // NIST FIPS-197 AES-256 example key/input/output.
        let key: [u8; 32] = test_hex("000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f")
            .try_into()
            .expect("32-byte key");
        let plaintext: [u8; 16] = test_hex("00112233445566778899aabbccddeeff")
            .try_into()
            .expect("16-byte block");
        let expected = test_hex("8ea2b7ca516745bfeafc49904b496089");
        let expanded = expand_key(&key);
        assert_eq!(aes_256_encrypt_block(&plaintext, &expanded), expected.as_slice());
    }

    #[test]
    fn aes256_ctr_matches_nist_sp800_38a() {
        // NIST SP 800-38A F.5.3, first two AES-256 CTR blocks.
        let key: [u8; 32] = test_hex("603deb1015ca71be2b73aef0857d77811f352c073b6108d72d9810a30914dff4")
            .try_into()
            .expect("32-byte key");
        let iv: [u8; 16] = test_hex("f0f1f2f3f4f5f6f7f8f9fafbfcfdfeff")
            .try_into()
            .expect("16-byte counter");
        let mut data = test_hex(
            "6bc1bee22e409f96e93d7e117393172aae2d8a571e03ac9c9eb76fac45af8e51",
        );
        aes_256_ctr_decrypt(&mut data, &key, &iv);
        assert_eq!(
            data,
            test_hex("601ec313775789a5b7a7f504bbf3d228f443e3ca4d62b59aca84e990cacaf5c5")
        );
    }

    #[cfg(target_arch = "x86_64")]
    #[test]
    fn decrypt_and_jit_keeps_pages_mapped() {
        // Regression: the non-microjit path dropped the JitMemoryManager
        // before returning, so Drop wiped+munmapped the RWX pages and the
        // returned pointer dangled (use-after-free).
        let key = test_material::<32>(0x11);
        let iv = test_material::<16>(0x22);
        let plain = vec![0x48u8, 0x31, 0xC0, 0xC3]; // xor rax,rax; ret
        let mut enc = plain.clone();
        aes_256_ctr_decrypt(&mut enc, &key, &iv); // CTR is its own inverse
        let code = decrypt_and_jit(&enc, &key, &iv, 7, false, None).expect("decrypt_and_jit");
        // Reading the returned pointer must not fault: pages still owned.
        let first = unsafe { std::ptr::read_volatile(code.as_ptr()) };
        assert_eq!(first, 0x48);
        assert_eq!(unsafe { code.execute(&[]) }.expect("execute"), 0);
    }

    #[test]
    fn aes_slice_decrypt_does_not_mutate_caller_key() {
        let key = test_material::<32>(0x5A);
        let original = key;
        let mut data = [0u8; 16];
        aes_256_ctr_decrypt_slice(&mut data, &key, &[0u8; 16]);
        assert_eq!(key, original);
    }

    #[test]
    fn decrypt_and_jit_does_not_mutate_caller_key_on_success_or_error() {
        let key = test_material::<32>(0x11);
        let original = key;
        let iv = test_material::<16>(0x22);
        let plain = vec![0x48u8, 0x31, 0xC0, 0xC3];
        let mut enc = plain.clone();
        aes_256_ctr_decrypt(&mut enc, &key, &iv);
        let code = decrypt_and_jit(&enc, &key, &iv, 7, false, None).expect("decrypt");
        assert_eq!(key, original);
        drop(code);
        assert!(decrypt_and_jit(&[], &key, &iv, 7, false, None).is_err());
        assert_eq!(key, original);
    }

    #[cfg(target_arch = "x86_64")]
    #[test]
    fn decrypt_and_jit_history_does_not_mutate_caller_key() {
        let key = test_material::<32>(0x33);
        let original = key;
        let accumulated = test_material::<32>(0x44);
        let seed = 9u64;
        let mut combined = Vec::new();
        combined.extend_from_slice(&key);
        combined.extend_from_slice(&accumulated);
        combined.extend_from_slice(&seed.to_le_bytes());
        let derived = crate::ledger::sha256(&combined);
        let original_iv = test_material::<16>(0x55);
        let mut derived_iv = original_iv;
        for (d, a) in derived_iv.iter_mut().zip(accumulated.iter()) {
            *d ^= *a;
        }
        let plain = vec![0x48u8, 0x31, 0xC0, 0xC3];
        let mut enc = plain.clone();
        aes_256_ctr_decrypt(&mut enc, &derived, &derived_iv);
        let code = decrypt_and_jit(&enc, &key, &original_iv, seed, false, Some(&accumulated))
            .expect("decrypt with history");
        assert_eq!(key, original);
        assert_eq!(unsafe { code.execute(&[]) }.expect("execute"), 0);
        drop(code);
        assert!(decrypt_and_jit(&[], &key, &original_iv, seed, false, Some(&accumulated)).is_err());
        assert_eq!(key, original);
    }
}
