#ifndef PLATFORM_H
#define PLATFORM_H

/* size_t is used below; the header must be self-contained so a consumer may
 * include it first (it previously relied on whoever included it having
 * already pulled in a definition, and failed to compile standalone). */
#include <stddef.h>

/* Platform detection */
#if defined(_WIN32) || defined(_WIN64)
    #define PLATFORM_WINDOWS 1
#elif defined(__linux__)
    #define PLATFORM_LINUX 1
#elif defined(__APPLE__)
    #define PLATFORM_MACOS 1
#else
    #error "Unsupported platform"
#endif

/* Export/visibility macros */
#if defined(PLATFORM_WINDOWS)
    #define EXPORT __declspec(dllexport)
#else
    #define EXPORT __attribute__((visibility("default")))
#endif

/* Inline macro */
#ifndef INLINE
    #if defined(_MSC_VER)
        #define INLINE __inline
    #else
        #define INLINE inline
    #endif
#endif

/* Secure memory wipe (platform-independent) */
static INLINE void secure_memzero(void *ptr, size_t len) {
    if (ptr && len) {
        volatile unsigned char *p = (volatile unsigned char *)ptr;
        for (size_t i = 0; i < len; i++) p[i] = 0;
    }
}

/* Page size */
#if defined(PLATFORM_WINDOWS)
    #define PAGE_SIZE 4096
#else
    #include <unistd.h>
    static INLINE size_t get_page_size(void) {
        return (size_t)sysconf(_SC_PAGESIZE);
    }
#endif

#endif /* PLATFORM_H */
