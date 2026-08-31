#include <stdint.h>
#include "benchmark.h"
#include "timer.h"

double measure_dependency_chain(struct node *start, uint64_t steps) {
    uint64_t t0 = timer_start();
    chase(start, steps);
    uint64_t t1 = timer_stop();
    return (double)(t1 - t0) / (double)steps;
}