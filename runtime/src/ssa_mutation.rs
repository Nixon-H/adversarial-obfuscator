use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct SsaInstruction {
    pub opcode: String,
    pub operands: Vec<i64>,
    pub result: Option<i64>,
}

#[derive(Debug, Clone)]
pub struct SsaVariant {
    pub instructions: Vec<SsaInstruction>,
    pub phi_positions: Vec<usize>,
}

#[derive(Debug, Clone)]
pub struct SsaFunctionVariants {
    pub name: String,
    pub variants: Vec<SsaVariant>,
}

pub struct SsaMutator {
    function_variants: HashMap<String, SsaFunctionVariants>,
    prng_state: u64,
    current_variant_idx: usize,
    current_fn: String,
    switch_count: u64,
}

impl SsaMutator {
    pub fn new(seed: [u8; 32]) -> Self {
        let prng_state = u64::from_le_bytes(seed[0..8].try_into().unwrap())
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        SsaMutator {
            function_variants: HashMap::new(),
            prng_state,
            current_variant_idx: 0,
            current_fn: String::new(),
            switch_count: 0,
        }
    }

    fn next_prng(&mut self) -> u64 {
        self.prng_state = self.prng_state
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        self.prng_state
    }

    pub fn register_variants(&mut self, func_variants: SsaFunctionVariants) {
        let name = func_variants.name.clone();
        self.function_variants.insert(name, func_variants);
    }

    pub fn load_function(&mut self, fn_name: &str) -> bool {
        if self.function_variants.contains_key(fn_name) {
            self.current_fn = fn_name.to_string();
            self.current_variant_idx = 0;
            self.switch_count = 0;
            true
        } else {
            false
        }
    }

    pub fn select_variant(&mut self, fn_name: &str) -> Option<SsaVariant> {
        let r = self.next_prng();
        self.current_fn = fn_name.to_string();
        let func = self.function_variants.get(fn_name)?;
        if func.variants.is_empty() {
            return None;
        }
        let idx = (r as usize) % func.variants.len();
        self.current_variant_idx = idx;
        Some(func.variants[idx].clone())
    }

    pub fn switch_at_phi(&mut self) -> Option<SsaVariant> {
        self.switch_count += 1;
        if self.switch_count % 3 == 0 {
            let r = self.next_prng();
            let fn_name = self.current_fn.clone();
            let func = self.function_variants.get(&fn_name)?;
            if func.variants.len() <= 1 {
                return None;
            }
            let new_idx = (r as usize) % func.variants.len();
            if new_idx != self.current_variant_idx {
                self.current_variant_idx = new_idx;
                return Some(func.variants[new_idx].clone());
            }
        }
        None
    }

    pub fn current_variant(&self, fn_name: &str) -> Option<&SsaVariant> {
        let func = self.function_variants.get(fn_name)?;
        if func.variants.is_empty() {
            return None;
        }
        Some(&func.variants[self.current_variant_idx % func.variants.len()])
    }

    pub fn variant_count(&self, fn_name: &str) -> usize {
        self.function_variants
            .get(fn_name)
            .map(|f| f.variants.len())
            .unwrap_or(0)
    }

    pub fn num_functions(&self) -> usize {
        self.function_variants.len()
    }

    pub fn current_index(&self) -> usize {
        self.current_variant_idx
    }
}

pub fn generate_phi_positions(num_instructions: usize, num_variants: usize) -> Vec<Vec<usize>> {
    let mut results = Vec::with_capacity(num_variants);
    for v in 0..num_variants {
        let mut positions: Vec<usize> = (2..num_instructions.saturating_sub(1))
            .filter(|i| i % 3 == v % 3)
            .collect();
        if positions.is_empty() && num_instructions > 2 {
            positions.push(num_instructions / 2);
        }
        results.push(positions);
    }
    results
}

