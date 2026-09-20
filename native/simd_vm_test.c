#include "simd_vm.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int g_failed = 0;

#define TEST(name, expr) do { \
    if (!(expr)) { \
        fprintf(stderr, "FAIL: %s\n", name); \
        g_failed = 1; \
    } else { \
        printf("PASS: %s\n", name); \
    } \
} while(0)

int main(void) {
    int avail = simd_available();
    printf("simd_available() = %d\n", avail);

    SimdVmState vm;
    simd_vm_init(&vm);
    TEST("init pc == 0", vm.pc == 0);
    TEST("init halted == 0", vm.halted == 0);

    uint8_t opcodes[] = {0, 1, 2, 10, 3};
    uint8_t decoded[16] = {0};
    size_t decoded_count = 0;
    int ret = simd_opcode_decode(opcodes, 5, decoded, &decoded_count);
    TEST("decode returns 0", ret == 0);
    TEST("decode count == 5", decoded_count == 5);
    TEST("decode op0 valid", decoded[0] == 1);
    TEST("decode op3 invalid (opcode 10 out of range)", decoded[3] == 0);

    simd_vm_init(&vm);
    uint8_t prog_nop[] = {0};
    ret = simd_dispatch_scalar(&vm, prog_nop, 1);
    TEST("scalar nop returns 0", ret == 0);
    TEST("scalar nop advances pc", vm.pc == 1);

    simd_vm_init(&vm);
    vm.regs[0] = 5;
    vm.regs[1] = 10;
    uint8_t prog_add[] = {1, 0x00, 0x11};
    ret = simd_dispatch_scalar(&vm, prog_add, 3);
    TEST("scalar add returns 0", ret == 0);

    simd_vm_init(&vm);
    vm.regs[0] = 20;
    vm.regs[1] = 7;
    uint8_t prog_sub[] = {2, 0x00, 0x11};
    ret = simd_dispatch_scalar(&vm, prog_sub, 3);
    TEST("scalar sub returns 0", ret == 0);

    simd_vm_init(&vm);
    vm.regs[0] = 6;
    vm.regs[1] = 7;
    uint8_t prog_mul[] = {3, 0x00, 0x11};
    ret = simd_dispatch_scalar(&vm, prog_mul, 3);
    TEST("scalar mul returns 0", ret == 0);

    simd_vm_init(&vm);
    vm.regs[0] = 0xFF;
    vm.regs[1] = 0x0F;
    uint8_t prog_xor[] = {4, 0x00, 0x11};
    ret = simd_dispatch_scalar(&vm, prog_xor, 3);
    TEST("scalar xor returns 0", ret == 0);

    simd_vm_init(&vm);
    vm.regs[0] = 0xFF;
    vm.regs[1] = 0x0F;
    uint8_t prog_and[] = {5, 0x00, 0x11};
    ret = simd_dispatch_scalar(&vm, prog_and, 3);
    TEST("scalar and returns 0", ret == 0);

    simd_vm_init(&vm);
    vm.regs[0] = 0xF0;
    vm.regs[1] = 0x0F;
    uint8_t prog_or[] = {6, 0x00, 0x11};
    ret = simd_dispatch_scalar(&vm, prog_or, 3);
    TEST("scalar or returns 0", ret == 0);

    simd_vm_init(&vm);
    uint8_t prog_nop_dispatch[] = {0};
    ret = simd_dispatch(&vm, prog_nop_dispatch, 1);
    TEST("dispatch nop returns 0", ret == 0);

    return g_failed ? 1 : 0;
}
