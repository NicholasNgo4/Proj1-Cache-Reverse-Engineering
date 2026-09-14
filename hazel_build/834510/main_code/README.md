# main_code/

Final source snapshots used to produce the submitted results. Must match the code
listings printed in the report body and the frozen Git commit.

- `x86_64/`   — Intel/AMD reverse-engineering benchmarks (RDTSC/RDTSCP timing paths)
- `aarch64/`  — Arm reverse-engineering benchmarks (CNTVCT_EL0 timing paths)
- `common/`   — shared/portable code (pointer-chase construction, stats, I/O)
- `pmu/`      — Phase-II performance-counter verification code (perf_event_open, etc.)
- `software_hit_rate/` — final timing-only cache hit-rate/residency estimator (Competition 2)

Each experiment (capacity, line size, associativity, hit latency, miss/next-level
latency, inclusion/exclusion) must have its complete main implementation visible here,
labeled by target property and architecture.
