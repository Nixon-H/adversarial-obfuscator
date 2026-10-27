use std::sync::atomic::{AtomicBool, AtomicI32, Ordering};

static ARMED: AtomicBool = AtomicBool::new(false);

/// The exit code, parked in memory so the register-scrubbing below
/// cannot destroy it. The scrubbing asm zeroes rax..r15 without
/// declaring the clobber to the compiler, so a value held in a register
/// across it is garbage -- which is why every tamper exit reported 0.
static EXIT_CODE: AtomicI32 = AtomicI32::new(1);

extern "C" fn cleanup_handler() {
    if !ARMED.load(Ordering::Relaxed) {
        return;
    }
    scrub_and_exit_inner(0);
}

pub fn arm_self_destruct() {
    ARMED.store(true, Ordering::SeqCst);
    unsafe {
        libc::atexit(cleanup_handler as extern "C" fn());
    }
}

fn scrub_and_exit_inner(code: i32) -> ! {
    EXIT_CODE.store(code, Ordering::SeqCst);

    unsafe {
        let mut tmp = [0u8; 4096];
        for byte in tmp.iter_mut() {
            *byte = 0;
        }
        for i in 0..16 {
            core::ptr::write_volatile(&mut tmp[i], 0);
        }
    }

    #[cfg(target_arch = "x86_64")]
    unsafe {
        core::arch::asm!(
            "xor rax, rax",
            "xor rbx, rbx",
            "xor rcx, rcx",
            "xor rdx, rdx",
            "xor rsi, rsi",
            "xor rdi, rdi",
            "xor r8, r8",
            "xor r9, r9",
            "xor r10, r10",
            "xor r11, r11",
            "xor r12, r12",
            "xor r13, r13",
            "xor r14, r14",
            "xor r15, r15",
            options(nostack, nomem),
        );
    }
    #[cfg(target_arch = "aarch64")]
    unsafe {
        core::arch::asm!("udf #0", options(nostack, nomem));
    }

    unsafe {
        libc::_exit(EXIT_CODE.load(Ordering::SeqCst));
    }
}

pub fn scrub_and_exit(code: i32) -> ! {
    scrub_and_exit_inner(code)
}

pub fn disarm() {
    ARMED.store(false, Ordering::SeqCst);
}
