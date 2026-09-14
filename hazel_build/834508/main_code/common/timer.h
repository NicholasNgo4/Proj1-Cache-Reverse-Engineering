#ifndef TIMER_H
#define TIMER_H

#include <stdint.h>

#if defined(__x86_64__) || defined(__i386__)

#include "../x86_64/timer_x86.h"

static inline uint64_t timer_start(void){
    return x86_tsc_start();
}

static inline uint64_t timer_stop(void){
    return x86_tsc_stop();
}

#elif defined(__aarch64__)

#include "../aarch64/timer_arm.h"

static inline uint64_t timer_start(void){
    return arm_counter_start();
}

static inline uint64_t timer_stop(void){
    return arm_counter_stop();
}

#else

#error "Unsupported architecture"

#endif

#endif