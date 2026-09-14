#include "pointer_chase.h"

static volatile struct node *sink_node;

void chase(struct node *p, uint64_t steps) {
    for (uint64_t i = 0; i < steps; i++) {
        p = p->next; /* next address depends on previous load */
    }
    sink_node = p; /* keep the final result observable */
}