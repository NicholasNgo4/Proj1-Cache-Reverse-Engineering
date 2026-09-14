#include <stdint.h>
    static inline uint64_t arm_counter_start(void) {
    uint64_t t;
    __asm__ __volatile__(
        "dsb sy\n\t"
        "isb\n\t"
        "mrs %0, cntvct_el0\n\t"
        "isb\n\t"
        : "=r"(t) :: "memory");
    return t;
}

static inline uint64_t arm_counter_stop(void) {
    uint64_t t;
    __asm__ __volatile__(
        "dsb sy\n\t"
        "isb\n\t"
        "mrs %0, cntvct_el0\n\t"
        "isb\n\t"
        : "=r"(t) :: "memory");
return t;
}

static inline uint64_t arm_counter_freq(void) {
    uint64_t f;
    __asm__ __volatile__("mrs %0, cntfrq_el0" : "=r"(f));
    return f;
}