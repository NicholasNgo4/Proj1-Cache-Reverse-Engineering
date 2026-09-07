#ifndef TIMER_ARM_H
#define TIMER_ARM_H
/*
 * timer_arm.h -- AArch64 timing path for Thunderbird (Ampere Q80-30).
 *
 * Uses the unprivileged virtual counter CNTVCT_EL0. The DSB/ISB
 * barrier sequence is intentionally conservative to bound ordering;
 * this adds real overhead that must be characterized (see the batched
 * timing method in cache_bench.c) rather than subtracted blindly.
 *
 * IMPORTANT: this generic timer may update far more slowly than a core
 * clock. Do not call a tick a "cycle." Report ticks/access as the
 * Phase-I unit, and only convert to ns/access using CNTFRQ_EL0 if that
 * frequency is confirmed trustworthy on this platform.
 */
#include <stdint.h>

static inline uint64_t timer_start(void) {
    uint64_t t;
    __asm__ __volatile__(
        "dsb sy\n\t"
        "isb\n\t"
        "mrs %0, cntvct_el0\n\t"
        "isb\n\t"
        : "=r"(t) :: "memory");
    return t;
}

static inline uint64_t timer_stop(void) {
    /* Same read, same barrier sequence -- symmetry keeps start/stop
     * overhead comparable so it cancels out over a batch. */
    return timer_start();
}

static inline uint64_t timer_freq(void) {
    uint64_t f;
    __asm__ __volatile__("mrs %0, cntfrq_el0" : "=r"(f));
    return f;
}

#define TIMER_UNIT_NAME "ARM_counter_ticks"

#endif /* TIMER_ARM_H */
