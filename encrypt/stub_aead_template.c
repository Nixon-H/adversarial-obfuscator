/* Build-time compiled position-independent ELF decryptor.
 * Tokens are replaced by encrypt/stub.py. No libc or external symbols.
 */
typedef unsigned char u8;
typedef unsigned int u32;
typedef unsigned long u64;
typedef __uint128_t u128;

#define ARRAY_LEN(a) (sizeof(a) / sizeof((a)[0]))

static const u8 aead_header[64] __attribute__((section(".rodata.aead.0"), aligned(1), used)) = { @HEADER@ };
static const u8 aead_nonce[12] __attribute__((section(".rodata.aead.1"), aligned(1), used)) = { @NONCE@ };
static const u8 aead_tag[16] __attribute__((section(".rodata.aead.2"), aligned(1), used)) = { @TAG@ };
static const char aead_key_path[@PATHLEN@] __attribute__((section(".rodata.aead.3"), aligned(1), used)) = { @KEYPATH@ };

static inline long sys_call3(long number, long a, long b, long c) {
    long result;
    __asm__ volatile("syscall" : "=a"(result) : "a"(number), "D"(a), "S"(b), "d"(c)
                     : "rcx", "r11", "memory");
    return result;
}

static inline long sys_call6(long number, long a, long b, long c,
                             long d, long e, long f) {
    register long r10 __asm__("r10") = d;
    register long r8 __asm__("r8") = e;
    register long r9 __asm__("r9") = f;
    long result;
    __asm__ volatile("syscall" : "=a"(result)
                     : "a"(number), "D"(a), "S"(b), "d"(c), "r"(r10), "r"(r8), "r"(r9)
                     : "rcx", "r11", "memory");
    return result;
}

static u32 load32_le(const u8 *p) {
    return (u32)p[0] | ((u32)p[1] << 8) | ((u32)p[2] << 16) | ((u32)p[3] << 24);
}

static u64 load64_le(const u8 *p) {
    return (u64)load32_le(p) | ((u64)load32_le(p + 4) << 32);
}

static void store32_le(u8 *p, u32 value) {
    p[0] = (u8)value; p[1] = (u8)(value >> 8);
    p[2] = (u8)(value >> 16); p[3] = (u8)(value >> 24);
}

static void store64_le(u8 *p, u64 value) {
    store32_le(p, (u32)value); store32_le(p + 4, (u32)(value >> 32));
}

static u32 rotl32(u32 value, unsigned count) {
    return (value << count) | (value >> (32 - count));
}

#define QR(a,b,c,d) do { \
    a += b; d ^= a; d = rotl32(d,16); \
    c += d; b ^= c; b = rotl32(b,12); \
    a += b; d ^= a; d = rotl32(d,8); \
    c += d; b ^= c; b = rotl32(b,7); \
} while (0)

static void chacha_block(const u8 key[32], const u8 nonce[12], u32 counter,
                         u8 output[64]) {
    static const char sigma[] = "expand 32-byte k";
    u32 state[16];
    u32 initial[16];
    for (int i = 0; i < 4; ++i) initial[i] = load32_le((const u8 *)sigma + i * 4);
    for (int i = 0; i < 8; ++i) initial[4 + i] = load32_le(key + i * 4);
    initial[12] = counter;
    for (int i = 0; i < 3; ++i) initial[13 + i] = load32_le(nonce + i * 4);
    for (int i = 0; i < 16; ++i) state[i] = initial[i];
    for (int i = 0; i < 10; ++i) {
        QR(state[0], state[4], state[8], state[12]);
        QR(state[1], state[5], state[9], state[13]);
        QR(state[2], state[6], state[10], state[14]);
        QR(state[3], state[7], state[11], state[15]);
        QR(state[0], state[5], state[10], state[15]);
        QR(state[1], state[6], state[11], state[12]);
        QR(state[2], state[7], state[8], state[13]);
        QR(state[3], state[4], state[9], state[14]);
    }
    for (int i = 0; i < 16; ++i) store32_le(output + i * 4, state[i] + initial[i]);
}

static void chacha_xor(const u8 key[32], const u8 nonce[12], u8 *data, u64 length,
                       u32 counter) {
    u8 stream[64];
    for (u64 offset = 0; offset < length; offset += 64) {
        chacha_block(key, nonce, counter++, stream);
        u64 chunk = length - offset;
        if (chunk > 64) chunk = 64;
        for (u64 i = 0; i < chunk; ++i) data[offset + i] ^= stream[i];
    }
}

