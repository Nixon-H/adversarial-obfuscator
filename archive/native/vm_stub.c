#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/syscall.h>

#if defined(_WIN32) || defined(_WIN64)
#define VM_EXPORT __declspec(dllexport)
#else
#define VM_EXPORT __attribute__((visibility("default")))
#endif

#define VM_NUM_REGS 16
#define VM_REG_PC   14
#define VM_REG_FLAGS 13
#define VM_REG_SP   15
#define VM_MEM_SIZE (64 * 1024)
#define VM_STACK_SIZE 4096

#define VM_FLAG_ZERO  1
#define VM_FLAG_SIGN  2
#define VM_FLAG_CARRY 4

#define VM_REKEY_INTERVAL 1000
#define VM_OPCODE_REKEY   255

#define VM_SHUFFLE_BUF_SIZE 32

struct sha256_ctx {
    uint8_t data[64];
    uint32_t datalen;
    uint64_t bitlen;
    uint32_t state[8];
};

static const uint32_t SHA256_K[64] = {
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
    0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
    0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
    0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
    0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
    0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
};

#define ROTLEFT(a,b) (((a) << (b)) | ((a) >> (32-(b))))
#define ROTRIGHT(a,b) (((a) >> (b)) | ((a) << (32-(b))))
#define CH(x,y,z) (((x) & (y)) ^ (~(x) & (z)))
#define MAJ(x,y,z) (((x) & (y)) ^ ((x) & (z)) ^ ((y) & (z)))
#define EP0(x) (ROTRIGHT(x,2) ^ ROTRIGHT(x,13) ^ ROTRIGHT(x,22))
#define EP1(x) (ROTRIGHT(x,6) ^ ROTRIGHT(x,11) ^ ROTRIGHT(x,25))
#define SIG0(x) (ROTRIGHT(x,7) ^ ROTRIGHT(x,18) ^ ((x) >> 3))
#define SIG1(x) (ROTRIGHT(x,17) ^ ROTRIGHT(x,19) ^ ((x) >> 10))

static void sha256_transform(struct sha256_ctx *ctx, const uint8_t data[]) {
    uint32_t m[64], a, b, c, d, e, f, g, h, t1, t2;
    for (int i = 0, j = 0; i < 16; i++, j += 4)
        m[i] = ((uint32_t)data[j] << 24) | ((uint32_t)data[j+1] << 16) | ((uint32_t)data[j+2] << 8) | (uint32_t)data[j+3];
    for (int i = 16; i < 64; i++)
        m[i] = SIG1(m[i-2]) + m[i-7] + SIG0(m[i-15]) + m[i-16];
    a = ctx->state[0]; b = ctx->state[1]; c = ctx->state[2]; d = ctx->state[3];
    e = ctx->state[4]; f = ctx->state[5]; g = ctx->state[6]; h = ctx->state[7];
    for (int i = 0; i < 64; i++) {
        t1 = h + EP1(e) + CH(e,f,g) + SHA256_K[i] + m[i];
        t2 = EP0(a) + MAJ(a,b,c);
        h = g; g = f; f = e; e = d + t1; d = c; c = b; b = a; a = t1 + t2;
    }
    ctx->state[0] += a; ctx->state[1] += b; ctx->state[2] += c; ctx->state[3] += d;
    ctx->state[4] += e; ctx->state[5] += f; ctx->state[6] += g; ctx->state[7] += h;
}

static void sha256_init(struct sha256_ctx *ctx) {
    ctx->datalen = 0;
    ctx->bitlen = 0;
    ctx->state[0] = 0x6a09e667; ctx->state[1] = 0xbb67ae85;
    ctx->state[2] = 0x3c6ef372; ctx->state[3] = 0xa54ff53a;
    ctx->state[4] = 0x510e527f; ctx->state[5] = 0x9b05688c;
    ctx->state[6] = 0x1f83d9ab; ctx->state[7] = 0x5be0cd19;
}

static void sha256_update(struct sha256_ctx *ctx, const uint8_t *data, size_t len) {
    for (size_t i = 0; i < len; i++) {
        ctx->data[ctx->datalen++] = data[i];
        ctx->bitlen += 8;
        if (ctx->datalen == 64) {
            sha256_transform(ctx, ctx->data);
            ctx->datalen = 0;
        }
    }
}

static void sha256_final(struct sha256_ctx *ctx, uint8_t hash[32]) {
    ctx->data[ctx->datalen++] = 0x80;
    while (ctx->datalen != 56) {
        if (ctx->datalen == 64) {
            sha256_transform(ctx, ctx->data);
            ctx->datalen = 0;
        }
        ctx->data[ctx->datalen++] = 0;
    }
    for (int i = 7; i >= 0; i--)
        ctx->data[56 + i] = (uint8_t)((ctx->bitlen >> (i * 8)) & 0xFF);
    sha256_transform(ctx, ctx->data);
    for (int i = 0; i < 4; i++) {
        hash[i*4]   = (uint8_t)((ctx->state[i] >> 24) & 0xFF);
        hash[i*4+1] = (uint8_t)((ctx->state[i] >> 16) & 0xFF);
        hash[i*4+2] = (uint8_t)((ctx->state[i] >> 8) & 0xFF);
        hash[i*4+3] = (uint8_t)(ctx->state[i] & 0xFF);
    }
    for (int i = 4; i < 8; i++) {
        hash[i*4]   = (uint8_t)((ctx->state[i] >> 24) & 0xFF);
        hash[i*4+1] = (uint8_t)((ctx->state[i] >> 16) & 0xFF);
        hash[i*4+2] = (uint8_t)((ctx->state[i] >> 8) & 0xFF);
        hash[i*4+3] = (uint8_t)(ctx->state[i] & 0xFF);
    }
}

