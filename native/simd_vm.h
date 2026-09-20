#ifndef SIMD_VM_H
#define SIMD_VM_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define SIMD_VM_NUM_OPCODES 32
#define SIMD_VM_MAX_HANDLERS 32
#define SIMD_VM_NUM_REGS 16

typedef int (*simd_handler_fn)(uint64_t *regs, const uint8_t *opcodes, size_t pc);

typedef struct {
    uint64_t regs[SIMD_VM_NUM_REGS];
    uint8_t  memory[65536];
    size_t   pc;
    int      halted;
    simd_handler_fn handlers[SIMD_VM_MAX_HANDLERS];
    int      use_simd;
} SimdVmState;

int simd_dispatch(SimdVmState *vm, const uint8_t *opcodes, size_t num_opcodes);
int simd_dispatch_scalar(SimdVmState *vm, const uint8_t *opcodes, size_t num_opcodes);
int simd_opcode_decode(const uint8_t *opcodes, size_t num_opcodes, uint8_t *decoded, size_t *decoded_count);
int simd_available(void);
void simd_vm_init(SimdVmState *vm);

#ifdef __cplusplus
}
#endif

#endif /* SIMD_VM_H */
