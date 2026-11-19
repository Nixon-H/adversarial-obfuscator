// nx_apply_protections — §4 anti-dump enforcement, moved OUT of readable
// loader text (2026-11-19).
//
// The hybrid loader carried this block as Python at the top of every
// artefact (ctypes prctl + resource.setrlimit). DS 4.1 Flash recovered the
// entire enforcement layer from artefact text alone (§5l, measured
// 2026-11-19), the operator accepted the wrapper-readability boundary, and
// the boundary-push option recorded in THREAT_BOUNDARY_LOADER.md — "move
// enforcement into the native blob" — is what this file implements.
//
//   Linux  : prctl(PR_SET_DUMPABLE, 0) + setrlimit(RLIMIT_CORE, {0, INF})
//   macOS  : setrlimit(RLIMIT_CORE, {0, INF}) + ptrace(PT_DENY_ATTACH)
//            (PT_DENY_ATTACH is ADDITIVE on macOS: the Python block was a
//             silent no-op there -- prctl does not exist on macOS -- so
//             macOS artefacts previously shipped dump-limit only.)
//   Windows: no dumpable / core-dump equivalent exists (status quo parity);
//            nothing to apply, nothing to suppress here.
//
// The loader dlopens the blob WITHOUT running its init, calls this entry,
// and only then lets PyInit execute payload code — so dump protection is
// in place before any payload code runs. Fail-closed: the loader refuses a
// blob that does not export the entry point (not one of ours).
//
// SELF-CONTAINED ON PURPOSE: the blob build compiles from a scratch build
// dir holding only payload.c + enforcement.c, so this file carries its own
// signal handling instead of including crash_suppress.h (which lives next
// to core.cpp and would have to be copied into every build dir). The
// handler set is identical in spirit to crash_suppress.h: SIGPIPE ignored,
// fatal signals route to the loader's silent _exit(137) kill ladder, no
// dialogs, no cores.
// struct sigaction / sigaction() hide behind the feature-test macros under a
// strict -std=c99 compile (measured: gcc errors "storage size of 'ign' isn't
// known"). They must be raised BEFORE any libc include is processed.
#if !defined(_WIN32)
#ifndef _POSIX_C_SOURCE
#define _POSIX_C_SOURCE 200809L
#endif
#ifndef _DEFAULT_SOURCE
#define _DEFAULT_SOURCE
#endif
#endif

#include <signal.h>
#include <unistd.h>

#if defined(_WIN32)
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#define NX_EXPORT __declspec(dllexport)
#elif defined(__APPLE__)
#include <sys/ptrace.h>
#include <sys/resource.h>
#include <sys/types.h>
#define NX_EXPORT __attribute__((visibility("default")))
#elif defined(__linux__)
#include <sys/prctl.h>
#include <sys/resource.h>
#include <sys/types.h>
#define NX_EXPORT __attribute__((visibility("default")))
#else
#define NX_EXPORT
#endif

// Async-signal-safe fatal handler: silent _exit(137), matching the loader's
// kill ladder and crash_suppress.h's POSIX behaviour.
static void nixon_fatal_handler(int sig)
{
    (void)sig;
    _exit(137);
}

// Returns a bitmask of what actually applied (1 = dumpable off, 2 = core
// limit zero, 4 = deny-attach). The loader ignores the value; it exists so
// a diagnostic build can print what the kernel accepted. On Windows the
// function applies nothing and returns 0 — same as the old Python block,
// which was a silent no-op there.
NX_EXPORT int nx_apply_protections(void)
{
    int applied = 0;
#if defined(__linux__)
    {
        struct rlimit rl;
        rl.rlim_cur = 0;
        rl.rlim_max = RLIM_INFINITY;
        if (prctl(PR_SET_DUMPABLE, 0, 0, 0, 0) == 0) applied |= 1;
        if (setrlimit(RLIMIT_CORE, &rl) == 0) applied |= 2;
    }
#elif defined(__APPLE__)
    {
        struct rlimit rl;
        rl.rlim_cur = 0;
        rl.rlim_max = RLIM_INFINITY;
        if (setrlimit(RLIMIT_CORE, &rl) == 0) applied |= 2;
        if (ptrace(PT_DENY_ATTACH, 0, (caddr_t)0, 0) == 0) applied |= 4;
    }
#else
    /* Windows / other: nothing to apply (see header comment). */
#endif
    /* Fatal signals route to the silent kill ladder; SIGPIPE is ignored so
       a broken pipe cannot kill the artefact mid-run. */
    {
        struct sigaction ign;
        ign.sa_handler = SIG_IGN;
        sigemptyset(&ign.sa_mask);
        ign.sa_flags = 0;
        sigaction(SIGPIPE, &ign, 0);

        struct sigaction fatal;
        fatal.sa_handler = nixon_fatal_handler;
        sigemptyset(&fatal.sa_mask);
        sigaction(SIGABRT, &fatal, 0);
        sigaction(SIGSEGV, &fatal, 0);
        sigaction(SIGILL, &fatal, 0);
        sigaction(SIGFPE, &fatal, 0);
#ifdef SIGBUS
        sigaction(SIGBUS, &fatal, 0);
#endif
    }
    return applied;
}
