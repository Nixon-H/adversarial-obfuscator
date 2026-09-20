#[derive(Debug, Clone)]
pub struct StackFrameLayout {
    pub slot_order: Vec<usize>,
    pub frame_size: usize,
}

#[derive(Debug, Clone)]
pub struct RegisterAllocation {
    pub logical_to_physical: Vec<usize>,
    pub physical_to_logical: Vec<usize>,
}

#[derive(Debug, Clone)]
pub struct HeapLayout {
    pub allocation_order: Vec<usize>,
    pub base_offset: usize,
}

pub struct StructureRandomizer {
    prng_state: u64,
    num_registers: usize,
    num_stack_slots: usize,
    pub current_stack: Option<StackFrameLayout>,
    pub current_regs: Option<RegisterAllocation>,
    pub current_heap: Option<HeapLayout>,
}

impl StructureRandomizer {
    pub fn new(seed: [u8; 32], num_registers: usize, num_stack_slots: usize) -> Self {
        let prng_state = u64::from_le_bytes(seed[0..8].try_into().unwrap())
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        StructureRandomizer {
            prng_state,
            num_registers,
            num_stack_slots,
            current_stack: None,
            current_regs: None,
            current_heap: None,
        }
    }

    pub fn new_with_seed_u64(seed: u64, num_registers: usize, num_stack_slots: usize) -> Self {
        StructureRandomizer {
            prng_state: seed,
            num_registers,
            num_stack_slots,
            current_stack: None,
            current_regs: None,
            current_heap: None,
        }
    }

    fn next_prng(&mut self) -> u64 {
        self.prng_state = self.prng_state
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        self.prng_state
    }

    fn fisher_yates_permutation(&mut self, n: usize) -> Vec<usize> {
        let mut perm: Vec<usize> = (0..n).collect();
        for i in (1..n).rev() {
            let j = (self.next_prng() as usize) % (i + 1);
            perm.swap(i, j);
        }
        perm
    }

    pub fn randomize_stack_layout(&mut self) -> StackFrameLayout {
        let slot_order = self.fisher_yates_permutation(self.num_stack_slots);
        let layout = StackFrameLayout {
            frame_size: self.num_stack_slots * 8,
            slot_order,
        };
        self.current_stack = Some(layout.clone());
        layout
    }

    pub fn randomize_register_allocation(&mut self) -> RegisterAllocation {
        let logical_to_physical = self.fisher_yates_permutation(self.num_registers);
        let mut physical_to_logical = vec![0usize; self.num_registers];
        for (logical, &physical) in logical_to_physical.iter().enumerate() {
            if physical < physical_to_logical.len() {
                physical_to_logical[physical] = logical;
            }
        }
        let alloc = RegisterAllocation {
            logical_to_physical,
            physical_to_logical,
        };
        self.current_regs = Some(alloc.clone());
        alloc
    }

    pub fn randomize_heap_layout(&mut self, num_allocations: usize) -> HeapLayout {
        let allocation_order = self.fisher_yates_permutation(num_allocations);
        let base_offset = (self.next_prng() as usize) % 4096;
        let layout = HeapLayout {
            allocation_order,
            base_offset,
        };
        self.current_heap = Some(layout.clone());
        layout
    }

    pub fn randomize_all(&mut self, num_heap_allocations: usize) {
        self.randomize_stack_layout();
        self.randomize_register_allocation();
        self.randomize_heap_layout(num_heap_allocations);
    }

    pub fn map_stack_slot(&self, logical_slot: usize) -> Option<usize> {
        self.current_stack
            .as_ref()
            .and_then(|layout| {
                layout
                    .slot_order
                    .get(logical_slot)
                    .copied()
            })
    }

    pub fn map_register(&self, logical_reg: usize) -> Option<usize> {
        self.current_regs
            .as_ref()
            .and_then(|alloc| alloc.logical_to_physical.get(logical_reg).copied())
    }

    pub fn unmap_register(&self, physical_reg: usize) -> Option<usize> {
        self.current_regs
            .as_ref()
            .and_then(|alloc| alloc.physical_to_logical.get(physical_reg).copied())
    }

