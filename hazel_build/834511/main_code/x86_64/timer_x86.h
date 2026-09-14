#include <stdint.h>
#include <x86intrin.h>

static inline uint64_t x86_tsc_start(void) {
    _mm_lfence();
    uint64_t t = __rdtsc();
    _mm_lfence();
    return t;
}

static inline uint64_t x86_tsc_stop(void) {
    unsigned aux;
    uint64_t t = __rdtscp(&aux);
    _mm_lfence();
    return t;
}

static inline uint64_t time_one_load(volatile const uint64_t *p) {
    uint64_t t0 = x86_tsc_start();
    uint64_t value = *p;
    uint64_t t1 = x86_tsc_stop();
    __asm__ __volatile__("" : "+r"(value) :: "memory");
    return t1 - t0;
}