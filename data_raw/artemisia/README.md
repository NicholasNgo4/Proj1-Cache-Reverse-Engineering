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
