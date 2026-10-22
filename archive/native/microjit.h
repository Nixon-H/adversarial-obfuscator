/* microjit.h — Micro-JIT Fragment Reassembly Engine
 *
 * Ephemeral execution reconstruction for protected binaries.
 * Memory never contains the full algorithm — fragments are
 * decrypted, executed, and wiped one at a time.
 *
 * Fragment A: decrypt -> execute -> wipe
 * Fragment B: decrypt -> execute -> wipe
 * Fragment C: decrypt -> execute -> wipe
 */

#ifndef MICROJIT_H
#define MICROJIT_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Export macro for shared library visibility */
#if defined(_WIN32) || defined(_WIN64)
#define MJ_EXPORT __declspec(dllexport)
#else
#define MJ_EXPORT __attribute__((visibility("default")))
#endif

/* ---- Constants -------------------------------------------------------- */

#define MJ_MAX_FRAGMENTS     64
#define MJ_KEY_SIZE          32
#define MJ_HASH_SIZE         32
#define MJ_MAX_BLOB_SIZE     4096
#define MJ_MAX_EXEC_BUFFER   4096

/* ---- Fragment descriptor --------------------------------------------- */

typedef struct {
    uint8_t*  encrypted_blob;
    size_t    blob_size;
    uint8_t   key[MJ_KEY_SIZE];
    void*     execution_buffer;
    size_t    buffer_size;
    int       next_fragment_id;
    int       is_last;
} mj_fragment_t;

/* ---- Fragment engine state -------------------------------------------- */

typedef struct {
    mj_fragment_t fragments[MJ_MAX_FRAGMENTS];
    int           fragment_count;
    int           current_fragment;
    uint8_t       chain_key[MJ_KEY_SIZE];
    uint8_t       chain_state[MJ_HASH_SIZE];
    uint8_t       accumulated_hash[MJ_HASH_SIZE];
    uint64_t      accumulator;
    int           initialized;
} mj_engine_t;

/* ---- Lifecycle -------------------------------------------------------- */

/* Initialize engine with chain key and fragment descriptors */
MJ_EXPORT void mj_engine_init(mj_engine_t* eng,
                              const uint8_t* chain_key,
                              size_t chain_key_len);

/* Add a fragment to the engine */
MJ_EXPORT int mj_engine_add_fragment(mj_engine_t* eng,
                                     const uint8_t* encrypted_blob,
                                     size_t blob_size,
                                     int next_fragment_id);

/* ---- Execution --------------------------------------------------------- */

/* Run the entire fragment chain sequentially */
MJ_EXPORT int mj_engine_execute_all(mj_engine_t* eng);

/* Run a single fragment (decrypt -> execute -> wipe) */
MJ_EXPORT int mj_engine_execute_one(mj_engine_t* eng, int fragment_id);

/* ---- Utility ----------------------------------------------------------- */

/* Derive fragment key: HMAC-SHA256(chain_key, chain_state || accumulated_hash || fragment_id) */
MJ_EXPORT void mj_derive_fragment_key(const uint8_t chain_key[MJ_KEY_SIZE],
                                      const uint8_t chain_state[MJ_HASH_SIZE],
                                      int fragment_id,
                                      uint8_t output_key[MJ_KEY_SIZE]);

/* Derive fragment key with execution history binding */
MJ_EXPORT void mj_derive_fragment_key_with_history(const uint8_t chain_key[MJ_KEY_SIZE],
                                                    const uint8_t chain_state[MJ_HASH_SIZE],
                                                    const uint8_t accumulated_hash[MJ_HASH_SIZE],
                                                    int fragment_id,
                                                    uint8_t output_key[MJ_KEY_SIZE]);

/* AES-256-CTR decrypt in-place (reuses encrypt) */
MJ_EXPORT void mj_aes_ctr_crypt(uint8_t* data, size_t len,
                                const uint8_t key[MJ_KEY_SIZE]);

/* Securely wipe memory region */
MJ_EXPORT void mj_secure_wipe(void* ptr, size_t len);

/* Update chain state: SHA256(old_state || fragment_output) */
MJ_EXPORT void mj_update_chain_state(uint8_t chain_state[MJ_HASH_SIZE],
                                     const uint8_t* fragment_output,
                                     size_t output_len);

/* ---- Fragment execution callback type ---------------------------------- */

typedef int (*mj_fragment_exec_fn)(const uint8_t* code, size_t code_len,
                                    uint64_t* accumulator);

/* Set custom execution callback (default: memcpy to RWX and call) */
MJ_EXPORT void mj_engine_set_exec_fn(mj_engine_t* eng, mj_fragment_exec_fn fn);

#ifdef __cplusplus
}
#endif

#endif /* MICROJIT_H */
