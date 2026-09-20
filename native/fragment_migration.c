#include "fragment_migration.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Unwired experimental sim — not part of the supported build. */
#ifndef NIXON_EXPERIMENTAL
#error "This is an unwired experimental sim. Define NIXON_EXPERIMENTAL to compile it."
#endif

static void sha256_migrate(const uint8_t* data, size_t len, uint8_t hash[32]) {
    uint32_t h[8] = {
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
        0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
    };
    uint32_t w[64];
    uint32_t k[64] = {
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

    size_t new_len = len + 9;
    uint64_t bit_len = (uint64_t)len * 8;
    while (new_len % 64 != 0) new_len++;

    uint8_t* msg = (uint8_t*)calloc(new_len, 1);
    if (!msg) return;
    memcpy(msg, data, len);
    msg[len] = 0x80;
    for (int i = 0; i < 8; i++)
        msg[new_len - 8 + i] = (uint8_t)(bit_len >> (56 - i * 8));

    for (size_t chunk = 0; chunk < new_len; chunk += 64) {
        for (int i = 0; i < 16; i++) {
            w[i] = ((uint32_t)msg[chunk + i*4] << 24) |
                   ((uint32_t)msg[chunk + i*4 + 1] << 16) |
                   ((uint32_t)msg[chunk + i*4 + 2] << 8) |
                   ((uint32_t)msg[chunk + i*4 + 3]);
        }
        for (int i = 16; i < 64; i++) {
            uint32_t s0 = ((w[i-15] >> 7) | (w[i-15] << 25)) ^
                          ((w[i-15] >> 18) | (w[i-15] << 14)) ^
                          (w[i-15] >> 3);
            uint32_t s1 = ((w[i-2] >> 17) | (w[i-2] << 15)) ^
                          ((w[i-2] >> 19) | (w[i-2] << 13)) ^
                          (w[i-2] >> 10);
            w[i] = w[i-16] + s0 + w[i-7] + s1;
        }

        uint32_t a = h[0], b = h[1], c = h[2], d = h[3];
        uint32_t e = h[4], f = h[5], g = h[6], hh = h[7];

        for (int i = 0; i < 64; i++) {
            uint32_t S1 = ((e >> 6) | (e << 26)) ^
                          ((e >> 11) | (e << 21)) ^
                          ((e >> 25) | (e << 7));
            uint32_t ch = (e & f) ^ ((~e) & g);
            uint32_t temp1 = hh + S1 + ch + k[i] + w[i];
            uint32_t S0 = ((a >> 2) | (a << 30)) ^
                          ((a >> 13) | (a << 19)) ^
                          ((a >> 22) | (a << 10));
            uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
            uint32_t temp2 = S0 + maj;
            hh = g; g = f; f = e;
            e = d + temp1;
            d = c; c = b; b = a;
            a = temp1 + temp2;
        }
        h[0] += a; h[1] += b; h[2] += c; h[3] += d;
        h[4] += e; h[5] += f; h[6] += g; h[7] += hh;
    }

    for (int i = 0; i < 8; i++) {
        hash[i*4]   = (uint8_t)(h[i] >> 24);
        hash[i*4+1] = (uint8_t)(h[i] >> 16);
        hash[i*4+2] = (uint8_t)(h[i] >> 8);
        hash[i*4+3] = (uint8_t)(h[i] & 0xFF);
    }
    free(msg);
}

bool migration_serialize_state(
    uint32_t fragment_id,
    uint32_t migration_count,
    migration_platform_t current_platform,
    const uint8_t* state_data,
    uint32_t state_len,
    uint8_t output[/* MIGRATION_MAX_STATE_SIZE + 16 */],
    uint32_t* output_len
) {
    if (!output || !output_len) return false;
    if (state_len > MIGRATION_MAX_STATE_SIZE) return false;

    uint32_t offset = 0;
    memcpy(output + offset, &fragment_id, sizeof(uint32_t));
    offset += sizeof(uint32_t);
    memcpy(output + offset, &migration_count, sizeof(uint32_t));
    offset += sizeof(uint32_t);
    memcpy(output + offset, &current_platform, sizeof(uint32_t));
    offset += sizeof(uint32_t);
    memcpy(output + offset, &state_len, sizeof(uint32_t));
    offset += sizeof(uint32_t);
    if (state_len > 0) {
        memcpy(output + offset, state_data, state_len);
        offset += state_len;
    }

    sha256_migrate(output, offset, output + offset);
    offset += MIGRATION_HASH_SIZE;

    *output_len = offset;
    return true;
}

bool migration_deserialize_state(
    const uint8_t* data,
    uint32_t data_len,
    migration_state_t* out_state
) {
    if (!data || !out_state) return false;
    if (data_len < sizeof(uint32_t) * 4 + MIGRATION_HASH_SIZE) return false;

    uint32_t offset = 0;
    memcpy(&out_state->fragment_id, data + offset, sizeof(uint32_t));
    offset += sizeof(uint32_t);
    memcpy(&out_state->migration_count, data + offset, sizeof(uint32_t));
    offset += sizeof(uint32_t);
    uint32_t plat;
    memcpy(&plat, data + offset, sizeof(uint32_t));
    offset += sizeof(uint32_t);
    out_state->current_platform = (migration_platform_t)plat;
    memcpy(&out_state->state_len, data + offset, sizeof(uint32_t));
    offset += sizeof(uint32_t);

    if (out_state->state_len > MIGRATION_MAX_STATE_SIZE) return false;
    if (offset + out_state->state_len + MIGRATION_HASH_SIZE > data_len) return false;

    if (out_state->state_len > 0) {
        memcpy(out_state->state, data + offset, out_state->state_len);
        offset += out_state->state_len;
    }

    memcpy(out_state->checksum, data + offset, MIGRATION_HASH_SIZE);
    return true;
}

bool migration_derive_platform_key(
    uint32_t fragment_id,
    migration_platform_t from,
    migration_platform_t to,
    const uint8_t secret[32],
    uint8_t output_key[32]
) {
    uint8_t data[sizeof(uint32_t) + sizeof(uint32_t) + sizeof(uint32_t) + 32];
    memcpy(data, &fragment_id, sizeof(uint32_t));
    memcpy(data + sizeof(uint32_t), &from, sizeof(uint32_t));
    memcpy(data + sizeof(uint32_t) * 2, &to, sizeof(uint32_t));
    memcpy(data + sizeof(uint32_t) * 3, secret, 32);
    sha256_migrate(data, sizeof(data), output_key);
    return true;
}

bool migration_verify_checksum(
    const migration_state_t* state,
    const uint8_t expected[MIGRATION_HASH_SIZE]
) {
    if (!state || !expected) return false;
    return memcmp(state->checksum, expected, MIGRATION_HASH_SIZE) == 0;
}
