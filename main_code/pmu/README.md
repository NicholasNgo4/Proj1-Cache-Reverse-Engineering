# main_code/pmu/

Intentionally empty (only `.gitkeep`). This project's Phase-II performance-counter
verification does not use a custom `perf_event_open(2)` C program — it wraps the same
`cache_bench` binary built from `main_code/common/` in the `perf stat` CLI instead, since
that gave clean, per-event-group results on every team machine without needing a bespoke
counter-reading harness.

The actual Phase-II PMU code/scripts live in `scripts/`, not here:

- `scripts/run_pmu_verification.sh` + `scripts/summarize_pmu.py` — the core Phase-II
  per-cache-level PMU verification pipeline (Problem 8.3).
- `scripts/run_standardized_benchmarks.sh` + `scripts/summarize_eight_counters.py` — the
  eight-counter cross-generation study (Problem 8.4).
- `scripts/run_hit_rate_pmu_validation.sh` + `scripts/compare_hit_rate_pmu.py` — PMU
  validation of the software-only hit-rate estimator (Problem 8.5 part 4).

See `scripts/README.md` for the full description of each.
