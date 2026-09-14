#include <stddef.h>
#include <stdint.h>

#include "benchmark.h"
#include "timer.h"

static volatile struct node *bench_sink;

void measure_dependency_chain_batched(struct node *start,
                                       uint64_t batch_size,
                                       size_t num_batches,
                                       double *out_latencies)
{
    struct node *p = start;

    for (size_t b = 0; b < num_batches; b++) {
        uint64_t t0 = timer_start();
        for (uint64_t i = 0; i < batch_size; i++) {
            p = p->next; /* next address depends on previous load */
        }
        uint64_t t1 = timer_stop();
        out_latencies[b] = (double)(t1 - t0) / (double)batch_size;
    }

    bench_sink = p; /* keep the final result observable */
}

void measure_independent_loads_batched(struct node *nodes,
                                        const size_t *order,
                                        size_t order_len,
                                        uint64_t batch_size,
                                        size_t num_batches,
                                        double *out_latencies)
{
    struct node *last = NULL;
    size_t idx = 0;

    for (size_t b = 0; b < num_batches; b++) {
        uint64_t t0 = timer_start();
        for (uint64_t i = 0; i < batch_size; i++) {
            /* Address comes from the caller-supplied permutation, not from
             * the value just loaded -- unlike measure_dependency_chain_batched(),
             * nothing here forces one load to wait on the previous one. */
            last = nodes[order[idx]].next;
            idx++;
            if (idx == order_len) {
                idx = 0;
            }
        }
        uint64_t t1 = timer_stop();
        out_latencies[b] = (double)(t1 - t0) / (double)batch_size;
    }

    bench_sink = last; /* keep the final result observable */
}
