#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "associativity.h"
#include "capacity.h"
#include "line_size.h"

#define DEFAULT_SAMPLES        1000000ULL      /* total timed accesses per point */
#define DEFAULT_BATCH_SIZE     1000ULL         /* dependent accesses per timed batch */
#define DEFAULT_MIN_BYTES      (1ULL << 10)    /* 1 KiB */
#define DEFAULT_MAX_BYTES      (64ULL << 20)   /* 64 MiB */
#define DEFAULT_PTS_PER_OCTAVE 8
#define DEFAULT_WARMUP_PASSES  2
#define DEFAULT_SEED           12345u

#define DEFAULT_FOOTPRINT_BYTES (64ULL << 10) /* 64 KiB fallback; run_line_size_full.sh
                                                  overrides this from a real capacity
                                                  boundary when one is available */
#define DEFAULT_MIN_STRIDE      8ULL           /* == sizeof(struct node) */
#define DEFAULT_MAX_STRIDE      1024ULL
#define DEFAULT_STRIDE_STEP     8ULL
#define DEFAULT_ALIGN_BYTES     4096ULL

#define DEFAULT_CACHE_BYTES     (32ULL << 10)  /* 32 KiB fallback; run_associativity_full.sh
                                                   overrides this from a real capacity
                                                   boundary when one is available */
#define DEFAULT_MIN_WAYS        2ULL
#define DEFAULT_MAX_WAYS        64ULL
#define DEFAULT_WAY_STEP        1ULL

