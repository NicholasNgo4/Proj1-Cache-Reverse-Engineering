#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "capacity.h"

#define DEFAULT_SAMPLES        1000000ULL      /* total timed accesses per point */
#define DEFAULT_BATCH_SIZE     1000ULL         /* dependent accesses per timed batch */
#define DEFAULT_MIN_BYTES      (1ULL << 10)    /* 1 KiB */
#define DEFAULT_MAX_BYTES      (64ULL << 20)   /* 64 MiB */
#define DEFAULT_PTS_PER_OCTAVE 8
#define DEFAULT_WARMUP_PASSES  2
#define DEFAULT_SEED           12345u

static void usage(const char *prog)
{
    fprintf(stderr,
        "Usage: %s --experiment <name> [options]\n"
        "\n"
        "Experiments:\n"
        "  capacity   sweep working-set size to find cache-level boundaries\n"
        "             (line_size, associativity, latency, inclusion: not yet implemented)\n"
        "\n"
        "Common options:\n"
        "  --samples N            total timed accesses per point (default %llu)\n"
        "  --batch-size N         dependent accesses per timed batch (default %llu)\n"
        "  --seed N               xorshift32 seed for the random cycle (default %u)\n"
        "\n"
        "capacity options:\n"
        "  --min-bytes N          smallest working-set size in bytes (default %llu)\n"
        "  --max-bytes N          largest working-set size in bytes (default %llu)\n"
        "  --points-per-octave N  size samples per doubling (default %d)\n"
        "  --warmup-passes N      untimed full passes before timing (default %d)\n"
        "  -h, --help             show this help\n",
        prog,
        (unsigned long long)DEFAULT_SAMPLES,
        (unsigned long long)DEFAULT_BATCH_SIZE,
        DEFAULT_SEED,
        (unsigned long long)DEFAULT_MIN_BYTES,
        (unsigned long long)DEFAULT_MAX_BYTES,
        DEFAULT_PTS_PER_OCTAVE,
        DEFAULT_WARMUP_PASSES);
}

static int parse_u64(const char *s, uint64_t *out)
{
    char *end;
    unsigned long long v = strtoull(s, &end, 10);
    if (end == s || *end != '\0') {
        return -1;
    }
    *out = (uint64_t)v;
    return 0;
}

int main(int argc, char **argv)
{
    const char *experiment = "capacity";
    struct capacity_config cap_cfg = {
        .samples = DEFAULT_SAMPLES,
        .batch_size = DEFAULT_BATCH_SIZE,
        .min_bytes = DEFAULT_MIN_BYTES,
        .max_bytes = DEFAULT_MAX_BYTES,
        .points_per_octave = DEFAULT_PTS_PER_OCTAVE,
        .warmup_passes = DEFAULT_WARMUP_PASSES,
        .seed = DEFAULT_SEED,
    };

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--experiment") == 0 && i + 1 < argc) {
            experiment = argv[++i];
        } else if (strcmp(argv[i], "--samples") == 0 && i + 1 < argc) {
            if (parse_u64(argv[++i], &cap_cfg.samples) != 0) { usage(argv[0]); return 1; }
        } else if (strcmp(argv[i], "--batch-size") == 0 && i + 1 < argc) {
            if (parse_u64(argv[++i], &cap_cfg.batch_size) != 0) { usage(argv[0]); return 1; }
        } else if (strcmp(argv[i], "--min-bytes") == 0 && i + 1 < argc) {
            if (parse_u64(argv[++i], &cap_cfg.min_bytes) != 0) { usage(argv[0]); return 1; }
        } else if (strcmp(argv[i], "--max-bytes") == 0 && i + 1 < argc) {
            if (parse_u64(argv[++i], &cap_cfg.max_bytes) != 0) { usage(argv[0]); return 1; }
        } else if (strcmp(argv[i], "--points-per-octave") == 0 && i + 1 < argc) {
            cap_cfg.points_per_octave = atoi(argv[++i]);
        } else if (strcmp(argv[i], "--warmup-passes") == 0 && i + 1 < argc) {
            cap_cfg.warmup_passes = atoi(argv[++i]);
        } else if (strcmp(argv[i], "--seed") == 0 && i + 1 < argc) {
            uint64_t s;
            if (parse_u64(argv[++i], &s) != 0) { usage(argv[0]); return 1; }
            cap_cfg.seed = (uint32_t)s;
        } else if (strcmp(argv[i], "-h") == 0 || strcmp(argv[i], "--help") == 0) {
            usage(argv[0]);
            return 0;
        } else {
            fprintf(stderr, "Unknown argument: %s\n", argv[i]);
            usage(argv[0]);
            return 1;
        }
    }

    if (cap_cfg.batch_size < 1 || cap_cfg.samples < cap_cfg.batch_size ||
        cap_cfg.points_per_octave < 1 || cap_cfg.warmup_passes < 0 ||
        cap_cfg.min_bytes < 1 || cap_cfg.max_bytes < cap_cfg.min_bytes) {
        fprintf(stderr, "Invalid parameter values\n");
        return 1;
    }

    if (strcmp(experiment, "capacity") == 0) {
        return run_capacity_experiment(&cap_cfg);
    }

    fprintf(stderr, "Unsupported --experiment '%s' (only 'capacity' is implemented so far)\n",
            experiment);
    return 1;
}
