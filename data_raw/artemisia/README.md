# artemisia — Reproduction Manifest

> Fill in every field before freezing results. This README must let a grader go from
> this folder to the exact command that generated the data without guessing.

## Machine Identification
- Hostname: artemisia.ece.ncsu.edu
- CPU model (from `lscpu`/`/proc/cpuinfo`): Intel(R) Xeon(R) Gold 5420+ (2 sockets, 28 cores/socket, SMT2 — 112 logical CPUs total)
- ISA / architecture: x86-64
- Vendor / microarchitecture / codename (researched, NOT from cache tables): Intel Sapphire Rapids (Golden Cove), per `MACHINE_RESEARCH.md` Table 1
- Introduction year (per the team's stated year convention): see `MACHINE_RESEARCH.md` (2023)
- Process node (if reliably documented): see `MACHINE_RESEARCH.md` (10 nm / Intel 7)
- Kernel version: Linux 6.17.8-1.el9.elrepo.x86_64
- Page size: 4096 bytes
- **Primary results below are from a 2026-09-09 redo on core 20**, superseding
  an original 2026-09-08 run on core 23 that turned out to share its socket
  with other students' active processes. The core-23 run and its analysis are
  archived in full under `data_processed/artemisia/capacity_prior_core23/`
  (not deleted) because the before/after comparison is itself informative —
  see the Anomaly sections below, which cite both runs directly.
- SMT siblings idle during the core-23 run (archived)? Nominally yes by a
  single 5s `/proc/stat` check immediately before launch, but this proved
  insufficient (see below). This session's cgroup/cpuset only grants logical
  CPUs `0-27,56-83` (socket 0 only, per `/proc/self/status Cpus_allowed_list`
  and `lscpu -e=CPU,CORE,SOCKET,NODE`). Machine was shared and heavily used:
  `who` showed 2 other logged-in users (4 sessions) and `uptime` reported load
  average 8.5/7.4/7.0 at the start of the run. `ps -eLo psr,...` at that time
  showed another student's `cache_bench`-style process (`hbsu`, PID 1481679,
  a different course project's benchmark) pinned to socket-1 cores, and a
  student's `block_size` benchmark (`clclark7`) pinned to core 2, same socket
  0 as our core — a plausible shared-L3 contention source. Core 23/79 itself
  never showed another user's process scheduled on it during spot checks, but
  the muddy 8-96 MiB region (Anomaly 2) later implicated broader session-level
  socket-0 load, not just core 23/79 directly.
- SMT siblings idle during the core-20 redo? Yes, more rigorously verified
  this time: at redo time `uptime` showed load average 30.47/30.88/31.01, but
  essentially all of it was ~25 of `dsengup2`'s python processes pinned to
  cores 28-55 (socket 1 — outside this session's cpuset entirely, per
  `ps -eLo pid,psr,pcpu,user,comm`). Within the allowed socket-0 set, a
  single `ps` snapshot showed core 4 (another student's `cache_bench` at
  ~99%) and core 13 (`updatedb`/`locate` at ~86-97%, a transient system
  cron job) busy. Rather than trust one snapshot (which the core-23 run's
  Anomaly 2 showed can miss slower-moving load), candidate cores were
  sampled via `/proc/stat` idle-time deltas across **three consecutive 6s
  windows** (18s total) — cores 6, 14, 17, 18, and 26 all looked idle in one
  window but spiked to 30-100% busy in a later window, underscoring that
  this machine's per-core load moves around and a single check is not
  trustworthy. Core 20 (logical CPUs 20, 76) was the only candidate under
  ~1% busy on both SMT siblings across all three windows and was selected.
  Pinning: `taskset -c 20 ./cache_bench ...`.

## Environment
- Compiler + version: GCC 11.5.0 (Red Hat 11.5.0-14)
- Compiler flags: `-O0 -g -std=c11 -Wall -Wextra -fno-omit-frame-pointer`
- Timer method used (RDTSC/RDTSCP+LFENCE, CNTVCT_EL0, etc.): x86 RDTSC (LFENCE-fenced
  start) / RDTSCP (LFENCE-fenced stop), batched: N=1000 dependent pointer-chase steps
  timed per start/stop pair, ticks/access = (t1-t0)/N. See `main_code/x86_64/timer_x86.h`.
- Affinity/binding command used: `taskset -c 20 ./cache_bench ...` (core-20 redo,
  primary); `taskset -c 23 ./cache_bench ...` (archived core-23 run)
- NUMA/locality method: no explicit NUMA pinning beyond CPU affinity; default
  first-touch allocation on the pinned CPU's own node (node 0) expected for
  `malloc`-then-touch. Not verified with `numastat` (Phase-I-safe, TODO if wanted).
- Git commit hash of the code used for these results: `881fbfc00f6bf576dfbc35cf5d97ce2a1aa09ad9`

## Per-Experiment Reproduction

### capacity/
- Source file(s): `main_code/common/{main.c,capacity.c,capacity.h,random.c,random.h}`,
  `scripts/cache_bench.c`, `scripts/pointer_chase.h`, `scripts/timer_x86.h`
- Build command: `make` (from repo root)
- Run command + arguments (**core-20 redo, primary, 2026-09-09**):
  Single driver script `data_raw/artemisia/capacity/run_full_redo_core20.sh`,
  launched inside a detached `tmux` session (`cache_redo_core20`) from the
  start so it would survive the driving session disconnecting; a second tmux
  session (`cache_redo_watch`) independently polled for completion. Stages,
  all at `--samples 1000000 --batch-size 1000 --warmup-passes 3 --seed 12345`,
  `taskset -c 20`:
  1. **Primary pipeline** (`scripts/run_capacity_full.sh artemisia 20`,
     timestamp `20260909T160641Z`): coarse sweep 1 KiB-64 MiB (ppo=8, both
     patterns) -> fixed 4x tail-extension 64-256 MiB (ppo=8) -> automatic
     boundary detection on combined random-pattern coarse+tail data -> dense
     sweep at ppo=48 (window = boundary/8 to boundary*8) around each of 7
     auto-detected boundaries -> 2 extra independent repeats of the deepest
     boundary's dense window -> a further dense sweep past the deepest
     boundary checking for a plateau. Took 16:06:41-17:36:02 UTC (~1h29m).
  2. **256 MiB-1 GiB tail-extension window**: base sweep (timestamp
     `20260909T173602Z`, ~1h08m) + 2 independent repeats (`20260909T184427Z`,
     `20260909T195921Z`), checking whether the top region plateaus.
  3. **8-96 MiB mid-transition window**: 2 independent repeats
     (`20260909T210741Z`, `20260909T211227Z`), targeting the region that was
     noisiest on core 23.
  Total wall time: 16:06:41-~21:17 UTC (~5h11m), faster than the archived
  core-23 run (~6.5h) despite doing strictly more work in one continuous
  script rather than a harness-driven handoff to tmux partway through.
- Run command + arguments (**archived core-23 run, 2026-09-08**, for reference):
  1. **Primary pipeline** (`scripts/run_capacity_full.sh artemisia 23`, timestamp
     `20260908T220941Z`): same stages as above, taskset -c 23.
  2. **Manual follow-up #1**: one additional 256 MiB-1 GiB dense sweep,
     timestamp `20260908T234652Z`.
  3. **Manual follow-up #2**: run via a detached `tmux` session (`cache_ext`,
     `data_raw/artemisia/capacity/run_extension_repeats.sh`) after a harness
     handoff mid-run — 2 more repeats of the 256 MiB-1 GiB window (timestamps
     `20260909T005539Z` [duplicate rep1, pre-handoff], `20260909T020545Z`,
     `20260909T031435Z`) and 2 repeats of the 8-96 MiB window
     (`20260909T042430Z`, `20260909T042841Z`).
