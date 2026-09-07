#ifndef TIMER_X86_H
#define TIMER_X86_H
/*
 * timer_x86.h -- x86-64 timing path for Intel/AMD lab machines
 * (Sunbird, Skylark, Artemisia, Charnwood, Crux, Ookay, Upgrade).
 *
 * RDTSC is not serializing by itself; LFENCE orders it relative to
 * surrounding instructions. RDTSCP additionally waits for all prior
 * instructions to execute before reading the counter, which is why it
 * is used to close out a timed interval instead of a second RDTSC.
 *
 * Reported unit: raw TSC ticks/access. On most modern systems the TSC
 * runs at an invariant reference rate, but that is NOT the same as the
 * instantaneous core clock under turbo/power-management -- do not
 * convert to core cycles without Phase-II PMU validation.
 */
#include <stdint.h>
#include <x86intrin.h>

static inline uint64_t timer_start(void) {
    _mm_lfence();
    uint64_t t = __rdtsc();
    _mm_lfence();
    return t;
}

static inline uint64_t timer_stop(void) {
    unsigned aux;
    uint64_t t = __rdtscp(&aux);
    _mm_lfence();
    return t;
}

#define TIMER_UNIT_NAME "TSC_ticks"

#endif /* TIMER_X86_H */
