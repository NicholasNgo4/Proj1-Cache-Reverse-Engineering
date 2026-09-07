#define _GNU_SOURCE
/*
 * cache_bench.c -- portable cache reverse-engineering benchmark.
 *
 * PHASE-I STATUS: this is a first working skeleton implementing only
 * --mode=capacity, at a SINGLE working-set size per invocation (the
 * driver script, written next, will call this repeatedly across a
 * size sweep). It is intentionally incomplete: it currently reports
 * only the median, not the full distribution (Q1/Q3/5th/95th
 * percentiles, outlier count) that the assignment requires -- that
 * comes next once this skeleton is confirmed working end-to-end on
 * real hardware.
 *
 * One source file, two architecture-specific timer paths, selected at
 * compile time -- this is the "one parameterized program" the
 * assignment expects, not seven separate programs.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <sched.h>
#include <unistd.h>

#include "pointer_chase.h"

#if defined(__x86_64__)
#include "timer_x86.h"
#elif defined(__aarch64__)
#include "timer_arm.h"
#else
#error "Unsupported architecture: add a timer_*.h for this target"
#endif

static int cmp_uint64(const void *a, const void *b) {
    uint64_t x = *(const uint64_t *)a;
    uint64_t y = *(const uint64_t *)b;
    return (x > y) - (x < y);
}

static void print_usage(const char *prog) {
    fprintf(stderr,
        "Usage: %s --mode=capacity --size=<bytes> --samples=<N> "
        "--cpu=<logical_cpu> [--seed=<S>] [--batch=<B>]\n", prog);
}

int main(int argc, char **argv) {
    size_t   footprint = 0;
    uint64_t samples   = 1000000;
    uint64_t batch     = 2000;
    int      cpu       = -1;
    uint32_t seed      = 12345;
    const char *mode   = NULL;

    for (int i = 1; i < argc; i++) {
        if      (strncmp(argv[i], "--mode=",    7) == 0) mode      = argv[i] + 7;
        else if (strncmp(argv[i], "--size=",    7) == 0) footprint = strtoull(argv[i] + 7, NULL, 10);
        else if (strncmp(argv[i], "--samples=",10) == 0) samples   = strtoull(argv[i] + 10, NULL, 10);
        else if (strncmp(argv[i], "--cpu=",     6) == 0) cpu       = atoi(argv[i] + 6);
        else if (strncmp(argv[i], "--seed=",    7) == 0) seed      = (uint32_t)strtoul(argv[i] + 7, NULL, 10);
        else if (strncmp(argv[i], "--batch=",   8) == 0) batch     = strtoull(argv[i] + 8, NULL, 10);
        else { print_usage(argv[0]); return 1; }
    }

    if (!mode || strcmp(mode, "capacity") != 0 || footprint == 0) {
        print_usage(argv[0]);
        return 1;
    }

    /* Pin to one logical CPU. Required control per Section 5: results
     * are meaningless if the OS migrates us mid-measurement. */
    if (cpu >= 0) {
        cpu_set_t set;
        CPU_ZERO(&set);
        CPU_SET(cpu, &set);
        if (sched_setaffinity(0, sizeof(set), &set) != 0) {
            perror("sched_setaffinity");
            return 1;
        }
    }

    size_t n = footprint / sizeof(struct node);
    if (n < 2) n = 2;

    struct node *nodes = malloc(n * sizeof(struct node));
    if (!nodes) { perror("malloc nodes"); return 1; }

    make_random_cycle(nodes, n, seed);

    /* Warm the chain into cache/TLB before timing begins. */
    volatile struct node *p = &nodes[0];
    for (size_t i = 0; i < n; i++) p = p->next;

    /* Batched dependent-chain timing: time `batch` dependent steps
     * between one start/stop pair, divide by `batch`. This amortizes
     * timer/fence overhead toward zero -- see Section 6F. A single-
     * access measurement cannot separate an L1 hit from an L2 hit
     * because the fence+timer overhead itself exceeds an L1 latency. */
    uint64_t *results = malloc(samples * sizeof(uint64_t));
    if (!results) { perror("malloc results"); free(nodes); return 1; }

    for (uint64_t s = 0; s < samples; s++) {
        compiler_barrier();
        uint64_t t0 = timer_start();
        for (uint64_t i = 0; i < batch; i++) {
            p = p->next;
        }
        uint64_t t1 = timer_stop();
        compiler_barrier();
        results[s] = (t1 - t0);
    }
    (void)p; /* keep the final pointer value observable, silence unused warning */

    qsort(results, samples, sizeof(uint64_t), cmp_uint64);
    double median_ticks_per_batch = (double)results[samples / 2];
    double ticks_per_access = median_ticks_per_batch / (double)batch;

    /* TODO (next iteration): also emit Q1, Q3, 5th/95th percentile,
     * mean, stddev, and outlier count -- Section 5 requires the full
     * distribution, not just a median. Also emit raw per-sample data
     * to a separate file for lossless preservation (Section 12). */
    printf("footprint_bytes,n_nodes,samples,batch,median_ticks_per_access,timer_unit\n");
    printf("%zu,%zu,%llu,%llu,%.4f,%s\n",
           footprint, n,
           (unsigned long long)samples, (unsigned long long)batch,
           ticks_per_access, TIMER_UNIT_NAME);

    free(results);
    free(nodes);
    return 0;
}
