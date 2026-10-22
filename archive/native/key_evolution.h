#ifndef KEY_EVOLUTION_H
#define KEY_EVOLUTION_H

#include <stdint.h>
#include <stddef.h>

#define KEY_EVOLUTION_HASH_SIZE 32

typedef struct {
    uint8_t evolved_key[KEY_EVOLUTION_HASH_SIZE];
    uint32_t roll_counter;
    uint8_t initialized;
} key_evolution_chain_t;

void key_evolution_init(key_evolution_chain_t* chain, const uint8_t seed[KEY_EVOLUTION_HASH_SIZE]);
void key_evolution_roll(key_evolution_chain_t* chain, const uint8_t output_hash[KEY_EVOLUTION_HASH_SIZE], uint32_t fragment_id);
void key_evolution_wipe(key_evolution_chain_t* chain);
int key_evolution_verify(const key_evolution_chain_t* chain, const uint8_t expected[KEY_EVOLUTION_HASH_SIZE]);

#endif /* KEY_EVOLUTION_H */
