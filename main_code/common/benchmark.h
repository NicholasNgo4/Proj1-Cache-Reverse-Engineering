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

/*
 * The independent-load counterpart to measure_dependency_chain_batched():
 * times `num_batches` batches of `batch_size` loads each, but every load's
 * address is `nodes[order[i % order_len]]` -- drawn from a caller-supplied
 * index sequence -- instead of being chained from the previous load's
 * result. The caller picks `order` to match --pattern, exactly like every
 * other experiment: a shuffled permutation (see make_shuffled_indices() in
 * random.h) for the random/primary signal, or a plain 0..order_len-1
 * sequence for the sequential/prefetcher-predictable control -- passing a
 * random order regardless of pattern would silently make "sequential"
 * mean nothing for this timer.
 *
 * This is the required diagnostic control for a hit-latency measurement:
 * at the random pattern, it exposes memory-level parallelism and is
 * expected to read *faster* per access than the dependent version at the
 * same footprint, which is exactly why it must never be reported as the
 * latency number itself (see latency.h).
 */
void measure_independent_loads_batched(struct node *nodes,
                                        const size_t *order,
                                        size_t order_len,
                                        uint64_t batch_size,
                                        size_t num_batches,
                                        double *out_latencies);

#endif
