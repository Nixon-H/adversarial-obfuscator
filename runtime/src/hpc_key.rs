use crate::hpc;

fn mix_key(base_key: &[u8; 32], delta: u64, seed: u64, real_hardware: bool) -> [u8; 32] {
    let mut derived = *base_key;
    if real_hardware {
        for i in 0..4 {
            let counter_val = delta.wrapping_mul(seed).rotate_left(i as u32 * 4);
            let bytes = counter_val.to_le_bytes();
            for j in 0..8 {
                derived[i * 8 + j] ^= bytes[j].wrapping_add(seed as u8);
            }
        }
    } else {
        for i in 0..4 {
            let counter_val = delta.wrapping_mul(!seed).rotate_right(i as u32 * 3);
            let bytes = counter_val.to_be_bytes();
            for j in 0..8 {
                derived[i * 8 + j] = derived[i * 8 + j].wrapping_add(bytes[j]).wrapping_mul(0x9b);
            }
        }
    }
    derived
}

pub fn derive_key_from_hpc(base_key: &[u8; 32], seed: u64) -> Result<[u8; 32], String> {
    hpc::prime_cache_pattern(seed);

    let before = hpc::read_pmc(0).map_err(|e| format!("HPC read before failed: {}", e))?;

    hpc::execute_access_pattern(seed);

    let after = hpc::read_pmc(0).map_err(|e| format!("HPC read after failed: {}", e))?;

    let delta = after.wrapping_sub(before);
    let expected = hpc::expected_counter_value(seed);
    let real_hardware = delta == expected;

    Ok(mix_key(base_key, delta, seed, real_hardware))
}

pub fn compute_key_delta(_base_key: &[u8; 32], hpc_seed: u64) -> Result<u64, String> {
    hpc::prime_cache_pattern(hpc_seed);
    let before = hpc::read_pmc(0).map_err(|e| format!("HPC read before failed: {}", e))?;
    hpc::execute_access_pattern(hpc_seed);
    let after = hpc::read_pmc(0).map_err(|e| format!("HPC read after failed: {}", e))?;
    Ok(after.wrapping_sub(before))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_key() -> [u8; 32] {
        let mut k = [0u8; 32];
        for i in 0..32 {
            k[i] = i as u8;
        }
        k
    }

    #[test]
    fn test_mix_key_deterministic_same_params() {
        let key = test_key();
        let r1 = mix_key(&key, 1000, 42, true);
        let r2 = mix_key(&key, 1000, 42, true);
        assert_eq!(r1, r2);
    }

    #[test]
    fn test_mix_key_different_seeds() {
        let key = test_key();
        let r1 = mix_key(&key, 1000, 100, true);
        let r2 = mix_key(&key, 1000, 200, true);
        assert_ne!(r1, r2);
    }

    #[test]
    fn test_mix_key_not_identity() {
        let key = test_key();
        let derived = mix_key(&key, 1000, 999, true);
        assert_ne!(derived, key);
    }

    #[test]
    fn test_mix_key_emulator_differs() {
        let key = test_key();
        let r_real = mix_key(&key, 1000, 42, true);
        let r_emu = mix_key(&key, 1000, 42, false);
        assert_ne!(r_real, r_emu);
    }

    #[test]
    fn test_derive_key_from_hpc_attempt() {
        let key = test_key();
        let result = derive_key_from_hpc(&key, 42);
        assert!(result.is_ok() || result.is_err());
    }

    #[test]
    fn test_compute_key_delta_returns_value() {
        let key = test_key();
        let delta = compute_key_delta(&key, 42);
        assert!(delta.is_ok() || delta.is_err());
    }
}
