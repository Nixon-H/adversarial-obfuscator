#include "crypto_chain.h"
#include "key_evolution.h"
#include <string.h>
#include <stdlib.h>

extern void sha256_hash(const uint8_t *data, size_t len, uint8_t hash[32]);
extern void sha256_hash2(const uint8_t *d1, size_t l1, const uint8_t *d2, size_t l2, uint8_t hash[32]);

static void derive_fragment_key_with_history(
    const uint8_t prev_output_hash[32],
    const uint8_t chain_secret[32],
    uint32_t fragment_id,
    const uint8_t nonce[16],
    const uint8_t accumulated_hash[32],
    uint8_t output_key[32]
);

static void hkdf_expand(
    const uint8_t prk[32],
    const uint8_t* info, size_t info_len,
    uint8_t output[32]
) {
    uint8_t mac_input[32 + info_len + 1];
    memcpy(mac_input, prk, 32);
    if (info_len > 0)
        memcpy(mac_input + 32, info, info_len);
    mac_input[32 + info_len] = 0x01;
    sha256_hash(mac_input, 32 + info_len + 1, output);
}

static void derive_fragment_key(
    const uint8_t prev_output_hash[32],
    const uint8_t chain_secret[32],
    uint32_t fragment_id,
    const uint8_t nonce[16],
    uint8_t output_key[32]
) {
    derive_fragment_key_with_history(prev_output_hash, chain_secret,
                                     fragment_id, nonce,
                                     NULL, output_key);
}

static void derive_fragment_key_with_history(
    const uint8_t prev_output_hash[32],
    const uint8_t chain_secret[32],
    uint32_t fragment_id,
    const uint8_t nonce[16],
    const uint8_t accumulated_hash[32],
    uint8_t output_key[32]
) {
    uint8_t genesis_hash[32];
    uint8_t actual_prev[32];

    int all_zero = 1;
    for (int i = 0; i < 32; i++) {
        if (prev_output_hash[i] != 0) { all_zero = 0; break; }
    }

    if (all_zero) {
        sha256_hash2(chain_secret, 32, (const uint8_t*)"GENESIS", 7, genesis_hash);
        memcpy(actual_prev, genesis_hash, 32);
    } else {
        memcpy(actual_prev, prev_output_hash, 32);
    }

    /* If accumulated_hash is provided, include it in key derivation */
    int use_history = (accumulated_hash != NULL);
    int info_len = use_history ? (32 + 32 + 4 + 16) : (32 + 4 + 16);
    uint8_t info[32 + 32 + 4 + 16];

    memcpy(info, actual_prev, 32);
    if (use_history) {
        memcpy(info + 32, accumulated_hash, 32);
        info[64] = (uint8_t)((fragment_id >> 24) & 0xFF);
        info[65] = (uint8_t)((fragment_id >> 16) & 0xFF);
        info[66] = (uint8_t)((fragment_id >> 8) & 0xFF);
        info[67] = (uint8_t)(fragment_id & 0xFF);
        memcpy(info + 68, nonce, 16);
    } else {
        info[32] = (uint8_t)((fragment_id >> 24) & 0xFF);
        info[33] = (uint8_t)((fragment_id >> 16) & 0xFF);
        info[34] = (uint8_t)((fragment_id >> 8) & 0xFF);
        info[35] = (uint8_t)(fragment_id & 0xFF);
        memcpy(info + 36, nonce, 16);
    }

    hkdf_expand(chain_secret, info, info_len, output_key);
}

static int aes_gcm_decrypt(
    const uint8_t* encrypted, uint32_t encrypted_len,
    const uint8_t key[32],
    const uint8_t iv[12],
    uint32_t fragment_id,
    uint32_t next_fragment_id,
    const uint8_t expected_tag[16],
    uint8_t* output_buffer
) {
    (void)iv;
    uint8_t aad[8];
    aad[0] = (uint8_t)((fragment_id >> 24) & 0xFF);
    aad[1] = (uint8_t)((fragment_id >> 16) & 0xFF);
    aad[2] = (uint8_t)((fragment_id >> 8) & 0xFF);
    aad[3] = (uint8_t)(fragment_id & 0xFF);
    aad[4] = (uint8_t)((next_fragment_id >> 24) & 0xFF);
    aad[5] = (uint8_t)((next_fragment_id >> 16) & 0xFF);
    aad[6] = (uint8_t)((next_fragment_id >> 8) & 0xFF);
    aad[7] = (uint8_t)(next_fragment_id & 0xFF);

    uint8_t digest[32];
    uint8_t state[32];
    memcpy(state, key, 32);

    sha256_hash2(state, 32, (const uint8_t*)"AES-GCM-KDF", 11, digest);

    uint8_t stream_key[16];
    memcpy(stream_key, digest, 16);

    for (uint32_t i = 0; i < encrypted_len; i++) {
        output_buffer[i] = encrypted[i] ^ stream_key[i % 16];
    }

    uint8_t computed_tag[32];
    sha256_hash2(output_buffer, encrypted_len, aad, 8, computed_tag);

    for (int i = 0; i < 16; i++) {
        if (computed_tag[i] != expected_tag[i])
            return 0;
    }

    return 1;
}

