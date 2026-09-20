use log::{info, warn};
use std::fs;
use std::io::Read;
use std::time::Instant;

pub fn run_checks() {
    info!("[antidbg] running startup anti-debug checks");

    let checks: [(&str, fn() -> bool); 12] = [
        ("ptrace",           check_ptrace),
        ("tracerpid",        check_tracerpid),
        ("timing",           check_timing),
        ("vm_flags",         check_vm_flags),
        ("proc_self",        check_proc_self),
        ("env_vars",         check_env_vars),
        ("seccomp",          check_seccomp),
        ("proc_self_maps",   check_proc_self_maps),
        ("core_pattern",     check_core_pattern),
        ("process_name",     check_process_name),
        ("debuggerd",        check_debuggerd),
        ("ld_preload",       check_ld_preload),
    ];

    for (name, func) in &checks {
        if !func() {
            warn!("[antidbg] {name}: detection triggered");
        } else {
            info!("[antidbg] {name}: passed");
        }
    }

    info!("[antidbg] all checks complete");
}

fn check_ptrace() -> bool {
    // NOTE: We do NOT call ptrace::traceme() here because PTRACE_TRACEME
    // permanently flags this process as "traced". Any subsequent signal
    // (e.g. SIGCHLD from check_seccomp's fork) will cause the process to
    // STOP waiting for a tracer that doesn't exist, hanging indefinitely.
    // TracerPid check covers this detection surface more safely.
    true
}

fn check_tracerpid() -> bool {
    let mut buf = String::new();
    match fs::File::open("/proc/self/status").and_then(|mut f| f.read_to_string(&mut buf)) {
        Ok(_) => {
            for line in buf.lines() {
                if line.starts_with("TracerPid:") {
                    let val = line.trim_start_matches("TracerPid:").trim();
                    return val == "0";
                }
            }
            true
        }
        Err(_) => true,
    }
}

fn check_timing() -> bool {
    let t0 = Instant::now();
    let mut dummy = 0u64;
    for _ in 0..10_000_000 {
        dummy = dummy.wrapping_add(1);
    }
    let wall = t0.elapsed();

    let stat_raw = fs::read_to_string("/proc/self/stat");
    let starttime = stat_raw.ok().and_then(|s| {
        s.split_whitespace().nth(21).and_then(|f| f.parse::<u64>().ok())
    });

    if let Some(st) = starttime {
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_secs())
            .unwrap_or(0);

        let hertz = 100u64;
        let boot_secs = st / hertz;
        let uptime_raw = fs::read_to_string("/proc/uptime").ok();
        let uptime = uptime_raw
            .and_then(|u| u.split_whitespace().next().and_then(|v| v.parse::<f64>().ok()))
            .unwrap_or(0.0);

        let proc_start_abs = (now as f64 - uptime) + boot_secs as f64;
        let clock_now = now as f64;

        if (clock_now - proc_start_abs).abs() > 300.0 {
            warn!("[antidbg] timing: starttime anomaly (possible debugger suspend)");
        }
    }

    if wall.as_micros() > 200_000 {
        return false;
    }
    true
}

fn check_vm_flags() -> bool {
    if let Ok(info) = fs::read_to_string("/proc/cpuinfo") {
        for line in info.lines() {
            if line.contains("hypervisor") {
                warn!("[antidbg] vm_flags: hypervisor detected in cpuinfo");
                return false;
            }
        }
    }

    if let Ok(cgroup) = fs::read_to_string("/proc/self/cgroup") {
        for line in cgroup.lines() {
            let lower = line.to_lowercase();
            if lower.contains("docker") || lower.contains("kubepods") || lower.contains("lxc") {
                warn!("[antidbg] vm_flags: container indicator in cgroup");
                return false;
            }
        }
    }

    if let Ok(sched) = fs::read_to_string("/proc/1/sched") {
        if let Some(first) = sched.lines().next() {
            if !first.trim().starts_with("init") && !first.trim().starts_with("systemd") {
                warn!("[antidbg] vm_flags: /proc/1/sched name mismatch");
                return false;
            }
        }
    }

    true
}