    pub fn map_heap_allocation(&self, logical_alloc: usize) -> Option<usize> {
        self.current_heap
            .as_ref()
            .and_then(|layout| layout.allocation_order.get(logical_alloc).copied())
    }

    pub fn reset_prng(&mut self, seed: u64) {
        self.prng_state = seed;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_rand(seed: u64) -> StructureRandomizer {
        StructureRandomizer::new_with_seed_u64(seed, 8, 16)
    }

    #[test]
    fn test_stack_layout_differs() {
        let mut r1 = make_rand(0xAAAA);
        let mut r2 = make_rand(0xBBBB);
        let l1 = r1.randomize_stack_layout();
        let l2 = r2.randomize_stack_layout();
        assert_ne!(l1.slot_order, l2.slot_order, "Different seeds -> different stack layouts");
        assert_eq!(l1.frame_size, 128);
        assert_eq!(l2.frame_size, 128);
    }

    #[test]
    fn test_register_allocation_differs() {
        let mut r1 = make_rand(0x1111);
        let mut r2 = make_rand(0x2222);
        let a1 = r1.randomize_register_allocation();
        let a2 = r2.randomize_register_allocation();
        assert_ne!(a1.logical_to_physical, a2.logical_to_physical);
    }

    #[test]
    fn test_heap_layout_differs() {
        let mut r1 = make_rand(0x3333);
        let mut r2 = make_rand(0x4444);
        let h1 = r1.randomize_heap_layout(10);
        let h2 = r2.randomize_heap_layout(10);
        assert_ne!(h1.allocation_order, h2.allocation_order);
    }

    #[test]
    fn test_semantic_preservation() {
        let mut r = make_rand(0x5555);
        let alloc = r.randomize_register_allocation();
        let mut seen: std::collections::HashSet<usize> = std::collections::HashSet::new();
        for &p in &alloc.logical_to_physical {
            assert!(p < alloc.logical_to_physical.len(), "Physical register must be in range");
            seen.insert(p);
        }
        assert_eq!(seen.len(), alloc.logical_to_physical.len(), "All physical registers must be unique");
    }

    #[test]
    fn test_deterministic_given_seed() {
        let mut r1 = make_rand(0x6666);
        let mut r2 = make_rand(0x6666);
        let l1 = r1.randomize_stack_layout();
        let l2 = r2.randomize_stack_layout();
        assert_eq!(l1.slot_order, l2.slot_order);
        let a1 = r1.randomize_register_allocation();
        let a2 = r2.randomize_register_allocation();
        assert_eq!(a1.logical_to_physical, a2.logical_to_physical);
    }

    #[test]
    fn test_map_roundtrip() {
        let mut r = make_rand(0x7777);
        r.randomize_register_allocation();
        for logical in 0..r.num_registers {
            if let Some(physical) = r.map_register(logical) {
                if let Some(mapped_back) = r.unmap_register(physical) {
                    assert_eq!(mapped_back, logical, "Map+unmap roundtrip must return original");
                }
            }
        }
    }

    #[test]
    fn test_stack_map() {
        let mut r = make_rand(0x8888);
        r.randomize_stack_layout();
        for slot in 0..r.num_stack_slots {
            let physical = r.map_stack_slot(slot);
            assert!(physical.is_some());
            let p = physical.unwrap();
            assert!(p < r.num_stack_slots);
        }
    }

    #[test]
    fn test_heap_map() {
        let mut r = make_rand(0x9999);
        r.randomize_heap_layout(20);
        for alloc_idx in 0..20 {
            let physical = r.map_heap_allocation(alloc_idx);
            assert!(physical.is_some());
            assert!(physical.unwrap() < 20);
        }
    }

    #[test]
    fn test_randomize_all() {
        let mut r = make_rand(0xAAAA);
        r.randomize_all(8);
        assert!(r.current_stack.is_some());
        assert!(r.current_regs.is_some());
        assert!(r.current_heap.is_some());
    }

    #[test]
    fn test_reset_prng() {
        let mut r = make_rand(0xBBBB);
        let l1 = r.randomize_stack_layout();
        r.reset_prng(0xBBBB);
        let l2 = r.randomize_stack_layout();
        assert_eq!(l1.slot_order, l2.slot_order, "Resetting PRNG should reproduce same layout");
    }
}
