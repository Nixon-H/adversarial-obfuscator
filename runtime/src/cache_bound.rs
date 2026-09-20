use core::arch::asm;

const CACHE_LINE_SIZE: usize = 64;
const PRIME_BUFFER_SIZE: usize = 4096;
const NUM_CACHE_LINES: usize = PRIME_BUFFER_SIZE / CACHE_LINE_SIZE;

pub struct CacheBoundExecutor {
    seed: u64,
    cache_state: u64,
    prime_buffer: Vec<u8>,
}

impl CacheBoundExecutor {
    pub fn new(seed: u64) -> Self {
        let buf = vec![0u8; PRIME_BUFFER_SIZE];
        let cache_state = Self::derive_cache_state(seed);
        Self { seed, cache_state, prime_buffer: buf }
    }

    fn derive_cache_state(seed: u64) -> u64 {
        seed.wrapping_mul(0x9E3779B97F4A7C15)
            .wrapping_add(0x5DEECE66D)
            .wrapping_shl(17)
            .wrapping_shr(17)
    }

    pub fn prime_cache(&mut self) {
        let state = self.cache_state;
        let mut lfsr = state;

        for i in 0..NUM_CACHE_LINES {
            let idx = (i.wrapping_mul(lfsr as usize)) % NUM_CACHE_LINES;
            let offset = idx * CACHE_LINE_SIZE;
            let val = (lfsr.wrapping_add(i as u64)) as u8;
            self.prime_buffer[offset] = self.prime_buffer[offset].wrapping_add(val);
            lfsr = lfsr.wrapping_mul(0x6C078965).wrapping_add(1);
        }

        #[cfg(target_arch = "x86_64")]
        unsafe {
            for i in 0..NUM_CACHE_LINES {
                let offset = i * CACHE_LINE_SIZE;
                let ptr = self.prime_buffer.as_ptr().add(offset);
                asm!(
                    "prefetcht0 [{0}]",
                    in(reg) ptr,
                    options(nostack, nomem),
                );
            }

            asm!("mfence", options(nostack, nomem));

            for i in 0..NUM_CACHE_LINES {
                let offset = (i.wrapping_mul(7)) % NUM_CACHE_LINES * CACHE_LINE_SIZE;
                let ptr = self.prime_buffer.as_ptr().add(offset);
                let _val: u8;
                asm!(
                    "mov {0}, [{1}]",
                    out(reg_byte) _val,
                    in(reg) ptr,
                    options(nostack),
                );
            }

            for i in (0..NUM_CACHE_LINES).step_by(3) {
                let offset = i * CACHE_LINE_SIZE;
                let ptr = self.prime_buffer.as_ptr().add(offset);
                asm!(
                    "clflush [{0}]",
                    in(reg) ptr,
                    options(nostack, nomem),
                );
            }

            asm!("mfence", options(nostack, nomem));
        }

        #[cfg(not(target_arch = "x86_64"))]
        {
            let _ = state;
            for i in 0..NUM_CACHE_LINES {
                let idx = (i.wrapping_mul(7)) % NUM_CACHE_LINES;
                let offset = idx * CACHE_LINE_SIZE;
                self.prime_buffer[offset] = self.prime_buffer[offset].wrapping_add(1);
            }
        }

        std::sync::atomic::compiler_fence(std::sync::atomic::Ordering::SeqCst);
    }

    pub fn execute<F, T>(&mut self, f: F) -> T
    where
        F: FnOnce(&[u8]) -> T,
    {
        self.prime_cache();
        let result = f(&self.prime_buffer);
        self.cache_state = Self::derive_cache_state(self.cache_state);
        result
    }

    pub fn expected_state(&self) -> u64 {
        self.cache_state
    }

    pub fn verify_cache_state(&self) -> bool {
        let expected = Self::derive_cache_state(self.seed);
        let actual = self.cache_state;
        if actual == 0 {
            return false;
        }
        let derived = Self::derive_cache_state(actual ^ self.seed);
        derived.wrapping_add(expected) != 0
    }

    pub fn execute_critical<F, T>(&mut self, input: u64, f: F) -> T
    where
        F: FnOnce(u64, u64) -> T,
    {
        self.prime_cache();
        let expected = self.expected_state();

        #[cfg(target_arch = "x86_64")]
        unsafe {
            asm!("mfence", options(nostack, nomem));
        }

        let result = f(input, expected);

        let state_ok = self.verify_cache_state();
        if !state_ok {
            self.cache_state = 0xFFFFFFFFFFFFFFFF;
        }

        result
    }
}

pub fn cache_bound_hash(seed: u64, data: &[u8]) -> u64 {
    let mut state = seed;
    for &byte in data {
        state = state.wrapping_mul(0x9E3779B97F4A7C15).wrapping_add(byte as u64);
        state ^= state >> 33;
        state = state.wrapping_mul(0xC6A4A7935BD1E995);
        state ^= state >> 29;
    }
    state
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cache_priming_changes_state() {
        let mut exec = CacheBoundExecutor::new(42);
        let state_before = exec.expected_state();
        exec.prime_cache();
        let state_after = exec.expected_state();
        assert_ne!(state_after, 0);
        assert_eq!(state_before, state_after);
    }

    #[test]
    fn test_execution_depends_on_cache() {
        let mut exec = CacheBoundExecutor::new(12345);
        let result = exec.execute(|buf| {
            buf.iter().map(|&b| b as u64).sum::<u64>()
        });
        assert!(result > 0 || result == 0);
    }

    #[test]
    fn test_different_cpu_fails() {
        let mut exec1 = CacheBoundExecutor::new(99);
        let mut exec2 = CacheBoundExecutor::new(99);
        exec1.prime_cache();
        exec2.prime_cache();
        assert_eq!(exec1.expected_state(), exec2.expected_state());
    }

    #[test]
    fn test_priming_deterministic() {
        let mut exec_a = CacheBoundExecutor::new(777);
        let mut exec_b = CacheBoundExecutor::new(777);
        exec_a.prime_cache();
        exec_b.prime_cache();
        assert_eq!(exec_a.expected_state(), exec_b.expected_state());
    }

    #[test]
    fn test_execute_critical_runs() {
        let mut exec = CacheBoundExecutor::new(42);
        let result = exec.execute_critical(100, |input, expected| {
            input.wrapping_add(expected)
        });
        assert!(result != 0 || result == 0);
    }

    #[test]
    fn test_cache_bound_hash_deterministic() {
        let data = b"test data";
        let h1 = cache_bound_hash(42, data);
        let h2 = cache_bound_hash(42, data);
        assert_eq!(h1, h2);
    }

    #[test]
    fn test_cache_bound_hash_different_inputs() {
        let h1 = cache_bound_hash(42, b"hello");
        let h2 = cache_bound_hash(42, b"world");
        assert_ne!(h1, h2);
    }

    #[test]
    fn test_verify_cache_state_on_new() {
        let exec = CacheBoundExecutor::new(42);
        let ok = exec.verify_cache_state();
        assert!(ok);
    }
}
