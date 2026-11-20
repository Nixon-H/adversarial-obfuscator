/* CET + CFG load-config probe, built with clang-cl + lld-link on Linux.
 *
 * Produced tests/fixtures/cet_marked_pe.exe, which is the first REAL object
 * in this repository whose IMAGE_LOAD_CONFIG carries the CET bits. The
 * 2026-11-19 record said CET was "measured as not instrumented"; that
 * measurement was taken without a correctly-sized structure, so the bits
 * never reached the PE. This file is the corrected probe.
 *
 * Build (Linux, no MSVC CRT):
 *   clang-cl-19 --target=x86_64-w64-windows-gnu /guard:cf /c cet_probe.c
 *   lld-link /guard:cf /subsystem:console /nodefaultlib \
 *            /entry:mainCRTStartup /out:cet.exe cet_probe.obj
 *
 * Expected: DllCharacteristics GUARD_CF set, load config 280+ bytes,
 * GuardFlags = 0x144100 (CF_INSTRUMENTED | CET_XFG | CET_SHADOW_STACK |
 * CET_USER_COMPAT), and endbr64 instructions in .text.
 *
 * NOT a statement that Windows enforces shadow stack for this image: that
 * depends on the CPU and the OS mitigation policy, neither of which exists
 * on a Linux host. See docs/security/THREAT_BOUNDARY_LOADER.md §1.
 */
typedef unsigned int u32;
typedef unsigned short u16;
typedef unsigned long long u64;

typedef struct {
    u32 Size; u32 TimeDateStamp;
    u16 MajorVersion; u16 MinorVersion;
    u32 GlobalFlagsClear; u32 GlobalFlagsSet;
    u32 CriticalSectionDefaultTimeout;
    u64 DeCommitFreeBlockThreshold; u64 DeCommitTotalFreeThreshold;
    u64 LockPrefixTable; u64 MaximumAllocationSize;
    u64 VirtualMemoryThreshold; u64 ProcessAffinityMask;
    u32 ProcessHeapFlags; u16 CSDVersion; u16 DependentLoadFlags;
    u64 EditList; u64 SecurityCookie;
    u64 SEHandlerTable; u64 SEHandlerCount;
    u64 GuardCFCheckFunctionPointer; u64 GuardCFDispatchFunctionPointer;
    u64 GuardCFFunctionTable; u64 GuardCFFunctionCount;
    u32 GuardFlags;
    u64 tail[15];
} NX_LC;

/* Only GlobalFlagsSet and GuardFlags are ours. The guard table fields stay
 * zero because lld-link refuses to fill a caller-defined structure -- see
 * the boundary document for the four measured probes behind that. */
__declspec(selectany) NX_LC _load_config_used = {
    sizeof(NX_LC), 0, 0, 0,
    0,
    0x100,
    0,
    0, 0, 0, 0, 0, 0, 0,
    0, 0,
    0, 0, 0, 0,
    0, 0, 0, 0,
    0x100 | 0x4000 | 0x40000 | 0x100000,
    {0}
};

int target_a(int x) { return x + 1; }
int target_b(int x) { return target_a(x) * 2; }

void mainCRTStartup(void)
{
    target_b(1);
}
