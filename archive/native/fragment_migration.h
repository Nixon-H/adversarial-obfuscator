#ifndef FRAGMENT_MIGRATION_H
#define FRAGMENT_MIGRATION_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#define MIGRATION_MAX_PLATFORMS 4
#define MIGRATION_HASH_SIZE 32
#define MIGRATION_MAX_STATE_SIZE 4096

typedef enum {
    PLATFORM_X86 = 0,
    PLATFORM_ARM = 1,
    PLATFORM_WASM = 2
} migration_platform_t;

typedef struct {
    uint32_t fragment_id;
    uint32_t migration_count;
    migration_platform_t current_platform;
    uint32_t state_len;
    uint8_t  state[MIGRATION_MAX_STATE_SIZE];
    uint8_t  checksum[MIGRATION_HASH_SIZE];
} migration_state_t;

bool migration_serialize_state(
    uint32_t fragment_id,
    uint32_t migration_count,
    migration_platform_t current_platform,
    const uint8_t* state_data,
    uint32_t state_len,
    uint8_t output[/* MIGRATION_MAX_STATE_SIZE + 16 */],
    uint32_t* output_len
);

bool migration_deserialize_state(
    const uint8_t* data,
    uint32_t data_len,
    migration_state_t* out_state
);

bool migration_derive_platform_key(
    uint32_t fragment_id,
    migration_platform_t from,
    migration_platform_t to,
    const uint8_t secret[32],
    uint8_t output_key[32]
);

bool migration_verify_checksum(
    const migration_state_t* state,
    const uint8_t expected[MIGRATION_HASH_SIZE]
);

#endif /* FRAGMENT_MIGRATION_H */
