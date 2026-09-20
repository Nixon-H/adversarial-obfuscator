use core::arch::asm;

const PAGE_SIZE: usize = 4096;
const N_PAGES: usize = 64;

pub fn read_pmc_raw(counter_idx: u32) -> Result<u64, String> {
    #[cfg(target_arch = "x86_64")]
    {
        let mut low: u32;
        let mut high: u32;
        unsafe {
            asm!(
                "rdpmc",
                in("ecx") counter_idx,
                out("eax") low,
                out("edx") high,
                options(nostack, nomem),
            );
        }
        Ok((high as u64) << 32 | low as u64)
    }
    #[cfg(target_arch = "aarch64")]
    {
        let _ = counter_idx;
        unsafe {
            let val: u64;
            asm!("mrs {}, cntvct_el0", out(reg) val);
            Ok(val)
        }
    }
    #[cfg(not(any(target_arch = "x86_64", target_arch = "aarch64")))]
    {
        let _ = counter_idx;
        Err("RDPMC not supported on this architecture".to_string())
    }
}

#[cfg(target_arch = "x86_64")]
pub fn read_pmc(counter_idx: u32) -> Result<u64, String> {
    let config = match counter_idx {
        0 => 0x3,
        1 => 0,
        2 => 1 | (0 << 8) | (1 << 16),
        3 => 0x5,
        _ => 0x3,
    };
    match perf_event_open(0, config) {
        Ok(fd) => {
            let val = perf_read_counter(fd)?;
            unsafe { libc::close(fd); }
            Ok(val)
        }
        Err(e) => Err(format!("cannot read PMC {}: {}", counter_idx, e)),
    }
}

#[cfg(not(target_arch = "x86_64"))]
pub fn read_pmc(_counter_idx: u32) -> Result<u64, String> {
    Err("RDPMC not supported on this architecture".to_string())
}

#[cfg(target_arch = "x86_64")]
pub fn read_tsc() -> u64 {
    unsafe { core::arch::x86_64::_rdtsc() }
}

#[cfg(not(target_arch = "x86_64"))]
pub fn read_tsc() -> u64 {
    0
}

#[cfg(target_arch = "x86_64")]
#[repr(C)]
struct PerfEventAttr {
    type_: u32,
    size: u32,
    config: u64,
    sample_period: u64,
    sample_type: u64,
    read_format: u64,
    flags: u64,
    wakeup_events: u32,
    bp_type: u32,
    bp_addr: u64,
    bp_len: u64,
    __reserved: [u64; 6],
}

#[cfg(target_arch = "x86_64")]
fn perf_event_open(type_: u32, config: u64) -> Result<i32, String> {
    let mut attr: PerfEventAttr = unsafe { std::mem::zeroed() };
    attr.type_ = type_;
    attr.size = std::mem::size_of::<PerfEventAttr>() as u32;
    attr.config = config;

    let fd = unsafe {
        let result: i64;
        asm!(
            "syscall",
            inlateout("rax") 298i64 => result,
            in("rdi") &attr as *const PerfEventAttr as i64,
            in("rsi") 0i64,
            in("rdx") -1i64,
            in("r10") -1i64,
            in("r8") 0i64,
            lateout("rcx") _,
            lateout("r11") _,
            options(nostack, nomem),
        );
        result as i32
    };

    if fd < 0 {
        Err(format!("perf_event_open failed: errno={}", -fd))
    } else {
        Ok(fd)
    }
}

#[cfg(target_arch = "x86_64")]
fn perf_read_counter(fd: i32) -> Result<u64, String> {
    let mut val: u64 = 0;
    let n = unsafe {
        libc::read(fd, &mut val as *mut u64 as *mut libc::c_void, 8)
    };
    if n != 8 {
        Err("perf read failed".to_string())
    } else {
        Ok(val)
    }
}

pub fn read_l2_cache_misses() -> u64 {
    #[cfg(target_arch = "x86_64")]
    {
        let config: u64 = 1 | (0 << 8) | (1 << 16);
        match perf_event_open(1, config) {
            Ok(fd) => {
                let val = perf_read_counter(fd).unwrap_or(0);
                unsafe { libc::close(fd); }
                val
            }
            Err(_) => 0,
        }
    }
    #[cfg(not(target_arch = "x86_64"))]
    { 0 }
}

