# skylark — Reproduction Manifest

> Fill in every field before freezing results. This README must let a grader go from
> this folder to the exact command that generated the data without guessing.

## Machine Identification
- Hostname: skylark.ece.ncsu.edu
- CPU model (from `lscpu`/`/proc/cpuinfo`): AMD EPYC 7532 32-Core Processor (x2 sockets, 64 logical CPUs total)
- ISA / architecture: x86_64
- Vendor / microarchitecture / codename (researched, NOT from cache tables): AMD, Zen 2 ("Rome" server line) — TODO: confirm against team's MACHINE_RESEARCH.md convention, not filled in here to avoid duplicating/contradicting that table
- Introduction year (per the team's stated year convention): see MACHINE_RESEARCH.md
- Process node (if reliably documented): TODO
- Kernel version: 5.14.0-611.38.1.el9_7.x86_64
- Page size: 4096 bytes
- SMT siblings idle during runs? `lscpu` reports Thread(s) per core = 1 (SMT appears disabled machine-wide, not just for this run) — no sibling to idle/reserve

## Environment
- Compiler + version: gcc (GCC) 11.5.0 20240719 (Red Hat 11.5.0-14)
- Compiler flags: `-O0 -g -std=c11 -Wall -Wextra -fno-omit-frame-pointer`
- Timer method used (RDTSC/RDTSCP+LFENCE, CNTVCT_EL0, etc.): `main_code/x86_64/timer_x86.h` — LFENCE+RDTSC to start, RDTSCP+LFENCE to stop (serialized TSC read pair)
- Affinity/binding command used: `taskset -c 10` (see `scripts/run_capacity_full.sh`)
- NUMA/locality method: none explicit — no `numactl` pinning in the script, only `taskset -c 10`. Core 10 is on NUMA node0 (node0 = CPUs 0-31, node1 = CPUs 32-63) per `lscpu -e`; memory locality was not independently verified/pinned.
- Git commit hash of the code used for these results: 881fbfc00f6bf576dfbc35cf5d97ce2a1aa09ad9 (main run, 2026-09-08 12:00:20 -0400) — NOTE: the manual tail-extension2 follow-up (see below) was run afterward against the same checkout; if any code changed between the two, re-check `git log` before treating this hash as covering all skylark capacity data.

## Per-Experiment Reproduction

### capacity/
- Source file(s): `main_code/common/capacity.c`, `main_code/common/main.c`, `main_code/x86_64/timer_x86.h`
- Build command: `make` (from repo root)
- Run command + arguments: `./scripts/run_capacity_full.sh skylark 10 134217728` (coarse_max=128 MiB; script internally invokes `taskset -c 10 ./cache_bench --experiment capacity --pattern <random|sequential> --samples 1000000 ...` per sweep stage — coarse, tail-extension, 3x dense-around-boundary, 2x repeat of deepest boundary, dense-past-deepest-boundary tail check)
- Sample count: 1,000,000 (timed; warm-up excluded)
- Random seed(s): 12345
- Raw output filename(s): `data_raw/skylark/capacity/capacity_{coarse,coarse_ext,dense0,dense1,dense2,dense2_rep1,dense2_rep2,denseTail}_{random,sequential}_20260908T160607Z.csv.gz` (gzipped after the fact, ~9x smaller, to keep repo size manageable; summaries below were generated from the uncompressed originals before compression)
- Processing script -> data_processed path: `data_processed/skylark/capacity/{coarse,coarse_ext,dense0,dense1,dense2,dense2_rep1,dense2_rep2,denseTail}_{random,sequential}_summary.csv`, plotted via `scripts/plot_capacity.py` into `data_processed/skylark/capacity/plots/{capacity_curve,capacity_boxplots}.{png,pdf}`. **Regenerated 2026-09-10** with `--boundary 32768 --boundary 16777216 --boundary 18295680 --boundary 21757352` to add the newly-identified L1 edge (see below).
- Detected boundaries (bytes): 16777216, 18295680, 21757352 (auto-detected by `run_capacity_full.sh`, dense-resampled and repeated 2x at the deepest one)
- **L1 boundary (backfilled 2026-09-10, from the already-collected coarse sweep — no
  new run needed):** `run_capacity_full.sh`'s auto-detector reported nothing below
  16.7 MiB at its default thresholds, but the coarse random-pattern data itself shows
  a clean flat plateau at 6.07-6.24 ticks/access from 1,024 to 32,768 bytes (41
  points, low noise), with the ramp starting immediately after (35,728 B -> 7.06
  ticks) and climbing steadily onward. **This gives L1 = 32,768 bytes (32 KiB)** —
  same value independently found the same way for Upgrade (see that machine's
  README) and matching Sunbird's hand-confirmed L1, via the same flat-then-ramp
  signature in each machine's own data, not assumed from one another. The
  auto-detector missed it for the same reason documented on Thunderbird: no single
  adjacent-point jump in the 8-points/octave coarse data clears the default
  `--min-abs-ticks 3.0`, even though the region is genuinely flat before and
  climbing after. Re-running `detect_cache_hierarchy.py` with `--min-abs-ticks 0.5
  --rel-threshold 0.1` recovers it: `L1: <= 32,768 bytes`. **PROVISIONAL** (clean in
  the data; not yet cross-checked by an independent test the way Sunbird's L1 was by
  its associativity knee).
- **Candidate L2/L3 shelf, ~4-16.8 MiB (backfilled 2026-09-10):** after the L1 ramp
  (6.24 ticks at 32,768 B climbing to 26.3 ticks at 4,194,304 B), the coarse data
  goes essentially flat from 4.19 MiB to 16.78 MiB — 17 points ranging only
  26.3-33.2 ticks with no monotonic trend (e.g. 27.6, 28.1, 27.0, 27.4, 27.9, 27.2,
  27.6 ticks bouncing in place across 5-9 MiB) — then jumps sharply to 52.4 ticks at
  18,295,680 B, a clear knee. At relaxed detector thresholds this whole 4-16.8 MiB
  span groups into one level (`detect_cache_hierarchy.py --min-abs-ticks 0.5
  --rel-threshold 0.1` reports `L7: 1,048,576–16,777,216 bytes, 27.22 ticks,
  33 points`). This reads like a genuine second plateau (candidate L2 or combined
  L2+L3, can't distinguish further without more targeted data) sitting before the
  already-confirmed L3->DRAM transition at ~16.8-22 MiB below — but at only
  8 points/octave this is not yet confirmed flat the same rigorous way Sunbird's
  plateaus were (40+ dense points, <2% run-to-run spread, independent repeats).
  **Would need a new 48-points/octave dense sweep across ~1-16 MiB on `skylark`
  itself to confirm — not resolvable from data already in this checkout** (this
  session has no access to `skylark`, only to this git checkout's already-collected
  data; analysis above used only already-committed `data_processed/skylark/capacity/`
  CSVs).
- Excluded runs (if any) and reason: none excluded. Note: the automated pipeline's own plotting step failed partway through the run (`ModuleNotFoundError: No module named 'matplotlib'` on this machine — see `data_raw/skylark/capacity/run_capacity_full_20260908T160607Z.log`); all data generation stages completed successfully before that failure. matplotlib (+ pillow, cycler, fonttools, kiwisolver) was installed via `pip3 install --user` and the plotting step was re-run standalone with the same summary-file set and boundaries the script would have used — `data_processed/skylark/capacity/plots/` is now up to date with all of the above data.
- Follow-up (not part of the automated `run_capacity_full.sh` pipeline): a manual tail-extension2 check further out (536870912-2147483648 bytes, i.e. 512 MiB-2 GiB), core=10, seed=12345, samples=1,000,000, warmup=3, points-per-octave=48 (same parameters as the script's own dense sweeps), to check for a further plateau beyond what the script's own tail-extension (128-512 MiB) covered.
  - `orig` pass: `run_capacity_ext2_20260908T171553Z.log` -> `data_raw/skylark/capacity/capacity_denseTail2_orig_{random,sequential}_20260908T171553Z.csv.gz` -> `data_processed/skylark/capacity/denseTail2_orig_{random,sequential}_summary.csv` (97 points each, complete).
  - `rep1` repeat: an initial attempt was interrupted partway (86/97 random points, no sequential); discarded and rerun cleanly as `run_capacity_ext2_rep1_20260908T220010Z.log` -> `capacity_denseTail2_rep1_{random,sequential}_20260908T220010Z.csv.gz` -> `denseTail2_rep1_{random,sequential}_summary.csv` (97 points each, complete).
  - Reproducibility: orig vs rep1 medians at 2147483648 bytes (2 GiB) agree within ~0.2% (279.05 vs 278.45 ticks/access, random pattern) -- no anomaly.
  - Finding: median latency rises only ~2% across the whole 512 MiB-2 GiB range (272.9 -> ~279 ticks/access, random pattern), flattening out by ~1.7 GiB. This region reads as an already-settled DRAM-latency plateau, not an open transition -- no further cache-level boundary detected out to 2 GiB.
  - Folded into `data_processed/skylark/capacity/plots/` -- `capacity_curve.{png,pdf}`/`capacity_boxplots.{png,pdf}` now span the full sweep out to 2 GiB (title-suffix "Phase I timing-only, extended to 2 GiB"), built from all coarse/dense/repeat/tail/tail2 summaries together. Confirms the ~16-22 MiB L3->DRAM transition is followed by a genuine flat plateau (~280 ticks/access) all the way to 2 GiB, not an unresolved further climb.

### line_size/
- Source file(s): 
- Build command: 
- Run command + arguments: 
- Sample count: 
- Notes on alignment/candidate strides tested: 

### associativity/
- Source file(s): `main_code/common/associativity.c`, `main_code/common/associativity.h`, `main_code/common/main.c`
- Build command: `make` (from repo root)
- Run command + arguments: `./scripts/run_associativity_full.sh skylark 10 32768,524288,8388608` (explicit hand-supplied `cache_bytes_csv`, NOT auto-detected — see below for where these three values came from)
- `cache_bytes` used per level (node-to-node stride, forces every probed node into the same cache set): L1=32,768 B, L2=524,288 B (512 KiB), L3/LLC=8,388,608 B (8 MiB) — taken from `CAPACITY_RESULTS.md`'s per-machine capacity table as manually curated there (2026-09-12), **not** from this machine's own `data_processed/skylark/capacity/` analysis above, which only established a *region* (candidate L2/L3 shelf ~4-16.8 MiB, one dominant ramp) rather than a single confirmed capacity value for L2 or L3 — see the discrepancy note below.
- Conflict-set construction method: cyclic dependent pointer chase over `num_ways` nodes spaced exactly `cache_bytes` apart (same set-index bits by construction regardless of unknown line size/way count — see `associativity.h`), num_ways swept 2-40 (way_step=1), both random and sequential-control patterns, 1,000,000 timed samples/point, batch_size=1000, 3 warmup passes, base seed=12345 + 2 reproducibility repeats (seeds 12346, 12347)
- Core/timestamp: core=10, timestamp=20260912T224538Z, full transcript in `data_raw/skylark/associativity/run_associativity_full_20260912T224538Z.log`
- Raw output: `data_raw/skylark/associativity/{L1,L2,L3_LLC}/associativity_{base,rep1,rep2}_{random,sequential}_20260912T224538Z.csv.gz`
- Processed summaries + plots: `data_processed/skylark/associativity/{L1,L2,L3_LLC}/*.csv`, `data_processed/skylark/associativity/{L1,L2,L3_LLC}/plots/associativity_{curve,boxplots}.{png,pdf}`

**Results and trustworthiness (read before citing any of these numbers):**
- **L1 (32,768 B): associativity = 8-way — TRUSTWORTHY.** Single sharp knee at num_ways=9, identical across base and both repeats (9, 9, 9), flat plateau before (~6.1 ticks) and after (~9.7 ticks), random and sequential curves overlap. Matches Sunbird's independently hand-confirmed 8-way L1 via the same clean-single-knee signature.
- **L2 (524,288 B): auto-detected "9-way" — NOT TRUSTWORTHY, likely an L1-aliasing artifact.** The curve is a multi-step staircase (jump at num_ways=9, partial drop, second jump at 13, a third rise starting ~37), not a single knee — see `associativity_curve.png`. The detector locked onto the *first* jump, which lands at exactly the same num_ways as L1's own knee. This is suspicious rather than confirmatory: 524,288 B is an exact 16x multiple of L1's own 32,768 B stride, so every node probed here also aliases into the same L1 set as every other probed node — this measurement is plausibly just re-detecting L1's 8-way limit, not L2's real associativity. This is the same unresolved stride-vs-true-structure confound already documented in `CAPACITY_INFERENCE_STATUS.md` for Sunbird's own L2 candidates (multi-step staircases at both 131,072 B and 262,144 B, "not a clean knee," open mechanistic question). Do not cite "L2 = 8-way" for skylark from this run.
- **L3/LLC (8,388,608 B): auto-detected "8-way" — NOT TRUSTWORTHY, and not even internally reproducible.** Also a multi-step staircase (small step at num_ways=8, another at 12, the dominant transition actually starts around num_ways=25-34 up to ~270 ticks/access) rather than one clean knee. Worse, the pipeline's own built-in reproducibility check disagreed across seeds: base=8, repeat1=8, repeat2=7 — printed as an explicit `WARNING: ... do NOT treat this level's associativity as resolved` by `run_associativity_full.sh` itself. Do not cite "L3 = 8-way" for skylark from this run.
- **Known discrepancy with this machine's own capacity data (flag for report writing):** `CAPACITY_RESULTS.md`'s L2=512 KiB / L3=~8 MiB values used as the stride here do not match what skylark's own capacity sweep above independently found — that data shows one candidate shelf spanning ~4-16.8 MiB (PROVISIONAL-WEAK, not resolved to a single boundary) rather than two separate levels at 512 KiB and 8 MiB. Per team decision (2026-09-12), the associativity experiment was still run at the manually-selected 512 KiB / 8 MiB values despite this open disagreement; the multi-step/non-reproducible results above are consistent with (though not conclusive proof of) `cache_bytes` not matching either level's true capacity, exactly as `associativity.h`'s own design notes predict for a wrong-by-construction stride.

### latency/
Two sub-experiments, `hit_latency` and `miss_latency`, run 2026-09-13
(unattended session; user not present). Footprint/target/evict byte values
taken **only from `CAPACITY_RESULTS.md`** (L1 = 32,768 B, L2 = 524,288 B,
LLC ≈ 8 MiB = 8,388,608 B, using N * 1,048,576 for "~N MiB" per project-wide
direction) — the associativity section above already flags a discrepancy
between this machine's own capacity data (one candidate ~4-16.8 MiB shelf,
not two separate L2/L3 boundaries) and `CAPACITY_RESULTS.md`'s picked
values; per the same project-wide direction that applies to this run,
`CAPACITY_RESULTS.md` is used anyway and this discrepancy is repeated here
rather than re-litigated.
- Idle-core check before running: `who`/`ps` showed no other logged-in
  users, but `ps aux` found another student's process (`msabap`,
  `cache_bench_x86 --exp nextlevel`) pinned via `psr=3` to core 3 at ~99.8%
  CPU the entire session — avoided. Two `/proc/stat` snapshots taken 3s
  apart confirmed core 6 idle (0 busy ticks out of ~724 total in the
  window, i.e. <1% busy); core 6 used for both runs below.
- Build command: `git pull && make clean && make` (from repo root); `python3 -c "import matplotlib"` confirmed working (3.9.4) before running.
- Git commit hash of the code used: `e343732c0b57beece621da8e7c3a9bd8be236d25`

**hit_latency (dependent chain + independent-load diagnostic control):**
- Source file(s): `main_code/common/{main.c,latency.c,latency.h,benchmark.c,benchmark.h,pointer_chase.c,pointer_chase.h,random.c,random.h}`, `main_code/x86_64/timer_x86.h`, `main_code/common/timer.h`
- Run command + arguments: `./scripts/run_hit_latency_full.sh skylark 6 L1:32768,L2:524288,LLC:8388608,DRAM:536870912` (pinned via `taskset -c 6`). DRAM's 536,870,912 B (512 MiB) footprint is not a `CAPACITY_RESULTS.md` boundary — it's a "deep in the DRAM plateau" pick, matching the same convention every other machine's hit_latency run used.
- Per level: base run + 2 reproducibility repeats (seed = 12345, 12346, 12347), each run at `--load-mode {dependent,independent}` × `--pattern {random,sequential}` (4 combinations), 1,000,000 timed accesses per combination (batch size 1000, `DEFAULT_BATCH_SIZE`), 3 untimed warm-up passes.
- Regular vs. randomized control included: yes, both `--pattern random` and `--pattern sequential` run at every (level, load_mode) combination.
- Raw output filename(s): `data_raw/skylark/latency/hit/<LEVEL>/hit_latency_{base,rep1,rep2}_{dependent,independent}_{random,sequential}_20260913T061014Z.csv.gz`
- Processing: `scripts/summarize_raw.py` per raw file → `data_processed/skylark/latency/hit/<LEVEL>/*_summary_20260913T061014Z.csv` → `scripts/plot_hit_latency.py` → `data_processed/skylark/latency/hit/<LEVEL>/plots/hit_latency_boxplots.{png,pdf}`.
- **Result (dependent, random pattern, base run median, n=1000 each): a clean, monotonically increasing 4-tier ladder — L1 ≈ 6.24 ticks, L2 ≈ 16.15 ticks, LLC ≈ 27.22 ticks, DRAM ≈ 274.87 ticks.** At every level and both patterns, `--load-mode independent` measured faster than `dependent` (e.g. LLC random: 7.48 vs 27.22; DRAM random: 46.49 vs 274.87), confirming the independent-load control correctly exposes memory-level parallelism at every level — the expected signature, not itself the reported latency. Sequential-pattern dependent latency stayed essentially flat (~6.1-6.2 ticks) at every level including DRAM, consistent with hardware prefetching hiding the miss cost entirely for a fully predictable stride — this is expected behavior, not a bug.
- No `[UNEXPECTED -- investigate]` flags fired at any level/pattern (checked all 8 combinations' printouts from `plot_hit_latency.py`'s required MLP-exposing check).

**miss_latency (forced eviction + single-shot reload):**
- Source file(s): same list as hit_latency above.
- Eviction-set calibration done before picking final parameters (core 6, random pattern, 100 trials, `target-bytes 8388608`): a candidate `evict-bytes` of 16,777,216 (2x the ~8 MiB LLC capacity) measured ~67.7 ms/trial (6.77s/100). Extrapolated to the full base+2reps × 2-pattern run (1,200 trials total across all three transitions, LLC_to_DRAM dominating) ≈ 81s — comfortably under the ~15 min budget, so no need to shrink; used 16,777,216 B as-is (did not jump to a much larger value, per the explicit caution against repeating Sunbird's original 512 MiB-evict-set mistake).
- Run command + arguments: `./scripts/run_miss_latency_full.sh skylark 6 L1_to_L2:32768:524288,L2_to_LLC:524288:8388608,LLC_to_DRAM:8388608:16777216` (core 6, same idleness check as hit_latency above; `--batch-size 1` passed automatically by the script only to satisfy `main.c`'s cross-experiment `--samples`/`--batch-size` validation, has no effect on miss_latency's own single-shot-per-trial logic).
- Per transition: base run + 2 reproducibility repeats (seed = 12345, 12346, 12347), each at `--pattern {random,sequential}`. 200 trials per (transition, pattern, run), 3 untimed warmup passes before the first timed trial and again before every subsequent trial.
- Raw output filename(s): `data_raw/skylark/latency/miss/<TRANSITION>/miss_latency_{base,rep1,rep2}_{random,sequential}_20260913T061426Z.csv.gz`
- Processing: `scripts/summarize_raw.py` → `data_processed/skylark/latency/miss/<TRANSITION>/*_summary_20260913T061426Z.csv` → `scripts/plot_miss_latency.py --hit-latency-summary <matching hit_latency dependent/random summaries>` → `data_processed/skylark/latency/miss/<TRANSITION>/plots/miss_latency_boxplots.{png,pdf}`.
- **Result (random pattern, base run median, n=200 each): L1→L2 ≈ 96.0 ticks, L2→LLC ≈ 120.0 ticks, LLC→DRAM ≈ 360.0 ticks** — monotonically increasing, consistent with genuinely deeper eviction at each transition.
- Run-to-run spread: `plot_miss_latency.py`'s >20%-spread stderr warning fired on two of the three transitions' random pattern — **L1_to_L2** (medians 96.0/120.0/120.0 across base/rep1/rep2, 21.4% spread) and **L2_to_LLC** (medians 120.0/96.0/144.0, 40.0% spread); **LLC_to_DRAM did not trigger the warning** (medians 360.0/360.0/384.0, ~6.4% spread). Per instructions, these two flagged transitions were NOT re-run to make the warning disappear — recorded as-is, consistent with this project's established pattern of real shared-machine interference showing up as scattered single-run spikes (see Sunbird/Crux/Charnwood/Thunderbird/Ookay's capacity/associativity write-ups) rather than necessarily a methodological flaw; not independently traced to a specific interfering process for this run.
- **Single-shot measurement overhead, isolated via a dedicated control (2026-09-13):** `taskset -c 6 ./cache_bench --experiment miss_latency --target-bytes 32768 --evict-bytes 512 --pattern random --samples 2000 --batch-size 1 --seed 12345`, then `tail -n +3 | awk -F, '{a[NR]=$5;...} END{asort(a); print a[int(n/2)]}'` → **median = 72 ticks**. `evict-bytes=512` is only ~8 cache lines spread across L1's sets — overwhelmingly unlikely to actually evict the target's own line — so this is a control, not a real L1 miss. Compared to this machine's own batched L1 hit_latency dependent/random median (6.24 ticks, above), the gap is **~65.8 ticks of fixed single-shot measurement overhead** (unamortized `lfence`/`rdtsc`/`rdtscp` + post-function-call pipeline state — see `main_code/common/latency.h`'s `run_miss_latency_experiment` "KNOWN LIMITATION" docstring), not real miss cost. This means every raw miss_latency median above is "true reload latency + ~66 ticks," not a clean number.
- **Approximate overhead-corrected incremental penalty** (raw miss median minus source-level's own batched hit_latency dependent/random median, then minus the ~65.8-tick overhead measured above — presented as approximate, not precise, per the caveat just above): L1→L2 ≈ 96.0 − 6.24 − 65.8 ≈ **24 ticks**; L2→LLC ≈ 120.0 − 16.15 − 65.8 ≈ **38 ticks**; LLC→DRAM ≈ 360.0 − 27.22 − 65.8 ≈ **267 ticks**. Still monotonically increasing after correction, consistent with genuinely deeper eviction at each transition — but treat the absolute values as approximate, same caution as every other machine's uncorrected miss_latency numbers.
- Not yet done: the L1_to_L2 and L2_to_LLC repeat-spread hasn't been traced to a specific interfering process (no `mpstat`/`ps` check was run again mid-sweep, only before the whole run started); the single-shot overhead above was only measured once, at the L1 footprint, not independently re-measured at L2/LLC/DRAM footprints.

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
