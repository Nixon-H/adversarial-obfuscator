// Nixon white-box Feistel core — shared by WHITEBOX_ONLY and FULL builds.
// 8-round Feistel, 16-byte blocks, real AES S-box core, SHA-256-expanded
// keyed S-boxes (2 per round) + diffusion masks. Raw key wiped after table
// derivation: only lookup tables persist, so no key bytes exist at rest.
// Obfuscation-grade white-box (raises key extraction to table inversion),
// composed with AES-CTR + runtime decrypt — never the sole secrecy layer.

#ifndef NIXON_WB_FEISTEL_H
#define NIXON_WB_FEISTEL_H

#include <cstdint>
#include <cstdio>
#include <ctime>
#include <vector>
#include <algorithm>

namespace nixon_wb {
inline uint32_t wb_rotr(uint32_t x, int n) { return (x >> n) | (x << (32 - n)); }
extern const uint32_t WB_K[64];
void wb_sha256(const uint8_t* msg, size_t len, uint8_t out[32]);
extern const uint8_t WB_AES_SBOX[256];
extern const uint8_t WB_AES_INV_SBOX[256];
#define WB_ROUNDS 8
#define WB_BLOCK 16
struct WbTables {
    uint8_t sbox[WB_ROUNDS][2][256];
    uint8_t inv_sbox[WB_ROUNDS][2][256];
    uint8_t diffmask[WB_ROUNDS][WB_BLOCK];
};
void wb_derive_tables(const uint8_t key16[16], uint64_t salt, WbTables& t);
void wb_feistel_block(const WbTables& t, uint8_t blk[WB_BLOCK], bool invert);
} // namespace nixon_wb

#endif
