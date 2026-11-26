//! Launcher-scope attestation only (see docs/ATTESTATION.md): challenge
//! issuance for the launcher process liveness — NOT payload attestation.
//! Canonical payload-integrity attestation lives in
//! runtime/src/sw_attestation.rs; new attestation logic goes there.
use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};

/// Maximum outstanding challenges. Expired entries are pruned first; when the
/// cap is still reached issuance fails closed instead of growing memory.
pub const MAX_CHALLENGES: usize = 1024;
const CHALLENGE_TTL_SECS: u64 = 30;
const MAX_RESPONDER_ID_BYTES: usize = 256;

pub struct AttestationModule {
    pub enabled: bool,
    challenges: HashMap<u64, Challenge>,
    /// Process-wide master secret. Per-responder secrets are derived on demand
    /// with domain-separated HMAC-SHA256, so there is no unbounded secret map.
    master_secret: [u8; 32],
    nonce_counter: u64,
}

#[derive(Clone)]
pub struct Challenge {
    pub challenge_id: u64,
    pub data: Vec<u8>,
    pub created_at: u64,
    pub ttl_secs: u64,
    /// HMAC-SHA256(responder_secret, data), computed at issuance. The secret
    /// itself is never placed in `data` and never leaves this module.
    expected: [u8; 32],
}

impl AttestationModule {
    pub fn new() -> Result<Self, String> {
        Ok(AttestationModule {
            enabled: true,
            challenges: HashMap::new(),
            master_secret: load_master_secret()?,
            nonce_counter: 0,
        })
    }

    pub fn create_challenge(&mut self, responder_id: &str) -> Option<Challenge> {
        let now = SystemTime::now().duration_since(UNIX_EPOCH).ok()?.as_secs();
        self.create_challenge_at(responder_id, now)
    }

    fn create_challenge_at(&mut self, responder_id: &str, now: u64) -> Option<Challenge> {
        if responder_id.len() > MAX_RESPONDER_ID_BYTES {
            return None;
        }
        self.prune(now);
        if self.challenges.len() >= MAX_CHALLENGES {
            return None;
        }
        let cid = self.nonce_counter.checked_add(1)?;
        self.nonce_counter = cid;
        let mut key_material = b"nixon-attestation-responder-v1\0".to_vec();
        key_material.extend_from_slice(responder_id.as_bytes());
        let secret = hmac_sha256(&self.master_secret, &key_material);
        let mut data = Vec::with_capacity(16);
        data.extend_from_slice(&cid.to_le_bytes());
        data.extend_from_slice(&now.to_le_bytes());
        let expected = hmac_sha256(&secret, &data);
        let challenge = Challenge {
            challenge_id: cid,
            data,
            created_at: now,
            ttl_secs: CHALLENGE_TTL_SECS,
            expected,
        };
        self.challenges.insert(cid, challenge.clone());
        Some(challenge)
    }

    fn prune(&mut self, now: u64) {
        self.challenges
            .retain(|_, challenge| now <= challenge.created_at.saturating_add(challenge.ttl_secs));
    }

    pub fn verify_response(&mut self, challenge_id: u64, response: &[u8]) -> bool {
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|duration| duration.as_secs())
            .unwrap_or(0);
        self.verify_response_at(challenge_id, response, now)
    }

    fn verify_response_at(&mut self, challenge_id: u64, response: &[u8], now: u64) -> bool {
        if response.len() != 32 {
            return false;
        }
        let valid = {
            let challenge = match self.challenges.get(&challenge_id) {
                Some(challenge) => challenge,
                None => return false,
            };
            if now > challenge.created_at.saturating_add(challenge.ttl_secs) {
                return false;
            }
            let mut diff = 0u8;
            for (actual, expected) in response.iter().zip(challenge.expected.iter()) {
                diff |= actual ^ expected;
            }
            diff == 0
        };
        if valid {
            self.challenges.remove(&challenge_id);
        }
        valid
    }

    pub fn is_enabled(&self) -> bool {
        self.enabled
    }
}

/// Load 32 bytes from an explicit environment secret or OS entropy. Invalid
/// explicit configuration is an error; there is deliberately no weak RNG
/// fallback.
fn load_master_secret() -> Result<[u8; 32], String> {
    match std::env::var("NIXON_ATTEST_MASTER_SECRET") {
        Ok(value) => decode_hex_32(value.trim()).ok_or_else(|| {
            "NIXON_ATTEST_MASTER_SECRET must be 64 ASCII hex characters".to_string()
        }),
        Err(std::env::VarError::NotPresent) => os_entropy_32(),
        Err(std::env::VarError::NotUnicode(_)) => {
            Err("NIXON_ATTEST_MASTER_SECRET must be ASCII hex".to_string())
        }
    }
}

fn decode_hex_32(value: &str) -> Option<[u8; 32]> {
    let bytes = value.as_bytes();
    if bytes.len() != 64 || !bytes.iter().all(u8::is_ascii_hexdigit) {
        return None;
    }
    let mut out = [0u8; 32];
    for (index, pair) in bytes.chunks_exact(2).enumerate() {
        let high = hex_nibble(pair[0])?;
        let low = hex_nibble(pair[1])?;
        out[index] = (high << 4) | low;
    }
    Some(out)
}

