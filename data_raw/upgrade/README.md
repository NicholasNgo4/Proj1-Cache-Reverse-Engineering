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
  caveat) — no snapshot was saved at that time.

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

**Bottom line: a genuinely new, validated-on-L1 technique, and a reproducible two-tier structure was found for L2/LLC-scale strides — but it is NOT yet a citable L2 or LLC associativity number.** Two concrete follow-ups, neither attempted yet: (1) modify (or add a variant of) `detect_associativity.py` to locate a *second* knee, then re-run the stride-scan's self-consistency check on that second knee's location across the same `A_guess` range, to see whether *it* tracks page count (confound) or stays fixed (real, larger structure); (2) the marginal way=4 step itself needs a tighter, higher-sample-count re-check right at the ways=3-5 boundary before trusting even the "first tier" number. Raw/processed data: `data_raw/upgrade/associativity/stride_scan/`, `data_processed/upgrade/associativity/stride_scan/` (scan comparison tables) and `data_raw/upgrade/associativity/L2/`, `data_processed/upgrade/associativity/L2/` (the full-rigor confirm run, labeled `L2_derived_stride` in its plot title since the underlying capacity candidate is unconfirmed).

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
