#include <inttypes.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#include "software_hit_rate.h"
#include "../common/pointer_chase.h"
#include "../common/random.h"
#include "../common/timer.h"

static volatile struct node *hit_rate_sink;

/* Times `samples` single-shot dependent loads by repeatedly advancing the
 * SAME chase cycle (wrapping around after `n` steps, which is fine -- the
 * cycle's residency class doesn't change by being walked more than once).
 * Same primitive latency.c's run_miss_latency_experiment() uses per trial. */
static void time_single_shot_chain(struct node *nodes, uint64_t samples, double *out_ticks)
{
    struct node *p = nodes;
    for (uint64_t i = 0; i < samples; i++) {
        uint64_t t0 = timer_start();
        p = p->next;
        uint64_t t1 = timer_stop();
        out_ticks[i] = (double)(t1 - t0);
    }
    hit_rate_sink = p;
}

struct labeled_tick {
    double val;
    int label; /* 1 = resident (hit) calibration class, 0 = nonresident (miss) */
};

static int cmp_labeled(const void *a, const void *b)
{
    double da = ((const struct labeled_tick *)a)->val;
    double db = ((const struct labeled_tick *)b)->val;
    if (da < db) return -1;
    if (da > db) return 1;
    return 0;
}

static int cmp_double(const void *a, const void *b)
{
    double da = *(const double *)a;
    double db = *(const double *)b;
    if (da < db) return -1;
    if (da > db) return 1;
    return 0;
}

/* ROC sweep over the merged, sorted calibration samples, picking the cut
 * point tau that maximizes Youden's J = TPR(tau) - FPR(tau). Ties at the
 * same tick value are resolved together (all same-value entries are folded
 * in before TPR/FPR are evaluated at that value), so a value shared by both
 * classes is never split into two different candidate thresholds. Returns
 * tau ("hit" iff ticks <= tau) and, via out params, sensitivity/specificity
 * AT that tau. */
static double select_threshold(const double *resident, uint64_t n_resident,
                                const double *nonresident, uint64_t n_nonresident,
                                double *out_se, double *out_sp)
{
    uint64_t n = n_resident + n_nonresident;
    struct labeled_tick *combined = malloc(n * sizeof(*combined));
    if (combined == NULL) {
        fprintf(stderr, "allocation failed for %" PRIu64 " combined calibration entries\n", n);
        exit(1);
    }
    for (uint64_t i = 0; i < n_resident; i++) {
        combined[i].val = resident[i];
        combined[i].label = 1;
    }
    for (uint64_t i = 0; i < n_nonresident; i++) {
        combined[n_resident + i].val = nonresident[i];
        combined[n_resident + i].label = 0;
    }
    qsort(combined, n, sizeof(*combined), cmp_labeled);

    double best_j = -2.0, best_tau = combined[0].val, best_se = 0.0, best_sp = 0.0;
    uint64_t resident_seen = 0, nonresident_seen = 0;
    uint64_t i = 0;
    while (i < n) {
        double v = combined[i].val;
        uint64_t j = i;
        while (j < n && combined[j].val == v) {
            if (combined[j].label) {
                resident_seen++;
            } else {
                nonresident_seen++;
            }
            j++;
        }
        double tpr = (double)resident_seen / (double)n_resident;
        double fpr = (double)nonresident_seen / (double)n_nonresident;
        double j_stat = tpr - fpr;
        if (j_stat > best_j) {
            best_j = j_stat;
            best_tau = v;
            best_se = tpr;
            best_sp = 1.0 - fpr;
        }
        i = j;
    }

    free(combined);
    *out_se = best_se;
    *out_sp = best_sp;
    return best_tau;
}

/* Rogan-Gladen prevalence-correction estimator: debiases a binary
 * classifier's naive positive rate (p_obs) into a calibrated rate estimate
 * given the classifier's own sensitivity/specificity. Clamped to [0, 1];
 * guarded against a degenerate (no-better-than-random) classifier. */
static double rogan_gladen(double p_obs, double se, double sp)
{
    double denom = se + sp - 1.0;
    if (denom < 1e-9) {
        denom = 1e-9;
    }
    double h = (p_obs + sp - 1.0) / denom;
    if (h < 0.0) h = 0.0;
    if (h > 1.0) h = 1.0;
    return h;
}

/* Nonparametric bootstrap over all three empirical distributions
 * (resident/nonresident calibration classes + the test stream): each
 * replicate resamples all three with replacement, re-derives tau/Se/Sp from
 * the resampled calibration data, reclassifies the resampled test stream at
 * that replicate's own tau, and recomputes Hhat -- so the reported interval
 * captures uncertainty from threshold selection as well as from the test
 * measurement itself, not just naive binomial sampling error on p_obs. */
