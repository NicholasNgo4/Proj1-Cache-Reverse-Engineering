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
- Source file(s): `main_code/common/{main.c,associativity.c,associativity.h,benchmark.c,benchmark.h,pointer_chase.c,pointer_chase.h,random.c,random.h}`, `main_code/aarch64/timer_arm.h`, `main_code/common/timer.h`
- Build command: `make` (from repo root)
- Run command + arguments: `scripts/run_associativity_full.sh thunderbird 4 65536,1048576,31457280` — explicit `cache_bytes` override (required by the script for a "final" run; auto-detect is opt-in only), values taken from this team's consolidated `CAPACITY_RESULTS.md` (L1=64 KiB, L2=1 MiB, LLC≈30 MiB) per that file's own instruction that it, not the older per-level `CAPACITY_INFERENCE_STATUS.md` confidence gate, is the source to use for this run. Core 4 was selected after an idle-time check (`/proc/stat` sampled over 1s, `mpstat` unavailable on this machine): cores 0-4 of this session's `Cpus_allowed_list: 0-4` cgroup were all lightly loaded by this session's own IDE/tooling processes (no other students' processes observed), core 4 was the quietest (~1% busy). One command ran the full pipeline for all 3 levels: base sweep `num_ways=2-40` (both patterns) → automatic knee detection → 2 reproducibility repeats (seeds 12346, 12347) → plots, per level.
- Sample count: 1,000,000 timed accesses per (num_ways, pattern) point; warm-up (3 full untimed chase passes) excluded
- Random seed(s): base=12345, repeats=12346/12347 (`make_random_cycle_strided`); sequential-pattern runs use `make_sequential_cycle_strided` (no seed)
- Conflict-set construction method: node-to-node stride fixed at the level's own capacity (`--cache-bytes`, validated only as a multiple of the 4096 B page size, NOT required to be a power of two — see `main_code/common/main.c`/`associativity.h`), so every probed node collides into the same cache set by construction regardless of unknown line size/way count; `num_ways_probed` swept 2-40, `--way-step 1`.
- Raw output filenames: `data_raw/thunderbird/associativity/{L1,L2,L3_LLC}/associativity_{base,rep1,rep2}_{random,sequential}_20260912T224539Z.csv.gz`; full transcript `data_raw/thunderbird/associativity/run_associativity_full_20260912T224539Z.log`.
- Processing: `scripts/summarize_raw.py` per raw CSV -> `data_processed/thunderbird/associativity/<level>/{base,rep1,rep2}_{random,sequential}_summary_20260912T224539Z.csv`; plots regenerated by hand (not the pipeline's own auto call) via `scripts/plot_associativity.py` with an explicit `--estimate`, for the reason in note 1 below.

- **Known issues / methodology notes (read before citing any of these numbers):**
  1. **`detect_associativity.py`'s default `--min-abs-ticks 3.0` is unreachable on this machine, same root cause as the capacity detector's documented failure (`CAPACITY_INFERENCE_STATUS.md`).** `CNTVCT_EL0` at 25 MHz keeps every level's ticks/access under ~1.1 across the whole `num_ways=2-40` range, so the pipeline's automatic detection returned "none" (reproducibly, across base+both repeats) for all 3 levels on the first pass. Re-ran `detect_associativity.py` by hand per level with a rescaled `--min-abs-ticks` chosen by eye from that level's own curve (see note 2 for why the value differs per level) — analogous to the `--min-abs-ticks 0.5` fix already documented for capacity, just needing a smaller value here since associativity's ticks/access are themselves smaller than capacity's.
  2. **L2 and LLC's detected "knees" are very likely the same universal large-stride confound already documented at length in `CLAUDE.md`'s associativity section (Sunbird + Upgrade, 2026-09-11/12), not each level's real associativity — treat both as unresolved, not just L1 as confirmed.** All three levels' curves show the *same* small first bump at `num_ways=5` (baseline ~0.08-0.13 ticks -> ~0.16-0.23 ticks): expected for L1 (`cache_bytes=65536` is exactly this level's own capacity), but this bump also appears at L2 (`cache_bytes=1048576`) and LLC (`cache_bytes=31457280`) — both are exact multiples of 65536 (16x and 480x respectively), so a stride of L2's or LLC's own capacity *also* lands every probed node in the same L1 set, re-triggering L1's own thrashing limit as a spurious low-`num_ways` step in what's supposed to be a higher-level sweep. Using a `--min-abs-ticks` high enough to skip that spurious bump (0.25 for L2, 0.2 for LLC) does surface a second, much larger knee — but that knee lands at essentially the *same* `num_ways` (L2: base=11-way, both repeats=12-way; LLC: 10-way, fully reproducible across base+both repeats) and the *same* post-knee plateau magnitude (~0.8 ticks) for both L2 and LLC, despite L2 and LLC differing by 30x in byte capacity. This is the exact "two structurally different levels break at the same num_ways regardless of a large change in byte capacity" signature that `CLAUDE.md` already used to establish, on Sunbird and Upgrade (both x86), that any stride above roughly 1 MiB cannot currently distinguish real L2/LLC associativity from a small, fixed, page-count-limited structure (~9-10 slots there, likely TLB/page-walk-cache-related, not proven) — this Thunderbird run reproduces the same phenomenon at ~10-12 slots on a third machine and a different architecture (ARM, not x86), which is new cross-architecture evidence the confound isn't x86-DTLB-microarchitecture-specific, though it is NOT proof the exact same mechanism or slot count applies here (different CPU, no PMU cross-check yet). **Only L1's result (4-way) should be treated as reasonably solid** (clean single knee, no competing lower-level artifact possible since L1 is the smallest level tested, reproducible across base+both repeat seeds — small-stride L1 results are the one case not yet implicated by this confound, per the same caveat `CLAUDE.md` already applies to Sunbird's own L1 result). L2's and LLC's numbers below are reported because the pipeline was run and the graphs were requested, not because they're believed to be correct. This run used the plain fixed-full-capacity-stride method only; `CLAUDE.md` documents a more rigorous "derived-stride scan" technique (`scripts/run_associativity_stride_scan.sh`, validated on Upgrade) that has NOT been tried on this machine — that, or Phase II PMU verification, is the natural next step before citing an L2/LLC number here.
  3. Per-level results (random-pattern base sweep, thresholds as in note 1; reproducibility repeats used the same threshold as the base sweep for that level):
     - **L1** (`cache_bytes=65536`, `--min-abs-ticks 0.05`): estimated **4-way**, identical across base + both repeats (seeds 12345/12346/12347). Flat plateau ~0.13 ticks through `num_ways=4`, jumps to ~0.23 ticks at `num_ways=5`.
     - **L2** (`cache_bytes=1048576`, `--min-abs-ticks 0.25`, after skipping the L1-artifact bump per note 2): base sweep = **11-way**, both repeats = **12-way** (off-by-one, not perfectly reproducible — see note 2 for why this number shouldn't be over-trusted regardless).
     - **LLC** (`cache_bytes=31457280`, `--min-abs-ticks 0.2`, after skipping the L1-artifact bump per note 2): estimated **10-way**, identical across base + both repeats.
  4. Sequential-pattern control tracks the randomized-chain curve closely at every level (no divergence that would suggest a hardware prefetcher masking the knees), except L1's sequential control shows an additional, unexplained jump at `num_ways=37-40` that the randomized chain does not show at all (randomized stays flat ~0.15 through `num_ways=40`) — visible in `data_processed/thunderbird/associativity/L1/plots/associativity_curve.png`, not yet investigated, does not affect the 4-way estimate (well past it).

### latency/
- Source file(s):
- Run command + arguments:
- Dependent-chain batch size N used:
- Regular vs. randomized control included?

### inclusion_policy/
- Source file(s):
- Run command + arguments:
- Eviction/reload construction:

### pmu/ (Phase II — started 2026-09-13, after tagging `phase1-timing-only` at commit `7be6dac`)
- `perf list` output filename: `data_raw/thunderbird/pmu/perf_list_20260913.txt` (also
  the full `armv8_pmuv3_0` raw event list from
  `/sys/bus/event_source/devices/armv8_pmuv3_0/events/`); system-reported cache
  topology (`lscpu -C`, sysfs) saved separately at
  `data_raw/thunderbird/pmu/sysfs_cache_topology_20260913.txt`.
- Events collected + exact semantics on this CPU: raw `armv8_pmuv3_0` architected
  ARMv8 PMUv3 cache events — `l1d_cache`/`l1d_cache_refill`,
  `l2d_cache`/`l2d_cache_refill`, `l3d_cache`/`l3d_cache_refill` (the `_cache` event
  counts attributable accesses at that level, `_refill` counts linefills i.e.
  misses), plus `mem_access`/`bus_access` and generic `cache-references`/
  `cache-misses` as a cross-check. Full per-level miss-rate results, PMU-vs-Phase-I
  comparison, and the required Table 2 are in `PHASE2_VALIDATION.md` (Thunderbird
  section) — not duplicated here to avoid the two documents drifting apart.
- Run command + arguments: `data_raw/thunderbird/pmu/run_pmu_sweep.sh 3
  data_raw/thunderbird/pmu/pmu_sweep_raw.csv` — reuses the Phase-I `cache_bench
  --experiment capacity` binary at one working-set size per invocation
  (`--samples 1000000 --pattern random --seed 12345`, same as Phase I), swept across
  23 sizes (4 KiB–512 MiB) under `perf stat`, core 3 (idle-checked via `/proc/stat`
  first, 96.5% idle). Raw: `data_raw/thunderbird/pmu/pmu_sweep_raw.csv`; processed:
  `data_processed/thunderbird/pmu/pmu_sweep_summary.csv`; plot:
  `data_processed/thunderbird/pmu/plots/pmu_miss_rate_sweep.{png,pdf}`.
- Literature references used: Ampere Altra Datasheet Rev A1 v1.30 (2022-07-28)
  §2.3–2.5 pp.9; Arm Neoverse N1 Core TRM r3p1 (100616_0301_01_en) §A2.1.2/A6.4/A7.1
  — full citations and the per-level Agreement analysis are in `PHASE2_VALIDATION.md`.

## Reservation Log (if applicable)
- Reserved core/package: core 3 (of `Cpus_allowed_list: 0-4` granted to this session)
- Time window: 2026-09-08 ~20:14 UTC - ~23:14 UTC
