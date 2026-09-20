use crate::timing;

pub struct DegradationEngine {
    pub seed: [u8; 32],
    pub corruption_count: u32,
}

impl DegradationEngine {
    pub fn new(original_seed: [u8; 32]) -> Self {
        DegradationEngine {
            seed: original_seed,
            corruption_count: 0,
        }
    }

    pub fn maybe_corrupt(&mut self) -> [u8; 32] {
        let rdtsc_val = timing::rdtsc();
        let bit_position = (rdtsc_val as usize) % 256;
        self.seed = Self::corrupt_key(&self.seed, bit_position);
        self.corruption_count += 1;
        self.seed
    }

    pub fn corrupt_key(key: &[u8; 32], bit_position: usize) -> [u8; 32] {
        let mut corrupted = *key;
        let byte_idx = bit_position / 8;
        let bit_idx = bit_position % 8;
        if byte_idx < 32 {
            corrupted[byte_idx] ^= 1u8 << bit_idx;
        }
        corrupted
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_engine_new() {
        let seed = [0xABu8; 32];
        let engine = DegradationEngine::new(seed);
        assert_eq!(engine.seed, seed);
        assert_eq!(engine.corruption_count, 0);
    }

    #[test]
    fn test_corrupt_key_flips_bit_0() {
        let key = [0x00u8; 32];
        let corrupted = DegradationEngine::corrupt_key(&key, 0);
        assert_eq!(corrupted[0], 0x01);
        assert_eq!(&corrupted[1..], &[0x00u8; 31]);
    }

    #[test]
    fn test_corrupt_key_bit_7() {
        let key = [0x00u8; 32];
        let corrupted = DegradationEngine::corrupt_key(&key, 7);
        assert_eq!(corrupted[0], 0x80);
    }

    #[test]
    fn test_corrupt_key_bit_255() {
        let key = [0x00u8; 32];
        let corrupted = DegradationEngine::corrupt_key(&key, 255);
        assert_eq!(corrupted[31], 0x80);
    }

    #[test]
    fn test_corrupt_key_out_of_range() {
        let key = [0x00u8; 32];
        let corrupted = DegradationEngine::corrupt_key(&key, 256);
        assert_eq!(corrupted, key);
    }

    #[test]
    fn test_corrupt_key_exactly_one_bit_flipped() {
        let key = [0x00u8; 32];
        let corrupted = DegradationEngine::corrupt_key(&key, 128);
        let bits_diff: u32 = key.iter().zip(corrupted.iter()).map(|(a, b)| (a ^ b).count_ones()).sum();
        assert_eq!(bits_diff, 1);
    }

    #[test]
    fn test_maybe_corrupt_increments_count() {
        let seed = [0xABu8; 32];
        let mut engine = DegradationEngine::new(seed);
        engine.maybe_corrupt();
        assert_eq!(engine.corruption_count, 1);
        engine.maybe_corrupt();
        assert_eq!(engine.corruption_count, 2);
    }
}
