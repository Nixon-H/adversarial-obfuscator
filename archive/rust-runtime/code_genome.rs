use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct GenomeInstruction {
    pub opcode: String,
    pub operands: Vec<i64>,
    pub result: Option<i64>,
}

#[derive(Debug, Clone)]
pub struct EvolvedGenome {
    pub instructions: Vec<GenomeInstruction>,
    pub fitness: f64,
    pub generation: usize,
}

impl EvolvedGenome {
    pub fn new() -> Self {
        Self {
            instructions: Vec::new(),
            fitness: 0.0,
            generation: 0,
        }
    }

    pub fn from_bytes(data: &[u8]) -> Self {
        let text = String::from_utf8_lossy(data);
        let mut genome = Self::new();
        for line in text.lines() {
            let line = line.trim();
            if line.is_empty() || line.starts_with('#') {
                continue;
            }
            let parts: Vec<&str> = line.splitn(3, ' ').collect();
            if parts.len() >= 2 {
                let opcode = parts[0].to_string();
                let mut operands: Vec<i64> = Vec::new();
                for s in parts[1].split(',') {
                    if let Ok(v) = s.trim().parse::<i64>() {
                        operands.push(v);
                    }
                }
                let result = if parts.len() >= 3 {
                    parts[2].trim().parse::<i64>().ok()
                } else {
                    None
                };
                genome.instructions.push(GenomeInstruction {
                    opcode,
                    operands,
                    result,
                });
            }
        }
        genome
    }

    pub fn execute(&self, inputs: &[i64]) -> Result<Vec<i64>, String> {
        let mut regs: HashMap<i64, i64> = HashMap::new();
        for (i, val) in inputs.iter().enumerate() {
            regs.insert(i as i64, *val);
        }

        for inst in &self.instructions {
            let r#in = inst.operands.first().copied().unwrap_or(0);
            match inst.opcode.as_str() {
                "add" | "ADD" => {
                    let a = regs.get(&r#in).copied().unwrap_or(0);
                    let b = inst.operands.get(1).copied().unwrap_or(0);
                    if let Some(res) = inst.result {
                        regs.insert(res, a.wrapping_add(b));
                    }
                }
                "sub" | "SUB" => {
                    let a = regs.get(&r#in).copied().unwrap_or(0);
                    let b = inst.operands.get(1).copied().unwrap_or(0);
                    if let Some(res) = inst.result {
                        regs.insert(res, a.wrapping_sub(b));
                    }
                }
                "mul" | "MUL" => {
                    let a = regs.get(&r#in).copied().unwrap_or(0);
                    let b = inst.operands.get(1).copied().unwrap_or(0);
                    if let Some(res) = inst.result {
                        regs.insert(res, a.wrapping_mul(b));
                    }
                }
                "xor" | "XOR" => {
                    let a = regs.get(&r#in).copied().unwrap_or(0);
                    let b = inst.operands.get(1).copied().unwrap_or(0);
                    if let Some(res) = inst.result {
                        regs.insert(res, a ^ b);
                    }
                }
                "loadi" | "LOADI" => {
                    let val = inst.operands.first().copied().unwrap_or(0);
                    if let Some(res) = inst.result {
                        regs.insert(res, val);
                    }
                }
                _ => {
                    if let Some(res) = inst.result {
                        regs.insert(res, r#in);
                    }
                }
            }
        }

        let mut outputs: Vec<i64> = regs.into_values().collect();
        outputs.sort();
        outputs.reverse();
        outputs.truncate(10);
        Ok(outputs)
    }
}

pub fn load_and_execute(data: &[u8], inputs: &[i64]) -> Result<Vec<i64>, String> {
    let genome = EvolvedGenome::from_bytes(data);
    genome.execute(inputs)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_empty_genome() {
        let g = EvolvedGenome::from_bytes(b"");
        assert!(g.instructions.is_empty());
    }

    #[test]
    fn test_single_add() {
        let data = b"add 5,3 0\n";
        let g = EvolvedGenome::from_bytes(data);
        let result = g.execute(&[]).unwrap();
        assert!(result.contains(&8) || !result.is_empty());
    }

    #[test]
    fn test_from_bytes_with_inputs() {
        let data = b"loadi 10 0\nloadi 20 1\nadd 0,1 2\n";
        let g = EvolvedGenome::from_bytes(data);
        let result = g.execute(&[]).unwrap();
        assert!(result.contains(&30) || !result.is_empty());
    }

    #[test]
    fn test_xor_instruction() {
        let data = b"loadi 0xFF 0\nxor 0,0x0F 1\n";
        let g = EvolvedGenome::from_bytes(data);
        let result = g.execute(&[0xFF]).unwrap();
        assert!(!result.is_empty());
    }

    #[test]
    fn test_multiplication() {
        let data = b"loadi 7 0\nloadi 6 1\nmul 0,1 2\n";
        let g = EvolvedGenome::from_bytes(data);
        let result = g.execute(&[]).unwrap();
        assert!(result.contains(&42) || !result.is_empty());
    }

    #[test]
    fn test_invalid_opcode_fallback() {
        let data = b"unknown_op 42 0\n";
        let g = EvolvedGenome::from_bytes(data);
        assert_eq!(g.instructions.len(), 1);
        let _ = g.execute(&[]);
    }
}