bool crypto_chain_validate(
    crypto_fragment_t* fragment,
    const uint8_t prev_output_hash[32],
    const uint8_t chain_secret[32]
) {
    uint8_t expected_key[32];
    derive_fragment_key(prev_output_hash, chain_secret,
                        fragment->fragment_id, fragment->nonce,
                        expected_key);

    uint8_t* temp = (uint8_t*)malloc(fragment->encrypted_len);
    if (!temp) return false;

    int ok = aes_gcm_decrypt(
        fragment->encrypted, fragment->encrypted_len,
        expected_key, fragment->iv,
        fragment->fragment_id, fragment->next_fragment_id,
        fragment->expected_mac, temp
    );

    free(temp);
    return ok;
}

bool crypto_chain_init(
    crypto_chain_t* chain,
    crypto_fragment_t** fragments,
    uint32_t count,
    const uint8_t chain_secret[32]
) {
    if (!chain || !fragments || count == 0)
        return false;

    chain->fragments = fragments;
    chain->count = count;
    chain->current_idx = 0;
    chain->rolling_key_mode = 0;
    chain->roll_counter = 0;

    memcpy(chain->chain_secret, chain_secret, 32);
    memset(chain->last_output_hash, 0, 32);
    sha256_hash((const uint8_t*)"EXECUTION_HISTORY_V1", 20, chain->accumulated_hash);
    memset(chain->evolved_key, 0, 32);

    uint8_t genesis_input[39];
    memcpy(genesis_input, chain_secret, 32);
    memcpy(genesis_input + 32, "GENESIS", 7);
    sha256_hash(genesis_input, 39, chain->last_output_hash);

    /* Initialize rolling key state */
    memcpy(chain->evolved_key, chain_secret, 32);
    chain->roll_counter = 0;

    return true;
}

crypto_fragment_t* crypto_chain_next(crypto_chain_t* chain) {
    if (!chain || chain->current_idx >= chain->count)
        return NULL;

    crypto_fragment_t* frag = chain->fragments[chain->current_idx];
    chain->current_idx++;
    return frag;
}

bool crypto_chain_decrypt_current(
    crypto_chain_t* chain,
    uint8_t* output_buffer,
    size_t* output_len
) {
    if (!chain || chain->current_idx == 0)
        return false;

    uint32_t idx = chain->current_idx - 1;
    crypto_fragment_t* frag = chain->fragments[idx];

    const uint8_t* effective_secret = chain->rolling_key_mode
        ? chain->evolved_key
        : chain->chain_secret;

    uint8_t expected_hash[32];
    /* Use history-bound key derivation: includes accumulated_hash */
    derive_fragment_key_with_history(
        chain->last_output_hash, effective_secret,
        frag->fragment_id, frag->nonce,
        chain->accumulated_hash, expected_hash
    );

    uint8_t* temp = (uint8_t*)malloc(frag->encrypted_len);
    if (!temp) return false;

    int ok = aes_gcm_decrypt(
        frag->encrypted, frag->encrypted_len,
        expected_hash, frag->iv,
        frag->fragment_id, frag->next_fragment_id,
        frag->expected_mac, temp
    );

    if (ok) {
        sha256_hash(temp, frag->encrypted_len, chain->last_output_hash);
        sha256_hash2(chain->accumulated_hash, 32, temp, frag->encrypted_len,
                     chain->accumulated_hash);

        if (chain->rolling_key_mode) {
            key_evolution_roll((key_evolution_chain_t*)chain,
                               chain->last_output_hash,
                               frag->fragment_id);
        }

        if (output_buffer && output_len) {
            size_t copy_len = frag->encrypted_len;
            if (*output_len < copy_len)
                copy_len = *output_len;
            memcpy(output_buffer, temp, copy_len);
            *output_len = copy_len;
        }
    }

    free(temp);
    return ok;
}

bool crypto_chain_verify_accumulated(
    crypto_chain_t* chain,
    const uint8_t expected_hash[32]
) {
    if (!chain) return false;
    return memcmp(chain->accumulated_hash, expected_hash, 32) == 0;
}

size_t crypto_fragment_total_size(const crypto_fragment_t* frag) {
    if (!frag) return 0;
    return sizeof(crypto_fragment_t) + frag->encrypted_len;
}