static void bootstrap_ci(const double *resident, uint64_t n_resident,
                          const double *nonresident, uint64_t n_nonresident,
                          const double *test, uint64_t n_test,
                          uint64_t reps, uint32_t seed,
                          double *out_mean, double *out_std, double *out_lo, double *out_hi)
{
    double *boot_h = malloc(reps * sizeof(double));
    double *rs_resident = malloc(n_resident * sizeof(double));
    double *rs_nonresident = malloc(n_nonresident * sizeof(double));
    double *rs_test = malloc(n_test * sizeof(double));
    if (boot_h == NULL || rs_resident == NULL || rs_nonresident == NULL || rs_test == NULL) {
        fprintf(stderr, "allocation failed for bootstrap scratch arrays\n");
        exit(1);
    }

    uint32_t state = seed ? seed : 1u;
    for (uint64_t b = 0; b < reps; b++) {
        for (uint64_t i = 0; i < n_resident; i++) {
            rs_resident[i] = resident[xorshift32(&state) % (uint32_t)n_resident];
        }
        for (uint64_t i = 0; i < n_nonresident; i++) {
            rs_nonresident[i] = nonresident[xorshift32(&state) % (uint32_t)n_nonresident];
        }
        for (uint64_t i = 0; i < n_test; i++) {
            rs_test[i] = test[xorshift32(&state) % (uint32_t)n_test];
        }

        double se_b, sp_b;
        double tau_b = select_threshold(rs_resident, n_resident, rs_nonresident, n_nonresident,
                                         &se_b, &sp_b);
        uint64_t hits = 0;
        for (uint64_t i = 0; i < n_test; i++) {
            if (rs_test[i] <= tau_b) {
                hits++;
            }
        }
        double p_obs_b = (double)hits / (double)n_test;
        boot_h[b] = rogan_gladen(p_obs_b, se_b, sp_b);
    }

    double sum = 0.0;
    for (uint64_t b = 0; b < reps; b++) {
        sum += boot_h[b];
    }
    double mean = sum / (double)reps;
    double sq = 0.0;
    for (uint64_t b = 0; b < reps; b++) {
        double d = boot_h[b] - mean;
        sq += d * d;
    }
    double std = sqrt(sq / (double)(reps > 1 ? reps - 1 : 1));

    qsort(boot_h, reps, sizeof(double), cmp_double);
    uint64_t lo_idx = (uint64_t)(0.025 * (double)(reps - 1));
    uint64_t hi_idx = (uint64_t)(0.975 * (double)(reps - 1));

    *out_mean = mean;
    *out_std = std;
    *out_lo = boot_h[lo_idx];
    *out_hi = boot_h[hi_idx];

    free(boot_h);
    free(rs_resident);
    free(rs_nonresident);
    free(rs_test);
}

/* Same idea as bootstrap_ci() above but for PMU VALIDATION MODE
 * (cfg->has_fixed_calibration): tau/Se/Sp are already fixed constants (from
 * a separate, out-of-band calibration run -- see software_hit_rate.h), so
 * there is no calibration data to resample here. Only the test stream's own
 * sampling uncertainty is captured; this is a narrower, CONDITIONAL
 * interval (conditioned on the given tau/Se/Sp being exact) than the normal
 * mode's bootstrap, which also propagates calibration uncertainty -- a
 * documented tradeoff of the validation harness, not of the estimator. */
static void bootstrap_ci_fixed(const double *test, uint64_t n_test,
                                double tau, double se, double sp,
                                uint64_t reps, uint32_t seed,
                                double *out_mean, double *out_std, double *out_lo, double *out_hi)
{
    double *boot_h = malloc(reps * sizeof(double));
    double *rs_test = malloc(n_test * sizeof(double));
    if (boot_h == NULL || rs_test == NULL) {
        fprintf(stderr, "allocation failed for fixed-calibration bootstrap scratch arrays\n");
        exit(1);
    }

    uint32_t state = seed ? seed : 1u;
    for (uint64_t b = 0; b < reps; b++) {
        uint64_t hits = 0;
        for (uint64_t i = 0; i < n_test; i++) {
            rs_test[i] = test[xorshift32(&state) % (uint32_t)n_test];
            if (rs_test[i] <= tau) {
                hits++;
            }
        }
        double p_obs_b = (double)hits / (double)n_test;
        boot_h[b] = rogan_gladen(p_obs_b, se, sp);
    }

    double sum = 0.0;
    for (uint64_t b = 0; b < reps; b++) {
        sum += boot_h[b];
    }
    double mean = sum / (double)reps;
    double sq = 0.0;
    for (uint64_t b = 0; b < reps; b++) {
        double d = boot_h[b] - mean;
        sq += d * d;
    }
    double std = sqrt(sq / (double)(reps > 1 ? reps - 1 : 1));

    qsort(boot_h, reps, sizeof(double), cmp_double);
    uint64_t lo_idx = (uint64_t)(0.025 * (double)(reps - 1));
    uint64_t hi_idx = (uint64_t)(0.975 * (double)(reps - 1));

    *out_mean = mean;
    *out_std = std;
    *out_lo = boot_h[lo_idx];
    *out_hi = boot_h[hi_idx];

    free(boot_h);
    free(rs_test);
}

