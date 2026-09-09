# skylark — Reproduction Manifest

> Fill in every field before freezing results. This README must let a grader go from
> this folder to the exact command that generated the data without guessing.

## Machine Identification
- Hostname: skylark.ece.ncsu.edu
- CPU model (from `lscpu`/`/proc/cpuinfo`): AMD EPYC 7532 32-Core Processor (x2 sockets, 64 logical CPUs total)
- ISA / architecture: x86_64
- Vendor / microarchitecture / codename (researched, NOT from cache tables): AMD, Zen 2 ("Rome" server line) — TODO: confirm against team's MACHINE_RESEARCH.md convention, not filled in here to avoid duplicating/contradicting that table
- Introduction year (per the team's stated year convention): see MACHINE_RESEARCH.md
- Process node (if reliably documented): TODO
- Kernel version: 5.14.0-611.38.1.el9_7.x86_64
- Page size: 4096 bytes
- SMT siblings idle during runs? `lscpu` reports Thread(s) per core = 1 (SMT appears disabled machine-wide, not just for this run) — no sibling to idle/reserve

## Environment
- Compiler + version: gcc (GCC) 11.5.0 20240719 (Red Hat 11.5.0-14)
- Compiler flags: `-O0 -g -std=c11 -Wall -Wextra -fno-omit-frame-pointer`
- Timer method used (RDTSC/RDTSCP+LFENCE, CNTVCT_EL0, etc.): `main_code/x86_64/timer_x86.h` — LFENCE+RDTSC to start, RDTSCP+LFENCE to stop (serialized TSC read pair)
- Affinity/binding command used: `taskset -c 10` (see `scripts/run_capacity_full.sh`)
- NUMA/locality method: none explicit — no `numactl` pinning in the script, only `taskset -c 10`. Core 10 is on NUMA node0 (node0 = CPUs 0-31, node1 = CPUs 32-63) per `lscpu -e`; memory locality was not independently verified/pinned.
- Git commit hash of the code used for these results: 881fbfc00f6bf576dfbc35cf5d97ce2a1aa09ad9 (main run, 2026-09-08 12:00:20 -0400) — NOTE: the manual tail-extension2 follow-up (see below) was run afterward against the same checkout; if any code changed between the two, re-check `git log` before treating this hash as covering all skylark capacity data.

## Per-Experiment Reproduction

### capacity/
- Source file(s): `main_code/common/capacity.c`, `main_code/common/main.c`, `main_code/x86_64/timer_x86.h`
- Build command: `make` (from repo root)
- Run command + arguments: `./scripts/run_capacity_full.sh skylark 10 134217728` (coarse_max=128 MiB; script internally invokes `taskset -c 10 ./cache_bench --experiment capacity --pattern <random|sequential> --samples 1000000 ...` per sweep stage — coarse, tail-extension, 3x dense-around-boundary, 2x repeat of deepest boundary, dense-past-deepest-boundary tail check)
- Sample count: 1,000,000 (timed; warm-up excluded)
- Random seed(s): 12345
- Raw output filename(s): `data_raw/skylark/capacity/capacity_{coarse,coarse_ext,dense0,dense1,dense2,dense2_rep1,dense2_rep2,denseTail}_{random,sequential}_20260908T160607Z.csv`
- Processing script -> data_processed path: `data_processed/skylark/capacity/{coarse,coarse_ext,dense0,dense1,dense2,dense2_rep1,dense2_rep2,denseTail}_{random,sequential}_summary.csv`, plotted via `scripts/plot_capacity.py` into `data_processed/skylark/capacity/plots/{capacity_curve,capacity_boxplots}.{png,pdf}`
- Detected boundaries (bytes): 16777216, 18295680, 21757352 (auto-detected by `run_capacity_full.sh`, dense-resampled and repeated 2x at the deepest one)
- Excluded runs (if any) and reason: none excluded. Note: the automated pipeline's own plotting step failed partway through the run (`ModuleNotFoundError: No module named 'matplotlib'` on this machine — see `data_raw/skylark/capacity/run_capacity_full_20260908T160607Z.log`); all data generation stages completed successfully before that failure. matplotlib (+ pillow, cycler, fonttools, kiwisolver) was installed via `pip3 install --user` and the plotting step was re-run standalone with the same summary-file set and boundaries the script would have used — `data_processed/skylark/capacity/plots/` is now up to date with all of the above data.
- Follow-up (not part of the automated `run_capacity_full.sh` pipeline): a manual tail-extension2 check further out (536870912-2147483648 bytes, i.e. 512 MiB-2 GiB), core=10, seed=12345, samples=1,000,000, warmup=3, points-per-octave=48 (same parameters as the script's own dense sweeps), to check for a further plateau beyond what the script's own tail-extension (128-512 MiB) covered.
  - `orig` pass: `run_capacity_ext2_20260908T171553Z.log` -> `data_raw/skylark/capacity/capacity_denseTail2_orig_{random,sequential}_20260908T171553Z.csv` -> `data_processed/skylark/capacity/denseTail2_orig_{random,sequential}_summary.csv` (97 points each, complete).
  - `rep1` repeat: an initial attempt was interrupted partway (86/97 random points, no sequential); discarded and rerun cleanly as `run_capacity_ext2_rep1_20260908T220010Z.log` -> `capacity_denseTail2_rep1_{random,sequential}_20260908T220010Z.csv` -> `denseTail2_rep1_{random,sequential}_summary.csv` (97 points each, complete).
  - Reproducibility: orig vs rep1 medians at 2147483648 bytes (2 GiB) agree within ~0.2% (279.05 vs 278.45 ticks/access, random pattern) -- no anomaly.
  - Finding: median latency rises only ~2% across the whole 512 MiB-2 GiB range (272.9 -> ~279 ticks/access, random pattern), flattening out by ~1.7 GiB. This region reads as an already-settled DRAM-latency plateau, not an open transition -- no further cache-level boundary detected out to 2 GiB.
  - Folded into `data_processed/skylark/capacity/plots/` -- `capacity_curve.{png,pdf}`/`capacity_boxplots.{png,pdf}` now span the full sweep out to 2 GiB (title-suffix "Phase I timing-only, extended to 2 GiB"), built from all coarse/dense/repeat/tail/tail2 summaries together. Confirms the ~16-22 MiB L3->DRAM transition is followed by a genuine flat plateau (~280 ticks/access) all the way to 2 GiB, not an unresolved further climb.

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
