#include "key_evolution.h"
#include <string.h>

extern void sha256_hash(const uint8_t *data, size_t len, uint8_t hash[32]);
extern void sha256_hash2(const uint8_t *d1, size_t l1, const uint8_t *d2, size_t l2, uint8_t hash[32]);

void key_evolution_init(key_evolution_chain_t* chain, const uint8_t seed[KEY_EVOLUTION_HASH_SIZE]) {
    if (!chain) return;
    memcpy(chain->evolved_key, seed, KEY_EVOLUTION_HASH_SIZE);
    chain->roll_counter = 0;
    chain->initialized = 1;
}

void key_evolution_roll(key_evolution_chain_t* chain,
                         const uint8_t output_hash[KEY_EVOLUTION_HASH_SIZE],
                         uint32_t fragment_id) {
    if (!chain || !chain->initialized) return;

    // key_{n+1} = SHA-256(key_n || output_hash || fragment_id || counter)
    uint8_t input[KEY_EVOLUTION_HASH_SIZE + KEY_EVOLUTION_HASH_SIZE + 4 + 4];
    memcpy(input, chain->evolved_key, KEY_EVOLUTION_HASH_SIZE);
    memcpy(input + KEY_EVOLUTION_HASH_SIZE, output_hash, KEY_EVOLUTION_HASH_SIZE);
    input[KEY_EVOLUTION_HASH_SIZE * 2 + 0] = (uint8_t)(fragment_id & 0xFF);
    input[KEY_EVOLUTION_HASH_SIZE * 2 + 1] = (uint8_t)((fragment_id >> 8) & 0xFF);
    input[KEY_EVOLUTION_HASH_SIZE * 2 + 2] = (uint8_t)((fragment_id >> 16) & 0xFF);
    input[KEY_EVOLUTION_HASH_SIZE * 2 + 3] = (uint8_t)((fragment_id >> 24) & 0xFF);
    input[KEY_EVOLUTION_HASH_SIZE * 2 + 4] = (uint8_t)(chain->roll_counter & 0xFF);
    input[KEY_EVOLUTION_HASH_SIZE * 2 + 5] = (uint8_t)((chain->roll_counter >> 8) & 0xFF);
    input[KEY_EVOLUTION_HASH_SIZE * 2 + 6] = (uint8_t)((chain->roll_counter >> 16) & 0xFF);
    input[KEY_EVOLUTION_HASH_SIZE * 2 + 7] = (uint8_t)((chain->roll_counter >> 24) & 0xFF);

    uint8_t new_key[KEY_EVOLUTION_HASH_SIZE];
    sha256_hash(input, sizeof(input), new_key);

    memcpy(chain->evolved_key, new_key, KEY_EVOLUTION_HASH_SIZE);
    chain->roll_counter++;
}

void key_evolution_wipe(key_evolution_chain_t* chain) {
    if (!chain) return;
    volatile uint8_t* p = (volatile uint8_t*)chain->evolved_key;
    for (size_t i = 0; i < KEY_EVOLUTION_HASH_SIZE; i++)
        p[i] = 0;
    chain->roll_counter = 0;
    chain->initialized = 0;
}

int key_evolution_verify(const key_evolution_chain_t* chain,
                          const uint8_t expected[KEY_EVOLUTION_HASH_SIZE]) {
    if (!chain || !chain->initialized) return 0;
    return memcmp(chain->evolved_key, expected, KEY_EVOLUTION_HASH_SIZE) == 0;
}
