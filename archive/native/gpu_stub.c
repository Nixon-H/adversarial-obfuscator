#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>

/* Unwired experimental sim — not part of the supported build. */
#ifndef NIXON_EXPERIMENTAL
#error "This is an unwired experimental sim. Define NIXON_EXPERIMENTAL to compile it."
#endif

#if defined(_WIN32) || defined(_WIN64)
#define GPU_EXPORT __declspec(dllexport)
#else
#define GPU_EXPORT __attribute__((visibility("default")))
#endif

#define GPU_MAX_THREADS 64
#define GPU_LOCAL_MEM_SIZE 16384
#define GPU_GLOBAL_MEM_SIZE (1024 * 1024)
#define GPU_WARP_SIZE 4
#define GPU_MAX_FRAGMENTS 256

typedef struct {
    uint8_t *code;
    size_t code_len;
    int kernel_id;
    int num_threads;
    int args[8];
} GpuKernel;

typedef struct {
    uint8_t global_mem[GPU_GLOBAL_MEM_SIZE];
    uint8_t local_mem[GPU_LOCAL_MEM_SIZE];
    uint64_t threads[GPU_MAX_THREADS];
    int num_fragments;
    GpuKernel fragments[GPU_MAX_FRAGMENTS];
    int use_gpu;
} GpuState;

typedef uint64_t (*gpu_kernel_fn)(uint64_t thread_id, uint64_t arg, uint8_t *global_mem, uint8_t *local_mem);

GPU_EXPORT void gpu_init(GpuState *state) {
    memset(state, 0, sizeof(GpuState));
    state->use_gpu = 0;
    state->num_fragments = 0;
}

GPU_EXPORT int gpu_load_kernel(GpuState *state, int kernel_id,
                                const uint8_t *code, size_t code_len) {
    if (state->num_fragments >= GPU_MAX_FRAGMENTS) return -1;
    GpuKernel *k = &state->fragments[state->num_fragments];
    k->code = (uint8_t*)malloc(code_len);
    if (!k->code) return -1;
    memcpy(k->code, code, code_len);
    k->code_len = code_len;
    k->kernel_id = kernel_id;
    k->num_threads = 1;
    state->num_fragments++;
    return state->num_fragments - 1;
}

GPU_EXPORT int gpu_set_kernel_args(GpuState *state, int fragment_idx,
                                    int arg0, int arg1, int arg2, int arg3) {
    if (fragment_idx < 0 || fragment_idx >= state->num_fragments) return -1;
    GpuKernel *k = &state->fragments[fragment_idx];
    k->args[0] = arg0;
    k->args[1] = arg1;
    k->args[2] = arg2;
    k->args[3] = arg3;
    return 0;
}

GPU_EXPORT int gpu_set_num_threads(GpuState *state, int fragment_idx, int num_threads) {
    if (fragment_idx < 0 || fragment_idx >= state->num_fragments) return -1;
    if (num_threads > GPU_MAX_THREADS) num_threads = GPU_MAX_THREADS;
    if (num_threads < 1) num_threads = 1;
    state->fragments[fragment_idx].num_threads = num_threads;
    return 0;
}

static uint64_t sim_kernel_add(uint64_t tid, uint64_t arg, uint8_t *global_mem, uint8_t *local_mem) {
    (void)local_mem;
    uint64_t *gm = (uint64_t*)global_mem;
    gm[tid] = gm[tid] + arg;
    return gm[tid];
}

static uint64_t sim_kernel_xor(uint64_t tid, uint64_t arg, uint8_t *global_mem, uint8_t *local_mem) {
    (void)local_mem;
    uint64_t *gm = (uint64_t*)global_mem;
    gm[tid] = gm[tid] ^ arg;
    return gm[tid];
}

#define ROL64(v, n) (((v) << (n)) | ((v) >> (64 - (n))))
#define MUL64(v, m) ((v) * (m))

static uint64_t sim_kernel_mix(uint64_t tid, uint64_t arg, uint8_t *global_mem, uint8_t *local_mem) {
    (void)local_mem;
    uint64_t *gm = (uint64_t*)global_mem;
    uint64_t val = gm[tid];
    val = MUL64(val, 0x9E3779B97F4A7C15ULL) + arg + tid;
    gm[tid] = val ^ (val >> 31);
    return gm[tid];
}

static gpu_kernel_fn sim_kernels[] = {
    sim_kernel_add,
    sim_kernel_xor,
    sim_kernel_mix,
};

GPU_EXPORT int gpu_execute_fragment(GpuState *state, int fragment_idx) {
    if (fragment_idx < 0 || fragment_idx >= state->num_fragments) return -1;
    GpuKernel *k = &state->fragments[fragment_idx];
    int num_threads = k->num_threads;
    int kernel_type = k->kernel_id % 3;
    gpu_kernel_fn fn = sim_kernels[kernel_type];
    uint64_t arg = (uint64_t)(k->args[0] ^ k->args[1]);

    for (int t = 0; t < num_threads; t++) {
        state->threads[t] = fn((uint64_t)t, arg, state->global_mem, state->local_mem);
    }

    return num_threads;
}

GPU_EXPORT int gpu_execute_all(GpuState *state) {
    if (!state) return -1;
    int total = 0;
    for (int i = 0; i < state->num_fragments; i++) {
        int n = gpu_execute_fragment(state, i);
        if (n < 0) return -1;
        total += n;
    }
    return total;
}

GPU_EXPORT int gpu_transfer_from_cpu(GpuState *state, const uint8_t *data, size_t len) {
    if (!state || !data) return -1;
    if (len > GPU_GLOBAL_MEM_SIZE) len = GPU_GLOBAL_MEM_SIZE;
    memcpy(state->global_mem, data, len);
    return (int)len;
}

GPU_EXPORT int gpu_transfer_to_cpu(GpuState *state, uint8_t *data, size_t len) {
    if (!state || !data) return -1;
    if (len > GPU_GLOBAL_MEM_SIZE) len = GPU_GLOBAL_MEM_SIZE;
    memcpy(data, state->global_mem, len);
    return (int)len;
}

GPU_EXPORT void gpu_reset(GpuState *state) {
    gpu_init(state);
}

GPU_EXPORT int gpu_fallback_available(void) {
    return 1;
}
