#include "struct_random.h"
#include <string.h>

void struct_random_init(StructRandomCtx *ctx, uint64_t seed) {
    memset(ctx, 0, sizeof(*ctx));
    ctx->seed = seed;
    ctx->num_fields = 0;
}

static uint64_t prng_next(uint64_t *state) {
    *state = (*state * 6364136223846793005ULL + 1442695040888963407ULL) & 0xFFFFFFFFFFFFFFFFULL;
    return *state;
}

int struct_random_permute_fields(StructRandomCtx *ctx, int num_fields) {
    if (num_fields <= 0 || num_fields > STRUCT_RANDOM_MAX_FIELDS) {
        return -1;
    }
    ctx->num_fields = num_fields;
    uint64_t rng = ctx->seed;

    // Identity permutation
    for (int i = 0; i < num_fields; i++) {
        ctx->perm[i] = i;
    }

    // Fisher-Yates shuffle
    for (int i = num_fields - 1; i > 0; i--) {
        uint64_t rv = prng_next(&rng);
        int j = (int)(rv % (uint64_t)(i + 1));
        int tmp = ctx->perm[i];
        ctx->perm[i] = ctx->perm[j];
        ctx->perm[j] = tmp;
    }

    ctx->seed = rng;
    return 0;
}

int struct_random_map_slot(StructRandomCtx *ctx, int original_index) {
    if (original_index < 0 || original_index >= ctx->num_fields) {
        return -1;
    }
    return ctx->perm[original_index];
}

int struct_random_unmap_slot(StructRandomCtx *ctx, int permuted_index, int num_fields) {
    for (int i = 0; i < ctx->num_fields && i < num_fields; i++) {
        if (ctx->perm[i] == permuted_index) {
            return i;
        }
    }
    return -1;
}

uint64_t struct_random_current_seed(StructRandomCtx *ctx) {
    return ctx->seed;
}