- Sample count: 1,000,000 timed accesses per (size, pattern) point; 3 warm-up
  passes excluded from that count.
- Random seed(s): 12345 (xorshift32, random pattern); sequential pattern uses
  no randomness.
- Raw output filename(s): `data_raw/artemisia/capacity/capacity_{coarse,coarse_ext,
  dense0..dense6,dense6_rep1,dense6_rep2,denseTail,denseExt2,denseExt2_rep1,
  denseExt2_rep2,denseMid_rep1,denseMid_rep2}_{random,sequential}_<timestamp>.csv.gz`
  (both the core-20 redo's and the archived core-23 run's raw files coexist
  here, distinguished only by timestamp — the filenames-without-timestamp
  convention is in the *processed* summaries, not the raw files). **Gzip
  -compressed in place** post-hoc (466 MB -> 64 MB, ~86% reduction) before
  committing — decompress with `gunzip`/`zcat` before re-running
  `summarize_raw.py` on them; the pipeline scripts themselves still write
  plain `.csv` when run fresh, compression is a separate step done once the
  run finished. Full
  transcripts: `run_capacity_full_20260909T160641Z.log` + `tmux_full_redo_core20.log`
  (core-20 redo); `run_capacity_full_20260908T220941Z.log` + `tmux_extension_run.log`
  (archived core-23 run).
