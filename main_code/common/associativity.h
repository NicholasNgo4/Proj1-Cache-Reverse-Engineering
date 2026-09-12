#ifndef ASSOCIATIVITY_H
#define ASSOCIATIVITY_H

#include <stdint.h>

#include "access_pattern.h"

struct associativity_config {
    uint64_t samples;       /* total timed accesses per num_ways point (>= 1e6 required) */
    uint64_t batch_size;    /* dependent accesses per timed batch */
    uint64_t cache_bytes;   /* stride between probed nodes, in bytes -- MUST be the
                              * target cache level's own capacity (or another whole
                              * multiple of that level's set-stride), not an arbitrary
                              * value: two addresses exactly cache_bytes apart always
                              * share the same set-index bits regardless of line size or
                              * associativity, because capacity = sets * line_size * ways
                              * is by definition a whole number of set-strides (see
                              * scripts/run_associativity_full.sh, which derives this
                              * from a completed capacity run). Only required to be a
                              * multiple of 4096 (the page size) -- NOT a power of two;
                              * that stricter check was relaxed (2026-09-12) specifically
                              * so a candidate can be tested at residues that don't align
                              * with a power-of-two page-indexed structure (DTLB, or a
                              * sliced/hashed cache -- see the two "known limitation"
                              * paragraphs below and CLAUDE.md's residue-scan writeup) */
    uint64_t min_ways;       /* fewest same-set nodes probed (clamped up to >= 2, the
                               * minimum viable cycle length) */
    uint64_t max_ways;       /* most same-set nodes probed */
    uint64_t way_step;       /* linear increment in nodes probed -- deliberately 1 by
                               * default: associativity is an exact small integer, not a
                               * byte-granularity boundary, so there is no "coarse octave"
                               * equivalent worth skipping */
    int warmup_passes;       /* untimed full cycle passes before timing */
    uint32_t seed;           /* xorshift32 seed for the random cycle */
    enum access_pattern pattern; /* random (default) or sequential control */
};

/*
 * Holds the node-to-node stride FIXED at cache_bytes (the capacity of the
 * cache level under test) and sweeps how many same-set nodes are chased in
 * one dependent cycle, from min_ways to max_ways. Every probed node lands
 * in the same cache set by construction (see cache_bytes's doc comment
 * above) but carries a distinct tag, so this counts how many simultaneous
 * tags that one set can hold before it starts evicting.
 *
 * Prints one raw CSV row per (num_ways, batch) to stdout:
 *   num_ways_probed,cache_bytes,pattern,batch_index,avg_ticks_per_access
 *
 * Expected shape: latency stays flat at hit cost while num_ways_probed <=
 * true associativity, then jumps sharply to next-level/miss cost once it's
 * exceeded (a cyclic dependent chase over N distinct blocks with an
 * (N-1)-way-or-smaller LRU set thrashes on every access, not gradually) --
 * see scripts/detect_associativity.py, which locates that step.
 *
 * Run both patterns over the same num_ways range: the random-vs-sequential
 * comparison here is a weaker prefetcher-sanity control than in
 * capacity/line_size (the stride is enormous, well past what a hardware
 * stride prefetcher typically tracks), but keeping it is cheap and
 * consistent with every other experiment's discipline.
 *
 * Known limitation: this assumes the cache level under test is indexed by
 * bits that a virtual-address stride of cache_bytes actually preserves
 * (true for VIPT/PIPT-with-page-aligned-index L1/L2). A physically-indexed
 * LLC may not honor this from virtual addresses alone if the OS scatters
 * physical pages -- treat an LLC associativity result as provisional until
 * cross-checked (e.g. with huge pages) if it looks noisy.
 *
 * A second, distinct known limitation for L2/LLC: even on a machine where
 * physical pages happen to stay contiguous (or huge pages are used), many
 * modern LLCs are SLICED and use a HASH function over extra physical
 * address bits (not just the low index bits capacity/sets/line_size would
 * suggest) to pick which slice a given address lands in. A stride of
 * exactly cache_bytes only guarantees "same set" under a plain linear
 * index; under a non-trivial slice hash, two addresses cache_bytes apart
 * can hash to DIFFERENT slices even though they'd share a set-index under
 * the naive model, which would look like extra effective capacity (a
 * higher apparent associativity, or no knee within max_ways at all) rather
 * than a clean thrashing knee. This is a plausible alternative explanation
 * for the same symptom the CLAUDE.md associativity section's leading
 * DTLB-aliasing hypothesis was written to explain (multi-step/no-knee L2/
 * LLC results) and has NOT been ruled out relative to that hypothesis --
 * both remain open. Same Phase I caveat as the DTLB thread applies: do not
 * try to confirm or rule this out by reading hardware hash/slice
 * documentation or CPU-specific tables; only timing-based inference is
 * permitted pre-freeze.
 */
int run_associativity_experiment(const struct associativity_config *cfg);

#endif
