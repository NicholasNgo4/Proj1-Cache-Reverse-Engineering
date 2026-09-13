#ifndef LATENCY_H
#define LATENCY_H

#include <stdint.h>

#include "access_pattern.h"

enum load_mode {
    LOAD_MODE_DEPENDENT = 0,
    LOAD_MODE_INDEPENDENT = 1,
};

struct hit_latency_config {
    uint64_t samples;            /* total timed accesses (>= 1e6 required) */
    uint64_t batch_size;         /* accesses per timed batch */
    uint64_t footprint_bytes;    /* ONE working-set size, already confirmed by
                                     the caller to sit inside a single cache
                                     level -- no auto-detection, same explicit-
                                     only discipline as associativity's
                                     --cache-bytes; see
                                     scripts/run_hit_latency_full.sh */
    int warmup_passes;           /* untimed full dependent-cycle passes before
                                     timing, run regardless of load_mode so
                                     both modes start from the same warmed
                                     residency */
    uint32_t seed;                /* xorshift32 seed for both the chain build
                                      and (in independent mode) the address
                                      permutation */
    enum access_pattern pattern;  /* random (default) or sequential control */
    enum load_mode load_mode;     /* which batched timer to run, see below */
};

/*
 * Measures per-access latency at ONE fixed working-set footprint (already
 * confirmed, by the caller, to sit inside a single cache level -- this
 * experiment infers nothing about capacity itself; that's capacity.c's job).
 * Two load modes, selected by --load-mode:
 *
 *   dependent   -- the same batched dependent pointer-chase every other
 *                  experiment uses (measure_dependency_chain_batched()).
 *                  This is the correct hit-latency number: memory-level
 *                  parallelism cannot hide any of it.
 *   independent -- batched, but each load's address is drawn from a
 *                  precomputed random permutation instead of the previous
 *                  load's result (measure_independent_loads_batched()). A
 *                  REQUIRED diagnostic control only, expected to read
 *                  *faster* per access because it exposes memory-level
 *                  parallelism -- must never be reported as the latency
 *                  number itself (PROJECT 1.pdf item 5).
 *
 * Prints one raw CSV row per batch to stdout:
 *   footprint_bytes,load_mode,pattern,batch_index,avg_ticks_per_access
 */
int run_hit_latency_experiment(const struct hit_latency_config *cfg);

struct miss_latency_config {
    uint64_t samples;       /* number of single-shot reload trials -- each
                                trial is exactly one timed dependent load, so
                                this is also the output row count, unlike the
                                batched experiments */
    uint64_t target_bytes;  /* footprint that places the target line inside
                                the SOURCE level (e.g. well inside a confirmed
                                L1 boundary) */
    uint64_t evict_bytes;   /* footprint of the eviction-set walk -- must
                                exceed the source level's real capacity (so
                                the target is actually displaced) while
                                staying inside the NEXT level's capacity (so
                                the walk itself doesn't also evict from the
                                level being measured into). Both byte values
                                are the caller's responsibility -- same
                                explicit-only, hand-confirmed-boundary
                                discipline as associativity's --cache-bytes;
                                see scripts/run_miss_latency_full.sh */
    int warmup_passes;       /* untimed target-touch + eviction-walk passes
                                 before the first timed trial */
    uint32_t seed;
    enum access_pattern pattern; /* controls the EVICTION SET's traversal
                                     order only (random default; sequential
                                     is the prefetcher-sanity control) -- the
                                     timed reload of the target is always a
                                     single dependent load either way */
};

/*
 * Forces the target line out of the source level, then times exactly the
 * first dependent access back to it -- the miss/next-level-latency
 * measurement (PROJECT 1.pdf item 6). Per trial: untimed re-touch of the
 * target set (re-establishes its residency in the source level), untimed
 * chase() of a fresh eviction-set cycle sized by evict_bytes (displaces the
 * target -- this is the only "eviction" mechanism in this codebase; there is
 * no clflush anywhere, so it relies entirely on the eviction set being sized,
 * by the caller, past the source level's real capacity), then ONE timed
 * dependent reload of the target via timer_start()/timer_stop() directly
 * (already portable across x86/ARM via timer.h -- no new architecture-
 * specific code is needed for this).
 *
 * Prints one raw CSV row per trial (not a batch average, since the
 * measurement is inherently one dependent load) to stdout:
 *   target_bytes,evict_bytes,pattern,trial_index,ticks
 *
 * This experiment reports the observed next-level access latency only. The
 * incremental miss penalty relative to the source level's own hit latency
 * (the other number PROJECT 1.pdf item 6 asks for) is a derived quantity --
 * computed downstream by scripts/plot_miss_latency.py from a paired
 * hit_latency processed summary, not by this experiment itself.
 *
 * KNOWN LIMITATION -- single-shot measurement overhead is baked into every
 * trial and is NOT directly comparable to hit_latency's batched numbers.
 * Confirmed on Sunbird (2026-09-13): a control run with target_bytes=32768
 * and a deliberately tiny, mostly-non-colliding evict_bytes (512 B, ~8
 * cache lines spread across L1's 64 sets -- overwhelmingly unlikely to
 * evict the target's own specific line) still measured a ~64-85 tick
 * median/min, versus hit_latency's batched L1 number of ~10 ticks at the
 * IDENTICAL footprint. Since that control trial shouldn't be evicting the
 * target most of the time, this gap is fixed per-measurement overhead, not
 * real miss cost: timer_start()/timer_stop()'s serializing instructions
 * (lfence/rdtsc/rdtscp) and the pipeline state right after a chase()/
 * function-call boundary cost much more when timed once than when
 * amortized across a batch of 1000+ back-to-back accesses (as every other
 * experiment in this codebase does). This means a raw miss_latency median
 * is roughly "true reload latency + a few dozen ticks of fixed overhead",
 * not a clean number -- report it as such, and treat any direct comparison
 * to a hit_latency plateau (e.g. the incremental-penalty annotation in
 * plot_miss_latency.py) as approximate until this overhead is itself
 * measured per-machine and subtracted, which this codebase does not yet
 * do automatically.
 */
int run_miss_latency_experiment(const struct miss_latency_config *cfg);

#endif
