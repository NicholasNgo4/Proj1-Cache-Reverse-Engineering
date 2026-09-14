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
Ran by a teammate (commit `990d5b6`, 2026-09-13, core 2) — narrative backfilled
here (2026-09-13) since the README section had been left blank while the data
itself was already committed. Not re-verified independently this session;
treat the git log message as the source of truth pending a fuller writeup.
- Source file(s): `main_code/common/{main.c,line_size.c,line_size.h}` +
  `scripts/{run_line_size.sh,plot_line_size_family.py,plot_line_size_offset.py}`;
  raw/processed data under `data_raw/ookay/line_size/level_{32768,262144,8388608}/`,
  `data_processed/ookay/line_size/level_{32768,262144,8388608}/`.
- Run command + arguments: `run_line_size.sh` for the three `CAPACITY_RESULTS.md`
  boundaries (32,768 / 262,144 / 8,388,608 B), Method A (family of curves) and
  Method B (single-curve ramp-saturation) each, plus a Method-A step-4
  bracket+offset refinement at candidate stride=64 B for all three levels. See
  `data_raw/ookay/line_size_run_wrapper.log` / `line_size_step4_wrapper.log`
  for the exact invocations.
- **Findings (from the commit message, not independently re-derived here):**
  L1 shows a clean, offset-independent V-shaped elbow at **64 B** — good
  Phase-I evidence for a 64 B line. L2's step-4 data is flat across the whole
  40–88 B bracket, not distinctively minimized at 64 B specifically — weak
  evidence, not counter-evidence. L3/LLC's family-of-curves data shows no
  stride-dependent separation at all (every candidate stride rides the same
  continuous capacity-to-DRAM ramp, consistent with this file's own capacity/
  section finding no clean LLC shelf); its step-4 "8/8 offset agreement" was
  flagged in the commit message as an artifact of the coarse
  points-per-octave=6 footprint grid quantizing nearby true elbow locations
  into the same bucket, not a genuine alignment-independent signal.
- **Net for downstream use:** 64 B is confirmed at L1, weakly-consistent
  (not contradicted) at L2, and unresolved at L3/LLC. `inclusion_policy/`'s
  `ASSUMED_LINE_SIZE_BYTES` below uses 64 B for all three levels on this
  basis — a materially weaker justification than Sunbird's (which had a
  positively-confirmed 64 B at all three footprints before that experiment
  ran), not a matching confirmation.

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
Ran 2026-09-13 using the hardened `run_inclusion_policy_full.sh` pulled from
main (commit `a6c0368` and its follow-ups). Boundary values from
`CAPACITY_RESULTS.md` only, same as latency/ above: L1 = 32,768 B,
L2 = 262,144 B, LLC = 8,388,608 B (8 MiB). All three pairings implied by
those three levels were run (L1 vs L2, L2 vs LLC, L1 vs LLC skip-level),
mirroring Sunbird's/Skylark's coverage.

**Idle-core check:** two `/proc/stat` per-core delta snapshots ~7s apart
(3s window each), taken immediately before the run, showed core 2
(CPU2/CPU6) at 0.0% busy in both — reused core 2, the same core the
hit_latency/miss_latency runs above already used successfully. `who`/`ps`
showed no CPU-heavy process from another user at the time (4 users logged
in: `rrsood`, `dchen27`, `dananth`, plus this session).

- Source file(s): `main_code/common/{main.c,inclusion_policy.c,inclusion_policy.h,pointer_chase.c,pointer_chase.h,random.c,random.h}`, `main_code/x86_64/timer_x86.h`, `main_code/common/timer.h`
- Build command: `make` (from repo root)
- Run command + arguments (pinned `taskset -c 2`, all three pairings in one invocation):
  `./scripts/run_inclusion_policy_full.sh ookay 2 L1_vs_L2:32768:262144:L2_to_LLC,L2_vs_LLC:262144:8388608:LLC_to_DRAM,L1_vs_LLC:32768:8388608:LLC_to_DRAM`
  (timestamp `20260913T182203Z`). The 3rd field on each spec names the
  already-collected `miss_latency` transition (see `latency/` section above)
  that pairing sources its "invalidated" calibration class from: L1_vs_L2
  evicts at L2 scale → invalidated class = `L2_to_LLC`; both L2_vs_LLC and
  L1_vs_LLC evict at LLC scale → invalidated class = `LLC_to_DRAM`.
