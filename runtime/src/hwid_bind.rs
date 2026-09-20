//! HWID-bound payload encryption in Rust.
//!
//! Mirrors `obfuscator/hwid_lock.py` exactly so both sides derive identical
//! keys and ciphertexts:
//! - Key: PBKDF2-HMAC-SHA256(password = hwid UTF-8 bytes, 100 000 iterations,
//!   dklen = 32) — same as `hashlib.pbkdf2_hmac("sha256", ...)`.
//! - Stream: `SHA-256(key || nonce || counter_be64)` keystream XOR, with the
//!   payload prefixed by its `SHA-256` tag (authenticated: wrong HWID or
//!   tampered bytes fail tag verification).
//!
//! No new dependencies: minimal SHA-256 (~60 lines) + HMAC + PBKDF2 below.

const K: [u32; 64] = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
];

/// PBKDF2 iteration count matching `hwid_lock.py::_ITERATIONS_DEFAULT`.
pub const HWID_ITERATIONS: u32 = 100_000;
/// Salt / nonce lengths matching `hwid_lock.py`.
pub const HWID_SALT_LEN: usize = 16;
pub const HWID_NONCE_LEN: usize = 16;
/// SHA-256 tag length.
pub const HWID_TAG_LEN: usize = 32;

fn sha256_compress(state: &mut [u32; 8], block: &[u8; 64]) {
    let mut w = [0u32; 64];
    for i in 0..16 {
        w[i] = u32::from_be_bytes([block[4 * i], block[4 * i + 1], block[4 * i + 2], block[4 * i + 3]]);
    }
    for i in 16..64 {
        let s0 = w[i - 15].rotate_right(7) ^ w[i - 15].rotate_right(18) ^ (w[i - 15] >> 3);
        let s1 = w[i - 2].rotate_right(17) ^ w[i - 2].rotate_right(19) ^ (w[i - 2] >> 10);
        w[i] = w[i - 16].wrapping_add(s0).wrapping_add(w[i - 7]).wrapping_add(s1);
    }
    let (mut a, mut b, mut c, mut d, mut e, mut f, mut g, mut h) =
        (state[0], state[1], state[2], state[3], state[4], state[5], state[6], state[7]);
    for i in 0..64 {
        let s1 = e.rotate_right(6) ^ e.rotate_right(11) ^ e.rotate_right(25);
        let ch = (e & f) ^ ((!e) & g);
        let t1 = h.wrapping_add(s1).wrapping_add(ch).wrapping_add(K[i]).wrapping_add(w[i]);
        let s0 = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
        let maj = (a & b) ^ (a & c) ^ (b & c);
        let t2 = s0.wrapping_add(maj);
        h = g; g = f; f = e;
        e = d.wrapping_add(t1); d = c; c = b; b = a;
        a = t1.wrapping_add(t2);
    }
    state[0] = state[0].wrapping_add(a);
    state[1] = state[1].wrapping_add(b);
    state[2] = state[2].wrapping_add(c);
    state[3] = state[3].wrapping_add(d);
    state[4] = state[4].wrapping_add(e);
    state[5] = state[5].wrapping_add(f);
    state[6] = state[6].wrapping_add(g);
    state[7] = state[7].wrapping_add(h);
}

fn sha256(data: &[u8]) -> [u8; 32] {
    let bit_len = data.len() as u64 * 8;
    let mut padded = data.to_vec();
    padded.push(0x80);
    while (padded.len() * 8) % 512 != 448 {
        padded.push(0);
    }
    padded.extend_from_slice(&bit_len.to_be_bytes());
    let mut state: [u32; 8] = [
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
        0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
    ];
    for chunk in padded.chunks_exact(64) {
        sha256_compress(&mut state, chunk.try_into().unwrap());
    }
    let mut out = [0u8; 32];
    for i in 0..8 {
        out[4 * i..4 * i + 4].copy_from_slice(&state[i].to_be_bytes());
    }
    out
}

fn hmac_sha256(key: &[u8], msg: &[u8]) -> [u8; 32] {
    // Block-size the key exactly like hashlib does.
    let mut kb = [0u8; 64];
    if key.len() > 64 {
        kb[..32].copy_from_slice(&sha256(key));
    } else {
        kb[..key.len()].copy_from_slice(key);
    }
    let mut ipad = [0x36u8; 64];
    let mut opad = [0x5cu8; 64];
    for i in 0..64 {
        ipad[i] ^= kb[i];
        opad[i] ^= kb[i];
    }
    let mut inner = Vec::with_capacity(64 + msg.len());
    inner.extend_from_slice(&ipad);
    inner.extend_from_slice(msg);
    let inner_hash = sha256(&inner);
    let mut outer = Vec::with_capacity(96);
    outer.extend_from_slice(&opad);
    outer.extend_from_slice(&inner_hash);
    sha256(&outer)
}