- Processing script -> data_processed path: `python3 scripts/summarize_raw.py
  <raw.csv> -o data_processed/artemisia/capacity/<name>_summary.csv` for every raw
  file from the core-20 redo, then `python3 scripts/plot_capacity.py <all summary
  csvs> -o data_processed/artemisia/capacity/plots --machine artemisia --boundary
  49152 --boundary 2097152 --boundary 94371840` for the curve/box-plot figures.
  The archived core-23 run's summaries/plots live under
  `data_processed/artemisia/capacity_prior_core23/`, generated the same way,
  using the **same three boundary flags** so the two boxplots are directly
  comparable.
- Excluded runs (if any) and reason: none excluded; all raw/summary pairs retained
  (including the archived core-23 run, kept for the before/after comparison).

#### Detected boundaries and plateau status

Auto-detector output on the core-20 redo's primary pipeline (bytes): `1720,
3440, 30048, 2097152, 3234248, 33554432, 39903168`. (For reference, the
archived core-23 run detected `16384, 30048, 2097152, 3234248, 15384768,
23726560, 56431600` — a different set, because the detector is sensitive to
noise in the sub-48 KiB region on *both* runs; see Anomaly 1.) As before,
most of these do **not** correspond to genuine, distinct cache-capacity
plateaus. The empirically supported picture, now confirmed on a second,
verifiably-idle core:

| Region | Status | Notes |
|---|---|---|
| ~1-48 KiB | **Confounded, not a clean plateau at the point level** | Should be flat (pure L1 hits); instead shows per-invocation bimodal noise (see Anomaly 1), on **both** core 20 and core 23. The auto-detected tiny-size boundaries (1720/3440 on core 20; 16384/30048 on core 23) are detector artifacts of that noise on both runs, not real transitions — and the fact that they differ between runs is itself evidence they're noise, not a repeatable feature of the hardware. |
| ~48-55 KiB onset -> ~90 MiB | **One continuous ramp, not discrete steps** | Latency climbs smoothly and reproducibly on both runs, with no flat intermediate plateau anywhere in this span. Confirmed again by 2 independent core-20 repeats of the 8-96 MiB sub-window. The remaining auto-detected boundaries in this range (2097152, 3234248, 33554432, 39903168 on core 20; 2097152, 3234248, 15384768, 23726560, 56431600 on core 23) all fall inside this one broad transition; treat them as waypoints along a ramp, not as separate cache levels. |
| ~90 MiB+ (sequential pattern) | **CONFIRMED genuine plateau** | Core 20: mean 35.41 ticks/access (n=73, range 33.4-36.4) from ~90 MiB through 1 GiB. Core 23: mean 35.55 (n=61, range 35.2-35.9). The two idle-vs-contended runs agree to within 0.4%, which is strong evidence this is a real hardware plateau (sequential/prefetched DRAM bandwidth limit) and not an artifact of either run's specific conditions. |
| ~90 MiB+ (random pattern) | **Still open beyond 1 GiB, but core-quality-dependent in magnitude** | Both runs show continued growth from 256 MiB to 1 GiB with no flattening — but core 20 (idle) grows only **+10.8%** (286.1 -> 317.1 ticks) vs core 23 (contended) growing **+21.8%** (260.1 -> 316.7 ticks). The two runs converge to nearly the same value at 1 GiB (~317 ticks either way) but core 23 started lower at 256 MiB and climbed more steeply. This means contention was inflating the *apparent* growth rate on core 23, but a genuine, smaller (~11%) growth persists even on an idle core — consistent with the working hypothesis of growing TLB/page-walk overhead as the buffer spans more distinct 4 KiB pages (Sapphire Rapids has no cache level beyond the shared L3, so this isn't a further capacity boundary). Left unresolved beyond 1 GiB. |

#### Anomaly 1: sub-48 KiB per-invocation P-state bimodality

Every summary row below ~48 KiB that overlaps between two different
`cache_bench` invocations (e.g. `dense0` vs `dense1`, run seconds apart in the
same session) shows the *same* two medians recurring — approximately 5.1 and
9.6-10.1 ticks/access (~1.9x apart) — with the value depending on **which
invocation** measured that size, not on the size itself. E.g. at 8.23 KiB,
`dense0`=9.7, `dense1`=5.1; at 8.35 KiB, `dense0`=9.6, `dense1`=5.1; the same
flip recurs at nearly every overlapping point across dozens of sizes. Since
this range should be pure L1 hits (flat true latency), a per-size effect is
ruled out; a per-invocation effect fits: TSC ticks per access scale inversely
with the core's instantaneous clock (fixed dependency-chain length in core
cycles / clock frequency x invariant-TSC frequency), so a short `cache_bench`
process that happens to run at a lower opportunistic-turbo bin for its whole
(sub-second) duration will read out ~1.9x more ticks/access than one that
gets full turbo — consistent with the observed ratio. **Practical effect on
the boundary detector**: this noise floor is comparable to or larger than the
true L1 ramp signal at small sizes, so the detector's 16384/30048 "boundaries"
are false positives from this effect, not real transitions.

**Confirmed on the core-20 redo, ruling out contention as the cause.** If
this were a contention artifact, moving to a verifiably idle core should have
made it mostly disappear. It didn't: `dense0` vs `dense1` on core 20 still
shows the same cross-invocation bimodality across 180 overlapping sub-48 KiB
points (median ratio 1.41x, max 1.98x) — essentially the same magnitude as
core 23's 178 points (median ratio 1.26x, max 1.98x; the max is nearly
identical between runs). Since core quality changed but the effect didn't go
away, this is strong evidence the P-state/turbo-boost hypothesis above is
correct and multi-tenant contention was never the driver of this particular
anomaly — it's an artifact of how short a single `cache_bench` invocation is,
independent of what else is running on the machine.

#### Anomaly 2: session-level (not per-point) noise in the 8-96 MiB transition

Naively pooling every run covering the 8-96 MiB window shows apparent
per-point spread up to 50-100%, which looks like ordinary high measurement
noise. Splitting by **which session** each run came from shows otherwise:
the 6 runs launched in the initial evening pipeline (all ~`20260908T220941Z`)
agree tightly with each other (typical spread 0.2-6%, worst-case ~17% right
in the steepest part of the transition around 9-10 MiB), and the 2 runs
launched independently ~6 hours later (`20260909T0424xxZ`) likewise agree
tightly with each other — but the two sessions sit **systematically apart**
from one another by 17-33% (growing with size), e.g. at 8.98 MiB: evening
mean 63.0 vs morning mean 53.9 ticks (evening/morning individual spreads
16.2%/0.0%). The same evening/morning split shows up in the sequential
pattern too (e.g. ~35 evening vs ~25-30 morning at several points in
30-95 MiB), confirming this is a shared-machine-load effect, not something
specific to the random pointer-chase. This matches the multi-user
interference this session directly observed via `who`/`ps` (see Machine
Identification above) varying in intensity over the course of the night —
it is a real, reproducible, slow (multi-hour-scale) drift in background
contention, not per-sample jitter. **Practical implication**: naively
averaging across sessions (as `plot_capacity.py`'s overlap-combining does by
default) overstates noise in this region — each session's own data is
precise; the environment, not the measurement, is what varies. Use median
(not mean) and report the per-session spread alongside the pooled spread
when citing a specific latency value from this region.

**Partially, not fully, explained by contention — core-20 redo shows a
real improvement but not a clean resolution.** Repeating the same 8-96 MiB
window twice on the idle core-20 redo (`denseMid_rep1` vs `denseMid_rep2`,
173 overlapping points each): median rep-to-rep spread dropped from 7.9%
(core 23) to **4.2%** (core 20) — a genuine, roughly 2x reduction consistent
with removing session-level contention as a noise source for the *typical*
point. But the worst-case behavior barely changed: p90 spread is 38.1%
(core 20) vs 30.0% (core 23), and max spread is 96.1% (core 20) vs 93.0%
(core 23) — both runs have a handful of points with large swings even though
core 20 had no observed contention during either repeat. **Revised
conclusion**: multi-tenant load explains part of this region's noise (the
typical-case improvement on core 20 confirms that), but not all of it — there
is a second, still-unidentified source of occasional large point-to-point
swings that contention alone doesn't account for. Candidates not yet ruled
out: thermal/frequency transients independent of other users' load, or
memory-allocator/page-placement differences between invocations (analogous
in spirit to Anomaly 1's per-invocation effect, but at a coarser timescale).
Flag as open if a future session wants to chase it further; not blocking for
Phase I reporting purposes given the region is already correctly characterized
as "one continuous ramp, not discrete steps" regardless of this residual noise.

### line_size/
- Source file(s):
- Build command:
- Run command + arguments:
- Sample count:
- Notes on alignment/candidate strides tested:

### associativity/
- Source file(s): `main_code/common/associativity.c`, `associativity.h`
- Run command + arguments: `./scripts/run_associativity_full.sh artemisia 4 49152,2097152,31457280`
  (core 4; confirmed idle via two `/proc/stat` idle-delta samples ~4-9s apart,
  both <1% busy on CPU 4 and its SMT sibling CPU 60, plus a `ps` check for
  competing processes on those CPUs — see "Known constraints" in `CLAUDE.md`
  for why a single snapshot isn't trusted on this machine)
- Conflict-set construction method: node-to-node stride fixed at each level's
  own capacity (see `associativity.h`'s docstring), sweeping num_ways=2-40,
  both patterns, base run + 2 reproducibility repeats (distinct seed per
  repeat) — standard `run_associativity_full.sh` pipeline, unmodified.
- `cache_bytes` values: taken directly from `CAPACITY_RESULTS.md` (this
  session's hand-curated capacity table), **not** auto-detected: L1 =
  49,152 B (48 KiB), L2 = 2,097,152 B (2 MiB), LLC = 31,457,280 B (30 MiB,
  the exact-multiple-of-4096 reading of that file's "~30 MiB" entry).
  base_seed=12345 (repeats 12346/12347), samples=1,000,000/point,
  max_ways=40, timestamp=20260912T232217Z.
- **Caveat carried over from this file's own capacity section, above: this
  machine's own capacity data explicitly flags 2,097,152 B as NOT a real
  boundary** — it's one of the auto-detected "waypoints" the
  "Detected boundaries and plateau status" table calls out by that exact
  byte value as falling inside the single continuous ~48 KiB-90 MiB ramp,
  with no discrete L2/L3 shelf found anywhere in that span on two
  independent runs (core 20 idle, core 23 contended). The LLC value is a
  rounded reading of a "~30 MiB" *manual* estimate, not a value this
  machine's own dense capacity sweep resolved as a clean knee either. Ran
  anyway per explicit instruction to proceed and document honestly, not to
  block on this conflict.
- **Results:**
  - **L1 (cache_bytes=49,152 B): not cleanly confirmed, unlike Sunbird/
    Upgrade's L1=8-way.** Base sweep's automatic knee detector reports 12
    (flat through num_ways=12, jump to a clean, low-spread ~16.2 ticks/
    access shelf at 13-24, then a **second, unexplained jump** to ~23
    ticks/access at ~25-29, flat through 40). Repeat 1 also reports 12;
    repeat 2's detector instead reports 3 — flagged as a disagreement by
    the pipeline itself. Inspecting repeat 2's raw per-point medians shows
    this "3" is a false positive: num_ways=2-12 there is highly
    non-monotonic (medians bounce 5.1/5.1/9.7/8.3/5.1/5.6/6.1/5.9/6.1/5.1/
    6.1 ticks), matching the same per-invocation P-state/turbo bimodality
    already documented in this file's "Anomaly 1" for small-buffer L1-scale
    capacity data on this machine — the detector locked onto one noisy
    spike (way 4) rather than a real knee, and repeat 2's own data still
    transitions cleanly to the ~16.2 shelf at exactly num_ways=13, same as
    base. So the clean, reproducible transition point is num_ways=13 in
    every run — plausibly consistent with associativity=12 (Sapphire
    Rapids' real L1D is a 48 KiB structure, and 12-way would be a
    physically ordinary width for that size) — but this run cannot call it
    machine-confirmed the way Sunbird/Upgrade's L1=8 was, both because of
    the noisy substrate and because of the second, unexplained ~16.2->23
    tick jump past it, which no existing hypothesis in `CLAUDE.md` accounts
    for yet (possibly the same confound found in L2/LLC below, showing up
    here as a secondary structure past the real L1 knee).
  - **L2 (cache_bytes=2,097,152 B) and LLC (cache_bytes=31,457,280 B):
    produced nearly IDENTICAL curves despite a 15x stride difference —
    clean, Phase-I-safe evidence this method cannot resolve either level's
    real associativity here, same conclusion as Sunbird/Upgrade, now on a
    third, architecturally distant machine.** Both: noisy num_ways=2-6
    (~5.5-7 ticks), a clean flat plateau at ~11.2-12.1 ticks through
    7-12, then a jump to the same ~23-tick ceiling seen in L1's final
    plateau, flat through num_ways=40. Automatic detector: L2 base=6,
    rep1=5, rep2=6 (disagreement flagged by the pipeline); LLC
    base=rep1=rep2=6 (only level with 3/3 repeat agreement — but see next
    sentence before trusting that as confirmation). A genuine L2 and a
    genuine LLC cannot share the same associativity number *and* the same
    absolute hit/miss latency at every probed width — this is the same
    "universal small-structure wall" signature `CLAUDE.md` documents from
    Sunbird's and Upgrade's large-stride attempts (there: ~9-10 way;
    here: ~6, then a shared ~23-tick ceiling regardless of level), most
    likely the same DTLB/page-structure aliasing hypothesis, now
    reproduced on a third CPU generation. **Do not cite "L2=6-way" or
    "LLC=6-way" (or any number from this run) as this machine's real L2/
    LLC associativity — flag as confounded/unresolved, matching Sunbird's
    and Upgrade's writeups in `CLAUDE.md`.** `--huge-pages` exists in
    `cache_bench`/`associativity.c` specifically to test the DTLB
    hypothesis directly (collapses the whole probe buffer onto one TLB
    entry via a 2 MiB huge page) but is not yet wired into
    `run_associativity_full.sh` and has not been exercised on any
    machine, including this run — natural next step before trying more
    candidate byte values here.
- Underlying data/plots: `data_raw/artemisia/associativity/{L1,L2,L3_LLC}/`
  (gzipped raw CSVs + full transcript
  `run_associativity_full_20260912T232217Z.log`),
  `data_processed/artemisia/associativity/{L1,L2,L3_LLC}/plots/
  {associativity_curve,associativity_boxplots}.{png,pdf}`.

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
- Reserved core/package (primary, core-20 redo): core 20 (logical CPUs 20, 76),
  chosen via 3x 6s `/proc/stat` idle-time sampling windows and `ps`/`who`
  checks, not a formal reservation system. Benchmark run inside detached tmux
  session `cache_redo_core20`; a second tmux session `cache_redo_watch`
  independently tracked completion so progress-tracking would survive this
  driving Claude Code session (or the user's terminal) disconnecting.
- Time window (core-20 redo): 2026-09-09 16:06 UTC - 2026-09-09 21:17 UTC (~5h11m)
- Reserved core/package (archived core-23 run): core 23 (logical CPUs 23, 79),
  chosen via a single 5s `/proc/stat` sample — later shown to be insufficient
  (see Machine Identification and Anomaly 2 above).
- Time window (archived core-23 run): 2026-09-08 22:09 UTC - 2026-09-09 04:29 UTC (~6h20m)
