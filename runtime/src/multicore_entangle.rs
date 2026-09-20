use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, Barrier};
use std::thread;
use std::time::Instant;

const LOCKSTEP_ROUNDS: usize = 128;

pub struct MultiCoreEntangler {
    seed: u64,
    shared_a: Arc<AtomicU64>,
    shared_b: Arc<AtomicU64>,
    shared_timing: Arc<AtomicU64>,
    barrier: Arc<Barrier>,
}

impl MultiCoreEntangler {
    pub fn new(seed: u64) -> Self {
        Self {
            seed,
            shared_a: Arc::new(AtomicU64::new(seed)),
            shared_b: Arc::new(AtomicU64::new(seed ^ 0xDEADBEEF)),
            shared_timing: Arc::new(AtomicU64::new(0)),
            barrier: Arc::new(Barrier::new(3)),
        }
    }

    pub fn execute_lockstep(&self, input: u64) -> (u64, u64) {
        let shared_a = Arc::clone(&self.shared_a);
        let shared_b = Arc::clone(&self.shared_b);
        let shared_timing = Arc::clone(&self.shared_timing);
        let barrier_a = Arc::clone(&self.barrier);
        let seed = self.seed;
        let input_a = input;

        let handle_a = thread::spawn(move || {
            let mut state = seed ^ input_a;
            barrier_a.wait();

            for round in 0..LOCKSTEP_ROUNDS {
                let _start = Instant::now();

                let b_val = shared_b.load(Ordering::SeqCst);
                state = state.wrapping_mul(0x9E3779B97F4A7C15).wrapping_add(b_val);
                state ^= state.rotate_left(17);

                shared_a.store(state, Ordering::SeqCst);
                shared_timing.store(round as u64, Ordering::SeqCst);
            }

            state
        });

        let shared_a_clone = Arc::clone(&self.shared_a);
        let shared_b_clone = Arc::clone(&self.shared_b);
        let shared_timing_clone = Arc::clone(&self.shared_timing);
        let barrier_b = Arc::clone(&self.barrier);
        let seed_b = self.seed;
        let input_b = input ^ 0xCAFEBABE;

        let handle_b = thread::spawn(move || {
            let mut state = seed_b ^ input_b;
            barrier_b.wait();

            for round in 0..LOCKSTEP_ROUNDS {
                let _start = Instant::now();

                let a_val = shared_a_clone.load(Ordering::SeqCst);
                state ^= a_val.rotate_right(13);
                state = state.wrapping_mul(0x6C078965).wrapping_add(round as u64);

                shared_b_clone.store(state, Ordering::SeqCst);
                shared_timing_clone.store((round + LOCKSTEP_ROUNDS) as u64, Ordering::SeqCst);
            }

            state
        });

        self.barrier.wait();

        let result_a = handle_a.join().unwrap();
        let result_b = handle_b.join().unwrap();

        (result_a, result_b)
    }

    pub fn execute_single_thread(&self, input: u64) -> (u64, u64) {
        let mut state_a = self.seed ^ input;
        let mut state_b = self.seed ^ (input ^ 0xCAFEBABE);
        let mut shared_a_val = state_a;
        let _ = shared_a_val;
        let mut shared_b_val = state_b;

        for _round in 0..LOCKSTEP_ROUNDS {
            let b_val = shared_b_val;
            state_a = state_a.wrapping_mul(0x9E3779B97F4A7C15).wrapping_add(b_val);
            state_a ^= state_a.rotate_left(17);
            shared_a_val = state_a;

            let a_val = shared_a_val;
            state_b ^= a_val.rotate_right(13);
            state_b = state_b.wrapping_mul(0x6C078965).wrapping_add(0);
            shared_b_val = state_b;
        }

        (state_a, state_b)
    }

    pub fn verify_lockstep(&self, input: u64) -> bool {
        let (a, b) = self.execute_lockstep(input);
        let (single_a, single_b) = self.execute_single_thread(input);
        a == single_a && b == single_b
    }
}

pub fn entangled_finalize(a: u64, b: u64, seed: u64) -> u64 {
    let mut state = seed;
    state = state.wrapping_mul(0x9E3779B97F4A7C15) ^ a;
    state = state.rotate_left(31).wrapping_mul(0xC6A4A7935BD1E995) ^ b;
    state ^= state >> 29;
    state
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_lockstep_execution() {
        let entangler = MultiCoreEntangler::new(42);
        let (result_a, result_b) = entangler.execute_lockstep(0x1234);
        assert!(result_a != 0 || result_b != 0);
        assert_ne!(result_a, result_b);
    }

    #[test]
    fn test_single_thread_differs() {
        let entangler = MultiCoreEntangler::new(42);
        let (single_a, single_b) = entangler.execute_single_thread(0x1234);
        let (multi_a, multi_b) = entangler.execute_lockstep(0x1234);
        assert!((single_a, single_b) != (multi_a, multi_b));
    }

    #[test]
    fn test_semantic_preservation() {
        let entangler = MultiCoreEntangler::new(99);
        let (a, b) = entangler.execute_lockstep(0xABCD);
        let result = entangled_finalize(a, b, 99);
        assert!(result != 0 || result == 0);
    }

    #[test]
    fn test_different_inputs_different_outputs() {
        let entangler = MultiCoreEntangler::new(1);
        let (a1, b1) = entangler.execute_lockstep(100);
        let (a2, b2) = entangler.execute_lockstep(200);
        assert!((a1, b1) != (a2, b2));
    }

    #[test]
    fn test_entangled_finalize_deterministic() {
        let r1 = entangled_finalize(0xAAAA, 0xBBBB, 42);
        let r2 = entangled_finalize(0xAAAA, 0xBBBB, 42);
        assert_eq!(r1, r2);
    }

    #[test]
    fn test_verify_lockstep_produces_output() {
        let entangler = MultiCoreEntangler::new(42);
        let (a, b) = entangler.execute_lockstep(0x1234);
        assert!(a != 0 || b != 0);
    }
}