void sha256_hash(const uint8_t *data, size_t len, uint8_t hash[32]) {
    struct sha256_ctx ctx;
    sha256_init(&ctx);
    sha256_update(&ctx, data, len);
    sha256_final(&ctx, hash);
}

void sha256_hash2(const uint8_t *d1, size_t l1, const uint8_t *d2, size_t l2, uint8_t hash[32]) {
    struct sha256_ctx ctx;
    sha256_init(&ctx);
    sha256_update(&ctx, d1, l1);
    sha256_update(&ctx, d2, l2);
    sha256_final(&ctx, hash);
}

static uint32_t __attribute__((unused)) read_le32(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static void runtime_collect_entropy(uint8_t seed[32]) {
    struct sha256_ctx ctx;
    sha256_init(&ctx);

    uint8_t buf[4096];
    ssize_t n;

    int fd = open("/proc/self/maps", O_RDONLY);
    if (fd >= 0) {
        while ((n = read(fd, buf, sizeof(buf))) > 0)
            sha256_update(&ctx, buf, (size_t)n);
        close(fd);
    }

    fd = open("/proc/self/status", O_RDONLY);
    if (fd >= 0) {
        while ((n = read(fd, buf, sizeof(buf))) > 0)
            sha256_update(&ctx, buf, (size_t)n);
        close(fd);
    }

    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);
    sha256_update(&ctx, (const uint8_t*)&ts, sizeof(ts));
    clock_gettime(CLOCK_MONOTONIC, &ts);
    sha256_update(&ctx, (const uint8_t*)&ts, sizeof(ts));

    long tid = syscall(SYS_gettid);
    sha256_update(&ctx, (const uint8_t*)&tid, sizeof(tid));

    if (gethostname((char*)buf, sizeof(buf)) == 0) {
        size_t hlen = strnlen((const char*)buf, sizeof(buf));
        sha256_update(&ctx, buf, hlen);
    }

    fd = open("/dev/urandom", O_RDONLY);
    if (fd >= 0) {
        uint8_t rand_buf[32];
        if (read(fd, rand_buf, sizeof(rand_buf)) == sizeof(rand_buf))
            sha256_update(&ctx, rand_buf, sizeof(rand_buf));
        close(fd);
    }

    sha256_final(&ctx, seed);
}

static void vm_derive_isa(const uint8_t seed[32], uint8_t mapping[256]) {
    for (int i = 0; i < 256; i++)
        mapping[i] = (uint8_t)i;

    uint8_t state[32];
    memcpy(state, seed, 32);

    for (int i = 254; i > 0; i--) {
        uint8_t hash[32];
        sha256_hash(state, 32, hash);
        memcpy(state, hash, 32);
        int j = hash[0] % (i + 1);
        uint8_t tmp = mapping[i];
        mapping[i] = mapping[j];
        mapping[j] = tmp;
    }

    mapping[255] = 255;
}

/* ── Self-Mutating ISA: types ─────────────────────────────────────── */

typedef enum {
    DISPATCH_SWITCH = 0,
    DISPATCH_INDIRECT = 1,
    DISPATCH_COMPUTED_GOTO = 2,
} dispatch_mode_t;

typedef enum {
    ENCODING_FIXED = 0,
    ENCODING_VARIABLE = 1,
    ENCODING_FIELD_SHUFFLE = 2,
} encoding_mode_t;

struct vm_state;
typedef void (*handler_fn_t)(struct vm_state *vm, const uint8_t *bc, size_t bc_len);

struct vm_handler_slot {
    uint8_t opcode;
    handler_fn_t fn;
};

#define VM_NUM_IMPL_HANDLERS 24

/* ── Forward declarations of handler functions ────────────────────── */

static void vm_handle_nop(struct vm_state *vm, const uint8_t *bc, size_t bc_len);
static void vm_handle_add(struct vm_state *vm, const uint8_t *bc, size_t bc_len);
static void vm_handle_sub(struct vm_state *vm, const uint8_t *bc, size_t bc_len);
static void vm_handle_mul(struct vm_state *vm, const uint8_t *bc, size_t bc_len);
static void vm_handle_div(struct vm_state *vm, const uint8_t *bc, size_t bc_len);
static void vm_handle_mod(struct vm_state *vm, const uint8_t *bc, size_t bc_len);
static void vm_handle_and(struct vm_state *vm, const uint8_t *bc, size_t bc_len);
static void vm_handle_or(struct vm_state *vm, const uint8_t *bc, size_t bc_len);
static void vm_handle_xor(struct vm_state *vm, const uint8_t *bc, size_t bc_len);
static void vm_handle_not(struct vm_state *vm, const uint8_t *bc, size_t bc_len);
static void vm_handle_shl(struct vm_state *vm, const uint8_t *bc, size_t bc_len);
static void vm_handle_shr(struct vm_state *vm, const uint8_t *bc, size_t bc_len);
static void vm_handle_load(struct vm_state *vm, const uint8_t *bc, size_t bc_len);
static void vm_handle_store(struct vm_state *vm, const uint8_t *bc, size_t bc_len);
static void vm_handle_mov(struct vm_state *vm, const uint8_t *bc, size_t bc_len);
static void vm_handle_jmp(struct vm_state *vm, const uint8_t *bc, size_t bc_len);
static void vm_handle_jz(struct vm_state *vm, const uint8_t *bc, size_t bc_len);
static void vm_handle_jnz(struct vm_state *vm, const uint8_t *bc, size_t bc_len);
static void vm_handle_call(struct vm_state *vm, const uint8_t *bc, size_t bc_len);
static void vm_handle_ret(struct vm_state *vm, const uint8_t *bc, size_t bc_len);
static void vm_handle_push(struct vm_state *vm, const uint8_t *bc, size_t bc_len);
static void vm_handle_pop(struct vm_state *vm, const uint8_t *bc, size_t bc_len);
static void vm_handle_fused_cmp_jmp(struct vm_state *vm, const uint8_t *bc, size_t bc_len);
static void vm_handle_default(struct vm_state *vm, const uint8_t *bc, size_t bc_len);

