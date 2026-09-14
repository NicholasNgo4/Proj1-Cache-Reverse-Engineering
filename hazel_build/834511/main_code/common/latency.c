#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>

#include "benchmark.h"
#include "latency.h"
#include "pointer_chase.h"
#include "random.h"
#include "timer.h"

static const char *load_mode_name(enum load_mode mode)
{
    return (mode == LOAD_MODE_INDEPENDENT) ? "independent" : "dependent";
}

static volatile struct node *miss_latency_sink;

int run_hit_latency_experiment(const struct hit_latency_config *cfg)
{
    size_t num_nodes = (size_t)(cfg->footprint_bytes / sizeof(struct node));
    if (num_nodes < 2) {
        num_nodes = 2;
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

    struct node *nodes = malloc(num_nodes * sizeof(struct node));
    if (nodes == NULL) {
        fprintf(stderr, "allocation failed at %zu nodes\n", num_nodes);
        free(batch_latencies);
        return 1;
    }

    const char *pattern_name =
        (cfg->pattern == ACCESS_PATTERN_SEQUENTIAL) ? "sequential" : "random";
    const char *mode_name = load_mode_name(cfg->load_mode);

    if (cfg->pattern == ACCESS_PATTERN_SEQUENTIAL) {
        make_sequential_cycle(nodes, num_nodes);
    } else {
        make_random_cycle(nodes, num_nodes, cfg->seed);
    }

    /* Untimed pass(es): fault in pages and settle steady-state residency at
     * this footprint before timing starts -- always via the dependent chain,
     * even when the timed mode below is independent, so both modes measure
     * from the same warmed-up state. */
    for (int w = 0; w < cfg->warmup_passes; w++) {
        chase(nodes, (uint64_t)num_nodes);
    }

    printf("# experiment=hit_latency samples_requested=%" PRIu64
           " samples_achieved=%" PRIu64 " batch_size=%" PRIu64
           " num_batches=%" PRIu64 " footprint_bytes=%" PRIu64
           " warmup_passes=%d seed=%u node_bytes=%zu pattern=%s load_mode=%s\n",
           cfg->samples, achieved_samples, cfg->batch_size, num_batches,
           cfg->footprint_bytes, cfg->warmup_passes, cfg->seed,
           sizeof(struct node), pattern_name, mode_name);
    printf("footprint_bytes,load_mode,pattern,batch_index,avg_ticks_per_access\n");

    size_t *order = NULL;
    if (cfg->load_mode == LOAD_MODE_INDEPENDENT) {
        /* Address order must follow --pattern, exactly like the dependent
         * chain's construction above -- otherwise "sequential" would mean
         * nothing for this timer and the two modes wouldn't be a fair
         * comparison at the same pattern. */
        if (cfg->pattern == ACCESS_PATTERN_SEQUENTIAL) {
            order = malloc(num_nodes * sizeof(*order));
            if (order == NULL) {
                fprintf(stderr, "allocation failed for %zu order entries\n", num_nodes);
                free(nodes);
                free(batch_latencies);
                return 1;
            }
            for (size_t i = 0; i < num_nodes; i++) {
                order[i] = i;
            }
        } else {
            order = make_shuffled_indices(num_nodes, cfg->seed);
        }
        measure_independent_loads_batched(nodes, order, num_nodes, cfg->batch_size,
                                           num_batches, batch_latencies);
    } else {
        measure_dependency_chain_batched(nodes, cfg->batch_size, num_batches,
                                          batch_latencies);
    }

    for (uint64_t b = 0; b < num_batches; b++) {
        printf("%" PRIu64 ",%s,%s,%" PRIu64 ",%.4f\n",
               cfg->footprint_bytes, mode_name, pattern_name, b, batch_latencies[b]);
    }
    fflush(stdout);

    free(order);
    free(nodes);
    free(batch_latencies);
    return 0;
}

int run_miss_latency_experiment(const struct miss_latency_config *cfg)
{
    size_t target_nodes = (size_t)(cfg->target_bytes / sizeof(struct node));
    if (target_nodes < 2) {
        target_nodes = 2;
    }
    size_t evict_nodes = (size_t)(cfg->evict_bytes / sizeof(struct node));
    if (evict_nodes < 2) {
        evict_nodes = 2;
    }

    struct node *target = malloc(target_nodes * sizeof(struct node));
    if (target == NULL) {
        fprintf(stderr, "allocation failed for target (%zu nodes)\n", target_nodes);
        return 1;
    }
    struct node *evict = malloc(evict_nodes * sizeof(struct node));
    if (evict == NULL) {
        fprintf(stderr, "allocation failed for eviction set (%zu nodes)\n", evict_nodes);
        free(target);
        return 1;
    }

    const char *pattern_name =
        (cfg->pattern == ACCESS_PATTERN_SEQUENTIAL) ? "sequential" : "random";

    /* Both the target and the eviction set are their own dependent cycles --
     * only node 0 of `target` is ever timed as "the target line", but the
     * rest of its set needs somewhere to point so chase() can refresh the
     * whole set's residency the same way every other experiment warms a
     * chain. Distinct seeds (seed, seed+1) so the two cycles aren't
     * identical permutations when both are random. */
    if (cfg->pattern == ACCESS_PATTERN_SEQUENTIAL) {
        make_sequential_cycle(target, target_nodes);
        make_sequential_cycle(evict, evict_nodes);
    } else {
        make_random_cycle(target, target_nodes, cfg->seed);
        make_random_cycle(evict, evict_nodes, cfg->seed + 1u);
    }

    for (int w = 0; w < cfg->warmup_passes; w++) {
        chase(target, (uint64_t)target_nodes);
        chase(evict, (uint64_t)evict_nodes);
    }

    printf("# experiment=miss_latency trials_requested=%" PRIu64
           " target_bytes=%" PRIu64 " evict_bytes=%" PRIu64
           " warmup_passes=%d seed=%u node_bytes=%zu pattern=%s\n",
           cfg->samples, cfg->target_bytes, cfg->evict_bytes,
           cfg->warmup_passes, cfg->seed, sizeof(struct node), pattern_name);
    printf("target_bytes,evict_bytes,pattern,trial_index,ticks\n");

    for (uint64_t trial = 0; trial < cfg->samples; trial++) {
        /* Untimed: re-establish the target set in the source level, then
         * displace it by walking the eviction-set cycle. This is the only
         * "eviction" mechanism in this codebase (no clflush is used anywhere)
         * -- it relies entirely on --evict-bytes being sized, by the caller,
         * past the source level's real capacity. */
        chase(target, (uint64_t)target_nodes);
        chase(evict, (uint64_t)evict_nodes);

        /* Timed: exactly one dependent reload of the target line. */
        uint64_t t0 = timer_start();
        struct node *reloaded = target->next;
        uint64_t t1 = timer_stop();
        miss_latency_sink = reloaded; /* keep the result observable */

        printf("%" PRIu64 ",%" PRIu64 ",%s,%" PRIu64 ",%" PRIu64 "\n",
               cfg->target_bytes, cfg->evict_bytes, pattern_name, trial,
               (uint64_t)(t1 - t0));
    }
    fflush(stdout);

    free(evict);
    free(target);
    return 0;
}
