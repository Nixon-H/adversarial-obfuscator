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
        // Every clobbered register is declared, so the compiler cannot cache
        // a live value across the asm (the old undeclared-clobber bug that
        // made every tamper exit report 0). rbx is skipped: LLVM reserves it
        // as a base pointer on x86_64 and forbids it as an operand; it is
        // callee-saved and nothing after the _exit reads it.
        core::arch::asm!(
            "xor rax, rax",
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
            lateout("rax") _, lateout("rcx") _,
            lateout("rdx") _, lateout("rsi") _, lateout("rdi") _,
            lateout("r8") _, lateout("r9") _, lateout("r10") _,
            lateout("r11") _, lateout("r12") _, lateout("r13") _,
            lateout("r14") _, lateout("r15") _,
            options(nostack, nomem),
        );
    }
    #[cfg(target_arch = "aarch64")]
    unsafe {
        // This used to be `udf #0` -- a deliberate undefined instruction, so
        // the ARM tamper exit was a SIGILL crash rather than the clean exit
        // x86 gets. Zero the caller-saved registers (x18 is platform
        // reserved; x29/x30 are FP/LR and nothing after the _exit reads
        // them) and take the same clean _exit.
        core::arch::asm!(
            "mov x0, xzr", "mov x1, xzr", "mov x2, xzr", "mov x3, xzr",
            "mov x4, xzr", "mov x5, xzr", "mov x6, xzr", "mov x7, xzr",
            "mov x8, xzr", "mov x9, xzr", "mov x10, xzr", "mov x11, xzr",
            "mov x12, xzr", "mov x13, xzr", "mov x14, xzr", "mov x15, xzr",
            "mov x16, xzr", "mov x17, xzr",
            lateout("x0") _, lateout("x1") _, lateout("x2") _,
            lateout("x3") _, lateout("x4") _, lateout("x5") _,
            lateout("x6") _, lateout("x7") _, lateout("x8") _,
            lateout("x9") _, lateout("x10") _, lateout("x11") _,
            lateout("x12") _, lateout("x13") _, lateout("x14") _,
            lateout("x15") _, lateout("x16") _, lateout("x17") _,
            options(nostack, nomem),
        );
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