/* ── Operand byte counts per logical opcode (for field shuffle) ──── */

static const uint8_t VM_OPCODE_OPERAND_BYTES[256] = {
    [0] = 0, [1] = 2, [2] = 2, [3] = 2, [4] = 2, [5] = 2,
    [6] = 2, [7] = 2, [8] = 2, [9] = 1, [10] = 2, [11] = 2,
    [12] = 2, [13] = 2, [14] = 3, [15] = 2,
    [16] = 4, [17] = 4, [18] = 4, [19] = 4, [20] = 4, [21] = 4, [22] = 4,
    [23] = 4, [24] = 0, [25] = 1, [26] = 1,
    [27] = 3, [28] = 0, [29] = 3, [30] = 3, [31] = 3, [32] = 3,
    [33] = 3, [34] = 9,
    [255] = 0,
};

/* ── vm_state with self-mutating ISA fields ───────────────────────── */

struct vm_state {
    uint64_t regs[VM_NUM_REGS];
    uint8_t  memory[VM_MEM_SIZE];
    uint64_t stack[VM_STACK_SIZE];
    size_t   sp;
    int      halted;
    uint8_t  isa_table[256];
    uint8_t  seed[32];
    int      epoch;
    int      steps_until_rekey;
    uint64_t bb_hash;

    /* Self-mutating ISA */
    struct vm_handler_slot handlers[VM_NUM_IMPL_HANDLERS];
    handler_fn_t dispatch[256];
    dispatch_mode_t dispatch_mode;
    encoding_mode_t encoding_mode;
    uint8_t field_perm[VM_SHUFFLE_BUF_SIZE];
    uint8_t shuffle_buf[VM_SHUFFLE_BUF_SIZE];
    int     shuffle_len;
    int     shuffle_pos;
    int     shuffle_active;
    uint8_t variable_instr_len;
    int     cfg_path_selector;
    uint8_t state_isa_state[32];
    uint8_t exec_history[64];
    int     exec_history_len;
    int     state_isa_rotation_offset;
};

/* ── Initial handler table ────────────────────────────────────────── */

static void vm_init_handlers(struct vm_state *vm) {
    struct vm_handler_slot slots[VM_NUM_IMPL_HANDLERS] = {
        {0, vm_handle_nop},
        {1, vm_handle_add},
        {2, vm_handle_sub},
        {3, vm_handle_mul},
        {4, vm_handle_div},
        {5, vm_handle_mod},
        {6, vm_handle_and},
        {7, vm_handle_or},
        {8, vm_handle_xor},
        {9, vm_handle_not},
        {10, vm_handle_shl},
        {11, vm_handle_shr},
        {12, vm_handle_load},
        {13, vm_handle_store},
        {14, vm_handle_mov},
        {16, vm_handle_jmp},
        {17, vm_handle_jz},
        {18, vm_handle_jnz},
        {23, vm_handle_call},
        {24, vm_handle_ret},
        {25, vm_handle_push},
        {26, vm_handle_pop},
        {34, vm_handle_fused_cmp_jmp},
        {255, vm_handle_default},
    };
    memcpy(vm->handlers, slots, sizeof(slots));
}

/* ── Handler table shuffling (Fisher-Yates) ──────────────────────── */

static void vm_shuffle_handlers(struct vm_state *vm, const uint8_t seed[32]) {
    uint8_t state[32];
    memcpy(state, seed, 32);

    for (int i = VM_NUM_IMPL_HANDLERS - 1; i > 0; i--) {
        uint8_t hash[32];
        sha256_hash(state, 32, hash);
        memcpy(state, hash, 32);
        int j = hash[0] % (i + 1);
        struct vm_handler_slot tmp = vm->handlers[i];
        vm->handlers[i] = vm->handlers[j];
        vm->handlers[j] = tmp;
    }
}

/* ── Rebuild dispatch table from shuffled handlers ───────────────── */

static void vm_rebuild_dispatch(struct vm_state *vm) {
    for (int i = 0; i < 256; i++)
        vm->dispatch[i] = vm_handle_default;

    for (int i = 0; i < VM_NUM_IMPL_HANDLERS; i++) {
        uint8_t op = vm->handlers[i].opcode;
        vm->dispatch[op] = vm->handlers[i].fn;
    }
}

/* ── Select dispatch mode from entropy seed + epoch ───────────────── */

