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
- Source file(s): `main_code/common/{main.c,line_size.c,line_size.h,random.c,random.h}`,
  `scripts/{cache_bench.c,pointer_chase.h,timer_x86.h,run_line_size.sh,
  plot_line_size_family.py,plot_line_size.py,detect_line_size.py,summarize_raw.py}`
- Build command: `make` (from repo root)
- Run command + arguments (**2026-09-12, first pass — Method A steps 1-3 + full Method B,
  no step-4 candidates yet**): `./scripts/run_line_size.sh artemisia 20
  49152,2097152,94371840` (boundaries = this machine's own established L1/L2/L3-onset
  capacity boundaries, see `CAPACITY_RESULTS.md` and the capacity/ section above; core 20
  reused deliberately — the same core independently re-verified idle via a fresh 3-window
  `/proc/stat` sample immediately before this run, no other `cache_bench` process running).
  Default coarse strides 8/16/32/64/128/256B, samples=1,000,000, batch=1000, seed=12345,
  align-bytes=4096, points-per-octave=6. Run inside a detached `tmux` session
  (`artemisia_line_size`) per this project's convention for long runs. Timestamp
  `20260912T213325Z`; full transcript
  `data_raw/artemisia/line_size/run_line_size_20260912T213325Z.log`.
- Sample count: 1,000,000 timed accesses per (stride, footprint, pattern) point; 2 warm-up
  passes (Method A) / 3 (Method B) excluded from that count.
