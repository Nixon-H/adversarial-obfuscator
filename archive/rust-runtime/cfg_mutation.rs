use std::collections::HashMap;

pub struct VariantTable {
    pub orderings: Vec<Vec<usize>>,
    pub seed: [u8; 32],
}

pub struct CfgMutator {
    pub variant_table: HashMap<String, VariantTable>,
    epoch: u64,
    running_hash: u64,
    prng_state: u64,
}

impl CfgMutator {
    pub fn new(seed: [u8; 32]) -> Self {
        let prng_state = u64::from_le_bytes(seed[0..8].try_into().unwrap())
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        CfgMutator {
            variant_table: HashMap::new(),
            epoch: 0,
            running_hash: 0,
            prng_state,
        }
    }

    fn next_prng(&mut self) -> u64 {
        self.prng_state = self.prng_state
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        self.prng_state
    }

    pub fn register_variant(&mut self, fn_name: &str, orderings: Vec<Vec<usize>>) {
        let seed_slice: [u8; 32] = {
            let mut s = [0u8; 32];
            let h = self.running_hash;
            s[0..8].copy_from_slice(&h.to_le_bytes());
            s
        };
        self.variant_table.insert(
            fn_name.to_string(),
            VariantTable {
                orderings,
                seed: seed_slice,
            },
        );
    }

    pub fn select_variant(&mut self, fn_name: &str) -> Option<Vec<usize>> {
        let prng_val = self.next_prng();
        let table = self.variant_table.get(fn_name)?;
        if table.orderings.is_empty() {
            return None;
        }
        let mixed = self.running_hash
            .wrapping_mul(self.epoch.wrapping_add(1))
            .wrapping_add(prng_val);
        let idx = (mixed as usize) % table.orderings.len();
        Some(table.orderings[idx].clone())
    }

    pub fn advance_epoch(&mut self, dispatch_hash: u64) {
        self.running_hash = self.running_hash
            .wrapping_mul(6364136223846793005)
            .wrapping_add(dispatch_hash);
        self.epoch = self.epoch.wrapping_add(1);
    }

    pub fn current_epoch(&self) -> u64 {
        self.epoch
    }

    pub fn variant_count(&self, fn_name: &str) -> usize {
        self.variant_table
            .get(fn_name)
            .map(|t| t.orderings.len())
            .unwrap_or(0)
    }
}

pub fn generate_orderings(num_blocks: usize, num_variants: usize) -> Vec<Vec<usize>> {
    let mut orderings = Vec::with_capacity(num_variants);
    for v in 0..num_variants {
        let mut order: Vec<usize> = (0..num_blocks).collect();
        let mut rng = v as u64;
        for i in (1..num_blocks).rev() {
            let j = (rng as usize) % (i + 1);
            rng = rng.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
            order.swap(i, j);
        }
        orderings.push(order);
    }
    orderings
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_mutator() -> CfgMutator {
        let seed = [0xABu8; 32];
        CfgMutator::new(seed)
    }

    #[test]
    fn test_selects_different_paths() {
        let mut m = make_mutator();
        let orderings = generate_orderings(5, 4);
        m.register_variant("test_fn", orderings);
        let mut selected = std::collections::HashSet::new();
        for _ in 0..100 {
            m.advance_epoch(0);
            if let Some(v) = m.select_variant("test_fn") {
                selected.insert(v.clone());
            }
        }
        assert!(selected.len() >= 2, "Should select at least 2 different orderings in 100 runs");
    }

    #[test]
    fn test_preserves_semantics() {
        let mut m = make_mutator();
        let orderings = generate_orderings(5, 3);
        m.register_variant("fn_a", orderings.clone());

        let mut results = Vec::new();
        for v in 0..orderings.len() {
            m.advance_epoch(v as u64);
            if let Some(ordering) = m.select_variant("fn_a") {
                let mut state: u64 = 0;
                for &block in ordering.iter() {
                    state = state.wrapping_add(block as u64).wrapping_mul(17);
                }
                results.push(state);
            }
        }
        assert!(!results.is_empty());
        // All orderings should visit same blocks (just different order)
        // so commutative operations produce same result
        let first = results[0];
        for r in &results {
            assert_eq!(*r, first, "All orderings must produce identical post-block state");
        }
    }

    #[test]
    fn test_deterministic_given_seed() {
        let seed = [0x42u8; 32];
        let mut m1 = CfgMutator::new(seed);
        let mut m2 = CfgMutator::new(seed);
        let orderings = generate_orderings(4, 3);
        m1.register_variant("f", orderings.clone());
        m2.register_variant("f", orderings);

        let mut results1 = Vec::new();
        let mut results2 = Vec::new();
        for i in 0..10 {
            m1.advance_epoch(i);
            m2.advance_epoch(i);
            if let Some(v1) = m1.select_variant("f") {
                results1.push(v1.clone());
            }
            if let Some(v2) = m2.select_variant("f") {
                results2.push(v2.clone());
            }
        }
        assert_eq!(results1, results2, "Same seed -> same ordering sequence");
    }

    #[test]
    fn test_does_not_add_branches() {
        let mut m = make_mutator();
        let orderings = generate_orderings(3, 2);
        m.register_variant("linear_fn", orderings);
        for v in m.variant_table.values() {
            for ordering in &v.orderings {
                assert_eq!(ordering.len(), 3, "Each variant must have exactly num_blocks entries");
            }
        }
    }

    #[test]
    fn test_generate_orderings() {
        let orderings = generate_orderings(5, 4);
        assert_eq!(orderings.len(), 4);
        for o in &orderings {
            let mut sorted = o.clone();
            sorted.sort();
            assert_eq!(sorted, vec![0, 1, 2, 3, 4], "Each ordering must cover all blocks");
        }
    }

    #[test]
    fn test_variant_count() {
        let mut m = make_mutator();
        assert_eq!(m.variant_count("nonexistent"), 0);
        let orderings = generate_orderings(3, 5);
        m.register_variant("f", orderings);
        assert_eq!(m.variant_count("f"), 5);
    }
}