/// PBKDF2-HMAC-SHA256, dklen = 32. Byte-identical to
/// `hashlib.pbkdf2_hmac("sha256", password, salt, iterations, dklen=32)`.
pub fn pbkdf2_hmac_sha256(password: &[u8], salt: &[u8], iterations: u32) -> [u8; 32] {
    assert!(iterations >= 1, "iterations must be >= 1");
    // dklen (32) <= hash len (32): exactly one block.
    let mut block = Vec::with_capacity(salt.len() + 4);
    block.extend_from_slice(salt);
    block.extend_from_slice(&1u32.to_be_bytes());
    let mut u = hmac_sha256(password, &block);
    let mut out = u;
    for _ in 1..iterations {
        u = hmac_sha256(password, &u);
        for i in 0..32 {
            out[i] ^= u[i];
        }
    }
    out
}

/// Derive the 32-byte HWID key with the production iteration count,
/// matching `hwid_lock.derive_hwid_key(hwid, salt)`.
pub fn derive_hwid_key(hwid: &[u8], salt: &[u8]) -> [u8; 32] {
    pbkdf2_hmac_sha256(hwid, salt, HWID_ITERATIONS)
}

/// `SHA-256(key || nonce || counter_be64)` keystream XOR.
/// Mirrors `hwid_lock._keystream`.
pub fn hwid_stream_xor(key: &[u8; 32], nonce: &[u8], data: &[u8]) -> Vec<u8> {
    let mut out = Vec::with_capacity(data.len());
    let mut counter: u64 = 0;
    while out.len() < data.len() {
        let mut block = Vec::with_capacity(32 + nonce.len() + 8);
        block.extend_from_slice(key);
        block.extend_from_slice(nonce);
        block.extend_from_slice(&counter.to_be_bytes());
        let digest = sha256(&block);
        let take = (data.len() - out.len()).min(32);
        for i in 0..take {
            out.push(data[out.len()] ^ digest[i]);
        }
        counter += 1;
    }
    out
}

/// Encrypt: prepend `SHA-256(payload)` tag, then XOR with the keystream.
/// Matches `hwid_lock.lock_payload` ciphertext bytes for the same
/// `(payload, hwid, salt, nonce)`.
pub fn lock_payload(payload: &[u8], hwid: &[u8], salt: &[u8], nonce: &[u8]) -> Vec<u8> {
    let key = derive_hwid_key(hwid, salt);
    let mut tagged = Vec::with_capacity(32 + payload.len());
    tagged.extend_from_slice(&sha256(payload));
    tagged.extend_from_slice(payload);
    hwid_stream_xor(&key, nonce, &tagged)
}

