#include "simd_vm.h"
#include <string.h>
#include <stdlib.h>

#if defined(__x86_64__) || defined(_M_X64)
#include <cpuid.h>
#endif

#if defined(__SSE4_1__) || defined(__SSE4_2__)
#include <smmintrin.h>
#endif

static int g_simd_available = -1;

int simd_available(void) {
    if (g_simd_available >= 0) return g_simd_available;
    g_simd_available = 0;
#if defined(__x86_64__) || defined(_M_X64)
    unsigned int eax, ebx, ecx, edx;
    if (__get_cpuid(1, &eax, &ebx, &ecx, &edx)) {
        if (ecx & (1 << 19)) {
            g_simd_available = 1;
        }
    }
#elif defined(__aarch64__) || defined(_M_ARM64)
    g_simd_available = 1;
#endif
    return g_simd_available;
}

/* Memory lives immediately after regs[] in SimdVmState, at offset 128, but the
 * handlers receive only the regs pointer. They used to index `mem[addr + 4096]`
 * from regs, which started 3968 bytes INTO memory and ended 3968 bytes past it --
 * straight through pc, halted and the handlers[] function-pointer table. Writes
 * there let payload data reach the opcode dispatch table.
 *
 * The offset is derived and asserted rather than hardcoded, so reordering the
 * struct breaks the build instead of the VM.
 */
/* Longest operand run any handler reads: 4 (jmp) -- see handler_jmp. */
#define SIMD_VM_MAX_OPERAND_BYTES 4

#define SIMD_VM_MEM_OFFSET (sizeof(uint64_t) * SIMD_VM_NUM_REGS)
#define SIMD_VM_MEM_BASE(regs_ptr) ((uint8_t *)(void *)(regs_ptr) + SIMD_VM_MEM_OFFSET)

/* If this fails, SIMD_VM_MEM_BASE is wrong and the handlers would corrupt memory. */
#if defined(__STDC_VERSION__) && __STDC_VERSION__ >= 201112L
_Static_assert(offsetof(SimdVmState, memory) == SIMD_VM_MEM_OFFSET,
               "SimdVmState.memory is not immediately after regs[]");
#endif

static int handler_nop(uint64_t *regs, const uint8_t *opcodes, size_t pc) {
    (void)regs; (void)opcodes; (void)pc;
    return 1;
}

static int handler_add(uint64_t *regs, const uint8_t *opcodes, size_t pc) {
    uint8_t dst = opcodes[pc + 1] & 0x0F;
    uint8_t src = opcodes[pc + 2] & 0x0F;
    regs[dst] = regs[dst] + regs[src];
    return 3;
}

static int handler_sub(uint64_t *regs, const uint8_t *opcodes, size_t pc) {
    uint8_t dst = opcodes[pc + 1] & 0x0F;
    uint8_t src = opcodes[pc + 2] & 0x0F;
    regs[dst] = regs[dst] - regs[src];
    return 3;
}

static int handler_mul(uint64_t *regs, const uint8_t *opcodes, size_t pc) {
    uint8_t dst = opcodes[pc + 1] & 0x0F;
    uint8_t src = opcodes[pc + 2] & 0x0F;
    regs[dst] = regs[dst] * regs[src];
    return 3;
}

static int handler_xor(uint64_t *regs, const uint8_t *opcodes, size_t pc) {
    uint8_t dst = opcodes[pc + 1] & 0x0F;
    uint8_t src = opcodes[pc + 2] & 0x0F;
    regs[dst] = regs[dst] ^ regs[src];
    return 3;
}

static int handler_and(uint64_t *regs, const uint8_t *opcodes, size_t pc) {
    uint8_t dst = opcodes[pc + 1] & 0x0F;
    uint8_t src = opcodes[pc + 2] & 0x0F;
    regs[dst] = regs[dst] & regs[src];
    return 3;
}

static int handler_or(uint64_t *regs, const uint8_t *opcodes, size_t pc) {
    uint8_t dst = opcodes[pc + 1] & 0x0F;
    uint8_t src = opcodes[pc + 2] & 0x0F;
    regs[dst] = regs[dst] | regs[src];
    return 3;
}

static int handler_load(uint64_t *regs, const uint8_t *opcodes, size_t pc) {
    uint8_t dst = opcodes[pc + 1] & 0x0F;
    uint8_t addr_reg = opcodes[pc + 2] & 0x0F;
    uint64_t addr = regs[addr_reg];
    if (addr < 65536) {
        uint8_t *mem = SIMD_VM_MEM_BASE(regs);
        regs[dst] = (uint64_t)mem[addr];
    }
    return 3;
}

static int handler_store(uint64_t *regs, const uint8_t *opcodes, size_t pc) {
    uint8_t src = opcodes[pc + 1] & 0x0F;
    uint8_t addr_reg = opcodes[pc + 2] & 0x0F;
    uint64_t addr = regs[addr_reg];
    if (addr < 65536) {
        uint8_t *mem = SIMD_VM_MEM_BASE(regs);
        mem[addr] = (uint8_t)(regs[src] & 0xFF);
    }
    return 3;
}

