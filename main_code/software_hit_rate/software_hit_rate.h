#ifndef SOFTWARE_HIT_RATE_H
#define SOFTWARE_HIT_RATE_H

#include <stdint.h>

#include "../common/access_pattern.h"

/*
 * Problem 8.5 -- software-only, timing-derived cache hit rate estimator. No
 * PMU/perf_event_open access anywhere in this file; every number here comes
 * from timer.h's portable RDTSC/CNTVCT reads and ordinary unprivileged loads.
 * This is also the Competition estimator (see competition/HIT_RATE_VALIDATION.md)
 * -- it MUST self-calibrate fresh on every invocation rather than assume any
 * per-machine constant, so it generalizes to a held-out machine unseen at
 * design time.
 *
 * Method, in three stages, all inside run_hit_rate_experiment():
 *
 *   1. CALIBRATION. Build two pointer-chase cycles (chase()/make_random_cycle(),
 *      same primitives as every other experiment in this codebase):
 *        - "resident" class: a small buffer (resident_bytes, default well
 *          inside a typical L1D), warmed with several full chase() passes so
 *          it is fully cache-resident, then timed with calib_samples
 *          single-shot loads. Definition of "hit" used throughout: served by
 *          ANY level of the cache hierarchy, i.e. not DRAM -- so this class
 *          stands in for "served by cache" in general, not just L1.
 *        - "nonresident" class: a large buffer (nonresident_bytes, default
 *          far past any real LLC) walked the same single-shot way. Because
 *          the cycle is randomized and far larger than the cache hierarchy,
 *          revisiting an already-cached line within any reasonable sample
 *          count is effectively impossible -- this class stands in for
 *          "served by DRAM".
 *      Both classes are timed with EXACTLY the same single-shot
 *      timer_start()/p = p->next/timer_stop() primitive latency.c's
 *      run_miss_latency_experiment() already uses, so both carry the same
 *      fixed per-measurement overhead and remain directly comparable.
 *
 *   2. CLASSIFICATION. A single scalar threshold tau is chosen from the
 *      calibration samples by an ROC sweep that maximizes Youden's J
 *      (TPR(tau) - FPR(tau)) over candidate cut points built from the
 *      merged, sorted calibration data -- the data itself picks tau, this is
 *      not a hand-tuned constant. A fixed threshold is appropriate here
 *      specifically because the two calibration classes are expected to be
 *      well separated (single-digit-tick cache hits vs. hundreds-of-ticks
 *      DRAM misses) -- the resulting sensitivity (Se) and specificity (Sp)
 *      at tau are reported precisely so that assumption is checked against
 *      real data, not just asserted. An access on the TEST workload is
 *      provisionally "classified a hit" iff its latency <= tau.
 *
 *      The raw classified-hit fraction on the test stream, p_obs, is then
 *      debiased into the reported Hhat using the Rogan-Gladen
 *      prevalence-correction estimator (the standard way to correct a
 *      binary classifier's naive positive rate into a calibrated rate
 *      estimate when the classifier's own Se/Sp are known and imperfect):
 *
 *          Hhat = (p_obs + Sp - 1) / (Se + Sp - 1),  clamped to [0, 1]
 *
 *      This is the "probabilistic estimator, justified" the assignment
 *      asks for, rather than a bare threshold count.
 *
 *   3. UNCERTAINTY. A nonparametric bootstrap (bootstrap_reps replicates,
 *      xorshift32-seeded, same PRNG as random.c) resamples the resident,
 *      nonresident, and test arrays with replacement each replicate,
 *      re-derives tau/Se/Sp/Hhat from the resampled data each time, and
 *      reports the resulting [2.5, 97.5] percentile confidence interval and
 *      bootstrap standard deviation alongside the point estimate. This is
 *      computed and printed by this program itself (a "#"-prefixed summary
 *      line), not deferred to a downstream script.
 *
 * KNOWN LIMITATIONS (see report/src/report.tex's "Software-Only Cache
 * Metric" section for the full discussion):
 *   - Single-shot timing carries the same fixed per-measurement overhead
 *     documented in latency.h's run_miss_latency_experiment() docstring
 *     (tens of ticks on this project's machines) -- it affects both
 *     calibration classes and the test stream equally, so it does not bias
 *     the classifier's threshold placement, but it does mean absolute tick
 *     values are inflated relative to a batched measurement.
 *   - A test workload whose true hit rate sits near a cache-level boundary
 *     can produce a genuinely bimodal or heavy-tailed access-latency
 *     mixture; the two calibration classes being well separated does not
 *     guarantee the TEST distribution is free of same-tick collisions
 *     between a slow hit (e.g. an L3 hit under contention) and a fast miss
 *     (e.g. a DRAM row-buffer hit) -- Se/Sp bound this failure mode but
 *     cannot eliminate it.
 *   - No accommodation for hardware prefetching beyond what
 *     make_random_cycle()'s randomized address stream already defeats;
 *     a workload with a prefetch-friendly stride would read as
 *     artificially cache-resident.
 */

