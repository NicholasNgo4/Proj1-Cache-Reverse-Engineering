/* Needed for posix_memalign() under strict -std=c11 (not ISO C -- a
 * POSIX/glibc extension). Must precede every #include, matching
 * line_size.c's identical requirement/comment. */
#define _POSIX_C_SOURCE 200112L

#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#include "inclusion_policy.h"
#include "pointer_chase.h"
#include "random.h"
#include "timer.h"

#define PAGE_BYTES 4096u

static volatile struct node *incl_sink;

int run_inclusion_policy_experiment(const struct inclusion_policy_config *cfg)
{
    size_t target_nodes = (size_t)(cfg->target_bytes / sizeof(struct node));
    if (target_nodes < 2) {
        target_nodes = 2;
    }
    size_t evict_nodes = (size_t)(cfg->evict_bytes / cfg->evict_stride_bytes);
    if (evict_nodes < 2) {
        evict_nodes = 2;
    }

    /* Target and control: densely packed, page-aligned (offset 0). Two
     * independent buffers so the control channel's residency can never be
     * disturbed by anything done to target's own memory. */
    struct node *target = NULL;
    struct node *control = NULL;
    if (posix_memalign((void **)&target, PAGE_BYTES, target_nodes * sizeof(struct node)) != 0 ||
        target == NULL) {
        fprintf(stderr, "allocation failed for target (%zu nodes)\n", target_nodes);
        return 1;
    }
    if (posix_memalign((void **)&control, PAGE_BYTES, target_nodes * sizeof(struct node)) != 0 ||
        control == NULL) {
        fprintf(stderr, "allocation failed for control (%zu nodes)\n", target_nodes);
        free(target);
        return 1;
    }

    /* Eviction buffer: one node every evict_stride_bytes (a page multiple),
     * offset evict_offset_bytes past a fresh page-aligned allocation -- see
     * inclusion_policy.h's module doc comment for why this specific shape
     * both avoids target's own set and still spans many lower-level sets. */
    uint64_t evict_buffer_bytes =
        (uint64_t)(evict_nodes - 1) * cfg->evict_stride_bytes + sizeof(struct node);
    uint64_t evict_alloc_bytes = evict_buffer_bytes + cfg->evict_offset_bytes;
    void *evict_alloc = NULL;
    if (posix_memalign(&evict_alloc, PAGE_BYTES, (size_t)evict_alloc_bytes) != 0 ||
        evict_alloc == NULL) {
        fprintf(stderr, "allocation failed for eviction set (%zu nodes, %" PRIu64 " bytes)\n",
                evict_nodes, evict_alloc_bytes);
        free(control);
        free(target);
        return 1;
    }
    void *evict_base = (void *)((uint8_t *)evict_alloc + cfg->evict_offset_bytes);

    const char *pattern_name =
        (cfg->pattern == ACCESS_PATTERN_SEQUENTIAL) ? "sequential" : "random";

    if (cfg->pattern == ACCESS_PATTERN_SEQUENTIAL) {
        make_sequential_cycle(target, target_nodes);
        make_sequential_cycle(control, target_nodes);
        make_sequential_cycle_strided(evict_base, evict_nodes, (size_t)cfg->evict_stride_bytes);
    } else {
        make_random_cycle(target, target_nodes, cfg->seed);
        make_random_cycle(control, target_nodes, cfg->seed + 1u);
        make_random_cycle_strided(evict_base, evict_nodes, (size_t)cfg->evict_stride_bytes,
                                   cfg->seed + 2u);
    }

    for (int w = 0; w < cfg->warmup_passes; w++) {
        chase(target, (uint64_t)target_nodes);
        chase(control, (uint64_t)target_nodes);
        chase(evict_base, (uint64_t)evict_nodes);
    }

    printf("# experiment=inclusion_policy trials_requested=%" PRIu64
           " target_bytes=%" PRIu64 " evict_bytes=%" PRIu64
           " evict_stride_bytes=%" PRIu64 " evict_offset_bytes=%" PRIu64
           " warmup_passes=%d seed=%u node_bytes=%zu pattern=%s\n",
           cfg->samples, cfg->target_bytes, cfg->evict_bytes, cfg->evict_stride_bytes,
           cfg->evict_offset_bytes, cfg->warmup_passes, cfg->seed, sizeof(struct node),
           pattern_name);
    printf("target_bytes,evict_bytes,evict_stride_bytes,evict_offset_bytes,pattern,channel,trial_index,ticks\n");

    for (uint64_t trial = 0; trial < cfg->samples; trial++) {
        /* Untimed: refresh target/control residency, then displace via the
         * eviction walk (see module doc comment -- this is the only
         * "eviction" mechanism in this codebase; there is no clflush). */
        chase(target, (uint64_t)target_nodes);
        chase(control, (uint64_t)target_nodes);
        chase(evict_base, (uint64_t)evict_nodes);

        /* Timed: exactly one dependent reload of each. */
        uint64_t t0 = timer_start();
        struct node *r_target = target->next;
        uint64_t t1 = timer_stop();

        uint64_t t2 = timer_start();
        struct node *r_control = control->next;
        uint64_t t3 = timer_stop();

        incl_sink = r_target;
        incl_sink = r_control;

        printf("%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%s,target,%" PRIu64 ",%" PRIu64 "\n",
               cfg->target_bytes, cfg->evict_bytes, cfg->evict_stride_bytes,
               cfg->evict_offset_bytes, pattern_name, trial, (uint64_t)(t1 - t0));
        printf("%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%s,control,%" PRIu64 ",%" PRIu64 "\n",
               cfg->target_bytes, cfg->evict_bytes, cfg->evict_stride_bytes,
               cfg->evict_offset_bytes, pattern_name, trial, (uint64_t)(t3 - t2));
    }
    fflush(stdout);

    free(evict_alloc);
    free(control);
    free(target);
    return 0;
}