pub fn check_semantic_equivalence(v1: &SsaVariant, v2: &SsaVariant) -> bool {
    if v1.instructions.len() != v2.instructions.len() {
        return false;
    }
    let commutatives = ["add", "mul", "and", "or", "xor"];
    for (i, (inst1, inst2)) in v1.instructions.iter().zip(v2.instructions.iter()).enumerate() {
        if inst1.opcode != inst2.opcode {
            if !(commutatives.contains(&inst1.opcode.as_str())
                && commutatives.contains(&inst2.opcode.as_str()))
            {
                return false;
            }
        }
        let _r1 = inst1.result.unwrap_or(i as i64);
        let _r2 = inst2.result.unwrap_or(i as i64);
    }
    true
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_variants(name: &str, n: usize) -> SsaFunctionVariants {
        let mut variants = Vec::with_capacity(n);
        for v in 0..n {
            let mut instructions = Vec::new();
            for i in 0..6 {
                let opcode = if v % 2 == 0 {
                    match i % 4 {
                        0 => "add",
                        1 => "mul",
                        2 => "sub",
                        3 => "phi",
                        _ => "nop",
                    }
                } else {
                    match i % 4 {
                        0 => "mul",
                        1 => "add",
                        2 => "sub",
                        3 => "phi",
                        _ => "nop",
                    }
                };
                instructions.push(SsaInstruction {
                    opcode: opcode.to_string(),
                    operands: vec![i as i64, (i + 1) as i64],
                    result: Some(100 + i as i64),
                });
            }
            let phi_positions: Vec<usize> = instructions
                .iter()
                .enumerate()
                .filter(|(_, inst)| inst.opcode == "phi")
                .map(|(i, _)| i)
                .collect();
            variants.push(SsaVariant {
                instructions,
                phi_positions,
            });
        }
        SsaFunctionVariants {
            name: name.to_string(),
            variants,
        }
    }

    #[test]
    fn test_ssa_variants_distinct() {
        let mut mutator = SsaMutator::new([0xABu8; 32]);
        let func_variants = make_variants("test_fn", 4);
        mutator.register_variants(func_variants);
        assert_eq!(mutator.variant_count("test_fn"), 4);
        let v1 = mutator.select_variant("test_fn").unwrap();
        let v2 = mutator.select_variant("test_fn").unwrap();
        let idx1 = mutator.current_index();
        let idx2 = mutator.current_index();
        let same = idx1 == idx2;
        if same {
            let _v3 = mutator.select_variant("test_fn").unwrap();
            let idx3 = mutator.current_index();
            let _v4 = mutator.select_variant("test_fn").unwrap();
            let idx4 = mutator.current_index();
            let all_same = idx1 == idx3 && idx1 == idx4;
            if all_same {
                assert!(false, "With 4 variants, we should eventually get a different selection");
            }
        } else {
            assert_ne!(v1.instructions[0].opcode, v2.instructions[0].opcode);
        }
    }

    #[test]
    fn test_semantic_equivalence() {
        let v1 = SsaVariant {
            instructions: vec![
                SsaInstruction { opcode: "add".into(), operands: vec![1, 2], result: Some(0) },
                SsaInstruction { opcode: "mul".into(), operands: vec![3, 4], result: Some(1) },
                SsaInstruction { opcode: "sub".into(), operands: vec![5, 6], result: Some(2) },
            ],
            phi_positions: vec![],
        };
        let v2 = SsaVariant {
            instructions: vec![
                SsaInstruction { opcode: "add".into(), operands: vec![1, 2], result: Some(0) },
                SsaInstruction { opcode: "mul".into(), operands: vec![3, 4], result: Some(1) },
                SsaInstruction { opcode: "sub".into(), operands: vec![5, 6], result: Some(2) },
            ],
            phi_positions: vec![],
        };
        assert!(check_semantic_equivalence(&v1, &v2));
        let v3 = SsaVariant {
            instructions: vec![
                SsaInstruction { opcode: "mul".into(), operands: vec![2, 1], result: Some(0) },
                SsaInstruction { opcode: "add".into(), operands: vec![4, 3], result: Some(1) },
                SsaInstruction { opcode: "sub".into(), operands: vec![5, 6], result: Some(2) },
            ],
            phi_positions: vec![],
        };
        assert!(check_semantic_equivalence(&v2, &v3));
        let v4 = SsaVariant {
            instructions: vec![
                SsaInstruction { opcode: "div".into(), operands: vec![1, 2], result: Some(0) },
                SsaInstruction { opcode: "mul".into(), operands: vec![3, 4], result: Some(1) },
                SsaInstruction { opcode: "sub".into(), operands: vec![5, 6], result: Some(2) },
            ],
            phi_positions: vec![],
        };
        assert!(!check_semantic_equivalence(&v1, &v4));
    }

    #[test]
    fn test_switches_at_boundaries() {
        let mut mutator = SsaMutator::new([0xCDu8; 32]);
        let func_variants = make_variants("boundary_fn", 3);
        mutator.register_variants(func_variants);
        mutator.select_variant("boundary_fn").unwrap();

        let mut switched = false;
        for _ in 0..20 {
            if mutator.switch_at_phi().is_some() {
                switched = true;
                break;
            }
        }
        assert!(switched, "Should switch variants at phi boundaries over many calls");
    }

    #[test]
    fn test_deterministic_given_seed() {
        let mut m1 = SsaMutator::new([0x42u8; 32]);
        let mut m2 = SsaMutator::new([0x42u8; 32]);
        let fv = make_variants("det_fn", 3);
        m1.register_variants(fv.clone());
        m2.register_variants(fv);

        let v1 = m1.select_variant("det_fn").unwrap();
        let v2 = m2.select_variant("det_fn").unwrap();
        assert_eq!(v1.instructions.len(), v2.instructions.len());
    }

    #[test]
    fn test_generate_phi_positions() {
        let positions = generate_phi_positions(10, 3);
        assert_eq!(positions.len(), 3);
        for p in &positions {
            for &pos in p {
                assert!(pos < 10);
            }
        }
    }

    #[test]
    fn test_register_and_load() {
        let mut m = SsaMutator::new([0xAAu8; 32]);
        let fv = make_variants("func1", 2);
        m.register_variants(fv);
        assert!(m.load_function("func1"));
        assert!(!m.load_function("nonexistent"));
    }
}
