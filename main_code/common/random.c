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

static struct node *node_at(void *base, size_t i, size_t stride) {
    return (struct node *)((uint8_t *)base + i * stride);
}

void make_random_cycle_strided(void *base, size_t n, size_t stride, uint32_t seed) {
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
        node_at(base, order[i], stride)->next = node_at(base, order[(i + 1) % n], stride);
    free(order);
}

void make_sequential_cycle_strided(void *base, size_t n, size_t stride) {
    if (n < 2) exit(1);
    for (size_t i = 0; i < n; i++)
        node_at(base, i, stride)->next = node_at(base, (i + 1) % n, stride);
}

void make_random_cycle(struct node *nodes, size_t n, uint32_t seed) {
    make_random_cycle_strided(nodes, n, sizeof(struct node), seed);
}

void make_sequential_cycle(struct node *nodes, size_t n) {
    make_sequential_cycle_strided(nodes, n, sizeof(struct node));
}

size_t *make_shuffled_indices(size_t n, uint32_t seed) {
    size_t *order = malloc(n * sizeof(*order));
    if (!order || n < 1) exit(1);
    for (size_t i = 0; i < n; i++) order[i] = i;

    uint32_t state = seed ? seed : 1u;
    for (size_t i = n - 1; i > 0; i--) {
        size_t j = (size_t)(xorshift32(&state) % (uint32_t)(i + 1));
        size_t tmp = order[i];
        order[i] = order[j];
        order[j] = tmp;
    }
    return order;
}