- Notes on alignment/candidate strides tested: Method A step 4 (bracket + 0-56B offset
  refinement) was **not yet run** — no `candidate_overrides_csv` was supplied on this pass,
  per the script's own design (no auto-detection; a human must inspect
  `line_size_family_curve.png` first). Findings from steps 1-3 + Method B, by level:
  - **L1 (boundary=49,152B, window=[6144,196608]): clean, confident 64B.** Both methods
    agree. Method A's auto-pick: per-stride elbow footprints (bytes) `{8B: 110336, 16B:
    110336, 32B: 87552, 64B: 55168, 128B: 55168, 256B: 55040}` -> smallest stride agreeing
    with the largest-stride (256B) reference is **64B**. Visual inspection of
    `data_processed/artemisia/line_size/level_49152/plots/line_size_family_curve.png`
    strongly corroborates this independent of the numeric picker: the 64/128/256B curves
    are visually indistinguishable, rising in lockstep to a shared ~16 ticks/access
    plateau at the same footprint (~2^15.85 B), while 8/16/32B stay measurably lower and
    ramp up more gradually (32B partially, 8/16B most) — exactly the signature the method
    predicts for strides at/above vs. below the true line size. Method B (single-curve,
    footprint=98,304B) independently auto-detected **64B** from ramp-saturation with no
    manual intervention. **Two independently-designed methods agreeing = frozen Phase I
    result for this level.**
  - **L2 (boundary=2,097,152B, window=[262144,8388608]): visual evidence also points to
    64B, but the numeric auto-pick is NOT trustworthy here — read before citing.**
    Per-stride elbow footprints: `{8B: 4707944, 16B: 4707936, 32B: 3736672, 64B: 3328960,
    128B: 3328896, 256B: 3328768}` -> the auto-picker's smallest-agreeing-stride answer is
    **32B** (ratio to the 256B reference = 1.122, just inside the 1.2 `separation_ratio`
    threshold) — but this is exactly the "coincidental near-boundary agreement" failure
    mode the script's own docstring warns about, not a real signal: visually, in
    `data_processed/artemisia/line_size/level_2097152/plots/line_size_family_curve.png`,
    the 64/128/256B curves track closely together throughout (plateauing ~65-73
    ticks/access from ~2^21.5B), while 32B sits measurably and consistently below them and
    8/16B sit lowest — the same qualitative pattern as L1, with 64B (not 32B) as the
    better-supported line-size candidate. Method B found **no transition** in its coarse
    sweep (footprint=4,194,304B = 2x boundary) — flagged 4 likely page-aliasing spike
    strides (128/256/512/1024B) but no clean saturation elbow, so no B-method corroboration
    at this level yet.
  - **L3-onset window (boundary=94,371,840B [90 MiB], window=[11796480,268435456]):
    inconclusive/noisy — expected, not a real anomaly.** Per-stride elbow footprints:
    `{8B: 94371840, 16B: 118901056, 32B: 94371840, 64B: 118901056, 128B: 118900992, 256B:
    133461760}` — non-monotonic in stride (8B and 32B match each other; 16/64/128B match
    each other; 256B separate again), and the auto-picker's "16B" answer has no visual
    support: in
    `data_processed/artemisia/line_size/level_94371840/plots/line_size_family_curve.png`
    the six stride curves cross and re-order repeatedly across the whole window with no
    clean convergence signature at any stride threshold (32B actually leads for most of
    the range, the opposite of the expected ordering). This is consistent with — not
    contradicting — this machine's own capacity finding
    (`CAPACITY_RESULTS.md` / capacity/ section above) that ~48-55 KiB through ~90 MiB is
    **one continuous ramp with no discrete plateau**, and 90 MiB is only the *onset* of the
    sequential-pattern plateau, not a clean, already-established cache-level edge the way
    L1/L2 boundaries are — the family-of-curves method's core premise (comparing where
    curves saturate against a real capacity plateau) doesn't cleanly apply to a window that
    isn't itself at a real boundary. Method B likewise found no transition. Not pursued
    further this pass; a step-4 run here would need a better-established LLC/DRAM boundary
    first (this machine doesn't have one — see the open items in capacity/ above).
  - **Recommended next step (not yet run):** re-run with
    `candidate_overrides_csv=64,64,` (L1 and L2 at 64B, L3-onset skipped) to get Method A's
    step-4 bracket (56/64/72B at 8B granularity) + 0-56B offset-invariance check, which
    would let the two already-agreeing L1 signals plus L2's visual-but-unconfirmed 64B
    candidate be checked against alignment sensitivity before either is cited as fully
    confirmed.

- Run command + arguments (**2026-09-12, second pass — independent full re-run, same
  boundaries/core/seed, no step-4 candidates yet — a reproducibility check, not a step-4
  refinement**): same command, `./scripts/run_line_size.sh artemisia 20
  49152,2097152,94371840`, re-launched from a fresh detached `tmux` session
  (`artemisia_line_size_rerun`) ~20 minutes after the first pass. Core 20 re-verified idle
  again beforehand (3-window `/proc/stat` sample: cpu20 busy 4.8/5.2/0.5%, sibling cpu76
  busy 0.0/4.8/11.8% — light shared-machine background jitter, not a competing benchmark;
  no other `cache_bench` process running). Timestamp `20260912T215134Z`; full transcript
  `data_raw/artemisia/line_size/run_line_size_20260912T215134Z.log`.
  - **L1: reproduced exactly.** Per-stride elbow footprints came back byte-for-byte
    identical to the first pass: `{8B: 110336, 16B: 110336, 32B: 87552, 64B: 55168, 128B:
    55168, 256B: 55040}` -> same 64B auto-pick, and Method B independently re-detected 64B
    again too. Visual inspection of the re-generated
    `line_size_family_curve.png` shows the same 64/128/256B lockstep-to-plateau signature
    (some below-64B curve *shape* wobble between the two runs — e.g. 16B tracks closer to
    32B this time than it did in the first pass — but the ≥64B cluster and its elbow
    location are unchanged). **This is now a twice-reproduced, two-method-agreeing result —
    the strongest-evidenced number in this machine's whole line-size dataset.**
  - **L2: also reproduced exactly, still short one corroborating method.** Elbow footprints
    identical to the first pass: `{8B: 4707944, 16B: 4707936, 32B: 3736672, 64B: 3328960,
    128B: 3328896, 256B: 3328768}` -> auto-pick still lands on 32B (same
    known near-threshold-agreement caveat as before — not trusted at face value), and the
    64/128/256B-track-together-while-32B-sits-below visual pattern reproduced too. Method B
    again found no transition. Reproducibility strengthens confidence that 64B is the real
    L2 answer (not run-to-run noise), but it's still a visual read, not a second
    independently-designed method's confirmation the way L1 has.
  - **L3-onset window: did NOT reproduce — and that instability is itself the useful
    result.** Elbow footprints came back substantially different from the first pass at
    3 of 6 strides: `{8B: 168151496 (was 94371840), 16B: 118901056 (unchanged), 32B:
    105928800 (was 94371840), 64B: 74902976 (was 118901056), 128B: 133461888 (~unchanged),
    256B: 133461760 (unchanged)}`. Auto-pick coincidentally landed on 16B again, but via a
    different, equally-unreliable path. This run-to-run instability in exactly the window
    this machine's own capacity data already flags as "one continuous ramp, no discrete
    plateau" (see capacity/ section above) is corroborating evidence, not a new problem: a
    genuine cache-level boundary's elbow should reproduce the way L1's and L2's did, and
    this window's failure to do so is consistent with there being no real boundary here for
    the family-of-curves method to lock onto.
  - Both runs' step-5 summary lines list method A as "none" at every level in their printed
    table — this is expected, not a discrepancy: `LEVEL_ESTIMATES_A` is only populated when
    a step-4 candidate override is supplied (see script header), so with no overrides given
    on either pass it always records "none" there regardless of the diagnostic elbow
    estimate printed earlier in the log. The diagnostic estimate (64B/32B/16B per level,
    discussed above) is what should actually be cited pending a step-4 run, not that
    summary line.
  - **Updated recommended next step:** the L1 vs. L2/L3 reproducibility contrast makes L1's
    64B step-4 refinement the highest-value next run (already two-method-confirmed and now
    twice-reproduced — step 4's offset check is the last remaining box to check before
    calling it fully frozen); L2 at 64B remains worth a step-4 run too now that it's shown
    to be reproducible, just not yet on L1's footing; L3-onset is not worth a step-4 run
    until this machine has an actual confirmed LLC/DRAM boundary to test at instead of this
    ramp's onset.

- Run command + arguments (**2026-09-12, third pass — L3 only, alternate candidate boundary
  = the ~30 MiB transition-onset value from `CAPACITY_RESULTS.md`'s L3 row, i.e. the
  earlier/looser onset rather than the ~90 MiB confirmed-sequential-plateau onset used
  above**): `./scripts/run_line_size.sh artemisia 20 31457280` (31,457,280 B = exactly
  30 MiB; single-boundary invocation, L1/L2 not re-run). Core 20 re-verified idle beforehand
  (3-window `/proc/stat` sample: cpu20 busy 1.8/2.5/1.2%, sibling cpu76 busy 2.3/1.5/0.2%).
  Detached `tmux` session `artemisia_line_size_l3_30mib`. Timestamp `20260912T220658Z`;
  full transcript `data_raw/artemisia/line_size/run_line_size_20260912T220658Z.log`. Window
  = [3932160, 125829120] bytes (boundary/8 to boundary*4).
  - **Still no clean signal — same conclusion as the ~90 MiB onset, now confirmed at a
    second candidate boundary in the same broad transition.** Per-stride elbow footprints:
    `{8B: 88974624, 16B: 88974624, 32B: 79267360, 64B: 99870592, 128B: 88974592, 256B:
    112100864}` — non-monotonic in stride with no large-stride cluster (128B's elbow sits
    *below* 64B's and close to 8B/16B's, the opposite of the expected ordering). The
    auto-picker's "64B" answer is an artifact of 64B being the *only* stride whose elbow
    happened to fall within the 1.2x threshold of the 256B reference, not a real
    convergence — visually, in
    `data_processed/artemisia/line_size/level_31457280/plots/line_size_family_curve.png`,
    all six curves interleave and cross throughout the window, and at the right edge
    16B (highest) and 8B (second-highest) sit *above* every larger stride, essentially
    inverted from the line-size signature's prediction. Method B again found no transition
    (footprint=62,914,560B = 2x boundary). This is consistent with — and reinforces —
    Artemisia's own capacity finding that ~30 MiB is merely this ramp's transition onset,
    not a real plateau edge (`CAPACITY_RESULTS.md`'s Artemisia L3 row: "Transition onset
    (one continuous ramp)"); the family-of-curves method needs a genuine capacity plateau to
    anchor against, and neither of the two candidate boundaries tried in this broad
    ~48 KiB–90 MiB span (30 MiB here, 90 MiB above) provides one. **No further line-size
    attempts are worth making in this span** until/unless a real intermediate plateau is
    found in the capacity data (currently none is — see capacity/ section above); the next
    useful boundary to try would be a confirmed LLC/DRAM edge above ~90 MiB, once one
    exists.

- Run command + arguments (**2026-09-12, fourth pass — L1 + L3(30 MiB) only, L2 skipped**):
  `./scripts/run_line_size.sh artemisia 20 49152,31457280`. Core 20 re-verified idle
  beforehand (3-window `/proc/stat` sample: cpu20 busy 0.2/0.0/0.2%, sibling cpu76 busy
  0.7/0.3/0.7% — as quiet as any run this session). Detached `tmux` session
  `artemisia_line_size_l1_l3_rerun`. Timestamp `20260912T223233Z`; full transcript
  `data_raw/artemisia/line_size/run_line_size_20260912T223233Z.log`.
  - **L1: Method A reproduced exactly a third time** — identical elbow footprints
    `{8B: 110336, 16B: 110336, 32B: 87552, 64B: 55168, 128B: 55168, 256B: 55040}`, same 64B
    answer, three runs running. **Method B this time reported "none" — but this looks like
    detector fragility, not a real change**, and is worth flagging for anyone touching
    `detect_line_size.py` later: the re-generated
    `data_processed/artemisia/line_size/level_49152/plots/line_size_curve.png` shows the
    *same* clean rise-then-flat-saturation shape at ~stride 200B as the two prior runs that
    successfully auto-detected 64B (visually indistinguishable from them), so the input
    curve's own shape didn't meaningfully change — `find_saturation`'s `confirm`/
    `flat_tolerance` logic apparently sits right at an edge case that flips pass/fail
    between otherwise-near-identical runs. Since Method A independently reproduced 3/3 and
    Method B still agreed 2/3, this doesn't weaken the 64B conclusion, but it does mean
    "Method B says none" should not, on its own, be read as contradicting evidence without
    checking the actual curve plot first.
  - **L3(30 MiB): still no clean signal, still doesn't reproduce run-to-run — third
    independent confirmation that this boundary carries no real line-size-detectable
    edge.** Elbow footprints yet again different from both prior 30 MiB attempts:
    `{8B: 99870632, 16B: 70619200, 32B: 79267360, 64B: 79267328, 128B: 99870592, 256B:
    88974592}`. Auto-pick landed on 8B this time (vs. 64B on the prior 30 MiB pass) — a
    third distinct "winning" stride across three tries at nominally the same measurement,
    which is itself strong evidence the picker is just latching onto whichever stride's
    noise happens to land closest to the reference each time, not a real signal. Visually,
    `data_processed/artemisia/line_size/level_31457280/plots/line_size_family_curve.png`
    again shows all six curves interleaving with no clean large-stride cluster. Method B
    again found no transition. **Conclusion unchanged and now well-supported: this span
    (30-90 MiB) has no capacity plateau for the family-of-curves method to anchor on, and
    no further reruns here are likely to add new information** — see the recommended next
    step in the third-pass entry above (a confirmed boundary above ~90 MiB is needed
    instead).

- Run command + arguments (**2026-09-12, fifth pass — L3(30 MiB) only, 4th independent
  attempt at this boundary, user-requested rerun**): `./scripts/run_line_size.sh artemisia
  17 31457280`. **Core switched from 20 to 17** (logical CPUs 17/73) — core 20 was found
  mid-`updatedb`/`locate` cron-job bursts (0-50% busy across a 4-window sample, `ps`
  confirmed `locate` at ~29% on cpu20), the same transient-cron interference pattern
  documented on other machines in this project; core 17/73 sampled clean (<5% busy) across
  4 independent 5s windows and was used instead. Timestamp `20260912T225025Z`; full
  transcript `data_raw/artemisia/line_size/run_line_size_20260912T225025Z.log`.
  - **4th distinct non-reproducing elbow set, same conclusion.** `{8B: 88974624, 16B:
    79267376, 32B: 62914560, 64B: 79267328, 128B: 79267328, 256B: 99870464}` — auto-pick
    8B again (matching the 3rd pass's pick, but at different absolute byte values, so not a
    real repeat), Method B again "none". Plot again shows full interleaving with 16B/8B near
    the top at the right edge rather than clustering with the larger strides. Four
    independent attempts (3 on core 20, 1 on core 17 — ruling out a core-specific artifact
    too) now agree on one thing only: **no reproducible line-size signal exists at this
    boundary.** Treating this as settled; no further reruns planned here absent a new,
    confirmed capacity boundary to target instead.

- Run command + arguments (**2026-09-12, sixth pass — L3(30 MiB), 5th independent attempt,
  user-requested rerun**): `./scripts/run_line_size.sh artemisia 3 31457280`. Core switched
  again, to 3 (logical CPUs 3/59) — a 4-window `/proc/stat` sample found core 17 (used last
  pass) had since picked up a load spike (85.8% busy in the last window) and core 20 also
  showed intermittent load; core 3/59 sampled clean (≤3.2%/2.2%) across all 4 windows and
  was used instead — the third distinct physical core used across these 5 attempts.
  Timestamp `20260912T225820Z`; transcript
  `data_raw/artemisia/line_size/run_line_size_20260912T225820Z.log`.
  - **5th distinct, still-non-reproducing elbow set** — `{8B: 99870632, 16B: 88974624, 32B:
    44487296, 64B: 88974592, 128B: 99870592, 256B: 79267328}`, auto-pick 16B (a 4th
    different "winning" stride across 5 tries: 64B, 8B, 8B, 16B). Method B again "none".
    **This run's underlying data is also the noisiest of the five** — the family-curve plot
    shows spikes past 400 ticks/access (vs. ~250-290 ticks max on the prior four attempts),
    despite core 3/59 having sampled clean immediately beforehand — consistent with this
    machine's own documented session-level-noise phenomenon (capacity/ section's Anomaly 2:
    slow, multi-hour-scale background contention drift that a short point-in-time
    `/proc/stat` sample can miss entirely). Doesn't change the conclusion — a noisier run
    still shows no large-stride convergence, it's just noisier on top of already having no
    signal — but is worth flagging as a data-quality note if anyone revisits this run
    specifically. **Five attempts across three physical cores (20, 17, 3) now agree: no
    reproducible line-size signal at 30 MiB.** Continuing to treat this as settled.

- Run command + arguments (**2026-09-13, seventh pass — L3(30 MiB), 6th independent
  attempt, user-requested rerun**): `./scripts/run_line_size.sh artemisia 0 31457280`, core 0
  (logical CPUs 0/56, a 4th distinct physical core, sampled clean beforehand). Timestamp
  `20260913T134827Z`. **7th distinct elbow set, same null result:** `{8B: 99870632, 16B:
  70619200, 32B: 79267360, 64B: 99870592, 128B: 99870592, 256B: 88974592}`, auto-pick 8B,
  Method B "none".
- Run command + arguments (**2026-09-13, eighth pass — L3(30 MiB), 7th independent
  attempt, user-requested rerun**): `./scripts/run_line_size.sh artemisia 9 31457280`, core 9
  (logical CPUs 9/65, a 5th distinct physical core, sampled clean beforehand). Timestamp
  `20260913T135516Z`. **8th distinct elbow set, same null result:** `{8B: 99870632, 16B:
  88974624, 32B: 70619200, 64B: 99870592, 128B: 79267328, 256B: 99870464}`, auto-pick 8B,
  Method B "none". **Seven independent attempts now, across five physical cores (20, 17, 3,
  0, 9) and two session days: the null result at 30 MiB is thoroughly exhausted.** Recommend
  treating this as final; further reruns at this specific boundary are not expected to add
  information (see the "next useful boundary" note earlier in this section).

- Run command + arguments (**2026-09-13, ninth pass — L3(30 MiB), 8th independent
  attempt, user-requested rerun**): `./scripts/run_line_size.sh artemisia 1 31457280`, core 1
  (logical CPUs 1/57, a 6th distinct physical core, sampled clean beforehand). Timestamp
  `20260913T142742Z`. **9th distinct elbow set, same null result:** `{8B: 79267376, 16B:
  79267376, 32B: 79267360, 64B: 112100992, 128B: 99870592, 256B: 79267328}`, auto-pick 8B,
  Method B "none". Plot:
  `data_processed/artemisia/line_size/level_31457280/plots/line_size_family_curve.png`.

- Run command + arguments (**2026-09-13, tenth pass — first formal Method-A step-4 run
  for L1 and L2 (candidate=64B each), plus a 10th independent L3(30 MiB) family-of-curves
  attempt, all in one invocation**): `./scripts/run_line_size.sh artemisia 0
  49152,2097152,31457280 8,16,32,64,128,256 64,64,` (L3's override field left blank —
  steps 1-3 + Method B only there, no step 4, per the established no-signal finding). Core 0
  (logical CPUs 0/56), sampled clean beforehand. Timestamp `20260913T143931Z`; transcript
  `data_raw/artemisia/line_size/run_line_size_20260913T143931Z.log`.
  - **L1: step 4 confirms 64B cleanly — this is now the script's own formally "frozen"
    number, not just a diagnostic.** Steps 1-3 reproduced the by-now-familiar exact elbow
    set (`{8B: 110336, 16B: 110336, 32B: 87552, 64B: 55168, 128B: 55168, 256B: 55040}`).
    Step 4's bracket (40/48/56/64/72/80/88B) × 8 offsets (0-56B) plot —
    `data_processed/artemisia/line_size/level_49152/plots/line_size_offset_elbow.png` —
    shows a clean, symmetric V bottoming out at **exactly 64B for every one of the 8 tested
    offsets**, all landing on the same point with no visible spread. This is the offset-
    invariance signature step 4 exists to check, and it's about as clean as this method can
    produce. Method B reconfirmed 64B too. Step 5's formal summary (populated for the first
    time, since a candidate was supplied): `method A (family of curves) = 64B, method B
    (single curve) = 64B`. **L1 = 64B: two methods, offset-invariance-confirmed, multiply
    reproduced — as settled as anything in this dataset.**
  - **L2: step 4 also lands on 64B, but the offset-invariance picture is much messier than
    L1's — read the plot before citing this as equally solid.** Steps 1-3's elbow set
    this time was `{8B: 4707944, 16B: 4707936, 32B: 4194304, 64B: 3328960, 128B: 3328896,
    256B: 3328768}` — note 32B's own elbow (4,194,304) moved further from the 64-256B
    cluster than in prior runs (was 3,736,672, within the auto-picker's threshold before);
    this time the auto-picker correctly lands on **64B directly**, not 32B, for the first
    time across all L2 attempts this session. But
    `data_processed/artemisia/line_size/level_2097152/plots/line_size_offset_elbow.png`
    shows several offsets (0B, 16B, 32B, 48B) jumping straight back up toward the 2^22-byte
    ceiling for candidate strides *above* 64B (72/80/88B) instead of staying low the way
    L1's did — only some offsets (8B, 24B, 40B, 56B) stay flat past the candidate. This is
    a real asymmetry, not just noise-shaped: a genuine line-size elbow should stay saturated
    for every stride ≥ the true line size regardless of alignment, and about half the tested
    offsets don't. Method B still found no transition at this level. Step 5:
    `method A (family of curves) = 64B, method B (single curve) = noneB`. **Treat L2 = 64B
    as the best-supported candidate, not yet as solid as L1** — the offset-invariance check
    that was supposed to be the final confirmation step instead surfaced a real, unresolved
    alignment sensitivity above the candidate stride.
  - **L3(30 MiB): 10th independent attempt, same null result** (`{8B: 99870632, 16B:
    88974624, 32B: 56050496, 64B: 70619200, 128B: 88974592, 256B: 88974592}`, auto-pick 8B,
    Method B "none", no step 4 attempted). Plot:
    `data_processed/artemisia/line_size/level_31457280/plots/line_size_family_curve.png`.
    No change to the standing conclusion that this boundary carries no detectable signal.
  - **All plot paths from this run**, for reference:
    - L1: `data_processed/artemisia/line_size/level_49152/plots/line_size_family_curve.png`,
      `line_size_family_boxplots.png`, `line_size_offset_elbow.png`,
      `line_size_offset_boxplots.png`, `line_size_curve.png` (Method B), `line_size_boxplots.png`
    - L2: same filenames under `data_processed/artemisia/line_size/level_2097152/plots/`
    - L3: `data_processed/artemisia/line_size/level_31457280/plots/line_size_family_curve.png`,
      `line_size_family_boxplots.png`, `line_size_curve.png` (Method B), `line_size_boxplots.png`
      (no offset plots — step 4 not run at this level)

- Run command + arguments (**2026-09-13, eleventh pass — forced Method-A step 4 at L3(30
  MiB) with candidate=64B, user-requested, specifically to test whether forcing the same
  candidate that worked at L1/L2 produces L1's clean offset-invariance signature here
  too**): `./scripts/run_line_size.sh artemisia 0 31457280 8,16,32,64,128,256 64`. Core 0,
  sampled clean beforehand. Timestamp `20260913T145240Z`; transcript
  `data_raw/artemisia/line_size/run_line_size_20260913T145240Z.log`.
  - Steps 1-3 gave an 11th distinct elbow set (`{8B: 99870632, 16B: 79267376, 32B:
    79267360, 64B: 112100992, 128B: 99870592, 256B: 99870464}`, auto-pick 8B) — same
    pattern as every prior attempt.
  - **Step 4's result answers the question directly: no, forcing 64B here does NOT
    reproduce L1's signature — it produces the opposite.**
    `data_processed/artemisia/line_size/level_31457280/plots/line_size_offset_elbow.png`
    shows all 8 tested offsets scattered essentially at random across roughly a 4x
    footprint range (2^25.5-2^27B), with no V-shape, no convergence at or near the 64B
    candidate line, and no coherent relationship to stride at all — the complete opposite
    of L1's clean, symmetric, offset-invariant V. This is the clearest direct
    demonstration yet that there's no line-size signal at this boundary: even when handed
    the "right" answer as a forced candidate, the alignment-invariance check that's
    supposed to confirm it instead falsifies it.
  - **Important caveat for anyone reading this run's own printed step-5 summary line
    without checking the plot first**: the script's `LEVEL_ESTIMATES_A` array records
    whatever candidate was supplied as soon as step 4 runs, unconditionally — it does NOT
    check whether the offset plot actually confirmed alignment-invariance before writing
    it down. This run's own step 5 output literally says `method A (family of curves) =
    64B` and `every level/method that produced an estimate AGREES on 64B`, which reads as
    a confirmation but is actually just an echo of the forced input — the offset-elbow
    plot above is the real result, and it says the opposite. Worth fixing in
    `run_line_size.sh` if this script sees further use (record confirmed/unconfirmed
    separately), but not attempted here since Phase I data collection, not tooling work,
    was requested.
  - Method B again found no transition. **Conclusion unchanged and now further
    strengthened**: no line-size signal exists at 30 MiB, and this is no longer just an
    absence of a positive result (steps 1-3 not converging) — step 4 actively falsifies the
    64B candidate at this boundary specifically, which is the strongest form of evidence
    against it this method can produce.

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
`--experiment inclusion_policy` run 2026-09-13, first data collection for this
machine. Boundary values from `CAPACITY_RESULTS.md` only (L1 = 49,152 B,
L2 = 2,097,152 B, LLC = 31,457,280 B ≈ 30 MiB) per project-wide direction —
note L2's value is the same one this machine's own capacity/ and associativity/
sections above already flag as NOT a confirmed boundary (a waypoint inside a
single continuous ~48 KiB–90 MiB ramp); run anyway per that direction, caveats
below.

- Source file(s): `main_code/common/{main.c,inclusion_policy.c,inclusion_policy.h,pointer_chase.c,pointer_chase.h,random.c,random.h}`, `main_code/x86_64/timer_x86.h`, `main_code/common/timer.h`
- Build command: `make` (from repo root)
- Idle-core check: `who`/`ps -eLo pid,psr,pcpu,user,comm` immediately before the run
  found another student's (`hbsu`) own `cache_bench`-style process pinned to
  logical CPUs 32/33/37 (100% each — the same cross-course-project contention
  pattern already documented in this file's capacity/ Machine Identification
  notes), not overlapping core 4. A single `/proc/stat` snapshot had
  transiently shown core 4's SMT sibling (CPU 60) at 99% busy, but this
  machine's own established practice (see Machine Identification above) is to
  not trust one snapshot — a 3-window `/proc/stat` sample (6s windows) showed
  core 4/60 at a maximum of 14.4%/11.2% across the three windows, and a final
  5s check immediately before launch read 1.4%/2.2% with no competing
  benchmark process on either logical CPU. Ran on **core 4**, the same
  physical core used for this machine's hit_latency/miss_latency/associativity
  runs (cross-run comparability).
- Run command + arguments (`taskset -c 4`, timestamp `20260913T181516Z`, single
  invocation covering all three pairings):
  `./scripts/run_inclusion_policy_full.sh artemisia 4 L1_vs_L2:49152:2097152:L2_to_LLC,L2_vs_LLC:2097152:31457280:LLC_to_DRAM,L1_vs_LLC:49152:31457280:LLC_to_DRAM`
- `ASSUMED_LINE_SIZE_BYTES` left at the script's default (64), not overridden:
  this machine's own line_size/ section above confirms 64 B at L1 (two
  methods, three reproductions, step-4 offset-invariance-confirmed) and reads
  64 B as the best-supported (if less airtight) candidate at L2 too; no
  line-size signal exists at all at the ~30 MiB LLC candidate (line_size/
  section's extensive 11-attempt investigation), so 64 B — the only
  measured value anywhere on this machine — is the only defensible choice
  there as well, not a blind carry-over of Sunbird's confirmed value.
- Eviction/reload construction: identical method to Sunbird's (see
  `main_code/common/inclusion_policy.h`'s docstring and Sunbird's README for
  the full argument) — one eviction node per page (`--evict-stride-bytes
  4096`) at a fixed sub-page offset (`--evict-offset-bytes 2048`), target and
  control freshly page-aligned at offset 0. Per trial: untimed re-touch of
  target/control, untimed eviction walk, one timed dependent reload of each.
  200 single-shot trials per (pairing, pattern, run), base + 2 reproducibility
  repeats (seed 12345/12346/12347), both eviction-walk traversal patterns, 3
  untimed warm-up passes. A dedicated 500-trial calibration run
  (`--evict-bytes` = `--target-bytes`, nothing evicted) establishes each
  pairing's own fresh "survived" baseline; the "invalidated" baseline is read
  from this machine's own already-collected `miss_latency` summaries
  (`L2_to_LLC` for `L1_vs_L2`; `LLC_to_DRAM` for both LLC-scale pairings).
- **Same three load-bearing caveats as Sunbird's writeup, plus one specific to
  this machine (caveat 4):**
  1. Assumed line size (see `ASSUMED_LINE_SIZE_BYTES` note above) — 64 B is
     this machine's only measured value, at any confidence level, so it's used
     everywhere rather than an unverified constant, but L2's own 64 B reading
     is visually-supported/not-offset-invariance-clean per line_size/'s own
     wording, and LLC has no measurement backing it at all.
  2. DTLB pressure at large eviction scale. `L2_vs_LLC` and `L1_vs_LLC` scale
     to `31,457,280 * 4096/64 = 2,013,265,920` B (~1.875 GiB, 491,520 pages —
     identical footprint to Sunbird's same-scale pairings, since both machines
     share the same ~30 MiB LLC candidate). **`L1_vs_L2` is a bigger DTLB-risk
     outlier here than on Sunbird**: because this machine's L2 candidate
     (2,097,152 B) is 8x Sunbird's confirmed 262,144 B, the scaled eviction
     footprint is `2,097,152 * 4096/64 = 134,217,728` B (128 MiB, 32,768
     pages) — 8x Sunbird's L1_vs_L2 footprint (16 MiB/4,096 pages), pushing
     this pairing much closer to the DTLB-risk regime Sunbird's writeup
     reserved only for its LLC-scale pairings. See caveat 4 below for direct
     evidence this actually shows up in the data.
  3. Avoidance guarantee only holds for a target whose full index fits in one
     page. Using this machine's associativity best-guess of 12-way (see the
     Final Cache Table reasoning), L1's index+offset works out to exactly one
     page here too (49,152 B / (12-way × 64 B line) = 64 sets = 6 index bits,
     +6 offset bits = 12 bits = 4,096 B) — the same lucky fit Sunbird's L1 had,
     so both `L1_vs_L2` and `L1_vs_LLC` get the structural guarantee. L2
     (2,097,152 B) almost certainly does not fit in one page by the same
     argument Sunbird's writeup made, so `L2_vs_LLC` is the least
     structurally-trustworthy of the three here too, independent of the
     capacity-value caveat above.
  4. **New, machine-specific: `L1_vs_L2`'s CONTROL channel came back a clean
     100% survived-like, but its TARGET channel landed mostly in the
     ambiguous zone rather than cleanly on either reference line** (see
     Results below) — consistent with caveat 2's prediction that this
     pairing's oversized (for an L1_vs_L2 test) 32,768-page eviction walk is
     doing more than cleanly evicting past L2; some genuine partial signal
     may be present (the paired-comparison check, which is independent of the
     classification thresholds, reads target-slower-than-control 100% of the
     time), but it cannot be read as a clean inclusion/exclusion verdict the
     way Sunbird's smaller-footprint `L1_vs_L2` result could.

**Results, one per pairing (n=200 target/control trials each, base/random run
unless noted):**

- **L1_vs_L2** (survived-class 70.08 ticks, invalidated-class 381.00 ticks
  from `L2_to_LLC`; classification boundary 163.40 ticks): target median 160
  ticks (22.0% survived-like, 0.5% invalidated-like, **77.5% ambiguous**),
  control median 110 ticks (100.0% survived-like). Paired check (target
  slower than its own trial's control): 100.0%. **Verdict: UNCERTAIN** — per
  caveat 4 above, read this as a muddied result from an oversized eviction
  footprint rather than either a clean "survives L2 eviction" or "gets
  invalidated by it" finding: the target sits well below the invalidated
  reference (381) but also well above its own clean survived baseline (70)
  and above the fully-clean control (110), and the 100% paired-slower result
  shows *something* about the eviction walk is consistently affecting the
  target beyond what it does to the control — just not enough to cross either
  classification threshold. Needs a re-run with a corrected, non-inflated L2
  eviction footprint (i.e., once this machine has an actual confirmed L2
  capacity) before this pairing can support any inclusion/exclusion claim.
- **L2_vs_LLC** (survived-class 88.77 ticks, invalidated-class 582.00 ticks
  from `LLC_to_DRAM`; classification boundary 227.30 ticks): target median
  476 ticks (**100.0% invalidated-like, 0% survived-like, 0% ambiguous**),
  control median 234 ticks (0.5% survived-like, 92.0% ambiguous, 7.5%
  invalidated-like). Paired check: 100.0%. **Verdict: INCLUSIVE** — this is a
  far cleaner split than Sunbird's own L2_vs_LLC result (which came back
  85% ambiguous there). Read with caveat 3's structural caution in mind (an
  L2-sized target has no guaranteed avoidance of its own set during the
  eviction walk, so this could in principle reflect ordinary incidental L2
  eviction rather than a specific LLC inclusion policy) — but a 100%/0%/0%
  split is a much stronger directional signal than an ambiguous one
  regardless of that caveat, and the control channel's own small 7.5%
  invalidated-like fraction is itself a useful, separate, and roughly
  consistent (with `L1_vs_LLC`'s own control, see below) direct measurement
  of how much of this pairing's signal DTLB pressure alone could plausibly
  explain — small relative to the 100% seen on target.
- **L1_vs_LLC** (survived-class 70.22 ticks, invalidated-class 582.00 ticks
  from `LLC_to_DRAM`; classification boundary 202.15 ticks): target median
  523 ticks (**100.0% invalidated-like, 0% survived-like, 0% ambiguous**),
  control median 208 ticks (0% survived-like, 88.5% ambiguous, 11.5%
  invalidated-like). Paired check: 98.0%. **Verdict: INCLUSIVE** — as clean a
  split as `L2_vs_LLC`'s, and this pairing gets the full benefit of caveat
  3's structural guarantee (L1's index does fit in one page here, see caveat
  3 above), so it's the more structurally trustworthy of the two
  LLC-involving pairings, mirroring which of Sunbird's two LLC pairings was
  more trustworthy there. Control's invalidated-like fraction (11.5%) is
  somewhat higher than `L2_vs_LLC`'s own control (7.5%) despite an identical
  1.875 GiB eviction footprint — plausibly just run-to-run noise (see the
  repeat-spread note below) rather than a systematic difference, since both
  pairings share the exact same eviction construction at this scale.
- **Repeat spread flagged by `plot_inclusion_policy.py` on both LLC-scale
  pairings' TARGET channel, not seen on `L1_vs_L2` or on either pairing's
  CONTROL channel at the same magnitude:** `L2_vs_LLC` target/random medians
  476/394/282 (50.5% spread), target/sequential 458/356/277 (49.8% spread);
  `L1_vs_LLC` target/random 523/502/292 (52.6% spread), target/sequential
  442/292/290 (44.5% spread) — `L1_vs_LLC` control also showed elevated
  spread (random 59.7%, sequential 20.4%). All three repeats' target medians
  stayed decisively above the classification boundary in every case (no
  repeat's median crossed back toward survived), so this spread doesn't
  change either LLC-scale verdict, but it's consistent with this project's
  established shared-machine-noise/session-level-drift signature already
  documented elsewhere in this file (Anomaly 2, the hit_latency LLC anomaly,
  3 of 6 flagged miss_latency combinations) rather than a new phenomenon —
  not traced to a specific interfering process for this run specifically.
- Raw output: `data_raw/artemisia/inclusion_policy/<pairing>/inclusion_policy_{calibration,base,rep1,rep2}_{random,sequential}_20260913T181516Z.csv.gz`;
  full transcript `data_raw/artemisia/inclusion_policy/run_inclusion_policy_full_20260913T181516Z.log`.
- Processing: `scripts/summarize_raw.py` → `data_processed/artemisia/inclusion_policy/<pairing>/*_summary_20260913T181516Z.csv` → `scripts/classify_inclusion_policy.py` → `scripts/plot_inclusion_policy.py` → `data_processed/artemisia/inclusion_policy/<pairing>/plots/inclusion_policy_boxplots.{png,pdf}`.

**Best-guess synthesis:** the two LLC-involving pairings both come back
decisively (100% invalidated-like on target, near-clean on control) —
noticeably cleaner evidence than Sunbird's own LLC pairings produced, and in
the same direction (inclusive). `L1_vs_L2` cannot support a verdict on this
run, most likely because its scaled eviction footprint inherited this
machine's oversized/unconfirmed L2 capacity candidate rather than reflecting
a genuinely ambiguous L1-L2 relationship. **Best-guess overall reading:**
this machine's LLC is confidently read as inclusive of both L1 and (with the
caveat-3 structural caveat) L2's resident lines — consistent with an
inclusive, cross-core snoop-filter-style LLC design, the same story Sunbird's
data pointed toward but reached with much higher confidence here on the
LLC-involving pairings specifically. L2's own relationship to L1 remains
genuinely open on this machine and would need a re-run at a corrected L2
eviction footprint (once a real L2 capacity is established) to resolve.

### pmu/ (Phase II — 2026-09-14)
Phase I frozen/tagged (`phase1-timing-only`) before anything below was run,
per `README.md`'s Phase Discipline. Ran via the now-canonical
`scripts/run_pmu_verification.sh` pipeline (the same one Sunbird/Thunderbird
established and standardized on — see `CLAUDE.md`'s "Phase II" subsection),
no script changes. See `data_processed/artemisia/PHASE2_VALIDATION_TABLE.md`
for the full methodology/results write-up and literature citations — this
section is the raw-data/reproduction-detail record.

- Source file(s): `scripts/run_pmu_verification.sh`, `scripts/summarize_pmu.py`
  (both pre-existing, from Sunbird's session — no changes needed here).
- Machine-specific PMU check done before running (this machine had never been
  checked before): `/proc/sys/kernel/nmi_watchdog` = 0 (unlike Sunbird/
  Thunderbird's 1 — no counter reserved for the watchdog here) and
  `perf_event_paranoid` = 1 (no root needed). A direct test of the FULL
  8-event combined group (`duration_time,cache-references,cache-misses,
  L1-dcache-loads,L1-dcache-load-misses,LLC-loads,LLC-load-misses,cycles,
  instructions`) scheduled every event at **100%** in one single `perf stat`
  invocation — unlike Sunbird/Thunderbird, which could only reliably schedule
  2 hardware events at once and needed 4 separate invocations. This machine
  (2x Xeon Gold 5420+, Sapphire Rapids/Golden Cove) evidently has enough
  general-purpose PMU counters (or little enough other contention for them)
  to not need the split. **Kept the script's existing 4-separate-group
  design anyway, deliberately, for cross-machine consistency with Sunbird's
  and Thunderbird's already-collected data** (same command structure, same
  files-per-group layout) rather than special-casing this machine — a real,
  documented finding, not a limitation to route around.
- Core selection: this is a heavily shared, multi-user class machine (not
  just this team) — `who` showed 8 other students' sessions active, `ps`
  showed several other unrelated CPU-bound jobs (a `champsim` simulation
  campaign, a multi-process CLIP/CIFAR-100 inference job pinned to cores
  28-55 on the *other* NUMA node/socket, and — notably — another student's
  own `incl_pmu` benchmark, at ~200% CPU, pinned to CPU 0, same NUMA
  node/socket/LLC domain as this run's core). Picked core 1 (logical CPUs
  1 and 57, its SMT sibling) after two 3-second-apart `/proc/stat` idle-delta
  samples showed both essentially fully idle (98-100%) while CPU 0/2/4 on the
  same socket were not. **CPU 0's concurrent `incl_pmu` job shares this run's
  LLC domain (`shared_cpu_list=0-27,56-83`, confirmed via sysfs below) even
  though it doesn't share a physical core with CPU 1** — flagged as a
  plausible real contention source for the LLC-footprint numbers below, not
  fully ruled out.
- Run command: `./scripts/run_pmu_verification.sh artemisia 1
  L1:49152,L2:2097152,LLC:31457280` (all three footprints taken directly from
  `CAPACITY_RESULTS.md`, per that file's standing authority over this file's
  own capacity prose — note the L2 value is the same one this machine's own
  `capacity/` section already flags as NOT a confirmed boundary, used anyway
  per project-wide direction, same as every other experiment type on this
  machine). base_seed=12345 (repeats use base_seed+index), samples=
  1,000,000/run, batch_size=1000, warmup_passes=3, dependent load mode,
  random pattern, timestamp `20260914T003056Z`. Total wall time: well under a
  minute per invocation even at the LLC footprint — much faster than
  Sunbird's own LLC-footprint runs, consistent with this machine's smaller
  absolute footprint relative to its (larger, as it turns out — see below)
  real LLC capacity.
- Raw output: `data_raw/artemisia/pmu/{L1,L2,LLC}/*_perfstat_*.csv.gz` (perf
  stat's own `-x,` CSV output, one file per group×run_tag, gzipped by hand
  per `.gitignore`'s `data_raw/**/*.csv` convention) and `*_bench_*.csv.gz`
  (cache_bench's own CSV from the same invocation). Transcript:
  `data_raw/artemisia/pmu/run_pmu_verification_20260914T003056Z.log`.
- Processed: `data_processed/artemisia/pmu/{L1,L2,LLC}/
  pmu_summary_20260914T003056Z.csv` (one row per run_tag + a median-of-3
  row).
- System-reported cache info (also Phase II, same session):
  `data_raw/artemisia/pmu/system_reported_cache_info.txt` — `lscpu --caches`,
  full `lscpu`, and per-instance `/sys/devices/system/cpu/{cpu0,cpu1}/cache/
  index*/` fields (cpu0 included for a sanity cross-check against cpu1, our
  actual test core — both agree), collected 2026-09-14T00:31:34Z.
- **Headline results** (full detail, caveats, and literature citations:
  `data_processed/artemisia/PHASE2_VALIDATION_TABLE.md`):
  - **L1D and L2: a striking confirmation of Phase I's own low-confidence
    associativity best guesses.** Phase I's L1 associativity (12-way) and L2
    associativity (16-way) were both explicitly flagged in
    `FINAL_CACHE_TABLE.md` as confound-blocked, low-confidence estimates —
    system-reported associativity (`lscpu --caches` / sysfs) is **12-way at
    L1D and 16-way at L2, an EXACT match to both**. Size/sets/line/sharing
    also match exactly at both levels across Phase I, system-report, and
    Intel's own published spec (Intel ARK product page for this exact SKU,
    Xeon Gold 5420+: 48 KB L1D / 2048 KB L2 per core — see the validation
    table for the full citation).
  - **LLC: a real, informative SIZE disagreement, not just an associativity
    one.** Phase I's `CAPACITY_RESULTS.md` value (~30 MiB, 31,457,280 B) was
    always presented as a representative footprint, not a confirmed
    boundary — this machine's own `capacity/` section explicitly found no
    discrete L2/L3 plateau, only one continuous ramp from ~48 KiB to
    ~90 MiB. System-report AND Intel ARK's own spec sheet independently
    agree the real per-socket L3 is **52.5 MiB (55,050,240 B, exactly
    57,344 sets × 15 ways × 64 B)** — 1.75x Phase I's representative value.
    This resolves the open question from the capacity writeup: the ~90 MiB
    plateau-onset Phase I did observe is much more consistent with a real
    ~52.5 MiB LLC (accounting for the extra headroom a random-probe pattern
    typically needs past nominal capacity to reliably evict everything) than
    with a ~30 MiB one. LLC associativity: system-reported **15-way** —
    neither of Phase I's two candidate guesses (16-way point estimate, 8-way
    "equally plausible alternative") is exact, but 16 is far closer than 8,
    a partial validation of the structural reasoning that produced it.
  - **LLC-footprint PMU numbers from this run look contention-inflated, most
    likely by the concurrent same-socket `incl_pmu` job noted above.** This
    run's own `cache_bench` bench-median latency at the LLC footprint
    (237.7 ticks) is ~2.5x Phase I's original latency-experiment number at
    the same exact footprint (94.4 ticks, collected 2026-09-13 on core 4, a
    presumably quieter session) — L1's and L2's own bench medians from this
    run (5.7 and 27.6 ticks) are much closer to their own original Phase I
    numbers (9.9 and 28.1), so this isn't a uniform re-run difference, it's
    LLC-specific. The PMU miss-rate signal is consistent with real,
    unusually heavy eviction: `cache_miss_rate` jumps from ~0.13-0.16% at
    the L1/L2 footprints to **~54%** at the LLC footprint — a much larger
    jump than Sunbird's equivalent (~0.1-1.4% to ~11-14%), even though this
    31 MiB probe is only ~60% of this machine's real 52.5 MiB LLC (i.e., in
    isolation it should mostly still fit). Read as a real, honestly-flagged
    shared-machine confound on top of a genuine LLC-crossing signal, not a
    measurement bug — consistent with this project's established pattern of
    documenting rather than hiding session-level contention (see Charnwood's,
    Ookay's, and this same machine's own P-state/contention writeups
    elsewhere in this file). Not re-run at a quieter time this session.
  - This machine's PMU reliably schedules **8** hardware events in one group
    at 100% (see the machine-specific check above) — worth re-checking, not
    assuming, on any future machine, same as Sunbird/Thunderbird's own
    2-event ceiling was.

### eight_counters/ (Problem 8.4, item 1 — 2026-09-14)
Ran `scripts/run_standardized_benchmarks.sh` (built by Sunbird's session,
already reused by Thunderbird and Skylark) — the 3 standardized
cross-machine microbenchmarks (`L1_resident`, `LLC_random`, `beyond_LLC`)
each wrapped in `perf stat` to collect this pipeline's fixed 8-event set
(`cache-references`, `cache-misses`, `L1-dcache-loads`,
`L1-dcache-load-misses`, `L1-dcache-stores`, `LLC-loads`, `LLC-load-misses`,
`dTLB-load-misses`) — distinct from `pmu/`'s own 8-event set (§8.3), which
swaps the store/TLB pair for `cycles`/`instructions`.

- `perf list` check (item 1's first requirement): all 8 event names are
  listed on this machine's PMU as genuine `[Hardware event]`/`cpu/.../`
  entries (`cache-references`, `cache-misses`, `L1-dcache-loads`,
  `L1-dcache-load-misses`, `L1-dcache-stores`, `LLC-loads`,
  `LLC-load-misses`, `dTLB-load-misses`) — unlike Skylark (only 5 of 8
  listed) or Thunderbird (`L1-dcache-stores` and both `LLC-*` events absent
  from its ARM PMU's listing), this machine needed no substitutions.
- Run command: `./scripts/run_standardized_benchmarks.sh artemisia 7
  L1_resident:49152,LLC_random:31457280,beyond_LLC:536870912` — the first
  two footprints are this machine's own `FINAL_CACHE_TABLE.md` L1/LLC
  representative values (same ones used for `pmu/`'s §8.3 run), kept
  as-is for cross-machine naming consistency even though §8.3's own results
  since showed the real LLC is ~52.5 MiB, not ~30 MiB — `beyond_LLC` uses
  the project's universal 536,870,912 B (512 MiB) constant. Core 7 (logical
  CPUs 7 and 63, its SMT sibling) chosen after 3-4 `/proc/stat` idle-delta
  samples ~3s apart showed it consistently ≥96% idle across every window,
  unlike cores 0/2/4 (another student's `incl_pmu` benchmark bouncing
  between CPUs 0/2, and a `champsim` simulation pinned to CPU 4, both still
  active from the earlier `pmu/` session) — `ps` confirmed no user process
  scheduled on CPU 7 or 63 at all, only kernel threads and idle
  editor/language-server processes at 0.0% CPU. base_seed=12345 (repeats
  use base_seed+index), samples=1,000,000/run, timestamp
  `20260914T053053Z`. `L1_resident` and `LLC_random` each completed in
  seconds; `beyond_LLC` (512 MiB, 3 warmup passes, random pattern) took
  the bulk of the wall time, consistent with this project's documented
  "long dense sweep" cost pattern — run in the background rather than
  polled synchronously.
- Raw output: `data_raw/artemisia/eight_counters/{L1_resident,LLC_random,
  beyond_LLC}/*_perfstat_*.csv.gz` and `*_bench_*.csv.gz`, gzipped by hand.
  Transcript: `data_raw/artemisia/eight_counters/
  run_standardized_benchmarks_20260914T053053Z.log`.
- Processed: `data_processed/artemisia/eight_counters/{L1_resident,
  LLC_random,beyond_LLC}/eight_counters_summary_20260914T053053Z.csv` (one
  row per run_tag + a median-of-3 row).
- **Results**: all 8 counters collected cleanly at all 3 benchmarks, no
  `<not counted>`/`<not supported>` events on this machine.
  - `L1_resident` (49,152 B): bench median 6.2 ticks/access — close to this
    machine's own already-documented L1 hit latency (~9.87 ticks from
    `latency/`, ~5.7-10.4 from the earlier `pmu/` run; all three sessions
    disagree with each other by roughly a factor of ~1.5-1.7x, an
    unresolved session-to-session noise pattern already flagged in the
    `pmu/` section above, not a new finding). `dtlb_load_misses` small and
    sane (~1.7K).
  - `LLC_random` (31,457,280 B, ~60% of this machine's real ~52.5 MiB LLC
    per §8.3): bench median 194.7 ticks/access — a THIRD different value
    for this exact footprint across this machine's 3 sessions so far
    (Phase I's original quiet-session number ≈94.4, the `pmu/` section's
    contention-affected re-run ≈237.7, now this run's 194.7). **Identified
    a concrete, session-specific cause this time, not just a generic
    "contention" attribution**: `ps` at the time of this run showed
    another student's `cache_bench_x86 --exp nextlevel --cpu 4
    --evict_kb 220000` process actively running on CPU 4 (a 220 MB
    eviction-buffer benchmark, i.e. itself deliberately LLC/
    memory-bandwidth-heavy) alongside the same `incl_pmu` process on CPUs
    0/2 already flagged in the `pmu/` section — both on this run's own
    socket/LLC domain (CPUs 0-27,56-83), even though core 7 itself stayed
    idle throughout. `dtlb_load_misses` climbs to ~11.1M (vs.
    `L1_resident`'s ~1.7K), as expected for a footprint spanning many more
    pages. `cache_miss_rate` climbs to ~35-40% and `llc_miss_rate` to
    ~30-34%, both a clear order-of-magnitude jump from `L1_resident`'s
    ~0.14-0.23%/~0.06-0.10% — the capacity-crossing signal itself is
    intact regardless of the contention-driven magnitude noise.
  - `beyond_LLC` (536,870,912 B): bench median 304.3-304.9 ticks/access
    across all 3 runs — **the tightest agreement of any benchmark this
    session** (≤0.5 tick spread) and an almost exact match to this
    machine's own already-documented ≈305.58-tick DRAM latency from
    `FINAL_CACHE_TABLE.md`. Unlike `LLC_random`, this benchmark shows no
    contention-driven anomaly, plausibly because every access here already
    has to reach DRAM regardless of LLC occupancy pressure from other
    processes, so shared-LLC contention has much less room to change the
    outcome (the same reasoning Skylark's own `beyond_LLC` run — also
    anomaly-free despite confirmed contention — was read against). `cache_
    miss_rate`/`llc_miss_rate` both climb further still (~80%/~77%), and
    `dtlb_load_misses` reaches ~251M, consistent with a working set far
    larger than DTLB reach. `l1_dcache_stores` also climbs by roughly
    1000x from `L1_resident` to `beyond_LLC` — almost certainly a
    whole-process-lifetime dilution artifact (the untimed warmup passes
    over a much larger buffer execute far more store instructions before
    the timed region even starts), the same caveat already documented for
    `cycles`/`instructions` in the `pmu/` section's PMU-overhead caveats,
    not a new finding specific to this counter.
- Items 2-4 of Problem 8.4 (normalization, ranked S-curves, Intel/AMD/Arm +
  generation comparison) are cross-machine analyses that need all 8
  machines' `eight_counters/` data first — not attempted here, per
  `CLAUDE.md`'s own tracking of this problem.

### software_hit_rate/ (Problem 8.5 — 2026-09-14)
Software-only, timing-derived cache hit-rate estimator
(`main_code/software_hit_rate/`, no PMU access anywhere in that file) plus
its Phase-II PMU validation, same pipeline and redesigned harness used on
Sunbird/Thunderbird/Skylark — see `data_raw/sunbird/README.md`'s
`software_hit_rate/` section for the original design, the invalid first
attempt, and the 2026-09-14 redesign that fixed it (none of that history is
re-derived here). See `main_code/software_hit_rate/software_hit_rate.h`'s
module doc comment for the full method (calibration -> ROC threshold
selection -> Rogan-Gladen prevalence correction -> bootstrap CI). Footprint
values come from `CAPACITY_RESULTS.md` (L1=49,152 B, L2=2,097,152 B,
LLC≈30 MiB=31,457,280 B, DRAM=536,870,912 B), per this project's
`CAPACITY_RESULTS.md`-is-authoritative rule. Core 4 (same core as this
machine's `hit_latency`/`miss_latency`/`associativity` runs), confirmed
idle via two `/proc/stat` idle-time-delta samples ~2s apart immediately
before each run (per this machine's own established practice of not
trusting a single `ps` snapshot).

#### Sweep (parts 1-3, standalone, no perf)
- Source file(s): `main_code/software_hit_rate/software_hit_rate.{c,h}`,
  `scripts/run_software_hit_rate_sweep.sh`,
  `scripts/summarize_software_hit_rate.py`, `scripts/plot_software_hit_rate.py`.
- Run command: `./scripts/run_software_hit_rate_sweep.sh artemisia 4
  4096,16384,32768,49152,65536,131072,262144,1048576,2097152,4194304,8388608,16777216,31457280,67108864,134217728,268435456,536870912
  "L1:49152,L2:2097152,LLC:31457280,DRAM:536870912"` — the script's own
  default sweep list with this machine's own L1 (49,152 B) and L2
  (2,097,152 B) boundaries inserted (the unmodified default only contains
  Sunbird's L1/L2 values, 32,768/262,144 B, not Artemisia's — same
  explicit-only discipline the Skylark run already established), and the
  boundary_spec passed explicitly (the script previously hardcoded
  Sunbird's boundaries for its plot reference lines until Skylark's session
  fixed it — see that machine's writeup). core=4, seed=12345,
  calib_samples=20000, test_samples=50000, bootstrap_reps=2000,
  pattern=random, timestamp `20260914T122226Z`.
- Raw output: `data_raw/artemisia/software_hit_rate/raw/hit_rate_<bytes>_20260914T122226Z.csv.gz`
  (full per-access CSV per footprint). Transcript:
  `data_raw/artemisia/software_hit_rate/run_software_hit_rate_sweep_20260914T122226Z.log`.
- Processed: `data_raw/artemisia/software_hit_rate/hit_rate_sweep_20260914T122226Z.csv.gz`
  (gzipped by hand after generation, matching Skylark's convention);
  plots: `data_processed/artemisia/software_hit_rate/plots/{hit_rate_sweep,calibration_distributions}.{png,pdf}`.
- **Headline results**: Hhat=1.0000 clear through 262,144 B — **no dip at
  this machine's own exact L1 boundary (49,152 B)**, unlike Sunbird's
  0.8664 dip at its own L1 edge, matching Skylark's (also no-dip) pattern
  rather than Sunbird's. Falls off starting at 1,048,576 B, and this
  transition is genuinely noisy, not a clean monotonic ramp:
  1,048,576 B -> Hhat=0.7221 but with a wide bootstrap CI (0.4046-0.7264,
  bootstrap_std=0.1575 — an order of magnitude higher than every other
  point's bootstrap_std, all of which are ≤0.07), then 2,097,152 B (this
  machine's own L2 boundary) -> 0.1944 (tight CI again), then a steady
  monotonic decline through 4,194,304 B (0.0642, itself still fairly wide:
  CI 0.0623-0.2423) down to 536,870,912 B (0.0001). This 1-4 MiB
  wide-uncertainty region lines up with this machine's own already-
  documented (`capacity/` section) unresolved ~48 KiB-90 MiB continuous
  ramp with no confirmed L2/L3 shelf — plausibly the same underlying
  cause, not investigated further here.

#### PMU validation (part 4)
- Source file(s): `scripts/run_hit_rate_pmu_validation.sh`,
  `scripts/compare_hit_rate_pmu.py` (unmodified from Sunbird's/Thunderbird's/
  Skylark's runs — this machine used the already-fixed, second-design
  version throughout, never the original broken one).
- Run command: `./scripts/run_hit_rate_pmu_validation.sh artemisia 4
  L1:49152,L2:2097152,LLC:31457280,DRAM:536870912`. Tested footprints after
  the L1/L2/LLC halving (DRAM left as given): L1=24,576, L2=1,048,576,
  LLC=15,728,640, DRAM=536,870,912. base_seed=12345 (repeats use
  base_seed+index), timestamp `20260914T123624Z`.
- Raw output: `data_raw/artemisia/software_hit_rate/pmu/{L1,L2,LLC,DRAM}/
  *_{calibonly,bench,hitlatpmu,perfstat}_{base,rep1,rep2}_20260914T123624Z.csv.gz`
  (gzipped by hand after the run, same as Sunbird/Skylark — this script does
  not compress its own output). Transcript:
  `data_raw/artemisia/software_hit_rate/pmu/run_hit_rate_pmu_validation_20260914T123624Z.log`.
- Processed: `data_processed/artemisia/software_hit_rate/pmu_validation_20260914T123624Z.csv`.
- **Headline results (median of base+2 repeats)**:

  | Level | Tested footprint | Hhat | H_pmu | rel. error |
  |---|---|---|---|---|
  | L1  | 24,576 B     | 1.0000 | 0.7827 | 27.8% |
  | L2  | 1,048,576 B  | 0.7163 | 0.6018 | 20.4% |
  | LLC | 15,728,640 B | 0.0060 | 0.9029 | 99.3% |
  | DRAM | 536,870,912 B | 0.0001 | 0.2328 | 100.0% |

  L1 and L2 are both sane and citable (same "L1/L2 roughly agree, LLC/DRAM
  diverge hugely" pattern as every other machine tested so far). **LLC and
  DRAM's large disagreement is EXPECTED, not a bug** — the estimator's own
  documented single-threshold limitation (tau ~86-90 ticks here sits well
  below a genuine LLC/DRAM hit's true single-shot latency), reproduced on
  a 5th machine now (after Sunbird, Thunderbird, Skylark, and this being
  the 4th x86 one).
- **New, Artemisia-specific finding: L2's repeats disagree with each other
  more than any other machine's L2 result so far** (base=0.7163,
  rep1=0.4119, rep2=0.7177 — rep1 is a real outlier, not within noise of
  the other two). This corroborates the sweep's own finding above that the
  1,048,576 B footprint sits in a genuinely wide-uncertainty region on this
  machine (that sweep point's own bootstrap CI was 0.40-0.73, wide enough
  to span both rep1's and base/rep2's PMU-validation values) — a real
  order-sensitivity/reproducibility issue at this specific footprint on
  this machine, not a PMU-harness artifact. Do not treat "L2 rel_error =
  20.4%" as a tight, fully resolved number the way Skylark's 0.78% L2
  result was; the median across 3 runs is being pulled by an outlier.
- **DRAM's H_pmu=0.2328 (not near 0, as `Hhat`'s definition would predict)
  is corroborated, not contradicted, by this machine's own already-
  collected `eight_counters/beyond_LLC` result above**: that run's generic
  `cache_miss_rate`/`llc_miss_rate` at 536,870,912 B were ~80%/~77%, i.e.
  a generic-counter-derived "hit rate" of roughly 0.20-0.23 — close to this
  H_pmu, an internal cross-check rather than the Thunderbird-style
  generic-counter-unreliable-at-DRAM-scale finding (that machine's own
  `cache-references`/`cache-misses` alias tracked something much closer to
  L1-scope traffic; this machine's does not show the same symptom).

## Final Inferred Cache Table (Artemisia, Phase I best guess, 2026-09-13)

Lives at `data_processed/artemisia/FINAL_CACHE_TABLE.md`, alongside this
machine's other processed benchmark outputs (same convention Sunbird's
writeup established), next to `capacity/`, `line_size/`, `associativity/`,
`latency/`, `inclusion_policy/`. The full per-pairing reasoning and caveats
behind it live here, in this file's `associativity/` and `inclusion_policy/`
sections above (the latter's "Best-guess synthesis" subsection) and the
`capacity/`, `line_size/`, and `latency/` sections before that — the
processed-directory copy is the consolidated table only, not a replacement
for that narrative.

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
