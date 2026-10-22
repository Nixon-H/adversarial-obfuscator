#ifndef CROSS_PROCESS_H
#define CROSS_PROCESS_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#define CROSS_PROCESS_SHM_SIZE 65536
#define CROSS_PROCESS_MAX_FRAGMENTS 64
#define CROSS_PROCESS_HASH_SIZE 32

typedef struct {
    int32_t  fragment_id;
    int32_t  process_id;
    uint8_t  key[CROSS_PROCESS_HASH_SIZE];
    uint32_t data_len;
    uint8_t  data[];
} cross_process_fragment_t;

typedef struct {
    int32_t    fragment_count;
    uint32_t   shm_key;
    uint8_t    transport_key[CROSS_PROCESS_HASH_SIZE];
    cross_process_fragment_t* fragments[CROSS_PROCESS_MAX_FRAGMENTS];
} cross_process_chain_t;

bool cross_process_init_shm(const char* shm_name, size_t size);
bool cross_process_write_shm(const char* shm_name, const uint8_t* data, size_t len);
uint8_t* cross_process_read_shm(const char* shm_name, size_t* out_len);
bool cross_process_close_shm(const char* shm_name);

int32_t cross_process_get_pid(void);
bool cross_process_derive_key(int32_t pid, uint64_t entropy, int32_t fragment_id, uint8_t output_key[32]);
bool cross_process_verify_binding(int32_t pid, int32_t fragment_id, const uint8_t key[32]);

#endif /* CROSS_PROCESS_H */
