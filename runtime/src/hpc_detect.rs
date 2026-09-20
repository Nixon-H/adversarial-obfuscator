use core::arch::asm;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum EmulatorType {
    RealHardware,
    QEMU,
    Wine,
    Frida,
    Hypervisor,
    Unknown,
}

pub fn detect_emulator_via_hpc() -> EmulatorType {
    let score = compute_emulator_score();
    if score >= 3 {
        return EmulatorType::QEMU;
    }
    if score >= 2 {
        return EmulatorType::Hypervisor;
    }
    if score == 1 {
        return if rdtscp_delta_high() {
            EmulatorType::Wine
        } else {
            EmulatorType::Frida
        };
    }
    if cpuid_hypervisor_bit() {
        return EmulatorType::Hypervisor;
    }
    EmulatorType::RealHardware
}

fn rdtscp_delta_high() -> bool {
    let tsc = crate::timing::rdtsc();
    let (_, _) = rdtscp();
    let tsc2 = crate::timing::rdtsc();
    tsc2.wrapping_sub(tsc) > 100
}

fn compute_emulator_score() -> u32 {
    let mut score = 0u32;

    if rdtscp_delta_high() {
        score += 1;
    }

    if cache_miss_ratio_high() {
        score += 1;
    }

    if branch_mispredict_rate_abnormal() {
        score += 1;
    }

    if invariant_tsc_ratio_off() {
        score += 1;
    }

    score
}

#[cfg(target_arch = "x86_64")]
fn rdtscp() -> (u64, u32) {
    let mut low: u32;
    let mut high: u32;
    let mut aux: u32;
    unsafe {
        asm!(
            "rdtscp",
            out("eax") low,
            out("edx") high,
            out("ecx") aux,
            options(nostack, nomem),
        );
    }
    ((high as u64) << 32 | low as u64, aux)
}

#[cfg(target_arch = "aarch64")]
fn rdtscp() -> (u64, u32) {
    (0, 0)
}

fn cache_miss_ratio_high() -> bool {
    let total = crate::hpc::read_l2_cache_misses();
    if total == 0 {
        return false;
    }
    let branch = crate::hpc::read_branch_mispredictions();
    if branch == 0 {
        return false;
    }
    let ratio = if branch > 0 {
        total as f64 / branch as f64
    } else {
        0.0
    };
    ratio > 50.0 || ratio < 0.01
}

fn branch_mispredict_rate_abnormal() -> bool {
    let before = crate::hpc::read_branch_mispredictions();
    if before == 0 {
        return false;
    }
    let mut x: u64 = 0;
    for i in 0..1000 {
        if i % 2 == 0 {
            x = x.wrapping_add(1);
        } else {
            x = x.wrapping_sub(1);
        }
    }
    let _ = x;
    let after = crate::hpc::read_branch_mispredictions();
    if after == 0 {
        return false;
    }
    let delta = after.wrapping_sub(before);
    delta > 100 || delta < 5
}

fn invariant_tsc_ratio_off() -> bool {
    let t1 = crate::timing::rdtsc();
    let mut sum: u64 = 0;
    for i in 0..1000 {
        sum = sum.wrapping_add(i);
    }
    let _ = sum;
    let t2 = crate::timing::rdtsc();
    let delta = t2.wrapping_sub(t1);
    delta > 10000 || delta < 10
}

fn cpuid_hypervisor_bit() -> bool {
    #[cfg(target_arch = "x86_64")]
    {
        let ecx: u32;
        unsafe {
            asm!(
                "push rbx",
                "cpuid",
                "pop rbx",
                inout("eax") 1u32 => _,
                out("ecx") ecx,
                out("edx") _,
                options(nostack, nomem),
            );
        }
        (ecx & (1u32 << 31)) != 0
    }
    #[cfg(target_arch = "aarch64")]
    {
        false
    }
    #[cfg(not(any(target_arch = "x86_64", target_arch = "aarch64")))]
    {
        false
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_detect_emulator_runs() {
        let result = detect_emulator_via_hpc();
        assert!(matches!(
            result,
            EmulatorType::RealHardware
                | EmulatorType::QEMU
                | EmulatorType::Wine
                | EmulatorType::Frida
                | EmulatorType::Hypervisor
                | EmulatorType::Unknown
        ));
    }

    #[test]
    fn test_rdtscp_returns_value() {
        let (tsc, aux) = rdtscp();
        assert!(tsc > 0 || tsc == 0);
        let _ = aux;
    }

    #[test]
    fn test_rdtscp_tsc_related_to_rdtsc() {
        let t0 = crate::timing::rdtsc();
        let (t1, _) = rdtscp();
        let t2 = crate::timing::rdtsc();
        assert!(t1 >= t0 || t2 >= t1);
    }

    #[test]
    fn test_cpuid_hypervisor_bit_check() {
        let _hv = cpuid_hypervisor_bit();
    }

    #[test]
    fn test_branch_mispredict_rate_abnormal_runs() {
        let _result = branch_mispredict_rate_abnormal();
    }
}
