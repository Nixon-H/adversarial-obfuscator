/* PE load-config provider: makes the CFG flag a mechanism, not a declaration.
 *
 * Measured 2026-11-19. lld-link (and MSVC's link.exe) set
 * DllCharacteristics bit 0x4000 for /GUARD:CF, but without this symbol the
 * linker warns
 *
 *     warning: Control Flow Guard is enabled but '_load_config_used' is missing
 *
 * and emits an EMPTY load-config data directory. Windows then has no guard
 * flags and nothing to enforce, so the bit is a claim with no control behind
 * it. Supplying this translation unit makes the linker emit
 * IMAGE_LOAD_CONFIG_DIRECTORY64 with GuardFlags set:
 *
 *     -guard:cf alone            load config empty,  GuardFlags n/a
 *     + this file                load config 288 B,  GuardFlags 0x100
 *
 * 0x100 is IMAGE_GUARD_CF_INSTRUMENTED: CFG checks were compiled in, so
 * indirect call sites verify against the guard check pointer. It is NOT
 * IMAGE_GUARD_CF_FUNCTION_TABLE_PRESENT (0x400), because that requires a
 * function table emitted by clang-cl with the MSVC headers — a Windows-runner
 * capability. The weaker state is what this host can honestly produce, and
 * `native_harden.check` reports it as `partial: ["cfg_no_function_table"]`
 * rather than rounding it up to full CFG.
 *
 * LAYOUT: field-for-field from IMAGE_LOAD_CONFIG_DIRECTORY64. Order, widths and
 * padding are load-bearing: a wrong layout produces a table the Windows loader
 * misreads, which is worse than emitting none. Two offsets were measured rather
 * than assumed while developing this — GuardFlags sits at 0x90 (not 0x70,
 * which is GuardCFCheckFunctionPointer), and the object carries 288 bytes.
 *
 * HOW TO USE: compile this file alongside the payload object and link both.
 * The runner then reports the resulting header, and `native_harden.check`
 * decides whether CFG is real, partial or inert.
 */
#include <stddef.h>

/* PORTABILITY FOR REAL cl.exe (measured 2026-11-20). This file had only ever
 * been compiled by gcc/clang on Linux, and the first run under MSVC failed:
 *
 *   pe_load_config.c(95): error C2143: syntax error: missing ')' before 'sizeof'
 *   pe_load_config.c(101): error C2143: syntax error: missing ')' before '('
 *
 * Two causes, both in this file:
 *   * `_Static_assert` is C11; MSVC's C frontend spells it `static_assert`
 *     (single underscore, <assert.h>), and rejects the double-underscore form
 *     outside C11 mode;
 *   * `__attribute__((used))` is GCC/Clang-only and MSVC does not parse it at
 *     all -- hence "missing ')' before '('" on the declaration line.
 *
 * Both are now selected per compiler, so the same source compiles with gcc,
 * clang AND cl.exe. This is the difference between "MSVC-ABI compatible" and
 * "compiles with Microsoft's compiler", and it was not demonstrated until the
 * farm ran on a real Windows runner.
 */
#if defined(_MSC_VER)
#include <assert.h>
#define NX_STATIC_ASSERT(cond, msg) static_assert(cond, msg)
#define NX_USED
#define NX_SELECTANY __declspec(selectany)
#else
#define NX_STATIC_ASSERT(cond, msg) _Static_assert(cond, msg)
#define NX_USED __attribute__((used))
/* gcc/clang have no selectany: a single definition in one translation unit
 * does not need it, and __attribute__((used)) keeps it past -O3. */
#define NX_SELECTANY
#endif

typedef unsigned long long NX_U64;
typedef unsigned int NX_U32;
typedef unsigned short NX_U16;

typedef struct {
    NX_U32 CodeIntegrityFlags;
    NX_U32 CodeIntegrityCatalog;
    NX_U32 CodeIntegrityCatalogOffset;
    NX_U32 CodeIntegrityReserved;
} NX_CODE_INTEGRITY;

typedef struct {
    NX_U32 Size;
    NX_U32 TimeDateStamp;
    NX_U16 MajorVersion;
    NX_U16 MinorVersion;
    NX_U32 GlobalFlagsClear;
    NX_U32 GlobalFlagsSet;
    NX_U32 CriticalSectionDefaultTimeout;
    NX_U64 DeCommitFreeBlockThreshold;
    NX_U64 DeCommitTotalFreeThreshold;
    NX_U64 LockPrefixTable;
    NX_U64 MaximumAllocationSize;
    NX_U64 VirtualMemoryThreshold;
    NX_U64 ProcessAffinityMask;
    NX_U32 ProcessHeapFlags;
    NX_U16 CSDVersion;
    NX_U16 DependentLoadFlags;
    NX_U64 EditList;
    NX_U64 SecurityCookie;
    NX_U64 SEHandlerTable;
    NX_U64 SEHandlerCount;
    NX_U64 GuardCFCheckFunctionPointer;
    NX_U64 GuardCFDispatchFunctionPointer;
    NX_U64 GuardCFFunctionTable;
    NX_U64 GuardCFFunctionCount;
    NX_U32 GuardFlags;
    NX_CODE_INTEGRITY CodeIntegrity;
    NX_U64 GuardAddressTakenIatEntryTable;
    NX_U64 GuardAddressTakenIatEntryCount;
    NX_U64 GuardLongJumpTargetTable;
    NX_U64 GuardLongJumpTargetCount;
    NX_U64 DynamicValueRelocTable;
    NX_U64 CHPEMetadataPointer;
    NX_U64 GuardRFFailureRoutine;
    NX_U64 GuardRFFailureRoutineFunctionPointer;
    NX_U32 DynamicValueRelocTableOffset;
    NX_U16 DynamicValueRelocTableSection;
    NX_U16 Reserved2;
    NX_U64 GuardRFVerifyStackPointerFunctionPointer;
    NX_U32 HotPatchTableOffset;
    NX_U32 Reserved3;
    NX_U64 EnclaveConfigurationPointer;
    NX_U64 VolatileMetadataPointer;
    NX_U64 GuardEHContinuationTable;
    NX_U64 GuardEHContinuationCount;
} NX_LOAD_CONFIG_64;

NX_STATIC_ASSERT(sizeof(NX_LOAD_CONFIG_64) == 288,
                 "load-config layout must be 288 bytes; the Windows loader "
                 "reads the Size field literally and a mismatch misreads the "
                 "table");

#define NX_GUARD_FLAGS 0x00000100u   /* IMAGE_GUARD_CF_INSTRUMENTED */

NX_SELECTANY NX_USED
const NX_LOAD_CONFIG_64 _load_config_used = {
    sizeof(NX_LOAD_CONFIG_64),
    0, 0, 0,
    0, 0, 0,
    0, 0, 0, 0, 0, 0,
    0, 0, 0,
    0, 0, 0, 0,
    0, 0, 0, 0,
    NX_GUARD_FLAGS,
    {0, 0, 0, 0},
    0, 0, 0, 0,
    0, 0, 0, 0,
    0, 0, 0,
    0,
    0, 0,
    0, 0,
    0, 0,
};
