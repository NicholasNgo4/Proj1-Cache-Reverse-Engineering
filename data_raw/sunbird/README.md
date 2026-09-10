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

### line_size/
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

### associativity/
- Source file(s): `main_code/common/{main.c,associativity.c,associativity.h,benchmark.c,benchmark.h,pointer_chase.c,pointer_chase.h,random.c,random.h}`, `main_code/x86_64/timer_x86.h`, `main_code/common/timer.h`
- Build command: `make` (from repo root; see `Makefile`)
- Run command + arguments: `./scripts/run_associativity_full.sh sunbird 2 32768` (pinned via `taskset -c 2`, same physical core/SMT-sibling-idle setup as the capacity section above; `who`/`ps` checked immediately before this run -- one other user logged in, all their processes idle, load average 1.02). `32768` (32 KiB) is this team's hand-confirmed L1 capacity from the capacity section above, passed as an explicit override -- NOT auto-detected from `detect_cache_hierarchy.py`, whose coarse first-pass boundary (285864B / ~279 KiB) is already documented as unreliable for L1 on this machine (see the line_size section above and `run_associativity_full.sh`'s header comment). **LLC associativity has since been attempted (2026-09-10) -- see the LLC subsection below; results were inconclusive, not confirmed.**
- Conflict-set construction method: node-to-node stride fixed at `cache_bytes` (32768 for this run) in a dependent pointer-chase cycle; since capacity = sets * line_size * ways is by construction a whole multiple of one set's address period, every node landed in the same cache set regardless of the (still unmeasured) line size or associativity, while getting a distinct tag each time (see `main_code/common/associativity.h`'s module docstring for the full argument). Swept `num_ways_probed` (cycle length) linearly from 2 to 64, one node added at a time, both randomized and sequential-order chase (`--pattern`), 1,000,000 timed accesses per point (batch size 1000), 3 untimed warm-up passes, seed 12345.
- Raw output filename(s): `data_raw/sunbird/associativity/L1/associativity_{base,rep1,rep2}_{random,sequential}_20260910T170145Z.csv.gz`
- Processing script -> data_processed path: `python3 scripts/summarize_raw.py <raw.csv> -o data_processed/sunbird/associativity/L1/<name>_summary.csv`, then `python3 scripts/detect_associativity.py data_processed/sunbird/associativity/L1/base_random_summary.csv` for the knee estimate, then `python3 scripts/plot_associativity.py data_processed/sunbird/associativity/L1/*_summary.csv -o data_processed/sunbird/associativity/L1/plots --machine sunbird --level L1 --estimate 8` for the curve and box-plot figures (all done automatically by `run_associativity_full.sh`).
- Result: **8-way** at L1 (cache_bytes=32768). Median latency is flat at ~10.1-11.6 ticks/access for `num_ways_probed` 2 through 8 (0% run-to-run spread across 3 independent runs at num_ways=8), then jumps sharply to ~21.2 ticks at num_ways=9 (also 0% spread) and ~25.1 ticks by num_ways=10 -- a step, not a ramp, consistent with a cyclic dependent chase over N distinct blocks thrashing completely once N exceeds the set's way count. See `data_processed/sunbird/associativity/L1/plots/associativity_curve.png` and `associativity_boxplots.png`.
- Notes: Latency drifts upward again gradually past num_ways~28-30 (both patterns), most visibly in the sequential-pattern curve, and gets noisier (higher run-to-run spread, e.g. 30-40% at several points above num_ways~29) than the clean L1 knee itself. This is most likely TLB/page-walk pressure as the touched virtual footprint grows past `num_ways * 32 KiB` (at num_ways=64 that's still only 2 MiB, but each node lives on its own page here since the stride equals a full 32 KiB, so it's really 64 distinct pages, not 64 distinct 32 KiB regions of a shared page set) rather than a second cache-level effect -- not investigated further since it sits well above the L1 knee this run was targeting; flag as a follow-up if a later experiment needs a clean baseline at large num_ways.

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
