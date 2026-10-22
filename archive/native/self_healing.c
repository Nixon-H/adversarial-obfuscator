#include "self_healing.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <pthread.h>

static uint64_t splitmix64(uint64_t *state) {
    uint64_t z = (*state += 0x9E3779B97F4A7C15ULL);
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31);
}

void healing_init(SelfHealingCtx *ctx) {
    memset(ctx, 0, sizeof(*ctx));
    ctx->running = 1;
}

uint64_t healing_checksum(const uint8_t *data, size_t len) {
    uint64_t h = 0xCBF29CE484222325ULL;  // FNV offset basis
    for (size_t i = 0; i < len; i++) {
        h ^= data[i];
        h *= 0x100000001B3ULL;  // FNV prime
    }
    return h;
}

static HealingRegion *find_region(SelfHealingCtx *ctx, const char *name) {
    for (int i = 0; i < ctx->num_regions; i++) {
        if (strcmp(ctx->regions[i].name, name) == 0) {
            return &ctx->regions[i];
        }
    }
    return NULL;
}

int healing_register_region(SelfHealingCtx *ctx, const char *name,
                            const uint8_t *data, size_t data_len) {
    if (ctx->num_regions >= HEALING_MAX_REGIONS) {
        return -1;
    }
    if (name == NULL || data == NULL || data_len == 0) {
        return -1;
    }
    int idx = ctx->num_regions;
    HealingRegion *r = &ctx->regions[idx];

    size_t name_len = strlen(name);
    if (name_len >= HEALING_MAX_NAME_LEN) {
        name_len = HEALING_MAX_NAME_LEN - 1;
    }
    memcpy(r->name, name, name_len);
    r->name[name_len] = '\0';

    r->data_len = data_len;
    uint64_t seed = 0;
    for (size_t i = 0; i < data_len; i++) {
        seed ^= ((uint64_t)data[i]) << ((i % 8) * 8);
    }
    seed ^= (uint64_t)(uintptr_t)data;
    uint64_t sm = seed;
    r->data = (uint8_t *)malloc(data_len);
    memcpy(r->data, data, data_len);

    r->expected_checksum = healing_checksum(data, data_len);

    for (int c = 0; c < HEALING_NUM_REDUNDANT_COPIES; c++) {
        r->redundant_copies[c] = (uint8_t *)malloc(data_len);
        uint64_t x = splitmix64(&sm);
        for (size_t i = 0; i < data_len; i++) {
            r->redundant_copies[c][i] = data[i] ^ (uint8_t)(x >> (i % 8) * 8);
            x = splitmix64(&sm);
        }
    }
    r->damaged = 0;
    ctx->num_regions++;
    return 0;
}

int healing_verify_and_heal_all(SelfHealingCtx *ctx) {
    int all_restored = 1;
    for (int i = 0; i < ctx->num_regions; i++) {
        HealingRegion *r = &ctx->regions[i];
        uint64_t actual = healing_checksum(r->data, r->data_len);
        if (actual != r->expected_checksum) {
            r->damaged = 1;
            int restored = 0;
            for (int c = 0; c < HEALING_NUM_REDUNDANT_COPIES; c++) {
                uint64_t copy_cs = healing_checksum(r->redundant_copies[c], r->data_len);
                if (copy_cs == r->expected_checksum) {
                    memcpy(r->data, r->redundant_copies[c], r->data_len);
                    r->damaged = 0;
                    restored = 1;
                    break;
                }
            }
            if (!restored) {
                all_restored = 0;
            }
        }
    }
    return all_restored;
}

void healing_tamper_region(SelfHealingCtx *ctx, const char *name) {
    HealingRegion *r = find_region(ctx, name);
    if (r == NULL || r->data_len == 0) return;
    r->data[0] ^= 0xFF;
}

int healing_get_region_data(SelfHealingCtx *ctx, const char *name,
                            uint8_t *out, size_t *out_len) {
    HealingRegion *r = find_region(ctx, name);
    if (r == NULL) return -1;
    if (*out_len < r->data_len) return -1;
    *out_len = r->data_len;
    memcpy(out, r->data, r->data_len);
    return 0;
}
