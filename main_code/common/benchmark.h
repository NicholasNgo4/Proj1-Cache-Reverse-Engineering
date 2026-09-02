#ifndef BENCHMARK_H
#define BENCHMARK_H

#include <stddef.h>
#include <stdint.h>

#include "pointer_chase.h"

/*
 * Times `num_batches` back-to-back batches of `batch_size` dependent
 * pointer-chase steps each, starting from `start` and continuing the same
 * chain across batch boundaries (so a sweep over a large working set keeps
 * exploring it rather than replaying a fixed prefix every batch). Batch b's
 * average ticks/access goes to out_latencies[b]. Caller must warm the chain
 * (see chase() in pointer_chase.h) before calling this, since warm-up
 * accesses must not count toward the required timed-sample total.
 */
void measure_dependency_chain_batched(struct node *start,
                                       uint64_t batch_size,
                                       size_t num_batches,
                                       double *out_latencies);

#endif
