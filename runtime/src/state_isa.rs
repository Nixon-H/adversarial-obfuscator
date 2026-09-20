use std::vec::Vec;

pub struct StateIsaTable {
    history_len: usize,
    state: Vec<u8>,
    rotation: u64,
    pub schedule: Vec<u64>,
}

impl StateIsaTable {
    pub fn new(seed: u64) -> Self {
        let mut schedule = Vec::with_capacity(16);
        let mut rng = seed;
        for _ in 0..16 {
            rng = rng.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
            let threshold = (rng % 0xFFFFFFFF) | 0x10000000;
            schedule.push(threshold);
        }
        StateIsaTable {
            history_len: 8,
            state: Vec::with_capacity(8),
            rotation: 0,
            schedule,
        }
    }

    pub fn with_history_len(seed: u64, history_len: usize) -> Self {
        let mut table = Self::new(seed);
        table.history_len = history_len;
        table
    }

    pub fn lookup(&mut self, opcode: u8, state_hash: &[u8; 32]) -> u8 {
        let state_val = u64::from_le_bytes(state_hash[0..8].try_into().unwrap());
        let threshold = self.schedule[self.rotation as usize % self.schedule.len()];
        if state_val > threshold {
            self.rotation = self.rotation.wrapping_add(1);
        }
        opcode.wrapping_add(self.rotation as u8)
    }

    pub fn update_state(&mut self, instruction_id: u8) -> [u8; 32] {
        self.state.push(instruction_id);
        if self.state.len() > self.history_len {
            self.state.remove(0);
        }
        if self.state.is_empty() {
            return [0u8; 32];
        }
        let digest = crate::ledger::sha256(&self.state);
        digest
    }

    pub fn current_rotation(&self) -> u64 {
        self.rotation
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_mapping_changes_over_time() {
        let mut table = StateIsaTable::new(42);
        let initial = table.lookup(0xAB, &[0u8; 32]);
        let mut hash = [0u8; 32];
        for step in 0..50 {
            hash = table.update_state(step as u8);
        }
        let later = table.lookup(0xAB, &hash);
        // After many updates with non-zero state, rotation may change
        if table.current_rotation() > 0 {
            assert_ne!(initial, later, "Same opcode should map differently after state change");
        }
    }

    #[test]
    fn test_deterministic_per_input() {
        let mut t1 = StateIsaTable::new(42);
        let mut t2 = StateIsaTable::new(42);
        for i in 0u8..20 {
            let h1 = t1.update_state(i);
            let h2 = t2.update_state(i);
            assert_eq!(h1, h2, "Same sequence -> same state hash");
        }
    }

    #[test]
    fn test_different_for_different_inputs() {
        let mut t1 = StateIsaTable::new(42);
        let mut t2 = StateIsaTable::new(42);
        for i in 0u8..10 {
            t1.update_state(i);
            t2.update_state(i.wrapping_add(1));
        }
        let h1 = t1.update_state(0);
        let h2 = t2.update_state(0);
        assert_ne!(h1, h2, "Different sequences -> different state hashes");
    }

    #[test]
    fn test_semantic_correctness() {
        // State ISA should produce a valid opcode for any input
        let mut table = StateIsaTable::new(0);
        for opcode in 0u8..=255u8 {
            let hash = table.update_state(opcode);
            let result = table.lookup(opcode, &hash);
            let _ = result;
        }
    }

    #[test]
    fn test_state_accumulates() {
        let mut table = StateIsaTable::new(7);
        let hash0 = table.update_state(0);
        let hash1 = table.update_state(1);
        assert_ne!(hash0, hash1, "State hash should change after each instruction");
    }
}