static void vm_select_dispatch_mode(struct vm_state *vm, const uint8_t seed[32], int epoch) {
    uint8_t input[64];
    memcpy(input, seed, 32);
    input[32] = (uint8_t)(epoch & 0xFF);
    input[33] = (uint8_t)((epoch >> 8) & 0xFF);
    input[34] = (uint8_t)((epoch >> 16) & 0xFF);
    input[35] = (uint8_t)((epoch >> 24) & 0xFF);
    input[36] = 0xDD;

    uint8_t hash[32];
    sha256_hash(input, 37, hash);
    int mode = hash[0] % 3;
    vm->dispatch_mode = (dispatch_mode_t)mode;
}

/* ── Select encoding mode from entropy seed + epoch ───────────────── */

static void vm_select_encoding_mode(struct vm_state *vm, const uint8_t seed[32], int epoch) {
    uint8_t input[64];
    memcpy(input, seed, 32);
    input[32] = (uint8_t)(epoch & 0xFF);
    input[33] = (uint8_t)((epoch >> 8) & 0xFF);
    input[34] = (uint8_t)((epoch >> 16) & 0xFF);
    input[35] = (uint8_t)((epoch >> 24) & 0xFF);
    input[36] = 0xEE;

    uint8_t hash[32];
    sha256_hash(input, 37, hash);
    int mode = hash[0] % 3;
    vm->encoding_mode = (encoding_mode_t)mode;
}

/* ── Derive field permutation for field shuffle encoding ──────────── */

static void vm_derive_field_perm(struct vm_state *vm, const uint8_t seed[32], int epoch) {
    uint8_t state[32];
    uint8_t input[64];
    memcpy(input, seed, 32);
    input[32] = (uint8_t)(epoch & 0xFF);
    input[33] = (uint8_t)((epoch >> 8) & 0xFF);
    input[34] = (uint8_t)((epoch >> 16) & 0xFF);
    input[35] = (uint8_t)((epoch >> 24) & 0xFF);
    input[36] = 0xFF;

    sha256_hash(input, 37, state);

    uint8_t perm[VM_SHUFFLE_BUF_SIZE];
    for (int i = 0; i < VM_SHUFFLE_BUF_SIZE; i++)
        perm[i] = (uint8_t)i;

    for (int i = VM_SHUFFLE_BUF_SIZE - 1; i > 0; i--) {
        uint8_t hash[32];
        sha256_hash(state, 32, hash);
        memcpy(state, hash, 32);
        int j = hash[0] % (i + 1);
        uint8_t t = perm[i];
        perm[i] = perm[j];
        perm[j] = t;
    }

    memcpy(vm->field_perm, perm, VM_SHUFFLE_BUF_SIZE);
}

/* ── Initialize self-mutating ISA at VM start ─────────────────────── */

static void vm_init_mutating_isa(struct vm_state *vm, const uint8_t seed[32]) {
    vm_init_handlers(vm);
    vm_shuffle_handlers(vm, seed);
    vm_rebuild_dispatch(vm);
    vm_select_dispatch_mode(vm, seed, vm->epoch);
    vm_select_encoding_mode(vm, seed, vm->epoch);
    vm_derive_field_perm(vm, seed, vm->epoch);
    vm->shuffle_active = 0;
    vm->shuffle_len = 0;
    vm->shuffle_pos = 0;
    vm->variable_instr_len = 0;
}

/* ── Rekey with self-mutating ISA rotation ────────────────────────── */

static void vm_rekey(struct vm_state *vm, uint64_t bb_hash) {
    uint8_t new_seed[32];
    struct sha256_ctx ctx;
    sha256_init(&ctx);
    sha256_update(&ctx, vm->seed, 32);
    uint8_t epoch_data[4];
    epoch_data[0] = (uint8_t)(vm->epoch & 0xFF);
    epoch_data[1] = (uint8_t)((vm->epoch >> 8) & 0xFF);
    epoch_data[2] = (uint8_t)((vm->epoch >> 16) & 0xFF);
    epoch_data[3] = (uint8_t)((vm->epoch >> 24) & 0xFF);
    sha256_update(&ctx, epoch_data, 4);
    sha256_update(&ctx, (const uint8_t*)&bb_hash, sizeof(bb_hash));
    sha256_final(&ctx, new_seed);

    memcpy(vm->seed, new_seed, 32);
    vm->epoch++;
    vm_derive_isa(vm->seed, vm->isa_table);

    /* Rotate handler order, dispatch mode, encoding mode */
    vm_shuffle_handlers(vm, vm->seed);
    vm_rebuild_dispatch(vm);
    vm_select_dispatch_mode(vm, vm->seed, vm->epoch);
    vm_select_encoding_mode(vm, vm->seed, vm->epoch);
    vm_derive_field_perm(vm, vm->seed, vm->epoch);
}

/* ── Bytecode reading (encoding-aware) ────────────────────────────── */

static uint8_t vm_read_byte(struct vm_state *vm, const uint8_t *bc, size_t bc_len) {
    if (vm->shuffle_active) {
        if (vm->shuffle_pos >= vm->shuffle_len) {
            vm->halted = 1;
            return 0;
        }
        return vm->shuffle_buf[vm->shuffle_pos++];
    }

    size_t pc = (size_t)vm->regs[VM_REG_PC];
    if (pc >= bc_len) {
        vm->halted = 1;
        return 0;
    }
    vm->regs[VM_REG_PC] = (uint64_t)(pc + 1);
    uint8_t val = bc[pc];
    vm->bb_hash = ((vm->bb_hash << 5) + vm->bb_hash) ^ (uint64_t)val;
    return val;
}

