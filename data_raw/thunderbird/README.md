# thunderbird — Reproduction Manifest

> Fill in every field before freezing results. This README must let a grader go from
> this folder to the exact command that generated the data without guessing.

## Machine Identification
- Hostname: thunderbird.ece.ncsu.edu
- CPU model (from `lscpu`/`/proc/cpuinfo`): Ampere Q80-30 (`lscpu` model name: Neoverse-N1), 80 cores, 1 socket
- ISA / architecture: aarch64
- Vendor / microarchitecture / codename (researched, NOT from cache tables): Ampere / ARM Neoverse N1, per `MACHINE_RESEARCH.md`
- Introduction year (per the team's stated year convention): 2020 (per `MACHINE_RESEARCH.md`)
- Process node (if reliably documented): 7 nm (per `MACHINE_RESEARCH.md`)
- Kernel version: Linux 5.14.0-611.54.1.el9_7.aarch64
- Page size: 4096 bytes (`getconf PAGESIZE`)
- SMT siblings idle during runs? N/A — `lscpu` reports "Thread(s) per core: 1" for this CPU (no SMT). This session's cgroup grants `Cpus_allowed_list: 0-4` only (not the full 0-79); of those, cores 1 and 2 were occupied by other students' active processes (`python3` at ~80% CPU, a process named `associativity` at 100% CPU) at the time of core selection — confirmed via `/proc/stat` idle-time sampling, not just a `ps` snapshot. Ran on core 3, which showed near-100% idle time before the run.

## Environment
- Compiler + version: GCC 11.5.0 (Red Hat 11.5.0-14)
- Compiler flags: `-O0 -g -std=c11 -Wall -Wextra -fno-omit-frame-pointer`
- Timer method used (RDTSC/RDTSCP+LFENCE, CNTVCT_EL0, etc.): ARM `CNTVCT_EL0` (DSB+ISB fenced start/stop), batched: N=1000 dependent pointer-chase steps timed per start/stop pair, ticks/access = (t1-t0)/N. See `main_code/aarch64/timer_arm.h`, `main_code/common/benchmark.c`. **Pre-flight sanity check (not committed, ad hoc):** `CNTFRQ_EL0` = 25,000,000 Hz (40 ns/tick resolution), confirmed readable unprivileged and monotonic across repeated reads, and a manual 8-trial/100,000-step dependent chase over a 4096-node (L1-resident) ring gave consistent ~3.3 ns/step — non-zero, non-negative, not erratic. This 40 ns/tick resolution is coarse relative to individual accesses, but the benchmark's batching (dividing total ticks by N=1000+ steps) makes per-access quantization error negligible; see "Known issues" below for a downstream consequence of this coarse resolution.
- Affinity/binding command used: `taskset -c 3 ./cache_bench ...` (see `scripts/run_capacity_full.sh` and the manual follow-up described below)
- NUMA/locality method: no explicit NUMA pinning beyond CPU affinity; single NUMA node (node0, all 80 CPUs) per `lscpu -e=CPU,CORE,SOCKET,NODE`, so first-touch locality is moot on this machine.
- Git commit hash of the code used for these results: `881fbfc00f6bf576dfbc35cf5d97ce2a1aa09ad9` (recorded at README-fill time; the actual runs spanned this and the immediately preceding commit — no code changes to `main_code/` occurred during the session)

## Per-Experiment Reproduction

### capacity/
- Source file(s): `main_code/common/{main.c,capacity.c,capacity.h,benchmark.c,benchmark.h,pointer_chase.c,pointer_chase.h,random.c,random.h}`, `main_code/aarch64/timer_arm.h`, `main_code/common/timer.h`
- Build command: `make` (from repo root; see `Makefile`)
- Run command + arguments:
  - `scripts/run_capacity_full.sh thunderbird 3` — ran the coarse sweep (1 KiB-64 MiB) and its tail extension (64 MiB-256 MiB) successfully, but its automatic boundary detection returned **no boundaries** (see "Known issues" below), so its own dense-sweep/repeat/plot stages never ran and it exited with a `matplotlib`-missing error at the plotting step.
  - Everything past the coarse+tail stage was completed manually, using the same `taskset -c 3 ./cache_bench --experiment capacity ...` invocation pattern with `--samples 1000000 --batch-size 1000 --warmup-passes 3 --seed 12345`, both `--pattern random` and `--pattern sequential`:
    - Dense window A (L1-plateau edge / start of ramp): `--min-bytes 12288 --max-bytes 786432 --points-per-octave 48`
    - Dense window B (dominant steep transition + a noisy zone): `--min-bytes 4194304 --max-bytes 268435456 --points-per-octave 48`, plus 2 independent repeats of the identical command (reproducibility check on the noisiest region, same rationale as Sunbird's window C)
    - Tail-extension window (checking whether the curve actually plateaus past the original 256 MiB coarse ceiling): `--min-bytes 268435456 --max-bytes 1073741824 --points-per-octave 48`, plus 2 independent repeats (the last 2 of these were run inside a detached `tmux` session, `data_raw/thunderbird/capacity/tail_repeats.sh`, for resilience against the remote session restarting mid-run — see that script for the exact resumed commands)
- Sample count: 1,000,000 timed accesses per (size, pattern) point; warm-up (3 full untimed chase passes) excluded from that count
- Random seed(s): 12345 (xorshift32, `make_random_cycle`); sequential-pattern runs use `make_sequential_cycle` (no seed/randomness)
- Raw output filename(s): `data_raw/thunderbird/capacity/capacity_coarse_{random,sequential}_20260909T001422Z.csv.gz`, `capacity_coarse_ext_{random,sequential}_20260909T001422Z.csv.gz`, `capacity_denseA_{random,sequential}_20260909T001422Z.csv.gz`, `capacity_denseB_{random,sequential}_20260909T001422Z.csv.gz`, `capacity_denseB_rep{1,2}_{random,sequential}_20260909T001422Z.csv.gz`, `capacity_denseTail_{random,sequential}_20260909T001422Z.csv.gz`, `capacity_denseTail_rep{1,2}_{random,sequential}_20260909T001422Z.csv.gz` (gzipped after the fact per the repo-wide `.gitignore` convention — ~9-10x smaller measured on this data; summaries in `data_processed/` were already generated from the uncompressed originals before compression, so they're unaffected — `zcat`/`gunzip` a file to inspect the raw per-batch rows). Full transcript (kept uncompressed per `.gitignore`'s `!data_raw/**/*.log` rule): `run_capacity_full_20260909T001422Z.log` (automated portion) and `manual_followup_20260909T001422Z.log` (everything after boundary detection returned nothing).
- Processing script -> data_processed path: `python3 scripts/summarize_raw.py <raw.csv> -o data_processed/thunderbird/capacity/<name>_summary.csv` for each file above (run against the uncompressed CSVs before they were gzipped), then `python3 scripts/plot_capacity.py <all summary.csv...> -o data_processed/thunderbird/capacity/plots --machine thunderbird --boundary 65536 --boundary 33554432 --boundary 268435456` for the final curve and box-plot figures. The 3 `--boundary` values (64 KiB, 32 MiB, 256 MiB) were picked by eye from the dense data (see "Known issues"), not from `detect_cache_hierarchy.py`'s output.
- Excluded runs (if any) and reason: none — all raw files listed above are included in the final plots.

- **Known issues / methodology notes (read before trusting any boundary number at face value):**
  1. **`detect_cache_hierarchy.py`'s default thresholds do not work on this machine's counter.** Its default `--min-abs-ticks 3.0` was implicitly calibrated to x86 TSC-scale ticks (Sunbird's ticks/access run in the tens-to-hundreds). Thunderbird's `CNTVCT_EL0` runs at only 25 MHz, so ticks/access over the *entire* 1 KiB-1 GiB range are just ~0.08-2.4 — the absolute-tick threshold is unreachable regardless of `--rel-threshold`, so the detector silently printed zero boundaries instead of erroring, and `run_capacity_full.sh`'s dense-sweep-per-boundary loop consequently never ran. Loosening `--min-abs-ticks` to compensate (tried `--min-abs-ticks 0.02 --rel-threshold 0.15`) does not give a clean answer either: this machine's curve is a smooth continuous ramp rather than discrete steps, so the detector's "consecutive points must not regress" rule over-fragments it into ~8 spurious "levels" instead of the true handful of transitions. **All boundary values used for dense-sweep windows and plot annotations here were chosen by eyeballing the coarse-then-dense plots, not from this script's output.** This is a real bug/limitation in the shared script worth fixing later (e.g. a threshold relative to `CNTFRQ_EL0` instead of an absolute tick count), not just a Thunderbird-specific quirk — flagged in `CLAUDE.md` for whichever machine hits it next.
  2. **`matplotlib`/`numpy` were not installed** for this user on Thunderbird, so `run_capacity_full.sh` died at its final plotting step even though all the sweep data it collected was fine. Fixed with `python3 -m pip install --user matplotlib numpy`.
  3. **Curve shape is genuinely different from Sunbird's (3 flat/ramp transitions).** Thunderbird shows: a flat plateau from 1 KiB to ~64-75 KiB (~0.084 ticks / ~3.4 ns, matches the L1-resident sanity-check number above); a long, shallow, continuous ramp from ~75 KiB up through ~8 MiB (no flat shelf); a steep, dominant climb from ~16 MiB to ~60 MiB (0.8 to ~2.1 ticks); a visibly noisy ~16-70 MiB zone (individual points show 20-65% run-to-run spread across the denseB + 2 repeats, even after averaging — see `capacity_boxplots.png`); then a slow continued climb from ~70 MiB to ~256 MiB before finally flattening. **The topmost region was explicitly checked for a genuine plateau, not assumed:** across the 256 MiB-1 GiB tail-extension window (97 points x 3 independent runs = the main sweep + 2 repeats), run-to-run spread averages ~2.0% (comparable to Sunbird's confirmed-plateau spread of ~3.6%, under 2% at many points), and the residual growth from the first quarter of that range to the last quarter is only +3.4% over a 4x size increase — this is a confirmed flat DRAM-latency plateau at ~2.3-2.4 ticks/access (~92-96 ns/access), not a region still climbing. The noisy 16-70 MiB zone, by contrast, is a real transition-region property (like Sunbird's 19-25 MiB zone), not something more averaging alone cleans up — treat any single-run boundary estimate inside that zone as unreliable.
  4. Noise in the 16-70 MiB zone is consistent with transient scheduling interference on this shared, multi-user machine (this session only had exclusive-in-practice use of core 3; cores 1-2 in the allowed cpuset were actively used by other students during setup), matching the same kind of finding Sunbird's README documents in more detail for its own transition region.
- `scripts/plot_capacity.py` combines overlapping (pattern, size) rows across the coarse/dense/repeat inputs by averaging medians and widening whiskers to the union of p5/p95, annotating each combined box with the number of runs and their run-to-run spread — the terminal output from the final `plot_capacity.py` call (not separately saved as a file) lists every point it combined, most of them exactly the noisy 16-70 MiB points described above.

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
- Reserved core/package: core 3 (of `Cpus_allowed_list: 0-4` granted to this session)
- Time window: 2026-09-08 ~20:14 UTC - ~23:14 UTC
