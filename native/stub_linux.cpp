#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <sys/ptrace.h>
#include <sys/prctl.h>
#include <sys/wait.h>
#include <signal.h>
#include <unistd.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <pthread.h>
#include <stdint.h>
#include <time.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

static volatile int g_debug_detected = 0;
static volatile int g_watchdog_running = 0;
static pthread_t g_watchdog_tid;

static int check_env(void) {
    const char* vars[] = {
        "LD_PRELOAD", "LD_LIBRARY_PATH", "LD_AUDIT", "LD_DEBUG",
        "LD_PROFILE", "LD_ORIGIN_PATH", "TRACE_FORK", "TRACE_PTRACE",
        NULL
    };
    for (int i = 0; vars[i]; i++) {
        if (getenv(vars[i]) != NULL) return 0;
    }
    return 1;
}

static int check_tracer(void) {
    FILE* f = fopen("/proc/self/status", "r");
    if (!f) return 1;
    char line[256];
    while (fgets(line, sizeof(line), f)) {
        if (strncmp(line, "TracerPid:", 10) == 0) {
            int pid = atoi(line + 10);
            fclose(f);
            return (pid == 0) ? 1 : 0;
        }
    }
    fclose(f);
    return 1;
}

static int check_ptrace(void) {
    int status;
    pid_t child = fork();
    if (child == -1) return 1;
    if (child == 0) {
        if (ptrace(PTRACE_TRACEME, 0, 0, 0) == -1)
            _exit(1);
        _exit(0);
    }
    waitpid(child, &status, WUNTRACED);
    if (WIFSTOPPED(status)) {
        ptrace(PTRACE_CONT, child, 0, 0);
        waitpid(child, &status, 0);
        return 1;
    }
    if (WIFEXITED(status) && WEXITSTATUS(status) == 1)
        return 0;
    return 1;
}

static int check_exe_path(void) {
    char buf[1024];
    ssize_t len = readlink("/proc/self/exe", buf, sizeof(buf) - 1);
    if (len > 0) {
        buf[len] = '\0';
        if (strstr(buf, "/sandbox/") || strstr(buf, "/.tmp/") ||
            strstr(buf, "/var/tmp/") || strstr(buf, "/vmtmp/"))
            return 0;
    }
    return 1;
}

static uint64_t rdtsc(void) {
    uint32_t lo, hi;
    __asm__ volatile("rdtsc" : "=a"(lo), "=d"(hi));
    return ((uint64_t)hi << 32) | lo;
}

static int check_timing(void) {
    uint64_t t1 = rdtsc();
    volatile int dummy = 0;
    for (int i = 0; i < 50000; i++) dummy += i;
    uint64_t t2 = rdtsc();
    if ((t2 - t1) > 0xFFFFFF) return 0;

    struct timespec ts1, ts2;
    clock_gettime(CLOCK_MONOTONIC, &ts1);
    dummy = 0;
    for (int i = 0; i < 100; i++) dummy += i;
    clock_gettime(CLOCK_MONOTONIC, &ts2);
    double elapsed = (ts2.tv_sec - ts1.tv_sec) * 1000.0 +
                     (ts2.tv_nsec - ts1.tv_nsec) / 1000000.0;
    if (elapsed > 200.0) return 0;
    return 1;
}

static int check_maps(void) {
    FILE* f = fopen("/proc/self/maps", "r");
    if (!f) return 1;
    char line[512];
    int suspicious = 0;
    while (fgets(line, sizeof(line), f)) {
        if (strstr(line, "rwxp") || strstr(line, "rwx ")) {
            suspicious++;
            if (suspicious > 2) { fclose(f); return 0; }
        }
    }
    fclose(f);
    return 1;
}

static int check_breakpoints(void) {
    unsigned char* addr = (unsigned char*)&check_ptrace;
    for (size_t i = 0; i < 256; i++) {
        if (addr[i] == 0xCC) return 0;
    }
    addr = (unsigned char*)&check_tracer;
    for (size_t i = 0; i < 256; i++) {
        if (addr[i] == 0xCC) return 0;
    }
    return 1;
}

static int check_sandbox(void) {
    long pages = sysconf(_SC_PHYS_PAGES);
    long psize = sysconf(_SC_PAGE_SIZE);
    if (pages > 0 && psize > 0 && (long long)pages * psize < 4LL * 1024 * 1024 * 1024)
        return 0;

    long cores = sysconf(_SC_NPROCESSORS_ONLN);
    if (cores < 2) return 0;

    FILE* f = fopen("/proc/cpuinfo", "r");
    if (f) {
        char line[256];
        while (fgets(line, sizeof(line), f)) {
            if (strstr(line, "hypervisor")) { fclose(f); return 0; }
        }
        fclose(f);
    }

    f = fopen("/proc/uptime", "r");
    if (f) {
        double uptime;
        if (fscanf(f, "%lf", &uptime) == 1 && uptime < 600.0) {
            fclose(f);
            return 0;
        }
        fclose(f);
    }
    return 1;
}

static void sigtrap_handler(int sig, siginfo_t* info, void* ucontext) {
    (void)sig; (void)info; (void)ucontext;
    g_debug_detected = 1;
}

static void* watchdog_loop(void* arg) {
    (void)arg;
    while (g_watchdog_running) {
        int hit = 0;
        if (!check_tracer()) hit = 1;
        if (!check_ptrace()) hit = 1;
        if (!check_breakpoints()) hit = 1;
        if (hit) g_debug_detected = 1;
        struct timespec ts = { .tv_sec = 2, .tv_nsec = 0 };
        nanosleep(&ts, NULL);
    }
    return NULL;
}

bool run_anti_debug_checks(void) {
    if (!check_env()) return false;
    if (!check_tracer()) return false;
    if (!check_ptrace()) return false;
    if (!check_exe_path()) return false;
    if (!check_maps()) return false;
    if (!check_timing()) return false;
    if (!check_sandbox()) return false;
    if (!check_breakpoints()) return false;
    return !g_debug_detected;
}

void apply_protections(void) {
    prctl(PR_SET_DUMPABLE, 0, 0, 0, 0);

    struct sigaction sa;
    sa.sa_sigaction = sigtrap_handler;
    sa.sa_flags = SA_SIGINFO;
    sigemptyset(&sa.sa_mask);
    sigaction(SIGTRAP, &sa, NULL);

    g_watchdog_running = 1;
    pthread_create(&g_watchdog_tid, NULL, watchdog_loop, NULL);
    pthread_detach(g_watchdog_tid);
}

int main(void) {
    apply_protections();
    return run_anti_debug_checks() ? 0 : 1;
}

#ifdef __cplusplus
}
#endif
