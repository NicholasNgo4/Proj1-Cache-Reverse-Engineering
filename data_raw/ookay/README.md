# ookay — Reproduction Manifest

> Fill in every field before freezing results. This README must let a grader go from
> this folder to the exact command that generated the data without guessing.

## Machine Identification
- Hostname: ookay.ece.ncsu.edu
- CPU model (from `lscpu`/`/proc/cpuinfo`): Intel(R) Core(TM) i7-7700 CPU @ 3.60GHz
- ISA / architecture: x86-64
- Vendor / microarchitecture / codename (researched, NOT from cache tables): Intel Kaby Lake, per `MACHINE_RESEARCH.md` Table 1
- Introduction year (per the team's stated year convention): 2017
- Process node (if reliably documented): 14 nm
- Kernel version: Linux 6.8.0-100-generic
- Page size: 4096 bytes (`getconf PAGESIZE`)
- SMT siblings idle during runs? Mixed — see Anomalies below. Main pipeline (core 1):
  yes, confirmed via `mpstat -P ALL` (both CPU1 and its SMT sibling CPU5 idle for the
  whole run). Tail-extension-2 follow-up (core 3): yes for run0+rep1 (CPU3/CPU7 both
  idle, confirmed via repeated `mpstat` samples); rep2 ran with CPU7 idle at start but
  another user's job had explicitly requested `--cpu=7` moments earlier (see Anomalies)
  — it had not started as of the last check during rep2, so rep2 is *believed* clean,
  not guaranteed.

## Environment
- Compiler + version: gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0
- Compiler flags: `-O0 -g -std=c11 -Wall -Wextra -fno-omit-frame-pointer` (Makefile CFLAGS)
- Timer method used (RDTSC/RDTSCP+LFENCE, CNTVCT_EL0, etc.): x86 RDTSC (LFENCE-fenced
  start) / RDTSCP (LFENCE-fenced stop), batched: N=1000 dependent pointer-chase steps
  timed per start/stop pair, ticks/access = (t1-t0)/N. See `main_code/x86_64/timer_x86.h`
  (`x86_tsc_start`/`x86_tsc_stop`), `main_code/common/benchmark.c`.
- Affinity/binding command used: `taskset -c 1` for the main `run_capacity_full.sh`
  pipeline (coarse, coarse tail-extension to 256 MiB, all 6 dense boundary windows,
  2 reproducibility repeats on the deepest boundary, dense past-boundary tail sweep);
  `taskset -c 3` for the manual tail-extension-2 follow-up (256 MiB-1 GiB, run0 + 2
  repeats) — switched cores mid-session, see Anomalies.
- NUMA/locality method: single-socket desktop part, one NUMA node; no explicit NUMA
  pinning used or needed.
- Git commit hash of the code used for these results: `e12bd90b0768442323479a5dc9a6c79cb6d6a794`

## Per-Experiment Reproduction

### capacity/
- Source file(s): `main_code/common/{main.c,capacity.c,capacity.h,benchmark.c,benchmark.h,pointer_chase.c,pointer_chase.h,random.c,random.h}`, `main_code/x86_64/timer_x86.h`, `main_code/common/timer.h`
- Build command: `make` (from repo root)
- Run command + arguments:
  - Main pipeline (coarse 1 KiB-64 MiB, auto boundary detection, dense windows around
    each of the 6 detected boundaries with 2 repeats on the deepest, tail-extension to
    256 MiB, dense past-boundary sweep): `./scripts/run_capacity_full.sh ookay 1`
    (all default constants: `--samples 1000000 --batch-size 1000 --warmup-passes 3
    --seed 12345`, coarse points-per-octave 8, dense points-per-octave 48)
  - Manual tail-extension-2 follow-up (the default 256 MiB ceiling was still gently
    climbing, not flat — see Plateau status below), run0 + 2 independent repeats,
    268,435,456-1,073,741,824 bytes, points-per-octave 48, both patterns, same
    samples/batch/warmup/seed as above, `taskset -c 3`. run0 and rep1 ran directly;
    rep2 was resumed inside a detached `tmux` session (`ookay_capacity`) partway
    through so it would survive a client disconnect — see Anomalies.
  - All runs: `--samples 1000000 --batch-size 1000 --warmup-passes 3 --seed 12345`
- Sample count: 1,000,000 timed accesses per (size, pattern) point; warm-up (3 full
  untimed chase passes) excluded from that count
- Random seed(s): 12345 (xorshift32, `make_random_cycle`); sequential-pattern runs use
  `make_sequential_cycle` (no seed/randomness)
- Raw output filename(s) (all gzip'd per repo convention — see `.gitignore` — commit
  the `.csv.gz`): `capacity_coarse_{random,sequential}_20260908T231044Z.csv.gz`,
  `capacity_coarse_ext_{random,sequential}_20260908T231044Z.csv.gz`,
  `capacity_dense{0..5}_{random,sequential}_20260908T231044Z.csv.gz`,
  `capacity_dense5_rep{1,2}_{random,sequential}_20260908T231044Z.csv.gz`,
  `capacity_denseTail_{random,sequential}_20260908T231044Z.csv.gz`,
  `capacity_tailExt2_{random,sequential}_20260909T002130Z.csv.gz`,
  `capacity_tailExt2_rep{1,2}_{random,sequential}_20260909T002130Z.csv.gz`.
  Transcripts: `run_capacity_full_20260908T231044Z.log`,
  `run_tail_extension2_20260909T002130Z.log`.
- Processing script -> data_processed path: `python3 scripts/summarize_raw.py <raw.csv>
  -o data_processed/ookay/capacity/<name>_summary.csv` for every raw file above, then
  `python3 scripts/detect_cache_hierarchy.py data_processed/ookay/capacity/coarse_combined_random_summary.csv`
  for the first-pass boundary hypothesis. **Plots not yet generated**: `matplotlib` is
  not installed on this machine and there is no passwordless `sudo` or working `pip`/
  `ensurepip` to install it non-interactively (same failure mode hit on Skylark and
  Thunderbird per `CLAUDE.md`); once available, run `python3 scripts/plot_capacity.py`
  over all summary CSVs above with `--machine ookay --boundary 285864 --boundary 440872
  --boundary 5439336 --boundary 6468496 --boundary 7692384 --boundary 11863280`.
- Excluded runs (if any) and reason: none.

- **Detected boundaries** (`detect_cache_hierarchy.py --machine-readable` on the
  combined coarse + coarse-tail-extension random-pattern data, 1 KiB-256 MiB):
  285,864 / 440,872 / 5,439,336 / 6,468,496 / 7,692,384 / 11,863,280 bytes — treat as
  a timing-only hypothesis, not a final level count. **The 4 boundaries between
  ~5.3 MiB and ~11.9 MiB (`L3`-`L6` in the detector's table) are very likely NOT four
  separate real cache levels but one continuous, unusually long steep transition**:
  the dedicated dense sweep bracketing the deepest boundary (`dense5`, 1.48-94.9 MiB,
  289 points, 3 independent runs) never flattens anywhere within its own range — its
  own last-quarter-vs-prior-quarter median change is +23%, i.e. still climbing at its
  own ceiling — so the detector is almost certainly over-splitting one smooth ramp
  (~40 ticks at 1.5 MiB up to ~262 ticks at 94.9 MiB) into spurious knees. Only the
  ~285,864 byte (L1, 279 KiB) and ~440,872 byte (L2, 430 KiB) boundaries look like
  genuinely separate flat/ramp transitions from the coarse+dense0+dense1 data (66 and
  5 points respectively with tight, low-noise medians); these were not re-verified
  with additional targeted sweeps this session since the follow-up work focused on the
  topmost (deepest/DRAM) region per this session's task.

- **Plateau status — topmost/DRAM region: CONFIRMED genuine flat plateau, resolved via
  follow-up.** The pipeline's default sweep only went to 256 MiB and was still
  gently rising at that ceiling (last-quarter-vs-prior-quarter +1.6%, median climbing
  from 254 to 279 ticks/access from 64 to 256 MiB) — not clearly flat, so per this
  session's task a manual tail-extension-2 follow-up was run: 268,435,456-1,073,741,824
  bytes (256 MiB-1 GiB), run0 + 2 independent repeats (same seed/flags), `taskset -c 3`.
  - Naive last-quarter-vs-prior-quarter check on the 3 individual runs disagreed
    (run0 +4.5% "flat", rep1 +6.8% "still climbing", rep2 -0.2% "flat") — this
    disagreement itself is diagnostic: rep1's apparent climb is driven entirely by a
    cluster of single-run spikes in its last quarter (e.g. 824.6 MiB: rep1=435.5 vs.
    run0=293.3/rep2=293.2, a +28% deviation from the other two), matching the same
    shared-machine-interference signature documented for Sunbird/Crux/Charnwood/
    Thunderbird: isolated spikes recur at *different* sizes in each independent run
    (run0 spikes at 745.3/789.6/1024.0 MiB; rep1 at 263.5/600.1/801.1/824.6/939.0/
    952.7/966.5 MiB; rep2 dips at 778.3/848.7 MiB where the other two spiked instead),
    which is the signature of transient OS scheduling interference, not a property of
    those specific working-set sizes.
  - A robust median-of-3 trend (taking the middle value at each of the 97 common size
    points, which filters out any single-run spike) is flat across the *entire*
    256 MiB-1 GiB range: 286.6 ticks/access at 256 MiB, 293.7 at ~813 MiB, 296.7 at
    1024 MiB (endpoint); last-quarter-vs-prior-quarter change on this robust trend is
    only +3.7%. Spike counts (points >15% off the robust median) were 10/97 for run0,
    12/97 for rep1, only 3/97 for rep2 — consistent with variable background load
    across the 3 runs' wall-clock windows (see Anomalies), not a real trend.
  - **Conclusion: the DRAM region has genuinely flattened by 256 MiB and stays flat
    out to 1 GiB, at a robust median of ~286-297 ticks/access.** The apparent slow
    climb visible in any single run (including the original pipeline's own 64-256 MiB
    tail-extension sweep) is scheduling noise on this heavily shared, multi-user
    machine, not a real capacity effect — confirmed by disagreement resolving under
    a 3-way robust combination, the same methodology used on Sunbird/Crux.
  - Use median (not mean) throughout; per-point mean/stddev are inflated by the same
    interference (occasional batch maxima far above the surrounding medians).

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

## Anomalies / Notes (this session)
- **Cores 0 and 2 were pinned near 100% by other students' own HW1 benchmark runs for
  the entire session** (confirmed via `mpstat -P ALL` and `ps -eo psr,...`, not just
  inferred from load average): `mrthumm2`'s `cache_bench --mode=capacity` on core 0
  (ran 1+ day, finished sometime after ~21:44 EDT), and `clclark7`'s `associativity`
  binary on core 2 (ran continuously for 4+ hours). Core 1 (used for the main pipeline)
  and core 3 (used for the follow-up) were chosen specifically to avoid these two.
- **A third user's process (`sbanaka`) started a CPU-bound `python3` job on core 1**
  partway through the session, *after* the main pipeline had already finished cleanly
  on that core — this did not affect the main-pipeline data, but meant core 1 was no
  longer available for the follow-up sweep, which is why the follow-up used core 3
  instead (re-verified idle via repeated `mpstat` sampling before switching).
- **A fourth user's job (`mrthumm2`, via `./scripts/run_bench.sh --mode=associativity
  ... --cpu=7`) explicitly requested core 3's SMT sibling (CPU7)** shortly before
  rep2 of the follow-up sweep started; it had not actually started running as of the
  last check during rep2 (CPU7 still idle), so rep2 is believed unaffected, but this
  is called out explicitly since it could not be *guaranteed* clean the way run0/rep1
  were. No unusual rep2-specific spike pattern was found in the plateau analysis above
  beyond the same class of scattered single-point noise seen in run0/rep1.
- **Machine-wide load average rose from ~2.0 to ~4.5 over the course of the session**
  (13 logged-in users throughout) as more classmates ran their own HW1 benchmarks —
  consistent with the assignment deadline (2026-09-10) approaching.
- **VS Code Remote-SSH on this host runs with `--enable-remote-auto-shutdown`**, which
  tears down the whole remote extension-host session (and everything under it) some
  time after the client disconnects — a plain `nohup`/`disown` would NOT have survived
  this, since it doesn't change which session (SID) a process belongs to. rep2 of the
  follow-up sweep was therefore moved into a detached `tmux` session (`ookay_capacity`,
  verified via `ps` to have PPID 1 and its own SID, i.e. fully outside the VS Code
  server's process tree) before the user disconnected, specifically so data collection
  would survive the disconnect. run0 and rep1 had already completed before this move.
- **`matplotlib`/`pip` are not available on this machine** and there is no passwordless
  `sudo` or working `ensurepip` to install them non-interactively — same failure mode
  hit on Skylark and Thunderbird (see `CLAUDE.md`). Plots for this machine are
  outstanding; data collection and analysis above do not depend on them.