static void poly1305(const u8 *message, u64 length, const u8 one_time_key[32],
                     u8 tag[16]) {
    /* poly1305-donna 64-bit limb formulation, adapted to GCC __int128. */
    const u64 mask44 = 0xfffffffffffULL;
    const u64 mask42 = 0x3ffffffffffULL;
    u64 t0 = load64_le(one_time_key);
    u64 t1 = load64_le(one_time_key + 8);
    u64 r0 = t0 & 0xffc0fffffffULL;
    u64 r1 = ((t0 >> 44) | (t1 << 20)) & 0xfffffc0ffffULL;
    u64 r2 = (t1 >> 24) & 0x00ffffffc0fULL;
    u64 s1 = r1 * 20;
    u64 s2 = r2 * 20;
    u64 pad0 = load64_le(one_time_key + 16);
    u64 pad1 = load64_le(one_time_key + 24);
    u64 h0 = 0, h1 = 0, h2 = 0;
    for (u64 offset = 0; offset < length; offset += 16) {
        u64 n0 = load64_le(message + offset);
        u64 n1 = load64_le(message + offset + 8);
        h0 += n0 & mask44;
        h1 += ((n0 >> 44) | (n1 << 20)) & mask44;
        h2 += ((n1 >> 24) & mask42) | (1ULL << 40);
        u128 d0 = (u128)h0 * r0 + (u128)h1 * s2 + (u128)h2 * s1;
        u128 d1 = (u128)h0 * r1 + (u128)h1 * r0 + (u128)h2 * s2;
        u128 d2 = (u128)h0 * r2 + (u128)h1 * r1 + (u128)h2 * r0;
        u64 c;
        c = (u64)(d0 >> 44); h0 = (u64)d0 & mask44;
        d1 += c; c = (u64)(d1 >> 44); h1 = (u64)d1 & mask44;
        d2 += c; c = (u64)(d2 >> 42); h2 = (u64)d2 & mask42;
        h0 += c * 5; c = h0 >> 44; h0 &= mask44; h1 += c;
    }
    u64 c;
    c = h1 >> 44; h1 &= mask44; h2 += c;
    c = h2 >> 42; h2 &= mask42; h0 += c * 5;
    c = h0 >> 44; h0 &= mask44; h1 += c;
    c = h1 >> 44; h1 &= mask44; h2 += c;
    c = h2 >> 42; h2 &= mask42; h0 += c * 5;
    c = h0 >> 44; h0 &= mask44; h1 += c;

    u64 g0 = h0 + 5; c = g0 >> 44; g0 &= mask44;
    u64 g1 = h1 + c; c = g1 >> 44; g1 &= mask44;
    u64 g2 = h2 + c - (1ULL << 42);
    c = (g2 >> 63) - 1;
    g0 &= c; g1 &= c; g2 &= c; c = ~c;
    h0 = (h0 & c) | g0; h1 = (h1 & c) | g1; h2 = (h2 & c) | g2;

    h0 += pad0 & mask44; c = h0 >> 44; h0 &= mask44;
    h1 += ((pad0 >> 44) | (pad1 << 20)) & mask44; h1 += c;
    c = h1 >> 44; h1 &= mask44;
    h2 += ((pad1 >> 24) & mask42) + c; h2 &= mask42;
    h0 = h0 | (h1 << 44);
    h1 = (h1 >> 20) | (h2 << 24);
    store64_le(tag, h0);
    store64_le(tag + 8, h1);
}

static int constant_time_equal(const u8 *a, const u8 *b, u64 length) {
    u8 difference = 0;
    for (u64 i = 0; i < length; ++i) difference |= a[i] ^ b[i];
    return difference == 0;
}

__attribute__((naked, noinline, noreturn, used)) static void tail_jump(u64 entry_rsp,
                                                                        u64 saved_rdx,
                                                                        void *target) {
    /* Naked basic asm preserves the SysV argument contract.  With extended
     * asm and no register inputs GCC may omit the argument setup entirely. */
    __asm__(
        "mov %rdx, %rcx\n"
        "mov %rdi, %rsp\n"
        "mov %rsi, %rdx\n"
        "jmp *%rcx\n");
}

