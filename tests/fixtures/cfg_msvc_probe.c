/* Does REAL cl.exe fill the CFG function table when the load config is
 * emitted by the CRT rather than hand-defined? (reviewer item, 2026-11-20)
 *
 * The earlier probes were all clang-cl/lld-link, which refuse to fill
 * `GuardCFFunctionTable` for a caller-defined `_load_config_used`. Real MSVC
 * links against libcmt, which DEFINES `__guard_fids_table` and
 * `__guard_check_icall_fptr` -- so with /guard:cf and NO hand-written
 * `_load_config_used`, msvcrt's own object should supply the complete
 * structure, function table included.
 *
 * This file therefore defines NO load config on purpose. Build with:
 *   cl /guard:cf /O2 /c cfg_msvc_probe.c
 *   link /guard:cf /entry:mainCRTStartup /subsystem:console cfg_msvc_probe.obj
 * and the expected result is GuardFlags & 0x400 set with a non-zero count.
 */
#include <stddef.h>

/* volatile so the optimiser cannot prove these are unused and delete them */
volatile int g_sink;

__declspec(noinline) int target_a(int x) { return x + 1; }
__declspec(noinline) int target_b(int x) { return target_a(x) * 2; }

int mainCRTStartup(void)
{
    g_sink = target_b(7);
    return 0;
}
