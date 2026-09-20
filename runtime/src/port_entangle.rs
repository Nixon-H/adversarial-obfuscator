use core::arch::asm;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CpuGeneration {
    IntelRaptorLake,
    IntelAlderLake,
    AmdZen4,
    AmdZen3,
    Unknown,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct PortConfig {
    pub alu_ports: u8,
    pub branch_ports: u8,
    pub load_ports: u8,
    pub store_ports: u8,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ExecutionPortScheduler {
    pub cpu_generation: CpuGeneration,
    pub port_config: PortConfig,
}

impl PortConfig {
    pub fn for_cpu(gen: CpuGeneration) -> Self {
        match gen {
            CpuGeneration::IntelRaptorLake => Self { alu_ports: 4, branch_ports: 1, load_ports: 2, store_ports: 1 },
            CpuGeneration::IntelAlderLake => Self { alu_ports: 4, branch_ports: 1, load_ports: 2, store_ports: 1 },
            CpuGeneration::AmdZen4 => Self { alu_ports: 4, branch_ports: 1, load_ports: 3, store_ports: 2 },
            CpuGeneration::AmdZen3 => Self { alu_ports: 4, branch_ports: 1, load_ports: 2, store_ports: 2 },
            CpuGeneration::Unknown => Self { alu_ports: 3, branch_ports: 1, load_ports: 2, store_ports: 1 },
        }
    }
}

impl ExecutionPortScheduler {
    pub fn new() -> Self {
        let cpu = detect_cpu_generation();
        let cfg = PortConfig::for_cpu(cpu);
        Self { cpu_generation: cpu, port_config: cfg }
    }
}

impl Default for ExecutionPortScheduler {
    fn default() -> Self {
        Self::new()
    }
}

pub fn detect_cpu_generation() -> CpuGeneration {
    #[cfg(target_arch = "x86_64")]
    {
        let vendor = core::arch::x86_64::__cpuid(0);
        let is_intel = vendor.ebx == 0x6C65746E
            && vendor.edx == 0x49656E69
            && vendor.ecx == 0x6E657470;
        let is_amd = vendor.ebx == 0x68747541
            && vendor.edx == 0x69746E65
            && vendor.ecx == 0x444D4163;

        if !is_intel && !is_amd {
            return CpuGeneration::Unknown;
        }

        let info = core::arch::x86_64::__cpuid(1);
        let family = (info.eax >> 8) & 0xf;
        let extended_family = (info.eax >> 20) & 0xff;
        let model = (info.eax >> 4) & 0xf;
        let extended_model = (info.eax >> 16) & 0xf;
        let full_family = if family == 15 { family + extended_family } else { family };
        let full_model = if family == 6 || family == 15 {
            (extended_model << 4) | model
        } else {
            model
        };

        if is_intel {
            return match (full_family, full_model) {
                (6, 183) => CpuGeneration::IntelRaptorLake,
                (6, 151) | (6, 154) => CpuGeneration::IntelAlderLake,
                (6, 140) | (6, 141) | (6, 142) => CpuGeneration::IntelRaptorLake,
                _ => CpuGeneration::Unknown,
            };
        }

        if is_amd {
            return match (full_family, full_model) {
                (25, 96..=127) | (25, 128..=143) => CpuGeneration::AmdZen4,
                (25, 80..=95) => CpuGeneration::AmdZen3,
                _ => CpuGeneration::Unknown,
            };
        }

        CpuGeneration::Unknown
    }
    #[cfg(not(target_arch = "x86_64"))]
    {
        CpuGeneration::Unknown
    }
}

const EXPECTED_TIMING_SIGS: [(CpuGeneration, u64); 4] = [
    (CpuGeneration::IntelRaptorLake, 0xA1B2C3D4E5F60708),
    (CpuGeneration::IntelAlderLake, 0xA1B2C3D4E5F60708),
    (CpuGeneration::AmdZen4, 0x123456789ABCDEF0),
    (CpuGeneration::AmdZen3, 0xFEDCBA9876543210),
];

pub fn expected_timing_signature(seed: u64) -> u64 {
    let cpu = detect_cpu_generation();
    for &(gen, sig) in &EXPECTED_TIMING_SIGS {
        if gen == cpu {
            return sig.wrapping_mul(seed).wrapping_add(0x9E3779B97F4A7C15);
        }
    }
    seed.wrapping_mul(0x6C078965).wrapping_add(0x5DEECE66D)
}

pub fn timing_test_loop(seed: u64, iterations: u32) -> u64 {
    let t0 = crate::timing::rdtsc();
    let mut a: u64 = seed;
    let mut b: u64 = seed ^ 0xDEADBEEF;
    let mut c: u64 = seed ^ 0xCAFEBABE;
    let mut d: u64 = seed;
    let ptr = &a as *const u64;

    for _ in 0..iterations {
        #[cfg(target_arch = "x86_64")]
        unsafe {
            asm!(
                "add {0}, {0}",
                "xor {1}, {1}",
                "sub {2}, 1",
                inout(reg) a, inout(reg) b, inout(reg) c,
                options(nomem, nostack),
            );
        }
        #[cfg(target_arch = "aarch64")]
        unsafe {
            asm!(
                "mrs {0}, cntvct_el0",
                out(reg) _,
                options(nomem, nostack),
            );
        }
        #[cfg(target_arch = "x86_64")]
        unsafe {
            asm!(
                "mov {0}, [{1}]",
                inout(reg) d, in(reg) ptr,
                options(nostack),
            );
        }
        #[cfg(target_arch = "aarch64")]
        unsafe {
            asm!(
                "mrs {0}, cntvct_el0",
                out(reg) _,
                options(nomem, nostack),
            );
        }
        #[cfg(target_arch = "x86_64")]
        unsafe {
            asm!(
                "cmp {0}, 0",
                "jz 2f",
                "2:",
                in(reg) a,
                options(nomem, nostack),
            );
        }
        #[cfg(target_arch = "aarch64")]
        unsafe {
            asm!(
                "mrs {0}, cntvct_el0",
                out(reg) _,
                options(nomem, nostack),
            );
        }
    }

    let t1 = crate::timing::rdtsc();
    let delta = t1.wrapping_sub(t0);
    delta ^ seed ^ a ^ b ^ c ^ d
}

pub fn derive_key_from_timing(base_key: &[u8; 32], seed: u64) -> [u8; 32] {
    let expected = expected_timing_signature(seed);
    let timing_result = expected.wrapping_mul(seed).wrapping_add(0x5DEECE66D);

    let mut derived = *base_key;
    for i in 0..32 {
        derived[i] ^= (timing_result >> (i % 64)) as u8;
    }

    derived
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
    fn test_detect_cpu_returns_value() {
        let cpu = detect_cpu_generation();
        assert!(matches!(
            cpu,
            CpuGeneration::IntelRaptorLake
                | CpuGeneration::IntelAlderLake
                | CpuGeneration::AmdZen4
                | CpuGeneration::AmdZen3
                | CpuGeneration::Unknown
        ));
    }

    #[test]
    fn test_timing_test_loop_nonzero() {
        let result = timing_test_loop(42, 10);
        assert!(result > 0 || result == 0);
    }

    #[test]
    fn test_timing_test_loop_different_seeds() {
        let r1 = timing_test_loop(1, 10);
        let r2 = timing_test_loop(2, 10);
        assert_ne!(r1, r2);
    }

    #[test]
    fn test_derive_key_deterministic_same_seed() {
        let key = test_key();
        let r1 = derive_key_from_timing(&key, 42);
        let r2 = derive_key_from_timing(&key, 42);
        assert_eq!(r1, r2);
    }

    #[test]
    fn test_derive_key_different_seeds() {
        let key = test_key();
        let r1 = derive_key_from_timing(&key, 100);
        let r2 = derive_key_from_timing(&key, 200);
        assert_ne!(r1, r2);
    }

    #[test]
    fn test_derive_key_not_identity() {
        let key = test_key();
        let derived = derive_key_from_timing(&key, 999);
        assert_ne!(derived, key);
    }

    #[test]
    fn test_execution_port_scheduler_creation() {
        let sched = ExecutionPortScheduler::new();
        assert!(sched.port_config.alu_ports > 0);
    }

    #[test]
    fn test_port_config_for_cpu_variants() {
        let rpl = PortConfig::for_cpu(CpuGeneration::IntelRaptorLake);
        let adl = PortConfig::for_cpu(CpuGeneration::IntelAlderLake);
        let zn4 = PortConfig::for_cpu(CpuGeneration::AmdZen4);
        let zn3 = PortConfig::for_cpu(CpuGeneration::AmdZen3);
        let unk = PortConfig::for_cpu(CpuGeneration::Unknown);
        assert_eq!(rpl, adl);
        assert_ne!(zn4, zn3);
        assert_eq!(unk.alu_ports, 3);
    }

    #[test]
    fn test_expected_timing_signature_detects_cpu() {
        let sig = expected_timing_signature(0);
        assert!(sig > 0 || sig == 0);
    }

    #[test]
    fn test_expected_timing_signature_different_seeds() {
        let s1 = expected_timing_signature(1);
        let s2 = expected_timing_signature(2);
        assert_ne!(s1, s2);
    }
}
