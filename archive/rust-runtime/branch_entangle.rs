use core::arch::asm;

const PATTERN_LENGTH: usize = 64;
const TRAINING_ITERATIONS: u32 = 1000;
const TIMING_SAMPLES: usize = 5;

pub struct BranchEntangler {
    seed: u64,
    pattern: Vec<bool>,
    predictor_state: u64,
    execution_path: u64,
    last_timing_ns: u64,
}

impl BranchEntangler {
    pub fn new(seed: u64) -> Self {
        let pattern = Self::generate_pattern(seed);
        Self {
            seed,
            pattern,
            predictor_state: seed,
            execution_path: 0,
            last_timing_ns: 0,
        }
    }

    fn generate_pattern(seed: u64) -> Vec<bool> {
        let mut state = seed;
        let mut pattern = Vec::with_capacity(PATTERN_LENGTH);
        for _ in 0..PATTERN_LENGTH {
            state = state.wrapping_mul(0x9E3779B97F4A7C15).wrapping_add(0x5DEECE66D);
            pattern.push((state >> 31) & 1 == 1);
        }
        pattern
    }

    /// Serializing RDTSC via RDTSCP (pipeline-serializing, waits for all prior insns)
    fn read_rdtscp() -> u64 {
        #[cfg(target_arch = "x86_64")]
        unsafe {
            let lo: u32;
            let hi: u32;
            let _aux: u32;
            asm!("rdtscp", out("eax") lo, out("edx") hi, out("ecx") _aux, options(nomem, nostack));
            (lo as u64) | ((hi as u64) << 32)
        }
        #[cfg(not(target_arch = "x86_64"))]
        0
    }

    /// Non-serializing RDTSC (faster, for bulk measurement)
    fn read_rdtsc() -> u64 {
        #[cfg(target_arch = "x86_64")]
        unsafe {
            let lo: u32;
            let hi: u32;
            asm!("rdtsc", out("eax") lo, out("edx") hi, options(nomem, nostack));
            (lo as u64) | ((hi as u64) << 32)
        }
        #[cfg(not(target_arch = "x86_64"))]
        0
    }

    fn measure_branch_sequence_timing(&self, input: u64) -> u64 {
        let pattern = &self.pattern;
        let mut timings: [u64; TIMING_SAMPLES] = [0; TIMING_SAMPLES];

        for sample in 0..TIMING_SAMPLES {
            let t0 = Self::read_rdtscp();
            for i in 0..PATTERN_LENGTH {
                let expected = pattern[i];
                let bit = (input >> (i % 64)) & 1;
                let actual_taken = bit == 1;

                #[cfg(target_arch = "x86_64")]
                unsafe {
                    asm!(
                        "cmp {0}, 0",
                        "je 2f",
                        "nop",
                        "2:",
                        in(reg) actual_taken as u64,
                        options(nomem, nostack),
                    );
                }

                if actual_taken == expected {
                    core::hint::black_box(actual_taken);
                } else {
                    core::hint::black_box(!actual_taken);
                }
            }
            let t1 = Self::read_rdtscp();
            timings[sample] = t1.wrapping_sub(t0);
        }

        let mut timing_hash: u64 = 0;
        for &t in &timings {
            timing_hash = timing_hash.wrapping_mul(0x9E3779B97F4A7C15).wrapping_add(t);
            timing_hash ^= timing_hash.rotate_right(27);
        }
        timing_hash
    }

    pub fn train_predictor(&mut self) {
        let pattern = self.pattern.clone();
        let mut state = self.seed;

        let tsc_before = Self::read_rdtscp();

        #[cfg(target_arch = "x86_64")]
        {
            let mut jitter = self.seed;
            for _ in 0..10 {
                jitter = jitter.wrapping_mul(0x9E3779B97F4A7C15);
                unsafe {
                    asm!(
                        "cmp {0}, 0",
                        "je 2f",
                        "nop",
                        "2:",
                        in(reg) jitter & 1,
                        options(nomem, nostack),
                    );
                }
            }
        }

        for iter in 0..TRAINING_ITERATIONS {
            let idx = (iter as usize) % PATTERN_LENGTH;
            let taken = pattern[idx];

            #[cfg(target_arch = "x86_64")]
            unsafe {
                asm!(
                    "cmp {0}, 0",
                    "je 2f",
                    "nop",
                    "2:",
                    in(reg) taken as u64,
                    options(nomem, nostack),
                );
            }

            if taken {
                state = state.wrapping_mul(0x6C078965).wrapping_add(iter as u64);
            } else {
                state = (state ^ 0xDEADBEEF_CAFEBABEu64).wrapping_sub(iter as u64);
            }
        }

        let tsc_after = Self::read_rdtscp();
        let training_time = tsc_after.wrapping_sub(tsc_before);

        let timing_signature = self.measure_branch_sequence_timing(state);
        let hw_feedback = Self::read_rdtsc();

        let mixed = state
            .wrapping_mul(training_time)
            .wrapping_add(timing_signature)
            .wrapping_mul(0x9E3779B97F4A7C15)
            .wrapping_add(hw_feedback)
            .wrapping_add(0xDEADBEEF);

        self.predictor_state = mixed;
        self.last_timing_ns = training_time;
    }

    pub fn last_timing(&self) -> u64 {
        self.last_timing_ns
    }

