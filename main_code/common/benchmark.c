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