- **`ASSUMED_LINE_SIZE_BYTES` left at the script's default of 64** (not
  overridden). Justification, since this file's own `line_size/` section
  above was never filled in narratively even though the raw/processed data
  exists (see `data_processed/ookay/line_size/`, generated by a teammate's
  commit `990d5b6`, "Add Ookay line_size results"): that run found L1 shows
  a clean, offset-independent 64B elbow (good evidence); L2's step-4 data is
  flat across the whole 40–88B bracket, i.e. not distinctively minimized at
  64B, but also not contradicting it (weak evidence, not counter-evidence);
  L3/LLC's family-of-curves data showed no stride-dependent separation at
  all (rides the same continuous capacity-to-DRAM ramp at every candidate
  stride, consistent with this machine's own capacity/ section finding no
  clean LLC shelf) — inconclusive, not contradictory. With no machine-level
  evidence pointing away from 64B at any of the three levels (unlike
  Thunderbird's confirmed 64B-at-L1/L2-vs-128B-at-LLC split), 64B was kept
  as the scaling constant for every pairing here. Flagged as a **weaker
  basis than Sunbird's** (which had a clean, positively-confirmed 64B at all
  three footprints before this experiment ran) — if L2 or LLC's real line
  size turns out to differ, the two LLC-scale pairings' eviction-footprint
  math below would need re-scaling.
