#ifndef SELF_HEALING_H
#define SELF_HEALING_H

#include <stdint.h>
#include <stddef.h>

#define HEALING_NUM_REDUNDANT_COPIES 3
#define HEALING_MAX_REGIONS 32
#define HEALING_MAX_NAME_LEN 64

typedef struct {
    char name[HEALING_MAX_NAME_LEN];
    uint8_t *data;
    size_t data_len;
    uint8_t *redundant_copies[HEALING_NUM_REDUNDANT_COPIES];
    uint64_t expected_checksum;
    int damaged;
} HealingRegion;

typedef struct {
    HealingRegion regions[HEALING_MAX_REGIONS];
    int num_regions;
    int running;
} SelfHealingCtx;

#ifdef __cplusplus
extern "C" {
#endif

void healing_init(SelfHealingCtx *ctx);
int healing_register_region(SelfHealingCtx *ctx, const char *name, const uint8_t *data, size_t data_len);
uint64_t healing_checksum(const uint8_t *data, size_t len);
int healing_verify_and_heal_all(SelfHealingCtx *ctx);
void healing_tamper_region(SelfHealingCtx *ctx, const char *name);
int healing_get_region_data(SelfHealingCtx *ctx, const char *name, uint8_t *out, size_t *out_len);

#ifdef __cplusplus
}
#endif

#endif
