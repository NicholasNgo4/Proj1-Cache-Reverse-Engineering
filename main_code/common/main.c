#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "associativity.h"
#include "capacity.h"
#include "latency.h"
#include "line_size.h"

#define DEFAULT_SAMPLES        1000000ULL      /* total timed accesses per point */
#define DEFAULT_BATCH_SIZE     1000ULL         /* dependent accesses per timed batch */
#define DEFAULT_MIN_BYTES      (1ULL << 10)    /* 1 KiB */
#define DEFAULT_MAX_BYTES      (64ULL << 20)   /* 64 MiB */
#define DEFAULT_PTS_PER_OCTAVE 8
#define DEFAULT_WARMUP_PASSES  2
#define DEFAULT_SEED           12345u

#define DEFAULT_FOOTPRINT_BYTES (64ULL << 10) /* 64 KiB fallback; run_line_size.sh
                                                  overrides this from a real capacity
                                                  boundary when one is available */
#define DEFAULT_MIN_STRIDE      8ULL           /* == sizeof(struct node) */
#define DEFAULT_MAX_STRIDE      1024ULL
#define DEFAULT_STRIDE_STEP     8ULL
#define DEFAULT_ALIGN_BYTES     4096ULL
#define DEFAULT_FAMILY_STRIDE   8ULL            /* one candidate stride per invocation --
                                                    see scripts/run_line_size.sh */
#define DEFAULT_OFFSET_BYTES    0ULL            /* node 0's offset past the aligned base --
                                                    see scripts/run_line_size.sh */

#define DEFAULT_CACHE_BYTES     (32ULL << 10)  /* 32 KiB fallback; run_associativity_full.sh
                                                   overrides this from a real capacity
                                                   boundary when one is available */
