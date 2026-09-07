#include <inttypes.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#include "benchmark.h"
#include "capacity.h"
#include "pointer_chase.h"
#include "random.h"

int run_capacity_experiment(const struct capacity_config *cfg)
{
    uint64_t min_bytes = cfg->min_bytes;
    if (min_bytes < sizeof(struct node) * 2) {
        min_bytes = sizeof(struct node) * 2;
    }

    /* Round up so the achieved timed-access total is never below the
     * requested --samples floor, even when --samples isn't an exact
     * multiple of --batch-size. Warm-up accesses (below) are untimed and
     * never enter batch_latencies, so they never count toward this total
     * either -- both halves of the "1,000,000 timed, warm-up excluded"
     * requirement are enforced structurally, not by convention. */
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

    printf("# experiment=capacity samples_requested=%" PRIu64
           " samples_achieved=%" PRIu64 " batch_size=%" PRIu64
           " num_batches=%" PRIu64 " warmup_passes=%d seed=%u node_bytes=%zu\n",
           cfg->samples, achieved_samples, cfg->batch_size, num_batches,
           cfg->warmup_passes, cfg->seed, sizeof(struct node));
    printf("size_bytes,num_nodes,batch_index,avg_ticks_per_access\n");

    size_t last_num_nodes = 0;
    double step = 1.0 / (double)cfg->points_per_octave;
    double log2_min = log2((double)min_bytes);
    double log2_max = log2((double)cfg->max_bytes);

    for (double exp = log2_min; exp <= log2_max + 1e-9; exp += step) {
        uint64_t bytes = (uint64_t)(pow(2.0, exp) + 0.5);
        size_t num_nodes = (size_t)(bytes / sizeof(struct node));
        if (num_nodes < 2) {
            num_nodes = 2;
        }
        if (num_nodes == last_num_nodes) {
            continue;
        }
        last_num_nodes = num_nodes;

        struct node *nodes = malloc(num_nodes * sizeof(struct node));
        if (nodes == NULL) {
            fprintf(stderr, "allocation failed at %zu nodes\n", num_nodes);
            free(batch_latencies);
            return 1;
        }

        make_random_cycle(nodes, num_nodes, cfg->seed);

        /* Untimed pass(es): fault in pages and settle steady-state
         * residency for this working-set size before timing starts. */
        for (int w = 0; w < cfg->warmup_passes; w++) {
            chase(nodes, (uint64_t)num_nodes);
        }

        measure_dependency_chain_batched(nodes, cfg->batch_size, num_batches,
                                          batch_latencies);

        uint64_t size_bytes = (uint64_t)num_nodes * sizeof(struct node);
        for (uint64_t b = 0; b < num_batches; b++) {
            printf("%" PRIu64 ",%zu,%" PRIu64 ",%.4f\n",
                   size_bytes, num_nodes, b, batch_latencies[b]);
        }
        fflush(stdout);

        free(nodes);
    }

    free(batch_latencies);
    return 0;
}
