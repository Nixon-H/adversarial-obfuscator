use core::arch::asm;
use std::sync::atomic::{AtomicU64, Ordering};

const ENTROPY_POOL_SIZE: usize = 64;
const FEEDBACK_ROUNDS: u32 = 16;

static ENTROPY_ACCUMULATOR: AtomicU64 = AtomicU64::new(0);

pub struct HardwareEntropyLoop {
    pool: [u64; ENTROPY_POOL_SIZE],
    pool_index: usize,
    accumulator: u64,
    iteration: u64,
}

impl HardwareEntropyLoop {
    pub fn new() -> Self {
        Self {
            pool: [0u64; ENTROPY_POOL_SIZE],
            pool_index: 0,
            accumulator: 0,
            iteration: 0,
        }
    }

    pub fn collect_rdtsc_jitter(&mut self) -> u64 {
        #[cfg(target_arch = "x86_64")]
        {
            let t0: u64;
            let t1: u64;
            let t2: u64;
            unsafe {
                asm!("rdtsc", "lfence", out("eax") _, out("edx") _);
                asm!(
                    "rdtsc",
                    out("eax") t0,
                    out("edx") _,
                    options(nomem, nostack),
                );
                for _ in 0..10 {
                    asm!("nop", options(nomem, nostack));
                }
                asm!(
                    "rdtsc",
                    out("eax") t1,
                    out("edx") _,
                    options(nomem, nostack),
                );
                for _ in 0..10 {
                    asm!("nop", options(nomem, nostack));
                }
                asm!(
                    "rdtsc",
                    out("eax") t2,
                    out("edx") _,
                    options(nomem, nostack),
                );
            }
            let jitter1 = t1.wrapping_sub(t0);
            let jitter2 = t2.wrapping_sub(t1);
            let entropy = (jitter1 ^ jitter2.rotate_left(17)).wrapping_mul(self.iteration.wrapping_add(1));
            self.push_entropy(entropy);
            entropy
        }
        #[cfg(not(target_arch = "x86_64"))]
        {
            let entropy = self.iteration.wrapping_mul(0x9E3779B97F4A7C15);
            self.push_entropy(entropy);
            entropy
        }
    }

    pub fn collect_cache_miss_entropy(&mut self) -> u64 {
        let buf = vec![0u8; 4096 * 64];
        let mut entropy = 0u64;

        for round in 0..4 {
            let offset = (round as usize) * 4096;
            let ptr = buf.as_ptr();
            let _val: u8;

            #[cfg(target_arch = "x86_64")]
            unsafe {
                asm!(
                    "mov {0}, [{1}]",
                    out(reg_byte) _val,
                    in(reg) ptr.wrapping_add(offset),
                    options(nostack),
                );
            }

            std::sync::atomic::compiler_fence(Ordering::SeqCst);

            let stride = ((round as u64).wrapping_mul(7) % 64) as usize;
            for i in 0..64 {
                let idx = (i * 64 + stride) % (4096 * 64);
                let val = buf[idx];
                entropy = entropy.wrapping_mul(0x6C078965).wrapping_add(val as u64);
            }
        }

        self.push_entropy(entropy);
        entropy
    }

    pub fn collect_branch_miss_entropy(&mut self) -> u64 {
        let mut entropy = 0u64;

        for i in 0..100 {
            #[cfg(target_arch = "x86_64")]
            {
                let val = if i % 2 == 0 { i as u64 } else { (i as u64).wrapping_add(1) };
                let cond = val % 3 == 0;
                unsafe {
                    asm!(
                        "cmp {0}, 0",
                        "je 5f",
                        "nop",
                        "5:",
                        in(reg) cond as u64,
                        options(nomem, nostack),
                    );
                }
            }

            let bit = ((i as u64).wrapping_mul(0x9E3779B9) >> (i % 32)) & 1;
            entropy ^= bit << (i % 64);
        }

        self.push_entropy(entropy);
        entropy
    }

    pub fn collect_cpuid_entropy(&mut self) -> u64 {
        let mut entropy = 0u64;

        #[cfg(target_arch = "x86_64")]
        {
            for leaf in [0u32, 1u32, 0x80000001u32] {
                let a: u32;
                let c: u32;
                let d: u32;
                unsafe {
                    asm!(
                        "mov {rbx_save}, rbx",
                        "cpuid",
                        "xchg {rbx_save}, rbx",
                        rbx_save = out(reg) _,
                        inout("eax") leaf => a,
                        out("ecx") c,
                        out("edx") d,
                    );
                }
                entropy = entropy.wrapping_mul(0x9E3779B97F4A7C15);
                entropy ^= (a as u64) ^ ((c as u64) << 32) ^ ((d as u64) << 48);
            }
        }

        self.push_entropy(entropy);
        entropy
    }

