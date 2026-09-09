#define _POSIX_C_SOURCE 200112L /* for posix_memalign -- aligned_alloc requires size to be
                                 * an exact multiple of alignment, which does not hold here
                                 * in general (buffer_bytes depends on the swept stride) */

#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>

#include "benchmark.h"
#include "line_size.h"
#include "pointer_chase.h"
#include "random.h"

int run_line_size_experiment(const struct line_size_config *cfg)
{
    uint64_t min_stride = cfg->min_stride;
    if (min_stride < sizeof(struct node)) {
        min_stride = sizeof(struct node);
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

    printf("# experiment=line_size samples_requested=%" PRIu64
           " samples_achieved=%" PRIu64 " batch_size=%" PRIu64
           " num_batches=%" PRIu64 " footprint_bytes=%" PRIu64
           " align_bytes=%" PRIu64 " warmup_passes=%d seed=%u node_bytes=%zu"
           " pattern=%s\n",
           cfg->samples, achieved_samples, cfg->batch_size, num_batches,
           cfg->footprint_bytes, cfg->align_bytes, cfg->warmup_passes, cfg->seed,
           sizeof(struct node), pattern_name);
    printf("stride_bytes,num_nodes,footprint_bytes,align_bytes,pattern,batch_index,avg_ticks_per_access\n");

    for (uint64_t stride = min_stride; stride <= cfg->max_stride; stride += cfg->stride_step) {
        size_t num_nodes = (size_t)(cfg->footprint_bytes / stride);
        if (num_nodes < 2) {
            /* Stride too large relative to footprint to form a valid cycle
             * at all -- skip rather than clamp-and-measure-something that
             * would no longer represent the configured footprint (unlike
             * capacity.c's low-end clamp, this happens at the HIGH end of
             * the sweep). */
            fprintf(stderr, "skipping stride=%" PRIu64 ": footprint_bytes/stride < 2 nodes\n",
                    stride);
            continue;
        }

        uint64_t buffer_bytes = (uint64_t)(num_nodes - 1) * stride + sizeof(struct node);

        void *base = NULL;
        int rc = posix_memalign(&base, (size_t)cfg->align_bytes, (size_t)buffer_bytes);
        if (rc != 0 || base == NULL) {
            fprintf(stderr,
                    "posix_memalign failed at stride=%" PRIu64 " (%zu nodes, %" PRIu64
                    " bytes): rc=%d\n",
                    stride, num_nodes, buffer_bytes, rc);
            free(batch_latencies);
            return 1;
        }

        if (cfg->pattern == ACCESS_PATTERN_SEQUENTIAL) {
            make_sequential_cycle_strided(base, num_nodes, (size_t)stride);
        } else {
            make_random_cycle_strided(base, num_nodes, (size_t)stride, cfg->seed);
        }

        /* Untimed pass(es): fault in pages and settle steady-state residency
         * for this stride before timing starts. */
        for (int w = 0; w < cfg->warmup_passes; w++) {
            chase(base, (uint64_t)num_nodes);
        }

        measure_dependency_chain_batched(base, cfg->batch_size, num_batches, batch_latencies);

        for (uint64_t b = 0; b < num_batches; b++) {
            printf("%" PRIu64 ",%zu,%" PRIu64 ",%" PRIu64 ",%s,%" PRIu64 ",%.4f\n",
                   stride, num_nodes, cfg->footprint_bytes, cfg->align_bytes,
                   pattern_name, b, batch_latencies[b]);
        }
        fflush(stdout);

        free(base);
    }

    free(batch_latencies);
    return 0;
}
