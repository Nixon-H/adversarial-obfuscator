use crate::memguard::scrub_memory;

const K: [u32; 64] = [
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

fn sha256(data: &[u8]) -> [u8; 32] {
    let mut h: [u32; 8] = [
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
        0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
    ];

    let ml = data.len() as u64 * 8;
    let mut padded = data.to_vec();
    padded.push(0x80);
    while (padded.len() * 8) % 512 != 448 {
        padded.push(0);
    }
    padded.extend_from_slice(&ml.to_be_bytes());

    for chunk in padded.chunks(64) {
        let mut w = [0u32; 64];
        for i in 0..16 {
            w[i] = u32::from_be_bytes([
                chunk[i * 4],
                chunk[i * 4 + 1],
                chunk[i * 4 + 2],
                chunk[i * 4 + 3],
            ]);
        }
        for i in 16..64 {
            let s0 = w[i - 15].rotate_right(7) ^ w[i - 15].rotate_right(18) ^ (w[i - 15] >> 3);
            let s1 = w[i - 2].rotate_right(17) ^ w[i - 2].rotate_right(19) ^ (w[i - 2] >> 10);
            w[i] = w[i - 16]
                .wrapping_add(s0)
                .wrapping_add(w[i - 7])
                .wrapping_add(s1);
        }

        let (mut a, mut b, mut c, mut d, mut e, mut f, mut g, mut hh) =
            (h[0], h[1], h[2], h[3], h[4], h[5], h[6], h[7]);

        for i in 0..64 {
            let s1 = e.rotate_right(6) ^ e.rotate_right(11) ^ e.rotate_right(25);
            let ch = (e & f) ^ ((!e) & g);
            let temp1 = hh.wrapping_add(s1).wrapping_add(ch).wrapping_add(K[i]).wrapping_add(w[i]);
            let s0 = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
            let maj = (a & b) ^ (a & c) ^ (b & c);
            let temp2 = s0.wrapping_add(maj);

            hh = g;
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
        h[7] = h[7].wrapping_add(hh);
    }

    let mut result = [0u8; 32];
    for i in 0..8 {
        result[i * 4..i * 4 + 4].copy_from_slice(&h[i].to_be_bytes());
    }
    result
}

pub struct CfgStateChain {
    pub current_token: [u8; 32],
    pub previous_token: [u8; 32],
    pub block_counter: u64,
}

impl CfgStateChain {
    pub fn new(initial_seed: [u8; 32]) -> Self {
        let previous_token = sha256(&initial_seed);
        let current_token = sha256(&previous_token);
        CfgStateChain {
            current_token,
            previous_token,
            block_counter: 0,
        }
    }

    pub fn advance(&mut self) -> [u8; 32] {
        let mut input = Vec::with_capacity(40);
        input.extend_from_slice(&self.current_token);
        input.extend_from_slice(&self.block_counter.to_le_bytes());
        let next_token = sha256(&input);
        self.previous_token = self.current_token;
        self.current_token = next_token;
        self.block_counter += 1;
        self.current_token
    }

    pub fn verify_transition(
        &self,
        claimed_prev_token: &[u8; 32],
        claimed_curr_token: &[u8; 32],
        claimed_counter: u64,
    ) -> bool {
        let mut input = Vec::with_capacity(40);
        input.extend_from_slice(claimed_prev_token);
        input.extend_from_slice(&claimed_counter.to_le_bytes());
        let computed = sha256(&input);
        computed == *claimed_curr_token
    }

    pub fn generate_block_key(&self, block_id: u64) -> [u8; 32] {
        let mut input = Vec::with_capacity(40);
        input.extend_from_slice(&self.current_token);
        input.extend_from_slice(&block_id.to_le_bytes());
        sha256(&input)
    }
}

pub fn check_block_authorization(
    block_id: u64,
    expected_token: &[u8; 32],
    encrypted_data: &[u8],
) -> Result<Vec<u8>, String> {
    if encrypted_data.len() < 4 {
        return Err("encrypted data too short".to_string());
    }
    let block_key = {
        let mut input = Vec::with_capacity(40);
        input.extend_from_slice(expected_token);
        input.extend_from_slice(&block_id.to_le_bytes());
        sha256(&input)
    };

    let decrypted: Vec<u8> = encrypted_data
        .iter()
        .enumerate()
        .map(|(i, &b)| b ^ block_key[i % 32])
        .collect();

    let magic = u32::from_le_bytes([decrypted[0], decrypted[1], decrypted[2], decrypted[3]]);
    if magic != 0xCFC0DE01 {
        scrub_memory(block_key.as_ptr() as *mut u8, block_key.len());
        return Err("decryption produced invalid data — token mismatch".to_string());
    }

    let payload_len = decrypted.len() - 4;
    let mut payload = Vec::with_capacity(payload_len);
    payload.extend_from_slice(&decrypted[4..]);

    let (payload_data, expected_digest) = payload.split_at(payload.len().saturating_sub(32));
    if payload_data.len() < 1 {
        scrub_memory(block_key.as_ptr() as *mut u8, block_key.len());
        return Err("no payload data".to_string());
    }
    let actual_payload = &payload_data[..payload_data.len()];
    let stored_digest = &expected_digest[..32];

    let digest = sha256(actual_payload);
    if &digest != stored_digest {
        scrub_memory(block_key.as_ptr() as *mut u8, block_key.len());
        return Err("decryption produced invalid data — digest mismatch".to_string());
    }

    scrub_memory(block_key.as_ptr() as *mut u8, block_key.len());
    Ok(actual_payload.to_vec())
}

pub fn encrypt_block_data(block_id: u64, token: &[u8; 32], plaintext: &[u8]) -> Vec<u8> {
    let block_key = {
        let mut input = Vec::with_capacity(40);
        input.extend_from_slice(token);
        input.extend_from_slice(&block_id.to_le_bytes());
        sha256(&input)
    };

    let digest = sha256(plaintext);
    let mut payload = Vec::with_capacity(4 + plaintext.len() + 32);
    payload.extend_from_slice(&0xCFC0DE01u32.to_le_bytes());
    payload.extend_from_slice(plaintext);
    payload.extend_from_slice(&digest);

    let result: Vec<u8> = payload
        .iter()
        .enumerate()
        .map(|(i, &b)| b ^ block_key[i % 32])
        .collect();
    scrub_memory(block_key.as_ptr() as *mut u8, block_key.len());
    result
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sha256_basic() {
        let input = b"hello";
        let result = sha256(input);
        let expected = [
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
        let expected = [
            0xe3, 0xb0, 0xc4, 0x42, 0x98, 0xfc, 0x1c, 0x14,
            0x9a, 0xfb, 0xf4, 0xc8, 0x99, 0x6f, 0xb9, 0x24,
            0x27, 0xae, 0x41, 0xe4, 0x64, 0x9b, 0x93, 0x4c,
            0xa4, 0x95, 0x99, 0x1b, 0x78, 0x52, 0xb8, 0x55,
        ];
        assert_eq!(result, expected);
    }

    #[test]
    fn test_state_chain_initializes_correctly() {
        let seed = [0x42u8; 32];
        let chain = CfgStateChain::new(seed);
        let expected_prev = sha256(&seed);
        let expected_curr = sha256(&expected_prev);
        assert_eq!(chain.previous_token, expected_prev);
        assert_eq!(chain.current_token, expected_curr);
        assert_eq!(chain.block_counter, 0);
    }

    #[test]
    fn test_advance_produces_deterministic_sequence() {
        let seed = [0xABu8; 32];
        let mut chain = CfgStateChain::new(seed);
        let first = chain.advance();
        let second = chain.advance();
        let third = chain.advance();

        let mut chain2 = CfgStateChain::new(seed);
        assert_eq!(chain2.advance(), first);
        assert_eq!(chain2.advance(), second);
        assert_eq!(chain2.advance(), third);
    }

    #[test]
    fn test_advance_changes_state() {
        let seed = [0xABu8; 32];
        let mut chain = CfgStateChain::new(seed);
        let before = chain.current_token;
        let _ = chain.advance();
        assert_ne!(chain.current_token, before);
    }

    #[test]
    fn test_verify_transition_valid() {
        let seed = [0x42u8; 32];
        let mut chain = CfgStateChain::new(seed);
        let prev = chain.current_token;
        let counter_before = chain.block_counter;
        let curr = chain.advance();

        assert!(chain.verify_transition(&prev, &curr, counter_before));
    }

    #[test]
    fn test_verify_transition_invalid_token() {
        let seed = [0x42u8; 32];
        let mut chain = CfgStateChain::new(seed);
        let prev = chain.current_token;
        let counter_before = chain.block_counter;
        let _curr = chain.advance();

        let wrong_token = [0xFFu8; 32];
        assert!(!chain.verify_transition(&prev, &wrong_token, counter_before));
    }

    #[test]
    fn test_verify_transition_invalid_counter() {
        let seed = [0x42u8; 32];
        let mut chain = CfgStateChain::new(seed);
        let prev = chain.current_token;
        let _counter_before = chain.block_counter;
        let curr = chain.advance();

        assert!(!chain.verify_transition(&prev, &curr, 999));
    }

    #[test]
    fn test_block_key_unique_per_block() {
        let seed = [0x42u8; 32];
        let chain = CfgStateChain::new(seed);
        let key1 = chain.generate_block_key(0);
        let key2 = chain.generate_block_key(1);
        assert_ne!(key1, key2);
    }

    #[test]
    fn test_block_key_deterministic() {
        let seed = [0x42u8; 32];
        let chain1 = CfgStateChain::new(seed);
        let chain2 = CfgStateChain::new(seed);
        assert_eq!(chain1.generate_block_key(5), chain2.generate_block_key(5));
    }

    #[test]
    fn test_check_block_authorization_valid() {
        let seed = [0x42u8; 32];
        let chain = CfgStateChain::new(seed);
        let block_id = 0;
        let token = chain.current_token;
        let plaintext = b"hello crypto world";

        let encrypted = encrypt_block_data(block_id, &token, plaintext);
        let result = check_block_authorization(block_id, &token, &encrypted);
        assert!(result.is_ok());
        assert_eq!(result.unwrap(), plaintext);
    }

    #[test]
    fn test_check_block_authorization_invalid_token() {
        let seed = [0x42u8; 32];
        let chain = CfgStateChain::new(seed);
        let block_id = 0;
        let real_token = chain.current_token;
        let wrong_token = [0xFFu8; 32];
        let plaintext = b"secret data";

        let encrypted = encrypt_block_data(block_id, &real_token, plaintext);
        let result = check_block_authorization(block_id, &wrong_token, &encrypted);
        assert!(result.is_err());
    }

    #[test]
    fn test_advance_updates_counter() {
        let seed = [0x00u8; 32];
        let mut chain = CfgStateChain::new(seed);
        assert_eq!(chain.block_counter, 0);
        let _ = chain.advance();
        assert_eq!(chain.block_counter, 1);
        let _ = chain.advance();
        assert_eq!(chain.block_counter, 2);
    }

    #[test]
    fn test_returned_token_matches_current() {
        let seed = [0xABu8; 32];
        let mut chain = CfgStateChain::new(seed);
        let returned = chain.advance();
        assert_eq!(returned, chain.current_token);
    }
}
