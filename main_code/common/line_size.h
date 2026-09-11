#ifndef LINE_SIZE_H
#define LINE_SIZE_H

#include <stdint.h>

#include "access_pattern.h"

/* Two independently-designed cache-line-size experiments live in this one
 * file/header pair (merged from what used to be line_size.c/h +
 * line_size_family.c/h):
 *
 *   run_line_size_experiment()        -- single-curve method: hold working-set
 *     footprint FIXED, sweep byte stride, and read the line size off where
 *     the resulting ramp SATURATES (see scripts/detect_line_size.py).
 *
 *   run_line_size_family_experiment() -- family-of-curves method (PROJECT
 *     1.pdf Figure 3 / "Example B"): hold one candidate byte stride FIXED,
 *     sweep working-set footprint, run once per candidate stride, and read
 *     the line size off which stride's curve separates from a shared
 *     low-stride baseline (see scripts/plot_line_size_family.py).
 *
 * Both are driven by the single scripts/run_line_size.sh pipeline, which
 * runs them per cache level and reports whether the two independent methods
 * agree -- see that script's header comment.
 */

struct line_size_config {
    uint64_t samples;          /* total timed accesses per stride point (>= 1e6 required) */
    uint64_t batch_size;       /* dependent accesses per timed batch */
    uint64_t footprint_bytes;  /* FIXED virtual span (num_nodes*stride) held constant across
                                 * the sweep -- choose just above a known capacity boundary
                                 * (see scripts/run_line_size.sh) or the line-size knee
                                 * is invisible: if the footprint always fits comfortably in
                                 * one cache level regardless of stride, nothing ever misses
                                 * and there is no signal to detect. */
    uint64_t min_stride;       /* smallest byte stride between nodes swept (clamped up to
                                 * >= sizeof(struct node), the minimum viable spacing) */
    uint64_t max_stride;       /* largest byte stride between nodes swept */
    uint64_t stride_step;      /* linear stride increment in bytes -- deliberately NOT
                                 * log-spaced like capacity's points_per_octave, since the
                                 * boundary must be probed byte-by-byte (e.g. 63/64/65), not
                                 * octave-by-octave */
    uint64_t align_bytes;      /* buffer base alignment (must be a power of two and a
                                 * multiple of every candidate stride) so node 0's offset
                                 * relative to any real physical cache line is always known
                                 * and recorded (0) -- this is how the sweep satisfies the
                                 * "record alignment so a boundary-crossing effect is not
                                 * confused with line size" requirement */
    int warmup_passes;         /* untimed full cycle passes before timing */
    uint32_t seed;             /* xorshift32 seed for the random cycle */
    enum access_pattern pattern; /* random (default) or sequential control */
};

/*
 * Holds working-set footprint FIXED at footprint_bytes and sweeps the byte
 * stride between consecutive nodes linearly from min_stride to max_stride
 * (num_nodes = footprint_bytes / stride, so the virtual span stays constant
 * while real cache occupancy -- distinct lines touched -- varies with
 * stride). Prints one raw CSV row per (stride, batch) to stdout:
 *   stride_bytes,num_nodes,footprint_bytes,align_bytes,pattern,batch_index,avg_ticks_per_access
 *
 * Run both patterns over the same stride range: the random-vs-sequential
 * comparison is load-bearing here, not just a sanity check -- a fixed-byte
 * stride sequential stream is exactly what a hardware stride prefetcher is
 * built to hide, so only the randomized-order curve is trustworthy evidence
 * of a real line-size effect. See scripts/detect_line_size.py.
 *
 * Known limitation: this sweep holds the buffer's base alignment fixed
 * (align_bytes, page-aligned by default) rather than also sweeping a
 * sub-line base offset. That is sufficient to record alignment as a
 * controlled, known parameter; run_line_size_family_experiment() below is
 * the one that actually sweeps a node-0 offset (see its offset_bytes field).
 */
int run_line_size_experiment(const struct line_size_config *cfg);

struct line_size_family_config {
    uint64_t samples;          /* total timed accesses per footprint point (>= 1e6 required) */
    uint64_t batch_size;       /* dependent accesses per timed batch */
    uint64_t stride;           /* FIXED byte stride between nodes for this whole sweep --
                                 * one candidate line-size guess (e.g. 8/16/32/64/128/256).
                                 * Run this experiment once per candidate stride (see
                                 * scripts/run_line_size.sh) and overlay the resulting
                                 * curves -- that overlay is the required "family of curves". */
    uint64_t min_bytes;        /* smallest working-set footprint swept (log-spaced, like capacity) */
    uint64_t max_bytes;        /* largest working-set footprint swept */
    int points_per_octave;     /* footprint samples per doubling */
    uint64_t align_bytes;      /* buffer base alignment (power of two), so node 0 sits at a
                                 * known, recorded offset relative to a real physical line */
    uint64_t offset_bytes;     /* extra byte offset added on top of align_bytes before laying
                                 * out node 0 -- lets the SAME candidate stride be re-tested at
                                 * different positions relative to a physical line boundary
                                 * (homework step 4: "repeat with different alignments"), so an
                                 * elbow that only shows up at one offset can be told apart from
                                 * a real, offset-independent spatial-locality transition. 0
                                 * reproduces the always-line-aligned-base behavior. See
                                 * scripts/run_line_size.sh. */
    int warmup_passes;         /* untimed full cycle passes before timing */
    uint32_t seed;             /* xorshift32 seed for the random cycle */
    enum access_pattern pattern; /* random (default) or sequential control */
};

/*
 * Holds the byte stride between consecutive pointer-chase nodes FIXED at
 * cfg->stride and sweeps total working-set footprint log-spaced from
 * min_bytes to max_bytes (num_nodes = footprint_bytes / stride) -- the same
 * sweep shape as run_capacity_experiment(), but at an arbitrary node
 * spacing instead of always tightly packing nodes at sizeof(struct node).
 *
 * This is the "family of curves" side of line-size inference (homework
 * Figure 3 / Example B): run this once per candidate stride s and overlay
 * the resulting footprint-vs-latency curves. Curves for s <= true_line_size
 * should coincide almost exactly, because any such s still touches
 * essentially footprint_bytes/line_size distinct cache lines (multiple
 * nodes legitimately share a line, so real cache pressure only depends on
 * total footprint, not on s). Curves for s > true_line_size separate from
 * that shared baseline: each node now occupies its own line, so the same
 * footprint_bytes touches fewer, more sparsely spread lines and the
 * capacity transition is pushed out to a larger footprint. The smallest
 * candidate stride whose curve visibly separates from the shared baseline
 * is the line-size estimate -- see scripts/plot_line_size_family.py.
 *
 * Prints one raw CSV row per (footprint, batch) to stdout:
 *   footprint_bytes,num_nodes,stride_bytes,align_bytes,offset_bytes,pattern,batch_index,avg_ticks_per_access
 */
int run_line_size_family_experiment(const struct line_size_family_config *cfg);

#endif
