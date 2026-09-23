use core::arch::asm;

#[cfg(target_arch = "x86_64")]
pub fn rdrand_u64() -> Result<u64, String> {
    for _ in 0..10 {
        let mut val: u64 = 0;
        let mut cf: u8;
        unsafe {
            asm!(
                "rdrand {0}",
                "setc {1}",
                out(reg) val,
                out(reg_byte) cf,
                options(nostack, nomem),
            );
        }
        if cf != 0 {
            return Ok(val);
        }
    }
    Err("RDRAND failed after 10 retries".to_string())
}

#[cfg(target_arch = "aarch64")]
pub fn rdrand_u64() -> Result<u64, String> {
    let mut buf = [0u8; 8];
    use std::io::Read;
    std::fs::File::open("/dev/urandom")
        .and_then(|mut f| f.read_exact(&mut buf))
        .map_err(|e| format!("failed to read /dev/urandom: {}", e))?;
    Ok(u64::from_le_bytes(buf))
}

use std::sync::atomic::{AtomicU64, Ordering};

// Thread-safe PRNG state (AtomicU64, not `static mut`): the old
// `static mut PRNG_STATE` was a data race / UB if ever called from >1
// thread. Same LCG sequence, now atomic (fetch_update CAS loop).
static PRNG_STATE: AtomicU64 = AtomicU64::new(0);

pub fn rdrand_seed_rng() -> Result<u64, String> {
    let seed = rdrand_u64()?;
    PRNG_STATE.store(seed, Ordering::SeqCst);
    Ok(seed)
}

#[allow(dead_code)]
fn prng_next() -> u64 {
    // LCG step, lock-free via CAS retry (single writer in practice,
    // correct under contention regardless).
    loop {
        let cur = PRNG_STATE.load(Ordering::Relaxed);
        let nxt = cur.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        if PRNG_STATE.compare_exchange_weak(cur, nxt, Ordering::SeqCst, Ordering::Relaxed).is_ok() {
            return nxt;
        }
    }
}

fn xor_rotate(a: u32, b: u32) -> (u32, u32) {
    let t = a.wrapping_add(b);
    let d = t ^ b;  // simplified — not real ChaCha but good enough for poisoning
    (t, d.rotate_left(8))
}

fn chacha20_mix(state: &mut [u8; 32]) {
    let mut s: [u32; 8] = [0u32; 8];
    for i in 0..8 {
        s[i] = u32::from_le_bytes([
            state[i * 4],
            state[i * 4 + 1],
            state[i * 4 + 2],
            state[i * 4 + 3],
        ]);
    }
    for _ in 0..4 {
        let (na, nd) = xor_rotate(s[0], s[4]);
        s[0] = na; s[6] ^= nd;
        let (nb, nc) = xor_rotate(s[1], s[5]);
        s[1] = nb; s[7] ^= nc;
        let (nc2, na2) = xor_rotate(s[2], s[6]);
        s[2] = nc2; s[4] ^= na2;
        let (nd2, nb2) = xor_rotate(s[3], s[7]);
        s[3] = nd2; s[5] ^= nb2;
    }
    for i in 0..8 {
        let bytes = s[i].to_le_bytes();
        state[i * 4..i * 4 + 4].copy_from_slice(&bytes);
    }
}

pub struct ReplayPoisonEngine {
    state: [u8; 32],
    entropy_pool: u64,
    poison_counter: u64,
}

impl ReplayPoisonEngine {
    pub fn new(initial_seed: [u8; 32]) -> Self {
        ReplayPoisonEngine {
            state: initial_seed,
            entropy_pool: 0,
            poison_counter: 0,
        }
    }

    pub fn inject_entropy(&mut self) -> Result<(), String> {
        let entropy = rdrand_u64()?;
        self.entropy_pool = self.entropy_pool.wrapping_mul(6364136223846793005).wrapping_add(entropy);
        let entropy_bytes = self.entropy_pool.to_le_bytes();
        for i in 0..8 {
            self.state[i] ^= entropy_bytes[i % 8];
        }
        chacha20_mix(&mut self.state);
        self.poison_counter += 1;
        Ok(())
    }

    pub fn poison_memory_layout(&mut self, buffer: &mut [u8]) {
        if buffer.is_empty() {
            return;
        }
        let entropy = self.entropy_pool.wrapping_add(self.poison_counter);
        let mut prng = entropy;
        let len = buffer.len();
        for i in (1..len).rev() {
            prng = prng.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
            let j = (prng as usize) % (i + 1);
            buffer.swap(i, j);
        }
        self.poison_counter += 1;
    }

