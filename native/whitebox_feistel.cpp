// Nixon white-box Feistel tables: SHA-256 expansion, AES S-box core,
// keyed Fisher-Yates S-boxes (2/round) + diffusion masks, Feistel rounds.

#include "whitebox_feistel.h"

namespace nixon_wb {
const uint32_t WB_K[64] = {
    0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
    0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
    0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
    0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
    0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
    0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
    0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
    0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
};
void wb_sha256(const uint8_t* msg, size_t len, uint8_t out[32]) {
    uint32_t h[8] = {0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
    uint64_t bitlen = (uint64_t)len * 8;
    size_t new_len = len + 1;
    while (new_len % 64 != 56) new_len++;
    std::vector<uint8_t> m(new_len + 8, 0);
    for (size_t i = 0; i < len; ++i) m[i] = msg[i];
    m[len] = 0x80;
    for (int i = 0; i < 8; ++i) m[new_len + i] = (uint8_t)(bitlen >> (56 - 8 * i));
    for (size_t off = 0; off < m.size(); off += 64) {
        uint32_t w[64];
        for (int i = 0; i < 16; ++i)
            w[i] = ((uint32_t)m[off+4*i] << 24) | ((uint32_t)m[off+4*i+1] << 16) |
                   ((uint32_t)m[off+4*i+2] << 8) | (uint32_t)m[off+4*i+3];
        for (int i = 16; i < 64; ++i) {
            uint32_t s0 = wb_rotr(w[i-15],7) ^ wb_rotr(w[i-15],18) ^ (w[i-15] >> 3);
            uint32_t s1 = wb_rotr(w[i-2],17) ^ wb_rotr(w[i-2],19) ^ (w[i-2] >> 10);
            w[i] = w[i-16] + s0 + w[i-7] + s1;
        }
        uint32_t a=h[0],b=h[1],c=h[2],d=h[3],e=h[4],f=h[5],g=h[6],hh=h[7];
        for (int i = 0; i < 64; ++i) {
            uint32_t S1 = wb_rotr(e,6) ^ wb_rotr(e,11) ^ wb_rotr(e,25);
            uint32_t ch = (e & f) ^ ((~e) & g);
            uint32_t t1 = hh + S1 + ch + WB_K[i] + w[i];
            uint32_t S0 = wb_rotr(a,2) ^ wb_rotr(a,13) ^ wb_rotr(a,22);
            uint32_t mj = (a & b) ^ (a & c) ^ (b & c);
            uint32_t t2 = S0 + mj;
            hh=g; g=f; f=e; e=d+t1; d=c; c=b; b=a; a=t1+t2;
        }
        h[0]+=a; h[1]+=b; h[2]+=c; h[3]+=d; h[4]+=e; h[5]+=f; h[6]+=g; h[7]+=hh;
    }
    for (int i = 0; i < 8; ++i) {
        out[4*i]=(uint8_t)(h[i]>>24); out[4*i+1]=(uint8_t)(h[i]>>16);
        out[4*i+2]=(uint8_t)(h[i]>>8); out[4*i+3]=(uint8_t)h[i];
    }
}
const uint8_t WB_AES_SBOX[256] = {
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
void wb_derive_tables(const uint8_t key16[16], uint64_t salt, WbTables& t) {
    uint8_t seed[24];
    for (int i = 0; i < 16; ++i) seed[i] = key16[i];
    for (int i = 0; i < 8; ++i) seed[16+i] = (uint8_t)(salt >> (8*i));
    uint8_t stream[32];
    static uint8_t pool[WB_ROUNDS * 2 * 256 + WB_ROUNDS * WB_BLOCK];
    size_t got = 0, ctr = 0;
    while (got < sizeof(pool)) {
        uint8_t in[28];
        for (int i = 0; i < 24; ++i) in[i] = seed[i];
        in[24]=(uint8_t)ctr; in[25]=(uint8_t)(ctr>>8);
        in[26]=(uint8_t)(ctr>>16); in[27]=(uint8_t)(ctr>>24);
        wb_sha256(in, 28, stream);
        size_t take = sizeof(pool) - got < 32 ? sizeof(pool) - got : 32;
        for (size_t i = 0; i < take; ++i) pool[got+i] = stream[i];
        got += take; ctr++;
    }
    size_t p = 0;
    for (int r = 0; r < WB_ROUNDS; ++r) {
        for (int k = 0; k < 2; ++k) {
            uint8_t perm[256];
            for (int i = 0; i < 256; ++i) perm[i] = (uint8_t)i;
            for (int i = 255; i > 0; --i) {
                uint8_t rnd = pool[p++ % sizeof(pool)];
                int j = rnd % (i + 1);
                uint8_t tmp = perm[i]; perm[i] = perm[j]; perm[j] = tmp;
            }
            for (int i = 0; i < 256; ++i) t.sbox[r][k][i] = perm[WB_AES_SBOX[i]];
            // Inverse of composed table: inv[y] = x s.t. sbox[x] == y.
            // AES S-box is a permutation so this always terminates.
            for (int i = 0; i < 256; ++i) {
                for (int j = 0; j < 256; ++j)
                    if (t.sbox[r][k][j] == (uint8_t)i) { t.inv_sbox[r][k][i] = (uint8_t)j; break; }
            }
        }
        for (int i = 0; i < WB_BLOCK; ++i) t.diffmask[r][i] = pool[p++ % sizeof(pool)];
    }
    volatile uint8_t* vp = pool;
    for (size_t i = 0; i < sizeof(pool); ++i) vp[i] = 0;
}
void wb_feistel_block(const WbTables& t, uint8_t blk[WB_BLOCK], bool invert) {
    uint8_t L[8], R[8];
    for (int i = 0; i < 8; ++i) { L[i] = blk[i]; R[i] = blk[8+i]; }
    if (!invert) {
        for (int r = 0; r < WB_ROUNDS; ++r) {
            uint8_t F[8];
            for (int i = 0; i < 8; ++i) {
                uint8_t x = R[i] ^ t.diffmask[r][i];
                x = t.sbox[r][0][x];
                x = WB_AES_SBOX[x];
                x = t.sbox[r][1][x];
                F[i] = x ^ t.diffmask[r][8+i];
            }
            uint8_t nL[8], nR[8];
            for (int i = 0; i < 8; ++i) { nL[i] = R[i]; nR[i] = (uint8_t)(L[i] ^ F[i]); }
            for (int i = 0; i < 8; ++i) { L[i] = nL[i]; R[i] = nR[i]; }
        }
    } else {
        for (int r = WB_ROUNDS - 1; r >= 0; --r) {
            // Forward step produced (nL,nR) = (R, L^F(R,mask_r)).
            // Invert with current (L,R)=(nL,nR): R_prev = L, L_prev = R ^ F(L).
            uint8_t F[8];
            for (int i = 0; i < 8; ++i) {
                uint8_t x = L[i] ^ t.diffmask[r][i];
                x = t.sbox[r][0][x];
                x = WB_AES_SBOX[x];
                x = t.sbox[r][1][x];
                F[i] = x ^ t.diffmask[r][8+i];
            }
            uint8_t pL[8], pR[8];
            for (int i = 0; i < 8; ++i) { pR[i] = L[i]; pL[i] = (uint8_t)(R[i] ^ F[i]); }
            for (int i = 0; i < 8; ++i) { L[i] = pL[i]; R[i] = pR[i]; }
        }
    }
    for (int i = 0; i < 8; ++i) { blk[i] = L[i]; blk[8+i] = R[i]; }
}
} // namespace nixon_wb