static void usage(const char *prog)
{
    fprintf(stderr,
        "Usage: %s --experiment <name> [options]\n"
        "\n"
        "Experiments:\n"
        "  capacity   sweep working-set size to find cache-level boundaries\n"
        "  line_size  sweep node stride at a fixed footprint to find the cache line size\n"
        "  associativity  sweep same-set node count at a fixed cache-capacity stride to\n"
        "             find the number of ways per set (latency, inclusion: not yet\n"
        "             implemented)\n"
        "\n"
        "Common options:\n"
        "  --samples N            total timed accesses per point (default %llu)\n"
        "  --batch-size N         dependent accesses per timed batch (default %llu)\n"
        "  --seed N               xorshift32 seed for the random cycle (default %u)\n"
        "  --warmup-passes N      untimed full passes before timing (default %d)\n"
        "  --pattern random|sequential  dependent-chain node order (default random);\n"
        "                         sequential is the prefetcher-sanity control\n"
        "\n"
        "capacity options:\n"
        "  --min-bytes N          smallest working-set size in bytes (default %llu)\n"
        "  --max-bytes N          largest working-set size in bytes (default %llu)\n"
        "  --points-per-octave N  size samples per doubling (default %d)\n"
        "\n"
        "line_size options:\n"
        "  --footprint-bytes N    fixed working-set footprint in bytes (default %llu);\n"
        "                         choose just above a known capacity boundary or the\n"
        "                         line-size knee is invisible -- see\n"
        "                         scripts/run_line_size_full.sh\n"
        "  --min-stride N         smallest node stride in bytes (default %llu)\n"
        "  --max-stride N         largest node stride in bytes (default %llu)\n"
        "  --stride-step N        linear stride increment in bytes (default %llu)\n"
        "  --align-bytes N        buffer base alignment, must be a power of two\n"
        "                         (default %llu)\n"
        "\n"
        "associativity options:\n"
        "  --cache-bytes N        stride between probed nodes, in bytes -- MUST be set\n"
        "                         to the target cache level's own capacity (default\n"
        "                         %llu); see scripts/run_associativity_full.sh, which\n"
        "                         derives this from a completed capacity run\n"
        "  --min-ways N           fewest same-set nodes probed (default %llu)\n"
        "  --max-ways N           most same-set nodes probed (default %llu)\n"
        "  --way-step N           linear increment in nodes probed (default %llu)\n"
        "\n"
        "  -h, --help             show this help\n",
        prog,
        (unsigned long long)DEFAULT_SAMPLES,
        (unsigned long long)DEFAULT_BATCH_SIZE,
        DEFAULT_SEED,
        DEFAULT_WARMUP_PASSES,
        (unsigned long long)DEFAULT_MIN_BYTES,
        (unsigned long long)DEFAULT_MAX_BYTES,
        DEFAULT_PTS_PER_OCTAVE,
        (unsigned long long)DEFAULT_FOOTPRINT_BYTES,
        (unsigned long long)DEFAULT_MIN_STRIDE,
        (unsigned long long)DEFAULT_MAX_STRIDE,
        (unsigned long long)DEFAULT_STRIDE_STEP,
        (unsigned long long)DEFAULT_ALIGN_BYTES,
        (unsigned long long)DEFAULT_CACHE_BYTES,
        (unsigned long long)DEFAULT_MIN_WAYS,
        (unsigned long long)DEFAULT_MAX_WAYS,
        (unsigned long long)DEFAULT_WAY_STEP);
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
        .pattern = ACCESS_PATTERN_RANDOM,
    };
    struct line_size_config ls_cfg = {
        .samples = DEFAULT_SAMPLES,
        .batch_size = DEFAULT_BATCH_SIZE,
        .footprint_bytes = DEFAULT_FOOTPRINT_BYTES,
        .min_stride = DEFAULT_MIN_STRIDE,
        .max_stride = DEFAULT_MAX_STRIDE,
        .stride_step = DEFAULT_STRIDE_STEP,
        .align_bytes = DEFAULT_ALIGN_BYTES,
        .warmup_passes = DEFAULT_WARMUP_PASSES,
        .seed = DEFAULT_SEED,
        .pattern = ACCESS_PATTERN_RANDOM,
    };
    struct associativity_config assoc_cfg = {
        .samples = DEFAULT_SAMPLES,
        .batch_size = DEFAULT_BATCH_SIZE,
        .cache_bytes = DEFAULT_CACHE_BYTES,
        .min_ways = DEFAULT_MIN_WAYS,
        .max_ways = DEFAULT_MAX_WAYS,
        .way_step = DEFAULT_WAY_STEP,
        .warmup_passes = DEFAULT_WARMUP_PASSES,
        .seed = DEFAULT_SEED,
        .pattern = ACCESS_PATTERN_RANDOM,
    };

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--experiment") == 0 && i + 1 < argc) {
            experiment = argv[++i];
        } else if (strcmp(argv[i], "--samples") == 0 && i + 1 < argc) {
            if (parse_u64(argv[++i], &cap_cfg.samples) != 0) { usage(argv[0]); return 1; }
            ls_cfg.samples = cap_cfg.samples;
            assoc_cfg.samples = cap_cfg.samples;
        } else if (strcmp(argv[i], "--batch-size") == 0 && i + 1 < argc) {
            if (parse_u64(argv[++i], &cap_cfg.batch_size) != 0) { usage(argv[0]); return 1; }
            ls_cfg.batch_size = cap_cfg.batch_size;
            assoc_cfg.batch_size = cap_cfg.batch_size;
        } else if (strcmp(argv[i], "--min-bytes") == 0 && i + 1 < argc) {
            if (parse_u64(argv[++i], &cap_cfg.min_bytes) != 0) { usage(argv[0]); return 1; }
        } else if (strcmp(argv[i], "--max-bytes") == 0 && i + 1 < argc) {
            if (parse_u64(argv[++i], &cap_cfg.max_bytes) != 0) { usage(argv[0]); return 1; }
        } else if (strcmp(argv[i], "--points-per-octave") == 0 && i + 1 < argc) {
            cap_cfg.points_per_octave = atoi(argv[++i]);
        } else if (strcmp(argv[i], "--footprint-bytes") == 0 && i + 1 < argc) {
            if (parse_u64(argv[++i], &ls_cfg.footprint_bytes) != 0) { usage(argv[0]); return 1; }
        } else if (strcmp(argv[i], "--min-stride") == 0 && i + 1 < argc) {
            if (parse_u64(argv[++i], &ls_cfg.min_stride) != 0) { usage(argv[0]); return 1; }
        } else if (strcmp(argv[i], "--max-stride") == 0 && i + 1 < argc) {
            if (parse_u64(argv[++i], &ls_cfg.max_stride) != 0) { usage(argv[0]); return 1; }
        } else if (strcmp(argv[i], "--stride-step") == 0 && i + 1 < argc) {
            if (parse_u64(argv[++i], &ls_cfg.stride_step) != 0) { usage(argv[0]); return 1; }
        } else if (strcmp(argv[i], "--align-bytes") == 0 && i + 1 < argc) {
            if (parse_u64(argv[++i], &ls_cfg.align_bytes) != 0) { usage(argv[0]); return 1; }
        } else if (strcmp(argv[i], "--cache-bytes") == 0 && i + 1 < argc) {
            if (parse_u64(argv[++i], &assoc_cfg.cache_bytes) != 0) { usage(argv[0]); return 1; }
        } else if (strcmp(argv[i], "--min-ways") == 0 && i + 1 < argc) {
            if (parse_u64(argv[++i], &assoc_cfg.min_ways) != 0) { usage(argv[0]); return 1; }
        } else if (strcmp(argv[i], "--max-ways") == 0 && i + 1 < argc) {
            if (parse_u64(argv[++i], &assoc_cfg.max_ways) != 0) { usage(argv[0]); return 1; }
        } else if (strcmp(argv[i], "--way-step") == 0 && i + 1 < argc) {
            if (parse_u64(argv[++i], &assoc_cfg.way_step) != 0) { usage(argv[0]); return 1; }
        } else if (strcmp(argv[i], "--warmup-passes") == 0 && i + 1 < argc) {
            cap_cfg.warmup_passes = atoi(argv[++i]);
            ls_cfg.warmup_passes = cap_cfg.warmup_passes;
            assoc_cfg.warmup_passes = cap_cfg.warmup_passes;
        } else if (strcmp(argv[i], "--seed") == 0 && i + 1 < argc) {
            uint64_t s;
            if (parse_u64(argv[++i], &s) != 0) { usage(argv[0]); return 1; }
            cap_cfg.seed = (uint32_t)s;
            ls_cfg.seed = cap_cfg.seed;
            assoc_cfg.seed = cap_cfg.seed;
        } else if (strcmp(argv[i], "--pattern") == 0 && i + 1 < argc) {
            const char *p = argv[++i];
            if (strcmp(p, "random") == 0) {
                cap_cfg.pattern = ACCESS_PATTERN_RANDOM;
            } else if (strcmp(p, "sequential") == 0) {
                cap_cfg.pattern = ACCESS_PATTERN_SEQUENTIAL;
            } else {
                fprintf(stderr, "Unknown --pattern '%s' (expected random|sequential)\n", p);
                usage(argv[0]);
                return 1;
            }
            ls_cfg.pattern = cap_cfg.pattern;
            assoc_cfg.pattern = cap_cfg.pattern;
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

    if (ls_cfg.batch_size < 1 || ls_cfg.samples < ls_cfg.batch_size ||
        ls_cfg.warmup_passes < 0 || ls_cfg.min_stride < 1 ||
        ls_cfg.max_stride < ls_cfg.min_stride || ls_cfg.stride_step < 1 ||
        ls_cfg.footprint_bytes < 1 || ls_cfg.align_bytes < 1 ||
        (ls_cfg.align_bytes & (ls_cfg.align_bytes - 1)) != 0) {
        fprintf(stderr, "Invalid line_size parameter values\n");
        return 1;
    }

    if (assoc_cfg.batch_size < 1 || assoc_cfg.samples < assoc_cfg.batch_size ||
        assoc_cfg.warmup_passes < 0 || assoc_cfg.cache_bytes < 1 ||
        (assoc_cfg.cache_bytes & (assoc_cfg.cache_bytes - 1)) != 0 ||
        assoc_cfg.min_ways < 2 || assoc_cfg.max_ways < assoc_cfg.min_ways ||
        assoc_cfg.way_step < 1) {
        fprintf(stderr, "Invalid associativity parameter values\n");
        return 1;
    }

    if (strcmp(experiment, "capacity") == 0) {
        return run_capacity_experiment(&cap_cfg);
    }
    if (strcmp(experiment, "line_size") == 0) {
        return run_line_size_experiment(&ls_cfg);
    }
    if (strcmp(experiment, "associativity") == 0) {
        return run_associativity_experiment(&assoc_cfg);
    }

    fprintf(stderr,
            "Unsupported --experiment '%s' (only 'capacity', 'line_size', and "
            "'associativity' are implemented so far)\n",
            experiment);
    return 1;
}