__attribute__((used, noinline)) static int decrypt_and_jump(u64 base, u64 saved_rdx,
                                                           u64 entry_rsp, int tail) {
    u32 text_size = load32_le(aead_header + 16);
    u64 text_base = base + load64_le(aead_header + 24);
    u64 entry = (u64)load64_le(aead_header + 32);
    u32 rodata_size = load32_le(aead_header + 40);
    u64 rodata_base = base + (u64)load64_le(aead_header + 44);
    u64 total = (u64)text_size + rodata_size;

    long fd = sys_call3(2, (long)aead_key_path, 0, 0); /* open */
    if (fd < 0) sys_call3(60, 1, 0, 0);
    u8 key[32];
    long got = sys_call3(0, fd, (long)key, sizeof(key)); /* read */
    sys_call3(3, fd, 0, 0); /* close */
    if (got != 32) sys_call3(60, 3, 0, 0);

    u64 text_page = text_base & ~0xfffULL;
    u64 text_end = (text_base + text_size + 0xfff) & ~0xfffULL;
    if (sys_call6(10, text_page, text_end - text_page, 7, 0, 0, 0) != 0)
        sys_call3(60, 4, 0, 0);
    if (rodata_size) {
        u64 ro_page = rodata_base & ~0xfffULL;
        u64 ro_end = (rodata_base + rodata_size + 0xfff) & ~0xfffULL;
        if (sys_call6(10, ro_page, ro_end - ro_page, 7, 0, 0, 0) != 0)
            sys_call3(60, 4, 0, 0);
    }

    u8 poly_key[64];
    chacha_block(key, aead_nonce, 0, poly_key);
    u64 mac_length = 16 + 64 + total + 16 + 16;
    u8 *mac = (u8 *)sys_call6(9, 0, mac_length, 3, 0x22, -1, 0); /* mmap */
    if ((long)mac < 0) sys_call3(60, 5, 0, 0);
    u64 cursor = 0;
    for (u64 i = 0; i < 64; ++i) mac[cursor++] = aead_header[i];
    while (cursor % 16) mac[cursor++] = 0;
    for (u64 i = 0; i < text_size; ++i) mac[cursor++] = ((u8 *)text_base)[i];
    for (u64 i = 0; i < rodata_size; ++i) mac[cursor++] = ((u8 *)rodata_base)[i];
    while (cursor % 16) mac[cursor++] = 0;
    store64_le(mac + cursor, 64); cursor += 8;
    store64_le(mac + cursor, total); cursor += 8;
    u8 expected[16];
    poly1305(mac, cursor, poly_key, expected);
    if (!constant_time_equal(expected, aead_tag, 16)) sys_call3(60, 6, 0, 0);

    /* The MAC buffer holds AAD(64) || text ciphertext || rodata ciphertext.
     * Decrypt that contiguous logical stream once, then copy plaintext back to
     * the two (non-contiguous) artifact regions. */
    chacha_xor(key, aead_nonce, mac + 64, total, 1);
    for (u64 i = 0; i < text_size; ++i) ((u8 *)text_base)[i] = mac[64 + i];
    for (u64 i = 0; i < rodata_size; ++i) ((u8 *)rodata_base)[i] = mac[64 + text_size + i];
    sys_call3(11, (long)mac, mac_length, 0); /* munmap */
    if (rodata_size) {
        u64 ro_page = rodata_base & ~0xfffULL;
        u64 ro_end = (rodata_base + rodata_size + 0xfff) & ~0xfffULL;
        sys_call6(10, ro_page, ro_end - ro_page, 1, 0, 0, 0); /* read-only */
    }
    u64 text_only_end = (text_base + text_size + 0xfff) & ~0xfffULL;
    sys_call6(10, text_page, text_only_end - text_page, 5, 0, 0, 0);
    /* Wipe the runtime key and the Poly1305 one-time key before jumping into
     * the payload: the sidecar key is the artifact's only secret and must not
     * survive in stack memory past its last use. Volatile byte stores so the
     * compiler cannot elide the wipes (the empty asm barrier that used to be
     * here constrained nothing and zeroed nothing). */
    {
        volatile u8 *vk = (volatile u8 *)key;
        for (u64 i = 0; i < sizeof(key); ++i) vk[i] = 0;
        volatile u8 *vp = (volatile u8 *)poly_key;
        for (u64 i = 0; i < sizeof(poly_key); ++i) vp[i] = 0;
    }
    __asm__ volatile("" : : : "memory");
    typedef int (*entry_fn)(void);
    entry_fn target = (entry_fn)(text_base + entry);
    if (tail) {
        /* The only caller of stub_main is the ELF loader, so GCC cannot see
         * the assembly call that supplies `tail`. Invoke the trampoline from
         * constrained asm as well; a C call may be optimized away and leave
         * _start with a synthetic return address instead of its entry stack. */
        __asm__ volatile(
            "mov %0, %%rdi\n\t"
            "mov %1, %%rsi\n\t"
            "mov %2, %%rdx\n\t"
            "call tail_jump\n\t"
            "ud2\n\t"
            : : "r"(entry_rsp), "r"(saved_rdx), "r"((void *)target)
            : "rdi", "rsi", "rdx", "memory");
        __builtin_unreachable();
    }
    return target();
}

__attribute__((naked, used, section(".text.stub_main"))) int stub_main(void) {
    __asm__ volatile(
        "lea stub_main(%%rip), %%rdi\n"
        "add $6, %%rdi\n"
        "cmpq $0x1000, (%%rsp)\n"
        "jb 1f\n"
        "push %%rdx\n"
        "mov %%rdx, %%rsi\n"
        "mov %%rsp, %%rdx\n"
        "xor %%ecx, %%ecx\n"
        "call decrypt_and_jump\n"
        "pop %%rdx\n"
        "ret\n"
        "1:\n"
        "mov %%rdx, %%rsi\n"
        "mov %%rsp, %%rdx\n"
        "mov $1, %%ecx\n"
        "jmp decrypt_and_jump\n"
        ::: "rdi", "rsi", "rdx", "rcx", "memory");
}
