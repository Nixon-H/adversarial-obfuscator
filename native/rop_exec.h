/* rop_exec.h — ROP chain executor (C runtime).
 *
 * Provides:
 *   - rop_execute()        — sets up stack with chain addresses and RETs through
 *   - rop_decrypt_chain()  — XOR-decrypt the chain blob
 *   - rop_chain_free()     — zeroes and frees chain memory
 *
 * On x86-64 the executor performs a stack-pivot: it saves RSP, points it at
 * the chain array, and issues a RET.  Each gadget address on the stack is
 * then consumed in sequence — each gadget does its work and RETs to the next.
 *
 * Usage:
 *   uint8_t  enc[] = { ... };            // encrypted ROP chain
 *   uint8_t  key[32] = { ... };
 *   uint64_t chain[1024];
 *   size_t   n = rop_decrypt_chain(enc, sizeof(enc), key, chain, 1024);
 *   uint64_t result = rop_execute(chain, n);
 */

#ifndef NIXON_ROP_EXEC_H
#define NIXON_ROP_EXEC_H

#include <stddef.h>
#include <stdint.h>
#include <string.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ─────────────────────────────────────────────
 * rop_decrypt_chain — XOR-decrypt a chain blob
 *   enc     : encrypted bytes
 *   enc_len : byte length (must be multiple of 8)
 *   key     : 32-byte XOR key
 *   out     : output buffer for decrypted addresses
 *   out_max : max number of uint64_t entries in out
 * Returns number of entries written, or 0 on error.
 * ───────────────────────────────────────────── */
static inline size_t rop_decrypt_chain(const uint8_t *enc, size_t enc_len,
                                       const uint8_t *key,
                                       uint64_t *out, size_t out_max) {
    if (!enc || !key || !out) return 0;
    if (enc_len == 0 || enc_len % 8 != 0) return 0;
    size_t count = enc_len / 8;
    if (count > out_max) return 0;

    for (size_t i = 0; i < enc_len; i++) {
        uint8_t dec = enc[i] ^ key[i % 32];
        ((uint8_t *)out)[i] = dec;
    }
    return count;
}

/* ─────────────────────────────────────────────
 * rop_execute — execute a ROP chain
 *   chain  : array of gadget addresses (stack frames)
 *   count  : number of entries
 * Returns the final value of RAX after execution.
 * The chain *must* end with a gadget whose last
 * instruction is `ret` (0xC3) to cleanly return.
 *
 * Implementation: stack-pivot then RET through chain.
 * ───────────────────────────────────────────── */
#if defined(__x86_64__) || defined(_M_X64)
#  if defined(_MSC_VER)
#    include <intrin.h>
#    pragma intrinsic(_ReadWriteBarrier)
#  endif

static inline uint64_t rop_execute(const uint64_t *chain, size_t count) {
    if (!chain || count == 0) return 0;

    uint64_t result = 0;
    /*
     * Stack pivot via inline asm:
     *   1. Save current RSP into R15
     *   2. Point RSP at the chain array
     *   3. Pop the first gadget address into a scratch reg
     *   4. On the final entry, RET will land at the chain's
     *      last gadget, which should be a `ret` (or we let
     *      control fall through to the caller's RET).
     *
     * Because we can't know at compile time where the chain
     * ends (the gadgets push/pop their own frames), we use
     * a simpler approach: push all addresses in reverse order
     * onto the stack (so the first address is on top), then RET.
     */
    __asm__ volatile (
        "movq   %%rsp, %%r15\n"          /* save caller RSP   */
        "movq   %[chain_ptr], %%rax\n"    /* RAX = chain base  */
        "movq   %[count], %%rcx\n"        /* RCX = count       */
        "leaq   (%%rax,%%rcx,8), %%rsp\n" /* RSP past last entry */
        "subq   $8, %%rsp\n"              /* point at last entry   */
        "std\n"                           /* go backwards          */
        "1:\n"
        "lodsq\n"                         /* load address, RSP-=8 */
        "pushq  %%rax\n"                  /* push onto "real" stack */
        "loop   1b\n"                     /* loop for all entries */
        "cld\n"
        "movq   %%r15, %%rsp\n"           /* restore RSP ...     */
        "subq   %[disp], %%rsp\n"         /* ... past pushes     */
        "retq\n"                          /* enter the chain!    */
        "movq   %%r15, %%rsp\n"           /* restore on return   */
        : "=a" (result)
        : [chain_ptr] "r" (chain),
          [count] "r" (count),
          [disp] "r" (count * 8)
        : "rcx", "r15", "memory", "cc"
    );

    return result;
}
#elif defined(__aarch64__)
static inline uint64_t rop_execute(const uint64_t *chain, size_t count) {
    (void)chain;
    (void)count;
    return 0;
}
#else
static inline uint64_t rop_execute(const uint64_t *chain, size_t count) {
    (void)chain;
    (void)count;
    return 0;
}
#endif

/* ─────────────────────────────────────────────
 * rop_chain_free — securely zero a chain buffer
 * ───────────────────────────────────────────── */
static inline void rop_chain_free(volatile uint64_t *chain, size_t count) {
    if (!chain) return;
    for (size_t i = 0; i < count; i++) {
        chain[i] = 0;
    }
}

/* ─────────────────────────────────────────────
 * rop_load_chain — convenience: decrypt + execute
 *   enc, enc_len, key : as in rop_decrypt_chain
 *   scratch           : buffer for decrypted chain
 *   scratch_max       : max entries in scratch
 * Returns RAX result, or 0 on failure.
 * ───────────────────────────────────────────── */
static inline uint64_t rop_load_and_exec(const uint8_t *enc, size_t enc_len,
                                         const uint8_t *key,
                                         uint64_t *scratch, size_t scratch_max) {
    size_t n = rop_decrypt_chain(enc, enc_len, key, scratch, scratch_max);
    if (n == 0) return 0;
    uint64_t result = rop_execute(scratch, n);
    rop_chain_free(scratch, n);
    return result;
}

#ifdef __cplusplus
}
#endif

#endif /* NIXON_ROP_EXEC_H */
