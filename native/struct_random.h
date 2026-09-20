#ifndef STRUCT_RANDOM_H
#define STRUCT_RANDOM_H

#include <stdint.h>
#include <stddef.h>

#define STRUCT_RANDOM_MAX_FIELDS 64

typedef struct {
    int num_fields;
    int perm[STRUCT_RANDOM_MAX_FIELDS];
    uint64_t seed;
} StructRandomCtx;

#ifdef __cplusplus
extern "C" {
#endif

void struct_random_init(StructRandomCtx *ctx, uint64_t seed);
int struct_random_permute_fields(StructRandomCtx *ctx, int num_fields);
int struct_random_map_slot(StructRandomCtx *ctx, int original_index);
int struct_random_unmap_slot(StructRandomCtx *ctx, int permuted_index, int num_fields);
uint64_t struct_random_current_seed(StructRandomCtx *ctx);

#ifdef __cplusplus
}
#endif

#endif
