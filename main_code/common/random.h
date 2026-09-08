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

#endif