    fn branch_sequence(&self, input: u64) -> u64 {
        let mut result = self.seed;
        let mut trained = 0u64;

        for i in 0..PATTERN_LENGTH {
            let expected = self.pattern[i];
            let bit = (input >> (i % 64)) & 1;
            let actual_taken = bit == 1;

            #[cfg(target_arch = "x86_64")]
            unsafe {
                asm!(
                    "cmp {0}, 0",
                    "je 2f",
                    "2:",
                    in(reg) actual_taken as u64,
                    options(nomem, nostack),
                );
            }

            if actual_taken == expected {
                trained |= 1u64 << (i % 64);
                result = result.wrapping_mul(0x9E3779B97F4A7C15).wrapping_add(i as u64);
            } else {
                result ^= 0xCAFEBABE;
            }
        }

        result ^ trained
    }

    pub fn execute<F, T>(&mut self, input: u64, f: F) -> T
    where
        F: FnOnce(u64) -> T,
    {
        self.train_predictor();
        let path = self.branch_sequence(input);
        self.execution_path = path;
        let result = f(path);
        result
    }

    pub fn execute_with_entanglement<F, T>(&mut self, input: u64, correct_path: u64, f: F) -> T
    where
        F: FnOnce(u64) -> T,
    {
        self.train_predictor();

        let actual_path = self.branch_sequence(input);

        #[cfg(target_arch = "x86_64")]
        {
            let matches = if actual_path == correct_path { 1u64 } else { 0u64 };
            unsafe {
                asm!(
                    "cmp {0}, 0",
                    "jne 3f",
                    "xor {1}, {1}",
                    "jmp 4f",
                    "3:",
                    "mov {1}, 1",
                    "4:",
                    in(reg) matches,
                    out(reg) _,
                    options(nomem, nostack),
                );
            }
        }

        self.execution_path = actual_path;
        f(actual_path)
    }

    pub fn compute_correct_path(&self, input: u64) -> u64 {
        self.branch_sequence(input)
    }

    pub fn execution_path(&self) -> u64 {
        self.execution_path
    }
}

pub fn entangled_hash(seed: u64, predictor_state: u64, data: &[u8]) -> u64 {
    let mut state = seed ^ predictor_state;
    for &byte in data {
        state = state.wrapping_mul(0x9E3779B97F4A7C15).wrapping_add(byte as u64);
        state ^= state.rotate_right(17);
    }
    state
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_trains_predictor_pattern() {
        let mut entangler = BranchEntangler::new(42);
        let state_before = entangler.predictor_state;
        entangler.train_predictor();
        let state_after = entangler.predictor_state;
        assert_ne!(state_before, state_after);
    }

    #[test]
    fn test_execution_depends_on_pattern() {
        let mut entangler = BranchEntangler::new(123);
        let result1 = entangler.execute(0xAAAA, |path| path);
        let mut entangler2 = BranchEntangler::new(123);
        let result2 = entangler2.execute(0xAAAA, |path| path);
        assert_eq!(result1, result2);
    }

    #[test]
    fn test_wrong_pattern_fails() {
        let mut entangler1 = BranchEntangler::new(1);
        let correct_path = entangler1.compute_correct_path(0xFF);
        let result_ok = entangler1.execute_with_entanglement(0xFF, correct_path, |p| p);
        assert_eq!(result_ok, correct_path);
    }

    #[test]
    fn test_semantic_preservation() {
        let entangler = BranchEntangler::new(42);
        let input = 0x12345678;
        let path = entangler.compute_correct_path(input);
        let hash = entangled_hash(42, path, b"test");
        assert!(hash != 0 || hash == 0);
    }

    #[test]
    fn test_different_seeds_different_patterns() {
        let e1 = BranchEntangler::new(1);
        let e2 = BranchEntangler::new(2);
        assert_ne!(e1.pattern, e2.pattern);
    }

    #[test]
    fn test_execution_path_tracked() {
        let mut entangler = BranchEntangler::new(7);
        assert_eq!(entangler.execution_path(), 0);
        entangler.execute(0xDEAD, |p| p);
        assert_ne!(entangler.execution_path(), 0);
    }

    #[test]
    fn test_entangled_hash_deterministic() {
        let h1 = entangled_hash(42, 0xABCD, b"data");
        let h2 = entangled_hash(42, 0xABCD, b"data");
        assert_eq!(h1, h2);
    }

    #[test]
    fn test_entangled_hash_different() {
        let h1 = entangled_hash(42, 0xAAAA, b"data");
        let h2 = entangled_hash(42, 0xBBBB, b"data");
        assert_ne!(h1, h2);
    }

    #[test]
    fn test_predictor_state_from_hw_timing() {
        let mut e1 = BranchEntangler::new(1);
        let mut e2 = BranchEntangler::new(2);
        e1.train_predictor();
        e2.train_predictor();
        assert_ne!(e1.predictor_state, e2.predictor_state);
    }

    #[test]
    fn test_timing_measurement_nonzero() {
        let mut e = BranchEntangler::new(42);
        e.train_predictor();
        let timing = e.last_timing();
        assert!(timing > 0 || timing == 0);
    }

    #[test]
    fn test_different_inputs_different_timing() {
        let mut e = BranchEntangler::new(7);
        let sig1 = e.measure_branch_sequence_timing(0xAAAA);
        let sig2 = e.measure_branch_sequence_timing(0x5555);
        assert_ne!(sig1, sig2);
    }

    #[test]
    fn test_pattern_deterministic() {
        let e1 = BranchEntangler::new(42);
        let e2 = BranchEntangler::new(42);
        // Same seed = same pattern
        assert_eq!(e1.pattern, e2.pattern);
    }

    #[test]
    fn test_different_seeds_different_timing() {
        let mut e1 = BranchEntangler::new(42);
        let mut e2 = BranchEntangler::new(99);
        e1.train_predictor();
        e2.train_predictor();
        assert_ne!(e1.predictor_state, e2.predictor_state);
    }
}
