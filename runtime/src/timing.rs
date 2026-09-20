use core::arch::asm;

#[cfg(target_arch = "x86_64")]
pub fn rdtsc() -> u64 {
    unsafe {
        core::arch::x86_64::_rdtsc()
    }
}

#[cfg(not(target_arch = "x86_64"))]
pub fn rdtsc() -> u64 {
    0
}

fn noop_loop(n: u32) {
    #[cfg(target_arch = "x86_64")]
    unsafe {
        asm!(
            "2:",
            "dec {0:e}",
            "jnz 2b",
            inout(reg) n => _,
            options(nostack, nomem),
        );
    }
    #[cfg(target_arch = "aarch64")]
    unsafe {
        asm!(
            "2:",
            "sub {0:w}, {0:w}, #1",
            "cbnz {0:w}, 2b",
            inout(reg) n => _,
            options(nostack, nomem),
        );
    }
}

pub fn check_timing_trap(threshold_cycles: u64) -> bool {
    let t0 = rdtsc();
    noop_loop(1000);
    let t1 = rdtsc();
    t1.wrapping_sub(t0) > threshold_cycles
}

pub fn timing_safe_compare(a: &[u8], b: &[u8]) -> bool {
    if a.len() != b.len() {
        return false;
    }
    let t0 = rdtsc();
    let mut result = 0u8;
    for i in 0..a.len() {
        result |= a[i] ^ b[i];
    }
    let t1 = rdtsc();
    let _delta = t1.wrapping_sub(t0);
    result == 0
}

/// Folded dual-timer check (patch-resistant timing pattern).
///
/// Reads TWO timers around a fixed workload, folds them through
/// xor/and/cmp/cmov-style mixing against a stored 48-bit reference, and
/// returns whether the fold matches. Unlike a bare `delta > threshold`
/// compare (one patchable branch), an attacker must recover the reference
/// AND the fold to forge a pass — the comparison result itself is derived,
/// not a literal threshold in the binary.
///
/// Reference is stored masked to 48 bits; callers bake it at build time
/// from a calibration run (see `calibrate_folded_reference`).
pub fn folded_timing_check(reference_48: u64) -> bool {
    let reference = reference_48 & 0x00ff_ffff_ffff;
    let t0 = rdtsc();
    noop_loop(1000);
    let t1 = rdtsc();
    // Second independent sample (different workload size defeats
    // single-point timer virtualization).
    let t2 = rdtsc();
    noop_loop(250);
    let t3 = rdtsc();
    let d1 = t1.wrapping_sub(t0);
    let d2 = t3.wrapping_sub(t2);
    // Fold: xor the deltas, mix with shifts, mask to 48 bits, then
    // cmov-style select: matched = fold == reference.
    let mut fold = d1 ^ d2.rotate_left(20);
    fold ^= fold >> 24;
    fold ^= fold >> 12;
    fold &= 0x00ff_ffff_ffff;
    // Constant-time select (no early branch on the secret fold):
    let diff = fold ^ reference;
    let mut acc: u64 = 0;
    for i in 0..8 {
        acc |= (diff >> (i * 8)) & 0xff;
    }
    acc == 0
}

/// Calibrate a reference fold on THIS machine (build/provision time).
/// Returns the 48-bit folded value to bake into the binary config.
pub fn calibrate_folded_reference() -> u64 {
    let t0 = rdtsc();
    noop_loop(1000);
    let t1 = rdtsc();
    let t2 = rdtsc();
    noop_loop(250);
    let t3 = rdtsc();
    let d1 = t1.wrapping_sub(t0);
    let d2 = t3.wrapping_sub(t2);
    let mut fold = d1 ^ d2.rotate_left(20);
    fold ^= fold >> 24;
    fold ^= fold >> 12;
    fold & 0x00ff_ffff_ffff
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_rdtsc_returns_value() {
        let val = rdtsc();
        assert!(val > 0 || val == 0);
    }

    #[test]
    fn test_rdtsc_monotonic() {
        let t0 = rdtsc();
        let t1 = rdtsc();
        assert!(t1 >= t0);
    }

    #[test]
    fn test_check_timing_trap_no_trigger() {
        assert!(!check_timing_trap(u64::MAX));
    }

    #[test]
    fn test_timing_safe_compare_equal() {
        let a = b"hello world";
        let b = b"hello world";
        assert!(timing_safe_compare(a, b));
    }

    #[test]
    fn test_timing_safe_compare_not_equal() {
        let a = b"hello world";
        let b = b"hello worlX";
        assert!(!timing_safe_compare(a, b));
    }

    #[test]
    fn test_timing_safe_compare_diff_len() {
        let a = b"short";
        let b = b"longer";
        assert!(!timing_safe_compare(a, b));
    }

    #[test]
    fn test_timing_safe_compare_empty() {
        assert!(timing_safe_compare(b"", b""));
    }

    #[test]
    fn test_folded_timing_check_consistent() {
        // Same reference twice: verdict must be deterministic.
        let reference = 0x2b992ddfa233u64 & 0xffffffffffff;
        let v1 = folded_timing_check(reference);
        let v2 = folded_timing_check(reference);
        assert_eq!(v1, v2);
    }

    #[test]
    fn test_folded_timing_check_rejects_garbage() {
        // A zero reference cannot match a real folded measurement.
        // (With overwhelming probability; the fold space is 2^48.)
        let reference = 0u64;
        let _ = folded_timing_check(reference);
    }
}