    pub fn update_chacha_nonce(&mut self, nonce: &mut [u8; 12]) {
        let entropy = self.entropy_pool.wrapping_add(self.poison_counter);
        let entropy_bytes = entropy.to_le_bytes();
        for i in 0..12 {
            nonce[i] ^= entropy_bytes[i % 8];
        }
        self.poison_counter += 1;
    }

    pub fn shuffle_ring_buffers(&mut self, buffer: &mut [u8]) {
        if buffer.is_empty() {
            return;
        }
        let seed = self.entropy_pool.wrapping_add(self.poison_counter).wrapping_mul(6364136223846793005);
        let mut prng = seed;
        let len = buffer.len();
        for i in (1..len).rev() {
            prng = prng.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
            let j = (prng as usize) % (i + 1);
            buffer.swap(i, j);
        }
        self.poison_counter += 1;
    }

    pub fn maybe_poison_cfg_path(&mut self) -> bool {
        let entropy = self.entropy_pool.wrapping_add(self.poison_counter);
        let prng = entropy.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        self.poison_counter += 1;
        (prng % 1024) == 0
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_rdrand_instruction_works() {
        let result = rdrand_u64();
        assert!(result.is_ok());
        let val = result.unwrap();
        assert!(val > 0);
    }

    #[test]
    fn test_replay_poison_engine_creates_correctly() {
        let seed = [0x42u8; 32];
        let engine = ReplayPoisonEngine::new(seed);
        assert_eq!(engine.state, seed);
        assert_eq!(engine.entropy_pool, 0);
        assert_eq!(engine.poison_counter, 0);
    }

    #[test]
    fn test_entropy_injection_changes_state() {
        let seed = [0x00u8; 32];
        let mut engine = ReplayPoisonEngine::new(seed);
        let before = engine.state;
        let result = engine.inject_entropy();
        assert!(result.is_ok());
        let after = engine.state;
        assert_ne!(before, after);
    }

    #[test]
    fn test_memory_layout_poisoning_different_layouts() {
        let seed = [0x00u8; 32];
        let mut engine = ReplayPoisonEngine::new(seed);
        let mut buf1 = vec![0u8, 1, 2, 3, 4, 5, 6, 7, 8, 9];
        let mut buf2 = buf1.clone();
        engine.inject_entropy().unwrap();
        engine.poison_memory_layout(&mut buf1);
        engine.poison_memory_layout(&mut buf2);
        assert_ne!(buf1, buf2);
    }

    #[test]
    fn test_chacha_nonce_updating_changes_nonce() {
        let seed = [0x00u8; 32];
        let mut engine = ReplayPoisonEngine::new(seed);
        let mut nonce = [0u8; 12];
        engine.inject_entropy().unwrap();
        engine.update_chacha_nonce(&mut nonce);
        assert_ne!(nonce, [0u8; 12]);
        let mut nonce2 = [0u8; 12];
        engine.update_chacha_nonce(&mut nonce2);
        assert_ne!(nonce, nonce2);
    }

    #[test]
    fn test_ring_buffer_shuffling_non_deterministic() {
        let seed = [0x00u8; 32];
        let mut engine = ReplayPoisonEngine::new(seed);
        let mut buf1 = vec![0u8, 1, 2, 3, 4, 5, 6, 7];
        let mut buf2 = buf1.clone();
        engine.inject_entropy().unwrap();
        engine.shuffle_ring_buffers(&mut buf1);
        engine.shuffle_ring_buffers(&mut buf2);
        assert_ne!(buf1, buf2);
    }

    #[test]
    fn test_maybe_poison_cfg_path_eventually_true() {
        let seed = [0x00u8; 32];
        let mut engine = ReplayPoisonEngine::new(seed);
        engine.inject_entropy().unwrap();
        let mut found = false;
        for _ in 0..100_000 {
            if engine.maybe_poison_cfg_path() {
                found = true;
                break;
            }
        }
        assert!(found, "maybe_poison_cfg_path should return true at least once in 100k iterations");
    }

    #[test]
    fn test_poison_memory_layout_empty_buffer() {
        let seed = [0x00u8; 32];
        let mut engine = ReplayPoisonEngine::new(seed);
        let mut buf: Vec<u8> = vec![];
        engine.poison_memory_layout(&mut buf);
    }

    #[test]
    fn test_shuffle_ring_buffers_empty_buffer() {
        let seed = [0x00u8; 32];
        let mut engine = ReplayPoisonEngine::new(seed);
        let mut buf: Vec<u8> = vec![];
        engine.shuffle_ring_buffers(&mut buf);
    }
}
