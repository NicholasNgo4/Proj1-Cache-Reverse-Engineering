# upgrade — Reproduction Manifest

> Fill in every field before freezing results. This README must let a grader go from
> this folder to the exact command that generated the data without guessing.

## Machine Identification
- Hostname: **TODO — not captured by any committed file; needs a session actually
  logged into `upgrade` to run `hostname`.** (This repo checkout is on `sunbird`;
  analysis below was done entirely from already-committed `data_raw`/`data_processed`
  CSVs, which don't carry the hostname.)
- CPU model (from `lscpu`/`/proc/cpuinfo`): TODO — same caveat; `MACHINE_RESEARCH.md`
  lists "Core i7-8700 / Coffee Lake" but that table is the team's separate ISA/
  microarch/year research (explicitly allowed pre-freeze), not a live `lscpu` capture
  on this specific machine — don't cite it here as if it were one without confirming.
- ISA / architecture: x86-64 (inferred from `main_code/x86_64/timer_x86.h` being the
  timer header used — see Environment below — but not independently confirmed via
  `uname -m` on the machine itself)
- Vendor / microarchitecture / codename (researched, NOT from cache tables): TODO
- Introduction year (per the team's stated year convention): TODO
- Process node (if reliably documented): TODO
- Kernel version: TODO — no `build/kernel_version.txt` was captured for this machine
  (unlike Sunbird's `build/` dir); needs `uname -r` on `upgrade` itself.
- Page size: TODO — no `build/page_size.txt` captured either.
- SMT siblings idle during runs? TODO — core=5 was used (confirmed from the run
  transcript, see capacity/ below) but no `who`/`ps`/`lscpu -e` snapshot was saved,
  so idle-sibling status at run time is unverified.

## Environment
- Compiler + version: TODO
- Compiler flags: `-O0 -g -std=c11 -Wall -Wextra -fno-omit-frame-pointer`
- Timer method used (RDTSC/RDTSCP+LFENCE, CNTVCT_EL0, etc.): x86 RDTSC/RDTSCP path
  (inferred from `main_code/x86_64/timer_x86.h` per the build layout; not
  independently confirmed with a disassembly excerpt the way Sunbird's is — TODO if
  needed for the report)
- Affinity/binding command used: `taskset -c 5 ./cache_bench ...` (core=5, confirmed
  from `run_capacity_full_20260908T231109Z.log`'s own header line)
- NUMA/locality method: TODO
- Git commit hash of the code used for these results: TODO — no
  `build/git_commit_at_run.txt` was captured for this machine.

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
