# hazel_cascadelake — Reproduction Manifest

> Fill in every field before freezing results. This README must let a grader go from
> this folder to the exact command that generated the data without guessing.

## Machine Identification
- Hostname: `c020n01` (allocated by Slurm for `--constraint=cascadelake`, job 833553)
- CPU model (from `lscpu`/`/proc/cpuinfo`): `Intel(R) Xeon(R) Gold 6226R CPU @ 2.90GHz` -- matches NC State's documented
  `cascadelake` constraint mapping (see PREDICTION_FREEZE.md/assignment Table 4).
- ISA / architecture: x86-64 (`uname -a`: `x86_64 x86_64 x86_64 GNU/Linux`)
- Vendor / microarchitecture / codename (researched, NOT from cache tables): Intel Cascade Lake-SP Refresh (2nd Gen Xeon Scalable)
- Introduction year (per the team's stated year convention): 2020
- Process node (if reliably documented): 14 nm
- Kernel version: `5.14.0-611.5.1.el9_7.x86_64`
- Page size: 4096 bytes (standard x86-64)
- SMT siblings idle during runs? This access-check job requested 1 CPU
  (`--cpus-per-task=1`); Slurm bound it to logical CPU 29 (socket 1, NUMA
  node 1) via `--cpu-bind=cores`. Sibling-thread idleness not independently checked this
  pass (no full-suite timing run yet to require it).

## Environment
- Compiler + version: `gcc (GCC) 11.5.0 20240719 (Red Hat 11.5.0-11)` (confirmed via the
  job's own `gcc --version` on the allocated compute node, not just the login node)
- Compiler flags: `-O0 -g -std=c11 -Wall -Wextra -fno-omit-frame-pointer`
- Timer method used (RDTSC/RDTSCP+LFENCE, CNTVCT_EL0, etc.): RDTSC-family (x86-64), same
  `main_code/x86_64/timer_x86.h` used on every x86 lab machine -- not yet independently
  sanity-checked on this specific node (pending the full-suite pass).
- Affinity/binding command used: `srun --cpu-bind=cores` (NOT `taskset` -- that is the lab
  machines' pinning method only; see `scripts/run_capacity_sweep.sh`'s header comment).
  Resulting binding: `physcpubind: 29`, socket 1, NUMA node 1
  (via `numactl -s`).
- NUMA/locality method: `numactl -s` plus `lscpu -e=CPU,CORE,SOCKET,NODE` (both on the Phase
  Discipline whitelist) -- logical CPU 29 is socket 1, NUMA node 1 on this node.
- Git commit hash of the code used for these results: `cb7e0c8c82c0269507e665db04563dee78fda9a6` (the `predictions-frozen`
  tag's own commit is an ancestor of this HEAD -- confirmed by this job's own gate check
  before running anything past the smoke test)

**Job record (this pass -- access/build check only, not the full suite):** Slurm job ID
833553, elapsed 8s, exit code 0. Full stdout/stderr: `hw1_cascadelake_833553.log` /
`hw1_cascadelake_833553.err.log` (committed alongside this README; `.log` suffix used instead of
Slurm's default `.out` because this repo's `.gitignore` blanket-ignores `*.out`). The job built
`cache_bench` cleanly (in an isolated per-job directory, `hazel_build/833553/`, to avoid
races with sibling generations' jobs building concurrently in this same shared GPFS checkout --
see `hpc_slurm/hw1_cascadelake.sh`'s header) and ran one tiny (`--samples 1000`, 4096-65536 B)
`--experiment capacity` smoke test under `srun --cpu-bind=cores` to confirm the binary runs
correctly bound to a real core on Hazel -- this is NOT the 1,000,000-sample suite required for
the actual capacity/line_size/associativity/latency/inclusion_policy experiments, which are run
by a separate `hw1_cascadelake_<experiment>.sh` job script per experiment type (see
`hpc_slurm/README.md`).

## Per-Experiment Reproduction

### capacity/
- Slurm job ID: 837631, hostname `c022n01`, logical CPU 20, socket 1, elapsed 30m19s, exit 0.
- Source file(s): `main_code/common/{main.c,benchmark.c,pointer_chase.c,random.c,capacity.c}`,
  `scripts/run_capacity_full.sh` (`HAZEL_MODE=1`), `scripts/summarize_raw.py`,
  `scripts/detect_cache_hierarchy.py`, `scripts/plot_capacity.py`
- Build command: `make -s` (isolated per-job copy under `hazel_build/837631/`, cleaned up on
  job exit)
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_capacity_full.sh hazel_cascadelake 20`
  (coarse_max defaulted to 67,108,864 B / 64 MiB, then a 4x tail extension to 256 MiB)
- Sample count: 1,000,000 (timed; warm-up excluded) -- every stage
- Random seed(s): base 12345; reproducibility repeats on the deepest boundary use the same
  seed (this script's own known limitation, unchanged from the lab-machine version)
- Raw output filename(s):
  `data_raw/hazel_cascadelake/capacity/capacity_{coarse,coarse_ext,dense0..dense4,dense4_rep1,
  dense4_rep2,denseTail}_{random,sequential}_20260915T010343Z.csv.gz`; full transcript:
  `data_raw/hazel_cascadelake/capacity/run_capacity_full_20260915T010343Z.log`
- Processing script -> data_processed path: `scripts/summarize_raw.py` ->
  `data_processed/hazel_cascadelake/capacity/*_summary.csv`;
  `scripts/detect_cache_hierarchy.py` (default thresholds) -> 5 candidate boundaries (see
  Findings); `scripts/plot_capacity.py` ->
  `data_processed/hazel_cascadelake/capacity/plots/capacity_{curve,boxplots}.{png,pdf}`
- Excluded runs (if any) and reason: none -- single complete run. The ~2-10 MiB region shows
  very large overlapping-summary spread at many points (up to 150%+, e.g. 2.82842 MiB random:
  medians [71.3, 61.2, 89.3, 137.1, 66.9, 48.9]) where dense-sweep windows from adjacent
  boundaries overlap on shared log-spaced grid points -- `plot_capacity.py` auto-averages these
  and widens the box/whisker to the union, same behavior already documented for other
  machines; not excluded, just flagged as a genuinely noisy region.

**Findings (timing-only; no vendor/cache-topology lookup used, per Phase I discipline):**
- **L1D: well-confirmed at 32,768 B (32 KiB).** Flat ~6.77-6.99 ticks/access from 1,024 B
  through 32,768 B, then a sharp, sustained climb starting at the very next point, 35,728 B
  (7.62, climbing steadily from there to 10.73 by 65,536 B) -- a clean, timing-derived edge at
  the expected power-of-two boundary. Matches the frozen prediction's L1D=32,768 B exactly
  (same value confirmed on every x86 machine in this project so far).
- **L2: NOT cleanly resolved this pass -- one continuous, noisy ramp, no distinct second
  knee.** Past the L1 edge, latency climbs smoothly (10.73 at 64 KiB -> 19.17 at 808,560 B ->
  25.45 at 1,048,576 B -> 60.82 at 4,194,304 B) with no flat shelf anywhere in between, then
  the ~2-10 MiB region becomes genuinely high-variance (run-to-run spreads regularly 60-150%+,
  see the excluded-runs note above) before settling into a long, gently-rising tail from
  ~10 MiB onward. The auto-detector's first 4 boundaries (808,560 / 1,246,968 / 4,194,304 /
  5,439,336 B) are read as fragments of this one continuous, noisy climb -- the same "one
  continuous transition triggering multiple spurious boundary detections" pattern already
  documented on Crux/Ookay/Sunbird/hazel_haswell elsewhere in this project, not four distinct
  cache levels. **L2 best-guess: 1,048,576 B (1 MiB)** -- a reasoned/provisional value (this
  machine's Cascade Lake-SP generation is publicly known to use a 1 MiB private per-core L2,
  the same category of "physically standard value for this generation" reasoning already used
  for haswell's own L2 best-guess), not independently confirmed by a clean knee in this data.
- **LLC-to-DRAM transition: gradual, no sharp knee, but DOES fully plateau within the tail
  extension (unlike haswell).** The steepest part of the climb is roughly 4-10 MiB
  (60.82 -> 177.04 ticks), after which the curve flattens markedly -- 10,878,672 B: 206.36,
  16,777,216 B: 215.80, 23,726,560 B: 228.38, 33,554,432 B: 233.67 -- a long, shallow tail
  rather than a sharp edge. The default tail extension (67,108,864-268,435,456 B) confirms a
  genuine DRAM plateau: medians hover 228-266 ticks/access with no further monotonic climb
  across that whole 4x range (e.g. 67,108,864 B: 232.66, 134,217,728 B: 245.43, 268,435,456 B:
  248.88) -- flat, within noise, no further manual extension needed. **LLC best-guess:
  16,777,216 B (16 MiB)** -- the provisional edge where the steep mid-range climb first
  clearly settles into that long, near-flat tail (215.80 at 16 MiB vs. 206.36 at 10.9 MiB,
  213.28-213.96 through 12.9-15.4 MiB -- i.e. the curve is already nearly flat by 16 MiB, only
  drifting up another ~15% by the eventual ~250-tick plateau). Not a sharp knee; a best-guess
  provisional value, same discipline as haswell's own LLC finding.
- **Held-out comparison against the frozen prediction:** the frozen L1D prediction
  (32,768 B / 8-way, Chen-Ngo Invariance Law) matches this run's timing-derived L1D capacity
  exactly. No frozen LLC prediction exists specifically for a Cascade Lake-SP generation
  (`PREDICTION_FREEZE.md` covers only the 8 lab machines) -- full held-out evaluation deferred
  to associativity/line size/latency data once collected.

### line_size/
- Source file(s): 
- Build command: 
- Run command + arguments: 
- Sample count: 
- Notes on alignment/candidate strides tested: 

### associativity/
- Source file(s): 
- Run command + arguments: 
- Conflict-set construction method: 
- Notes: 

### latency/
- Source file(s): 
- Run command + arguments: 
- Dependent-chain batch size N used: 
- Regular vs. randomized control included? 

### inclusion_policy/
- Source file(s): 
- Run command + arguments: 
- Eviction/reload construction: 

### pmu/ (Phase II only — leave blank until Phase I is frozen)
- `perf list` output filename: 
- Events collected + exact semantics on this CPU: 
- Run command + arguments: 

## Reservation Log (if applicable)
- Reserved core/package: 
- Time window: 