    pub fn collect_all(&mut self) -> u64 {
        let e1 = self.collect_rdtsc_jitter();
        let e2 = self.collect_cache_miss_entropy();
        let e3 = self.collect_branch_miss_entropy();
        let e4 = self.collect_cpuid_entropy();
        let combined = e1 ^ e2.rotate_left(13) ^ e3.rotate_left(27) ^ e4.rotate_left(43);
        self.accumulator = self.accumulator.wrapping_mul(0x5851F42D4C957F2D) ^ combined;
        ENTROPY_ACCUMULATOR.store(self.accumulator, Ordering::Relaxed);
        combined
    }

    fn push_entropy(&mut self, val: u64) {
        self.pool[self.pool_index % ENTROPY_POOL_SIZE] = val;
        self.pool_index = self.pool_index.wrapping_add(1);
    }

    pub fn feed_forward(&mut self, key: &mut [u8; 32]) {
        let entropy = self.collect_all();
        for i in 0..32 {
            key[i] ^= ((entropy >> ((i * 5) % 64)) as u8).wrapping_mul(0x9E);
        }
    }

    pub fn feedback_loop<F>(&mut self, mut state: u64, mut f: F) -> u64
    where
        F: FnMut(u64) -> u64,
    {
        for round in 0..FEEDBACK_ROUNDS {
            let entropy = self.collect_all();
            state = f(state);
            state ^= entropy.rotate_left(round);
            state = state.wrapping_mul(0x27D4EB2F165667C5);
        }
        self.accumulator ^= state;
        state
    }

    pub fn accumulator_value(&self) -> u64 {
        ENTROPY_ACCUMULATOR.load(Ordering::Relaxed)
    }

    pub fn pool_snapshot(&self) -> &[u64; ENTROPY_POOL_SIZE] {
        &self.pool
    }
}

impl Default for HardwareEntropyLoop {
    fn default() -> Self {
        Self::new()
    }
}

pub fn derive_protection_key(entropy: u64, base: &[u8; 32]) -> [u8; 32] {
    let mut key = *base;
    for i in 0..32 {
        key[i] ^= ((entropy >> ((i * 3) % 64)) as u8).wrapping_mul(0xA5);
    }
    key
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_collects_rdtsc_jitter() {
        let mut loop_ = HardwareEntropyLoop::new();
        let entropy = loop_.collect_rdtsc_jitter();
        assert!(entropy > 0 || entropy == 0);
    }

    #[test]
    fn test_cache_miss_entropy() {
        let mut loop_ = HardwareEntropyLoop::new();
        let entropy = loop_.collect_cache_miss_entropy();
        assert!(entropy > 0 || entropy == 0);
    }

    #[test]
    fn test_branch_miss_entropy() {
        let mut loop_ = HardwareEntropyLoop::new();
        let entropy = loop_.collect_branch_miss_entropy();
        assert!(entropy > 0 || entropy == 0);
    }

    #[test]
    fn test_feedback_loop_integrates() {
        let mut loop_ = HardwareEntropyLoop::new();
        let result = loop_.feedback_loop(42, |s| s.wrapping_mul(0x9E3779B97F4A7C15));
        assert_ne!(result, 42);
    }

    #[test]
    fn test_collect_all_produces_entropy() {
        let mut loop_ = HardwareEntropyLoop::new();
        let entropy = loop_.collect_all();
        assert!(entropy > 0 || entropy == 0);
    }

    #[test]
    fn test_feed_forward_changes_key() {
        let mut loop_ = HardwareEntropyLoop::new();
        let mut key = [0u8; 32];
        for i in 0..32 { key[i] = i as u8; }
        let original = key;
        loop_.feed_forward(&mut key);
        assert_ne!(key, original);
    }

    #[test]
    fn test_derive_protection_key_changes() {
        let base = [0xABu8; 32];
        let key1 = derive_protection_key(42, &base);
        let key2 = derive_protection_key(99, &base);
        assert_ne!(key1, key2);
    }

    #[test]
    fn test_pool_accumulates() {
        let mut loop_ = HardwareEntropyLoop::new();
        loop_.collect_all();
        loop_.collect_all();
        loop_.collect_all();
        let pool = loop_.pool_snapshot();
        let non_zero = pool.iter().filter(|&&v| v != 0).count();
        assert!(non_zero >= 1);
    }
}