static uint32_t vm_read_u32(struct vm_state *vm, const uint8_t *bc, size_t bc_len) {
    uint32_t val = 0;
    for (int i = 0; i < 4; i++)
        val |= (uint32_t)vm_read_byte(vm, bc, bc_len) << (i * 8);
    return val;
}

static uint8_t vm_read_reg(struct vm_state *vm, const uint8_t *bc, size_t bc_len) {
    return vm_read_byte(vm, bc, bc_len) & 0x0F;
}

static inline uint64_t vm_get_reg(struct vm_state *vm, uint8_t idx) {
    if (idx < VM_NUM_REGS) return vm->regs[idx];
    return 0;
}

static inline void vm_set_reg(struct vm_state *vm, uint8_t idx, uint64_t val) {
    if (idx < VM_NUM_REGS) vm->regs[idx] = val;
}

static void vm_set_flags(struct vm_state *vm, uint64_t result) {
    uint64_t flags = 0;
    if (result == 0) flags |= VM_FLAG_ZERO;
    if (result & 0x8000000000000000ULL) flags |= VM_FLAG_SIGN;
    vm_set_reg(vm, VM_REG_FLAGS, flags);
}

/* ── Prepare field shuffle: read raw operand bytes, de-permute ────── */

static void vm_prepare_field_shuffle(struct vm_state *vm, const uint8_t *bc, size_t bc_len, uint8_t logical_opcode) {
    int n_op = (int)VM_OPCODE_OPERAND_BYTES[logical_opcode];
    if (n_op > VM_SHUFFLE_BUF_SIZE)
        n_op = VM_SHUFFLE_BUF_SIZE;

    uint8_t raw[VM_SHUFFLE_BUF_SIZE];
    for (int i = 0; i < n_op; i++) {
        size_t pc = (size_t)vm->regs[VM_REG_PC];
        if (pc >= bc_len) {
            vm->halted = 1;
            return;
        }
        raw[i] = bc[pc];
        vm->regs[VM_REG_PC] = (uint64_t)(pc + 1);
        vm->bb_hash = ((vm->bb_hash << 5) + vm->bb_hash) ^ (uint64_t)raw[i];
    }

    /* Apply inverse field permutation */
    uint8_t unshuffled[VM_SHUFFLE_BUF_SIZE];
    memset(unshuffled, 0, VM_SHUFFLE_BUF_SIZE);
    for (int i = 0; i < n_op; i++) {
        int src_idx = (int)vm->field_perm[i];
        if (src_idx < n_op)
            unshuffled[src_idx] = raw[i];
        else
            unshuffled[i] = raw[i];
    }

    memcpy(vm->shuffle_buf, unshuffled, (size_t)n_op);
    vm->shuffle_len = n_op;
    vm->shuffle_pos = 0;
    vm->shuffle_active = 1;
}

/* ── Handler implementations ──────────────────────────────────────── */

static void vm_handle_nop(struct vm_state *vm, const uint8_t *bc, size_t bc_len) {
    (void)vm; (void)bc; (void)bc_len;
}

static void vm_handle_add(struct vm_state *vm, const uint8_t *bc, size_t bc_len) {
    uint8_t d = vm_read_reg(vm, bc, bc_len);
    uint8_t s = vm_read_reg(vm, bc, bc_len);
    uint64_t a = vm_get_reg(vm, d);
    uint64_t b = vm_get_reg(vm, s);
    uint64_t r = a + b;
    vm_set_reg(vm, d, r);
    vm_set_flags(vm, r);
}

static void vm_handle_sub(struct vm_state *vm, const uint8_t *bc, size_t bc_len) {
    uint8_t d = vm_read_reg(vm, bc, bc_len);
    uint8_t s = vm_read_reg(vm, bc, bc_len);
    uint64_t a = vm_get_reg(vm, d);
    uint64_t b = vm_get_reg(vm, s);
    uint64_t r = a - b;
    vm_set_reg(vm, d, r);
    vm_set_flags(vm, r);
}

static void vm_handle_mul(struct vm_state *vm, const uint8_t *bc, size_t bc_len) {
    uint8_t d = vm_read_reg(vm, bc, bc_len);
    uint8_t s = vm_read_reg(vm, bc, bc_len);
    uint64_t a = vm_get_reg(vm, d);
    uint64_t b = vm_get_reg(vm, s);
    uint64_t r = a * b;
    vm_set_reg(vm, d, r);
    vm_set_flags(vm, r);
}

static void vm_handle_div(struct vm_state *vm, const uint8_t *bc, size_t bc_len) {
    uint8_t d = vm_read_reg(vm, bc, bc_len);
    uint8_t s = vm_read_reg(vm, bc, bc_len);
    uint64_t a = vm_get_reg(vm, d);
    uint64_t b = vm_get_reg(vm, s);
    if (b == 0) { vm->halted = 1; return; }
    uint64_t r = a / b;
    vm_set_reg(vm, d, r);
    vm_set_flags(vm, r);
}

static void vm_handle_mod(struct vm_state *vm, const uint8_t *bc, size_t bc_len) {
    uint8_t d = vm_read_reg(vm, bc, bc_len);
    uint8_t s = vm_read_reg(vm, bc, bc_len);
    uint64_t a = vm_get_reg(vm, d);
    uint64_t b = vm_get_reg(vm, s);
    if (b == 0) { vm->halted = 1; return; }
    uint64_t r = a % b;
    vm_set_reg(vm, d, r);
    vm_set_flags(vm, r);
}

