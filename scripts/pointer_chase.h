#ifndef POINTER_CHASE_H
#define POINTER_CHASE_H
/*
 * pointer_chase.h -- shared, architecture-independent construction of a
 * randomized dependent-access cycle through memory. Used by EVERY
 * experiment mode (capacity, line size, associativity, latency, ...):
 * only the footprint size and node spacing differ between modes, this
 * file never changes.
 */
#include <stdint.h>
#include <stdlib.h>

struct node {
    struct node *next;
};

/* xorshift32 -- small, fast, deterministic PRNG. Deterministic from a
 * given seed so every run can be exactly reproduced by recording the
 * seed alongside the raw data (a Section 12 traceability requirement). */
static uint32_t xorshift32(uint32_t *state) {
    uint32_t x = *state;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    return *state = x;
}

/*
 * make_random_cycle -- links `n` pre-allocated nodes into ONE randomized
 * cycle (a single Hamiltonian loop through all of them), so a pointer
 * chase starting anywhere visits every node exactly once before
 * returning to the start. This defeats stride/stream prefetchers: there
 * is no predictable pattern to detect, since the next address is only
 * known once the current node's value has actually been loaded.
 */
static void make_random_cycle(struct node *nodes, size_t n, uint32_t seed) {
    size_t *order = malloc(n * sizeof(*order));
    if (!order || n < 2) {
        exit(1);
    }
    for (size_t i = 0; i < n; i++) order[i] = i;

    uint32_t state = seed ? seed : 1u;
    for (size_t i = n - 1; i > 0; i--) {
        size_t j = (size_t)(xorshift32(&state) % (uint32_t)(i + 1));
        size_t tmp = order[i];
        order[i] = order[j];
        order[j] = tmp;
    }
    for (size_t i = 0; i < n; i++) {
        nodes[order[i]].next = &nodes[order[(i + 1) % n]];
    }
    free(order);
}

/*
 * compiler_barrier -- prevents the COMPILER from reordering memory
 * operations across this point. It is NOT a CPU fence: it does nothing
 * to stop out-of-order execution or serialize the timer. Real ordering
 * for timing comes from the architecture-specific timer functions.
 */
static inline void compiler_barrier(void) {
    __asm__ __volatile__("" ::: "memory");
}

#endif /* POINTER_CHASE_H */
