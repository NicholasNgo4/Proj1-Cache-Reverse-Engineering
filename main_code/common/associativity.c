/* Needed for posix_memalign() and madvise()/MADV_HUGEPAGE under strict
 * -std=c11 (neither is ISO C -- both are POSIX/glibc extensions). Must
 * precede every #include, per glibc's feature-test-macro requirements. */
#define _GNU_SOURCE

#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>

#include "associativity.h"
#include "benchmark.h"
#include "pointer_chase.h"
#include "random.h"

/*
 * Reports the ACTUAL huge-page backing achieved for [base, base+size), read
 * from this process's own /proc/self/smaps -- a successful madvise() call is
 * only a hint to the kernel, not a guarantee, so this is measured rather than
 * assumed. Finds the VMA containing `base` and prints its AnonHugePages
 * field; a nonzero value confirms the allocation is genuinely backed by one
 * or more 2 MiB pages at the time of the call.
 */
static void report_huge_page_backing(const void *base, uint64_t size, uint64_t num_ways)
{
    FILE *f = fopen("/proc/self/smaps", "r");
    if (f == NULL) {
        fprintf(stderr, "huge_pages_diag num_ways=%" PRIu64 " buffer_bytes=%" PRIu64
                " /proc/self/smaps unavailable (errno=%d)\n", num_ways, size, errno);
        return;
    }

    uintptr_t target = (uintptr_t)base;
    char line[512];
    int in_region = 0;
    unsigned long region_kb = 0;
    unsigned long anon_huge_kb = 0;

    while (fgets(line, sizeof(line), f) != NULL) {
        unsigned long start, end;
        if (sscanf(line, "%lx-%lx", &start, &end) == 2) {
            in_region = (target >= start && target < end);
            if (in_region) {
                region_kb = (end - start) / 1024;
            }
            continue;
        }
        if (in_region && strncmp(line, "AnonHugePages:", 14) == 0) {
            sscanf(line + 14, "%lu", &anon_huge_kb);
            break;
        }
    }
    fclose(f);

    fprintf(stderr, "huge_pages_diag num_ways=%" PRIu64 " buffer_bytes=%" PRIu64
            " vma_kB=%lu anon_huge_kB=%lu (%s)\n",
            num_ways, size, region_kb, anon_huge_kb,
            anon_huge_kb > 0 ? "HUGE-PAGE BACKED" : "NOT huge-page backed -- treat this run's result as inconclusive for the huge-page test");
}

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

        void *base = NULL;
        void *map_raw = NULL;   /* only set (and only munmap()-able) on the huge_alloc path */
        size_t map_len = 0;     /* munmap() needs the exact length back, unlike free() */
        int huge_alloc = 0;
        if (cfg->huge_pages) {
            const size_t HUGE_ALIGN = 2ULL * 1024 * 1024; /* this machine's Hugepagesize */
            /* posix_memalign()/malloc() below ~128 KiB get served out of glibc's heap
             * arena, not a dedicated VMA -- THP collapse needs its own VMA to apply to,
             * so allocate via mmap() directly. mmap() has no alignment parameter, so
             * over-reserve by one extra HUGE_ALIGN, carve out the 2 MiB-aligned region
             * we actually want, and munmap() the unused head/tail slack. */
            size_t want = (((size_t)buffer_bytes + HUGE_ALIGN - 1) / HUGE_ALIGN) * HUGE_ALIGN;
            size_t reserve = want + HUGE_ALIGN;
            void *raw = mmap(NULL, reserve, PROT_READ | PROT_WRITE,
                              MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
            if (raw == MAP_FAILED) {
                fprintf(stderr, "mmap failed (errno=%d) at num_ways=%" PRIu64
                        "; falling back to malloc (result NOT huge-page-eligible)\n",
                        errno, num_ways);
                base = malloc((size_t)buffer_bytes);
            } else {
                uintptr_t aligned = ((uintptr_t)raw + HUGE_ALIGN - 1) & ~(uintptr_t)(HUGE_ALIGN - 1);
                size_t head_slack = aligned - (uintptr_t)raw;
                size_t tail_slack = reserve - head_slack - want;
                if (head_slack > 0) { munmap(raw, head_slack); }
                if (tail_slack > 0) { munmap((void *)(aligned + want), tail_slack); }
                base = (void *)aligned;
                map_raw = base;
                map_len = want;
                huge_alloc = 1;
                if (madvise(base, want, MADV_HUGEPAGE) != 0) {
                    fprintf(stderr, "madvise(MADV_HUGEPAGE) failed at num_ways=%" PRIu64
                            " (errno=%d)\n", num_ways, errno);
                }
            }
        } else {
            base = malloc((size_t)buffer_bytes);
        }
        if (base == NULL) {
            fprintf(stderr,
                    "allocation failed at num_ways=%" PRIu64 " (%" PRIu64 " bytes virtual"
                    " span)\n",
                    num_ways, buffer_bytes);
            free(batch_latencies);
            return 1;
        }

        if (huge_alloc) {
            /* Fault in every 4 KiB page before building the chain/warmup --
             * chase() only touches the exact node offsets (cache_bytes apart),
             * which would leave most of a >4 KiB-per-node buffer untouched and
             * give the kernel nothing to back with a huge page. A volatile
             * read-modify-write can't be optimized away even without -O0. */
            volatile char *touch = (volatile char *)base;
            for (uint64_t off = 0; off < map_len; off += 4096) {
                touch[off] = touch[off];
            }
            report_huge_page_backing(base, map_len, num_ways);
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

        if (huge_alloc) {
            munmap(map_raw, map_len);
        } else {
            free(base);
        }
    }

    free(batch_latencies);
    return 0;
}
