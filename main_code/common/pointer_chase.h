#ifndef POINTER_CHASE_H
#define POINTER_CHASE_H

#include <stdint.h>

struct node {
    struct node *next;
};

void chase(struct node *p, uint64_t steps);

#endif