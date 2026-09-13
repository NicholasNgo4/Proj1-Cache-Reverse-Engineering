#ifndef INCLUSION_POLICY_H
#define INCLUSION_POLICY_H

#include <stdint.h>

#include "access_pattern.h"

/*
 * Method (PROJECT 1.pdf item 7): establish a target line resident in a
 * small UPPER (inner, closer-to-core) cache level, apply capacity-scale
 * eviction pressure at a bigger LOWER (outer, closer-to-memory) level, and
 * reload the target -- comparing its latency against calibrated hit-latency
 * classes (done downstream by scripts/classify_inclusion_policy.py, using
 * this machine's own hit_latency data) tells you whether the upper-level
 * copy survived (evidence of exclusive/non-inclusive behavior) or was
 * invalidated along with the lower-level copy (evidence of inclusive
 * behavior). "Upper"/"lower" follow the standard textbook diagram: L1 drawn
 * closest to the core ("upper"), LLC drawn closest to memory ("lower") --
 * matching the assignment's own phrasing, "if lower-level eviction
 * consistently removes the upper-level copy, that is evidence of inclusive
 * behavior."
 *
 * THE HARD PART, and why this needs its own construction instead of
 * reusing miss_latency's: the assignment explicitly asks to displace the
 * target from the lower level "while avoiding a direct intentional
 * eviction from the upper level when possible." A naive, DENSELY-packed
 * eviction buffer (capacity.c/miss_latency.c's usual construction, node
 * stride = sizeof(struct node)) touches EVERY byte offset within EVERY
 * page it spans -- across a multi-page (let alone multi-MB) eviction
 * buffer, that means it inevitably also touches whatever narrow byte
 * range corresponds to the target's own upper-level SET on every single
 * page, hammering that one set directly. That is not "avoiding" upper-
 * level eviction at all; it is guaranteeing it. A naive SAME-CAPACITY-
 * STRIDE buffer (associativity.h's technique) is even worse for this
 * purpose: by design, EVERY node it touches shares the target's exact
 * page offset, which is precisely what must be avoided here.
 *
 * THE FIX: build the eviction chain with a stride that is an exact
 * multiple of 4096 (the page size) -- see evict_stride_bytes below -- so
 * every eviction node shares the SAME fixed sub-page byte position
 * (evict_offset_bytes) across however many distinct pages the walk spans,
 * instead of touching every byte of every page. Placing that fixed
 * position at a different offset than the target's (target is always
 * allocated page-aligned, i.e. offset 0) means the eviction walk can
 * genuinely never land on the target's own line/set, PROVIDED the upper
 * level's entire index range fits within one page (4096 B) -- true for a
 * typical VIPT L1 (e.g. 32-64 KiB, 8-way, since a physically-indexed LLC
 * cannot alias the untranslated low bits a VIPT L1 uses for its own
 * index). Meanwhile, because the walk still spans many DIFFERENT pages
 * (varying the higher-order address bits a bigger, physically-indexed
 * lower level's own index depends on), it still exerts broad capacity
 * pressure across many of the lower level's sets -- both properties at
 * once, from page-size knowledge alone, with NO dependence on the actual
 * cache line size or associativity of either level.
 *
 * KNOWN LIMITATION: this reasoning only holds when the UPPER level's own
 * index range fits within one page -- true for most real L1 caches, but
 * NOT for an L2-or-bigger target (its own index range spans many pages by
 * construction). Testing inclusion with a target at L2 or above reduces to
 * the same unavoidable-collision case a dense eviction buffer would give;
 * report that explicitly rather than claiming clean avoidance. This is
 * also why a `control` channel is measured every trial (see below) --
 * it's a live, per-run check of whether the avoidance assumption is
 * actually holding on this specific machine/level, not just an assumption
 * taken on faith.
 */
struct inclusion_policy_config {
    uint64_t samples;             /* number of single-shot trials (each trial produces
                                      two CSV rows -- target and control channels -- not
                                      a batch average) */
    uint64_t target_bytes;        /* footprint of the target's own small, densely-packed
                                      set -- MUST already be confirmed to sit inside the
                                      UPPER level under test (e.g. an L1 boundary from
                                      CAPACITY_RESULTS.md); no auto-detection, same
                                      explicit-only discipline as every other experiment
                                      here */
    uint64_t evict_bytes;         /* total footprint of the eviction walk -- MUST exceed
                                      the LOWER level's real capacity (e.g. the LLC
                                      boundary from CAPACITY_RESULTS.md) to exert genuine
                                      capacity pressure there */
    uint64_t evict_stride_bytes;  /* byte stride between consecutive eviction nodes --
                                      MUST be a multiple of 4096 (validated in main.c) so
                                      every eviction node shares the same low-order
                                      (sub-page) address bits; default 4096 (exactly one
                                      page per node) */
    uint64_t evict_offset_bytes;  /* the fixed sub-page byte position every eviction node
                                      shares (MUST be < evict_stride_bytes) -- deliberately
                                      different from the target/control buffers' own
                                      offset (always 0, since they're freshly page-aligned)
                                      so the eviction walk structurally cannot land on the
                                      target's own line; default 2048 (half a page, far
                                      past any realistic real line size) */
    int warmup_passes;             /* untimed target/control-touch + eviction-walk passes
                                       before the first timed trial */
    uint32_t seed;
    enum access_pattern pattern;   /* controls the EVICTION SET's traversal order only
                                       (random default; sequential is the prefetcher-
                                       sanity control) -- both timed reloads are always a
                                       single dependent load either way */
};

/*
 * Per trial: untimed re-touch of the target set and the control set (both
 * page-aligned, offset 0 -- refreshes their upper-level residency), untimed
 * chase() of the eviction cycle (see the module doc comment above for why
 * its construction avoids the target's own set while still pressuring many
 * of the lower level's), then ONE timed dependent reload of the target and
 * ONE of the control, each via timer_start()/timer_stop() directly (no new
 * architecture-specific code needed -- see latency.c/miss_latency for the
 * same reasoning). The control channel is a live per-run sanity check: it
 * sits at the exact same offset (0) as the target but is never touched by
 * the eviction walk by construction, so it should read at upper-level-hit
 * speed on every trial REGARDLESS of this machine's inclusion policy; if it
 * doesn't, that's evidence the avoidance construction isn't holding here
 * (see the KNOWN LIMITATION above), not evidence about inclusion policy.
 *
 * Prints TWO raw CSV rows per trial (target then control -- one experiment,
 * two "channels" sharing every other key column, so
 * scripts/summarize_raw.py's single-value-column model handles both without
 * modification) to stdout:
 *   target_bytes,evict_bytes,evict_stride_bytes,evict_offset_bytes,pattern,channel,trial_index,ticks
 *
 * This experiment reports raw per-channel latencies only. Classifying them
 * as inclusive/exclusive/non-inclusive/uncertain against this machine's own
 * calibrated hit_latency classes is done downstream by
 * scripts/classify_inclusion_policy.py, which needs the RAW per-trial data
 * (not just a summarized median) to report what FRACTION of trials look
 * like each class -- a single average can hide a genuinely mixed/bimodal
 * result the assignment explicitly warns not to over-claim from.
 */
int run_inclusion_policy_experiment(const struct inclusion_policy_config *cfg);

#endif
