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
Both sub-experiments (`hit_latency`, `miss_latency`) run 2026-09-13, unattended,
core/idleness-checked but with no user present to interpret anomalies live —
see the LLC hit_latency investigation below for how one was handled. Footprint/
target/evict byte values taken **only from `CAPACITY_RESULTS.md`** (L1 =
49,152 B, L2 = 2,097,152 B, LLC ≈ 30 MiB = 31,457,280 B, using 1,048,576
B/MiB, not 1,000,000) per that file's own directive — this supersedes the
per-machine capacity prose earlier in this README/CLAUDE.md where the two
disagree (note in particular: `CAPACITY_RESULTS.md` flags L2=2,097,152 B as
sitting inside this machine's own continuous ~48 KiB–90 MiB capacity ramp,
not a real boundary, and LLC's ~30 MiB as not cross-validated by
associativity — both used anyway per this file's rule, caveats noted here).

**Idle-core check (before both runs):** `who`/`ps` showed no student processes
pinned to a specific core (top non-idle entries were background daemons —
`CrashPlanService`, an Elastic Agent fleet-server, `mongod`, `locate` —
none `taskset`-bound); two `/proc/stat` snapshots 3s apart showed every
logical CPU (including core 4 and its SMT sibling, logical CPU 60) at 0%
busy over that window. Ran both experiments on **core 4** (same physical
core used for this machine's 2026-09-12 associativity run, so cross-run
core comparisons stay apples-to-apples).

**hit_latency (dependent chain + independent-load diagnostic control):**
- Source file(s): `main_code/common/{main.c,latency.c,latency.h,benchmark.c,benchmark.h,pointer_chase.c,pointer_chase.h,random.c,random.h}`, `main_code/x86_64/timer_x86.h`, `main_code/common/timer.h`
- Run command + arguments: `./scripts/run_hit_latency_full.sh artemisia 4 L1:49152,L2:2097152,LLC:31457280,DRAM:536870912` (pinned via `taskset -c 4`; DRAM's 536,870,912 B footprint is not a `CAPACITY_RESULTS.md` value — a "deep in the DRAM plateau" pick well past LLC, same convention Sunbird's writeup used).
- Per level: base run + 2 reproducibility repeats (seed = 12345, 12346, 12347), each at `--load-mode {dependent,independent}` × `--pattern {random,sequential}`, 1,000,000 timed accesses per combination (`--batch-size 1000`), 3 untimed warm-up passes.
- Regular vs. randomized control included: yes, both `--pattern random` and `--pattern sequential` at every (level, load_mode).
- Raw output: `data_raw/artemisia/latency/hit/<LEVEL>/hit_latency_{base,rep1,rep2}_{dependent,independent}_{random,sequential}_20260913T060959Z.csv.gz`; full transcript `data_raw/artemisia/latency/run_hit_latency_full_20260913T060959Z.log`.
- Processing: `scripts/summarize_raw.py` → `data_processed/artemisia/latency/hit/<LEVEL>/*_summary_20260913T060959Z.csv` → `scripts/plot_hit_latency.py` → `data_processed/artemisia/latency/hit/<LEVEL>/plots/hit_latency_boxplots.{png,pdf}`.
- **Result (dependent, random pattern, base-run median, n=1000 each): L1 ≈ 9.87 ticks, L2 ≈ 28.05 ticks, LLC ≈ 94.38 ticks, DRAM ≈ 305.58 ticks** — a clean, monotonically increasing 4-tier ladder, reproduced across both repeats at L2/LLC/DRAM (28.05/30.02/27.18; 94.38/92.91/89.04; 305.58/300.78/299.64 — all within a few percent). L1's own three medians (9.866 / 9.921 / 5.986) show one low-side outlier (rep2) consistent with this machine's already-documented per-invocation P-state/turbo bimodality at small buffer sizes (same phenomenon flagged for this machine's capacity and L1-associativity data elsewhere in this file) — not treated as a boundary problem, just noted.
- At every level and both patterns, `--load-mode independent` measured faster than `dependent` **except one flagged case** (see below) — e.g. random pattern: L1 7.31 vs 8.59 (mean of medians), L2 8.49 vs 28.42, LLC 22.19 vs 92.11, DRAM 29.26 vs 302.00 — confirming the independent-load control correctly exposes memory-level parallelism at the random pattern, as required (must not be reported as the latency number itself, per `latency.h`).
- **Flagged anomaly, investigated per the run instructions (do not treat as a boundary/data problem): LLC, sequential pattern, base pipeline run reported `independent >= dependent` (24.42 vs 15.52 ticks) — the one "UNEXPECTED" the script's own printout raised.** Per-run breakdown: dependent-sequential medians [14.628, 13.463, 18.472] (base/rep1/rep2) vs. independent-sequential [17.677, 16.552, 39.031] — rep2's independent run (39.031) is a clear outlier vs. its own base/rep1 (16.6–17.7), but even excluding it, independent (~17.1 avg of base+rep1) still ran slower than dependent (~14.0 avg of base+rep1) at this one (level, pattern) combination. Investigated with 3 fresh, unpipelined seeds (111/222/333) directly at the same footprint: dependent-sequential medians came back **32.08 / 15.76 / 32.63** — a ~2x spread across just 3 back-to-back invocations — while independent-sequential stayed comparatively tight (21.43 / 23.50 / 23.26). This points to the *dependent*-sequential number being the noisy one, not independent being genuinely slower: because the hardware prefetcher hides almost all of the dependent-sequential chase's real latency at this footprint (it's a fully predictable, in-order chain), its small absolute tick count is disproportionately sensitive to this machine's already-documented per-invocation P-state/turbo variability, occasionally landing in a "slow" invocation that reads higher than independent's comparatively stable, prefetcher-hidden-but-slightly-larger baseline (independent mode issues one extra sequential/prefetchable load per access, from the `order[]` index array alongside the target array — see `benchmark.c`'s `measure_independent_loads_batched()` — which may also add a small, consistent floor at this footprint scale). Not resolved further (Phase I: timing-only, no PMU/perf) — flagged here as investigated-and-attributed-to-known-machine-noise rather than blocked on. Does not affect the primary/reportable random-pattern signal, which was clean and monotonic at every level including LLC.
- Bug found and fixed on Sunbird before this session (see `data_raw/sunbird/README.md`): independent-load addressing now correctly follows `--pattern` rather than always shuffling; this build already includes that fix.

**miss_latency (forced eviction + single-shot reload):**
- Source file(s): same list as hit_latency above.
- Wall-time calibration (core 4, random pattern, 100 trials, before picking final `evict_bytes`): the LLC_to_DRAM candidate must exceed the ~30 MiB LLC capacity; a first candidate at ~2x LLC (62,914,560 B / 60 MiB) measured **~1.036 s/trial**, which would have put the full base+2reps × 2-pattern run at ~21 minutes — over the ~15-minute guideline, so shrunk to 39,321,600 B (37.5 MiB, ~1.25x LLC, still comfortably past the 31,457,280 B boundary): **~0.49 s/trial**, extrapolating to ~9.8 minutes for that transition. L2_to_LLC (evict=31,457,280 B) calibrated separately at ~0.138 s/trial (~2.8 min total); L1_to_L2 (evict=2,097,152 B) at ~0.00237 s/trial (negligible). Total estimated wall time ~12.7 min, run without further shrinking.
- Run command + arguments: `./scripts/run_miss_latency_full.sh artemisia 4 L1_to_L2:49152:2097152,L2_to_LLC:2097152:31457280,LLC_to_DRAM:31457280:39321600` (core 4, same idleness check as hit_latency).
- Per transition: base run + 2 reproducibility repeats (seed = 12345, 12346, 12347), each at `--pattern {random,sequential}`. 200 trials per (transition, pattern, run), `--batch-size 1` (satisfies `main.c`'s cross-experiment validation only, no effect on miss_latency's logic). 3 untimed warm-up passes before every trial (re-touch target, re-walk eviction set).
- Raw output: `data_raw/artemisia/latency/miss/<TRANSITION>/miss_latency_{base,rep1,rep2}_{random,sequential}_20260913T061940Z.csv.gz`; full transcript `data_raw/artemisia/latency/run_miss_latency_full_20260913T061940Z.log`.
- Processing: `scripts/summarize_raw.py` → `data_processed/artemisia/latency/miss/<TRANSITION>/*_summary_20260913T061940Z.csv` → `scripts/plot_miss_latency.py` → `data_processed/artemisia/latency/miss/<TRANSITION>/plots/miss_latency_boxplots.{png,pdf}` (annotated against the matching hit_latency dependent/random summaries above).
- **Result (random pattern, base-run median, n=200 each): L1→L2 ≈ 188 ticks, L2→LLC ≈ 381 ticks, LLC→DRAM ≈ 582 ticks** — monotonically increasing, consistent with genuinely deeper eviction at each transition.
- **Run-to-run spread >20% flagged by `plot_miss_latency.py` at 3 of 6 (transition, pattern) combinations** (not re-run, per instructions — noted instead): L1_to_L2 sequential — medians 92/134/135 (base/rep1/rep2), 35.7% spread; L2_to_LLC random — medians 381/608/522, 45.1% spread; LLC_to_DRAM sequential — medians 386/208/220, 65.6% spread. (L1_to_L2 random 17.8%, L2_to_LLC sequential 10.6%, and LLC_to_DRAM random 3.1% all stayed under the threshold.) Consistent with this project's established pattern of real shared-machine interference/P-state noise producing scattered single-run spikes on this and other machines (see the hit_latency LLC anomaly above and this file's own Anomaly 1/2 write-ups) rather than a flaw in the method — not independently traced to a specific process per repeat.
- **Single-shot measurement overhead, measured directly per `latency.h`'s KNOWN LIMITATION and the run instructions:** `--target-bytes 49152 --evict-bytes 512 --pattern random --samples 2000 --batch-size 1` (a deliberately tiny, mostly-non-colliding eviction set — 8 cache lines, overwhelmingly unlikely to evict the target's own line) measured a **median of 70 ticks** (mean 69.97, n=2000), vs. hit_latency's batched L1 dependent-random median of ~9.87–9.92 ticks (base/rep1) at the identical 49,152 B footprint. **Gap ≈ 60 ticks of fixed single-shot overhead** (`timer_start()`/`timer_stop()` serializing-instruction cost and post-chase()-call pipeline state, unamortized — same mechanism documented on Sunbird, same order of magnitude: Sunbird measured ~64–85 ticks vs. its own ~10-tick batched L1 number). Every miss_latency number above should be read as "true reload latency + ~60 ticks of fixed overhead," not a clean number — the monotonic L1→L2→LLC→DRAM increase is still meaningful evidence of deeper eviction, but absolute values and any direct incremental-penalty subtraction against the hit_latency medians above are approximate until this overhead is subtracted, which the pipeline does not do automatically.
- Not yet done: no per-transition-specific overhead measurement (only measured once, at the L1/49,152 B footprint); the 3 flagged spread anomalies weren't traced to a specific interfering process via `mpstat`/`ps` at the time they occurred (only the pre-run idleness check was done).

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