fn hex_nibble(byte: u8) -> Option<u8> {
    match byte {
        b'0'..=b'9' => Some(byte - b'0'),
        b'a'..=b'f' => Some(byte - b'a' + 10),
        b'A'..=b'F' => Some(byte - b'A' + 10),
        _ => None,
    }
}

#[cfg(target_os = "linux")]
fn os_entropy_32() -> Result<[u8; 32], String> {
    let mut out = [0u8; 32];
    loop {
        let count = unsafe { libc::getrandom(out.as_mut_ptr().cast(), out.len(), 0) };
        if count == out.len() as libc::ssize_t {
            return Ok(out);
        }
        if count < 0 && std::io::Error::last_os_error().kind() == std::io::ErrorKind::Interrupted {
            continue;
        }
        break;
    }
    urandom_entropy_32()
}

#[cfg(all(unix, not(target_os = "linux")))]
fn os_entropy_32() -> Result<[u8; 32], String> {
    urandom_entropy_32()
}

#[cfg(not(unix))]
fn os_entropy_32() -> Result<[u8; 32], String> {
    Err("OS entropy unavailable: set NIXON_ATTEST_MASTER_SECRET".to_string())
}

#[cfg(unix)]
fn urandom_entropy_32() -> Result<[u8; 32], String> {
    use std::io::Read;
    let mut file = std::fs::File::open("/dev/urandom")
        .map_err(|error| format!("OS entropy unavailable: {error}"))?;
    let mut out = [0u8; 32];
    file.read_exact(&mut out)
        .map_err(|error| format!("OS entropy unavailable: {error}"))?;
    Ok(out)
}

/// HMAC-SHA256 (RFC 2104) over the local SHA-256. Keyed, so a peer that sees
/// the public challenge cannot compute the expected response.
fn hmac_sha256(key: &[u8], data: &[u8]) -> [u8; 32] {
    const BLOCK: usize = 64;
    let mut normalized = [0u8; BLOCK];
    if key.len() > BLOCK {
        normalized[..32].copy_from_slice(&sha256_simple(key));
    } else {
        normalized[..key.len()].copy_from_slice(key);
    }
    let mut inner = Vec::with_capacity(BLOCK + data.len());
    inner.extend(normalized.iter().map(|b| b ^ 0x36));
    inner.extend_from_slice(data);
    let inner_hash = sha256_simple(&inner);
    let mut outer = Vec::with_capacity(BLOCK + 32);
    outer.extend(normalized.iter().map(|b| b ^ 0x5c));
    outer.extend_from_slice(&inner_hash);
    sha256_simple(&outer)
}

