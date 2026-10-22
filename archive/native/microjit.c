/* microjit.c — Micro-JIT Fragment Reassembly Engine Implementation
 *
 * Implements ephemeral execution reconstruction: functions are split into
 * encrypted fragments that are decrypted, executed, and wiped one at a time.
 * Each fragment key is cryptographically bound to the previous fragment's
 * output, so recovering one fragment is insufficient to decrypt the next.
 */

#include "microjit.h"
#include "key_evolution.h"

#include <stdlib.h>
#include <string.h>
#include <stdio.h>

#if defined(_WIN32) || defined(_WIN64)
#include <windows.h>
#else
#include <sys/mman.h>
#include <unistd.h>
#endif

/* ---- SHA-256 implementation (self-contained, no external deps) --------- */

#define SHA256_BLOCK_SIZE 64

typedef struct {
    uint8_t  data[SHA256_BLOCK_SIZE];
    uint32_t datalen;
    uint64_t bitlen;
    uint32_t state[8];
} mj_sha256_ctx;

static const uint32_t MJ_SHA256_K[64] = {
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

#define MJ_ROTLEFT(a,b) (((a) << (b)) | ((a) >> (32-(b))))
#define MJ_ROTRIGHT(a,b) (((a) >> (b)) | ((a) << (32-(b))))
#define MJ_CH(x,y,z) (((x) & (y)) ^ (~(x) & (z)))
#define MJ_MAJ(x,y,z) (((x) & (y)) ^ ((x) & (z)) ^ ((y) & (z)))
#define MJ_EP0(x) (MJ_ROTRIGHT(x,2) ^ MJ_ROTRIGHT(x,13) ^ MJ_ROTRIGHT(x,22))
#define MJ_EP1(x) (MJ_ROTRIGHT(x,6) ^ MJ_ROTRIGHT(x,11) ^ MJ_ROTRIGHT(x,25))
#define MJ_SIG0(x) (MJ_ROTRIGHT(x,7) ^ MJ_ROTRIGHT(x,18) ^ ((x) >> 3))
#define MJ_SIG1(x) (MJ_ROTRIGHT(x,17) ^ MJ_ROTRIGHT(x,19) ^ ((x) >> 10))

static void mj_sha256_transform(mj_sha256_ctx *ctx, const uint8_t data[]) {
    uint32_t m[64], a, b, c, d, e, f, g, h, t1, t2;
    for (int i = 0, j = 0; i < 16; i++, j += 4)
        m[i] = ((uint32_t)data[j] << 24) | ((uint32_t)data[j+1] << 16)
             | ((uint32_t)data[j+2] << 8)  | (uint32_t)data[j+3];
    for (int i = 16; i < 64; i++)
        m[i] = MJ_SIG1(m[i-2]) + m[i-7] + MJ_SIG0(m[i-15]) + m[i-16];
    a = ctx->state[0]; b = ctx->state[1]; c = ctx->state[2]; d = ctx->state[3];
    e = ctx->state[4]; f = ctx->state[5]; g = ctx->state[6]; h = ctx->state[7];
    for (int i = 0; i < 64; i++) {
        t1 = h + MJ_EP1(e) + MJ_CH(e,f,g) + MJ_SHA256_K[i] + m[i];
        t2 = MJ_EP0(a) + MJ_MAJ(a,b,c);
        h = g; g = f; f = e; e = d + t1; d = c; c = b; b = a; a = t1 + t2;
    }
    ctx->state[0] += a; ctx->state[1] += b; ctx->state[2] += c;
    ctx->state[3] += d; ctx->state[4] += e; ctx->state[5] += f;
    ctx->state[6] += g; ctx->state[7] += h;
}

static void mj_sha256_init(mj_sha256_ctx *ctx) {
    ctx->datalen = 0; ctx->bitlen = 0;
    ctx->state[0] = 0x6a09e667; ctx->state[1] = 0xbb67ae85;
    ctx->state[2] = 0x3c6ef372; ctx->state[3] = 0xa54ff53a;
    ctx->state[4] = 0x510e527f; ctx->state[5] = 0x9b05688c;
    ctx->state[6] = 0x1f83d9ab; ctx->state[7] = 0x5be0cd19;
}

static void mj_sha256_update(mj_sha256_ctx *ctx, const uint8_t *data, size_t len) {
    for (size_t i = 0; i < len; i++) {
        ctx->data[ctx->datalen++] = data[i];
        ctx->bitlen += 8;
        if (ctx->datalen == SHA256_BLOCK_SIZE) {
            mj_sha256_transform(ctx, ctx->data);
            ctx->datalen = 0;
        }
    }
}

static void mj_sha256_final(mj_sha256_ctx *ctx, uint8_t hash[MJ_HASH_SIZE]) {
    ctx->data[ctx->datalen++] = 0x80;
    while (ctx->datalen != 56) {
        if (ctx->datalen == SHA256_BLOCK_SIZE) {
            mj_sha256_transform(ctx, ctx->data);
            ctx->datalen = 0;
        }
        ctx->data[ctx->datalen++] = 0;
    }
    for (int i = 0; i < 8; i++)
        ctx->data[63 - i] = (uint8_t)((ctx->bitlen >> (i * 8)) & 0xFF);
    mj_sha256_transform(ctx, ctx->data);
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

static void mj_sha256(const uint8_t *data, size_t len, uint8_t hash[MJ_HASH_SIZE]) {
    mj_sha256_ctx ctx;
    mj_sha256_init(&ctx);
    mj_sha256_update(&ctx, data, len);
    mj_sha256_final(&ctx, hash);
}

/* ---- HMAC-SHA256 ------------------------------------------------------- */

static void mj_hmac_sha256(const uint8_t *key, size_t key_len,
                            const uint8_t *msg, size_t msg_len,
                            uint8_t out[MJ_HASH_SIZE]) {
    uint8_t k0[MJ_HASH_SIZE];
    uint8_t ipad[SHA256_BLOCK_SIZE];
    uint8_t opad[SHA256_BLOCK_SIZE];

    if (key_len > SHA256_BLOCK_SIZE) {
        mj_sha256(key, key_len, k0);
        key = k0;
        key_len = MJ_HASH_SIZE;
    }

    memset(ipad, 0, sizeof(ipad));
    memset(opad, 0, sizeof(opad));
    memcpy(ipad, key, key_len);
    memcpy(opad, key, key_len);

    for (size_t i = 0; i < SHA256_BLOCK_SIZE; i++) {
        ipad[i] ^= 0x36;
        opad[i] ^= 0x5c;
    }

    mj_sha256_ctx ctx;
    mj_sha256_init(&ctx);
    mj_sha256_update(&ctx, ipad, sizeof(ipad));
    mj_sha256_update(&ctx, msg, msg_len);
    mj_sha256_final(&ctx, out);

    mj_sha256_init(&ctx);
    mj_sha256_update(&ctx, opad, sizeof(opad));
    mj_sha256_update(&ctx, out, MJ_HASH_SIZE);
    mj_sha256_final(&ctx, out);
}

/* ---- Key Derivation ---------------------------------------------------- */

MJ_EXPORT void mj_derive_fragment_key(const uint8_t chain_key[MJ_KEY_SIZE],
                             const uint8_t chain_state[MJ_HASH_SIZE],
                             int fragment_id,
                             uint8_t output_key[MJ_KEY_SIZE]) {
    mj_derive_fragment_key_with_history(chain_key, chain_state, NULL,
                                        fragment_id, output_key);
}

MJ_EXPORT void mj_derive_fragment_key_with_history(const uint8_t chain_key[MJ_KEY_SIZE],
                                                    const uint8_t chain_state[MJ_HASH_SIZE],
                                                    const uint8_t accumulated_hash[MJ_HASH_SIZE],
                                                    int fragment_id,
                                                    uint8_t output_key[MJ_KEY_SIZE]) {
    int use_history = (accumulated_hash != NULL);
    int msg_len = MJ_HASH_SIZE + (use_history ? MJ_HASH_SIZE : 0) + 4;
    uint8_t msg[MJ_HASH_SIZE + MJ_HASH_SIZE + 4];

    memcpy(msg, chain_state, MJ_HASH_SIZE);
    if (use_history) {
        memcpy(msg + MJ_HASH_SIZE, accumulated_hash, MJ_HASH_SIZE);
        msg[MJ_HASH_SIZE * 2 + 0] = (uint8_t)(fragment_id & 0xFF);
        msg[MJ_HASH_SIZE * 2 + 1] = (uint8_t)((fragment_id >> 8) & 0xFF);
        msg[MJ_HASH_SIZE * 2 + 2] = (uint8_t)((fragment_id >> 16) & 0xFF);
        msg[MJ_HASH_SIZE * 2 + 3] = (uint8_t)((fragment_id >> 24) & 0xFF);
    } else {
        msg[MJ_HASH_SIZE + 0] = (uint8_t)(fragment_id & 0xFF);
        msg[MJ_HASH_SIZE + 1] = (uint8_t)((fragment_id >> 8) & 0xFF);
        msg[MJ_HASH_SIZE + 2] = (uint8_t)((fragment_id >> 16) & 0xFF);
        msg[MJ_HASH_SIZE + 3] = (uint8_t)((fragment_id >> 24) & 0xFF);
    }

    mj_hmac_sha256(chain_key, MJ_KEY_SIZE, msg, msg_len, output_key);
}

/* ---- AES-256-CTR ------------------------------------------------------- */

static const uint8_t MJ_AES_SBOX[256] = {
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

static void mj_aes256_key_expand(const uint8_t key[MJ_KEY_SIZE],
                                   uint32_t rk[60]) {
    for (int i = 0; i < 8; i++)
        rk[i] = ((uint32_t)key[4*i] << 24) | ((uint32_t)key[4*i+1] << 16)
              | ((uint32_t)key[4*i+2] << 8)  | (uint32_t)key[4*i+3];
    uint32_t temp;
    const uint32_t rcon[10] = {0x01000000,0x02000000,0x04000000,0x08000000,
                               0x10000000,0x20000000,0x40000000,0x80000000,
                               0x1b000000,0x36000000};
    for (int i = 8; i < 60; i++) {
        temp = rk[i-1];
        if (i % 8 == 0) {
            uint32_t rot = ((temp << 8) | (temp >> 24)) & 0xFFFFFFFF;
            temp = ((uint32_t)MJ_AES_SBOX[(rot>>24)&0xFF] << 24)
                 | ((uint32_t)MJ_AES_SBOX[(rot>>16)&0xFF] << 16)
                 | ((uint32_t)MJ_AES_SBOX[(rot>>8)&0xFF] << 8)
                 | (uint32_t)MJ_AES_SBOX[rot&0xFF];
            temp ^= rcon[i/8 - 1];
        } else if (i % 8 == 4) {
            temp = ((uint32_t)MJ_AES_SBOX[(temp>>24)&0xFF] << 24)
                 | ((uint32_t)MJ_AES_SBOX[(temp>>16)&0xFF] << 16)
                 | ((uint32_t)MJ_AES_SBOX[(temp>>8)&0xFF] << 8)
                 | (uint32_t)MJ_AES_SBOX[temp&0xFF];
        }
        rk[i] = rk[i-8] ^ temp;
    }
}

static void mj_aes256_encrypt_block(const uint8_t in[16],
                                     uint8_t out[16],
                                     const uint32_t rk[60]) {
    uint32_t s[4];
    for (int i = 0; i < 4; i++)
        s[i] = ((uint32_t)in[4*i] << 24) | ((uint32_t)in[4*i+1] << 16)
             | ((uint32_t)in[4*i+2] << 8) | (uint32_t)in[4*i+3];
    for (int i = 0; i < 4; i++) s[i] ^= rk[i];
    for (int r = 1; r < 14; r++) {
        uint32_t t[4];
        for (int i = 0; i < 4; i++) {
            uint32_t v = s[i];
            t[i] = ((uint32_t)MJ_AES_SBOX[(v>>24)&0xFF] << 24)
                 | ((uint32_t)MJ_AES_SBOX[(v>>16)&0xFF] << 16)
                 | ((uint32_t)MJ_AES_SBOX[(v>>8)&0xFF] << 8)
                 | (uint32_t)MJ_AES_SBOX[v&0xFF];
        }
        s[0] = (t[0] & 0xFF000000) | ((t[1]>>8)&0x00FF0000)
             | ((t[2]>>16)&0x0000FF00) | (t[3]>>24);
        s[1] = (t[1] & 0xFF000000) | ((t[2]>>8)&0x00FF0000)
             | ((t[3]>>16)&0x0000FF00) | (t[0]>>24);
        s[2] = (t[2] & 0xFF000000) | ((t[3]>>8)&0x00FF0000)
             | ((t[0]>>16)&0x0000FF00) | (t[1]>>24);
        s[3] = (t[3] & 0xFF000000) | ((t[0]>>8)&0x00FF0000)
             | ((t[1]>>16)&0x0000FF00) | (t[2]>>24);
        uint32_t a0, a1, a2, a3;
        #define MJ_GFMUL2(x) ((((x)<<1) ^ (((x)&0x80)?0x11b:0)) & 0xFF)
        #define MJ_GFMUL3(x) (MJ_GFMUL2(x) ^ (x))
        for (int i = 0; i < 4; i++) {
            a0 = (s[i] >> 24) & 0xFF; a1 = (s[i] >> 16) & 0xFF;
            a2 = (s[i] >> 8) & 0xFF;  a3 = s[i] & 0xFF;
            s[i] = (MJ_GFMUL2(a0) ^ MJ_GFMUL3(a1) ^ a2 ^ a3) << 24
                 | (a0 ^ MJ_GFMUL2(a1) ^ MJ_GFMUL3(a2) ^ a3) << 16
                 | (a0 ^ a1 ^ MJ_GFMUL2(a2) ^ MJ_GFMUL3(a3)) << 8
                 | (MJ_GFMUL3(a0) ^ a1 ^ a2 ^ MJ_GFMUL2(a3));
        }
        for (int i = 0; i < 4; i++) s[i] ^= rk[4*r + i];
    }
    uint32_t t[4];
    for (int i = 0; i < 4; i++) {
        uint32_t v = s[i];
        t[i] = ((uint32_t)MJ_AES_SBOX[(v>>24)&0xFF] << 24)
             | ((uint32_t)MJ_AES_SBOX[(v>>16)&0xFF] << 16)
             | ((uint32_t)MJ_AES_SBOX[(v>>8)&0xFF] << 8)
             | (uint32_t)MJ_AES_SBOX[v&0xFF];
    }
    s[0] = (t[0] & 0xFF000000) | ((t[1]>>8)&0x00FF0000)
         | ((t[2]>>16)&0x0000FF00) | (t[3]>>24);
    s[1] = (t[1] & 0xFF000000) | ((t[2]>>8)&0x00FF0000)
         | ((t[3]>>16)&0x0000FF00) | (t[0]>>24);
    s[2] = (t[2] & 0xFF000000) | ((t[3]>>8)&0x00FF0000)
         | ((t[0]>>16)&0x0000FF00) | (t[1]>>24);
    s[3] = (t[3] & 0xFF000000) | ((t[0]>>8)&0x00FF0000)
         | ((t[1]>>16)&0x0000FF00) | (t[2]>>24);
    for (int i = 0; i < 4; i++) s[i] ^= rk[56 + i];
    for (int i = 0; i < 4; i++) {
        out[4*i]   = (uint8_t)(s[i] >> 24);
        out[4*i+1] = (uint8_t)(s[i] >> 16);
        out[4*i+2] = (uint8_t)(s[i] >> 8);
        out[4*i+3] = (uint8_t)(s[i] & 0xFF);
    }
}

MJ_EXPORT void mj_aes_ctr_crypt(uint8_t* data, size_t len,
                       const uint8_t key[MJ_KEY_SIZE]) {
    if (len == 0) return;
    uint32_t rk[60];
    mj_aes256_key_expand(key, rk);
    uint8_t counter[16];
    memset(counter, 0, 16);
    size_t offset = 0;
    while (offset < len) {
        uint8_t keystream[16];
        mj_aes256_encrypt_block(counter, keystream, rk);
        size_t chunk = (len - offset < 16) ? (len - offset) : 16;
        for (size_t i = 0; i < chunk; i++)
            data[offset + i] ^= keystream[i];
        offset += chunk;
        for (int i = 15; i >= 0; i--) {
            if (++counter[i] != 0) break;
        }
    }
}

/* ---- Utility functions ------------------------------------------------- */

MJ_EXPORT void mj_secure_wipe(void* ptr, size_t len) {
    if (ptr == NULL || len == 0) return;
    volatile uint8_t* p = (volatile uint8_t*)ptr;
    for (size_t i = 0; i < len; i++)
        p[i] = 0;
}

MJ_EXPORT void mj_update_chain_state(uint8_t chain_state[MJ_HASH_SIZE],
                            const uint8_t* fragment_output,
                            size_t output_len) {
    mj_sha256_ctx ctx;
    mj_sha256_init(&ctx);
    mj_sha256_update(&ctx, chain_state, MJ_HASH_SIZE);
    mj_sha256_update(&ctx, fragment_output, output_len);
    mj_sha256_final(&ctx, chain_state);
}

/* ---- Default execution callback (RWX + call) --------------------------- */

static int mj_default_exec(const uint8_t* code, size_t code_len,
                            uint64_t* accumulator) {
    (void)accumulator;
#if defined(_WIN32) || defined(_WIN64)
    HANDLE h = VirtualAlloc(NULL, code_len, MEM_COMMIT, PAGE_EXECUTE_READWRITE);
    if (!h) return -1;
    memcpy(h, code, code_len);
    int (*fn)(void) = (int (*)(void))h;
    int ret = fn();
    VirtualFree(h, 0, MEM_RELEASE);
    return ret;
#else
    size_t page_size = (size_t)sysconf(_SC_PAGESIZE);
    size_t alloc_size = ((code_len + page_size - 1) / page_size) * page_size;
    void* exec_mem = mmap(NULL, alloc_size, PROT_READ | PROT_WRITE | PROT_EXEC,
                          MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (exec_mem == MAP_FAILED) return -1;
    memcpy(exec_mem, code, code_len);
    int (*fn)(void) = (int (*)(void))exec_mem;
    int ret = fn();
    mj_secure_wipe(exec_mem, alloc_size);
    munmap(exec_mem, alloc_size);
    return ret;
#endif
}

static mj_fragment_exec_fn g_exec_fn = mj_default_exec;

/* ---- Engine implementation --------------------------------------------- */

MJ_EXPORT void mj_engine_init(mj_engine_t* eng,
                    const uint8_t* chain_key,
                    size_t chain_key_len) {
    memset(eng, 0, sizeof(*eng));
    if (chain_key) {
        size_t copy = chain_key_len < MJ_KEY_SIZE ? chain_key_len : MJ_KEY_SIZE;
        memcpy(eng->chain_key, chain_key, copy);
    }
    /* Initialize accumulated_hash to SHA-256("EXECUTION_HISTORY_V1") */
    mj_sha256((const uint8_t*)"EXECUTION_HISTORY_V1", 20, eng->accumulated_hash);
    eng->initialized = 1;
}

MJ_EXPORT int mj_engine_add_fragment(mj_engine_t* eng,
                           const uint8_t* encrypted_blob,
                           size_t blob_size,
                           int next_fragment_id) {
    if (eng->fragment_count >= MJ_MAX_FRAGMENTS) return -1;
    if (blob_size > MJ_MAX_BLOB_SIZE) return -2;
    mj_fragment_t* f = &eng->fragments[eng->fragment_count];
    f->encrypted_blob = (uint8_t*)malloc(blob_size);
    if (!f->encrypted_blob) return -3;
    memcpy(f->encrypted_blob, encrypted_blob, blob_size);
    f->blob_size = blob_size;
    f->next_fragment_id = next_fragment_id;
    f->is_last = (next_fragment_id < 0 || next_fragment_id >= MJ_MAX_FRAGMENTS);
    f->execution_buffer = NULL;
    f->buffer_size = 0;
    eng->fragment_count++;
    return 0;
}

MJ_EXPORT void mj_engine_set_exec_fn(mj_engine_t* eng, mj_fragment_exec_fn fn) {
    (void)eng;
    g_exec_fn = fn ? fn : mj_default_exec;
}

MJ_EXPORT int mj_engine_execute_one(mj_engine_t* eng, int fragment_id) {
    if (!eng->initialized) return -1;
    if (fragment_id < 0 || fragment_id >= eng->fragment_count) return -2;
    mj_fragment_t* f = &eng->fragments[fragment_id];
    if (!f->encrypted_blob) return -3;

    /* Allocate execution buffer */
    size_t buf_size = f->blob_size < MJ_MAX_EXEC_BUFFER ? MJ_MAX_EXEC_BUFFER : f->blob_size;

    /* Decrypt fragment into execution buffer */
    uint8_t* exec_buf = (uint8_t*)malloc(buf_size);
    if (!exec_buf) return -4;
    memcpy(exec_buf, f->encrypted_blob, f->blob_size);
    mj_aes_ctr_crypt(exec_buf, f->blob_size, f->key);

    /* Execute fragment */
    int ret = g_exec_fn(exec_buf, f->blob_size, &eng->accumulator);
    if (ret != 0) {
        mj_secure_wipe(exec_buf, buf_size);
        free(exec_buf);
        return ret;
    }

    /* Wipe execution buffer */
    mj_secure_wipe(exec_buf, buf_size);
    free(exec_buf);
    exec_buf = NULL;

    return 0;
}

MJ_EXPORT int mj_engine_execute_all(mj_engine_t* eng) {
    if (!eng->initialized) return -1;
    if (eng->fragment_count == 0) return -2;

    /* Initialize chain state from fragment 0 */
    {
        uint8_t seed[MJ_HASH_SIZE];
        memset(seed, 0, MJ_HASH_SIZE);
        memcpy(eng->chain_state, seed, MJ_HASH_SIZE);
    }

    int current_id = 0;
    int visited = 0;
    uint8_t prev_key[MJ_KEY_SIZE];
    memset(prev_key, 0, MJ_KEY_SIZE);

    key_evolution_chain_t ke_chain;
    key_evolution_init(&ke_chain, eng->chain_key);

    while (current_id >= 0 && current_id < eng->fragment_count && visited < eng->fragment_count) {
        mj_fragment_t* f = &eng->fragments[current_id];

        /* Derive key for this fragment using evolved key + accumulated hash */
        uint8_t effective_key[MJ_KEY_SIZE];
        memcpy(effective_key, ke_chain.evolved_key, MJ_KEY_SIZE);
        mj_derive_fragment_key_with_history(effective_key, eng->chain_state,
                                            eng->accumulated_hash,
                                            current_id, f->key);

        /* Decrypt & execute */
        size_t buf_size = f->blob_size < MJ_MAX_EXEC_BUFFER ? MJ_MAX_EXEC_BUFFER : f->blob_size;
        uint8_t* exec_buf = (uint8_t*)malloc(buf_size);
        if (!exec_buf) return -4;

        memcpy(exec_buf, f->encrypted_blob, f->blob_size);
        mj_aes_ctr_crypt(exec_buf, f->blob_size, f->key);

        int ret = g_exec_fn(exec_buf, f->blob_size, &eng->accumulator);
        if (ret != 0) {
            mj_secure_wipe(exec_buf, buf_size);
            free(exec_buf);
            return ret;
        }

        /* Update chain state with fragment output */
        mj_update_chain_state(eng->chain_state, (const uint8_t*)&eng->accumulator,
                              sizeof(eng->accumulator));

        /* Update accumulated hash: SHA-256(accumulated_hash || output || fragment_id) */
        {
            uint8_t hash_input[MJ_HASH_SIZE + sizeof(eng->accumulator) + 4];
            memcpy(hash_input, eng->accumulated_hash, MJ_HASH_SIZE);
            memcpy(hash_input + MJ_HASH_SIZE, &eng->accumulator, sizeof(eng->accumulator));
            hash_input[MJ_HASH_SIZE + sizeof(eng->accumulator) + 0] = (uint8_t)(current_id & 0xFF);
            hash_input[MJ_HASH_SIZE + sizeof(eng->accumulator) + 1] = (uint8_t)((current_id >> 8) & 0xFF);
            hash_input[MJ_HASH_SIZE + sizeof(eng->accumulator) + 2] = (uint8_t)((current_id >> 16) & 0xFF);
            hash_input[MJ_HASH_SIZE + sizeof(eng->accumulator) + 3] = (uint8_t)((current_id >> 24) & 0xFF);
            mj_sha256(hash_input, sizeof(hash_input), eng->accumulated_hash);
        }

        /* Roll key evolution after fragment execution */
        uint8_t output_hash[MJ_HASH_SIZE];
        mj_sha256((const uint8_t*)&eng->accumulator, sizeof(eng->accumulator), output_hash);
        key_evolution_roll(&ke_chain, output_hash, current_id);

        /* Wipe old key securely */
        mj_secure_wipe(prev_key, MJ_KEY_SIZE);

        /* Wipe execution buffer BEFORE advancing */
        mj_secure_wipe(exec_buf, buf_size);
        free(exec_buf);

        /* Save key for next iteration */
        memcpy(prev_key, f->key, MJ_KEY_SIZE);

        /* Advance to next fragment */
        current_id = f->next_fragment_id;
        visited++;
    }

    /* Wipe rolling key state */
    key_evolution_wipe(&ke_chain);
    mj_secure_wipe(prev_key, MJ_KEY_SIZE);

    return 0;
}