int run_hit_rate_experiment(const struct hit_rate_config *cfg)
{
    size_t test_nodes = (size_t)(cfg->test_bytes / sizeof(struct node));
    if (test_nodes < 2) test_nodes = 2;

    const char *pattern_name =
        (cfg->pattern == ACCESS_PATTERN_SEQUENTIAL) ? "sequential" : "random";

    double *test_ticks = malloc(cfg->test_samples * sizeof(double));
    if (test_ticks == NULL) {
        fprintf(stderr, "allocation failed for test_ticks (test_samples=%" PRIu64 ")\n",
                cfg->test_samples);
        return 1;
    }

    double *resident_ticks = NULL;
    double *nonresident_ticks = NULL;
    uint64_t calib_samples_used = 0;
    double se, sp, tau;

    if (cfg->has_fixed_calibration) {
        /* PMU validation mode: skip calibration entirely -- see
         * software_hit_rate.h's "PMU VALIDATION MODE" note. */
        tau = cfg->fixed_tau;
        se = cfg->fixed_sensitivity;
        sp = cfg->fixed_specificity;
    } else {
        /* STAGE 1 -- calibration, fully isolated from the test workload: the
         * resident/nonresident buffers are allocated, built, warmed, timed,
         * AND FREED before the test buffer is ever allocated. This matters:
         * an earlier version of this function built/warmed all three
         * buffers together, and a large --test-bytes buffer's own warmup
         * pass measurably disturbed the immediately-following nonresident
         * calibration timing (TLB/page-fault/allocator side effects),
         * shifting tau and inflating Hhat on an otherwise-DRAM-scale test
         * workload -- confirmed by comparing runs that differed only in
         * test_bytes. Isolating calibration like this also matches the
         * Competition's own requirement that the estimator self-calibrate
         * independently of whatever workload it is later pointed at. */
        size_t resident_nodes = (size_t)(cfg->resident_bytes / sizeof(struct node));
        if (resident_nodes < 2) resident_nodes = 2;
        size_t nonresident_nodes = (size_t)(cfg->nonresident_bytes / sizeof(struct node));
        if (nonresident_nodes < 2) nonresident_nodes = 2;

        resident_ticks = malloc(cfg->calib_samples * sizeof(double));
        nonresident_ticks = malloc(cfg->calib_samples * sizeof(double));
        if (resident_ticks == NULL || nonresident_ticks == NULL) {
            fprintf(stderr, "allocation failed for calibration tick arrays (calib_samples=%"
                             PRIu64 ")\n", cfg->calib_samples);
            free(resident_ticks);
            free(nonresident_ticks);
            free(test_ticks);
            return 1;
        }
        calib_samples_used = cfg->calib_samples;

        struct node *resident = malloc(resident_nodes * sizeof(struct node));
        struct node *nonresident = malloc(nonresident_nodes * sizeof(struct node));
        if (resident == NULL || nonresident == NULL) {
            fprintf(stderr, "allocation failed (resident_nodes=%zu nonresident_nodes=%zu)\n",
                    resident_nodes, nonresident_nodes);
            free(resident);
            free(nonresident);
            free(resident_ticks);
            free(nonresident_ticks);
            free(test_ticks);
            return 1;
        }

        if (cfg->pattern == ACCESS_PATTERN_SEQUENTIAL) {
            make_sequential_cycle(resident, resident_nodes);
            make_sequential_cycle(nonresident, nonresident_nodes);
        } else {
            make_random_cycle(resident, resident_nodes, cfg->seed);
            make_random_cycle(nonresident, nonresident_nodes, cfg->seed + 1u);
        }

        /* Untimed: fault in pages and settle steady-state residency before
         * any timed access, same discipline as every other experiment here.
         * For the nonresident cycle this does NOT establish cache residency
         * (it is far larger than the cache hierarchy by construction) -- it
         * only pays the one-time page-fault cost up front so it doesn't
         * contaminate the timed samples. */
        for (int w = 0; w < cfg->warmup_passes; w++) {
            chase(resident, (uint64_t)resident_nodes);
            chase(nonresident, (uint64_t)nonresident_nodes);
        }

        time_single_shot_chain(resident, cfg->calib_samples, resident_ticks);
        time_single_shot_chain(nonresident, cfg->calib_samples, nonresident_ticks);

        free(resident);
        free(nonresident);

        tau = select_threshold(resident_ticks, cfg->calib_samples,
                                nonresident_ticks, cfg->calib_samples, &se, &sp);
    }

    /* STAGE 2 -- the test workload, measured only now that tau is already
     * frozen (either from calibration above, or from the caller in PMU
     * validation mode). */
    struct node *test = malloc(test_nodes * sizeof(struct node));
    if (test == NULL) {
        fprintf(stderr, "allocation failed for test buffer (test_nodes=%zu)\n", test_nodes);
        free(resident_ticks);
        free(nonresident_ticks);
        free(test_ticks);
        return 1;
    }

    if (cfg->pattern == ACCESS_PATTERN_SEQUENTIAL) {
        make_sequential_cycle(test, test_nodes);
    } else {
        make_random_cycle(test, test_nodes, cfg->seed + 2u);
    }
    for (int w = 0; w < cfg->warmup_passes; w++) {
        chase(test, (uint64_t)test_nodes);
    }
    time_single_shot_chain(test, cfg->test_samples, test_ticks);
    free(test);

    uint64_t hits = 0;
    for (uint64_t i = 0; i < cfg->test_samples; i++) {
        if (test_ticks[i] <= tau) {
            hits++;
        }
    }
    double p_obs = (double)hits / (double)cfg->test_samples;
    double hhat = rogan_gladen(p_obs, se, sp);

    double boot_mean, boot_std, ci_lo, ci_hi;
    if (cfg->has_fixed_calibration) {
        bootstrap_ci_fixed(test_ticks, cfg->test_samples, tau, se, sp, cfg->bootstrap_reps,
                            cfg->seed + 3u, &boot_mean, &boot_std, &ci_lo, &ci_hi);
    } else {
        bootstrap_ci(resident_ticks, calib_samples_used, nonresident_ticks, calib_samples_used,
                     test_ticks, cfg->test_samples, cfg->bootstrap_reps, cfg->seed + 3u,
                     &boot_mean, &boot_std, &ci_lo, &ci_hi);
    }

    printf("# experiment=hit_rate resident_bytes=%" PRIu64 " nonresident_bytes=%" PRIu64
           " calib_samples=%" PRIu64 " test_bytes=%" PRIu64 " test_samples=%" PRIu64
           " bootstrap_reps=%" PRIu64 " warmup_passes=%d seed=%u node_bytes=%zu pattern=%s"
           " fixed_calibration=%d\n",
           cfg->resident_bytes, cfg->nonresident_bytes, calib_samples_used,
           cfg->test_bytes, cfg->test_samples, cfg->bootstrap_reps,
           cfg->warmup_passes, cfg->seed, sizeof(struct node), pattern_name,
           cfg->has_fixed_calibration);

    printf("phase,index,ticks,classified_hit\n");
    for (uint64_t i = 0; i < calib_samples_used; i++) {
        printf("calib_resident,%" PRIu64 ",%.4f,%d\n", i, resident_ticks[i],
               resident_ticks[i] <= tau ? 1 : 0);
    }
    for (uint64_t i = 0; i < calib_samples_used; i++) {
        printf("calib_nonresident,%" PRIu64 ",%.4f,%d\n", i, nonresident_ticks[i],
               nonresident_ticks[i] <= tau ? 1 : 0);
    }
    for (uint64_t i = 0; i < cfg->test_samples; i++) {
        printf("test,%" PRIu64 ",%.4f,%d\n", i, test_ticks[i], test_ticks[i] <= tau ? 1 : 0);
    }

    printf("# result tau_ticks=%.4f sensitivity=%.4f specificity=%.4f p_obs=%.4f "
           "Hhat=%.4f ci_lower=%.4f ci_upper=%.4f bootstrap_mean=%.4f bootstrap_std=%.4f "
           "bootstrap_reps=%" PRIu64 "\n",
           tau, se, sp, p_obs, hhat, ci_lo, ci_hi, boot_mean, boot_std, cfg->bootstrap_reps);
    fflush(stdout);

    free(resident_ticks);
    free(nonresident_ticks);
    free(test_ticks);
    return 0;
}
