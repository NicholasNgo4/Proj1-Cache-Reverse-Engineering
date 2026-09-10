#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>

#include "associativity.h"
#include "benchmark.h"
#include "pointer_chase.h"
#include "random.h"

int run_associativity_experiment(const struct associativity_config *cfg)
{
    uint64_t min_ways = cfg->min_ways;
    if (min_ways < 2) {
        min_ways = 2; /* a 1-node cycle can't exercise set conflicts at all */
    }

    uint64_t num_batches = (cfg->samples + cfg->batch_size - 1) / cfg->batch_size;
    if (num_batches < 1) {
        num_batches = 1;
    }
    uint64_t achieved_samples = num_batches * cfg->batch_size;

    double *batch_latencies = malloc(num_batches * sizeof(double));
    if (batch_latencies == NULL) {
        fprintf(stderr, "allocation failed for %" PRIu64 " batch samples\n", num_batches);
        return 1;
    }

    const char *pattern_name =
        (cfg->pattern == ACCESS_PATTERN_SEQUENTIAL) ? "sequential" : "random";

    printf("# experiment=associativity samples_requested=%" PRIu64
           " samples_achieved=%" PRIu64 " batch_size=%" PRIu64
           " num_batches=%" PRIu64 " cache_bytes=%" PRIu64
           " warmup_passes=%d seed=%u node_bytes=%zu pattern=%s\n",
           cfg->samples, achieved_samples, cfg->batch_size, num_batches,
           cfg->cache_bytes, cfg->warmup_passes, cfg->seed, sizeof(struct node),
           pattern_name);
    printf("num_ways_probed,cache_bytes,pattern,batch_index,avg_ticks_per_access\n");

    for (uint64_t num_ways = min_ways; num_ways <= cfg->max_ways; num_ways += cfg->way_step) {
        /* Every node is cfg->cache_bytes apart, so the buffer only needs to
         * span (num_ways - 1) strides plus one node -- the address range
         * touched, not num_ways * cache_bytes. Physical memory actually
         * faulted in is one page per node (a handful of KB); the huge
         * virtual span is demand-paged and costs nothing until touched. */
        uint64_t buffer_bytes = (num_ways - 1) * cfg->cache_bytes + sizeof(struct node);

        void *base = malloc((size_t)buffer_bytes);
        if (base == NULL) {
            fprintf(stderr,
                    "allocation failed at num_ways=%" PRIu64 " (%" PRIu64 " bytes virtual"
                    " span)\n",
                    num_ways, buffer_bytes);
            free(batch_latencies);
            return 1;
        }

        if (cfg->pattern == ACCESS_PATTERN_SEQUENTIAL) {
            make_sequential_cycle_strided(base, (size_t)num_ways, (size_t)cfg->cache_bytes);
        } else {
            make_random_cycle_strided(base, (size_t)num_ways, (size_t)cfg->cache_bytes,
                                       cfg->seed);
        }

        /* Untimed pass(es): fault in the num_ways touched pages and settle
         * steady-state occupancy of this set before timing starts. */
        for (int w = 0; w < cfg->warmup_passes; w++) {
            chase(base, num_ways);
        }

        measure_dependency_chain_batched(base, cfg->batch_size, num_batches, batch_latencies);

        for (uint64_t b = 0; b < num_batches; b++) {
            printf("%" PRIu64 ",%" PRIu64 ",%s,%" PRIu64 ",%.4f\n",
                   num_ways, cfg->cache_bytes, pattern_name, b, batch_latencies[b]);
        }
        fflush(stdout);

        free(base);
    }

    free(batch_latencies);
    return 0;
}
