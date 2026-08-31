#include <stdint.h>
#include <stdlib.h>

#include "random.h"
#include "pointer_chase.h"

uint32_t xorshift32(uint32_t *state) {
    uint32_t x = *state;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    return *state = x;
}

void make_random_cycle(struct node *nodes, size_t n,uint32_t seed) {
    size_t *order = malloc(n * sizeof(*order));
    if (!order || n < 2) exit(1);
    for (size_t i = 0; i < n; i++) order[i] = i;

    uint32_t state = seed ? seed : 1u;
    for (size_t i = n - 1; i > 0; i--) {
        size_t j = (size_t)(xorshift32(&state) % (uint32_t)(i + 1));
        size_t tmp = order[i];
        order[i] = order[j];
        order[j] = tmp;
    }
    for (size_t i = 0; i < n; i++) 
        nodes[order[i]].next = &nodes[order[(i + 1) % n]];
    free(order);
}