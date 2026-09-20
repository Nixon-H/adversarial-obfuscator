#ifndef DISTRIBUTED_VM_H
#define DISTRIBUTED_VM_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#define VM_NUM_REGISTERS 8
#define VM_MEMORY_SIZE 4096
#define VM_STACK_SIZE 256
#define VM_MAX_HOSTS 8
#define VM_PACKET_SIZE 8192

typedef enum {
    VM_PARTITION_REGISTERS = 0,
    VM_PARTITION_MEMORY = 1,
    VM_PARTITION_STACK = 2
} vm_partition_t;

typedef struct {
    int64_t registers[VM_NUM_REGISTERS];
    uint8_t memory[VM_MEMORY_SIZE];
    int64_t stack[VM_STACK_SIZE];
    uint32_t sp;
    uint32_t pc;
    uint32_t sync_counter;
} vm_state_t;

typedef struct {
    uint32_t host_id;
    vm_partition_t partition;
    uint8_t packet_data[VM_PACKET_SIZE];
    uint32_t packet_len;
} vm_network_packet_t;

void vm_state_init(vm_state_t* state);
bool vm_network_send(uint32_t dest_host, const uint8_t* data, uint32_t len);
bool vm_network_recv(uint32_t source_host, uint8_t* data, uint32_t* len);
bool vm_sync_state(vm_state_t* state, uint32_t host_id, vm_partition_t partition);

#endif /* DISTRIBUTED_VM_H */
