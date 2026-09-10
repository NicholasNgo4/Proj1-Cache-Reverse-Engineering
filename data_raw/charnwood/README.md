# charnwood — Reproduction Manifest

> Fill in every field before freezing results. This README must let a grader go from
> this folder to the exact command that generated the data without guessing.

## Machine Identification
- Hostname: charnwood.ece.ncsu.edu
- CPU model (from `lscpu`/`/proc/cpuinfo`): Intel(R) Core(TM) i7-6700 CPU @ 3.40GHz (1 socket, 4 cores / 8 threads)
- ISA / architecture: x86-64
- Vendor / microarchitecture / codename (researched, NOT from cache tables): Intel Skylake (desktop), per `MACHINE_RESEARCH.md` Table 1
- Introduction year (per the team's stated year convention): 2015 (per `MACHINE_RESEARCH.md`)
- Process node (if reliably documented): 14 nm (per `MACHINE_RESEARCH.md`)
- Kernel version: Linux 6.8.0-101-generic (see `build/kernel_version.txt`)
- Page size: 4096 bytes (see `build/page_size.txt`)
- SMT siblings idle during runs? Yes for the pinned core: this session had `Cpus_allowed_list` 0-7 (all logical CPUs on this 4c/8t chip). Topology (`lscpu -e=CPU,CORE,SOCKET,NODE`): physical core 3 = logical CPUs {3,7}. Before and throughout every run, another logged-in user's process (`clclark7`, command name `associativity`, PID 982794) was pinned at ~100% CPU on logical CPU 5 (physical core 1, the sibling of CPU 1) — confirmed via repeated `mpstat -P ALL` sampling before the run and `ps`/`taskset` checks during it. Runs were pinned to CPU 3 (physical core 3, socket 0, NUMA node 0), a different physical core from the one in use by the other user; its SMT sibling CPU 7 was left idle. `who` showed no interactive login sessions at run time (15 users counted by `uptime` are stale/background sessions), but `ps`/`mpstat` showed the machine was not otherwise quiet — see "Known interference" below.

## Environment
- Compiler + version: GCC 13.3.0 (Ubuntu 13.3.0-6ubuntu2~24.04.1) (see `build/compiler_version.txt`)
- Compiler flags: `-O0 -g -std=c11 -Wall -Wextra -fno-omit-frame-pointer` (Makefile CFLAGS)
- Timer method used (RDTSC/RDTSCP+LFENCE, CNTVCT_EL0, etc.): x86 RDTSC (LFENCE-fenced start) / RDTSCP (LFENCE-fenced stop), batched: N=1000 dependent pointer-chase steps timed per start/stop pair, ticks/access = (t1-t0)/N. See `main_code/x86_64/timer_x86.h`, `main_code/common/benchmark.c`. Disassembly excerpt confirming the loop/timer placement survived -O0 unmodified: `build/cache_bench.source.dis` (functions `x86_tsc_start`, `x86_tsc_stop`, `measure_dependency_chain_batched`).
- Affinity/binding command used: `taskset -c 3 ./cache_bench ...` (see `scripts/run_capacity_full.sh` / `scripts/run_capacity_sweep.sh`)
- NUMA/locality method: no explicit NUMA pinning beyond CPU affinity; single-socket machine (1 NUMA node), so no cross-node concern. Not verified with `numastat` (Phase-I-safe; contains no cache-topology info, TODO if we want to confirm).
- Git commit hash of the code used for these results: 881fbfc00f6bf576dfbc35cf5d97ce2a1aa09ad9 (see `build/git_commit_at_run.txt`, recorded at build+run time)

## Per-Experiment Reproduction

### capacity/
- Source file(s): `main_code/common/{main.c,capacity.c,capacity.h,benchmark.c,benchmark.h,pointer_chase.c,pointer_chase.h,random.c,random.h}`, `main_code/x86_64/timer_x86.h`, `main_code/common/timer.h`
- Build command: `make` (from repo root; see `Makefile`)
- Run command + arguments:
  - **Automated pipeline** (coarse sweep, 1 KiB-64 MiB -> auto boundary detection -> dense +-3 octave sweep per boundary -> 2 repeats on deepest boundary -> 4x tail-extension sweep 64-256 MiB): `./scripts/run_capacity_full.sh charnwood 3 67108864`. Full transcript: `data_raw/charnwood/capacity/run_capacity_full_20260908T221801Z.log`.
  - **Manual follow-up** (the 64-256 MiB tail-extension was still climbing, not flat -- see below): one additional dense sweep 256 MiB-1 GiB plus 2 independent repeats, same flags as the pipeline's dense sweeps (`--points-per-octave 48 --samples 1000000 --batch-size 1000 --warmup-passes 3 --seed 12345 --min-bytes 268435456 --max-bytes 1073741824`, both patterns, `taskset -c 3`), run ad hoc (not via a script) at timestamp `20260908T230824Z`.
  - All runs pinned with `taskset -c 3`
- Sample count: 1,000,000 timed accesses per (size, pattern) point; warm-up (3 full untimed chase passes) excluded from that count
- Random seed(s): 12345 (xorshift32, `make_random_cycle`); sequential-pattern runs use `make_sequential_cycle` (no seed/randomness)
- Raw output filename(s): `data_raw/charnwood/capacity/capacity_coarse_{random,sequential}_20260908T221801Z.csv.gz`, `capacity_coarse_ext_{random,sequential}_20260908T221801Z.csv.gz` (64-256 MiB tail), `capacity_dense{0..5}_{random,sequential}_20260908T221801Z.csv.gz` (one dense window per auto-detected boundary), `capacity_dense5_rep{1,2}_{random,sequential}_20260908T221801Z.csv.gz` (repeats on deepest boundary), `capacity_denseTail_{random,sequential}_20260908T221801Z.csv.gz` (dense sweep past the deepest boundary, 64-256 MiB), `capacity_denseTail2{,_rep1,_rep2}_{random,sequential}_20260908T230824Z.csv.gz` (manual 256 MiB-1 GiB extension, main + 2 repeats). All gzipped (~9x smaller) before committing, per `.gitignore`; summarization was run on the uncompressed originals before compression, so summary CSVs in `data_processed/` are unaffected.
- Processing script -> data_processed path: `python3 scripts/summarize_raw.py <raw.csv> -o data_processed/charnwood/capacity/<name>_summary.csv` for each raw file above (run before gzipping), then `python3 scripts/detect_cache_hierarchy.py data_processed/charnwood/capacity/coarse_combined_random_summary.csv` for the first-pass boundary hypothesis, then `python3 scripts/plot_capacity.py data_processed/charnwood/capacity/*_summary.csv -o data_processed/charnwood/capacity/plots --machine charnwood --boundary 311744 --boundary 1923096 --boundary 2286960 --boundary 5931640 --boundary 7692384 --boundary 11863280` for the final curve and box-plot figures (re-run after the manual 1 GiB extension so the plots include it)
- Excluded runs (if any) and reason: none
- **Auto-detected boundaries** (from `detect_cache_hierarchy.py`, timing-only, on the coarse 1 KiB-256 MiB random-pattern data): 311,744 B (~304 KiB), 1,923,096 B (~1.83 MiB), 2,286,960 B (~2.18 MiB), 5,931,640 B (~5.66 MiB), 7,692,384 B (~7.34 MiB), 11,863,280 B (~11.31 MiB). The detector's naive per-boundary "L1..L6, Memory" labeling should **not** be taken at face value: this chip physically has only L1/L2/L3 (per later literature check in Phase II), so the 4 boundaries between ~1.83 MiB and ~11.31 MiB are very likely partly or wholly artifacts of the interference documented below, not 4 genuine additional cache levels. Only the ~304 KiB (L1) boundary showed low run-to-run spread (5%, 2 runs) in the box-plot check; every boundary from ~1.83 MiB through ~11.31 MiB showed 12-157% run-to-run spread with hundreds of outlier batches per point (see `plots/capacity_boxplots.png` annotations) -- these should be treated as unresolved/contaminated pending a re-run when the machine is quiet, not as confirmed cache-level transitions.

- **CORRECTION (2026-09-10, from already-committed coarse data -- no new runs
  needed): the "~304 KiB (L1)" label above is wrong.** Re-examining the full coarse
  random-pattern curve from 1 KiB through ~680 KiB (not just the narrow dense window
  immediately around 311,744 B) shows there is **no flat shelf anywhere between
  32,768 B and at least 679,912 B** -- it's one continuous, monotonic ramp (7.80
  ticks at 32,768 B up to 33.1 ticks at 679,912 B, noisier than the other machines
  in this exact range consistent with the interference documented below, but still
  clearly one climbing trend, not a step). 311,744 B is just an ordinary point on
  that ramp. The low run-to-run spread originally cited for it (5%, 2 runs) shows
  it was measured precisely, not that it sits at a real knee -- a smooth ramp can be
  measured precisely at any single point without that point being a boundary.
  What actually *is* a genuine flat plateau, missed by the original auto-detector
  run (same failure mode documented on Thunderbird -- no adjacent coarse point
  clears the default `--min-abs-ticks 3.0` even though the region is flat before and
  ramping after): **1,024-30,048 bytes, 26 points, 7.60-7.87 ticks/access** (noisier
  than Sunbird/Skylark/Crux's equivalent region -- consistent with this machine's
  already-documented shared-machine interference -- but still clearly flat, not
  trending), with the ramp clearly underway by 35,728 B (8.33). Sequential-pattern
  control at 32,768 vs. 35,728 B stays flat (7.882 vs 7.890 ticks), confirming this
  is a real random-access cache effect. **Corrected L1 estimate: 32,768 bytes
  (32 KiB)** -- same value independently found the same way on Sunbird
  (hand-confirmed via associativity), Crux, Skylark, Upgrade, and Ookay (see each
  machine's own README) -- consistent across 6 of this team's 7 x86 machines
  checked so far. **PROVISIONAL** (clean in the data; not yet cross-checked by an
  independent test). The already-documented contamination in the ~1.83-11.31 MiB
  region is unaffected by this correction and still needs the planned quiet re-run
  to resolve L2/L3 here -- **do not use 311,744 bytes as an L1 associativity
  stride on this machine; use 32,768 instead if/when associativity is run here.**
- **Known interference (confirmed, not just suspected):** another logged-in user's process (`clclark7`, PID 982794, command `associativity`) ran continuously at ~100% CPU on logical CPU 5 (a different physical core from the one used here) for the entire duration of both the automated pipeline and the manual follow-up. Despite correct core isolation (disjoint physical cores), this produced strong bimodal contamination in the random-pattern medians from ~1.8 MiB through ~20 MiB: many overlapping-window points show two well-separated median clusters (e.g. one cluster ~40-50 ticks, another ~200-250 ticks, at the *same* working-set size across different sweep passes) rather than a single noisy value, consistent with shared-L3/memory-bandwidth contention from the other user's benchmark rather than scheduling jitter alone (see `plot_capacity.py`'s per-point spread notes in the run log). This is the same *category* of multi-tenant interference documented on Sunbird, but here it is a real-time, sustained, identifiable contending process rather than transient OS scheduling noise, so no exact analogue of Sunbird's "different spike locations across independent repeats" argument was needed to demonstrate it -- the contending process was directly observed via `ps`/`mpstat` throughout.
- **Topmost-region plateau check:** the pipeline's default 64-256 MiB tail-extension sweep did *not* flatten -- median latency rose steadily from ~289 ticks (64-80 MiB) to ~321 ticks (203-256 MiB), an ~11% climb with no sign of leveling off, confirmed monotonic across 6 size buckets (see analysis notes below). Per project convention (mirroring the Sunbird follow-up), one additional manual dense sweep (256 MiB-1 GiB) plus 2 independent repeats was run to resolve this. Result: **the region from ~256-600 MiB does look like a genuine, reproducible plateau** (~320-335 ticks/access; run-to-run spread <5% across the 3 independent runs at most points in that band). However, **the climb does not fully stop by 1 GiB** -- mean per-bucket medians continue rising gently in the main run and rep1 (up to ~335-347 ticks by 800 MiB-1 GiB), and one of the two repeats (`rep2`) diverges sharply above ~700 MiB (up to 412 ticks by the 812-1024 MiB bucket, vs. ~330-337 for the main run and rep1 in the same range; run-to-run spread reaches 17-43% in that band). This late-onset, single-repeat divergence is most plausibly additional shared-machine memory-pressure interference (system swap was already 2.6-2.8 GiB in use out of 4 GiB total at run time, from other users' processes) rather than a cache-hierarchy effect, but it was not run down further -- per the pipeline's own non-adaptive design philosophy, this is flagged as **still open** rather than chased with further extensions. **Bottom line: no hard capacity plateau was reached within the swept range (up to 1 GiB); the gentle ~11-15% rise from ~12 MiB to ~600 MiB is reproducible and likely reflects real TLB/page-walk-driven latency growth as the working set exceeds TLB reach (to be confirmed in Phase II), while the instability above ~700 MiB is most likely shared-machine noise and needs a re-run on a quiet machine to resolve.**

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
