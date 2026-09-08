#ifndef CAPACITY_H
#define CAPACITY_H

#include <stdint.h>

enum access_pattern {
    ACCESS_PATTERN_RANDOM = 0,     /* randomized dependent cycle (primary) */
    ACCESS_PATTERN_SEQUENTIAL = 1, /* in-array-order dependent cycle (prefetcher control) */
};

struct capacity_config {
    uint64_t samples;          /* total timed accesses per size point (>= 1e6 required) */
    uint64_t batch_size;       /* dependent accesses per timed batch */
    uint64_t min_bytes;        /* smallest working-set footprint swept */
    uint64_t max_bytes;        /* largest working-set footprint swept */
    int points_per_octave;     /* size samples per doubling */
    int warmup_passes;         /* untimed full cycle passes before timing */
    uint32_t seed;             /* xorshift32 seed for the random cycle */
    enum access_pattern pattern; /* random (default) or sequential control */
};

/*
 * Sweeps working-set size with a dependent pointer-chase cycle (randomized
 * by default; --pattern sequential builds the in-array-order control chain
 * instead) and prints one raw CSV row per (size, batch) to stdout:
 *   size_bytes,num_nodes,pattern,batch_index,avg_ticks_per_access
 *
 * This is raw, per-batch data (not a single averaged number) so the
 * distribution at each working-set size can be reconstructed downstream --
 * see scripts/summarize_raw.py and scripts/detect_cache_hierarchy.py. Run
 * both patterns over the same size range to get the required regular-vs-
 * randomized prefetcher sanity check.
 */
int run_capacity_experiment(const struct capacity_config *cfg);

#endif