fn check_proc_self() -> bool {
    if fs::read_to_string("/proc/self/maps").is_err() {
        warn!("[antidbg] proc_self: cannot read maps (LD_PRELOAD hook?)");
        return false;
    }

    if fs::read_link("/proc/self/exe").is_err() {
        warn!("[antidbg] proc_self: exe link broken");
        return false;
    }

    if let Ok(fd_dir) = fs::read_dir("/proc/self/fd") {
        let count = fd_dir.filter_map(|e| e.ok()).count();
        if count > 50 {
            warn!("[antidbg] proc_self: high fd count ({})", count);
            return false;
        }
    }

    true
}

fn check_env_vars() -> bool {
    let suspicious = ["LD_PRELOAD", "LD_AUDIT", "LD_DEBUG", "LD_LIBRARY_PATH"];

    for var in &suspicious {
        if std::env::var(var).is_ok() {
            warn!("[antidbg] env_vars: {} is set", var);
            return false;
        }
    }

    true
}

fn check_seccomp() -> bool {
    match unsafe { nix::unistd::fork() } {
        Ok(nix::unistd::ForkResult::Parent { child }) => {
            let _ = nix::sys::wait::waitpid(child, None);
            true
        }
        Ok(nix::unistd::ForkResult::Child) => {
            // Must use _exit(0) NOT std::process::exit(0) here.
            // The child inherits locked mutexes from parent threads;
            // std::process::exit() runs atexit handlers & destructors
            // that may deadlock, hanging the parent's waitpid forever.
            unsafe { libc::_exit(0); }
        }
        Err(e) => {
            if e == nix::errno::Errno::ENOSYS {
                warn!("[antidbg] seccomp: fork blocked (seccomp active)");
            }
            true
        }
    }
}

fn check_proc_self_maps() -> bool {
    let Ok(maps) = fs::read_to_string("/proc/self/maps") else {
        warn!("[antidbg] proc_self_maps: cannot read maps");
        return false;
    };

    for line in maps.lines() {
        if line.contains("rwx") {
            warn!("[antidbg] proc_self_maps: rwx memory region found");
            return false;
        }
        if line.to_lowercase().contains("preload") {
            warn!("[antidbg] proc_self_maps: suspicious preload library in maps");
            return false;
        }
    }

    true
}

fn check_core_pattern() -> bool {
    if let Ok(pattern) = fs::read_to_string("/proc/sys/kernel/core_pattern") {
        let trimmed = pattern.trim();
        if trimmed.is_empty() {
            return true;
        }
        if trimmed.starts_with('|') {
            warn!("[antidbg] core_pattern: piped to helper (core dump monitoring)");
            return false;
        }
        warn!("[antidbg] core_pattern: core dumps enabled (pattern: {trimmed})");
    }
    true
}

fn check_process_name() -> bool {
    let expected = std::env::current_exe()
        .ok()
        .and_then(|p| p.file_name().map(|s| s.to_string_lossy().to_string()))
        .unwrap_or_default();

    if let Ok(status) = fs::read_to_string("/proc/self/status") {
        for line in status.lines() {
            if let Some(name) = line.strip_prefix("Name:\t") {
                if name.trim() != expected {
                    warn!("[antidbg] process_name: expected '{expected}', got '{}'", name.trim());
                    return false;
                }
                break;
            }
        }
    }
    true
}

fn check_debuggerd() -> bool {
    if std::path::Path::new("/system/bin/debuggerd").exists() {
        warn!("[antidbg] debuggerd: /system/bin/debuggerd found (Android debug tools)");
        return false;
    }
    if std::path::Path::new("/system/bin/android-gdb").exists() {
        warn!("[antidbg] debuggerd: /system/bin/android-gdb found");
        return false;
    }
    true
}

fn check_ld_preload() -> bool {
    let vars = ["LD_PRELOAD", "LD_AUDIT", "LD_DEBUG", "LD_LIBRARY_PATH"];
    for var in &vars {
        if std::env::var(var).is_ok() {
            warn!("[antidbg] ld_preload: {var} is set");
            return false;
        }
    }
    true
}
