//! Runtime event ledger (in-artifact append-only log).
//! TWIN: scripts/ledger_proof.py (offline integrity proofs over built
//! artifacts) — that script proves artifacts; this module records runtime
//! events inside the protected binary. Do not merge.
use std::fs;

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

fn sha256_pad(data: &[u8]) -> Vec<u8> {
    let bit_len = data.len() as u64 * 8;
    let mut padded = data.to_vec();
    padded.push(0x80);
    while (padded.len() * 8) % 512 != 448 {
        padded.push(0);
    }
    padded.extend_from_slice(&bit_len.to_be_bytes());
    padded
}

fn sha256_compress(state: &mut [u32; 8], block: &[u8; 64]) {
    let mut w = [0u32; 64];
    for i in 0..16 {
        w[i] = u32::from_be_bytes([
            block[4 * i], block[4 * i + 1], block[4 * i + 2], block[4 * i + 3],
        ]);
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
        let temp1 = h.wrapping_add(s1).wrapping_add(ch).wrapping_add(K[i]).wrapping_add(w[i]);
        let s0 = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
        let maj = (a & b) ^ (a & c) ^ (b & c);
        let temp2 = s0.wrapping_add(maj);
        h = g; g = f; f = e;
        e = d.wrapping_add(temp1); d = c; c = b; b = a;
        a = temp1.wrapping_add(temp2);
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

pub(crate) fn sha256(data: &[u8]) -> [u8; 32] {
    let padded = sha256_pad(data);
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

fn merkle_root(data: &[u8], block_size: usize) -> [u8; 32] {
    if data.is_empty() {
        return sha256(b"");
    }
    let mut hashes: Vec<[u8; 32]> = data.chunks(block_size).map(|b| sha256(b)).collect();
    while hashes.len() > 1 {
        let mut next = Vec::with_capacity((hashes.len() + 1) / 2);
        for i in (0..hashes.len()).step_by(2) {
            let mut combined = Vec::with_capacity(64);
            combined.extend_from_slice(&hashes[i]);
            combined.extend_from_slice(if i + 1 < hashes.len() { &hashes[i + 1] } else { &hashes[i] });
            next.push(sha256(&combined));
        }
        hashes = next;
    }
    hashes[0]
}

fn constant_time_eq(a: &[u8; 32], b: &[u8; 32]) -> bool {
    let mut diff = 0u8;
    for i in 0..32 {
        diff |= a[i] ^ b[i];
    }
    diff == 0
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IntegrityProof {
    pub text_hash: [u8; 32],
    pub merkle_root: [u8; 32],
    pub memory_layout_hash: [u8; 32],
    pub timestamp: u64,
    pub nonce: [u8; 16],
}

pub fn compute_text_proof(text_section: &[u8]) -> IntegrityProof {
    IntegrityProof {
        text_hash: sha256(text_section),
        merkle_root: merkle_root(text_section, 64),
        memory_layout_hash: [0u8; 32],
        timestamp: 0,
        nonce: [0u8; 16],
    }
}

pub fn verify_merkle_proof(text_section: &[u8], expected_root: &[u8; 32]) -> bool {
    let actual_root = merkle_root(text_section, 64);
    constant_time_eq(&actual_root, expected_root)
}

pub fn verify_memory_layout(proof: &IntegrityProof) -> bool {
    let maps = match fs::read_to_string("/proc/self/maps") {
        Ok(m) => m,
        Err(_) => return false,
    };
    let mut layout_data = Vec::new();
    for line in maps.lines() {
        let cols: Vec<&str> = line.splitn(5, ' ').collect();
        if cols.len() < 5 {
            continue;
        }
        let perms = cols[1];
        if !perms.contains('x') {
            continue;
        }
        let path = cols[4].trim();
        if path.is_empty() || path.starts_with('[') {
            continue;
        }
        let addrs: Vec<&str> = cols[0].split('-').collect();
        if addrs.len() != 2 {
            continue;
        }
        let start = match usize::from_str_radix(addrs[0], 16) {
            Ok(s) => s,
            Err(_) => continue,
        };
        let end = match usize::from_str_radix(addrs[1], 16) {
            Ok(e) => e,
            Err(_) => continue,
        };
        let flags: u32 = (if perms.contains('r') { 4 } else { 0 })
            | (if perms.contains('w') { 2 } else { 0 })
            | (if perms.contains('x') { 1 } else { 0 });
        layout_data.extend_from_slice(&(start as u64).to_ne_bytes());
        layout_data.extend_from_slice(&((end - start) as u64).to_ne_bytes());
        layout_data.extend_from_slice(&flags.to_ne_bytes());
    }
    let actual_hash = sha256(&layout_data);
    constant_time_eq(&actual_hash, &proof.memory_layout_hash)
}

pub fn full_integrity_check(text_section: &[u8], proof: &IntegrityProof) -> bool {
    if !verify_merkle_proof(text_section, &proof.merkle_root) {
        return false;
    }
    if !verify_memory_layout(proof) {
        return false;
    }
    let text_hash = sha256(text_section);
    constant_time_eq(&text_hash, &proof.text_hash)
}

pub fn load_text_section() -> Option<Vec<u8>> {
    let maps = fs::read_to_string("/proc/self/maps").ok()?;
    for line in maps.lines() {
        let cols: Vec<&str> = line.splitn(5, ' ').collect();
        if cols.len() < 5 || cols[1] != "r-xp" {
            continue;
        }
        let path = cols[4].trim();
        if path.is_empty() || path.starts_with('[') {
            continue;
        }
        let addrs: Vec<&str> = cols[0].split('-').collect();
        if addrs.len() != 2 {
            continue;
        }
        let start = usize::from_str_radix(addrs[0], 16).ok()?;
        let end = usize::from_str_radix(addrs[1], 16).ok()?;
        let slice = unsafe { std::slice::from_raw_parts(start as *const u8, end - start) };
        return Some(slice.to_vec());
    }
    None
}

pub fn derive_decryption_key(key: &[u8; 32], proof: &IntegrityProof) -> [u8; 32] {
    let mut binding = Vec::with_capacity(64);
    binding.extend_from_slice(key);
    binding.extend_from_slice(&proof.text_hash);
    sha256(&binding)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sha256_known_value() {
        let input = b"hello";
        let result = sha256(input);
        let expected: [u8; 32] = [
            0x2c, 0xf2, 0x4d, 0xba, 0x5f, 0xb0, 0xa3, 0x0e,
            0x26, 0xe8, 0x3b, 0x2a, 0xc5, 0xb9, 0xe2, 0x9e,
            0x1b, 0x16, 0x1e, 0x5c, 0x1f, 0xa7, 0x42, 0x5e,
            0x73, 0x04, 0x33, 0x62, 0x93, 0x8b, 0x98, 0x24,
        ];
        assert_eq!(result, expected);
    }

    #[test]
    fn test_sha256_empty() {
        let result = sha256(b"");
        let expected: [u8; 32] = [
            0xe3, 0xb0, 0xc4, 0x42, 0x98, 0xfc, 0x1c, 0x14,
            0x9a, 0xfb, 0xf4, 0xc8, 0x99, 0x6f, 0xb9, 0x24,
            0x27, 0xae, 0x41, 0xe4, 0x64, 0x9b, 0x93, 0x4c,
            0xa4, 0x95, 0x99, 0x1b, 0x78, 0x52, 0xb8, 0x55,
        ];
        assert_eq!(result, expected);
    }

    #[test]
    fn test_merkle_root_single_block() {
        let data = [0x42u8; 64];
        let root = merkle_root(&data, 64);
        let expected = sha256(&data);
        assert_eq!(root, expected);
    }

    #[test]
    fn test_merkle_root_two_blocks() {
        let data = [0xABu8; 128];
        let root = merkle_root(&data, 64);
        let block0 = sha256(&[0xABu8; 64]);
        let block1 = sha256(&[0xABu8; 64]);
        let mut combined = Vec::with_capacity(64);
        combined.extend_from_slice(&block0);
        combined.extend_from_slice(&block1);
        let expected = sha256(&combined);
        assert_eq!(root, expected);
    }

    #[test]
    fn test_verify_merkle_proof_valid() {
        let data = b"hello world, this is a test of the merkle tree verification system";
        let root = merkle_root(data, 64);
        assert!(verify_merkle_proof(data, &root));
    }

    #[test]
    fn test_verify_merkle_proof_tampered() {
        let data = b"hello world, this is a test of the merkle tree verification system";
        let root = merkle_root(data, 64);
        let mut tampered = data.to_vec();
        tampered[0] ^= 0xFF;
        assert!(!verify_merkle_proof(&tampered, &root));
    }

    #[test]
    fn test_full_integrity_check_components() {
        let data = b"test text section content for integrity check";
        let proof = compute_text_proof(data);
        assert!(verify_merkle_proof(data, &proof.merkle_root));
        assert!(constant_time_eq(&sha256(data), &proof.text_hash));
    }

    #[test]
    fn test_derive_decryption_key_deterministic() {
        let key = [0xAB; 32];
        let proof = IntegrityProof {
            text_hash: [0x01; 32],
            merkle_root: [0x02; 32],
            memory_layout_hash: [0x03; 32],
            timestamp: 100,
            nonce: [0x04; 16],
        };
        let k1 = derive_decryption_key(&key, &proof);
        let k2 = derive_decryption_key(&key, &proof);
        assert_eq!(k1, k2);
    }

    #[test]
    fn test_derive_decryption_key_different_text_hash() {
        let key = [0xAB; 32];
        let proof_a = IntegrityProof {
            text_hash: [0x01; 32],
            merkle_root: [0x02; 32],
            memory_layout_hash: [0x03; 32],
            timestamp: 100,
            nonce: [0x04; 16],
        };
        let proof_b = IntegrityProof {
            text_hash: [0xFF; 32],
            merkle_root: [0x02; 32],
            memory_layout_hash: [0x03; 32],
            timestamp: 100,
            nonce: [0x04; 16],
        };
        assert_ne!(derive_decryption_key(&key, &proof_a), derive_decryption_key(&key, &proof_b));
    }
}