/// Minimal correct SHA-256 (FIPS 180-4), pure Rust, stdlib only.
///
/// Replaces the previous DefaultHasher-based placeholder which was NOT
/// real SHA-256 (and was non-deterministic across processes due to
/// RandomState seeding). Same signature so callers are unaffected.
fn sha256_simple(data: &[u8]) -> [u8; 32] {
    const K: [u32; 64] = [
        0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4,
        0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe,
        0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f,
        0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
        0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc,
        0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
        0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116,
        0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
        0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7,
        0xc67178f2,
    ];
    let mut h: [u32; 8] = [
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab,
        0x5be0cd19,
    ];
    let bit_len = (data.len() as u64).wrapping_mul(8);
    let mut msg = Vec::with_capacity((data.len() + 9).div_ceil(64) * 64);
    msg.extend_from_slice(data);
    msg.push(0x80);
    while msg.len() % 64 != 56 {
        msg.push(0);
    }
    msg.extend_from_slice(&bit_len.to_be_bytes());
    for chunk in msg.chunks_exact(64) {
        let mut w = [0u32; 64];
        for i in 0..16 {
            w[i] = u32::from_be_bytes([
                chunk[4 * i],
                chunk[4 * i + 1],
                chunk[4 * i + 2],
                chunk[4 * i + 3],
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
            let t1 = hh
                .wrapping_add(s1)
                .wrapping_add(ch)
                .wrapping_add(K[i])
                .wrapping_add(w[i]);
            let s0 = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
            let maj = (a & b) ^ (a & c) ^ (b & c);
            let t2 = s0.wrapping_add(maj);
            hh = g;
            g = f;
            f = e;
            e = d.wrapping_add(t1);
            d = c;
            c = b;
            b = a;
            a = t1.wrapping_add(t2);
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
    let mut out = [0u8; 32];
    for (i, v) in h.iter().enumerate() {
        out[4 * i..4 * i + 4].copy_from_slice(&v.to_be_bytes());
    }
    out
}

#[cfg(test)]
mod tests {
    use super::sha256_simple;

    fn hex(b: &[u8]) -> String {
        b.iter().map(|x| format!("{x:02x}")).collect()
    }

    fn responder_key(master: &[u8; 32], responder: &[u8]) -> [u8; 32] {
        let mut material = b"nixon-attestation-responder-v1\0".to_vec();
        material.extend_from_slice(responder);
        super::hmac_sha256(master, &material)
    }

    #[test]
    fn empty_vector() {
        assert_eq!(
            hex(&sha256_simple(b"")),
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        );
    }

    #[test]
    fn abc_vector() {
        assert_eq!(
            hex(&sha256_simple(b"abc")),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        );
    }

    #[test]
    fn determinism_same_input() {
        assert_eq!(
            sha256_simple(b"challenge-data"),
            sha256_simple(b"challenge-data")
        );
    }

    #[test]
    fn output_len_32() {
        assert_eq!(sha256_simple(b"anything").len(), 32);
    }

    #[test]
    fn challenge_secret_not_derivable_from_public_data() {
        use super::{hmac_sha256, AttestationModule};
        let mut m = AttestationModule::new().expect("master secret");
        let ch = m.create_challenge("peer-1").expect("challenge");
        // Regression: the old code set secret = 32 bytes of (now+cid) as u8,
        // all of which is visible in ch.data. Recomputing the HMAC with that
        // public-derived "secret" must NOT reproduce the expected tag.
        let cid = u64::from_le_bytes(ch.data[0..8].try_into().unwrap());
        let now = u64::from_le_bytes(ch.data[8..16].try_into().unwrap());
        let mut forged_key = vec![0u8; 32];
        for b in forged_key.iter_mut() {
            *b = now.wrapping_add(cid) as u8;
        }
        // The forged key must differ from the real per-responder secret.
        let real = responder_key(&m.master_secret, b"peer-1");
        assert_ne!(forged_key, real.to_vec());
        // And the expected tag must not be reproducible from public data.
        assert_ne!(hmac_sha256(&forged_key, &ch.data), ch.expected);
    }

    #[test]
    fn response_is_single_use() {
        use super::{hmac_sha256, AttestationModule};
        let mut m = AttestationModule::new().expect("master secret");
        let ch = m.create_challenge("peer-2").expect("challenge");
        let resp = hmac_sha256(&responder_key(&m.master_secret, b"peer-2"), &ch.data);
        assert!(m.verify_response(ch.challenge_id, &resp));
        // Replay of the same captured response must fail.
        assert!(!m.verify_response(ch.challenge_id, &resp));
    }

    #[test]
    fn wrong_response_does_not_consume_the_challenge() {
        use super::AttestationModule;
        let mut m = AttestationModule::new().expect("master secret");
        let ch = m.create_challenge("peer-3").expect("challenge");
        assert!(!m.verify_response(ch.challenge_id, &[0u8; 32]));
        let resp = super::hmac_sha256(&responder_key(&m.master_secret, b"peer-3"), &ch.data);
        assert!(m.verify_response(ch.challenge_id, &resp));
    }

    #[test]
    fn response_length_must_be_exactly_32() {
        use super::AttestationModule;
        let mut m = AttestationModule::new().expect("master secret");
        let ch = m.create_challenge("peer-length").expect("challenge");
        let resp = super::hmac_sha256(&responder_key(&m.master_secret, b"peer-length"), &ch.data);
        assert!(!m.verify_response(ch.challenge_id, &resp[..31]));
        let mut long = resp.to_vec();
        long.push(0);
        assert!(!m.verify_response(ch.challenge_id, &long));
        assert!(m.verify_response(ch.challenge_id, &resp));
    }

    #[test]
    fn challenge_issuance_is_capped() {
        use super::{AttestationModule, MAX_CHALLENGES};
        let mut m = AttestationModule::new().expect("master secret");
        for _ in 0..MAX_CHALLENGES {
            assert!(m.create_challenge("peer").is_some());
        }
        assert!(m.create_challenge("peer").is_none());
    }

    #[test]
    fn expired_challenges_are_pruned_and_rejected() {
        use super::AttestationModule;
        let mut m = AttestationModule::new().expect("master secret");
        let challenge = m
            .create_challenge_at("peer-expiry", 100)
            .expect("challenge");
        let response = super::hmac_sha256(
            &responder_key(&m.master_secret, b"peer-expiry"),
            &challenge.data,
        );
        assert!(m.verify_response_at(challenge.challenge_id, &response, 130));
        let challenge = m
            .create_challenge_at("peer-expiry", 200)
            .expect("challenge");
        assert!(!m.verify_response_at(challenge.challenge_id, &response, 231));
        assert!(m.create_challenge_at("peer-expiry", 262).is_some());
    }

    #[test]
    fn nonce_counter_overflow_fails_closed() {
        use super::AttestationModule;
        let mut m = AttestationModule::new().expect("master secret");
        m.nonce_counter = u64::MAX;
        assert!(m.create_challenge("peer-overflow").is_none());
    }

    #[test]
    fn non_ascii_master_secret_is_rejected_without_panicking() {
        let value = "é".repeat(64);
        let result = std::panic::catch_unwind(|| super::decode_hex_32(&value));
        assert!(result.is_ok(), "hex decoding panicked");
        assert!(result.unwrap().is_none());
    }
}