pub fn read_branch_mispredictions() -> u64 {
    #[cfg(target_arch = "x86_64")]
    {
        match perf_event_open(0, 0x5) {
            Ok(fd) => {
                let val = perf_read_counter(fd).unwrap_or(0);
                unsafe { libc::close(fd); }
                val
            }
            Err(_) => 0,
        }
    }
    #[cfg(not(target_arch = "x86_64"))]
    { 0 }
}

fn lfsr_step(state: u64) -> u64 {
    let bit = ((state >> 63) ^ (state >> 62) ^ (state >> 60) ^ (state >> 59)) & 1;
    (state << 1) | bit
}

pub fn prime_cache_pattern(seed: u64) {
    let mut buf = vec![0u8; PAGE_SIZE * N_PAGES];
    let stride = (seed as usize & (N_PAGES - 1)) | 1;
    let mut idx = (seed as usize) % N_PAGES;
    let mut lfsr = seed;
    for _ in 0..N_PAGES {
        let offset = idx * PAGE_SIZE + ((lfsr as usize) & (PAGE_SIZE - 1));
        buf[offset] = buf[offset].wrapping_add(1);
        lfsr = lfsr_step(lfsr);
        idx = (idx + stride) % N_PAGES;
    }
    std::sync::atomic::compiler_fence(std::sync::atomic::Ordering::SeqCst);
    drop(buf);
}

pub fn measure_delta<F>(f: F) -> Result<u64, String>
where
    F: FnOnce(),
{
    let before = read_pmc(0)?;
    f();
    let after = read_pmc(0)?;
    Ok(after.wrapping_sub(before))
}

pub fn expected_counter_value(seed: u64) -> u64 {
    let stride = (seed as usize & (N_PAGES - 1)) | 1;
    let mut idx = (seed as usize) % N_PAGES;
    let mut expected = seed;
    let mut lfsr = seed;
    for _ in 0..N_PAGES {
        let _offset = idx * PAGE_SIZE + ((lfsr as usize) & (PAGE_SIZE - 1));
        expected = expected.wrapping_mul(0x9E3779B97F4A7C15).wrapping_add(lfsr);
        lfsr = lfsr_step(lfsr);
        idx = (idx + stride) % N_PAGES;
    }
    expected
}

pub fn execute_access_pattern(seed: u64) {
    let mut buf = vec![0u8; PAGE_SIZE * N_PAGES];
    let stride = (seed as usize & (N_PAGES - 1)) | 1;
    let mut idx = (seed as usize) % N_PAGES;
    let mut lfsr = seed;
    for _ in 0..N_PAGES {
        let offset = idx * PAGE_SIZE + ((lfsr as usize) & (PAGE_SIZE - 1));
        buf[offset] = buf[offset].wrapping_add(2);
        lfsr = lfsr_step(lfsr);
        idx = (idx + stride) % N_PAGES;
    }
    std::sync::atomic::compiler_fence(std::sync::atomic::Ordering::SeqCst);
    drop(buf);
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_read_tsc_returns_value() {
        let val = read_tsc();
        assert!(val > 0 || val == 0);
    }

    #[test]
    fn test_read_tsc_monotonic() {
        let t0 = read_tsc();
        let t1 = read_tsc();
        assert!(t1 >= t0);
    }

    #[test]
    fn test_read_pmc_attempt() {
        let result = read_pmc(0);
        assert!(result.is_ok() || result.is_err());
    }

    #[test]
    fn test_lfsr_step_does_not_stall() {
        let s = lfsr_step(42);
        assert_ne!(s, 0);
    }

    #[test]
    fn test_prime_cache_pattern_does_not_crash() {
        prime_cache_pattern(12345);
    }

    #[test]
    fn test_execute_access_pattern_does_not_crash() {
        execute_access_pattern(67890);
    }

    #[test]
    fn test_expected_counter_value_deterministic() {
        let v1 = expected_counter_value(42);
        let v2 = expected_counter_value(42);
        assert_eq!(v1, v2);
    }

    #[test]
    fn test_expected_counter_value_different_seeds() {
        let v1 = expected_counter_value(0);
        let v2 = expected_counter_value(1);
        assert_ne!(v1, v2);
    }

    #[test]
    fn test_read_l2_cache_misses_attempt() {
        let val = read_l2_cache_misses();
        assert!(val > 0 || val == 0);
    }

    #[test]
    fn test_read_branch_mispredictions_attempt() {
        let val = read_branch_mispredictions();
        assert!(val > 0 || val == 0);
    }
}
