# hazel_broadwell — Reproduction Manifest

> Fill in every field before freezing results. This README must let a grader go from
> this folder to the exact command that generated the data without guessing.

## Machine Identification
- Hostname: `c205n04` (allocated by Slurm for `--constraint=broadwell`, job 833551)
- CPU model (from `lscpu`/`/proc/cpuinfo`): `Intel(R) Xeon(R) CPU E5-2650 v4 @ 2.20GHz` -- matches NC State's documented
  `broadwell` constraint mapping (see PREDICTION_FREEZE.md/assignment Table 4).
- ISA / architecture: x86-64 (`uname -a`: `x86_64 x86_64 x86_64 GNU/Linux`)
- Vendor / microarchitecture / codename (researched, NOT from cache tables): Intel Broadwell-EP
- Introduction year (per the team's stated year convention): 2016
- Process node (if reliably documented): 14 nm
- Kernel version: `5.14.0-611.5.1.el9_7.x86_64`
- Page size: 4096 bytes (standard x86-64)
- SMT siblings idle during runs? This access-check job requested 1 CPU
  (`--cpus-per-task=1`); Slurm bound it to logical CPU 13 (socket 1, NUMA
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
  Resulting binding: `physcpubind: 13`, socket 1, NUMA node 1
  (via `numactl -s`).
- NUMA/locality method: `numactl -s` plus `lscpu -e=CPU,CORE,SOCKET,NODE` (both on the Phase
  Discipline whitelist) -- logical CPU 13 is socket 1, NUMA node 1 on this node.
- Git commit hash of the code used for these results: `cb7e0c8c82c0269507e665db04563dee78fda9a6` (the `predictions-frozen`
  tag's own commit is an ancestor of this HEAD -- confirmed by this job's own gate check
  before running anything past the smoke test)

**Job record (this pass -- access/build check only, not the full suite):** Slurm job ID
833551, elapsed 35s, exit code 0. Full stdout/stderr: `hw1_broadwell_833551.log` /
`hw1_broadwell_833551.err.log` (committed alongside this README; `.log` suffix used instead of
Slurm's default `.out` because this repo's `.gitignore` blanket-ignores `*.out`). The job built
`cache_bench` cleanly (in an isolated per-job directory, `hazel_build/833551/`, to avoid
races with sibling generations' jobs building concurrently in this same shared GPFS checkout --
see `hpc_slurm/hw1_broadwell.sh`'s header) and ran one tiny (`--samples 1000`, 4096-65536 B)
`--experiment capacity` smoke test under `srun --cpu-bind=cores` to confirm the binary runs
correctly bound to a real core on Hazel -- this is NOT the 1,000,000-sample suite required for
the actual capacity/line_size/associativity/latency/inclusion_policy experiments, which are run
by a separate `hw1_broadwell_<experiment>.sh` job script per experiment type (see
`hpc_slurm/README.md`).

## Per-Experiment Reproduction

### capacity/
- Slurm job ID: 837629, logical CPU 12, elapsed 1h23m07s, exit 0.
- Source file(s): `main_code/common/{main.c,benchmark.c,pointer_chase.c,random.c,capacity.c}`,
  `scripts/run_capacity_full.sh` (`HAZEL_MODE=1`), `scripts/summarize_raw.py`,
  `scripts/detect_cache_hierarchy.py`, `scripts/plot_capacity.py`
- Build command: `make -s` (isolated per-job copy under `hazel_build/837629/`, cleaned up on
  job exit)
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_capacity_full.sh hazel_broadwell 12`
  (coarse_max defaulted to 67,108,864 B / 64 MiB, then a 4x tail extension to 256 MiB)
- Sample count: 1,000,000 (timed; warm-up excluded) -- every stage
- Random seed(s): base 12345; reproducibility repeats on the deepest boundary use the same
  seed (this script's own known limitation)
- Raw output filename(s):
  `data_raw/hazel_broadwell/capacity/capacity_{coarse,coarse_ext,dense0..dense4,dense4_rep1,
  dense4_rep2,denseTail}_{random,sequential}_20260915T010343Z.csv.gz`; full transcript:
  `data_raw/hazel_broadwell/capacity/run_capacity_full_20260915T010343Z.log`
- Processing script -> data_processed path: `scripts/summarize_raw.py` ->
  `data_processed/hazel_broadwell/capacity/*_summary.csv`;
  `scripts/detect_cache_hierarchy.py` (default thresholds) -> 5 candidate boundaries (see
  Findings); `scripts/plot_capacity.py` ->
  `data_processed/hazel_broadwell/capacity/plots/capacity_{curve,boxplots}.{png,pdf}`
- Excluded runs (if any) and reason: none -- single complete run, no anomalies of the
  icelake_6326/sapphirerapids kind (some noise, but no implausible ~2x drops).

**Findings (timing-only; no vendor/cache-topology lookup used, per Phase I discipline).
CPU: Intel Xeon E5-2650 v4 (Broadwell-EP) -- same E5-2650 SKU line, one generation newer,
as hazel_haswell's own E5-2650 v3.**
- **L1D: well-confirmed at 32,768 B (32 KiB).** Flat ~7.66-7.83 ticks/access from 1,024 B
  through 32,768 B, then a clean, sustained climb starting at 35,728 B (8.26) -- matches the
  frozen prediction and hazel_haswell's own confirmed L1D exactly (same family, one
  generation apart).
- **L2: a real, if noisy, transition centered almost exactly on the architecturally-standard
  256 KiB.** The 142,928-285,864 B region shows large point-to-point oscillation (e.g.
  169,976 B: 14.80 vs. 202,136 B: 13.10 vs. 220,432 B: 16.78 -- 20-30% swings between adjacent
  points), but the auto-detector's own two candidates here (202,136 / 339,952 B) bracket
  262,144 B almost symmetrically, and 262,144 B (18.70) sits right in the middle of the
  climbing trend. **L2 best-guess: 262,144 B (256 KiB)** -- Broadwell-EP's publicly known
  per-core L2 size (matching haswell's own L2 best-guess exactly, same family), read with
  higher confidence than a pure best-guess given how well the noisy region's center lines up
  with this exact round value, but still not a single clean knee.
- **LLC: a genuine, long flat shelf (2-24 MiB) followed by a real departure.** From
  1,923,096 B (43.30) the curve settles into a long, quite flat plateau -- 38-43 ticks/access
  continuously from ~2 MiB through 23,726,560 B (41.41), a 12x size range with minimal drift
  -- then a clear, sustained departure: 25,874,000 B -> 46.78, 28,215,800 B -> 49.60,
  33,554,432 B -> 58.56, 36,591,368 B -> 89.76. **LLC best-guess: 25,874,000 B (~24.68 MiB)**
  -- the provisional edge where the shelf first clearly departs (same methodology as
  hazel_haswell's own LLC pick), somewhat below this SKU's own often-cited ~30 MB L3 spec but
  in the same order of magnitude.
- **LLC-to-DRAM: noisy, does not cleanly plateau within the tested range (up to 268 MiB).**
  Tail extension values swing substantially (103,496,016 B: 149.99, 181,765,096 B: 264.63,
  210,002,800 B: 173.66, 268,435,448 B: 202.65) with no clear monotonic trend but also no
  settled floor -- consistent with a real but noisy plateau, not confidently resolved. A
  further manual extension/repeat would be needed to pin down the true DRAM floor cleanly --
  not attempted this pass.
- **Held-out comparison against the frozen prediction:** the frozen L1D prediction
  (32,768 B / 8-way, Chen-Ngo Invariance Law, derived from hazel_haswell's own sibling SKU)
  matches this run's timing-derived L1D capacity exactly.
- Raw output filename(s): 
- Processing script -> data_processed path: 
- Excluded runs (if any) and reason: 

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
