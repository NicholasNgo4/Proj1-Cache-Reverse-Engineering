# crux — Reproduction Manifest

> Fill in every field before freezing results. This README must let a grader go from
> this folder to the exact command that generated the data without guessing.

## Machine Identification
- Hostname: crux.ece.ncsu.edu
- CPU model (from `lscpu`/`/proc/cpuinfo`): Intel(R) Core(TM) i7-9700 CPU @ 3.00GHz (1 socket, 8 cores, 1 thread/core -- no SMT)
- ISA / architecture: x86-64
- Vendor / microarchitecture / codename (researched, NOT from cache tables): Intel Coffee Lake (Coffee Lake Refresh), per `MACHINE_RESEARCH.md` Table 1
- Introduction year (per the team's stated year convention): 2019 (per `MACHINE_RESEARCH.md`)
- Process node (if reliably documented): 14 nm (per `MACHINE_RESEARCH.md`)
- Kernel version: Linux 6.8.0-88-generic
- Page size: 4096 bytes (`getconf PAGE_SIZE`)
- SMT siblings idle during runs? N/A -- this CPU has no SMT (`lscpu`: 1 thread/core, 8 cores/socket, 1 socket = 8 logical CPUs total, one-to-one with physical cores).

## Environment
- Compiler + version: GCC 13.3.0 (Ubuntu 13.3.0-6ubuntu2~24.04.1)
- Compiler flags: `-O0 -g -std=c11 -Wall -Wextra -fno-omit-frame-pointer`
- Timer method used (RDTSC/RDTSCP+LFENCE, CNTVCT_EL0, etc.): x86 RDTSC (LFENCE-fenced start) / RDTSCP (LFENCE-fenced stop), batched: N=1000 dependent pointer-chase steps timed per start/stop pair, ticks/access = (t1-t0)/N. See `main_code/x86_64/timer_x86.h`, `main_code/common/benchmark.c`.
- Affinity/binding command used: `taskset -c 7 ./cache_bench ...` (see `scripts/run_capacity_full.sh` and the ad hoc `crux_tail2.sh` follow-up described below). Core 7 was chosen after checking `Cpus_allowed_list` (session had 0-7 available), `lscpu -e=CPU,CORE,SOCKET,NODE` (confirmed CPU==CORE, i.e. no SMT sibling to worry about), and `who`/`ps -eLo pid,psr,pcpu,user,comm`/`mpstat -P ALL 1 2` to check for other students' active load: at run time, CPU 0 was 100%-pinned by `clclark7`'s `associativity` process and CPU 4 was 100%-pinned by `hbsu`'s and `rsivaku3`'s `cache_bench` processes (confirmed via `taskset -pc` on each PID); CPUs 1,2,3,5,6,7 were idle across two independent `mpstat` samples. Core 7 was picked from that idle set.
- NUMA/locality method: no explicit NUMA pinning; single-socket machine (no NUMA to control for). Default first-touch allocation on `malloc`-then-touch.
- Git commit hash of the code used for these results: `881fbfc00f6bf576dfbc35cf5d97ce2a1aa09ad9` (working tree was clean of code changes at run time; only new data/plot files were added by the run, listed below)

## Per-Experiment Reproduction

### capacity/
- Source file(s): `main_code/common/{main.c,capacity.c,capacity.h,benchmark.c,benchmark.h,pointer_chase.c,pointer_chase.h,random.c,random.h}`, `main_code/x86_64/timer_x86.h`, `main_code/common/timer.h`
- Build command: `make` (from repo root; see `Makefile`)
- Run command + arguments:
  - Full automatic pipeline: `./scripts/run_capacity_full.sh crux 7` (default `coarse_max_bytes` = 64 MiB). This ran, in order: coarse sweep 1 KiB-64 MiB (both patterns, 8 points/octave) -> automatic 4x tail-extension sweep 64-256 MiB -> `detect_cache_hierarchy.py --machine-readable` on the combined coarse+tail random data -> dense sweeps (48 points/octave, +-3 octaves) around each of the 4 detected boundaries (262144, 9147840, 11863280, 16777216 bytes) -> 2 reproducibility repeats on the deepest boundary's dense window (16.78 MiB, i.e. 2-128 MiB) -> a dense sweep past the deepest boundary, 64-256 MiB, checking for a further plateau -> plots.
  - Manual follow-up (`crux_tail2.sh`, ad hoc script, not committed): after inspecting the automatic pipeline's 64-256 MiB tail data, the median was still climbing at the 256 MiB ceiling (218 ticks at 64 MiB -> 243 ticks at 256 MiB, no flattening), so per the team's Sunbird precedent this was extended rather than accepted as final. Ran one additional dense sweep (48 points/octave) from 256 MiB to 1 GiB (`--min-bytes 268435456 --max-bytes 1073741824`), both patterns, plus 2 independent repeats of the same window, all pinned `taskset -c 7`, same seed/samples/batch/warmup as below. 1 GiB was chosen as 4x the prior 256 MiB ceiling (matching the automatic script's own tail-extension rule), and checked against the memory-safety rule (25% of `MemAvailable` at run time was ~3.46 GiB, comfortably above the 1 GiB single-buffer allocation).
  - All runs: `--samples 1000000 --batch-size 1000 --warmup-passes 3 --seed 12345`, `--pattern random` and `--pattern sequential` each.
- Sample count: 1,000,000 timed accesses per (size, pattern) point; warm-up (3 full untimed chase passes) excluded from that count
- Random seed(s): 12345 (xorshift32, `make_random_cycle`); sequential-pattern runs use `make_sequential_cycle` (no seed/randomness)
- Raw output filename(s): all under `data_raw/crux/capacity/`, timestamp `20260908T231021Z` for every file (the manual follow-up reused this timestamp for filename continuity even though it ran later in a separate invocation): `capacity_coarse_{random,sequential}_*.csv.gz`, `capacity_coarse_ext_{random,sequential}_*.csv.gz` (64-256 MiB tail), `capacity_dense{0,1,2,3}_{random,sequential}_*.csv.gz` (dense windows around the 4 detected boundaries), `capacity_dense3_rep{1,2}_{random,sequential}_*.csv.gz` (deepest-boundary repeats), `capacity_denseTail_{random,sequential}_*.csv.gz` (64-256 MiB post-boundary check, part of the automatic pipeline), `capacity_denseTail2_{orig,rep1,rep2}_{random,sequential}_*.csv.gz` (manual 256 MiB-1 GiB follow-up, 3 independent runs). Gzipped after the fact (~9x smaller) to keep repo size manageable; summaries in `data_processed/` were generated from the uncompressed originals before compression. Full transcript of the automatic pipeline: `run_capacity_full_20260908T231021Z.log`.
- Processing script -> data_processed path: `python3 scripts/summarize_raw.py <raw.csv> -o data_processed/crux/capacity/<name>_summary.csv` for every raw file above, then `python3 scripts/plot_capacity.py <all summary.csv except coarse_combined_random_summary.csv> -o data_processed/crux/capacity/plots --machine crux --boundary 262144 --boundary 9147840 --boundary 11863280 --boundary 16777216`. (`coarse_combined_random_summary.csv` is an internal concatenation used only as input to `detect_cache_hierarchy.py`, not a real independent run -- excluded from the plot inputs to avoid `plot_capacity.py` treating it as a spurious duplicate/second observation of the same data.)
- Excluded runs (if any) and reason: none excluded; all runs listed above are included in the final plots.
- **Boundary detection and plateau status** (see also `MACHINE_RESEARCH.md`/report for the final level assignment -- this is the raw-data-level finding):
  - **~5.6-7 ticks/access plateau, 1 KiB-~64 KiB**: flat, low-noise (stddev ~0.2 ticks at most points). Confirmed genuine plateau (L1 region) directly from the coarse sweep; no further work needed.
  - **~7-40 ticks/access, ~64 KiB-~4 MiB**: a shallow, continuous ramp rather than a hard plateau -- `dense0` (32 KiB-2 MiB, bracketing the auto-detected 262144-byte/256 KiB boundary) shows no flat shelf immediately after 256 KiB; latency keeps climbing gently all the way to ~4 MiB. Treated as an open/soft region, not a confirmed second plateau -- flagged here rather than asserted as an L2 boundary.
  - **~40-250 ticks/access, ~4-64 MiB**: one dominant steep S-curve transition. The auto-detector's three boundaries in this span (9147840 / 11863280 / 16777216 bytes, i.e. ~8.7/11.3/16 MiB) are three points along this single ramp, not three separate levels -- consistent with the team's Sunbird finding that a steep transition region gets over-segmented by the knee-detector. The two independent repeats (`dense3_rep1`, `dense3_rep2`) on the 16.78 MiB window reproduced large point-to-point run-to-run spread here (up to ~89% at some sizes, e.g. 8.85 MiB: medians [59.3, 48.2, 51.6, 108.7, 76.0] across runs) -- this region is genuinely noisy/variable run-to-run, not just noisy within one run, and any single-run boundary estimate inside it should be treated with caution.
  - **~245-250 ticks/access plateau, ~100 MiB-1 GiB**: **initially open, now confirmed genuine.** The automatic pipeline's 64-256 MiB tail-extension was still climbing at its 256 MiB ceiling (218 ticks at 64 MiB -> 243 ticks at 256 MiB, no flattening) -- per the team's Sunbird precedent, this was not accepted as final. The manual 256 MiB-1 GiB follow-up (orig + 2 repeats) shows the climb slowing sharply and flattening: average median across the 3 runs rises only ~243->250 ticks (~3%) over the full 256 MiB-1 GiB range (vs. ~11% per octave in the still-transitioning 64-256 MiB region), and the 3 independent runs agree within 0.2-0.5% at the 1 GiB endpoint (249.376 / 249.893 / 249.901 ticks). Run-to-run spread across the 256 MiB-1 GiB range is under 1% at nearly every point, with two isolated exceptions (~322 MiB: 3.7%, ~912 MiB: 4.7%) consistent with the same kind of transient scheduling interference documented below, not a real property of those sizes. This plateau is interpreted as the machine's true random-access DRAM latency floor once the working set is far outside any cache level, not a cache boundary itself.
- **Known interference / anomalies**:
  - This is a shared, multi-user lab machine. At run time (concurrently with our benchmark, on other cores): `clclark7` running an `associativity` benchmark pinned to CPU 0, `hbsu` and `rsivaku3` each running `cache_bench`-family benchmarks pinned to CPU 4 (`hbsu`'s own project, unrelated to this repo) -- confirmed not to overlap our core (7) via `taskset -pc` on each PID. Load average climbed from ~3.1 to ~3.9 over the course of this session as more students started jobs.
  - The automatic pipeline's `dense3` deepest-boundary window (16.78 MiB, 2-128 MiB) showed very large run-to-run spread in its 2 reproducibility repeats (up to ~89% at individual points in the 5-15 MiB steep-transition region) -- same signature as the Sunbird multi-tenant-interference finding: noise localized to a subset of runs at a subset of sizes, not a consistent property of the region across all runs.
  - The manual 256 MiB-1 GiB follow-up showed large wall-clock time variance for nominally identical work: the original 256 MiB-1 GiB random sweep took 35m53s, an immediately following independent repeat (rep1) took only 13m01s for the same parameters, and a second repeat (rep2) took ~40 min -- a ~3x spread in wall-clock time for the same fixed sample count, most plausibly explained by other students' concurrent jobs contending for shared resources (memory bandwidth, LLC) even though affinity kept our process on its own dedicated core. This did not measurably corrupt the *timing* data itself (the three runs' medians agree within 0.5% at every size checked), only the wall-clock duration of collecting it.
  - Sequential-pattern latency stayed flat (~5-7 ticks) across the entire 1 KiB-1 GiB range in every sweep, confirming the hardware prefetcher fully hides main-memory latency for the sequential control even at gigabyte-scale footprints, as expected.

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
