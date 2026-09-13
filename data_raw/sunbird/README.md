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
- Timer method used (RDTSC/RDTSCP+LFENCE, CNTVCT_EL0, etc.): x86 RDTSC (LFENCE-fenced start) / RDTSCP (LFENCE-fenced stop), batched: N=1000 dependent pointer-chase steps timed per start/stop pair, ticks/access = (t1-t0)/N. See `main_code/x86_64/timer_x86.h`, `main_code/common/benchmark.c`. Disassembly excerpt confirming the loop/timer placement survived -O0 unmodified: `build/cache_bench.source.dis` (`objdump -d -S`, generated on Sunbird itself, not substituted from another machine) — confirms `x86_tsc_start` emits `lfence` immediately before `rdtsc` and `x86_tsc_stop` emits `rdtscp` immediately before its own `lfence`, with no reordering across the fence, and that `measure_dependency_chain_batched` (the timed pointer-chase loop) is called directly around the start/stop pair as written in source, not inlined or hoisted.
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
- Raw output filename(s): `data_raw/sunbird/capacity/capacity_coarse_{random,sequential}_<timestamp>.csv.gz`, `capacity_coarse_ext256_{random,sequential}_<timestamp>.csv.gz`, `capacity_denseA_{random,sequential}_<timestamp>.csv.gz`, `capacity_denseB_{random,sequential}_<timestamp>.csv.gz`, `capacity_denseC_{random,sequential}_<timestamp>.csv.gz` (gzipped after the fact, ~9x smaller, to keep repo size manageable across all machines; summaries in `data_processed/` were already generated from the uncompressed originals before compression, so they're unaffected — `zcat`/`gunzip` a file to inspect the raw per-batch rows)
- Processing script -> data_processed path: `python3 scripts/summarize_raw.py <raw.csv> -o data_processed/sunbird/capacity/<name>_summary.csv`, then `python3 scripts/detect_cache_hierarchy.py <summary.csv>` for a first-pass (non-final) boundary hypothesis, then `python3 scripts/plot_capacity.py <all summary.csv...> -o data_processed/sunbird/capacity/plots --machine sunbird --boundary 32KiB --boundary 20MiB --boundary 150MiB` for the required curve and box-plot figures
- Excluded runs (if any) and reason: `capacity_20260907T053240Z.csv.gz` (first exploratory run, predates the `--pattern` CLI option and the `pattern` CSV column) is retained but superseded by `capacity_coarse_random_*` for analysis, since its schema differs (no pattern column) and it was random-pattern-only.
- Known noise in dense window C, and reproducibility check: isolated single-point median spikes at working-set sizes ~16.5, 20.5, 22.6, 25.4, 28.9, and 29.3 MiB in the original window C run (several with `n_outliers=0`, meaning most of that point's 1000 batches were elevated together, not just a few stray ones) are consistent with transient scheduling interference on this shared, multi-user machine. This was confirmed, not just assumed: an independent repeat run over the same 16-128 MiB size grid (identical flags/seed) produced spikes at *different* sizes than the original run (e.g. original spikes at 16.47/20.45 MiB were flat in the repeat; the repeat instead spiked at 16.0/19.87 MiB where the original was flat). Since the noise doesn't recur at the same working-set size across independent runs, it is not a property of that size -- it's whatever else happened to be running on the shared machine during that specific ~1-2s measurement window. Point-by-point comparison of the two runs is not saved as a script (was done ad hoc in the session); the two raw/summary file pairs (`capacity_denseC_*_20260908T013237Z*` and `capacity_denseC_repeat_*_20260908T023625Z*`) are both retained so this comparison is reproducible from the data.
- `scripts/plot_capacity.py` combines overlapping summary rows (same size+pattern appearing in more than one input file, e.g. the coarse/dense/repeat sweeps above overlap on a shared log-spaced grid) by averaging medians and widening the plotted whisker range to the union of the inputs' p5/p95, rather than letting the last-loaded file silently overwrite the others -- see `combine_duplicate_rows()` in that script.
- With rep2/rep3 added, most size points >=16 MiB now have 3-5 independent measurements. Checked the >=145 MiB plateau specifically: across 40 points, the run-to-run spread in median (max-min across available runs, divided by mean) averages 3.6% and is under 2% at many points -- confirms this region is a genuine stable plateau (~190-205 ticks/access) rather than a still-noisy or still-climbing region; the wider apparent noise in earlier single/double-run plots there was mostly a small-sample-size artifact. The ~19-25 MiB transition region remains genuinely more variable run-to-run even after averaging (individual points still show 30-90 tick spreads across runs) -- this is a real property of measuring a steep transition, not something more averaging alone will fully clean up.
- `capacity_boxplots.png/.pdf` now annotates each box with the number of independent runs combined at that point and their run-to-run median spread as a percentage (e.g. "5 runs, 4% spread"), or "1,000 samples" when only one run covered that exact size -- so the figure itself shows which boundary points are well-supported vs. which aren't, rather than that having to live only in this README. The 19.87 MiB "near 20 MiB boundary" box is a good example of the latter: 95% spread across 5 runs, correctly flagging it as an unreliable point sitting inside the steep transition rather than a clean boundary marker.
- Known interference: many summary rows show per-point mean/stddev far above the median (batch maxima repeatedly near ~32.5-60k ticks among otherwise ~10-150 tick batches), consistent with occasional OS scheduling interruptions on this shared, multi-user machine rather than a cache effect. Use median (not mean) for boundary inference; report the outlier count and note this in box plots.
- **~20 MiB boundary: superseded by a more precise follow-up (2026-09-10).** An
  initial re-examination of `denseB` (8-points/octave) mistakenly concluded the
  transition began at ~20-22 MiB, based on a jump to 54.07 ticks at 21,757,352 B.
  **This was wrong** — that single point was almost certainly one of this machine's
  well-documented interference spikes, not the start of a real transition. Three
  follow-up sweeps at 200-400 points/octave (`capacity_denseD_boundary{20,25,
  28to42}_random_20260910T175351Z/175438Z/175644Z.csv.gz`, same core/seed/samples,
  `taskset -c 2`, core confirmed >=96% idle via 3 `/proc/stat` samples before
  running) resolved the true shape: computing the **robust floor** (minimum
  ticks/access per 1 MiB bin — immune to upward-only interference spikes, unlike a
  raw median at 8-points/octave resolution) shows the plateau (~48-51 ticks) holds
  essentially flat from 8.39 MiB through **~26 MiB**, with individual points in the
  20-26 MiB range spiking as high as 60-95 ticks (matching this machine's documented
  noise pattern) while the *floor* stays flat — then, starting at ~26-27 MiB, the
  floor itself begins a genuine sustained monotonic climb (50.6 at 26 MiB -> 52.3 at
  27 -> 59.6 at 29 -> 70.2 at 32 -> 96.1 at 38 -> 106.1 at 41 MiB), confirming this is
  a real transition, not more noise. Sequential-pattern control stays perfectly flat
  (10.12-10.124 ticks, zero variation) across the entire 8-42 MiB range, confirming
  the random-pattern floor climb is a genuine cache effect. **Corrected estimate: the
  L2/L3 transition begins at ~26-27 MiB**, not ~20 MiB as originally plotted --
  **PROVISIONAL** (data-grounded floor-based estimate; still not a single precise
  byte value, and not yet cross-checked by an independent test the way L1 was).
  `--boundary 20971520` in the current plots is now known to be measuring noise, not
  the real knee -- regenerate plots with a ~27 MiB boundary flag before using this
  figure in the report. (The ~145 MiB+ DRAM-like plateau below this bullet was
  already confirmed genuine via the rep2/rep3 analysis further down and is
  unaffected by this correction.)
- **Checked for a hidden L2 shelf between L1 (32 KiB) and the ~2-26 MiB plateau
  (2026-09-10): none found — this machine shows exactly two shelves (L1 and the
  ~2-26 MiB plateau above), nothing else.** Two motivations: (1) the coarse
  random-pattern data showed a mild, narrow inflection near 256 KiB (220,432 B ->
  262,144 B: +2.5%, vs. +14-28% immediately before/after — suggestive but not
  conclusive at 8-points/octave resolution); (2) 256 KiB is this chip family's
  textbook per-core L2 size — cited here only as a candidate to test against the
  empirical curve, not as something used to derive a boundary (Phase I stays
  timing-only; this is exactly the kind of cross-check Phase II literature
  comparison is for). A first dense sweep (128-512 KiB, 200 ppo,
  `capacity_denseE_l2check_random_20260910T181421Z.csv.gz`) appeared to show a
  genuine flat shelf at 15.7-15.8 ticks from ~133-173 KiB — but this was a false
  lead: the sweep's own first several points (131,072 B: 20.64 -> 132,896 B: 17.0,
  decaying toward the 15.7 baseline) show the classic signature of the CPU not yet
  at steady-state clock frequency this early in the process, not a cache effect.
  A second sweep starting from a colder 64 KiB (`capacity_denseE_l2check_
  warmstart_random_20260910T181514Z.csv.gz`, same resolution), giving the CPU room
  to reach steady frequency before entering the region of interest, resolved it:
  **one smooth, continuous, monotonic ramp the entire way from 65,536 B
  (14.02 ticks) through 299,040 B (24.66 ticks)** — no shelf anywhere, including no
  shelf at 256 KiB. **Practical lesson for future dense sweeps on this or other
  machines: start the size range meaningfully below the region of actual interest,
  not exactly at its left edge, to avoid mistaking a cold-start frequency-ramp
  artifact for a cache boundary.**
- **Coarse-resolution confirmation of the ~26-27 MiB boundary (2026-09-10):** a
  standard 8-points/octave coarse sweep, 16-28.2 MiB (started well below the region
  of interest per the lesson above), both patterns
  (`capacity_coarseF_boundary26_{random,sequential}_20260910T195504Z/195506Z.csv.gz`).
  Random-pattern medians: flat 48.5-49.1 ticks at 16.78/18.3/19.95/21.76/23.73/
  25.87 MiB, then 51.3 ticks at 28.22 MiB -- consistent with (though coarser than,
  and not contradicting) the high-resolution floor analysis above. Sequential
  stayed perfectly flat at 10.12 ticks across all 7 points, again confirming a real
  cache effect. This coarse grid doesn't happen to land a point between 26-27 MiB
  specifically (octave spacing skips from 25.87 to 28.22 MiB at 8 ppo) -- the
  high-resolution sweeps above remain the precise source for the boundary location
  itself; this pass is corroborating evidence at standard resolution, not a
  replacement for them.
- **Re-verified 256 KiB and ~30 MiB (2026-09-11): neither is a genuine capacity
  boundary -- both are noise/grid artifacts of the coarse-resolution auto-detector,
  not real cache-level transitions. This resolves the "provisional pending capacity
  writeup" flag on the `262144,31457280` boundary pair cited in the line_size/
  section below.** These two exact byte values (262,144 = 256 KiB; 31,457,280 =
  30 MiB) came from an ad hoc "reprocessing" of combined random-pattern summary
  data that was never committed or written up here -- run against
  `scripts/detect_cache_hierarchy.py`'s naive first-jump-past-threshold heuristic,
  which is already documented above (see the 256 KiB / hidden-L2-shelf bullet, and
  the superseded-~20 MiB-boundary bullet) as prone to false positives on this
  machine's noisy coarse grid. Re-ran two fresh, targeted, high-resolution
  (300 points/octave, both patterns, `taskset -c 1` -- core 2 was busy with another
  student's process at the time, confirmed via `/proc/stat` idle-time sampling
  across 3 windows and a `ps --sort=-pcpu` check showing a `git` process at ~92%
  CPU on that core's SMT sibling; core 1/25 sampled 95-99% idle across 3 separate
  windows and used instead) dense sweeps bracketing each value directly:
  `capacity_denseG_256kib_check_{random,sequential}_20260911T232724Z.csv.gz`
  (64 KiB-1 MiB) and `capacity_denseG_30mib_check_{random,sequential}_
  20260911T232756Z.csv.gz` (16-42 MiB).
  - **256 KiB:** confirms the existing denseE warm-start conclusion above (no
    shelf) rather than contradicting it. At 300 ppo the random-pattern median
    right around 262,144 B bounces noisily between ~18.9-24.75 ticks with no
    step, riding the same continuous ramp documented above; the sequential
    control is dead flat at 10.12-10.124 ticks across the entire window.
    `detect_cache_hierarchy.py` run against this fresh summary alone reports
    zero internal boundaries (one "Memory (DRAM)" level spanning the whole
    64 KiB-1 MiB range) -- there is nothing here for a non-noisy detector run
    to have found.
  - **~30 MiB:** sits partway up the already-documented ~26-27 MiB+ monotonic
    climb, not at a separate knee. Random-pattern median is flat ~48.6-49.4
    ticks from 16.78-26.1 MiB (matching the established L2/L3-plateau value),
    then climbs continuously and smoothly through 31,452,392 B (the closest
    grid point to the 30 MiB target, 60.55 ticks) out to 104.4 ticks by
    43.9 MiB -- a continuation of the same trend already documented, not a
    plateau-then-jump. Sequential control again stays flat at 10.12 ticks
    (with only 3 single-point sub-1% blips) the entire way, confirming this
    climb is real and cache-driven, not scheduling noise. One 3-point cluster
    at 31.97-32.11 MiB (102.4 / 88.2 / 137.8 ticks, one point with
    `n_outliers=0` -- i.e. its *entire* 1000-batch sample was elevated, this
    machine's documented signature for a session-level interference event, not
    a per-batch fluke) sits directly on top of the ~60-63 tick trend on both
    sides of it. Running `detect_cache_hierarchy.py` on this window in
    isolation **reproduces the artifact directly**: it reports a hard
    boundary at 31,891,456 B -- locking onto that exact noise cluster, not a
    real transition -- which is very likely the same failure mode (a different
    noise realization on a different run/grid) that originally produced the
    now-suspect 31,457,280 candidate. This is direct, reproduced evidence for
    *why* these auto-detected values shouldn't have been trusted as capacity
    boundaries in the first place, not just an unconfirmed suspicion.
  - **Practical takeaway for the line_size/ results below:** the `262144` and
    `31457280` footprints used there are not sitting at clean single-level
    boundaries -- 30 MiB in particular is inside a region already partway
    toward the deeper DRAM-like tier, not fully "resident in one cache level."
    This doesn't by itself invalidate those line-size measurements (a
    footprint just needs to be a stable, repeatable memory-access regime for
    the stride-sweep method to find a real elbow in; it doesn't strictly need
    to sit at an exact capacity edge), and all three tested levels converged
    on the same 64B result regardless -- but the two footprints should be
    described as "inside the L2/L3-to-DRAM transition region" rather than "at
    a cache-level boundary" in any final writeup, and this is worth
    remembering if a future session re-derives per-level line-size candidates
    from this machine's capacity data.

