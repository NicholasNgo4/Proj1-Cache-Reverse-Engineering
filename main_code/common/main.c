#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

#include "pointer_chase.h"
#include "random.h"
#include "benchmark.h"

int main(void)
{
    size_t num_nodes = 1024;
    uint64_t steps = 100000;

    struct node *nodes = malloc(num_nodes * sizeof(struct node));

    if (nodes == NULL) {
        fprintf(stderr, "Memory allocation failed\n");
        return 1;
    }

    make_random_cycle(nodes, num_nodes, 12345);

    double latency =
        measure_dependency_chain(nodes, steps);

    printf("Average latency: %.4f timer ticks/access\n", latency);

    free(nodes);

    return 0;
}