#define ASSOC_CACHE_BYTES_ALIGN 4096ULL        /* --cache-bytes must be a multiple of this
                                                   (the page size), not a power of two --
                                                   see the validation below and
                                                   associativity.h's docstring: the only
                                                   real requirement is a whole number of
                                                   page-granular "set periods", which a
                                                   non-power-of-two multiple of 4096
                                                   satisfies just as well and is needed to
                                                   test residues that aren't multiples of
                                                   a power-of-two page-indexed structure
                                                   (see CLAUDE.md's residue-scan writeup) */
#define DEFAULT_MIN_WAYS        2ULL
#define DEFAULT_MAX_WAYS        40ULL   /* real L1/L2/LLC associativities on modern
                                            x86/ARM never reach the low 20s, but the
                                            unresolved L2/LLC DTLB/slice-hash confound
                                            (see CLAUDE.md) means extra headroom above
                                            an earlier 32 is worth the small added wall
                                            time -- keeps run_associativity_full.sh's
                                            own MAX_WAYS in sync for direct/manual
                                            cache_bench invocations that skip the
                                            wrapper's explicit --max-ways */
#define DEFAULT_WAY_STEP        1ULL

#define DEFAULT_LOAD_MODE       LOAD_MODE_DEPENDENT
#define DEFAULT_TARGET_BYTES    DEFAULT_CACHE_BYTES /* 32 KiB fallback; run_miss_latency_full.sh
                                                        overrides this from a real confirmed
                                                        SOURCE-level capacity boundary */
#define DEFAULT_EVICT_BYTES     DEFAULT_MAX_BYTES   /* 64 MiB fallback; run_miss_latency_full.sh
                                                        overrides this from a real confirmed
                                                        NEXT-level capacity boundary -- must
                                                        exceed the source level's real capacity
                                                        while staying inside the next level's,
                                                        see latency.h's docstring */

static void usage(const char *prog)
{
    fprintf(stderr,
        "Usage: %s --experiment <name> [options]\n"
        "\n"
        "Experiments:\n"
        "  capacity          sweep working-set size to find cache-level boundaries\n"
        "  line_size         sweep node stride at a fixed footprint to find the cache\n"
        "                    line size (single curve, ramp-saturation method)\n"
        "  line_size_family  sweep working-set footprint at one FIXED candidate stride;\n"
        "                    run once per candidate stride and overlay the resulting\n"
        "                    curves to get the family-of-curves line-size evidence (see\n"
        "                    scripts/run_line_size.sh)\n"
        "  associativity     sweep same-set node count at a fixed cache-capacity stride\n"
        "                    to find the number of ways per set\n"
        "  hit_latency       measure per-access latency at ONE fixed, already-confirmed\n"
        "                    working-set footprint, dependent vs. independent load mode\n"
        "  miss_latency      force a target line out of a source cache level via a\n"
        "                    sized eviction-set walk, then time exactly one dependent\n"
        "                    reload (the miss/next-level-latency measurement; inclusion:\n"
        "                    not yet implemented)\n"
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
        "                         scripts/run_line_size.sh\n"
        "  --min-stride N         smallest node stride in bytes (default %llu)\n"
        "  --max-stride N         largest node stride in bytes (default %llu)\n"
        "  --stride-step N        linear stride increment in bytes (default %llu)\n"
        "  --align-bytes N        buffer base alignment, must be a power of two\n"
        "                         (default %llu)\n"
        "\n"
        "line_size_family options:\n"
        "  --stride N             FIXED byte stride between nodes for this run -- one\n"
        "                         candidate line-size guess (default %llu); sweeps\n"
        "                         --min-bytes..--max-bytes footprint at this stride\n"
        "                         (also honors --min-bytes/--max-bytes/--points-per-\n"
        "                         octave/--align-bytes above)\n"
        "  --offset-bytes N       extra byte offset for node 0 past the aligned base\n"
        "                         (default %llu); re-run the same --stride at several\n"
        "                         offsets to check a detected transition survives\n"
        "                         different alignments -- see\n"
        "                         scripts/run_line_size.sh\n"
        "\n"
        "associativity options:\n"
        "  --cache-bytes N        stride between probed nodes, in bytes -- MUST be set\n"
        "                         to the target cache level's own capacity (default\n"
        "                         %llu); must be a multiple of 4096 (the page size),\n"
        "                         NOT required to be a power of two -- see\n"
        "                         scripts/run_associativity_full.sh, which derives this\n"
        "                         from a completed capacity run\n"
        "  --min-ways N           fewest same-set nodes probed (default %llu)\n"
        "  --max-ways N           most same-set nodes probed (default %llu)\n"
        "  --way-step N           linear increment in nodes probed (default %llu)\n"
        "  --huge-pages           allocate the probe buffer 2 MiB-aligned and\n"
        "                         madvise(MADV_HUGEPAGE); if the buffer fits within one\n"
        "                         2 MiB page, this collapses every probed node onto a\n"
        "                         single TLB entry regardless of num_ways -- a knee that\n"
        "                         survives unchanged cannot be a TLB/page artifact.\n"
        "                         Actual backing achieved is reported to stderr from\n"
        "                         /proc/self/smaps, not assumed from madvise succeeding.\n"
        "\n"
        "hit_latency options:\n"
        "  --footprint-bytes N    fixed working-set footprint in bytes (default %llu);\n"
        "                         MUST already be confirmed to sit inside one cache\n"
        "                         level -- no auto-detection, see\n"
        "                         scripts/run_hit_latency_full.sh\n"
        "  --load-mode dependent|independent  which batched timer to run (default\n"
        "                         dependent); independent is a REQUIRED diagnostic\n"
        "                         control only, never the reported latency number\n"
        "\n"
        "miss_latency options:\n"
        "  --target-bytes N       footprint placing the target line inside the SOURCE\n"
        "                         level (default %llu)\n"
        "  --evict-bytes N        footprint of the eviction-set walk -- must exceed the\n"
        "                         source level's real capacity while staying inside the\n"
        "                         next level's (default %llu); --pattern controls this\n"
        "                         walk's traversal order only\n"
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
        (unsigned long long)DEFAULT_FAMILY_STRIDE,
        (unsigned long long)DEFAULT_OFFSET_BYTES,
        (unsigned long long)DEFAULT_CACHE_BYTES,
        (unsigned long long)DEFAULT_MIN_WAYS,
        (unsigned long long)DEFAULT_MAX_WAYS,
        (unsigned long long)DEFAULT_WAY_STEP,
        (unsigned long long)DEFAULT_FOOTPRINT_BYTES,
        (unsigned long long)DEFAULT_TARGET_BYTES,
        (unsigned long long)DEFAULT_EVICT_BYTES);
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
    struct line_size_family_config fam_cfg = {
        .samples = DEFAULT_SAMPLES,
        .batch_size = DEFAULT_BATCH_SIZE,
        .stride = DEFAULT_FAMILY_STRIDE,
        .min_bytes = DEFAULT_MIN_BYTES,
        .max_bytes = DEFAULT_MAX_BYTES,
        .points_per_octave = DEFAULT_PTS_PER_OCTAVE,
        .align_bytes = DEFAULT_ALIGN_BYTES,
        .offset_bytes = DEFAULT_OFFSET_BYTES,
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
        .huge_pages = 0,
    };
    struct hit_latency_config hl_cfg = {
        .samples = DEFAULT_SAMPLES,
        .batch_size = DEFAULT_BATCH_SIZE,
        .footprint_bytes = DEFAULT_FOOTPRINT_BYTES,
        .warmup_passes = DEFAULT_WARMUP_PASSES,
        .seed = DEFAULT_SEED,
        .pattern = ACCESS_PATTERN_RANDOM,
        .load_mode = DEFAULT_LOAD_MODE,
    };
    struct miss_latency_config ml_cfg = {
        .samples = DEFAULT_SAMPLES,
        .target_bytes = DEFAULT_TARGET_BYTES,
        .evict_bytes = DEFAULT_EVICT_BYTES,
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
            fam_cfg.samples = cap_cfg.samples;
            assoc_cfg.samples = cap_cfg.samples;
            hl_cfg.samples = cap_cfg.samples;
            ml_cfg.samples = cap_cfg.samples;
        } else if (strcmp(argv[i], "--batch-size") == 0 && i + 1 < argc) {
            if (parse_u64(argv[++i], &cap_cfg.batch_size) != 0) { usage(argv[0]); return 1; }
            ls_cfg.batch_size = cap_cfg.batch_size;
            fam_cfg.batch_size = cap_cfg.batch_size;
            assoc_cfg.batch_size = cap_cfg.batch_size;
            hl_cfg.batch_size = cap_cfg.batch_size;
        } else if (strcmp(argv[i], "--min-bytes") == 0 && i + 1 < argc) {
            if (parse_u64(argv[++i], &cap_cfg.min_bytes) != 0) { usage(argv[0]); return 1; }
            fam_cfg.min_bytes = cap_cfg.min_bytes;
        } else if (strcmp(argv[i], "--max-bytes") == 0 && i + 1 < argc) {
            if (parse_u64(argv[++i], &cap_cfg.max_bytes) != 0) { usage(argv[0]); return 1; }
            fam_cfg.max_bytes = cap_cfg.max_bytes;
        } else if (strcmp(argv[i], "--points-per-octave") == 0 && i + 1 < argc) {
            cap_cfg.points_per_octave = atoi(argv[++i]);
            fam_cfg.points_per_octave = cap_cfg.points_per_octave;
        } else if (strcmp(argv[i], "--footprint-bytes") == 0 && i + 1 < argc) {
            if (parse_u64(argv[++i], &ls_cfg.footprint_bytes) != 0) { usage(argv[0]); return 1; }
            hl_cfg.footprint_bytes = ls_cfg.footprint_bytes;
        } else if (strcmp(argv[i], "--min-stride") == 0 && i + 1 < argc) {
            if (parse_u64(argv[++i], &ls_cfg.min_stride) != 0) { usage(argv[0]); return 1; }
        } else if (strcmp(argv[i], "--max-stride") == 0 && i + 1 < argc) {
            if (parse_u64(argv[++i], &ls_cfg.max_stride) != 0) { usage(argv[0]); return 1; }
        } else if (strcmp(argv[i], "--stride-step") == 0 && i + 1 < argc) {
            if (parse_u64(argv[++i], &ls_cfg.stride_step) != 0) { usage(argv[0]); return 1; }
        } else if (strcmp(argv[i], "--stride") == 0 && i + 1 < argc) {
            if (parse_u64(argv[++i], &fam_cfg.stride) != 0) { usage(argv[0]); return 1; }
        } else if (strcmp(argv[i], "--align-bytes") == 0 && i + 1 < argc) {
            if (parse_u64(argv[++i], &ls_cfg.align_bytes) != 0) { usage(argv[0]); return 1; }
            fam_cfg.align_bytes = ls_cfg.align_bytes;
        } else if (strcmp(argv[i], "--offset-bytes") == 0 && i + 1 < argc) {
            if (parse_u64(argv[++i], &fam_cfg.offset_bytes) != 0) { usage(argv[0]); return 1; }
        } else if (strcmp(argv[i], "--cache-bytes") == 0 && i + 1 < argc) {
            if (parse_u64(argv[++i], &assoc_cfg.cache_bytes) != 0) { usage(argv[0]); return 1; }
        } else if (strcmp(argv[i], "--min-ways") == 0 && i + 1 < argc) {
            if (parse_u64(argv[++i], &assoc_cfg.min_ways) != 0) { usage(argv[0]); return 1; }
        } else if (strcmp(argv[i], "--max-ways") == 0 && i + 1 < argc) {
            if (parse_u64(argv[++i], &assoc_cfg.max_ways) != 0) { usage(argv[0]); return 1; }
        } else if (strcmp(argv[i], "--way-step") == 0 && i + 1 < argc) {
            if (parse_u64(argv[++i], &assoc_cfg.way_step) != 0) { usage(argv[0]); return 1; }
        } else if (strcmp(argv[i], "--huge-pages") == 0) {
            assoc_cfg.huge_pages = 1;
        } else if (strcmp(argv[i], "--load-mode") == 0 && i + 1 < argc) {
            const char *m = argv[++i];
            if (strcmp(m, "dependent") == 0) {
                hl_cfg.load_mode = LOAD_MODE_DEPENDENT;
            } else if (strcmp(m, "independent") == 0) {
                hl_cfg.load_mode = LOAD_MODE_INDEPENDENT;
            } else {
                fprintf(stderr, "Unknown --load-mode '%s' (expected dependent|independent)\n", m);
                usage(argv[0]);
                return 1;
            }
        } else if (strcmp(argv[i], "--target-bytes") == 0 && i + 1 < argc) {
            if (parse_u64(argv[++i], &ml_cfg.target_bytes) != 0) { usage(argv[0]); return 1; }
        } else if (strcmp(argv[i], "--evict-bytes") == 0 && i + 1 < argc) {
            if (parse_u64(argv[++i], &ml_cfg.evict_bytes) != 0) { usage(argv[0]); return 1; }
        } else if (strcmp(argv[i], "--warmup-passes") == 0 && i + 1 < argc) {
            cap_cfg.warmup_passes = atoi(argv[++i]);
            ls_cfg.warmup_passes = cap_cfg.warmup_passes;
            fam_cfg.warmup_passes = cap_cfg.warmup_passes;
            assoc_cfg.warmup_passes = cap_cfg.warmup_passes;
            hl_cfg.warmup_passes = cap_cfg.warmup_passes;
            ml_cfg.warmup_passes = cap_cfg.warmup_passes;
        } else if (strcmp(argv[i], "--seed") == 0 && i + 1 < argc) {
            uint64_t s;
            if (parse_u64(argv[++i], &s) != 0) { usage(argv[0]); return 1; }
            cap_cfg.seed = (uint32_t)s;
            ls_cfg.seed = cap_cfg.seed;
            fam_cfg.seed = cap_cfg.seed;
            assoc_cfg.seed = cap_cfg.seed;
            hl_cfg.seed = cap_cfg.seed;
            ml_cfg.seed = cap_cfg.seed;
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
            fam_cfg.pattern = cap_cfg.pattern;
            assoc_cfg.pattern = cap_cfg.pattern;
            hl_cfg.pattern = cap_cfg.pattern;
            ml_cfg.pattern = cap_cfg.pattern;
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

    if (fam_cfg.batch_size < 1 || fam_cfg.samples < fam_cfg.batch_size ||
        fam_cfg.points_per_octave < 1 || fam_cfg.warmup_passes < 0 ||
        fam_cfg.min_bytes < 1 || fam_cfg.max_bytes < fam_cfg.min_bytes ||
        fam_cfg.stride < 1 || fam_cfg.align_bytes < 1 ||
        (fam_cfg.align_bytes & (fam_cfg.align_bytes - 1)) != 0) {
        fprintf(stderr, "Invalid line_size_family parameter values\n");
        return 1;
    }

    if (assoc_cfg.batch_size < 1 || assoc_cfg.samples < assoc_cfg.batch_size ||
        assoc_cfg.warmup_passes < 0 || assoc_cfg.cache_bytes < ASSOC_CACHE_BYTES_ALIGN ||
        (assoc_cfg.cache_bytes % ASSOC_CACHE_BYTES_ALIGN) != 0 ||
        assoc_cfg.min_ways < 2 || assoc_cfg.max_ways < assoc_cfg.min_ways ||
        assoc_cfg.way_step < 1) {
        fprintf(stderr, "Invalid associativity parameter values "
                        "(--cache-bytes must be a multiple of %llu)\n",
                (unsigned long long)ASSOC_CACHE_BYTES_ALIGN);
        return 1;
    }

    if (hl_cfg.batch_size < 1 || hl_cfg.samples < hl_cfg.batch_size ||
        hl_cfg.warmup_passes < 0 || hl_cfg.footprint_bytes < 1) {
        fprintf(stderr, "Invalid hit_latency parameter values\n");
        return 1;
    }

    if (ml_cfg.samples < 1 || ml_cfg.warmup_passes < 0 ||
        ml_cfg.target_bytes < 1 || ml_cfg.evict_bytes < 1) {
        fprintf(stderr, "Invalid miss_latency parameter values\n");
        return 1;
    }

    if (strcmp(experiment, "capacity") == 0) {
        return run_capacity_experiment(&cap_cfg);
    }
    if (strcmp(experiment, "line_size") == 0) {
        return run_line_size_experiment(&ls_cfg);
    }
    if (strcmp(experiment, "line_size_family") == 0) {
        return run_line_size_family_experiment(&fam_cfg);
    }
    if (strcmp(experiment, "associativity") == 0) {
        return run_associativity_experiment(&assoc_cfg);
    }
    if (strcmp(experiment, "hit_latency") == 0) {
        return run_hit_latency_experiment(&hl_cfg);
    }
    if (strcmp(experiment, "miss_latency") == 0) {
        return run_miss_latency_experiment(&ml_cfg);
    }

    fprintf(stderr,
            "Unsupported --experiment '%s' (only 'capacity', 'line_size', "
            "'line_size_family', 'associativity', 'hit_latency', and "
            "'miss_latency' are implemented so far)\n",
            experiment);
    return 1;
}