### line_size/
**Code layout note (post-session cleanup): every run command cited anywhere in this
subsection is historical** -- it shows exactly what was typed at the time, using
whatever script/source names existed then. Since then, `line_size.c`/`.h`
(single-curve) and `line_size_family.c`/`.h` (family-of-curves) have been merged
into one `line_size.c`/`.h` pair, and `run_line_size_family.sh` +
`run_line_size_full.sh` + `run_line_size_sweep.sh` have been merged into one
`scripts/run_line_size.sh` that runs both methods per cache level and reports
whether they agree (see that script's own header comment). A future re-run on
this or any other machine should use
`scripts/run_line_size.sh <machine> <core> <boundaries_csv>`, not any of the
per-method names cited below.
- Source file(s): `main_code/common/{main.c,line_size.c,line_size.h,benchmark.c,benchmark.h,pointer_chase.c,pointer_chase.h,random.c,random.h}`, `main_code/x86_64/timer_x86.h`, `main_code/common/timer.h`
- Build command: `make` (from repo root; see `Makefile`)
- Run command + arguments: `./scripts/run_line_size_full.sh sunbird 20` (auto-picks footprint; pinned via `taskset -c 20`). This run predates bug (2) below, so it hit the glob bug and fell back to `footprint_bytes=65536` with a misleading "no capacity summary found" warning (see caveat below) -- coarse random+sequential sweep 8-1024B stride (step 8) -> dense sweep 64-257B (step 1) around the (at-the-time, wrongly-computed) estimate -> 2 independent dense repeats -> plots. Raw: `data_raw/sunbird/line_size/line_size_{coarse,dense,dense_rep1,dense_rep2}_{random,sequential}_20260909T202041Z.csv` (not yet gzipped), log `run_line_size_full_20260909T202041Z.log`. Core 20's SMT-sibling/quiet-machine status was not logged for this run -- TODO: confirm with `lscpu -e` / `who` / `ps` before treating this as a fully clean run, per the project's affinity discipline.
- Sample count: 1,000,000 timed accesses per (stride, pattern) point; warm-up (3 full untimed chase passes) excluded from that count
- Random seed: 12345 (xorshift32, `make_random_cycle_strided`); sequential-pattern runs use `make_sequential_cycle_strided` (no seed/randomness)
- Line-size estimate: **64 bytes**, from `scripts/detect_line_size.py`'s ramp-saturation detector (`python3 scripts/detect_line_size.py data_processed/sunbird/line_size/coarse_random_summary.csv`) -- median latency rises monotonically 14.0->17.1 ticks from stride=8B to stride=64B (more nodes packed per line at small stride means a random chase step has a higher chance of landing back in the already-resident current line), then plateaus flat at ~17.1 ticks through stride=128B (9 clean points, 0% run-to-run spread across the dense sweep's independent repeats -- see `plots/line_size_boxplots.png`), before a separate, later capacity-driven fall-off to ~10.1 ticks at stride=136B (this fall-off point is NOT the line size -- see `detect_line_size.py`'s module docstring for why it's biased by footprint_bytes/L1_capacity instead).
- **Caveats / notes on alignment and candidate strides tested:**
  - **Two pipeline bugs found and fixed this session** (see git history / CLAUDE.md for detail): (1) `detect_line_size.py` previously keyed its estimate off that capacity-driven fall-off (reporting 128B) instead of the ramp-saturation plateau -- the fall-off's stride scales with `footprint_bytes/L1_capacity` and is not the line size; rewritten to find the plateau directly, which needs no such correction. (2) `run_line_size_full.sh`'s footprint auto-selection glob matched `coarse_ext256_random_summary.csv` (a wide, coarse tail-extension sweep with no clean boundary) ahead of the actual `coarse_random_summary.csv`, alphabetically, silently falling back to a hardcoded default footprint with a misleading "no capacity summary found" warning even though a good one existed; fixed to skip `*ext*` files and verify a candidate file actually yields a boundary before accepting it.
  - Strides that divide the 4096B page into very few pieces (256B, 512B, and the max swept stride 1024B observed here) show isolated single-point latency spikes well above their neighbors, in both random and sequential patterns -- a page/set-aliasing artifact, not line-size or capacity signal. `plot_line_size.py` now auto-flags these (red circles in `line_size_curve.png`) rather than letting them read as part of the curve.
  - The `MULTIPLIER` used to pick `footprint_bytes` from an L1 boundary was bumped from 1.2x to 2.0x this session -- 1.2x-1.5x left only 0-3 clean plateau points before the capacity-driven fall-off, too few for the detector's default 5-point confirmation window; 2.0x reliably leaves ~8-9.
  - The dense-sweep box plot shows the point immediately above the estimate (65B) reading notably higher (~18.5 ticks) than 64B itself (~17.1 ticks) despite differing by only 1 byte -- plausibly an unaligned-access penalty specific to an odd (non-power-of-two) stride rather than a line-size effect; flagged here, not yet explained, TODO for Phase II.
  - `footprint_bytes=65536` here came from the pipeline's hardcoded fallback, not an actual measured L1 boundary (bug (2) above meant no capacity boundary was found for this run) -- but it happens to be a reasonable value anyway (2x this machine's team-established ~32 KiB L1 estimate from the capacity section above). Re-running now with the glob fix does NOT automatically do better: it picks up `coarse_random_summary.csv` fine, but `detect_cache_hierarchy.py`'s automatic first-boundary on that file is 285864B (~279 KiB) -- nowhere near the ~32 KiB L1 this team already established by hand in the capacity writeup above, so it would hand this pipeline a ~560 KiB footprint instead. That's a pre-existing limitation in `detect_cache_hierarchy.py`'s coarse-grained first-pass heuristic, not something this session's fixes touched. Until that's revisited, prefer an explicit `--footprint-bytes` override (e.g. 65536, as used here) over trusting the auto-selected footprint on this machine.
  - **This actually happened, immediately:** `./scripts/run_line_size_full.sh sunbird 20` was re-run (`source`d directly in a terminal -- see `run_line_size_full_20260909T205256Z.log`, and note it also got appended, garbled with shell-prompt text, into the older `..._20260909T202041Z.log` because `source`ing the script leaves its `exec > tee` redirect attached to the *interactive* shell instead of a subshell -- harmless here but worth invoking this script with `./scripts/...` or `bash scripts/...`, not `source`, going forward). That re-run auto-picked `footprint_bytes=571728` (558 KiB) exactly per the paragraph above, produced a noisy/non-monotonic curve, and correctly got `no line-size transition detected` from the fixed `detect_line_size.py` -- but it still overwrote `coarse_{random,sequential}_summary.csv` and the plots with that noisy, no-signal coarse-only data (dense/repeat stages were skipped, since detection had failed). Restored by re-summarizing from the still-good `line_size_coarse_{random,sequential}_20260909T202041Z.csv` raw files back onto `data_processed/sunbird/line_size/coarse_{random,sequential}_summary.csv`, then re-plotting against the (untouched) dense/dense_rep1/dense_rep2 summaries -- back to the 64B estimate and clean plot described above. `run_line_size_full.sh` now prints an explicit, actionable warning (naming this exact failure mode and suggesting the override) instead of silently completing when this happens again.