/// Decrypt + verify tag. `Err` on wrong HWID, tampered bytes, or truncation.
pub fn unlock_payload(
    blob: &[u8],
    hwid: &[u8],
    salt: &[u8],
    nonce: &[u8],
) -> Result<Vec<u8>, String> {
    if blob.len() < HWID_TAG_LEN {
        return Err("decryption failed (truncated)".to_string());
    }
    let key = derive_hwid_key(hwid, salt);
    let tagged = hwid_stream_xor(&key, nonce, blob);
    let (tag, data) = tagged.split_at(HWID_TAG_LEN);
    if sha256(data) != tag {
        return Err("decryption failed: wrong hwid or tampered data".to_string());
    }
    Ok(data.to_vec())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn hex_to_32(s: &str) -> [u8; 32] {
        let v: Vec<u8> = (0..s.len())
            .step_by(2)
            .map(|i| u8::from_str_radix(&s[i..i + 2], 16).unwrap())
            .collect();
        v.try_into().unwrap()
    }

    fn hex_to_vec(s: &str) -> Vec<u8> {
        (0..s.len())
            .step_by(2)
            .map(|i| u8::from_str_radix(&s[i..i + 2], 16).unwrap())
            .collect()
    }

    #[test]
    fn test_pbkdf2_c1_vector() {
        // hashlib.pbkdf2_hmac('sha256', b'password', b'salt', 1, dklen=32)
        let got = pbkdf2_hmac_sha256(b"password", b"salt", 1);
        assert_eq!(
            got,
            hex_to_32("120fb6cffcf8b32c43e7225256c4f837a86548c92ccc35480805987cb70be17b")
        );
    }

    #[test]
    fn test_pbkdf2_c2_vector() {
        // hashlib.pbkdf2_hmac('sha256', b'password', b'salt', 2, dklen=32)
        let got = pbkdf2_hmac_sha256(b"password", b"salt", 2);
        assert_eq!(
            got,
            hex_to_32("ae4d0c95af6b46d32d0adff928f06dd02a303f8ef3c251dfd6e2d85a95474c43")
        );
    }

    #[test]
    fn test_pbkdf2_c4096_long_vector() {
        // passwordPASSWORDpassword / saltSALTsaltSALTsaltSALTsaltSALTsalt, c=4096
        let got = pbkdf2_hmac_sha256(
            b"passwordPASSWORDpassword",
            b"saltSALTsaltSALTsaltSALTsaltSALTsalt",
            4096,
        );
        assert_eq!(
            got,
            hex_to_32("348c89dbcbd32b2f32d814b8116e84cf2b17347ebc1800181c4e2a1fb8dd53e1")
        );
    }

    #[test]
    fn test_hwid_keystream_roundtrip() {
        let key = [0x11u8; 32];
        let nonce = [0x22u8; 16];
        let data = b"some payload bytes for stream test";
        let enc = hwid_stream_xor(&key, &nonce, data);
        assert_ne!(enc, data.to_vec());
        let dec = hwid_stream_xor(&key, &nonce, &enc);
        assert_eq!(dec, data.to_vec());
    }

    #[test]
    fn test_lock_unlock_roundtrip() {
        let payload = b"hello hwid-bound world";
        let salt = [0xAAu8; 16];
        let nonce = [0xBBu8; 16];
        let blob = lock_payload(payload, b"my-machine", &salt, &nonce);
        assert_eq!(blob.len(), payload.len() + HWID_TAG_LEN);
        let back = unlock_payload(&blob, b"my-machine", &salt, &nonce).unwrap();
        assert_eq!(back, payload.to_vec());
    }

    #[test]
    fn test_wrong_hwid_fails() {
        let salt = [0x01u8; 16];
        let nonce = [0x02u8; 16];
        let blob = lock_payload(b"secret", b"machine-A", &salt, &nonce);
        let err = unlock_payload(&blob, b"machine-B", &salt, &nonce).unwrap_err();
        assert!(err.contains("wrong hwid"), "unexpected: {err}");
    }

    #[test]
    fn test_tamper_fails() {
        let salt = [0x01u8; 16];
        let nonce = [0x02u8; 16];
        let mut blob = lock_payload(b"secret data", b"hwid", &salt, &nonce);
        blob[40] ^= 0xFF;
        assert!(unlock_payload(&blob, b"hwid", &salt, &nonce).is_err());
        // Truncation also fails.
        assert!(unlock_payload(&blob[..10], b"hwid", &salt, &nonce).is_err());
    }

    #[test]
    fn test_cross_compat_with_python_hwid_lock() {
        // Generated NOW with:
        //   hashlib.pbkdf2_hmac('sha256', b'TEST-HWID-1234',
        //       bytes.fromhex('001122...eeff'), 100000, dklen=32)
        // plus hwid_lock._keystream/lock_payload over b'hello hwid-bound world'.
        let hwid = b"TEST-HWID-1234";
        let salt = hex_to_vec("00112233445566778899aabbccddeeff");
        let nonce = hex_to_vec("0102030405060708090a0b0c0d0e0f10");
        let key = derive_hwid_key(hwid, &salt);
        assert_eq!(
            key,
            hex_to_32("b44dad5818182fa5c3341e4513bc452e28379baabf84fded6fe42d4f92af21b1")
        );
        let blob = lock_payload(b"hello hwid-bound world", hwid, &salt, &nonce);
        assert_eq!(
            blob,
            hex_to_vec("875f5104f9e5db3edc5e766e761324e8ca03091c6965df41637ca854b16c82c2023be14ac2aa009d4e85a1a638c11f746d1826cd70b7")
        );
        let back = unlock_payload(&blob, hwid, &salt, &nonce).unwrap();
        assert_eq!(back, b"hello hwid-bound world".to_vec());
    }
}
