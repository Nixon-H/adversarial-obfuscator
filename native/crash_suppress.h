// Crash-dialog suppression (#34 audit gap, Batch B).
//
// Single shared header used by both native stubs so the tamper-kill path
// exits silently (exit code 137, the project's kill-ladder code) instead of
// raising an OS crash dialog / abort prompt / core-dump notice.
//
//   Windows (guarded by _WIN32):
//     - SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX |
//                    SEM_NOOPENFILEERRORBOX) so hard errors route to the
//                    unhandled-exception filter instead of a message box.
//     - _set_abort_behavior(0, _WRITE_ABORT_MSG) so abort() skips the
//                    "abort() has been called" dialog.
//     - SetUnhandledExceptionFilter-compatible helper: terminate the
//                    process with exit code 137 without dialogs.
//   Linux/POSIX:
//     - SIGPIPE -> SIG_IGN (broken-pipe kills are silent, no SIGPIPE
//                    dialog/terminate noise).
//     - Fatal signals (SIGABRT/SIGSEGV/SIGILL/SIGFPE/SIGBUS) -> a minimal
//                    async-signal-safe handler that calls _exit(137).
//                    (PR_SET_DUMPABLE(0) already lives in stub_linux.cpp's
//                    apply_protections(); this header does not duplicate it.)
//
// Header-only, C and C++ compatible, no new link dependency.
#ifndef NIXON_CRASH_SUPPRESS_H
#define NIXON_CRASH_SUPPRESS_H

#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#include <stdlib.h>
#include <crtdbg.h>

#ifdef __cplusplus
extern "C" {
#endif

// Install once at process start (before any tamper check can fire).
static inline void nixon_suppress_crash_dialogs(void) {
    SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX |
                 SEM_NOOPENFILEERRORBOX);
    _set_abort_behavior(0, _WRITE_ABORT_MSG);
}

// Silent kill used by the tamper path: no dialog, exit code 137
// (matches the project's kill-ladder exit code).
static inline void nixon_silent_kill(void) {
    UINT prev = SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX |
                             SEM_NOOPENFILEERRORBOX);
    (void)prev;
    ExitProcess(137);
}

#ifdef __cplusplus
}
#endif

#else /* POSIX */

#include <signal.h>
#include <unistd.h>

#ifdef __cplusplus
extern "C" {
#endif

// Async-signal-safe fatal handler: silent _exit(137).
static void nixon_fatal_handler(int sig) {
    (void)sig;
    _exit(137);
}

// Install once at process start. SIGPIPE is ignored; fatal signals get
// the silent handler. Uses sigaction when available.
static inline void nixon_suppress_crash_dialogs(void) {
    struct sigaction ign;
    ign.sa_handler = SIG_IGN;
    sigemptyset(&ign.sa_mask);
    ign.sa_flags = 0;
    sigaction(SIGPIPE, &ign, 0);

    struct sigaction fatal;
    fatal.sa_handler = nixon_fatal_handler;
    sigemptyset(&fatal.sa_mask);
    fatal.sa_flags = 0;
    sigaction(SIGABRT, &fatal, 0);
    sigaction(SIGSEGV, &fatal, 0);
    sigaction(SIGILL, &fatal, 0);
    sigaction(SIGFPE, &fatal, 0);
#ifdef SIGBUS
    sigaction(SIGBUS, &fatal, 0);
#endif
}

// Silent kill used by the tamper path: flush nothing, _exit(137).
static inline void nixon_silent_kill(void) {
    _exit(137);
}

#ifdef __cplusplus
}
#endif

#endif /* _WIN32 */
#endif /* NIXON_CRASH_SUPPRESS_H */
