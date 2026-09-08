# sunbird — Reproduction Manifest

> Fill in every field before freezing results. This README must let a grader go from
> this folder to the exact command that generated the data without guessing.

## Machine Identification
- Hostname: sunbird.ece.ncsu.edu
- CPU model (from `lscpu`/`/proc/cpuinfo`): Intel(R) Xeon(R) CPU E5-2680 v3 @ 2.50GHz (2 sockets)
- ISA / architecture: x86-64
- Vendor / microarchitecture / codename (researched, NOT from cache tables): Intel Haswell (Haswell-EP), per course Table 1
- Introduction year (per the team's stated year convention): TODO — fill in per team's chosen convention (see MACHINE_RESEARCH.md)
- Process node (if reliably documented): TODO
- Kernel version: Linux 5.14.0-611.54.1.el9_7.x86_64 (see build/kernel_version.txt)
- Page size: 4096 bytes (see build/page_size.txt)
- SMT siblings idle during runs? Yes for the pinned core: this session's cgroup/cpuset grants exclusive use of logical CPUs {0,1,2,24,25,26} (3 full physical cores, both SMT threads each, per `lscpu -e=CPU,CORE,SOCKET,NODE`). Runs are pinned to CPU 2 (physical core 2, socket 0, NUMA node 0); its SMT sibling CPU 26 was left idle (no other process launched on it) for the duration of each run. Machine is shared: `who`/`uptime` showed 4 other logged-in users and load average ~3.0 at run time — see below for the interference this produced.

## Environment
- Compiler + version: see `build/compiler_version.txt` (GCC 11.5.0, Red Hat 11.5.0-14)
- Compiler flags: `-O0 -g -std=c11 -Wall -Wextra -fno-omit-frame-pointer` (Makefile CFLAGS)
- Timer method used (RDTSC/RDTSCP+LFENCE, CNTVCT_EL0, etc.): x86 RDTSC (LFENCE-fenced start) / RDTSCP (LFENCE-fenced stop), batched: N=1000 dependent pointer-chase steps timed per start/stop pair, ticks/access = (t1-t0)/N. See `main_code/x86_64/timer_x86.h`, `main_code/common/benchmark.c`. Disassembly excerpt confirming the loop/timer placement survived -O0 unmodified: `build/cache_bench.source.dis` (functions `x86_tsc_start`, `x86_tsc_stop`, `measure_dependency_chain_batched`).
- Affinity/binding command used: `taskset -c 2 ./cache_bench ...` (see `scripts/run_capacity_sweep.sh`)
- NUMA/locality method: no explicit NUMA pinning beyond CPU affinity; default first-touch allocation on the pinned CPU's own node (node 0) is expected for `malloc`-then-touch on Linux. Not verified with `numastat` (Phase-I-safe; contains no cache-topology info, TODO if we want to confirm).
- Git commit hash of the code used for these results: see `build/git_commit_at_run.txt` (recorded at build+run time; update after each frozen checkpoint)

## Per-Experiment Reproduction

### capacity/
- Source file(s): `main_code/common/{main.c,capacity.c,capacity.h,benchmark.c,benchmark.h,pointer_chase.c,pointer_chase.h,random.c,random.h}`, `main_code/x86_64/timer_x86.h`, `main_code/common/timer.h`
- Build command: `make` (from repo root; see `Makefile`)
- Run command + arguments:
  - Coarse sweep, 1 KiB-64 MiB (both patterns): `./scripts/run_capacity_sweep.sh sunbird 2 --pattern random --samples 1000000 --batch-size 1000 --min-bytes 1024 --max-bytes 67108864 --points-per-octave 8 --warmup-passes 3 --seed 12345` (and `--pattern sequential`)
  - Coarse sweep extension, 64 MiB-256 MiB (both patterns): same flags with `--min-bytes 67108864 --max-bytes 268435456 --points-per-octave 8`
  - Dense window A (candidate L1 transition, ~16 KiB - 512 KiB): same flags with `--min-bytes 16384 --max-bytes 524288 --points-per-octave 48`, both patterns
  - Dense window B (candidate deeper-level transition, ~8 MiB - 64 MiB): same flags with `--min-bytes 8388608 --max-bytes 67108864 --points-per-octave 48`, both patterns
  - Dense window C (deeper-level transition and its plateau, ~16 MiB - 256 MiB): same flags with `--min-bytes 16777216 --max-bytes 268435456 --points-per-octave 48`, both patterns
  - Dense window C repeat (reproducibility check, ~16 MiB - 128 MiB): identical flags/seed, re-run independently to test whether the spikes seen in window C recur at the same sizes; `--min-bytes 16777216 --max-bytes 134217728 --points-per-octave 48`, both patterns
  - Dense window C rep2, rep3 (two more independent repeats, full ~16 MiB - 256 MiB range, identical flags/seed to window C): run specifically to tighten the noisy ~150 MiB+ plateau estimate by averaging more independent samples per size point
  - All runs pinned with `taskset -c 2`
- Sample count: 1,000,000 timed accesses per (size, pattern) point; warm-up (3 full untimed chase passes) excluded from that count
- Random seed(s): 12345 (xorshift32, `make_random_cycle`); sequential-pattern runs use `make_sequential_cycle` (no seed/randomness)
- Raw output filename(s): `data_raw/sunbird/capacity/capacity_coarse_{random,sequential}_<timestamp>.csv`, `capacity_coarse_ext256_{random,sequential}_<timestamp>.csv`, `capacity_denseA_{random,sequential}_<timestamp>.csv`, `capacity_denseB_{random,sequential}_<timestamp>.csv`, `capacity_denseC_{random,sequential}_<timestamp>.csv`
- Processing script -> data_processed path: `python3 scripts/summarize_raw.py <raw.csv> -o data_processed/sunbird/capacity/<name>_summary.csv`, then `python3 scripts/detect_cache_hierarchy.py <summary.csv>` for a first-pass (non-final) boundary hypothesis, then `python3 scripts/plot_capacity.py <all summary.csv...> -o data_processed/sunbird/capacity/plots --machine sunbird --boundary 32KiB --boundary 20MiB --boundary 150MiB` for the required curve and box-plot figures
- Excluded runs (if any) and reason: `capacity_20260907T053240Z.csv` (first exploratory run, predates the `--pattern` CLI option and the `pattern` CSV column) is retained but superseded by `capacity_coarse_random_*` for analysis, since its schema differs (no pattern column) and it was random-pattern-only.
- Known noise in dense window C, and reproducibility check: isolated single-point median spikes at working-set sizes ~16.5, 20.5, 22.6, 25.4, 28.9, and 29.3 MiB in the original window C run (several with `n_outliers=0`, meaning most of that point's 1000 batches were elevated together, not just a few stray ones) are consistent with transient scheduling interference on this shared, multi-user machine. This was confirmed, not just assumed: an independent repeat run over the same 16-128 MiB size grid (identical flags/seed) produced spikes at *different* sizes than the original run (e.g. original spikes at 16.47/20.45 MiB were flat in the repeat; the repeat instead spiked at 16.0/19.87 MiB where the original was flat). Since the noise doesn't recur at the same working-set size across independent runs, it is not a property of that size -- it's whatever else happened to be running on the shared machine during that specific ~1-2s measurement window. Point-by-point comparison of the two runs is not saved as a script (was done ad hoc in the session); the two raw/summary file pairs (`capacity_denseC_*_20260908T013237Z*` and `capacity_denseC_repeat_*_20260908T023625Z*`) are both retained so this comparison is reproducible from the data.
- `scripts/plot_capacity.py` combines overlapping summary rows (same size+pattern appearing in more than one input file, e.g. the coarse/dense/repeat sweeps above overlap on a shared log-spaced grid) by averaging medians and widening the plotted whisker range to the union of the inputs' p5/p95, rather than letting the last-loaded file silently overwrite the others -- see `combine_duplicate_rows()` in that script.
- With rep2/rep3 added, most size points >=16 MiB now have 3-5 independent measurements. Checked the >=145 MiB plateau specifically: across 40 points, the run-to-run spread in median (max-min across available runs, divided by mean) averages 3.6% and is under 2% at many points -- confirms this region is a genuine stable plateau (~190-205 ticks/access) rather than a still-noisy or still-climbing region; the wider apparent noise in earlier single/double-run plots there was mostly a small-sample-size artifact. The ~19-25 MiB transition region remains genuinely more variable run-to-run even after averaging (individual points still show 30-90 tick spreads across runs) -- this is a real property of measuring a steep transition, not something more averaging alone will fully clean up.
- `capacity_boxplots.png/.pdf` now annotates each box with the number of independent runs combined at that point and their run-to-run median spread as a percentage (e.g. "5 runs, 4% spread"), or "1,000 samples" when only one run covered that exact size -- so the figure itself shows which boundary points are well-supported vs. which aren't, rather than that having to live only in this README. The 19.87 MiB "near 20 MiB boundary" box is a good example of the latter: 95% spread across 5 runs, correctly flagging it as an unreliable point sitting inside the steep transition rather than a clean boundary marker.
- Known interference: many summary rows show per-point mean/stddev far above the median (batch maxima repeatedly near ~32.5-60k ticks among otherwise ~10-150 tick batches), consistent with occasional OS scheduling interruptions on this shared, multi-user machine rather than a cache effect. Use median (not mean) for boundary inference; report the outlier count and note this in box plots.

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
