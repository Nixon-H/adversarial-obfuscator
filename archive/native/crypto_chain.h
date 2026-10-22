#ifndef CRYPTO_CHAIN_H
#define CRYPTO_CHAIN_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#define CRYPTO_CHAIN_HASH_SIZE 32
#define CRYPTO_CHAIN_IV_SIZE 12
#define CRYPTO_CHAIN_NONCE_SIZE 16
#define CRYPTO_CHAIN_TAG_SIZE 16
#define CRYPTO_CHAIN_SECRET_SIZE 32

/* Execution-History-Bound Decryption (Item 89):
 * accumulated_hash is now used in key derivation:
 * Key = HKDF(chain_secret, prev_output_hash || accumulated_hash || fragment_id || nonce)
 * After decrypt: accumulated_hash = SHA-256(accumulated_hash || output || fragment_id)
 * Accumulator initialized to SHA-256("EXECUTION_HISTORY_V1")
 */

typedef struct {
    uint32_t fragment_id;
    uint32_t next_fragment_id;
    uint8_t  iv[CRYPTO_CHAIN_IV_SIZE];
    uint8_t  nonce[CRYPTO_CHAIN_NONCE_SIZE];
    uint8_t  prev_output_hash[CRYPTO_CHAIN_HASH_SIZE];
    uint8_t  output_signature[CRYPTO_CHAIN_HASH_SIZE];
    uint8_t  expected_mac[CRYPTO_CHAIN_TAG_SIZE];
    uint32_t encrypted_len;
    uint8_t  encrypted[];
} crypto_fragment_t;

typedef struct {
    crypto_fragment_t** fragments;
    uint32_t count;
    uint32_t current_idx;
    uint8_t chain_secret[CRYPTO_CHAIN_SECRET_SIZE];
    uint8_t last_output_hash[CRYPTO_CHAIN_HASH_SIZE];
    uint8_t accumulated_hash[CRYPTO_CHAIN_HASH_SIZE];
    uint8_t evolved_key[CRYPTO_CHAIN_HASH_SIZE];
    uint32_t roll_counter;
    int rolling_key_mode;
} crypto_chain_t;

bool crypto_chain_validate(
    crypto_fragment_t* fragment,
    const uint8_t prev_output_hash[CRYPTO_CHAIN_HASH_SIZE],
    const uint8_t chain_secret[CRYPTO_CHAIN_SECRET_SIZE]
);

bool crypto_chain_init(
    crypto_chain_t* chain,
    crypto_fragment_t** fragments,
    uint32_t count,
    const uint8_t chain_secret[CRYPTO_CHAIN_SECRET_SIZE]
);

crypto_fragment_t* crypto_chain_next(crypto_chain_t* chain);

bool crypto_chain_decrypt_current(
    crypto_chain_t* chain,
    uint8_t* output_buffer,
    size_t* output_len
);

bool crypto_chain_verify_accumulated(
    crypto_chain_t* chain,
    const uint8_t expected_hash[CRYPTO_CHAIN_HASH_SIZE]
);

size_t crypto_fragment_total_size(const crypto_fragment_t* frag);

#endif /* CRYPTO_CHAIN_H */