static int handler_jmp(uint64_t *regs, const uint8_t *opcodes, size_t pc) {
    (void)regs;
    uint32_t target = (uint32_t)opcodes[pc + 1]
                    | ((uint32_t)opcodes[pc + 2] << 8)
                    | ((uint32_t)opcodes[pc + 3] << 16)
                    | ((uint32_t)opcodes[pc + 4] << 24);
    regs[14] = target;
    return 5;
}

static simd_handler_fn handlers[SIMD_VM_MAX_HANDLERS] = {
    handler_nop, handler_add, handler_sub, handler_mul,
    handler_xor, handler_and, handler_or, handler_load,
    handler_store, handler_jmp,
};

/* Bytes each handler needs: it is the instruction length, and therefore how far
 * past pc it may read. The dispatch loops check it, so a truncated operand run
 * halts instead of reading past the opcode buffer -- handler_jmp reads pc+4 and
 * the arithmetic handlers read pc+2, and nothing used to verify those existed.
 * Must stay in step with handlers[] above. */
static const uint8_t handler_operand_bytes[SIMD_VM_MAX_HANDLERS] = {
    1, 3, 3, 3, 3, 3, 3, 3, 3, 5,
};

void simd_vm_init(SimdVmState *vm) {
    memset(vm, 0, sizeof(SimdVmState));
    memcpy(vm->handlers, handlers, sizeof(handlers));
    vm->use_simd = simd_available();
}

int simd_opcode_decode(const uint8_t *opcodes, size_t num_opcodes,
                       uint8_t *decoded, size_t *decoded_count) {
    if (!opcodes || !decoded || !decoded_count) return -1;
    for (size_t i = 0; i < num_opcodes; i++) {
        uint8_t op = opcodes[i];
        decoded[i] = (op < 10) ? 1 : 0;
    }
    *decoded_count = num_opcodes;
    return 0;
}

#if defined(__x86_64__) && defined(__SSE4_1__)
static int simd_dispatch_sse(SimdVmState *vm, const uint8_t *opcodes, size_t num_opcodes) {
    size_t pc = vm->pc;
    while (pc < num_opcodes && !vm->halted && vm->regs[14] < num_opcodes) {
        if (pc + 16 <= num_opcodes) {
            __m128i chunk = _mm_loadu_si128((const __m128i*)(opcodes + pc));
            uint8_t temp[16];
            _mm_storeu_si128((__m128i*)temp, chunk);

            for (int j = 0; j < 16 && pc < num_opcodes && !vm->halted; j++, pc++) {
                uint8_t op = temp[j];
                op = (op < SIMD_VM_MAX_HANDLERS) ? op : 0;
                simd_handler_fn handler = vm->handlers[op];
                if (handler) {
                    if (pc + handler_operand_bytes[op] > num_opcodes) {
                        vm->halted = 1;
                        break;
                    }
                    handler(vm->regs, opcodes, pc);
                } else {
                    vm->halted = 1;
                }
            }
        } else {
            uint8_t op = opcodes[pc];
            op = (op < SIMD_VM_MAX_HANDLERS) ? op : 0;
            simd_handler_fn handler = vm->handlers[op];
            if (handler) {
                if (pc + handler_operand_bytes[op] > num_opcodes) {
                    vm->halted = 1;
                    break;
                }
                handler(vm->regs, opcodes, pc);
            } else {
                vm->halted = 1;
            }
            pc++;
        }
    }
    vm->pc = pc;
    return vm->halted ? 1 : 0;
}
#endif

int simd_dispatch(SimdVmState *vm, const uint8_t *opcodes, size_t num_opcodes) {
    if (!vm || !opcodes || num_opcodes == 0) return -1;

#if defined(__x86_64__) && defined(__SSE4_1__)
    if (vm->use_simd) {
        return simd_dispatch_sse(vm, opcodes, num_opcodes);
    }
#endif

    return simd_dispatch_scalar(vm, opcodes, num_opcodes);
}

int simd_dispatch_scalar(SimdVmState *vm, const uint8_t *opcodes, size_t num_opcodes) {
    if (!vm || !opcodes) return -1;

    size_t pc = vm->pc;
    while (pc < num_opcodes && !vm->halted && vm->regs[14] < num_opcodes) {
        uint8_t op = opcodes[pc];
        op = (op < SIMD_VM_MAX_HANDLERS) ? op : 0;
        simd_handler_fn handler = vm->handlers[op];
        if (handler) {
            int advance;
            if (pc + handler_operand_bytes[op] > num_opcodes) {
                vm->halted = 1;
                break;
            }
            advance = handler(vm->regs, opcodes, pc);
            pc += (size_t)advance;
        } else {
            vm->halted = 1;
        }
    }
    vm->pc = pc;
    return vm->halted ? 1 : 0;
}