- Eviction/reload construction: identical method to Sunbird's (see
  `main_code/common/inclusion_policy.h`'s module doc comment) — target and
  an untouched control buffer freshly page-aligned at offset 0; eviction
  buffer places one node per page (`--evict-stride-bytes 4096`) at a fixed
  sub-page offset of 2048 B, so it spans many pages/lower-level sets while
  structurally avoiding target's own line, provided target's full index
  fits within one page (true for L1, not reliable for the L2 target in
  L2_vs_LLC — same caveat 3 as Sunbird's writeup, see below).
- Per trial: 200 single-shot trials (`--samples 200 --batch-size 1`), base +
  2 reproducibility repeats (seed 12345/12346/12347), both eviction-walk
  patterns, 3 untimed warmup passes; separate 500-trial calibration run per
  pairing (`--evict-bytes` = `--target-bytes`, nothing evicted) for the
  "survived" baseline.
- **Wall-time calibration done first** (per this session's cross-machine
  caveat that miss_latency/inclusion_policy timing is non-linear in
  eviction-set size): a 20-trial and then a 200-trial manual run at the
  L2_vs_LLC/L1_vs_LLC scale (`--evict-bytes 536870912`, the 8 MiB LLC value
  scaled by `4096/64`, i.e. 512 MiB / 131,072 pages) measured **~12 ms/trial**
  — the full pipeline (calibration + base+2reps×2patterns per pairing, ~1,700
  single-shot trials total across all 3 pairings) finished in well under a
  minute end to end, unlike Sunbird's ~1.9 GiB/~604 ms-per-trial LLC-scale
  footprint — no `tmux` needed at this machine's scale.
- Raw output filename(s): `data_raw/ookay/inclusion_policy/<pairing>/inclusion_policy_{calibration,base,rep1,rep2}_{random,sequential}_20260913T182203Z.csv.gz`
- Processing: `scripts/summarize_raw.py` → `data_processed/ookay/inclusion_policy/<pairing>/*_summary_20260913T182203Z.csv` → `scripts/classify_inclusion_policy.py` (reads the base/random raw data directly) → `scripts/plot_inclusion_policy.py`.

**Fixed single-shot overhead:** already isolated in the latency/ section above
(~58.5 ticks, control median 66 vs. batched L1 hit-latency median 7.49) — the
same instrument and overhead applies here since inclusion_policy also times a
single dependent reload per trial. Every ticks number below carries that same
floor; the classification below works in absolute/relative terms against this
machine's own single-shot survived/invalidated calibration, so the fixed
overhead is present in both reference points and in the measured channels
alike — it does not need a separate subtraction to make the *classification*
valid, only to interpret any individual tick number as a "clean" latency.

**Results, one per pairing (n=200 target/control trials each, base/random run
unless noted):**

- **L1_vs_L2** (survived-class 61.44 ticks, invalidated-class 723.0 ticks from
  `L2_to_LLC`): target median 90 ticks (100.0% survived-like, 0% invalidated-like),
  control median 88 ticks (100.0% survived-like). Paired check (target slower
  than its own control): 52.0% — essentially a coin flip, i.e. target and
  control are statistically indistinguishable from each other, both sitting
  right next to the survived-class calibration and nowhere near the
  invalidated-class one. **Verdict: EXCLUSIVE / NON-INCLUSIVE** — the cleanest
  and most confident result of the three, matching Sunbird's and Skylark's own
  L1_vs_L2 conclusion, and arguably even cleaner here (100%/100% survived-like
  vs. Sunbird's 90%/92%, with no invalidated-like trials at all).
- **L2_vs_LLC** (survived-class 73.86 ticks, invalidated-class 693.0 ticks
  from `LLC_to_DRAM`): target median 142 ticks (69.5% survived-like, 30.5%
  invalidated-like, 0% ambiguous — this machine's classifier resolved every
  trial one way or the other here, unlike Sunbird's 85%-ambiguous result for
  the same pairing), control median 166 ticks (97.5% survived-like, 2.5%
  invalidated-like). Paired check: 29.0% (target read slower than control in
  only 29% of trials — control was, if anything, the slower channel more
  often, plausibly reflecting run-to-run noise given the high spread flagged
  by the plotting step below rather than a real per-trial effect). **Verdict:
  UNCERTAIN**, but with a real directional lean worth stating: target's
  30.5% invalidated-like fraction is ~12x control's 2.5%, i.e. eviction
  pressure at LLC scale invalidates the L2-sized target meaningfully more
  often than it invalidates an untouched control of the same size — a weak
  lean toward INVALIDATED/inclusive-like, same direction as this pairing's
  result on Sunbird (which leaned survived, i.e. the *opposite* direction —
  see the cross-machine note below) and consistent with caveat 3: an L2
  target's index does not fit in one page, so this pairing structurally
  can't distinguish "LLC evicted the L2 line because it's inclusive" from
  "the eviction walk incidentally landed on the L2 target's own set" —
  read this as the least trustworthy of the three, per Sunbird's own
  writeup's reasoning, not because the data itself is noisier than the
  others (it isn't — L1_vs_L2 and L1_vs_LLC are both individually more
  internally consistent). The plotting step flagged two boxes with >20%
  run-to-run spread: `control/random` (medians 166/142/136, 20.3%) and
  `target/sequential` (medians 140/326/218, 81.6%) — not investigated
  further this session.
- **L1_vs_LLC** (survived-class 57.13 ticks, invalidated-class 693.0 ticks
  from `LLC_to_DRAM`): target median 194 ticks (0% survived-like, 97.0%
  ambiguous, 3.0% invalidated-like — median sits just inside the classifier's
  ±15% ambiguous band around its 198.98-tick boundary, 194 vs. 198.98, so
  almost the entire distribution lands in the fence rather than resolving
  either way), control median 132 ticks (98.5% survived-like). **Paired
  check: 99.5%** — target read slower than its own trial's control in
  essentially every single trial, the single cleanest directional signal of
  any pairing on this machine (cleaner even than L1_vs_L2's own paired
  check, which was a coin flip in the *other* direction). **Verdict:
  UNCERTAIN** by the absolute-ticks classifier (it never quite crosses into
  "invalidated-like" territory), but the paired check makes the directional
  read unambiguous: LLC-scale eviction pressure consistently and
  substantially slows down the L1-resident target relative to an untouched
  control of the same size, i.e. leans strongly toward INVALIDATED/
  inclusive-like — matching Sunbird's own L1_vs_LLC lean (75% invalidated-like
  there) in direction, just expressed through a different one of this
  script's two diagnostics (paired-check vs. absolute-threshold) on this
  machine's numbers.
- **Cross-machine note on L2_vs_LLC's direction:** Sunbird's L2_vs_LLC leaned
  (weakly, 9:1 among the trials that resolved) toward SURVIVED; Ookay's leans
  (weakly, ~12x) toward INVALIDATED. Given caveat 3 applies identically to
  both machines (an L2 target's index structurally doesn't fit in one page on
  either), and both results are individually low-confidence to begin with,
  this disagreement is read as evidence the pairing itself doesn't produce a
  reliable per-machine signal at all, not as evidence Sunbird's and Ookay's
  LLCs actually behave oppositely toward L2. Kept as a directional best guess
  per pairing (below) anyway, per this session's instruction not to leave any
  cell blank — just flagged as the lowest-confidence number in the table.
- Not yet done, any pairing: multiple different target addresses/sets (only
  one target buffer per repeat, just re-seeded); a real (narratively
  documented) line_size measurement for L2/LLC to replace the weak/
  inconclusive evidence noted above; the huge-pages TLB mitigation for
  caveat 2 (large-footprint DTLB pressure) that Sunbird's writeup also
  flagged as future work, not implemented here either.

**Best-guess synthesis:** combining all three pairings the same way Sunbird's
table does — **L1 vs L2: confidently NON-INCLUSIVE** (cleanest result, no
caveats apply strongly). **L1 vs LLC (skip-level): leans INVALIDATED/
inclusive-like**, on the strength of the 99.5% paired-check signal even
though the absolute-ticks classifier calls it ambiguous. **L2 vs LLC:
UNCERTAIN with a weak lean toward INVALIDATED/inclusive-like**, read with the
least confidence of the three per caveat 3 and the cross-machine direction
disagreement noted above. Put together: this is the same overall story
Sunbird's data told — a non-inclusive L2 alongside an LLC that behaves
inclusively toward what's resident above it (both L1 directly and, more
weakly, L2) — reached independently on a second machine, which is itself
mild corroborating evidence for that pattern rather than a coincidence of
one machine's noise.