static void vm_handle_and(struct vm_state *vm, const uint8_t *bc, size_t bc_len) {
    uint8_t d = vm_read_reg(vm, bc, bc_len);
    uint8_t s = vm_read_reg(vm, bc, bc_len);
    vm_set_reg(vm, d, vm_get_reg(vm, d) & vm_get_reg(vm, s));
    vm_set_flags(vm, vm_get_reg(vm, d));
}

static void vm_handle_or(struct vm_state *vm, const uint8_t *bc, size_t bc_len) {
    uint8_t d = vm_read_reg(vm, bc, bc_len);
    uint8_t s = vm_read_reg(vm, bc, bc_len);
    vm_set_reg(vm, d, vm_get_reg(vm, d) | vm_get_reg(vm, s));
    vm_set_flags(vm, vm_get_reg(vm, d));
}

static void vm_handle_xor(struct vm_state *vm, const uint8_t *bc, size_t bc_len) {
    uint8_t d = vm_read_reg(vm, bc, bc_len);
    uint8_t s = vm_read_reg(vm, bc, bc_len);
    vm_set_reg(vm, d, vm_get_reg(vm, d) ^ vm_get_reg(vm, s));
    vm_set_flags(vm, vm_get_reg(vm, d));
}

static void vm_handle_not(struct vm_state *vm, const uint8_t *bc, size_t bc_len) {
    uint8_t d = vm_read_reg(vm, bc, bc_len);
    vm_set_reg(vm, d, ~vm_get_reg(vm, d));
    vm_set_flags(vm, vm_get_reg(vm, d));
}

static void vm_handle_shl(struct vm_state *vm, const uint8_t *bc, size_t bc_len) {
    uint8_t d = vm_read_reg(vm, bc, bc_len);
    uint8_t s = vm_read_reg(vm, bc, bc_len);
    uint64_t shift = vm_get_reg(vm, s) & 63;
    vm_set_reg(vm, d, vm_get_reg(vm, d) << shift);
    vm_set_flags(vm, vm_get_reg(vm, d));
}

static void vm_handle_shr(struct vm_state *vm, const uint8_t *bc, size_t bc_len) {
    uint8_t d = vm_read_reg(vm, bc, bc_len);
    uint8_t s = vm_read_reg(vm, bc, bc_len);
    uint64_t shift = vm_get_reg(vm, s) & 63;
    vm_set_reg(vm, d, vm_get_reg(vm, d) >> shift);
    vm_set_flags(vm, vm_get_reg(vm, d));
}

static void vm_handle_load(struct vm_state *vm, const uint8_t *bc, size_t bc_len) {
    uint8_t d = vm_read_reg(vm, bc, bc_len);
    uint8_t a = vm_read_reg(vm, bc, bc_len);
    uint64_t addr = vm_get_reg(vm, a);
    if (addr < VM_MEM_SIZE)
        vm_set_reg(vm, d, (uint64_t)vm->memory[addr]);
    else
        vm->halted = 1;
}

static void vm_handle_store(struct vm_state *vm, const uint8_t *bc, size_t bc_len) {
    uint8_t s = vm_read_reg(vm, bc, bc_len);
    uint8_t a = vm_read_reg(vm, bc, bc_len);
    uint64_t addr = vm_get_reg(vm, a);
    if (addr < VM_MEM_SIZE)
        vm->memory[addr] = (uint8_t)(vm_get_reg(vm, s) & 0xFF);
    else
        vm->halted = 1;
}

static void vm_handle_mov(struct vm_state *vm, const uint8_t *bc, size_t bc_len) {
    uint8_t d = vm_read_reg(vm, bc, bc_len);
    uint8_t lo = vm_read_byte(vm, bc, bc_len);
    uint8_t hi = vm_read_byte(vm, bc, bc_len);
    vm_set_reg(vm, d, (uint64_t)((hi << 8) | lo));
}

static void vm_handle_jmp(struct vm_state *vm, const uint8_t *bc, size_t bc_len) {
    uint32_t target = vm_read_u32(vm, bc, bc_len);
    vm_set_reg(vm, VM_REG_PC, (uint64_t)target);
    vm->cfg_path_selector = (int)(vm->bb_hash ^ (uint64_t)target);
}

static void vm_handle_jz(struct vm_state *vm, const uint8_t *bc, size_t bc_len) {
    uint32_t target = vm_read_u32(vm, bc, bc_len);
    if (vm_get_reg(vm, VM_REG_FLAGS) & VM_FLAG_ZERO)
        vm_set_reg(vm, VM_REG_PC, (uint64_t)target);
    vm->cfg_path_selector = (int)(vm->bb_hash ^ (uint64_t)target);
}

static void vm_handle_jnz(struct vm_state *vm, const uint8_t *bc, size_t bc_len) {
    uint32_t target = vm_read_u32(vm, bc, bc_len);
    if (!(vm_get_reg(vm, VM_REG_FLAGS) & VM_FLAG_ZERO))
        vm_set_reg(vm, VM_REG_PC, (uint64_t)target);
    vm->cfg_path_selector = (int)(vm->bb_hash ^ (uint64_t)target);
}

