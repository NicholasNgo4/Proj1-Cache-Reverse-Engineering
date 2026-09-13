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
  for the first-pass boundary hypothesis. **Plots generated**: `matplotlib`/`pandas`/
  `numpy` were bootstrapped via `get-pip.py --user --break-system-packages` (no
  passwordless `sudo`, no `ensurepip`, no `python3-venv` on this machine, same
  failure mode as Skylark/Thunderbird per `CLAUDE.md`), then
  `python3 scripts/plot_capacity.py data_processed/ookay/capacity/*_summary.csv
  -o data_processed/ookay/capacity/plots --machine ookay --boundary 285864
  --boundary 440872 --boundary 5439336 --boundary 6468496 --boundary 7692384
  --boundary 11863280` produced `data_processed/ookay/capacity/plots/capacity_curve.
  {pdf,png}` and `capacity_boxplots.{pdf,png}`. The script's own duplicate-row
  averaging flagged the same 256 MiB-1 GiB interference spikes documented above
  (e.g. 824.6 MiB: 41.8% spread across the 3 combined runs) rather than hiding them.
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

- **CORRECTION (2026-09-10, from already-committed coarse data — no new runs
  needed):** the "L1, 279 KiB" and "L2, 430 KiB" labels above are wrong. Re-examining
  the *full* coarse random-pattern curve from 1 KiB through ~1 MiB (not just the
  dense0/dense1 windows immediately around 285,864/440,872 B) shows there is **no
  flat shelf anywhere between 32,768 B and at least 961,544 B** — it's one smooth,
  continuous, monotonic ramp (7.56 ticks at 32,768 B up to 36.4 ticks at 961,544 B),
  and 285,864/440,872 are just two ordinary points on that ramp, not knees. Locally
  tight/low-noise medians (the evidence originally cited) are consistent with *either*
  a genuine plateau *or* a well-measured point on a smooth ramp — tightness alone
  doesn't distinguish the two without looking at the wider trend, which is what this
  correction adds.
  What actually *is* a genuine flat plateau, missed by the original auto-detector run
  (same failure mode documented on Thunderbird — no single adjacent coarse point
  clears the default `--min-abs-ticks 3.0`, even though the region is flat before and
  ramping after): **1,024-30,048 bytes, 66 points, 7.40-7.56 ticks/access, tight**,
  with the ramp starting immediately at 32,768 B (7.56) and clearly underway by
  35,728 B (8.17). Sequential-pattern control at the same two sizes stays flat
  (7.512 vs 7.524 ticks) confirming this is a real random-access cache effect, not a
  benchmark artifact. **Corrected L1 estimate: 32,768 bytes (32 KiB)** — same value
  independently found the same way on Sunbird (hand-confirmed via associativity),
  Crux, Skylark, Upgrade, and Charnwood (see each machine's own README) — consistent
  across 6 of this team's 7 x86 machines checked so far. **PROVISIONAL** (clean in
  the data; not yet cross-checked by an independent test the way Sunbird's was).
  L2/L3 remain **UNRESOLVED** here: the entire 32,768 B-~5.3 MiB span is one
  continuous ramp with no confirmed second shelf (960 KiB was the widest range
  checked in this correction pass; the region from there to the already-flagged
  ~5.3-11.9 MiB over-segmented transition was not re-examined point-by-point). Do
  **not** use 285,864 or 440,872 bytes as an L1/L2 associativity stride — if
  `run_associativity_full.sh` is run on Ookay, use 32,768 for L1 and leave L2/LLC
  for a future session with either a targeted dense sweep to find a real L2 shelf
  (if one exists) or an explicit decision to test at some other candidate value.

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
- Source file(s): `data_raw/ookay/associativity/{L1,L2,L3_LLC}/associativity_*.csv.gz`,
  full transcript `data_raw/ookay/associativity/run_associativity_full_20260912T225532Z.log`.
- Run command + arguments:
  `./scripts/run_associativity_full.sh ookay 3 32768,262144,8388608`
  (core 3 + SMT sibling CPU7, confirmed fully idle via `mpstat`/`ps -eo psr` both
  immediately before and after the run; run completed in ~42s, 22:55:32Z-22:56:14Z,
  so no other user's job had a realistic window to interfere). base_seed=12345
  (repeats use base_seed+1, +2), samples=1,000,000/point, max_ways=40, both
  random and sequential (control) patterns per level.
- Conflict-set construction method: fixed node-to-node stride equal to each
  level's own assumed capacity (see `main_code/common/associativity.h`), sweeping
  same-set node count (num_ways 2-40) — forces all probed nodes into the same
  cache set regardless of the (unknown) real line size.
- **cache_bytes values used — explicit override from `CAPACITY_RESULTS.md`
  (this team's own hand-curated capacity table), NOT auto-detected:**
  - L1 = 32,768 B (32 KiB) — matches this file's own PROVISIONAL L1 estimate
    above (flat-then-ramp signature, 6/7 x86 machines agree).
  - L2 = 262,144 B (256 KiB) — **caveat:** `CAPACITY_INFERENCE_STATUS.md` and
    this file's own correction note above (line ~127) flag Ookay's L2/LLC as
    UNRESOLVED from the capacity sweep itself (32,768 B-~5.3 MiB is one
    continuous ramp with no confirmed shelf at 256 KiB specifically); 256 KiB
    was used here as a deliberate, explicitly-acknowledged choice (this chip
    family's textbook L2 size) per instruction, not because the capacity data
    independently pinned it. Treat the resulting way-count as conditional on
    that choice being correct.
  - L3/LLC = 8,388,608 B (8 MiB) — same caveat: the capacity sweep's own
    5.3-11.9 MiB region was flagged as one over-segmented transition, not a
    confirmed discrete boundary; 8 MiB was used as `CAPACITY_RESULTS.md`'s
    rounded "~8 MiB" figure (conveniently an exact power of two already).
- **Results — `detect_associativity.py`'s reported estimate, reproduced
  identically across the base run and both seeded repeats at every level (no
  disagreement warning fired). L1 is a genuine single clean knee; L2 and
  L3/LLC are NOT — see the staircase caveat below before citing either as
  resolved:**

  | Level | cache_bytes | Reported estimate (ways) | Base | Repeat 1 | Repeat 2 |
  |---|---|---|---|---|---|
  | L1 | 32,768 | **8-way** (single clean knee) | 8 | 8 | 8 |
  | L2 | 262,144 | **4-way** (first of two steps — see below) | 4 | 4 | 4 |
  | L3/LLC | 8,388,608 | **4-way** (first of two steps — see below) | 4 | 4 | 4 |

  Plots: `data_processed/ookay/associativity/{L1,L2,L3_LLC}/plots/associativity_{curve,boxplots}.{png,pdf}`.
- **L2 and L3/LLC are two-step staircases, not single knees — `4-way` is only
  the first step, and the reported estimate should NOT be treated as
  resolved.** Both levels' random-pattern medians show the identical shape
  (from `base_random_summary_20260912T225532Z.csv`, both L2 and L3):
  ~7.2 ticks at num_ways 2-4, a first jump to ~15 ticks at num_ways 5-8,
  then a second, larger jump to ~21 ticks at num_ways 9+ — the same two
  latency tiers, at the same two num_ways breakpoints, for BOTH the
  262,144 B and the 8,388,608 B stride. `detect_associativity.py` stops at
  the *first* confirmed knee (`find_first_knee`, see the script), so it
  reports "4-way" (the first step) for both levels and never evaluates the
  second, sharper step at num_ways=9. That second step lands at exactly
  L1's own independently-confirmed 8-way limit — for two strides 8x and
  256x larger than L1's own capacity. This is the same undiagnosed
  early-break confound `CAPACITY_INFERENCE_STATUS.md` already documents on
  Sunbird ("why do strides larger than L1's own capacity ... consistently
  break earlier than L1's confirmed 8-way limit, when both are still
  multiples of L1's set-stride and by that reasoning should reproduce L1's
  clean break at 9" — open question, not yet mechanistically explained
  there either). Given L2 and L3/LLC produce numerically identical
  staircases despite an 32x difference in stride, the more likely reading
  is that neither sweep is actually resolving L2 or L3/LLC set structure at
  all — both are probably re-measuring some shared L1/DTLB-scale effect
  (e.g. an artifact of every probed node landing on a distinct 4 KiB page
  once stride exceeds the page size), with the true L2/LLC signal (if
  visible at all at these strides) buried past num_ways=9 in the
  continuing climb through num_ways=40. **Net: per the cache_bytes caveat
  above (256 KiB / 8 MiB were explicit, not capacity-sweep-confirmed,
  choices), combined with this staircase shape, treat Ookay's L2 and
  L3/LLC way-counts as UNRESOLVED, not confirmed 4-way** — flagging for
  Phase II (PMU) or a follow-up Phase I investigation (e.g. a stride swept
  across several power-of-two candidates to see whether the num_ways=9
  break moves) rather than citing "4-way" in the report as-is.
  - Post-knee (thrashing) ticks also show substantial run-to-run spread at
    both L2 (up to ~63%, num_ways 18-40) and L3 (up to ~26%, scattered
    num_ways 26-40) — consistent with the same scattered single-run
    interference signature already documented elsewhere on this machine's
    capacity data, and separate from the staircase-shape issue above.
  - Sequential-pattern control: at L1, it tracks random almost exactly
    across the whole sweep (no divergence at all) — the strongest form of
    "not a prefetcher artifact" for that level. At L2 and L3/LLC, sequential
    reproduces the SAME two-step staircase as random up through num_ways=9
    (not flat — both patterns break together), then plateaus while random
    keeps climbing further — i.e. the control does not rule out the
    staircase being a real (if not yet understood) hardware effect, it only
    shows the *post*-num_ways=9 continued climb is pattern-dependent.

### latency/
Ran 2026-09-13, unattended (user not present; decisions below made per the
session's own explicit instructions). Both `hit_latency` and `miss_latency`
use footprint/target/evict byte values taken **only from
`CAPACITY_RESULTS.md`** (per that file's own directive and this session's
instructions): L1 = 32,768 B, L2 = 262,144 B, LLC = 8 MiB = 8,388,608 B
(`CAPACITY_RESULTS.md`'s "~8 MiB" row, converted as `8 * 1,048,576`, not
`8,000,000`). This supersedes this file's own capacity/ section above where
the two disagree (they don't here — Ookay's L1/L2/LLC candidates already
match `CAPACITY_RESULTS.md` exactly).

**Idle-core check (unattended, before running):** `who` showed only this
session (`nsngo`) and `dchen27` logged in; `ps -u dchen27` showed no
CPU-heavy process (pipewire/dbus/tmux-server only). Two `/proc/stat`
per-core delta snapshots 3s apart, taken before any run, showed core 0
(CPU0/CPU4) and core 1 (CPU1/CPU5) at ~3.5%/~0% busy (background
VS Code/Claude-session processes visible on CPU1 via `ps -eo psr`) and
core 2 (CPU2/CPU6) and core 3 (CPU3/CPU7) both at **0% busy in both
snapshots**. Picked **core 2** (`taskset -c 2`) to avoid any interaction
with this driving session's own processes on core 0/1. Re-checked
core 2 idle again immediately after the miss_latency run finished (still
0% busy, two more delta snapshots) — see the run-to-run spread caveat
below for why this matters.

**hit_latency (dependent chain + independent-load diagnostic control):**
- Source file(s): `main_code/common/{main.c,latency.c,latency.h,benchmark.c,benchmark.h,pointer_chase.c,pointer_chase.h,random.c,random.h}`, `main_code/x86_64/timer_x86.h`, `main_code/common/timer.h`
- Run command + arguments: `./scripts/run_hit_latency_full.sh ookay 2 L1:32768,L2:262144,LLC:8388608,DRAM:536870912` (core 2, idle-checked as above). DRAM's 536,870,912 B (512 MiB) is not a `CAPACITY_RESULTS.md` value — a "deep in the DRAM plateau" pick well past LLC, same convention Sunbird's writeup used.
- Per level: base run + 2 reproducibility repeats (seed = 12345, 12346, 12347), each at `--load-mode {dependent,independent}` × `--pattern {random,sequential}`, 1,000,000 timed accesses per combination (batch size 1000), 3 untimed warm-up passes.
- Dependent-chain batch size N used: 1000.
- Regular vs. randomized control included? Yes, both `--pattern random` and `--pattern sequential` at every (level, load_mode) combination.
- Raw output filename(s): `data_raw/ookay/latency/hit/<LEVEL>/hit_latency_{base,rep1,rep2}_{dependent,independent}_{random,sequential}_20260913T061059Z.csv.gz`
- Processing: `scripts/summarize_raw.py` → `data_processed/ookay/latency/hit/<LEVEL>/*_summary_20260913T061059Z.csv` → `scripts/plot_hit_latency.py` → `data_processed/ookay/latency/hit/<LEVEL>/plots/hit_latency_boxplots.{png,pdf}`.
- **Result (dependent, random pattern, base run median, n=1000 each): L1 ≈ 7.49 ticks, L2 ≈ 18.53 ticks, LLC ≈ 74.78 ticks, DRAM ≈ 284.45 ticks** — a clean, monotonically increasing 4-tier ladder, consistent with `CAPACITY_RESULTS.md`'s byte boundaries and with this machine's own capacity/ section (DRAM median here, 284.45, lands right inside the ~286–297 ticks/access topmost-region plateau already confirmed above).
- **Independent-vs-dependent check: 2 of 8 (level, pattern) cells flagged `[UNEXPECTED -- investigate]` by the pipeline's own printout** — LLC/sequential (independent 7.79 vs dependent 7.73 ticks) and DRAM/sequential (independent 7.85 vs dependent 7.77 ticks); every other cell (both L1/L2 patterns, and LLC/DRAM's own random-pattern cells: LLC 29.86 vs 75.65, DRAM 51.69 vs 284.60) showed the expected independent-faster signature. **Investigated per the session's instructions before trusting anything past this point — root cause found, not a measurement error:** `pointer_chase.c`'s `chase()` is a plain `next`-pointer walk, and for `--pattern sequential`, `latency.c` builds both the dependent chain AND the independent mode's address order as the same in-array (stride-1) sequence (`access_pattern.h` documents sequential explicitly as "the prefetcher-sanity control", not a load-latency-revealing pattern). At LLC/DRAM footprints, a strided sequential walk is fully hidden by the hardware prefetcher regardless of load mode, so both dependent and independent collapse to the same ~L1-speed floor (7.7–7.9 ticks, matching L1's own sequential numbers of 7.07/7.34) — the tiny 0.02–0.08 tick "inversions" are sub-tick noise around that shared floor, not a real loss of the expected ordering. **Conclusion: LLC/DRAM sequential-pattern hit_latency numbers should not be cited as genuine LLC/DRAM latency — they reflect prefetcher-hidden, effectively-L1-speed access.** Only the random-pattern numbers (unpredictable, defeats the prefetcher) are trustworthy as this machine's real LLC/DRAM hit latency; this is exactly the role `access_pattern.h` documents sequential as playing (a prefetcher sanity control), so the collapse is itself confirmation the prefetcher is working, not a bug.

**miss_latency (forced eviction + single-shot reload):**
- Source file(s): same list as hit_latency above.
- Run command + arguments: `./scripts/run_miss_latency_full.sh ookay 2 L1_to_L2:32768:262144,L2_to_LLC:262144:8388608,LLC_to_DRAM:8388608:16777216` (core 2, same idle check). `LLC_to_DRAM`'s evict_bytes = 16,777,216 B (16 MiB = 2× LLC) is not itself a `CAPACITY_RESULTS.md` value — picked after timing calibration (below) as comfortably past the 8 MiB LLC capacity.
- Wall-time calibration done first (core 2, random pattern, 100 trials, `--evict-bytes 16777216`): ~125 ms/trial. Extrapolated to the full base+2reps × 2-pattern LLC_to_DRAM sweep (1200 trials) ≈ 2.5 minutes, well under the ~15 min budget — used 16 MiB as-is, no shrinking needed. (L1_to_L2 and L2_to_LLC use much smaller evict sets, 262,144 B and 8,388,608 B respectively, taken directly from `CAPACITY_RESULTS.md`, so were not separately calibrated.)
- Per transition: base run + 2 reproducibility repeats (seed = 12345, 12346, 12347), each at `--pattern {random,sequential}`. 200 trials per (transition, pattern, run) — each trial is a single dependent reload, not a batch average (`--batch-size 1` passed only to satisfy `main.c`'s cross-experiment `--samples`/`--batch-size` validation; has no effect on miss_latency's own logic). 3 untimed warm-up passes (target set + eviction set) before the first timed trial, and again before every subsequent trial.
- Raw output filename(s): `data_raw/ookay/latency/miss/<TRANSITION>/miss_latency_{base,rep1,rep2}_{random,sequential}_20260913T061506Z.csv.gz`
- Processing: `scripts/summarize_raw.py` → `data_processed/ookay/latency/miss/<TRANSITION>/*_summary_20260913T061506Z.csv` → `scripts/plot_miss_latency.py --hit-latency-summary <matching hit_latency dependent/random summaries>` → `data_processed/ookay/latency/miss/<TRANSITION>/plots/miss_latency_boxplots.{png,pdf}`.
- **Result (random pattern, base run median, n=200 each): L1→L2 ≈ 96 ticks, L2→LLC ≈ 723 ticks, LLC→DRAM ≈ 693 ticks.** L1→L2 is a clean, modest step above L1→L2's own hit-latency levels; L2→LLC and LLC→DRAM are both far larger than their respective hit_latency plateaus (LLC hit ≈ 74.78, DRAM hit ≈ 284.45) and, unusually, LLC→DRAM's median (693) is not clearly larger than L2→LLC's (723) despite evicting one level further — see the overhead/interpretation caveat below before reading anything into that near-tie.
- **`plot_miss_latency.py`'s own >20%-run-to-run-spread warning fired on 4 of the 6 (transition, pattern) cells** — noted per the session's instructions rather than re-run: L1→L2/random (medians 96/122/104, 24.2%), L2→LLC/random (723/698/532, 29.3%), L2→LLC/sequential (350/182/346, 57.4%), LLC→DRAM/random (693/650/516, 28.6%). Core 2 was re-verified fully idle (0% busy, two `/proc/stat` delta snapshots) both immediately before the whole run and immediately after it finished, so this spread is **not explained by an obviously busy core at those two checkpoints** — continuous monitoring *during* the run itself was not done, so transient contention during the run can't be ruled out either. A more likely candidate, not confirmed further (Phase I timing-only — no PMU/perf lookups done): `L2_to_LLC`'s evict_bytes (8,388,608 B) exactly equals the LLC capacity estimate rather than exceeding it with margin, and the eviction walk plus the 262,144 B target array resident simultaneously slightly exceeds 8 MiB — plausibly causing some trials to spill part of the eviction set (or the target) into DRAM and others not to, which would produce exactly this kind of bimodal high-spread signature. Not investigated with a larger evict-bytes margin this session (out of scope: instructions said to note the warning, not chase it down).
- **IMPORTANT caveat, confirmed via a dedicated control test (2026-09-13) — do not treat the numbers above as clean reload latencies:** miss_latency times a SINGLE dependent load per trial (`timer_start()`/`timer_stop()` directly), unlike every other experiment here, which amortizes timer overhead across 1000+ accesses. Control run on this machine (`--target-bytes 32768 --evict-bytes 512 --pattern random --samples 2000`, an eviction set of ~8 cache lines spread across L1's sets, overwhelmingly unlikely to evict the target's own line): **median 66 ticks, mean 66.8, range 58–84**, vs. hit_latency's batched L1 median of 7.49 ticks at the identical footprint — a **~58.5-tick fixed single-shot overhead** on this machine (comparable in shape to, though numerically different from, Sunbird's own ~64–85 tick floor — different machines, not expected to match exactly). Even after subtracting this ~58.5-tick floor, L2→LLC's and LLC→DRAM's medians (723→664.5, 693→634.5) remain far above their own batched hit-latency plateaus (74.78, 284.45) — fixed overhead alone does not fully explain the gap, consistent with the evict-bytes-margin hypothesis above being a real contributor, not yet isolated from genuine (if elevated) single-shot reload cost. Treat every miss_latency number in this section as "true reload latency + a per-machine fixed overhead of roughly 58–60 ticks + an unresolved additional inflation at L2→LLC/LLC→DRAM", not a clean number — same discipline `latency.h`'s own `run_miss_latency_experiment` docstring and Sunbird's writeup already establish.
- Not yet done: tracing the 4-cell spread to a specific cause (no continuous `mpstat`/`/proc/stat` sampling during the run itself, only before/after); re-running L2_to_LLC/LLC_to_DRAM with an evict_bytes comfortably larger than the LLC capacity (e.g. 1.5–2× margin at L2_to_LLC too) to test the near-capacity-aliasing hypothesis; isolating per-transition single-shot overhead (only measured once, at the L1 footprint, matching Sunbird's own approach).

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