struct hit_rate_config {
    uint64_t resident_bytes;     /* calibration "resident" footprint -- caller's
                                     responsibility to keep well inside a real
                                     cache level, same explicit-only discipline
                                     as every other experiment's *_bytes args */
    uint64_t nonresident_bytes;  /* calibration "nonresident" footprint -- must
                                     exceed the true LLC capacity by a wide
                                     margin */
    uint64_t calib_samples;      /* single-shot trials per calibration class */
    uint64_t test_bytes;         /* the working set whose Hhat is being
                                     estimated -- this is the only footprint
                                     whose hit rate is actually unknown to
                                     the estimator */
    uint64_t test_samples;       /* single-shot trials on the test workload */
    uint64_t bootstrap_reps;     /* nonparametric bootstrap replicate count */
    int warmup_passes;           /* untimed full chase() passes before timing
                                     each of the three cycles (resident,
                                     nonresident, test) */
    uint32_t seed;               /* xorshift32 seed -- calibration cycles use
                                     seed/seed+1, the test cycle uses seed+2,
                                     the bootstrap resampler uses seed+3, all
                                     distinct streams */
    enum access_pattern pattern; /* random (default; required for the
                                     nonresident class to behave as claimed)
                                     or sequential prefetcher-sanity control */

    /* OPTIONAL decoupled-calibration override, used ONLY by the PMU
     * validation harness (scripts/run_hit_rate_pmu_validation.sh) -- NEVER
     * set by the estimator's own normal (competition-facing) invocation.
     * See the "PMU VALIDATION MODE" note below for why this exists. When
     * has_fixed_calibration is nonzero, tau/sensitivity/specificity are
     * used AS GIVEN instead of being derived from a resident/nonresident
     * calibration run -- the resident/nonresident buffers are never
     * allocated and no calib_resident/calib_nonresident CSV rows are
     * printed. */
    int has_fixed_calibration;
    double fixed_tau;
    double fixed_sensitivity;
    double fixed_specificity;
};

/*
 * Runs calibration, classification, and the test-workload measurement
 * described above. Prints:
 *   - a "#"-prefixed metadata line echoing the config
 *   - a CSV header + one row per single-shot access:
 *       phase,index,ticks,classified_hit
 *     where phase is one of "calib_resident","calib_nonresident","test"
 *     (calib_* rows are omitted entirely in PMU validation mode, see below)
 *   - a final "#"-prefixed result line:
 *       # result tau_ticks=... sensitivity=... specificity=... p_obs=...
 *       Hhat=... ci_lower=... ci_upper=... bootstrap_std=... bootstrap_reps=...
 * Returns 0 on success, 1 on allocation failure.
 *
 * PMU VALIDATION MODE (cfg->has_fixed_calibration != 0) -- why this exists:
 * `perf stat` counts a PROCESS's entire memory traffic, not just one
 * function's. The normal, self-calibrating mode of this experiment builds
 * and times a large (hundreds-of-MiB) "nonresident" calibration buffer
 * INSIDE THE SAME PROCESS as the test workload -- confirmed on Sunbird
 * (2026-09-14) that this makes a whole-process `perf stat -e
 * cache-references,cache-misses` wrap around the normal mode produce a
 * meaningless comparison: calibration's own (necessary, large) volume of
 * genuine DRAM misses completely swamps the aggregate counters, so
 * H_pmu = 1 - misses/references measured that way reflects mostly
 * calibration traffic, not the test workload's own hit rate (observed:
 * H_pmu ~= 0.51 at an L1-resident test footprint where both this
 * estimator's own Hhat and this project's independent hit_latency-based
 * Phase II PMU run agree the true miss rate is under 1.5%). Scoping the PMU
 * counters to just the test phase via perf_event_open()/ioctl
 * enable-disable from INSIDE this file is not an option -- that would put
 * PMU-reading code in the estimator's own source, which the assignment and
 * competition/HIT_RATE_VALIDATION.md's rules forbid unconditionally, not
 * just "unless a flag is set".
 *
 * The fix used here instead: the PMU validation harness runs cache_bench
 * TWICE per measurement -- once, PLAIN (no perf, exactly the normal
 * self-calibrating mode, calibration-only, run_hit_rate_pmu_validation.sh
 * discards its test-phase numbers) to obtain tau/Se/Sp, then a SECOND time,
 * wrapped in perf, with cfg->has_fixed_calibration set from that first
 * run's already-computed values -- so the perf-wrapped process touches
 * ONLY the test buffer, never the large nonresident calibration buffer,
 * and the whole-process PMU counters are then actually scoped to the same
 * workload the software Hhat is computed from. The estimator's own source
 * still never reads a PMU counter anywhere, in either mode -- only the
 * shell harness around it decides which of two ordinary CLI-argument modes
 * to invoke.
 */
int run_hit_rate_experiment(const struct hit_rate_config *cfg);

#endif