static void vm_handle_call(struct vm_state *vm, const uint8_t *bc, size_t bc_len) {
    uint32_t target = vm_read_u32(vm, bc, bc_len);
    if (vm->sp < VM_STACK_SIZE)
        vm->stack[vm->sp++] = vm_get_reg(vm, VM_REG_PC);
    vm_set_reg(vm, VM_REG_PC, (uint64_t)target);
}

static void vm_handle_ret(struct vm_state *vm, const uint8_t *bc, size_t bc_len) {
    (void)bc; (void)bc_len;
    if (vm->sp > 0)
        vm_set_reg(vm, VM_REG_PC, vm->stack[--vm->sp]);
    else
        vm->halted = 1;
}

static void vm_handle_push(struct vm_state *vm, const uint8_t *bc, size_t bc_len) {
    uint8_t s = vm_read_reg(vm, bc, bc_len);
    if (vm->sp < VM_STACK_SIZE)
        vm->stack[vm->sp++] = vm_get_reg(vm, s);
}

static void vm_handle_pop(struct vm_state *vm, const uint8_t *bc, size_t bc_len) {
    uint8_t d = vm_read_reg(vm, bc, bc_len);
    if (vm->sp > 0)
        vm_set_reg(vm, d, vm->stack[--vm->sp]);
}

static void vm_handle_fused_cmp_jmp(struct vm_state *vm, const uint8_t *bc, size_t bc_len) {
    uint8_t c = vm_read_reg(vm, bc, bc_len);
    uint32_t t = vm_read_u32(vm, bc, bc_len);
    uint32_t f = vm_read_u32(vm, bc, bc_len);
    if (vm_get_reg(vm, c) != 0)
        vm_set_reg(vm, VM_REG_PC, (uint64_t)t);
    else
        vm_set_reg(vm, VM_REG_PC, (uint64_t)f);
    vm->cfg_path_selector = (int)(vm->bb_hash ^ (uint64_t)(vm_get_reg(vm, c) != 0 ? t : f));
}

static void vm_handle_default(struct vm_state *vm, const uint8_t *bc, size_t bc_len) {
    (void)bc; (void)bc_len;
    vm->halted = 1;
}

/* ── State-dependent ISA update ───────────────────────────────────── */

static void vm_state_isa_update(struct vm_state *vm, uint8_t instruction_id) {
    if (vm->exec_history_len < 64) {
        vm->exec_history[vm->exec_history_len++] = instruction_id;
    } else {
        memmove(vm->exec_history, vm->exec_history + 1, 63);
        vm->exec_history[63] = instruction_id;
    }

    uint8_t state_hash[32];
    sha256_hash(vm->exec_history, (size_t)vm->exec_history_len, state_hash);
    memcpy(vm->state_isa_state, state_hash, 32);

    uint64_t state_val = (uint64_t)state_hash[0]
                       | ((uint64_t)state_hash[1] << 8)
                       | ((uint64_t)state_hash[2] << 16)
                       | ((uint64_t)state_hash[3] << 24)
                       | ((uint64_t)state_hash[4] << 32)
                       | ((uint64_t)state_hash[5] << 40)
                       | ((uint64_t)state_hash[6] << 48)
                       | ((uint64_t)state_hash[7] << 56);

    uint64_t threshold = 0x10000000
        + (uint64_t)(state_hash[0] ^ state_hash[8])
        + ((uint64_t)(state_hash[1] ^ state_hash[9]) << 8)
        + ((uint64_t)(state_hash[2] ^ state_hash[10]) << 16)
        + ((uint64_t)(state_hash[3] ^ state_hash[11]) << 24);

    if (state_val > threshold) {
        vm->state_isa_rotation_offset++;
    }
}

/* ── Main execution loop ──────────────────────────────────────────── */

