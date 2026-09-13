# upgrade — Reproduction Manifest

> Fill in every field before freezing results. This README must let a grader go from
> this folder to the exact command that generated the data without guessing.

## Machine Identification
- Hostname: **upgrade.ece.ncsu.edu** (confirmed 2026-09-11/12 via `hostname` in a
  session actually logged into `upgrade`; the capacity backfill below predates this
  and was done without machine access, hence the surrounding TODOs it left).
- CPU model (from `/proc/cpuinfo`): **Intel(R) Core(TM) i7-8700 CPU @ 3.20GHz**
  (confirmed via `grep "model name" /proc/cpuinfo`; matches `MACHINE_RESEARCH.md`'s
  "Core i7-8700 / Coffee Lake" row exactly — that table's entry is now confirmed
  live on this specific machine, not just pre-freeze research).
- ISA / architecture: x86-64 (confirmed via `uname -a`: `x86_64 x86_64 x86_64
  GNU/Linux`; consistent with `main_code/x86_64/timer_x86.h` being the timer header
  used — see Environment below)
- Vendor / microarchitecture / codename (researched, NOT from cache tables): Intel,
  Coffee Lake (per `MACHINE_RESEARCH.md`, cross-checked against the confirmed CPU
  model above)
- Introduction year (per the team's stated year convention): 2017 (per
  `MACHINE_RESEARCH.md`)
- Process node (if reliably documented): 14 nm (per `MACHINE_RESEARCH.md`)
- Kernel version: `6.8.0-138-generic` (confirmed via `uname -r`)
- Page size: 4096 bytes (confirmed via `getconf PAGESIZE`)
- SMT siblings idle during runs? Confirmed idle for the associativity/ run below
  (2026-09-12, core 5 = CPUs {5,11} per `lscpu -e=CPU,CORE,SOCKET,NODE`; `who`/`ps`
  showed only light, unrelated background load, no other student process pinned to
  either sibling). Unverified for the original capacity/ run (see that section's own
  caveat) — no snapshot was saved at that time. Also confirmed idle for the
  latency/ run below (2026-09-13, unattended session): two `/proc/stat` deltas 3s
  apart showed cpu5/cpu11 at 0% busy; a `pmu_pilot` process (another student's,
  unrelated) was pinned at ~100% on core 2 the whole session but never on core 5.

## Environment
- Compiler + version: `gcc (Ubuntu 12.3.0-1ubuntu1~22.04.3) 12.3.0` (confirmed via
  `gcc --version`; applies to the associativity/ run below — not independently
  reconfirmed for the original capacity/ run, though `make` uses the same toolchain
  by default on this machine either way)
- Compiler flags: `-O0 -g -std=c11 -Wall -Wextra -fno-omit-frame-pointer`
- Timer method used (RDTSC/RDTSCP+LFENCE, CNTVCT_EL0, etc.): x86 RDTSC/RDTSCP path
  (inferred from `main_code/x86_64/timer_x86.h` per the build layout; not
  independently confirmed with a disassembly excerpt the way Sunbird's is — TODO if
  needed for the report)
- Affinity/binding command used: `taskset -c 5 ./cache_bench ...` (core=5, confirmed
  from `run_capacity_full_20260908T231109Z.log`'s own header line, and reused for the
  associativity/ run below)
- NUMA/locality method: single-socket machine (`lscpu -e` shows SOCKET=0/NODE=0 for
  all 12 CPUs) — no NUMA placement concern on this host
- Git commit hash of the code used for these results: `06beab16fa7ece5a8f0f48c227efc852b854c2d3`
  for the associativity/ run below (confirmed via `git rev-parse HEAD` in this
  session); not captured for the original capacity/ run.

## Per-Experiment Reproduction