### pmu/ (Phase II — 2026-09-14)
Phase I frozen/tagged (`phase1-timing-only`) before anything below was run,
per `README.md`'s Phase Discipline. See `CLAUDE.md`'s "Phase II" subsection
and `data_processed/ookay/PHASE2_VALIDATION_TABLE.md` for the full
methodology/results write-up and literature citation — this section is the
raw-data/reproduction-detail record. Uses the same reusable pipeline
Sunbird's session built and Thunderbird's session migrated to (no script
changes needed).

- Source file(s): `scripts/run_pmu_verification.sh`, `scripts/summarize_pmu.py`
  (both pre-existing, reused unmodified — wraps the existing `cache_bench
  --experiment hit_latency` binary in `perf stat`).
- PMU scheduling on this machine: all 4 two-hardware-event groups
  (`cache-references,cache-misses` / `L1-dcache-loads,L1-dcache-load-misses`
  / `LLC-loads,LLC-load-misses` / `cycles,instructions`, each also carrying
  the software `duration_time` event) scheduled at 100% with no
  `<not counted>` flags anywhere in this run — `LLC-loads`/`LLC-load-misses`
  counted normally at every footprint (no ARM-style `<not supported>`
  limitation here, unlike Thunderbird).
- Core selection: this session's shell defaults to `Cpus_allowed_list: 0-1`,
  but `taskset -c <core>` can still target any of this machine's 8 logical
  CPUs (confirmed: a child process explicitly `taskset -c 2`'d shows
  `Cpus_allowed_list: 2`, not clipped) — there is no cgroup cpuset actually
  restricting the choice, just this shell's own inherited default. Checked
  `mpstat -P ALL` across 3 samples ~3s apart before running: core 0 ~58%
  busy (another student's `incl_pmu` process, confirmed via `ps -eLo
  pid,psr,pcpu,comm`), core 1 partially busy (this session's own VS
  Code/tooling processes), core 2 100% busy (another student's
  `cache_bench_x86 --cpu 2`, confirmed via `ps`), cores 3–7 100% idle in
  all 3 samples. Chose **core 3** (physical core 3, both SMT threads 3 and
  7 idle) — a genuinely idle full physical core, not just one idle thread
  of a partly-busy one.
- Run command: `./scripts/run_pmu_verification.sh ookay 3
  L1:32768,L2:262144,LLC:8388608` (footprints from `CAPACITY_RESULTS.md`'s
  Ookay row). base_seed=12345 (repeats use base_seed+index), samples=
  1,000,000/run, batch_size=1000, warmup_passes=3, dependent load mode,
  random pattern, timestamp `20260914T003308Z`.
- Raw output: `data_raw/ookay/pmu/{L1,L2,LLC}/*_perfstat_*.csv.gz` (perf
  stat's own `-x,` CSV output) and `*_bench_*.csv.gz` (cache_bench's own
  CSV from the same invocation), gzipped by hand after the run per
  `.gitignore`'s `data_raw/**/*.csv` convention. Transcript:
  `data_raw/ookay/pmu/run_pmu_verification_20260914T003308Z.log`.
- Processed: `data_processed/ookay/pmu/{L1,L2,LLC}/pmu_summary_20260914T003308Z.csv`
  (one row per run_tag + a median-of-3 row).
- System-reported cache info (also Phase II, same session):
  `data_raw/ookay/pmu/system_reported_cache_info.txt` — `lscpu --caches`,
  full `lscpu`, and per-instance `/sys/devices/system/cpu/cpu0/cache/index*/`
  fields, collected 2026-09-14T00:33:33Z.
- Headline results (full detail and caveats:
  `data_processed/ookay/PHASE2_VALIDATION_TABLE.md`): size/ways/sets/line
  match exactly across Phase I timing, system-report, AND Agner Fog's
  literature table (Table 11.2, "Cache sizes on Skylake" — covers Kaby
  Lake per Fog's own text) at L1D; L2 and LLC associativity **both
  disagree with Phase I's confound-blocked best guess (8-way at both
  levels) — system-reported is 4-way at L2 and 16-way at LLC**, resolved
  in favor of the system-reported values, directly confirming (not just
  suspecting) that Phase I's repeated "8" at this level and above was the
  cross-machine small-structure confound, not real associativity. LLC size
  matches Phase I's ~8 MiB estimate to the exact byte (8,388,608 B).
  Miss-rate PMU evidence reproduces Phase I's own L1/L2/LLC boundary
  placement (LLC-scope-specific miss rate: 17.34% at L1 footprint → 1.38%
  at L2 → 32.39% at LLC; L1-dcache miss rate climbs monotonically 0.97% →
  12.14% → 8.79%, saturating). **New finding not seen on Sunbird/
  Thunderbird**: the LLC-footprint run's own bench latency (≈128.42 ticks)
  diverged +71.7% from Phase I's original ≈74.78-tick result, coinciding
  with an unstable implied clock frequency across repeats (2.32-4.80 GHz,
  computed from `cycles ÷ duration_time`, briefly exceeding this CPU's own
  4.2 GHz max turbo) even though core 3 itself was independently confirmed
  idle throughout — attributed to shared-LLC/memory-bandwidth contention
  and per-package Turbo Boost power-budget sharing from the two other
  students' processes pinned at 100% on cores 0 and 2 the entire session,
  since an idle *core* doesn't insulate against contention on *chip-shared*
  resources (LLC, package power budget) the way it does for private L1/L2.
  Flagged plainly, not re-run this session — see the validation table's
  caveat section for the full reasoning and per-run numbers.

### eight_counters/ (Problem 8.4, item 1 — 2026-09-14)
Uses `scripts/run_standardized_benchmarks.sh` + `scripts/summarize_eight_counters.py`
(the pipeline Sunbird/Thunderbird/Skylark's sessions already used — no
script changes needed). Same underlying `cache_bench --experiment
hit_latency --load-mode dependent --pattern random` construction as every
other experiment on this machine, just 3 standardized footprint choices
and a different fixed 8-event set (`cache-references`, `cache-misses`,
`L1-dcache-loads`, `L1-dcache-load-misses`, `L1-dcache-stores`,
`LLC-loads`, `LLC-load-misses`, `dTLB-load-misses`) than `pmu/`'s own.

- Idle-core check immediately before running: 3 `mpstat -P ALL` samples
  ~3s apart, cores 2-7 all 100% idle (the two other students' processes
  from this morning's `pmu/` run had since finished). Reused core 3 for
  consistency with that earlier run.
- Run command: `./scripts/run_standardized_benchmarks.sh ookay 3
  L1_resident:32768,LLC_random:8388608,beyond_LLC:536870912` (L1/LLC bytes
  from `CAPACITY_RESULTS.md`/`FINAL_CACHE_TABLE.md`; `beyond_LLC` is the
  project's universal 512 MiB constant). base_seed=12345 (repeats use
  base_seed+index), samples=1,000,000/run, batch_size=1000, warmup_passes=3,
  timestamp `20260914T052901Z`. All 4 perf groups scheduled at 100% for
  every benchmark/run_tag, no `<not counted>` anywhere.
- Raw: `data_raw/ookay/eight_counters/{L1_resident,LLC_random,beyond_LLC}/
  *_{perfstat,bench}_*.csv.gz`. Transcript:
  `data_raw/ookay/eight_counters/run_standardized_benchmarks_20260914T052901Z.log`.
  Processed: `data_processed/ookay/eight_counters/<benchmark>/
  eight_counters_summary_20260914T052901Z.csv`.
- **Headline results**: ticks/access climb monotonically as expected
  (`L1_resident`≈7.60, `LLC_random`≈80.24, `beyond_LLC`≈287.44) and closely
  match this machine's own already-documented Phase I numbers (≈7.49 /
  ≈74.78 / ≈284.45). Notably, `LLC_random`'s ≈80.24 sits much closer to the
  original ≈74.78 than this morning's `pmu/` run's contended LLC footprint
  reading (≈128.42) did — corroborating that run's own hypothesis that its
  inflated number came from two other students' processes contending for
  chip-shared LLC/memory bandwidth, not from anything wrong with the
  measurement itself; this run's machine was independently confirmed
  quiet on every core.
- `l1_miss_rate` climbs cleanly monotonic (0.96% → 8.79% → 13.36%,
  saturating at the top like every other machine's own L1-dcache signal).
  `llc_miss_rate` and the generic `cache_miss_rate` both climb monotonically
  too this time (11.04%/13.84% → 16.33%/18.04% → 47.79%/55.41%) — unlike
  this morning's `pmu/` run, which showed a non-monotonic dip at its L2
  footprint, plausibly for the same contention-related reason noted above
  (though the footprint sets aren't directly comparable: L1/L2/LLC there
  vs. L1_resident/LLC_random/beyond_LLC here).
- `dtlb_load_misses` climbs cleanly across all 3 orders of magnitude
  (1,838 → 1,091,713 → 252,964,812) — real, hardware-counter-based data
  toward the still-open DTLB-scale-confound question from the
  associativity investigation, not yet interpreted further (items 2-4 of
  Problem 8.4 need all 8 machines' data first, per `CLAUDE.md`).

### software_hit_rate/ (Problem 8.5 — 2026-09-14)
Software-only, timing-derived cache hit-rate estimator
(`main_code/software_hit_rate/`, no PMU access anywhere in that file) plus
its Phase-II PMU validation. Same pipeline and method as Sunbird's own
`software_hit_rate/` section (see that machine's README for the full
calibration -> ROC threshold -> Rogan-Gladen -> bootstrap CI method write-up
and the PMU-validation-script redesign history) — no script changes needed
for this machine.

- Idle-core check immediately before running: two independent `/proc/stat`
  idle-time-delta samples (2s apart each), physical core 2 (logical CPUs 2
  and 6) 0.0% busy in both windows, with only kernel housekeeping threads
  (`cpuhp/2`, `ksoftirqd/2`, `kworker/2:*`, etc.) scheduled there — used core
  2 for both the sweep and the PMU validation run.

#### Sweep (parts 1-3, standalone, no perf)
- Run command: `./scripts/run_software_hit_rate_sweep.sh ookay 2 ""
  "L1:32768,L2:262144,LLC:8388608,DRAM:536870912"` — footprint arg left
  empty so the script's default 15-point log-spaced sweep (4 KiB-512 MiB)
  ran (an empty `"$3"` falls through bash's `${3:-default}` the same as
  unset, per `run_software_hit_rate_sweep.sh`'s own default-sweep logic);
  boundary_spec passed explicitly as this machine's own
  `CAPACITY_RESULTS.md` values (L1=32,768 B, L2=262,144 B, LLC=8,388,608 B,
  DRAM=536,870,912 B) for the plot reference lines only, per the
  Skylark-discovered bug already documented in the shared script's header
  comment (never rely on the hardcoded Sunbird default for a non-Sunbird
  machine). core=2, seed=12345, resident_bytes=16384,
  nonresident_bytes=536870912, calib_samples=20000, test_samples=50000,
  bootstrap_reps=2000, pattern=random, timestamp `20260914T123827Z`.
- Raw output: `data_raw/ookay/software_hit_rate/raw/hit_rate_<bytes>_20260914T123827Z.csv.gz`.
  Transcript: `data_raw/ookay/software_hit_rate/run_software_hit_rate_sweep_20260914T123827Z.log`.
- Processed: `data_raw/ookay/software_hit_rate/hit_rate_sweep_20260914T123827Z.csv`;
  plots: `data_processed/ookay/software_hit_rate/plots/{hit_rate_sweep,calibration_distributions}.{png,pdf}`.
- **Headline results**: Hhat=1.0000 for every footprint from 4,096 B through
  131,072 B — i.e. through this machine's own L1 (32,768 B) boundary AND
  well past it into L2-scale territory, consistent with the estimator's
  "hit = served by ANY cache level" definition, not L1-specifically. Unlike
  Sunbird (whose dip showed up exactly at its own L1 boundary), **Ookay's
  first dip appears at the L2 boundary (262,144 B): Hhat=0.9613** (CI
  0.9321-0.9631) — a modest, real conflict/associativity-driven dip at
  exactly-full L2 capacity, the same qualitative signature Sunbird
  documented at its own boundary. Falls further at 1,048,576 B (Hhat=0.7069,
  but with a very wide CI: 0.40-0.71, bootstrap_std=0.14 — the noisiest
  point in the whole sweep) and, oddly, partially recovers at 4,194,304 B
  (Hhat=0.9964, CI 0.337-0.997, bootstrap_std=0.266 — also highly unstable,
  not a genuine second high-hit-rate region) before resuming its decline:
  0.5976 at the LLC boundary itself (8,388,608 B), 0.1279 at 16,777,216 B,
  down to 0.0526/0.0077/0.0023/0.0005/0.0000 at 31,457,280 / 67,108,864 /
  134,217,728 / 268,435,456 / 536,870,912 B. **The 1 MiB-4 MiB region's huge
  bootstrap-std swing (0.14-0.27, an order of magnitude above every other
  point's spread) is the same single-threshold-classifier instability later
  confirmed more sharply in the PMU-validation run below (see LLC repeat
  disagreement) — read this mid-sweep noise as an early symptom of the same
  root cause, not independent noise.**

#### PMU validation (part 4)
- Run command: `./scripts/run_hit_rate_pmu_validation.sh ookay 2
  L1:32768,L2:262144,LLC:8388608,DRAM:536870912` (core 2, same idle check as
  above). Tested footprints after the script's own /2 "safely inside the
  level" halving: L1=16384, L2=131072, LLC=4194304, DRAM=536870912
  (unchanged). base_seed=12345 (repeats use base_seed+index), timestamp
  `20260914T125828Z`.
- Raw output: `data_raw/ookay/software_hit_rate/pmu/{L1,L2,LLC,DRAM}/
  *_{calibonly,bench,hitlatpmu,perfstat}_{base,rep1,rep2}_20260914T125828Z.csv.gz`.
  Transcript: `data_raw/ookay/software_hit_rate/pmu/run_hit_rate_pmu_validation_20260914T125828Z.log`.
- Processed: `data_processed/ookay/software_hit_rate/pmu_validation_20260914T125828Z.csv`.
- Headline results (median of base+2 repeats):

  | Level | Tested footprint | Hhat | H_pmu | rel. error |
  |---|---|---|---|---|
  | L1  | 16,384 B    | 1.0000 | 0.8564 | 16.8% |
  | L2  | 131,072 B   | 1.0000 | 0.8655 | 14.9% |
  | LLC | 4,194,304 B | 0.7886 | 0.9705 | 18.7% |
  | DRAM | 536,870,912 B | 0.0002 | 0.4484 | 99.96% |

- **L1/L2: Hhat correctly reads 1.0 (both footprints genuinely fit and
  should hit), but H_pmu independently reads only ~0.86-0.87 — a
  reproducible ~15-17% disagreement even where the software estimator is
  unambiguously right.** Cross-checked against this machine's own, entirely
  separate Phase-II PMU run (`data_processed/ookay/pmu/L1/pmu_summary_
  20260914T003308Z.csv`, full unhalved 32,768 B footprint, different
  timestamp/session): that run independently measured an 18.5%
  `cache-references`/`cache-misses` miss rate at L1 too — so this ~15-17%
  gap is a real, reproducible property of what these generic PMU events
  count on Ookay specifically (not a fluke of this run), consistent with
  the generic PMU-event-semantics gap already documented elsewhere in this
  project — read as evidence against H_pmu's own precision here, not
  against Hhat.
- **LLC: the single most unstable result of the whole run — Hhat swings
  0.7886 (base) -> 0.1702 (rep1) -> 0.9990 (rep2) at the IDENTICAL
  4,194,304 B footprint, only the seed changed — but tracing this into the
  raw calibration data changes the diagnosis from the first-pass read
  below.** base/rep1 calibrated tau≈88-94 ticks; rep2's calibration landed
  on tau=266. Directly inspecting rep2's 20,000-sample `calib_resident`
  distribution (`LLC_calibonly_rep2_...csv.gz`): the bulk is tightly
  clustered (median 60, p95=68 ticks, nearly identical to base's median
  58/p95 68) — **only 63/20,000 (0.3%) of "resident" calibration samples
  exceed 266 ticks**, a sparse high-tail contamination (plausibly page
  faults/scheduler noise on the freshly-mapped calibration buffer, not a
  second real latency population) that the ROC/Youden threshold selection
  is evidently sensitive to: to keep sensitivity up despite that thin tail,
  it pushed tau all the way to 266 (specificity dropped correspondingly,
  0.9980 vs. the usual 0.9998-0.9999). **This is a calibration-step
  robustness issue — present in principle for ANY level's run, since
  calibration always re-uses the same fixed 16,384 B resident buffer
  regardless of test_bytes — not evidence that the classifier specifically
  breaks down "at LLC scale."** It happened to land on the LLC run in this
  session; the sweep's own per-point tau values (all 15 points: 90-104
  ticks, no outliers) show this instability did NOT recur elsewhere this
  run, so it reads as an infrequent (~1/12 calibrations here) but real
  failure mode, not a systematic LLC-specific one. **H_pmu, by contrast,
  stays tight and physically sensible across all 3 runs (2.9-3.6% miss
  rate)** — 4,194,304 B is half this machine's ~8 MiB LLC estimate so
  should mostly hit, which matches; this is also consistent with (not
  contradicting) the much higher ~61.5% miss rate the separate Phase-II PMU
  run measured at the FULL 8,388,608 B boundary itself — a footprint sized
  to exactly fill LLC capacity is expected to show far more conflict misses
  than one sized to half of it, the same boundary-vs-interior pattern
  already seen in the L2 dip in the sweep above.
- **L2's rep1 also shows an isolated H_pmu dip (0.669, vs. base/rep2's
  ~0.866-0.871) despite Hhat correctly reading 1.0 in all three L2 runs.**
  Checked the raw `perf stat` output directly: `duration_time` (5.80/6.04/
  5.83 ms) and `cache-references` counts (217,268/219,100/216,344) are
  essentially identical across base/rep1/rep2 — ruling out the
  wall-time-inflation failure mode already documented for `hit_rate`'s own
  single-shot loop (that would show up as elevated duration_time/reference
  counts too, and doesn't here). Only `cache-misses` itself jumps
  (29,222/72,526/28,003) with timing and reference-count otherwise
  unchanged — genuine, unexplained hardware-counter noise isolated to one
  repeat, not a measurement-harness artifact; flagged rather than averaged
  away.
- **DRAM: Hhat correctly reads ~0.0001-0.0002 (near-zero, as expected for a
  512 MiB random footprint), but H_pmu reads 0.448 (44.8%)** — the same
  generic PMU-event-semantics gap already documented at DRAM scale on
  Sunbird; H_pmu is not a trustworthy ground truth at this footprint either.
- **Conclusion for the report:** Hhat is directionally correct everywhere
  here (high where it should hit, near-zero at DRAM) and its L1/L2 values
  are arguably the most reliable numbers in this table (corroborated by an
  independent PMU run). Its one real failure mode observed this session is
  a calibration-threshold instability driven by sparse outlier ticks in the
  resident reference distribution (not a footprint-scale-dependent
  weakness) — a second, distinct
  concrete failure mode for the same underlying single-threshold design
  limitation, useful as a second data point for the report's "when does
  this estimator fail" discussion (8.5, part 4).

## Final Inferred Cache Table (Ookay, Phase I best guess, 2026-09-13)

Lives at `data_processed/ookay/FINAL_CACHE_TABLE.md` (2026-09-13), alongside
this machine's other processed benchmark outputs, next to `capacity/`,
`line_size/`, `associativity/`, `latency/`, `inclusion_policy/` — same
placement convention as Sunbird's. The full per-pairing reasoning and caveats
behind it remain here, in this file's `associativity/` and `inclusion_policy/`
sections above (the latter's "Best-guess synthesis" subsection in particular)
— the processed-directory copy is the consolidated table only, not a
replacement for that narrative.

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
