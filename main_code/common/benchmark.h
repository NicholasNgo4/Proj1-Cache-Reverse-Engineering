#ifndef BENCHMARK_H
#define BENCHMARK_H

#include <stdint.h>

#include "pointer_chase.h"

double measure_dependency_chain(struct node *start, uint64_t steps);

#endif