### capacity/
- Source file(s): `main_code/common/{main.c,capacity.c,capacity.h,benchmark.c,benchmark.h,pointer_chase.c,pointer_chase.h,random.c,random.h}`, `main_code/x86_64/timer_x86.h`, `main_code/common/timer.h`
- Build command: `make` (from repo root; see `Makefile`)
- Run command + arguments: `./scripts/run_capacity_full.sh upgrade 5` (default 64 MiB coarse ceiling; ran coarse sweep 1 KiB-64 MiB -> 4x tail-extension 64-256 MiB -> auto boundary detection -> dense sweep at 6 auto-detected boundaries -> 2 repeats on the deepest boundary's window -> dense past-deepest-boundary tail check). All stages pinned `taskset -c 5`, `--samples 1000000 --batch-size 1000 --warmup-passes 3 --seed 12345`, both `--pattern random` and `--pattern sequential`. Full transcript: `run_capacity_full_20260908T231109Z.log`.
- Sample count: 1,000,000 timed accesses per (size, pattern) point; warm-up (3 full untimed chase passes) excluded from that count
- Random seed(s): 12345 (xorshift32, `make_random_cycle`); sequential-pattern runs use `make_sequential_cycle` (no seed/randomness)
- Raw output filename(s): `data_raw/upgrade/capacity/capacity_coarse_{random,sequential}_20260908T231109Z.csv.gz`, `capacity_coarse_ext_{random,sequential}_*.csv.gz` (64-256 MiB tail), `capacity_dense{0..5}_{random,sequential}_*.csv.gz` (one dense window per auto-detected boundary), `capacity_dense5_rep{1,2}_{random,sequential}_*.csv.gz` (repeats on deepest boundary), `capacity_denseTail_{random,sequential}_*.csv.gz` (dense sweep past the deepest boundary, 64-256 MiB)
- Processing script -> data_processed path: `python3 scripts/summarize_raw.py <raw.csv> -o data_processed/upgrade/capacity/<name>_summary.csv` for each raw file above, then `python3 scripts/plot_capacity.py data_processed/upgrade/capacity/*_summary.csv -o data_processed/upgrade/capacity/plots --machine upgrade --boundary 32768 --boundary 9975792 --boundary 11863280 --boundary 18295680 --boundary 21757352` (plots existed in the repo pre-dating this writeup with unrecorded `--boundary` flags; regenerated 2026-09-10 with the boundary set above, informed by the analysis in this section)
- Excluded runs (if any) and reason: none excluded

- **Boundary detection and plateau status** (backfilled 2026-09-10 by analyzing the
  already-committed `data_processed/upgrade/capacity/*.csv` — no new benchmark runs;
  this session has no access to the `upgrade` machine itself, only to this git
  checkout's already-collected data):
  - **~6.28-6.33 ticks/access plateau, 1,024-27,552 bytes**: flat, low-noise (26
    points in the coarse sweep, range 6.28-6.33). Ramp onset begins at 30,048 B
    (6.40) and sharpens at 35,728 B (6.90). **This gives a clean L1 estimate of
    32,768 bytes (32 KiB)** — the same value as Sunbird's independently
    hand-confirmed L1 and as the value found below for Skylark's coarse data (see
    that machine's README) — via the exact same "flat-then-ramp" signature, not
    assumed from any of those other machines. Auto-detector did not report this
    boundary at its default thresholds (same class of issue documented on
    Thunderbird — the jump per adjacent coarse point stays under the 3.0-tick
    absolute-threshold default even though the region is genuinely flat before and
    genuinely climbing after); re-running `detect_cache_hierarchy.py` with
    `--min-abs-ticks 0.5 --rel-threshold 0.1` recovers it: `L1: <= 32,768 bytes`.
    **PROVISIONAL** — clean in the data, but not yet cross-checked by an
    independent test (Sunbird's L1 was corroborated by a clean associativity knee;
    this one hasn't been).
  - **~32 KiB-~1.5 MiB: continuous ramp, no flat shelf** (6.43 at 32,768 B up to
    34.7 at 1,482,904 B, climbing steadily the whole way). The two smallest
    auto-detected boundaries (185,360 B and 311,744 B) both fall inside this ramp,
    not at any flat region before/after them — consistent with the same
    over-segmentation pattern already documented on Crux/Charnwood/Ookay (the
    detector fragments one continuous ramp into spurious "levels"). No discrete L2
    value identifiable from existing data in this sub-range.
  - **~1.5-4.5 MiB: mild near-plateau, not confirmed flat** (34.7 -> 37.1 ticks
    ticks/access, coarse 8-points/octave resolution only, only a ~7% rise over 3
    octaves — visibly shallower than the ramp immediately before and after it).
    Flagging this as a **candidate** L2/L3 shelf, not a confirmed one: at only
    8 points/octave this could still be real flatness or just a locally-slow
    stretch of one long ramp (Skylark's analogous but much more clearly flat
    ~4-16.8 MiB region needed 48-points/octave dense data to confirm — see that
    machine's README). **Would need a new dense sweep (48 ppo, ~1-6 MiB) on
    `upgrade` itself to resolve either way; not resolvable from data already in
    this checkout.**
  - **~5-22 MiB: steep, genuinely noisy transition** (38.3 ticks at 5.4 MiB up to
    137.5 ticks at 21.8 MiB). The remaining 4 auto-detected boundaries
    (9,975,792 / 11,863,280 / 18,295,680 / 21,757,352 bytes) are waypoints along
    this one transition, not separate levels — same pattern as Crux's ~4-64 MiB
    region. **Reproducibility check** on the deepest boundary's dense window
    (`dense5` vs. its 2 repeats, 289 common points): median run-to-run spread
    12.6%, but with isolated points up to ~119% (e.g. 7.37 MiB: 42.1 / 70.0 / 143.2
    ticks across the 3 runs). Unlike Sunbird/Crux/Ookay's "spikes recur at
    *different* sizes in each run" signature, here **`rep2` is the largest of the
    3 values at 175/289 points (60%)** — a systematic, not scattered, elevation,
    matching the *session-level* interference pattern Artemisia's README documents
    (one run's whole wall-clock window sees heavier background load than another's,
    rather than isolated per-point scheduling blips). No discrete L3/LLC boundary
    is identifiable from existing data in this sub-range; a quiet re-run would be
    needed to settle it, same as Charnwood's still-open mid-region.
  - **Topmost/DRAM region: NOT flat at the pipeline's default 256 MiB ceiling —
    genuinely needs new data, not just more analysis.** `denseTail` (64-256 MiB,
    97 points): first-quarter median 222.9 ticks, last-quarter median 249.5 ticks,
    **+11.9%**, no sign of flattening — same "still climbing" situation every other
    machine hit at this ceiling (Sunbird/Crux/Charnwood/Skylark/Thunderbird/Ookay
    all needed a manual 256 MiB-1 GiB follow-up to resolve this). **This is the one
    piece of this section that cannot be settled from data already in this
    checkout — it requires actually running a new dense sweep on `upgrade` itself**
    (a session with `taskset -c 5` access to that machine, following the same
    256 MiB-1 GiB + 2-repeat pattern used on every other machine).
  - Sequential-pattern control stayed flat (6.1-8.4 ticks) across the entire coarse
    1 KiB-256 MiB range, consistent with every other machine's prefetcher-hides-DRAM-
    latency finding for the sequential control.

### line_size/
- Source file(s): 
- Build command: 
- Run command + arguments: 
- Sample count: 
- Notes on alignment/candidate strides tested: 

### associativity/
- Source file(s): `main_code/common/{main.c,associativity.c,associativity.h,benchmark.c,benchmark.h,pointer_chase.c,pointer_chase.h,random.c,random.h}`, `main_code/x86_64/timer_x86.h`, `main_code/common/timer.h`
- Build command: `make` (from repo root)
- Run command + arguments: `./scripts/run_associativity_full.sh upgrade 5 32768` — explicit hand-confirmed `cache_bytes` override, **L1 only**: the capacity section above only confirmed one clean boundary on this machine (L1 = 32,768 B, itself still flagged PROVISIONAL there); L2/L3 have no discrete confirmed value yet, so no candidate value was fabricated for them (per this script's own guidance, an explicit override is required for a "final" result — see `scripts/README.md`). All stages pinned `taskset -c 5`, `--samples 1000000 --batch-size 1000 --warmup-passes 3 --min-ways 2 --max-ways 40 --way-step 1`, base seed 12345 (repeats: 12346, 12347), both `--pattern random` and `--pattern sequential`. Timestamp: `20260912T013715Z`. Full transcript: `data_raw/upgrade/associativity/run_associativity_full_20260912T013715Z.log`.
- Sample count: 1,000,000 timed accesses per (num_ways, pattern) point; 39 points per sweep (num_ways=2..40), 3 sweeps (base + 2 repeats) per pattern
- Conflict-set construction method: node-to-node stride fixed at the level's own capacity (32,768 B for L1) so every probed node lands in the same cache set regardless of line size/way count (see `main_code/common/associativity.h`); `num_ways_probed` nodes chased in a dependent pointer chain, `random` = xorshift32-shuffled chain order, `sequential` = in-address-order control (prefetcher-sanity check, same convention as the capacity experiment)
- Result: **L1 = 8-way**, sharp/unambiguous knee — flat ~6.0-6.2 ticks/access for num_ways=2-8, jumping to ~15-19 ticks/access at num_ways=9 and climbing gently through 40 (both patterns behave the same, as expected for a capacity-thrashing effect rather than a prefetcher effect — see `data_processed/upgrade/associativity/L1/plots/associativity_curve.png`). Identical estimate (8) from the base sweep and both reproducibility repeats — no disagreement warning raised. This also cross-checks the capacity section's PROVISIONAL 32,768 B L1 boundary (a clean associativity knee at that stride is the same corroboration method used on Sunbird — see that machine's README).
- Notes: L2/L3 associativity via the standard full-capacity-stride method **not run** — blocked on the capacity section's open TODO (no discrete L2/LLC boundary identified yet on this machine). Instead, a new exploratory technique was tried for L2/LLC — see below.

#### L2/LLC: derived-stride scan (2026-09-12, EXPLORATORY — new technique, not a confirmed result)

**Motivation.** CLAUDE.md documents that on Sunbird, every associativity attempt above ~1 MiB stride broke at nearly the same `num_ways` (~9-10) regardless of the actual capacity candidate tested — strong evidence of a page-count-limited confound (DTLB or similar), since `run_associativity_full.sh`'s method always uses the *full* target capacity as the node-to-node stride, putting one probed node on its own distinct page for any capacity above 4 KiB. New script `scripts/run_associativity_stride_scan.sh` (added this session) instead tests `stride = capacity_candidate / A_guess` for a list of candidate divisors: any `A_guess` that evenly divides the true associativity still yields a mathematically valid same-set stride (see the script's own header comment for the modular-arithmetic argument, mirrored in `associativity.h`), but a much smaller one — touching far fewer distinct pages for the same `num_ways` swept. If the *same* knee value recurs across multiple different `A_guess` (hence different page counts), that's evidence of a real signal rather than a page-count artifact.

**Validation against known-good L1 data.** Ran the scan at `capacity_bytes=32768` (Upgrade's confirmed L1 stride) with `A_guess=1,2,4,8`: all four report knee=8 (matching the confirmed L1 result above) across arena sizes from 200 pages down to 25 pages — strong sanity check that the technique and its self-consistency logic work correctly.

**L2 candidate (2,097,152 B = 2 MiB, itself unconfirmed — picked as a round value inside this README's own "~1.5-4.5 MiB candidate shelf, not confirmed" note above).** Scan with `A_guess=1..64`: `A_guess=1` through `32` (strides 2,097,152 down to 65,536 B, 12,800 down to 400 pages) all report a first knee of **4**; `A_guess=64` (stride=32,768 B — exactly the L1 stride) correctly recovers **8** instead, i.e. the scan correctly detects it has shrunk the stride down into L1's own set rather than testing something new — an unplanned second validation of the technique.

**LLC-region candidate (16,777,216 B = 16 MiB, inside this README's noisy/unresolved ~5-22 MiB transition).** Scan with `A_guess=1..512`: **every** value from 1 through 256 (strides 16 MiB down to 65,536 B, 102,400 down to 400 pages — a 256x range) reports the same first knee of **4**; `A_guess=512` (stride=32,768 B, again the L1 stride) again correctly recovers **8**. Note several of these strides numerically coincide with strides already tested in the 2 MiB scan above (e.g. `A_guess=8` here = 2,097,152 B = the entire 2 MiB scan's `A_guess=1`), so this is not fully independent evidence, but it is a second capacity-candidate starting point converging on the same stride-indexed answer.

**Full-rigor confirm run at stride=65,536 B (1,000,000 samples, both patterns, 2 repeats, `--max-ways 24`) — this is the finding that keeps "L2=4-way" from being citable yet:** the plot (`data_processed/upgrade/associativity/L2/plots/associativity_curve.png`) shows a **two-step staircase**, not one clean knee — flat ~6.1 ticks/access through ways 2-3, a marginal/noisy partial rise at way 4 (this exact point has 47% spread across the base run and its 2 repeats: medians 6.1/6.0/9.4 ticks — base and repeat 1 called it thrashing, repeat 2 didn't, giving base=4, rep1=4, rep2=3), a plateau around ~12 ticks for ways 5-8, then a **second, much sharper jump at way 9** up to ~17-19 ticks. `scripts/detect_associativity.py` only ever reports the *first* knee it finds, so every scan result above only ever "saw" the first (marginal, ~4) step — none of them can speak to whether the second (~9) step is itself self-consistent across strides, and its location matches the exact confound signature from the Sunbird investigation closely enough to be a real concern, not a coincidence.

**Bottom line: a genuinely new, validated-on-L1 technique, and a reproducible two-tier structure was found for L2/LLC-scale strides — but it is NOT yet a citable L2 or LLC associativity number.** Two concrete follow-ups, neither attempted yet: (1) modify (or add a variant of) `detect_associativity.py` to locate a *second* knee, then re-run the stride-scan's self-consistency check on that second knee's location across the same `A_guess` range, to see whether *it* tracks page count (confound) or stays fixed (real, larger structure); (2) the marginal way=4 step itself needs a tighter, higher-sample-count re-check right at the ways=3-5 boundary before trusting even the "first tier" number. Raw/processed data: `data_raw/upgrade/associativity/stride_scan/`, `data_processed/upgrade/associativity/stride_scan/` (scan comparison tables) and `data_raw/upgrade/associativity/L2/`, `data_processed/upgrade/associativity/L2/` (the full-rigor confirm run at stride=65,536 B, timestamp `20260912T015914Z`). **Plot path correction (2026-09-12, later same day):** this run's plot was originally at `data_processed/upgrade/associativity/L2/plots/`, but that path was reused (and the PNG/PDF overwritten — the underlying timestamped CSVs were untouched) by the CAPACITY_RESULTS.md-driven run below. This run's plot has been regenerated from its own untouched summary CSVs at `data_processed/upgrade/associativity/L2/plots_derived_stride_65536B_20260912T015914Z/` — that is now the correct path for the two-step-staircase description above.

#### L1/L2/LLC: CAPACITY_RESULTS.md run (2026-09-12) — reproduces the same confound on L2/LLC; do not cite "4-way"

**Context:** `CAPACITY_RESULTS.md` was hand-assembled the same day from every machine's own capacity README, consolidating a suspected capacity per level per machine (Upgrade's row: L1 = 32,768 B, L2 = 262,144 B, LLC ≈ 12 MiB). Per the user's explicit request, `./scripts/run_associativity_full.sh upgrade 5 32768,262144,16777216` was run to test all three levels against those values (core 5 reconfirmed idle first via 3 `/proc/stat` samples 2s apart, 97-100% idle on both CPU5/CPU11 SMT siblings — same core as every other Upgrade run). The ~12 MiB LLC candidate is not a power of two (a hard `--cache-bytes` requirement, see `main.c`), so it was rounded to the nearest power of two, **16,777,216 B (16 MiB)** (16/12 = 1.33x vs. 8 MiB's 12/8 = 1.5x — 16 MiB is proportionally closer). Timestamp: `20260912T230322Z`; full transcript `data_raw/upgrade/associativity/run_associativity_full_20260912T230322Z.log`. Same fixed parameters as every associativity run on this machine: `--samples 1000000 --batch-size 1000 --warmup-passes 3 --min-ways 2 --max-ways 40 --way-step 1`, base seed 12345, repeats at 12346/12347, both `--pattern random` and `--pattern sequential`.

- **L1 (32,768 B): reconfirmed, 8-way, identical to the original run.** Base and both repeats all report 8, 0% disagreement — same sharp single knee as `20260912T013715Z` above. See `data_processed/upgrade/associativity/L1/plots/` (this run's plot overwrote the identical-shaped original; nothing lost, the estimate and shape are unchanged).
- **L2 (262,144 B): base=4, both repeats=4 — clean-looking, but this IS the known confound, not a real knee.** The full curve (`data_processed/upgrade/associativity/L2/plots/associativity_curve.png`, regenerated with a `CONFOUND SUSPECTED` title after the automatic pipeline's misleading `--estimate 4` marker was dropped) shows the same multi-step staircase as the 65,536 B derived-stride run above: flat ~6.0 through ways 2-3/4, first step to ~12.3-12.6 at way 5, second and much sharper step to ~17.6-17.8 at way 9, then a third, more gradual climb from ~way 20 onward reaching ~27 by way 32-40 (random pattern). `detect_associativity.py` only reports the *first* knee, so "4" here is the same marginal early step already flagged as an artifact, not the level's real associativity.
- **LLC (16,777,216 B, rounded from ~12 MiB): base=4, repeats disagree (3, 4) — pipeline's own disagreement warning fired.** Its curve (`data_processed/upgrade/associativity/L3_LLC/plots/associativity_curve.png`) is close to point-for-point the same shape as the L2 curve above — flat ~6.0-6.4 through ways 2-4, step to ~12.4-13.7 at way 5, sharper step to ~17.3-18.3 at way 9, third climb from ~way 20-21 onward to ~20.6-22.7 by way 33-40. Two strides 64x apart in byte size (262,144 B vs. 16,777,216 B) producing the *same* step locations (way 5, way 9, way ~20-21) is exactly the cross-stride signature CLAUDE.md already documents as a structural confound (DTLB-set-count or similar), not evidence of two different cache levels each independently having ~4-way associativity.
- **Conclusion: this run does not produce new, citable L2 or LLC associativity numbers — it reproduces the existing dead-end.** Consistent with the derived-stride finding above (which the automatic pipeline's first-knee detector also could not see past), any single-fixed-stride sweep at these byte values lands on the same universal small-way-count wall before it ever reaches a real L2 or LLC set's actual associativity. Do not report "L2 = 4-way" or "LLC = 4-way" for Upgrade from this data. The three required plots (L1, L2, L3_LLC) were still generated per the assignment ask, but the L2 and L3_LLC ones carry an explicit "CONFOUND SUSPECTED" caption instead of a false confidence marker; the L2/LLC associativity question on this machine remains exactly as open as the entry above states, pending the two follow-ups already listed (second-knee detection + stride-scan self-consistency check on it).

### latency/
Two sub-experiments, `hit_latency` and `miss_latency`, run 2026-09-13 (unattended
session, machine confirmed idle beforehand — see below). Footprint/target/evict
byte values taken **only from `CAPACITY_RESULTS.md`** (L1 = 32,768 B, L2 = 262,144
B, LLC ≈ 12 MiB = 12,582,912 B, per that file's directive that it is the single
source of truth for capacity boundaries — the per-machine capacity prose earlier
in this file, and any earlier CLAUDE.md capacity narrative, was NOT used to pick
these values, even where the two agree).

**Pre-run machine check:** `who` showed one other logged-in user (`dchen27`, an
idle tmux session since 2026-09-09, no active shell). `ps -eo pid,pcpu,psr,comm`
showed a `pmu_pilot` process pinned at ~100% CPU on PSR 2 (i.e. physical core 2,
CPUs {2,8}) — another student's Phase II PMU work, unrelated to this run. Two
`/proc/stat` snapshots 3s apart (delta, not point-in-time) confirmed cpu2=100%
busy (matching `pmu_pilot`) and **cpu5/cpu11 (physical core 5) at 0% busy**, all
other cores ≤0.3% — core 5 chosen, matching every prior Upgrade run
(capacity/associativity), and re-checked as still idle (only `pmu_pilot` on core 2)
immediately before the miss_latency run.

**hit_latency (dependent chain + independent-load diagnostic control):**
- Source file(s): `main_code/common/{main.c,latency.c,latency.h,benchmark.c,benchmark.h,pointer_chase.c,pointer_chase.h,random.c,random.h}`, `main_code/x86_64/timer_x86.h`, `main_code/common/timer.h`
- Build command: `make clean && make` (from repo root, after `git pull`; commit `e343732c0b57beece621da8e7c3a9bd8be236d25`)
- Run command + arguments: `./scripts/run_hit_latency_full.sh upgrade 5 L1:32768,L2:262144,LLC:12582912,DRAM:536870912` (pinned via `taskset -c 5`). DRAM's 536,870,912 B (512 MiB) footprint is not itself a `CAPACITY_RESULTS.md` boundary — it's a "deep in the DRAM plateau" pick per the task instructions, comfortably past the ~12 MiB LLC estimate.
- Per level: base run + 2 reproducibility repeats (seed = 12345, 12346, 12347), each at `--load-mode {dependent,independent}` × `--pattern {random,sequential}` (4 combinations), 1,000,000 timed accesses per combination (batch size 1000), 3 untimed warm-up passes.
- Dependent-chain batch size: 1000 (`--batch-size 1000`, `DEFAULT_BATCH_SIZE`).
- Regular vs. randomized control included: yes, both `--pattern random` and `--pattern sequential` run at every (level, load_mode) combination.
- Raw output filename(s): `data_raw/upgrade/latency/hit/<LEVEL>/hit_latency_{base,rep1,rep2}_{dependent,independent}_{random,sequential}_20260913T061042Z.csv.gz`
- Processing: `scripts/summarize_raw.py` per raw file → `data_processed/upgrade/latency/hit/<LEVEL>/*_summary_20260913T061042Z.csv` → `scripts/plot_hit_latency.py` → `data_processed/upgrade/latency/hit/<LEVEL>/plots/hit_latency_boxplots.{png,pdf}`.
- **Result (dependent, random pattern, base run median, n=1000 each): L1 ≈ 6.17 ticks, L2 ≈ 16.12 ticks, LLC ≈ 155.05 ticks, DRAM ≈ 251.56 ticks** — monotonically increasing 4-tier ladder. `--load-mode independent` measured faster than `dependent` at every level for the random pattern (e.g. LLC random: 38.80 vs 155.05; DRAM random: 45.60 vs 251.56 base-run; combined-across-repeats: 38.35 vs 155.44 and 46.08 vs 251.85), confirming the independent-load control correctly exposes memory-level parallelism as required.
- **UNEXPECTED flag investigated, not re-run — explained by prefetcher saturation, not a broken control:** `plot_hit_latency.py`'s required independent-vs-dependent check flagged `LLC sequential: independent >= dependent (6.99 vs 6.67 ticks) [UNEXPECTED -- investigate]` (combined across base+2 repeats). Checked all 3 individual runs before trusting this: base 6.996 vs 6.670, rep1 6.977 vs 6.650, rep2 6.983 vs 6.687 — the ordering is small (~0.3 ticks, ~5%) but *consistent* across all 3 independently-seeded runs, so it's a real, reproducible effect, not a noise flip. Root cause: at both LLC and DRAM footprints, the `sequential` pattern lets the hardware prefetcher hide essentially all of the real cache/DRAM latency for BOTH load modes — dependent-sequential and independent-sequential converge to within ~5% of the L1 floor (LLC seq: 6.67/6.99 vs L1 seq: 6.20/6.09; DRAM seq: 6.33/6.44), unlike the random pattern where the gap stays huge (LLC random: 155 vs 39). Once the prefetcher has already hidden nearly all real latency there is essentially no memory-level parallelism left for the independent mode to expose, so the comparison bottoms out on a smaller, secondary effect: `measure_independent_loads_batched()` (`main_code/common/benchmark.c`) does `nodes[order[idx]].next` — one extra load (reading `order[idx]`) per iteration versus the dependent chain's plain `last = last->next` — and that extra, otherwise-negligible load becomes visible as a small, consistent overhead once both modes are already running at the prefetch-bound floor. DRAM sequential shows the same near-tie (independent slightly faster there, 6.44 vs 6.46 combined, well inside the same noise band), consistent with this being one shared saturation effect at both deep levels rather than a level-specific bug. Not treated as invalidating the LLC/DRAM sequential numbers — both are genuinely reporting "prefetcher hides it," which is itself the correct physical finding for a sequential pattern at these footprints — but flagged here per this run's explicit instruction to investigate rather than silently trust it.
- Bug note: none found this run — the `--pattern`-aware independent-load addressing fix documented in Sunbird's README (2026-09-13) was already present in the pulled code (commit above), so this run did not need to rediscover or refix it.

**miss_latency (forced eviction + single-shot reload):**
- Source file(s): same list as hit_latency above.
- Wall-time calibration done before picking final parameters (core 5, random pattern, 100 trials each): ~223 ms/trial at evict_bytes=25,165,824 (2× LLC, the LLC→DRAM candidate) and ~83 ms/trial at evict_bytes=12,582,912 (the L2→LLC candidate). Extrapolated to the full base+2reps × 2-patterns × 200-trials workload: ≈4.5 min for LLC_to_DRAM, ≈1.7 min for L2_to_LLC, L1_to_L2's evict_bytes (262,144 B) is smaller than both so bounded above by the L2_to_LLC figure — total well under the ~15 min shrink threshold, so no evict_bytes reduction was needed and the full pipeline was run directly (not inside tmux; total wall time a few minutes).
- Run command + arguments: `./scripts/run_miss_latency_full.sh upgrade 5 L1_to_L2:32768:262144,L2_to_LLC:262144:12582912,LLC_to_DRAM:12582912:25165824` (core 5, same idleness check as hit_latency above, re-verified immediately before this run). `LLC_to_DRAM`'s evict_bytes (25,165,824 B = 2× the ~12 MiB LLC estimate) is not itself a `CAPACITY_RESULTS.md` value — it only needs to comfortably exceed LLC capacity to guarantee eviction into DRAM, and was picked directly from the calibration above (no oversized-evict-set mistake made or needed to revert on this machine).
- Per transition: base run + 2 reproducibility repeats (seed = 12345, 12346, 12347), each at `--pattern {random,sequential}`. 200 trials per (transition, pattern, run), `--batch-size 1` (meaningless to miss_latency's own logic, passed only to satisfy `main.c`'s cross-experiment `--samples`/`--batch-size` validation). 3 untimed warm-up passes before the first timed trial and again before every subsequent trial.
- Raw output filename(s): `data_raw/upgrade/latency/miss/<TRANSITION>/miss_latency_{base,rep1,rep2}_{random,sequential}_20260913T061519Z.csv.gz`
- Processing: `scripts/summarize_raw.py` → `data_processed/upgrade/latency/miss/<TRANSITION>/*_summary_20260913T061519Z.csv` → `scripts/plot_miss_latency.py --hit-latency-summary <matching hit_latency dependent/random summaries>` → `data_processed/upgrade/latency/miss/<TRANSITION>/plots/miss_latency_boxplots.{png,pdf}`.
- **Result (random pattern, base run median, n=200 each): L1→L2 ≈ 67 ticks, L2→LLC ≈ 510 ticks, LLC→DRAM ≈ 605 ticks** — monotonically increasing, consistent with genuinely deeper eviction at each transition. Run-to-run spread across the 3 repeats exceeded `plot_miss_latency.py`'s 20% stderr-warning threshold at **every one of the 6 (transition, pattern) combinations** (random: L1→L2 medians 67/123/116 = 54.9%, L2→LLC 510/424/636 = 40.5%, LLC→DRAM 605/461/617 = 27.8%; sequential: L1→L2 97.5/79/121 = 42.4%, L2→LLC 170.5/290/327.5 = 59.8%, LLC→DRAM 304/288/153 = 60.8%). Per this run's instructions, these warnings are noted rather than re-run-until-clean; consistent with this project's established pattern of real shared-machine interference showing up as scattered single-run spikes (see Sunbird/Crux/Charnwood/Thunderbird/Ookay's write-ups) rather than a flaw in the method — not independently traced to a specific interfering process for this run (only the pre-run and pre-miss_latency idleness checks above were done; no `mpstat`/`ps` snapshot was taken immediately after each individual repeat).
- **Single-shot measurement overhead, measured directly on this machine (2026-09-13):** control run `--target-bytes 32768 --evict-bytes 512 --pattern random --samples 2000 --batch-size 1 --seed 12345` (evict_bytes=512 B is ~8 cache lines, overwhelmingly unlikely to evict the L1-resident target most trials) gave **median = 55 ticks, mean = 56.0 ticks (n=2000)**. Compared against this machine's own L1 hit_latency dependent/random median (6.17-6.35 ticks across runs), the gap is **~48-49 ticks of fixed per-trial overhead** (timer serialization + post-function-call pipeline state, unamortized — see `main_code/common/latency.h`'s `run_miss_latency_experiment` docstring, "KNOWN LIMITATION" paragraph). Every miss_latency number above should be read as "true reload latency + ~48-49 ticks of fixed overhead," not a clean number; the increasing trend (67→510→605) is still meaningful evidence of deeper eviction, but absolute values and any direct incremental-penalty subtraction against a hit_latency plateau (`plot_miss_latency.py`'s annotation) are approximate, consistent with the same caveat Sunbird's README documents (though Sunbird's own control measured a higher ~64-85 tick floor — the two machines' fixed overheads are not identical, as expected for different CPU generations).
- Not yet done: the per-transition/per-pattern spread wasn't traced to a specific interfering process; the single-shot overhead above was only measured once, at the L1 footprint (not per-transition); and it hasn't been subtracted from the headline numbers (pipeline does not do this automatically).

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
