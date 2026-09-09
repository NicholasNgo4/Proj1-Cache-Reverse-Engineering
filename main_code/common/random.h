#ifndef RANDOM_H
#define RANDOM_H

#include <stddef.h>
#include <stdint.h>

struct node;

uint32_t xorshift32(uint32_t *state);

void make_random_cycle(
    struct node *nodes,
    size_t n,
    uint32_t seed
);

/*
 * Links nodes[0] -> nodes[1] -> ... -> nodes[n-1] -> nodes[0], i.e. the same
 * physical (array) order the nodes were allocated in. Used as the
 * regular/sequential-traversal control: same footprint, same node count,
 * same dependent-chain timing method as make_random_cycle(), but a stride
 * prefetcher can predict this address stream while it cannot predict the
 * randomized cycle. Comparing the two is the required prefetcher sanity
 * check for every capacity/latency boundary.
 */
void make_sequential_cycle(
    struct node *nodes,
    size_t n
);

/*
 * Strided variants of make_random_cycle()/make_sequential_cycle(): node i is
 * placed at (uint8_t*)base + i*stride instead of assuming stride equals
 * sizeof(struct node). Used by the line_size experiment to hold a fixed
 * virtual footprint (n*stride) while varying how many bytes separate
 * consecutive nodes in memory. stride must be >= sizeof(struct node)
 * (caller's responsibility -- not validated here, matching this file's
 * existing style of not validating n>=2 either).
 */
void make_random_cycle_strided(
    void *base,
    size_t n,
    size_t stride,
    uint32_t seed
);

void make_sequential_cycle_strided(
    void *base,
    size_t n,
    size_t stride
);

#endif