VM_EXPORT
int vm_execute(
    const unsigned char *bytecode,
    size_t bytecode_len,
    const unsigned char *key,
    const unsigned char *input,
    size_t input_len,
    unsigned char *output,
    size_t *output_len
) {
    (void)input;
    (void)input_len;

    struct vm_state vm;
    memset(&vm, 0, sizeof(vm));
    vm.sp = 0;
    vm.halted = 0;
    vm.epoch = 0;
    vm.steps_until_rekey = VM_REKEY_INTERVAL;
    vm.bb_hash = 0;
    vm.cfg_path_selector = 0;
    memset(vm.state_isa_state, 0, 32);
    memset(vm.exec_history, 0, 64);
    vm.exec_history_len = 0;
    vm.state_isa_rotation_offset = 0;

    if (output_len) *output_len = 0;

    uint8_t entropy[32];
    if (key) {
        struct sha256_ctx mix_ctx;
        sha256_init(&mix_ctx);
        runtime_collect_entropy(entropy);
        sha256_update(&mix_ctx, entropy, 32);
        sha256_update(&mix_ctx, key, 32);
        sha256_final(&mix_ctx, entropy);
    } else {
        runtime_collect_entropy(entropy);
    }
    memcpy(vm.seed, entropy, 32);
    vm_derive_isa(vm.seed, vm.isa_table);

    /* Initialize self-mutating ISA */
    vm_init_mutating_isa(&vm, vm.seed);

    const uint8_t *bc = (const uint8_t *)bytecode;
    size_t bc_len = bytecode_len;
    int steps = 0;
    const int MAX_STEPS = 1000000;

    while (!vm.halted && (size_t)vm.regs[VM_REG_PC] < bc_len && steps < MAX_STEPS) {
        size_t instr_start = (size_t)vm.regs[VM_REG_PC];
        steps++;

        /* Variable encoding: read total instruction length first */
        if (vm.encoding_mode == ENCODING_VARIABLE) {
            vm.variable_instr_len = vm_read_byte(&vm, bc, bc_len);
            if (vm.halted) break;
        }

        uint8_t phys_opcode = vm_read_byte(&vm, bc, bc_len);
        if (vm.halted) break;

        if (phys_opcode == VM_OPCODE_REKEY) {
            vm_rekey(&vm, vm.bb_hash);
            vm.steps_until_rekey = VM_REKEY_INTERVAL;
            continue;
        }

        vm.steps_until_rekey--;
        if (vm.steps_until_rekey <= 0) {
            vm_rekey(&vm, vm.bb_hash);
            vm.steps_until_rekey = VM_REKEY_INTERVAL;
        }

        /* State-dependent ISA lookup: rotate opcode based on execution history */
        uint8_t state_rotation = (uint8_t)(vm.state_isa_rotation_offset & 0xFF);
        uint8_t rotated_opcode = (phys_opcode + state_rotation) & 0xFF;
        uint8_t logical_opcode = vm.isa_table[rotated_opcode];

        /* Update state ISA with current instruction */
        vm_state_isa_update(&vm, phys_opcode);

        /* Field shuffle: pre-read operand bytes and de-permute */
        if (vm.encoding_mode == ENCODING_FIELD_SHUFFLE) {
            vm_prepare_field_shuffle(&vm, bc, bc_len, logical_opcode);
            if (vm.halted) break;
        }

        /* Dispatch via selected mechanism */
        switch (vm.dispatch_mode) {
            case DISPATCH_SWITCH: {
                switch (logical_opcode) {
                    case 0: break;
                    case 1: vm_handle_add(&vm, bc, bc_len); break;
                    case 2: vm_handle_sub(&vm, bc, bc_len); break;
                    case 3: vm_handle_mul(&vm, bc, bc_len); break;
                    case 4: vm_handle_div(&vm, bc, bc_len); break;
                    case 5: vm_handle_mod(&vm, bc, bc_len); break;
                    case 6: vm_handle_and(&vm, bc, bc_len); break;
                    case 7: vm_handle_or(&vm, bc, bc_len); break;
                    case 8: vm_handle_xor(&vm, bc, bc_len); break;
                    case 9: vm_handle_not(&vm, bc, bc_len); break;
                    case 10: vm_handle_shl(&vm, bc, bc_len); break;
                    case 11: vm_handle_shr(&vm, bc, bc_len); break;
                    case 12: vm_handle_load(&vm, bc, bc_len); break;
                    case 13: vm_handle_store(&vm, bc, bc_len); break;
                    case 14: vm_handle_mov(&vm, bc, bc_len); break;
                    case 16: vm_handle_jmp(&vm, bc, bc_len); break;
                    case 17: vm_handle_jz(&vm, bc, bc_len); break;
                    case 18: vm_handle_jnz(&vm, bc, bc_len); break;
                    case 23: vm_handle_call(&vm, bc, bc_len); break;
                    case 24: vm_handle_ret(&vm, bc, bc_len); break;
                    case 25: vm_handle_push(&vm, bc, bc_len); break;
                    case 26: vm_handle_pop(&vm, bc, bc_len); break;
                    case 34: vm_handle_fused_cmp_jmp(&vm, bc, bc_len); break;
                    default: vm.halted = 1; break;
                }
                break;
            }

            case DISPATCH_INDIRECT: {
                handler_fn_t handler = vm.dispatch[logical_opcode];
                if (handler)
                    handler(&vm, bc, bc_len);
                else
                    vm.halted = 1;
                break;
            }

            case DISPATCH_COMPUTED_GOTO: {
                /* Computed dispatch using handler order + epoch rotation */
                int idx = (int)((logical_opcode * 7 + (uint8_t)vm.epoch) % VM_NUM_IMPL_HANDLERS);
                uint8_t dispatched_op = vm.handlers[idx].opcode;
                if (dispatched_op == logical_opcode || dispatched_op == 255) {
                    handler_fn_t handler = vm.dispatch[logical_opcode];
                    if (handler)
                        handler(&vm, bc, bc_len);
                    else
                        vm.halted = 1;
                } else {
                    vm.halted = 1;
                }
                break;
            }
        }

        /* Deactivate shuffle buffer after handler */
        vm.shuffle_active = 0;

        /* Update CFG path selector at instruction boundary */
        vm.cfg_path_selector = (int)((vm.cfg_path_selector * 31) ^ (uint64_t)vm.epoch ^ vm.bb_hash);

        /* Variable encoding: skip padding bytes */
        if (vm.encoding_mode == ENCODING_VARIABLE && !vm.halted && vm.variable_instr_len > 0) {
            size_t consumed = (size_t)vm.regs[VM_REG_PC] - instr_start;
            if (consumed < (size_t)vm.variable_instr_len)
                vm.regs[VM_REG_PC] = (uint64_t)(instr_start + (size_t)vm.variable_instr_len);
            else if (consumed > (size_t)vm.variable_instr_len)
                vm.halted = 1;
        }
    }

    if (output_len && input_len > 0 && output) {
        size_t copy_len = input_len < VM_MEM_SIZE ? input_len : VM_MEM_SIZE;
        memcpy(output, vm.memory, copy_len);
        *output_len = copy_len;
    }

    return vm.halted ? 1 : 0;
}
