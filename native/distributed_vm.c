#include "distributed_vm.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Unwired experimental sim — not part of the supported build. */
#ifndef NIXON_EXPERIMENTAL
#error "This is an unwired experimental sim. Define NIXON_EXPERIMENTAL to compile it."
#endif

void vm_state_init(vm_state_t* state) {
    memset(state, 0, sizeof(vm_state_t));
    state->pc = 0;
    state->sp = 0;
    state->sync_counter = 0;
}

bool vm_network_send(uint32_t dest_host, const uint8_t* data, uint32_t len) {
    if (!data || len == 0 || len > VM_PACKET_SIZE) return false;
    /* Simulated: just validate parameters */
    (void)dest_host;
    return true;
}

bool vm_network_recv(uint32_t source_host, uint8_t* data, uint32_t* len) {
    if (!data || !len) return false;
    /* Simulated: return empty packet */
    (void)source_host;
    *len = 0;
    return true;
}

bool vm_sync_state(vm_state_t* state, uint32_t host_id, vm_partition_t partition) {
    if (!state) return false;

    state->sync_counter++;

    uint8_t packet[VM_PACKET_SIZE];
    uint32_t offset = 0;

    switch (partition) {
        case VM_PARTITION_REGISTERS:
            memcpy(packet + offset, &state->pc, sizeof(uint32_t));
            offset += sizeof(uint32_t);
            memcpy(packet + offset, state->registers, sizeof(state->registers));
            offset += sizeof(state->registers);
            break;

        case VM_PARTITION_MEMORY:
            memcpy(packet + offset, state->memory, VM_MEMORY_SIZE);
            offset += VM_MEMORY_SIZE;
            break;

        case VM_PARTITION_STACK:
            memcpy(packet + offset, &state->sp, sizeof(uint32_t));
            offset += sizeof(uint32_t);
            memcpy(packet + offset, state->stack, state->sp * sizeof(int64_t));
            offset += state->sp * sizeof(int64_t);
            break;

        default:
            return false;
    }

    /* Broadcast to all hosts */
    for (uint32_t h = 0; h < VM_MAX_HOSTS; h++) {
        if (h != host_id) {
            vm_network_send(h, packet, offset);
        }
    }

    (void)packet;
    return true;
}
