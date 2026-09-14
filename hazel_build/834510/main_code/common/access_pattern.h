#ifndef ACCESS_PATTERN_H
#define ACCESS_PATTERN_H

/* Shared by every experiment that builds a dependent pointer-chase cycle
 * (capacity, line_size, ...): randomized order is the primary signal,
 * sequential/in-array order is the prefetcher-sanity control. */
enum access_pattern {
    ACCESS_PATTERN_RANDOM = 0,     /* randomized dependent cycle (primary) */
    ACCESS_PATTERN_SEQUENTIAL = 1, /* in-array-order dependent cycle (prefetcher control) */
};

#endif