- **Family-of-curves sub-experiment (PROJECT 1.pdf's Figure 3 / "Example B" requirement) -- superseded three times now, current architecture is per-cache-level with a MANUAL step-4 candidate (auto-detection removed, see Attempt 4).** History, most recent first (each bullet below is a full retelling of the fix that produced it, not just a result -- the earlier attempts are kept for the record, not because they're still trustworthy; see the code-layout note at the top of this line_size/ section for current script/source names):
  - **Attempt 4 (current, authoritative): keeps attempt 3's per-cache-level architecture but removes Method-A's automatic step-4 candidate selection.** Two exploratory re-runs of attempt 3's own auto-detection (identical boundaries/strides/seed, only the pinned core changed) showed the coarse pass's candidate was NOT reproducible: core 1 (`run_line_size_20260911T182443Z.log`) picked 32B/16B/32B for the 32768/262144/31457280B levels respectively; core 0 (`run_line_size_20260911T185011Z.log`) picked 16B/64B/8B for the same three levels. Boundaries used for these and the final run below: `32768,262144,31457280` -- note the latter two differ from attempt 3's `20971520,157286400` because they're sourced from an in-progress reprocessing of this machine's random-pattern-only capacity data (`data_processed/sunbird/capacity/coarse_combined_random_summary.csv` and siblings) that was **not written up in this README's capacity/ section at the time this bullet was written. Resolved 2026-09-11: see the "Re-verified 256 KiB and ~30 MiB" bullet in the capacity/ section above -- both values turned out to be noise/detector artifacts, not genuine capacity boundaries** (262144 rides a continuous, boundary-free ramp; 31457280 sits partway up the already-documented ~26-27 MiB+ climb, and a fresh high-resolution re-run of the same detector on that exact window reproduces a spurious boundary by locking onto a 3-point interference spike). This does not invalidate the 64B line-size results below on its own (see that bullet's practical-takeaway note), but these two footprints should be described as sitting inside the L2/L3-to-DRAM transition region, not at a cache-level edge. Root cause of the instability: `infer_line_size()` (`scripts/plot_line_size_family.py`) anchors to the largest tested stride's elbow, which is the right design (see that function's docstring), but the underlying elbow values it's comparing come from a single, un-repeated, 6-points-per-octave coarse sweep -- noisy enough that which smaller stride's elbow happens to fall inside the 1.2x agreement ratio flips from run to run. Worse, a wrong (too-small) candidate's own step-4 offset check can still look clean: below the true line size, packing multiple nodes per line is roughly offset-insensitive too, so "N/8 offsets agree" doesn't by itself validate a candidate (confirmed directly -- core 0's spurious 16B pick for the L1 level passed its own step-4 check at "7/8 offsets, 1.00x spread", every bit as clean-looking as a correct candidate would be). **Fix: `scripts/run_line_size.sh` no longer auto-applies this estimate.** Steps 1-3 (coarse pass, `line_size_family_curve.png`) still run unconditionally for every level; the coarse pass's own diagnostic elbow/estimate is still computed and printed to the log (useful as a hint) but step 4 is now skipped for any level whose `candidate_overrides_csv` field is left blank, with an explicit message pointing at that level's plot and asking for a manual candidate on the next invocation -- see the script's header comment for the full rationale and usage. Final run: all three levels manually forced to **64B** (chosen by inspecting each level's `line_size_family_curve.png` -- all three show the same textbook split, {8,16,32B} clustering separately from {64,128,256B}), `taskset -c 1`, timestamp `20260911T200548Z`, log `run_line_size_20260911T200548Z.log` (this is the authoritative raw/plot data for the three `level_<boundary>/` directories cited below; the two exploratory auto-detect logs above are kept only as evidence for the instability finding, not as a source of trustworthy line-size numbers).
    - **Level boundary=32768B (L1) -- RESULT: 64B, but this particular run's own step-4 check was noisy (3.56x spread, 1/8 offsets with no detectable elbow at all; see `plots/line_size_offset_elbow.png`) -- a spike at offset=0B/stride=64B and at offset=32B/stride=80B, several offsets only partially covered.** Don't over-read this one run in isolation: Method B independently reads 64B here (as it does in every run on this machine so far), and attempt 3's dedicated, earlier run of this exact level already produced a clean 64B confirmation (5/8 offsets, 36736 bytes, documented above) -- the noise here is sampling variance in one more coarse pass, not a contradiction of the established result.
    - **Level boundary=262144B -- RESULT: 64B, clean (but see 2026-09-11 correction: this footprint is NOT a real capacity boundary, just a point on a continuous ramp -- see the capacity/ section's "Re-verified 256 KiB and ~30 MiB" bullet).** `plots/line_size_offset_elbow.png` shows a tight V bottoming right at stride=64B with all 8 offsets visually overlapping (printed spread 1.41x, 8/8 offsets reporting -- the printed ratio undersells how clean this looks visually). Method B found no ramp-saturation signal in its own coarse sweep at this footprint (consistent with the "no separation at deeper levels" pattern already documented at the 20/150 MiB levels above -- not a contradiction).
    - **Level boundary=31457280B (~30 MiB) -- RESULT: 64B, the cleanest of the three (but see the same 2026-09-11 correction: this footprint sits partway up the ~26-27 MiB+ climb, not at a distinct level's edge).** `plots/line_size_offset_elbow.png` shows a sharp, tight V at exactly stride=64B, 8/8 offsets essentially coincident (1.12x spread). Method B also independently reached 64B for this level in the core-0 exploratory run (`run_line_size_20260911T185011Z.log`) -- the first time Method B has produced any result this deep; it found none in the final (core-1) run's coarse sweep, consistent with Method B being less sensitive at this depth in general, not a disagreement.
    - **Net Phase-I verdict: 64B is the best-supported line size on this machine across every level and both methods to date.** Raw data: `data_raw/sunbird/line_size/level_{32768,262144,31457280}/*.csv.gz` (gzipped after collection by hand -- unlike `run_capacity_full.sh`, `run_line_size.sh` does not gzip its own output yet; worth adding to that script later). Plots: `data_processed/sunbird/line_size/level_{32768,262144,31457280}/plots/`.
  - **Attempt 3 (superseded for candidate SELECTION only -- its per-level architecture and its L1 result both still stand, corroborated by Attempt 4 above): per-cache-level independent sweeps, auto-detected candidate.** The original single-sweep design (attempt 1 below) ran one footprint sweep spanning the WHOLE range (1 KiB to 64+ MiB) and let one elbow detector pick whichever transition crossed its threshold first. That's a real design flaw: a small, early bump near the L1 boundary can (and did, in attempt 2) get reported as "the line size" while a much more dramatic, later stride-dependent separation near a deeper cache level goes undetected because the detector already fired. Fixed by restructuring `scripts/run_line_size_family.sh` to take a list of this machine's OWN, already-established capacity-experiment boundaries (`32768,20971520,157286400` = the same ~32 KiB / ~20 MiB / ~150 MiB boundaries this README's capacity/ section cites, sourced from `--boundary` values already passed to `plot_capacity.py` there, not re-derived or guessed) and run all 5 Example-B steps completely independently within a narrow window around EACH boundary (`[boundary/8, min(boundary*4, 256 MiB)]`), each with its own coarse pass, its own auto-detected candidate, its own step-4 bracket+offset refine, and its own plots -- rather than one sweep and one number. Deliberately does NOT use sysfs/`lscpu` cache sizes to pick the windows (those come from Phase II documented specs, not Phase I timing); the boundaries are the machine's own timing-measured capacity transitions.
    - Run command: `./scripts/run_line_size_family.sh sunbird 0 32768,20971520,157286400` (default candidate strides 8/16/32/64/128/256B; 6 points/octave; both patterns for the coarse pass, random only for step-4 refine). `taskset -c 0`; core selected by sampling `/proc/stat` idle-time deltas across 3 separate ~3-4s windows (not a single `ps` snapshot -- see the Known constraints in the top-level `CLAUDE.md`) after `ps`/`/proc/stat` showed another student's own `cache_bench` pinned at ~99.5% CPU on core 2 (also inside this session's allowed cpuset, `0-2,24-26`) moments earlier; core 0 (and its SMT sibling, logical CPU 24) read ~95-100% idle on every sample and was used instead. Timestamp `20260910T220442Z`; full transcript `data_raw/sunbird/line_size/run_line_size_family_20260910T220442Z.log`.
    - Sample count: 1,000,000 timed accesses per (footprint, stride, offset, pattern) point; seed 12345; align-bytes 4096 -- all identical to every other run on this machine.
    - Output layout changed: everything now lives under a per-level subdirectory keyed by its boundary in bytes -- `data_raw/sunbird/line_size/level_<boundary>/{family,refine}_*.csv.gz` (gzipped, ~111 MiB -> ~10.3 MiB), `data_processed/sunbird/line_size/level_<boundary>/{family,refine}_*_summary.csv`, `data_processed/sunbird/line_size/level_<boundary>/plots/line_size_{family_curve,family_boxplots,offset_elbow,offset_boxplots}.{png,pdf}`. The old flat (non-per-level) `family_*`/`refine_*` raw+processed+plot files from attempts 1-2 (timestamps `20260910T040650Z`, `204702Z`, `214111Z`, `215035Z`) were deleted as part of this rewrite -- superseded, not archived, since (unlike Artemisia's core-23-vs-20 redo) the earlier flat architecture had no comparative value once the per-level restructure landed; the numbers are recorded here instead.
    - **Level boundary=32768B (~32 KiB L1), window=[4096,131072] bytes -- RESULT: 64B.** Coarse-pass per-stride elbow: `{8B: 58384, 16B: None, 32B: None, 64B: 36736, 128B: 36736, 256B: None}` (16B/32B/256B never rose >=1.3x above their own low-footprint baseline within this narrow window -- see `plots/line_size_family_curve.png`'s dotted/faint handling of those, not a bug, just this window being too narrow to catch their slower rise). Visually, `line_size_family_curve.png` shows the textbook Figure-3 shape: all six strides track each other almost exactly below ~32 KiB, then split sharply right at 32768 bytes into two clusters -- {8,16,32B} lower and slower-rising, {64,128,256B} upper and fast-saturating to ~17 ticks. Step 4 bracketed 64B at 8-byte granularity (40/48/56/64/72/80/88B) and repeated at the fixed 0/8/16/24/32/40/48/56B offset span. **Correction (user caught this from the plot, second bug this session):** `plot_line_size_offset.py` originally dropped any (stride, offset) pair with no detectable elbow and silently connected whatever points remained with a straight line -- bridging directly across missing measurements as if they were a real trend (e.g. offset=40B's line jumped straight from stride 40 to stride 64, skipping the missing 48B/56B points entirely). Fixed by plotting every offset against the full stride axis with `NaN` at missing strides, so matplotlib breaks the line at real gaps instead of interpolating through them, and by making the printed verdict state the gap count explicitly rather than only reporting a spread over whatever happened to be present. Re-running the (already-collected) data through the fixed script shows the honest picture: only **5 of the 8 tested offsets** (0/8/16/24/40B) produced a detectable elbow at stride=64B at all within this narrow window -- 32B/48B/56B did not (not a disagreement, just no crossing of the detector's threshold in this range). Of the 5 that did report a value, 4 agree exactly at 36736 bytes and one (offset=40B) reads lower at 32768 bytes (1.12x spread) -- see `plots/line_size_offset_elbow.png` for the corrected chart, now with visible gaps rather than false bridging lines. This is still the machine's best Phase-I line-size evidence (a real, tight pinch at exactly stride=64B among the offsets that resolved), but it is 5/8-offset support, not the "every one of the 8 offsets" this bullet previously and incorrectly claimed -- widening this level's footprint window would be needed to get all 8 offsets to resolve before citing full agreement.
    - **Level boundary=20971520B (~20 MiB), window=[2621440,83886080] bytes -- RESULT: no separation.** Per-stride elbow: `{8B: 29658208, 16B: 26422448, 32B: 26422432, 64B: 29658176, 128B: 29658112, 256B: 29658112}` -- all six land in a tight 26.4-29.7 MiB cluster regardless of stride; step 4 was skipped (nothing to bracket). Not treated as a failure: whether two nodes share one physical line is an L1-fetch-granularity question, and once footprint is well past L1 the transition is governed by total distinct-line/set pressure against L2/L3 capacity, which an 8-256B stride difference doesn't meaningfully change -- no separation here is the physically expected outcome, not a tooling gap.
    - **Level boundary=157286400B (~150 MiB), window=[19660800,268435456] bytes (upper bound capped from 600 MiB to the pipeline's 256 MiB ceiling to keep wall time reasonable) -- RESULT: no separation.** Per-stride elbow: `{8B: 24771056, 16B: 27804560, 32B: 27804544, 64B: 31209536, 128B: 31209472, 256B: 31209472}` -- again one tight 24.8-31.2 MiB cluster, no candidate separated, step 4 skipped. Same explanation as the 20 MiB level.
    - This L1-level family-of-curves result also agrees with the independently-run single-curve `--experiment line_size` ramp-saturation result documented earlier in this section -- two independently-designed Phase-I, timing-only methods converging on the same candidate.
    - Caveat: only the L1-level window produced a candidate at all; the 20 MiB and 150 MiB windows show no stride-dependent signal in this design, so they neither confirm nor contradict the L1-level candidate. If a second independent per-level confirmation is wanted later, consider a finer candidate-stride list or a more sensitive elbow detector specifically for those deeper windows -- not attempted here. Phase II (PMU counters, then documented/system-reported specs) is still outstanding and untouched by this session's work -- deliberately not previewed here.
  - **Attempt 2 (found broken by user inspection of the resulting plot, now deleted): single sweep, offsets scaled to the candidate.** Same single-window design as attempt 1 but added a step-4 offset re-test. `compute_offsets()` derived offsets as quarters of whatever candidate the coarse pass auto-detected (`0, c/4, c/2, 3c/4`). When the coarse pass (wrongly, see below) picked a small candidate like 16B, this produced offsets of 0/4/8/12 bytes -- far too fine to probe a different position relative to a REAL physical cache line (essentially always >=32B on any real machine), and tied the offset scale to a candidate that was itself likely wrong. User caught this from the resulting elbow-vs-stride plot looking chaotic with no interpretable signal. Fixed by decoupling offsets from the candidate entirely: a fixed 0/8/16/24/32/40/48/56B span (one full period of the most common real line size, 64B) at the same 8-byte granularity as the stride bracket, regardless of which candidate is being refined -- this fix is what's live in the current script and used by attempt 3.
  - **Attempt 1 (superseded, now deleted): single sweep, one global elbow detector.** `--experiment line_size_family` (`main_code/common/line_size_family.{c,h}`) was added this session as a third experiment alongside `capacity`/`line_size` (capacity.c has no stride parameter; line_size.c always sweeps stride at one fixed footprint -- neither can produce the Figure-3 family-of-curves shape). First version ran ONE footprint sweep (1 KiB-64 MiB, 6 points/octave, both patterns, `taskset -c 2`) across all six candidate strides and inferred a line size from wherever any curve's elbow first separated from the shared low-stride baseline by >=1.3x. Result was **32B** (per-stride elbow `{8B: 294240, 16B: 262144, 32B: 208064, 64B: 208064, 128B: 208000, 256B: 185344}`), which disagreed with attempt 3's L1-level result and with the independently-run single-curve `--experiment line_size` result above -- inspecting the underlying curve plot showed all six strides overlapping almost exactly up to ~2 MiB with only a small early wiggle, meaning the detector had locked onto a noise-level bump rather than a genuine stride-dependent transition, exactly the failure mode attempt 3's per-level restructuring exists to avoid. Superseded; not a citable line-size number for this machine.

### associativity/
- Source file(s): `main_code/common/{main.c,associativity.c,associativity.h,benchmark.c,benchmark.h,pointer_chase.c,pointer_chase.h,random.c,random.h}`, `main_code/x86_64/timer_x86.h`, `main_code/common/timer.h`
- Build command: `make` (from repo root; see `Makefile`)
- Run command + arguments: `./scripts/run_associativity_full.sh sunbird 2 32768` (pinned via `taskset -c 2`, same physical core/SMT-sibling-idle setup as the capacity section above; `who`/`ps` checked immediately before this run -- one other user logged in, all their processes idle, load average 1.02). `32768` (32 KiB) is this team's hand-confirmed L1 capacity from the capacity section above, passed as an explicit override -- NOT auto-detected from `detect_cache_hierarchy.py`, whose coarse first-pass boundary (285864B / ~279 KiB) is already documented as unreliable for L1 on this machine (see the line_size section above and `run_associativity_full.sh`'s header comment). **LLC associativity has since been attempted (2026-09-10) -- see the LLC subsection below; results were inconclusive, not confirmed.**
- Conflict-set construction method: node-to-node stride fixed at `cache_bytes` (32768 for this run) in a dependent pointer-chase cycle; since capacity = sets * line_size * ways is by construction a whole multiple of one set's address period, every node landed in the same cache set regardless of the (still unmeasured) line size or associativity, while getting a distinct tag each time (see `main_code/common/associativity.h`'s module docstring for the full argument). Swept `num_ways_probed` (cycle length) linearly from 2 to 64, one node added at a time, both randomized and sequential-order chase (`--pattern`), 1,000,000 timed accesses per point (batch size 1000), 3 untimed warm-up passes, seed 12345.
- Raw output filename(s): `data_raw/sunbird/associativity/L1/associativity_{base,rep1,rep2}_{random,sequential}_20260910T170145Z.csv.gz`
- Processing script -> data_processed path: `python3 scripts/summarize_raw.py <raw.csv> -o data_processed/sunbird/associativity/L1/<name>_summary.csv`, then `python3 scripts/detect_associativity.py data_processed/sunbird/associativity/L1/base_random_summary.csv` for the knee estimate, then `python3 scripts/plot_associativity.py data_processed/sunbird/associativity/L1/*_summary.csv -o data_processed/sunbird/associativity/L1/plots --machine sunbird --level L1 --estimate 8` for the curve and box-plot figures (all done automatically by `run_associativity_full.sh`).
- Result: **8-way** at L1 (cache_bytes=32768). Median latency is flat at ~10.1-11.6 ticks/access for `num_ways_probed` 2 through 8 (0% run-to-run spread across 3 independent runs at num_ways=8), then jumps sharply to ~21.2 ticks at num_ways=9 (also 0% spread) and ~25.1 ticks by num_ways=10 -- a step, not a ramp, consistent with a cyclic dependent chase over N distinct blocks thrashing completely once N exceeds the set's way count. See `data_processed/sunbird/associativity/L1/plots/associativity_curve.png` and `associativity_boxplots.png`. **Follow-up (2026-09-10): this post-L1-thrashing latency (~25.0-25.1 ticks) turns out to itself be a genuinely important signal -- it stays flat and clean for num_ways=10 through 37 (28 points, essentially 0 noise), well below LLC's independently-established ~48-51 ticks/access (see capacity section). Since these spilled-over accesses scatter across many sets of whatever level absorbs them (32,768 isn't a multiple of that level's own set-stride the way it is for L1), this is very likely genuine L2 hit latency, not a conflict artifact -- see the new L2 candidate subsection below, which corroborates this independently at a different `cache_bytes`.**
- Notes: Latency drifts upward again gradually past num_ways~28-30 (both patterns), most visibly in the sequential-pattern curve, and gets noisier (higher run-to-run spread, e.g. 30-40% at several points above num_ways~29) than the clean L1 knee itself. This is most likely TLB/page-walk pressure as the touched virtual footprint grows past `num_ways * 32 KiB` (at num_ways=64 that's still only 2 MiB, but each node lives on its own page here since the stride equals a full 32 KiB, so it's really 64 distinct pages, not 64 distinct 32 KiB regions of a shared page set) rather than a second cache-level effect -- not investigated further since it sits well above the L1 knee this run was targeting; flag as a follow-up if a later experiment needs a clean baseline at large num_ways.

#### L2 candidate (exploratory, 2026-09-10) -- evidence for a real level, associativity number not trustworthy

Motivated by the L1 test's own post-thrashing plateau (~25.0-25.1 ticks,
see above) sitting well below LLC's ~48-51 ticks -- a distinct third tier,
not a transition toward LLC. The capacity section's coarse random-pattern
data shows ~25 ticks/access occurring around 310-370 KiB, close to this
chip family's textbook per-core L2 size (256 KiB) -- cited as a candidate
to test, not used to derive anything. Ran `cache_bytes=262144` (256 KiB,
a valid power of two) as an explicitly exploratory attempt (real L1 output
moved aside first, same collision-avoidance procedure as the LLC attempts
below; archived to `LLC_16MiB`-style naming as `L2_256KiB_candidate/`),
`taskset -c 2`, core confirmed idle first, same samples/batch/warmup/seed.

- Auto-detector estimate: 4-way. **But the curve is a multi-step staircase,
  not a single knee** -- flat 10.07 (num_ways 2-4, matches L1 hit latency),
  step to 18.06 (5-8), a single-point dip to 12.12 at num_ways=9 (likely
  noise), then **flat at 24.996-25.06 for num_ways 10-16 -- matching the
  L1 test's independently-found ~25-tick tier almost exactly**, then
  further steps: ~33.0 (18-34), ~40.3 (35-45), ~44-46 (46-59), climbing
  toward ~49-53 by num_ways=60-64 (approaching LLC's range). Sequential
  pattern shows the same staircase shape (as expected for this experiment
  -- unlike the capacity experiment's sequential control, both associativity
  patterns touch the identical set of addresses, just in a different visit
  order, so matching curves here is a consistency check passed, not a
  surprise).
- **Interpretation: the ~25-tick corroboration is the trustworthy part of
  this result -- it now agrees between two independent tests (this one and
  the L1 test's spillover), which is real evidence for a genuine
  intermediate cache level with roughly that hit latency.** The *specific*
  "4-way" estimate from this test should **not** be taken at face value,
  though: a clean single-level associativity test (like the real L1 one)
  produces exactly one step; this one produces five-plus. The additional
  steps beyond the first are most plausibly a confound from testing at a
  stride that doesn't align cleanly with any one level's own true
  structure (the same failure mode already documented for the LLC attempts
  below, just producing more visible internal structure here rather than
  one big jump) -- not five real nested cache levels. **Net conclusion: this
  session now has good evidence a real L2 (or some genuine intermediate
  level) exists with ~25 ticks/access hit latency, but not a trustworthy
  associativity (way-count) number for it.** Pinning that would need a
  properly-isolated stride, which in turn needs the L2's true capacity
  (not just its hit latency) determined independently first -- e.g. a
  dedicated dense random-pattern capacity sweep across ~128 KiB-1 MiB to
  find where the smooth ramp's *rate* changes, rather than relying on the
  256 KiB textbook guess used here.
- **Follow-up (2026-09-10): slope analysis of already-collected capacity data,
  then a second candidate at 131,072 B (128 KiB).** Binning the clean
  warm-started dense sweep (65,536-299,040 B, see capacity section) together
  with coarse data out to 2 MiB and computing ticks-per-octave shows the ramp
  *decelerating* from ~4.9 down to a minimum of ~1.1-1.2 around 121-155 KiB
  (the flattest point in the whole ramp outside the confirmed plateaus), then
  *re-accelerating* from ~175 KiB onward -- the classic signature of a real
  level's capacity being approached then exceeded under random access. This
  motivated testing 131,072 B (128 KiB, also a valid power of two) as a
  second, better-data-grounded L2 candidate.
  - Result (`data_raw/sunbird/associativity/L2_128KiB_candidate/`,
    `data_processed/sunbird/associativity/L2_128KiB_candidate/`, timestamp
    `20260910T214703Z`): flat 10.07-10.39 (num_ways 2-4), step to 18.06
    (5-8), step to ~26.6-27.4 (9-16, matching the ~25-tick tier within normal
    run-to-run variation -- a *third* independent corroboration of that
    tier), then noisy ~40-49 for num_ways>=17 with no further clean step.
  - **This is nearly identical in shape to the 256 KiB result** (same two
    initial tiers: flat 10.07 for 2-4, flat 18.06 for 5-8, before reaching
    the ~25-27 tick tier) -- reproducible across two different candidate
    byte values, so it's a real effect, not noise from one run. But **neither
    breaks at num_ways=9 the way L1's own clean test did at its correct
    stride (32,768 B)** -- both break at num_ways=5 instead, which does not
    match an "L2 is also 8-way" hypothesis. Not yet explained: 131,072 and
    262,144 are both multiples of L1's own 4,096-byte set-stride (sets x
    line_size, for a 32,768 B / 8-way / 64 B-line L1), so by the same
    reasoning that correctly predicted L1's clean break at 9 for stride
    32,768, both larger strides should show that same break -- they don't,
    consistently. Root cause not yet identified (candidates not yet ruled
    out: TLB set-associativity interacting with the larger inter-node page
    stride, or some other confound specific to strides larger than L1's own
    capacity) -- flagged as an open question rather than guessed at further.
  - Plots for both `L2_128KiB_candidate` and `L2_256KiB_candidate` (and the
    `LLC_16MiB`/`LLC_32MiB` attempts below) were regenerated with corrected
    `--level` labels after an initial run -- `run_associativity_full.sh`
    always titles its first (only, in these single-value invocations) level
    "L1" internally regardless of the `cache_bytes` value tested, which is
    correct behavior for its intended one-shot-per-level usage but produced
    misleading plot titles here since these were all run as one-off L1-slot
    substitutions (see the collision-avoidance procedure described above).
    The underlying data was always correct throughout (verified directly
    from each raw CSV's own `cache_bytes` header field and per-row column);
    only the plot titles needed fixing, not the experiment itself.

#### LLC (exploratory, 2026-09-10) -- inconclusive, not a confirmed result

The capacity section above pins the LLC boundary at ~26-27 MiB via a robust
floor analysis, but `--cache-bytes` is hard-validated as an exact power of
two (`main.c`), and ~26-27 MiB isn't one -- ruled out a hidden L2 shelf
first (see capacity section) before spending associativity time here, since
that would have changed which level this actually tests. Ran both power-of-
two values bracketing the estimate as explicitly provisional attempts,
`taskset -c 2`, core confirmed >=96% idle first, same samples/batch/warmup/
seed as the L1 run. To avoid colliding with `run_associativity_full.sh`'s
fixed "first level = `L1/`" directory naming, the real L1 output was moved
aside before each run and the result relabeled afterward (documented here
for reproducibility, not part of the script itself):

- **16 MiB** (`data_raw/sunbird/associativity/LLC_16MiB/`,
  `data_processed/sunbird/associativity/LLC_16MiB/`, timestamp
  `20260910T181751Z`): auto-detector estimate 6-way, but the curve is a
  **staircase, not a single step**: flat 10.07 ticks through num_ways=6,
  a small bump to ~12.6-14.3 at 7-9, then a large jump to ~47.8 at
  num_ways=10 and ~54-57 for num_ways>=16 -- with 22-29% run-to-run spread
  at several points, unlike L1's 0%-spread clean knee.
- **32 MiB** (`data_raw/sunbird/associativity/LLC_32MiB/`,
  `data_processed/sunbird/associativity/LLC_32MiB/`, timestamp
  `20260910T181912Z`): auto-detector estimate 5-way, same staircase shape:
  flat 10.07 through num_ways=5, a step to ~17 at 6-8, another step to
  ~24 at num_ways=9, then a large jump to ~54-57 for num_ways>=10.

**Interpretation: neither result should be read as "LLC is 5-way" or
"6-way."** A multi-step staircase, not L1's clean single step, is exactly
what the conflict-set-construction method predicts when `cache_bytes`
doesn't exactly equal the true capacity (`associativity.h`'s doc comment:
the same-set guarantee requires capacity to be a whole multiple of the
stride, which an arbitrary nearby power of two isn't) -- the two steps
likely correspond to the working set (`num_ways * cache_bytes`) crossing
other unrelated size thresholds rather than any single set's true way
count. That both power-of-two brackets around the ~26-27 MiB estimate
produced the same qualitative failure mode is itself evidence the true
LLC capacity genuinely isn't a nearby power of two -- consistent with real
multi-socket Xeon LLC capacities often not being exact powers of two.
**This associativity method as currently implemented cannot cleanly test
Sunbird's LLC without either a non-power-of-two `--cache-bytes` (would
need the hard validation in `main.c` relaxed, out of scope for this
session) or a much more precise capacity estimate that happens to land on
a power of two.**

#### Order-sensitivity re-check on both candidates (2026-09-11, hardened pipeline)

Following external review of `run_associativity_full.sh` (see CLAUDE.md's
"Pipeline hardening" bullet), that script's reproducibility repeats now use a
distinct seed per repeat (`base_seed + repeat_index`) instead of one fixed
seed for every run, specifically to test whether the L2/LLC candidates'
multi-step staircases (above) are sensitive to the dependent chase's access
*order*, not just to plain measurement noise. Also re-tested "~30 MiB" from a
fresh user request by substituting the nearest valid power of two, 32 MiB
(`--cache-bytes` is hard-validated as an exact power of two; 31,457,280 itself
is rejected) -- this is the same `LLC_32MiB` candidate already tested above,
so this re-check reuses that directory rather than creating a new one.
Re-ran both `L2_256KiB_candidate` (262144) and `LLC_32MiB` (33554432) directly
via `cache_bench` (bypassing `run_associativity_full.sh`'s own per-index
`L1`/`L2`/`L3_LLC` labeling, which would have collided with the real L1
directory for either a 1- or 2-element override list -- same collision this
README's L2/LLC subsections above already document working around by hand):
base run at seed 12345 (same seed as every prior run on this machine, for
comparability), then 2 repeats at seeds 12346 and 12347; `--max-ways 40`
(this session's new default, see CLAUDE.md); `taskset -c 1` (core 2 was busy
with another student's `git` process at ~92% CPU on its SMT sibling at the
time, confirmed via `/proc/stat` idle-time sampling across 3 windows plus
`ps --sort=-pcpu`; core 1/25 sampled 95-98.5% idle across 2 separate windows
and used instead). Raw:
`data_raw/sunbird/associativity/{L2_256KiB_candidate,LLC_32MiB}/associativity_{base,rep1,rep2}_{random,sequential}_20260911T23{4957,5003}Z.csv.gz`.
Processed summaries are timestamped (`*_summary_<ts>.csv`) per the same
hardening, sitting alongside (not overwriting) the original un-timestamped
`base_random_summary.csv` etc. from the 2026-09-10 single-seed runs above.

- **`L2_256KiB_candidate` is genuinely order-sensitive.** The naive
  first-knee detector reports a different estimate at every seed --
  base(12345)=3, rep1(12346)=4, rep2(12347)=4 -- and the underlying curves
  differ in more than just which number the detector picks: the big jump
  into the ~44-48 tick tier happens at num_ways=17 in base and rep2, but at
  num_ways=11 in rep1, a real, substantial shift in *where* the curve breaks
  depending only on which pseudo-random node order was chased. This is
  exactly the kind of order-dependence a pseudo-LRU (tree-based, not true
  LRU) replacement policy could produce, and is new evidence beyond what the
  single fixed-seed run above could show.
  - **One feature is NOT order-sensitive, though, and is worth flagging on
    its own: all three seeds show a sharp single-point dip to ~12.07-12.13
    ticks specifically at num_ways=9**, bracketed by ~17-19 ticks on both
    sides. num_ways=9 is exactly where the real, hand-confirmed L1 result
    (cache_bytes=32768) breaks from its flat plateau. Seeing an anomaly
    recur at precisely that same way-count here -- at a completely different
    `cache_bytes` stride, and now confirmed independent of chase order too
    -- is new corroborating evidence for a shared, fixed, small-way-count
    structure common to multiple strides (the DTLB-aliasing hypothesis in
    CLAUDE.md), though it doesn't confirm the mechanism.
  - **Candid caveat:** the new base run's raw values at small `num_ways`
    (e.g. ~14.8/14.0/19.0 ticks at ways 2/3/4) don't closely match the
    previously-committed same-seed base run's values at those same points
    (~10.07/10.07/10.07) despite identical seed and `cache_bytes`. The most
    likely explanation is ordinary run-to-run noise -- this machine's
    documented interference pattern shows up most visibly at exactly these
    small absolute tick values -- but `--max-ways` also differs between the
    two runs (64 originally vs. 40 now, changing the probe buffer's total
    allocation size, which could shift page placement). That wasn't
    controlled for here and hasn't been ruled out as a contributing factor;
    flagged as an open uncertainty, not resolved.
- **`LLC_32MiB` is NOT order-sensitive -- it reproduces the same staircase
  essentially exactly across all three seeds.** Base/rep1/rep2 all show: flat
  ~10-15 ticks through num_ways 4-5, a ~17-18 tick tier at 6-8, a jump to
  ~24 ticks at num_ways=9 in *every* seed, then a big jump to a ~53-59 tick
  plateau from num_ways=10 onward in *every* seed -- matching the shape of
  the original single-seed committed result closely. This is the opposite
  finding from the 256 KiB candidate: whatever produces this candidate's
  staircase does not depend on chase order, which argues against a
  replacement-policy-order explanation for *this* stride specifically (more
  consistent with a page-placement/TLB-set-collision mechanism that only
  cares about which pages are touched, not the order they're chased in) --
  meaning the two candidates are most likely not being broken by the exact
  same confound, or at least not in the same way. num_ways=9 shows up here
  too (this time as a genuine sustained step to ~24 ticks, not a dip) -- a
  third recurrence of exactly "9" across two different `cache_bytes`
  candidates and three different seeds, which is unlikely to be coincidence.
- **Bottom line: still not a trustworthy per-level associativity number for
  either candidate** (the pre-existing conclusion above stands), but this
  re-check adds two concrete, reproducible facts worth carrying into a Phase
  II follow-up: (a) num_ways=9 recurs as a transition point across every
  stride and seed tried on this machine so far, and (b) the confound's
  order-sensitivity differs between the two candidates tested, meaning at
  least two distinct mechanisms (or one mechanism with stride-dependent
  behavior) are in play, not one uniform explanation.

#### Residue scan (2026-09-12): pins the confound's implied set-count at S=256, timing-only

Direct follow-up to the order-sensitivity difference above, using CLAUDE.md's
"Option 1" (vary `cache_bytes` at different residues mod a candidate set-count
and see if the knee moves as predicted) -- chosen specifically because it
needs no code change (still power-of-two `--cache-bytes` values, just more of
them) and is Phase-I-safe (pure timing comparison, no hardware readout).
Tested 6 more power-of-two candidates bridging the two known anchors --
256 KiB (64 pages/node, order-*sensitive*) and 32 MiB (8192 pages/node,
order-*independent*) -- at 512 KiB, 1, 2, 4, 8, and 16 MiB (128, 256, 512,
1024, 2048, 4096 pages/node respectively), each with the same base+2-repeat,
3-seed (12345/12346/12347) methodology, `taskset -c 1`, `--max-ways 40`. Raw:
`data_raw/sunbird/associativity/{residue_scan_512KiB,residue_scan_1MiB,
residue_scan_2MiB,residue_scan_4MiB,residue_scan_8MiB,LLC_16MiB}/`. Rather
than eyeballing each curve, computed one objective metric per (candidate,
seed): the smallest `num_ways_probed` at which the random-pattern median
first exceeds 2x that run's own low-`num_ways` baseline -- then compared how
much that location varies across the 3 seeds for each candidate.

- **Result: a sharp transition between 128 and 256 pages/node, not a gradual
  one.** At 64 and 128 pages/node the jump location scatters widely across
  seeds (64: 17/11/13, spread 6; 128: 10/9/13, spread 4). At every candidate
  from 256 pages/node upward, it clusters tightly at 9-11 regardless of seed
  (256: 11/11/11; 512: 10/10/10; 1024: 10/10/9; 2048: 10/10/10; 4096:
  10/10/11; 8192: 9/10/9) -- essentially the same 0-1-way noise level as the
  already-confirmed-clean 32 MiB candidate, not the 4-6-way scatter seen
  below the transition. See
  `data_processed/sunbird/associativity/residue_scan_summary/
  residue_scan_transition.png` for the plot (jump-location vs. stride, log
  scale, all 3 seeds per candidate) -- the transition is visually obvious,
  not a judgment call.
- **Interpretation offered at the time (RETRACTED same day -- see the
  "Falsification test" subsection immediately below before trusting this):**
  under the simplest version of the page-indexed-structure model in
  `associativity.h`'s docstring (a stride of P pages/node lands every probed
  node in the same one set exactly when P is a multiple of the structure's
  set-count S), the flip at exactly 128->256 pages/node was read as pinning
  **S=256**. This reasoning had a real flaw: every candidate tested was a
  power of two, so "is a multiple of S=256" and "is simply large" were the
  same condition for this specific candidate set -- the experiment could not
  actually tell those two explanations apart. See below for the follow-up
  that exposed this and what actually happened instead.

#### Falsification test + real-capacity test (2026-09-12): S=256 is wrong; testing at the real LLC capacity doesn't help either

**Part 1 -- falsification test.** To distinguish "multiple of S=256" from
"just large," `main_code/common/main.c`'s hard power-of-two `--cache-bytes`
validation was relaxed to "must be a multiple of 4096 (the page size)" (see
that file and `associativity.h`'s updated docstring) so non-power-of-two
strides could be tested. Two candidates, neither a multiple of 256: 300
pages/node (1,228,800 B) and 4200 pages/node (17,203,200 B), same 3-seed
methodology, `taskset -c 2` (core 1 had picked up load from another
process by this point; core 2 confirmed idle first). Raw:
`data_raw/sunbird/associativity/{falsify_300pages_notmult256,
falsify_4200pages_notmult256}/`.

- **4200 pages/node came out completely clean** -- 0 spread across 3 seeds,
  wall at num_ways=10, indistinguishable from every multiple-of-256
  candidate. Under the S=256 model this should have been scattered (4200
  mod 256 = 104, not 0). It wasn't. **This directly falsifies S=256 as
  stated.**
- **300 pages/node showed a genuine intermediate tier** (flat 10.08 through
  way 8, the same "way=9" bump to 12.2 seen almost everywhere, then a
  flat ~17.1 tier from way 10-18, THEN a big jump to ~44-48 at way 19) --
  neither cleanly "scattered" nor cleanly "clean," and not what a simple
  multiple-of-256 model predicts either. The most likely explanation: real
  TLB/paging-structure indexing on modern hardware is often a bit-XOR hash
  across several address-bit ranges, not simple `address mod S` -- which
  would explain why a simple linear-residue model fits some strides and
  not others. Not resolvable further with simple timing arithmetic alone.

**Part 2 -- real-capacity test.** Independent of the falsification test,
also retested directly at the ACTUAL measured ~26-27 MiB LLC capacity
estimate from the capacity/ section, instead of rounding to 16 MiB or
32 MiB: three non-power-of-two candidates, 27,262,976 B (26.0 MiB),
27,787,264 B (26.5 MiB), and 28,311,552 B (27.0 MiB), same 3-seed
methodology, `taskset -c 1` (confirmed idle first). Raw:
`data_raw/sunbird/associativity/{LLC_real_26p0MiB,LLC_real_26p5MiB,
LLC_real_27p0MiB}/`.

- All three gave a clean, order-independent wall -- **but at exactly
  num_ways=10 in every case, identical to nearly every other large-stride
  candidate tested this session.** Tabulating the wall location across
  every candidate tried from 512 KiB to 27 MiB (13 candidates total,
  spanning a 27x byte range, power-of-two and non-power-of-two alike): 10
  of 13 break at exactly num_ways=10, and 12 of 13 show the same "way=9"
  bump immediately before it. Changing the candidate from 1 MiB to 27 MiB
  -- a 27x change -- did not move the wall. **A genuine capacity-driven
  associativity knee should not sit at the same num_ways regardless of a
  27x change in the tested byte value; this is the signature of a small,
  fixed, page-COUNT-limited structure (roughly 9 slots), not a real
  cache's byte capacity.**

**Conclusion: for any stride above roughly 1 MiB on Sunbird, this method
cannot currently distinguish real L2/LLC associativity from this small,
universal confound.** This is not a "wrong candidate value" problem --
every candidate from 512 KiB to 27 MiB was tried, none escaped it -- it is
structural to the method (one node per page, stride = target capacity) at
this stride scale: something with ~9 slots saturates long before any real,
larger cache set would. Trying more candidate byte values, power-of-two or
not, is very unlikely to resolve this further.

**This also casts new, concrete doubt on the previously-trusted L1 = 8-way
result** (`cache_bytes=32768` = 8 pages/node, far below the ~1 MiB
threshold characterized here). The L1 result remains the one case that's
fully order-independent at a SMALL page count, so it may still be a
genuine, independent signal -- but given how consistently a small
fixed-entry structure has now turned up at every larger stride tried, it
is no longer safe to treat L1=8-way as automatically confound-free just
because its curve looks clean. Not retracted (nothing directly contradicts
it), but flagged as unresolved pending a Phase II PMU check or a
differently-designed timing test.

**What would actually need to change, if this is picked back up:** the
core assumption of one node per page (stride = target capacity) is what
exposes every large stride to this confound. A redesign that keeps
multiple same-set nodes on fewer distinct pages would sidestep it, but no
such design has been worked out yet. This is a method-design problem, not
a "test more candidates" problem.

### latency/
Two sub-experiments, `hit_latency` and `miss_latency`, added to `cache_bench`
2026-09-13 (were "not yet implemented" before this). Both use footprint/
target/evict byte values taken **only from `CAPACITY_RESULTS.md`** (L1 =
32,768 B, L2 = 262,144 B, LLC ≈ 30 MiB = 31,457,280 B) — per project-wide
direction (2026-09-13), `CAPACITY_RESULTS.md` is now the single source of
truth for capacity boundaries; the earlier per-machine capacity write-up
further up this file (and the "2026-09-11 re-verified NOT genuine" retraction
of 256 KiB / ~30 MiB in `CLAUDE.md`) is superseded and must not be used to
pick these values.

**hit_latency (dependent chain + independent-load diagnostic control):**
- Source file(s): `main_code/common/{main.c,latency.c,latency.h,benchmark.c,benchmark.h,pointer_chase.c,pointer_chase.h,random.c,random.h}`, `main_code/x86_64/timer_x86.h`, `main_code/common/timer.h`
- Build command: `make` (from repo root)
- Run command + arguments: `./scripts/run_hit_latency_full.sh sunbird 2 L1:32768,L2:262144,LLC:31457280,DRAM:536870912` (pinned via `taskset -c 2`; core 2 re-verified idle via two independent `/proc/stat` delta samples 3s apart, ~0.7% busy, immediately before running — same discipline as the capacity/associativity sections above). DRAM's 536,870,912 B (512 MiB) footprint is not itself a `CAPACITY_RESULTS.md` boundary — it's a "deep in the DRAM plateau" pick, comfortably past LLC, chosen the same way the capacity experiment's tail-extension sweeps picked a deep DRAM point.
- Per level: base run + 2 reproducibility repeats (seed = 12345, 12346, 12347), each run at `--load-mode {dependent,independent}` × `--pattern {random,sequential}` (4 combinations), 1,000,000 timed accesses per combination (batch size 1000), 3 untimed warm-up passes.
- Dependent-chain batch size: 1000 (`--batch-size 1000`, `DEFAULT_BATCH_SIZE`).
- Regular vs. randomized control included: yes, both `--pattern random` and `--pattern sequential` run at every (level, load_mode) combination.
- Raw output filename(s): `data_raw/sunbird/latency/hit/<LEVEL>/hit_latency_{base,rep1,rep2}_{dependent,independent}_{random,sequential}_20260913T053708Z.csv.gz`
- Processing: `scripts/summarize_raw.py` per raw file → `data_processed/sunbird/latency/hit/<LEVEL>/*_summary_20260913T053708Z.csv` → `scripts/plot_hit_latency.py` → `data_processed/sunbird/latency/hit/<LEVEL>/plots/hit_latency_boxplots.{png,pdf}`.
- **Result (dependent, random pattern, base run median, n=1000 each):** a clean, monotonically increasing 4-tier ladder — **L1 ≈ 10.35 ticks, L2 ≈ 26.83 ticks, LLC ≈ 58.42 ticks, DRAM ≈ 207.10 ticks**. At every level and both patterns, `--load-mode independent` measured faster than `dependent` (e.g. LLC random: 32.29 vs 60.03; DRAM random: 37.61 vs 207+), confirming the independent-load control correctly exposes memory-level parallelism as required — this is the expected signature, not the reported latency number.
- Bug found and fixed during this run: the first implementation of `measure_independent_loads_batched()` always read addresses from a randomly shuffled permutation regardless of `--pattern`, so a `sequential`+`independent` run wasn't testing anything sequential (it measured *slower* than sequential+dependent, since sequential+dependent uniquely benefits from hardware prefetching and independent mode's addressing ignored that). Fixed so the independent-load address order also follows `--pattern` (a plain 0..n-1 sequence for sequential, a shuffled permutation for random) — see `benchmark.c`/`benchmark.h`'s updated `measure_independent_loads_batched()` signature and `latency.c`. Confirmed fixed: after the fix, independent reads faster than dependent at BOTH patterns, at every level.

**miss_latency (forced eviction + single-shot reload):**
- Source file(s): same list as hit_latency above.
- Run command + arguments: `./scripts/run_miss_latency_full.sh sunbird 2 L1_to_L2:32768:262144,L2_to_LLC:262144:31457280,LLC_to_DRAM:31457280:67108864` (core 2, same idleness check). `LLC_to_DRAM`'s evict_bytes (67,108,864 B = 64 MiB) is not itself a `CAPACITY_RESULTS.md` value -- it only needs to exceed the ~30 MiB LLC capacity comfortably to guarantee eviction into DRAM, and was picked after timing calibration (see below) showed a much larger eviction set (originally tried: 512 MiB, matching the DRAM hit_latency footprint) was impractically slow.
- Per transition: base run + 2 reproducibility repeats (seed = 12345, 12346, 12347), each at `--pattern {random,sequential}` (the eviction-set traversal order control). **200 trials per (transition, pattern, run)**, NOT 1,000,000 — each trial is a single dependent reload, not a batch average (`--batch-size 1` passed only to satisfy `main.c`'s cross-experiment validation, which fans `--samples`/`--batch-size` out to every experiment's config struct unconditionally regardless of which `--experiment` is selected; it has no effect on miss_latency's own logic, which has no batch concept). 3 untimed warm-up passes (one full lap of the target set, one full lap of the eviction set) before the first timed trial, and again before every subsequent trial.
- Wall-time calibration done before picking final parameters (core 2, random pattern, 1000 trials): ~74 ms/trial at a 27 MiB eviction set, but ~604 ms/trial at 64 MiB -- worse than linear in eviction-set size (8x the bytes, >2x the extrapolated per-trial cost), plausibly growing TLB pressure as the walk spans more pages; not investigated further. A first attempt at 512 MiB (LLC_to_DRAM, matching the DRAM hit_latency footprint) was killed after >3 minutes on just the first (transition, pattern) combination and abandoned in favor of 64 MiB.
- Raw output filename(s): `data_raw/sunbird/latency/miss/<TRANSITION>/miss_latency_{base,rep1,rep2}_{random,sequential}_20260913T054413Z.csv.gz`
- Processing: `scripts/summarize_raw.py` → `data_processed/sunbird/latency/miss/<TRANSITION>/*_summary_20260913T054413Z.csv` → `scripts/plot_miss_latency.py --hit-latency-summary <matching hit_latency dependent/random summaries>` → `data_processed/sunbird/latency/miss/<TRANSITION>/plots/miss_latency_boxplots.{png,pdf}` (annotated with the incremental-penalty delta against the source level's own hit_latency median).
- **Result (random pattern, base run median, n=200 each): L1→L2 ≈ 124 ticks, L2→LLC ≈ 284 ticks, LLC→DRAM ≈ 622 ticks** — monotonically increasing, consistent with genuinely deeper eviction at each transition. Run-to-run spread across the 3 repeats was substantial at two of the three transitions (L1→L2: medians 124/116/150, 26.2% spread; L2→LLC: medians 284/300/510 random and 288/144/288 sequential, ~60% spread both patterns) — `plot_miss_latency.py`'s existing >20%-spread stderr warning (ported from `plot_associativity.py`) fired on both, consistent with this project's established pattern of real shared-machine interference showing up as scattered single-run spikes (see Sunbird/Crux/Charnwood/Thunderbird/Ookay's capacity/associativity write-ups) rather than a flaw in the method itself; not independently re-verified against a `/proc/stat` idle re-check per repeat, so shared-machine noise vs. a genuine methodological artifact is not yet distinguished for these two transitions specifically.
- **IMPORTANT caveat, confirmed via a dedicated control test (2026-09-13) — do not treat the numbers above as clean reload latencies:** miss_latency times a SINGLE dependent load per trial (`timer_start()`/`timer_stop()` directly, no batching), unlike every other experiment in this codebase, which amortizes timer overhead across 1000+ back-to-back accesses. A control run (`--target-bytes 32768 --evict-bytes 512 --pattern random --samples 2000`, an eviction set of only ~8 cache lines spread across L1's 64 sets -- overwhelmingly unlikely to actually evict the target's own line) still measured a 64-85 tick median/min, vs. hit_latency's batched L1 number of ~10 ticks at the identical footprint. Since that control shouldn't be evicting the target most of the time, this ~64-85 tick floor is FIXED single-shot measurement overhead (serializing `lfence`/`rdtsc`/`rdtscp` cost and post-function-call pipeline state, unamortized), not real miss cost. This means every miss_latency number above is "true reload latency + tens of ticks of fixed overhead" -- the increasing trend across transitions (124→284→622) is still meaningful evidence of deeper eviction, but the absolute values, and any direct subtraction against a hit_latency plateau (e.g. `plot_miss_latency.py`'s incremental-penalty annotation), should be read as approximate until this overhead is measured per-machine and subtracted, which the pipeline does not yet do automatically. See `main_code/common/latency.h`'s `run_miss_latency_experiment` docstring, "KNOWN LIMITATION" paragraph.
- Not yet done: the L1_to_L2 and L2_to_LLC repeat-spread hasn't been traced to a specific interfering process (no `who`/`ps`/`mpstat` check was run immediately after the anomaly appeared, only before the whole run started); and the single-shot overhead above hasn't been isolated per-transition (only measured once, at the L1 footprint) or subtracted from the headline numbers.

### inclusion_policy/
`--experiment inclusion_policy` added to `cache_bench` 2026-09-13 (was
"not yet implemented" before this). Boundary values from `CAPACITY_RESULTS.md`
only (L1 = 32,768 B, L2 = 262,144 B, LLC ≈ 30 MiB = 31,457,280 B), per
project-wide direction. **All three adjacent-and-skip-level pairings implied
by CAPACITY_RESULTS.md's three levels were run** (L1 vs L2, L2 vs LLC, and
L1 vs LLC directly) — do not read a result from only one pairing as covering
the others; each has its own confidence level (see per-pairing Results below).

- Source file(s): `main_code/common/{main.c,inclusion_policy.c,inclusion_policy.h,pointer_chase.c,pointer_chase.h,random.c,random.h}`, `main_code/x86_64/timer_x86.h`, `main_code/common/timer.h`
- Build command: `make` (from repo root)
- Run commands + arguments (pinned `taskset -c 2`, core re-verified idle via `/proc/stat` deltas immediately before each invocation):
  - `./scripts/run_inclusion_policy_full.sh sunbird 2 L1_vs_LLC:32768:31457280:LLC_to_DRAM` (timestamp `20260913T065738Z`)
  - `./scripts/run_inclusion_policy_full.sh sunbird 2 L1_vs_L2:32768:262144:L2_to_LLC,L2_vs_LLC:262144:31457280:LLC_to_DRAM` (timestamp `20260913T070727Z`, both pairings in one invocation)
  - The 4th field on each spec names the already-collected `miss_latency` transition (see `latency/` section above) that pairing sources its "invalidated" calibration class from: L1_vs_L2 evicts at L2 scale, so "invalidated" (beyond L2) = the `L2_to_LLC` transition; both L2_vs_LLC and L1_vs_LLC evict at LLC scale, so "invalidated" (beyond LLC) = the `LLC_to_DRAM` transition.
- Eviction/reload construction (see `main_code/common/inclusion_policy.h`'s module doc comment for the full argument): target (the UPPER level's capacity) and an untouched control buffer are both freshly page-aligned (offset 0). The eviction buffer places one node every 4096 B (exactly one page, `--evict-stride-bytes`), all at a FIXED sub-page offset of 2048 B (`--evict-offset-bytes`) — different from target/control's offset 0 — so every eviction node varies the higher-order (lower-level-relevant) address bits by spanning many pages, while structurally never landing on target's own line, PROVIDED the target's entire index fits within one page. Per trial: untimed re-touch of target and control, untimed eviction walk, then one timed dependent reload of each, exactly like `miss_latency`'s mechanism but potentially skipping a level.
- **Three load-bearing caveats, all undecided pending future work — read before trusting a result:**
  1. **Assumed line size (affects all three pairings).** Because the eviction buffer touches only one cache line per page, exerting genuinely comparable capacity pressure to a dense buffer requires scaling the lower level's real byte capacity up by `evict_stride_bytes / line_size` before using it as `--evict-bytes`. Line size data was not available for this machine when this was built, so `run_inclusion_policy_full.sh` uses a **documented assumption of 64 B** (`ASSUMED_LINE_SIZE_BYTES=64`) — e.g. `31,457,280 * 4096/64 = 2,013,265,920` (~1.875 GiB) for an LLC-scale eviction. If Sunbird's real line size turns out to be smaller (e.g. 32 B), this UNDERSTATES the eviction footprint needed; re-run with the corrected scaling once line_size data exists.
  2. **DTLB pressure at large eviction scale (affects L2_vs_LLC and L1_vs_LLC specifically, both ~491,520-page/~1.9 GiB eviction footprints; L1_vs_L2's ~4,096-page/16 MiB footprint is far smaller and less suspect).** Touching that many distinct pages risks blowing the DTLB regardless of any real cache eviction. The `control` channel (never touched by the eviction walk by construction) is a live per-run check for this — see each pairing's Result below; mitigating this properly (e.g. huge-pages backing for the eviction buffer, mirroring `associativity.c`'s existing `--huge-pages` diagnostic) was identified as a next step but deliberately NOT implemented in this pass.
  3. **Avoidance guarantee only holds for a target whose full index fits in one page (affects L2_vs_LLC specifically).** L1 (32,768 B, likely ≤64 sets) plausibly satisfies this; L2 (262,144 B) almost certainly does NOT (its index necessarily depends on physical address bits above the page offset for any realistic line size/associativity), so for the L2_vs_LLC pairing the eviction walk may well ALSO land on target's own L2 set by ordinary chance across its many pages — the "avoids the upper level" property this method relies on is NOT reliably true there. Treat L2_vs_LLC's result as the least trustworthy of the three for that reason, independent of caveats 1-2.
- Per trial: 200 single-shot trials (`--samples 200 --batch-size 1`, the `--batch-size` value only exists to satisfy `main.c`'s unconditional cross-experiment validation, same as `miss_latency`), base + 2 reproducibility repeats (seed 12345/12346/12347), both eviction-walk traversal patterns, 3 untimed warm-up passes. A separate calibration run (500 trials, `--evict-bytes` = `--target-bytes`, i.e. nothing evicted) establishes each pairing's own single-shot "survived" baseline fresh.
- Raw output filename(s): `data_raw/sunbird/inclusion_policy/<pairing>/inclusion_policy_{calibration,base,rep1,rep2}_{random,sequential}_<ts>.csv.gz` (calibration has no pattern suffix)
- Processing: `scripts/summarize_raw.py` per raw file (the CSV's `channel` column, `target`/`control`, is picked up automatically as part of the default grouping key — no special flags needed) → `data_processed/sunbird/inclusion_policy/<pairing>/*_summary_<ts>.csv` → `scripts/classify_inclusion_policy.py` (reads the RAW base/random data directly, not the summary, so per-trial classification fractions are real, not inferred from an average) → `scripts/plot_inclusion_policy.py`.

**Results, one per pairing (n=200 target/control trials each, base/random run unless noted):**

- **L1_vs_L2** (survived-class 60.0 ticks, invalidated-class 284.0 ticks from `L2_to_LLC`): target median 84 ticks (90.0% survived-like, 4.5% invalidated-like), control median 68 ticks (92.0% survived-like). Paired check (target slower than its own control): 96.5%. Both channels sit close to the survived reference line in the plot, well below invalidated (see `L1_vs_L2/plots/inclusion_policy_boxplots.png`). **Verdict: EXCLUSIVE / NON-INCLUSIVE** — this is the cleanest, most confident result of the three (also the pairing least exposed to caveats 2-3 above, since its eviction footprint is only ~16 MiB/4,096 pages and its target is L1-sized).
- **L1_vs_LLC** (survived-class 60.0 ticks, invalidated-class 622.0 ticks from `LLC_to_DRAM`): target median 236 ticks (75.0% invalidated-like, 11.0% survived-like), control median 136 ticks (97.5% survived-like, 2.5% invalidated-like). Paired check: 98.5%. **Verdict: UNCERTAIN** — target's 75.0% invalidated-like fraction falls just short of the 80% threshold `classify_inclusion_policy.py` uses for a firm call, and neither channel's box in the plot cleanly sits at either reference line; both patterns cluster in a broad 130-250 tick band strictly between the two calibrated lines. Read as: strong relative evidence (control stayed clean, so caveat 2 looks like a minor factor here) leaning toward inclusive behavior, not a clean textbook classification.
- **L2_vs_LLC** (survived-class 76.0 ticks, invalidated-class 622.0 ticks from `LLC_to_DRAM`): target median 212 ticks (13.5% survived-like, 1.5% invalidated-like, **85.0% ambiguous** — most trials fall inside the classification boundary's fence, not confidently on either side), control median 144 ticks (96.5% survived-like). Paired check: 92.0%. **Verdict: UNCERTAIN**, and read this one with the most skepticism of the three per caveat 3 above — an L2 target does not get the same structural "avoids the upper level" guarantee L1 does, so this pairing's numbers may reflect ordinary incidental L2 eviction from the walk rather than anything specific to LLC's inclusion policy. Also noted: the `target (sequential)` box showed 80% run-to-run spread (medians 164/372/240 across the 3 repeats) — the widest disagreement seen across any inclusion_policy run so far, not yet investigated.
- Anomaly noted separately, not yet explained: in the L1_vs_LLC run specifically, the `control (sequential)` box showed 77% spread (max ~756 ticks) — worth a dedicated re-check (e.g. `who`/`mpstat` at the time) before citing that pairing's sequential-pattern numbers.
- Not yet done, any pairing: multiple different target addresses/sets (PROJECT 1.pdf explicitly asks to "repeat with controls and multiple target sets/addresses" — every run above tested exactly one target buffer per repeat, just re-seeded); a real line_size measurement to replace the assumed 64 B scaling constant; and the huge-pages TLB mitigation noted in caveat 2.

### pmu/ (Phase II only — leave blank until Phase I is frozen)
- `perf list` output filename: 
- Events collected + exact semantics on this CPU: 
- Run command + arguments: 

## Reservation Log (if applicable)
- Reserved core/package: 
- Time window: 
