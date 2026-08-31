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

#endif