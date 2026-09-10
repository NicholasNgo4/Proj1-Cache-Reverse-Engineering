#ifndef LINE_SIZE_H
#define LINE_SIZE_H

#include <stdint.h>

#include "access_pattern.h"

struct line_size_config {
    uint64_t samples;          /* total timed accesses per stride point (>= 1e6 required) */
    uint64_t batch_size;       /* dependent accesses per timed batch */
    uint64_t footprint_bytes;  /* FIXED virtual span (num_nodes*stride) held constant across
                                 * the sweep -- choose just above a known capacity boundary
                                 * (see scripts/run_line_size_full.sh) or the line-size knee
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
 * controlled, known parameter, but a deliberate sub-line offset sweep is a
 * documented manual follow-up if a machine's result looks ambiguous, not a
 * built-in part of this pipeline.
 */
int run_line_size_experiment(const struct line_size_config *cfg);

#endif
