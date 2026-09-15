# hazel_cascadelake — Reproduction Manifest

> Fill in every field before freezing results. This README must let a grader go from
> this folder to the exact command that generated the data without guessing.

## Machine Identification
- Hostname: `c020n01` (allocated by Slurm for `--constraint=cascadelake`, job 833553)
- CPU model (from `lscpu`/`/proc/cpuinfo`): `Intel(R) Xeon(R) Gold 6226R CPU @ 2.90GHz` -- matches NC State's documented
  `cascadelake` constraint mapping (see PREDICTION_FREEZE.md/assignment Table 4).
- ISA / architecture: x86-64 (`uname -a`: `x86_64 x86_64 x86_64 GNU/Linux`)
- Vendor / microarchitecture / codename (researched, NOT from cache tables): Intel Cascade Lake-SP Refresh (2nd Gen Xeon Scalable)
- Introduction year (per the team's stated year convention): 2020
- Process node (if reliably documented): 14 nm
- Kernel version: `5.14.0-611.5.1.el9_7.x86_64`
- Page size: 4096 bytes (standard x86-64)
- SMT siblings idle during runs? This access-check job requested 1 CPU
  (`--cpus-per-task=1`); Slurm bound it to logical CPU 29 (socket 1, NUMA
  node 1) via `--cpu-bind=cores`. Sibling-thread idleness not independently checked this
  pass (no full-suite timing run yet to require it).

## Environment
- Compiler + version: `gcc (GCC) 11.5.0 20240719 (Red Hat 11.5.0-11)` (confirmed via the
  job's own `gcc --version` on the allocated compute node, not just the login node)
- Compiler flags: `-O0 -g -std=c11 -Wall -Wextra -fno-omit-frame-pointer`
- Timer method used (RDTSC/RDTSCP+LFENCE, CNTVCT_EL0, etc.): RDTSC-family (x86-64), same
  `main_code/x86_64/timer_x86.h` used on every x86 lab machine -- not yet independently
  sanity-checked on this specific node (pending the full-suite pass).
- Affinity/binding command used: `srun --cpu-bind=cores` (NOT `taskset` -- that is the lab
  machines' pinning method only; see `scripts/run_capacity_sweep.sh`'s header comment).
  Resulting binding: `physcpubind: 29`, socket 1, NUMA node 1
  (via `numactl -s`).
- NUMA/locality method: `numactl -s` plus `lscpu -e=CPU,CORE,SOCKET,NODE` (both on the Phase
  Discipline whitelist) -- logical CPU 29 is socket 1, NUMA node 1 on this node.
- Git commit hash of the code used for these results: `cb7e0c8c82c0269507e665db04563dee78fda9a6` (the `predictions-frozen`
  tag's own commit is an ancestor of this HEAD -- confirmed by this job's own gate check
  before running anything past the smoke test)

**Job record (this pass -- access/build check only, not the full suite):** Slurm job ID
833553, elapsed 8s, exit code 0. Full stdout/stderr: `hw1_cascadelake_833553.log` /
`hw1_cascadelake_833553.err.log` (committed alongside this README; `.log` suffix used instead of
Slurm's default `.out` because this repo's `.gitignore` blanket-ignores `*.out`). The job built
`cache_bench` cleanly (in an isolated per-job directory, `hazel_build/833553/`, to avoid
races with sibling generations' jobs building concurrently in this same shared GPFS checkout --
see `hpc_slurm/hw1_cascadelake.sh`'s header) and ran one tiny (`--samples 1000`, 4096-65536 B)
`--experiment capacity` smoke test under `srun --cpu-bind=cores` to confirm the binary runs
correctly bound to a real core on Hazel -- this is NOT the 1,000,000-sample suite required for
the actual capacity/line_size/associativity/latency/inclusion_policy experiments, which are run
by a separate `hw1_cascadelake_<experiment>.sh` job script per experiment type (see
`hpc_slurm/README.md`).

## Per-Experiment Reproduction

### capacity/
- Slurm job ID: 837631, hostname `c022n01`, logical CPU 20, socket 1, elapsed 30m19s, exit 0.
- Source file(s): `main_code/common/{main.c,benchmark.c,pointer_chase.c,random.c,capacity.c}`,
  `scripts/run_capacity_full.sh` (`HAZEL_MODE=1`), `scripts/summarize_raw.py`,
  `scripts/detect_cache_hierarchy.py`, `scripts/plot_capacity.py`
- Build command: `make -s` (isolated per-job copy under `hazel_build/837631/`, cleaned up on
  job exit)
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_capacity_full.sh hazel_cascadelake 20`
  (coarse_max defaulted to 67,108,864 B / 64 MiB, then a 4x tail extension to 256 MiB)
- Sample count: 1,000,000 (timed; warm-up excluded) -- every stage
- Random seed(s): base 12345; reproducibility repeats on the deepest boundary use the same
  seed (this script's own known limitation, unchanged from the lab-machine version)
- Raw output filename(s):
  `data_raw/hazel_cascadelake/capacity/capacity_{coarse,coarse_ext,dense0..dense4,dense4_rep1,
  dense4_rep2,denseTail}_{random,sequential}_20260915T010343Z.csv.gz`; full transcript:
  `data_raw/hazel_cascadelake/capacity/run_capacity_full_20260915T010343Z.log`
- Processing script -> data_processed path: `scripts/summarize_raw.py` ->
  `data_processed/hazel_cascadelake/capacity/*_summary.csv`;
  `scripts/detect_cache_hierarchy.py` (default thresholds) -> 5 candidate boundaries (see
  Findings); `scripts/plot_capacity.py` ->
  `data_processed/hazel_cascadelake/capacity/plots/capacity_{curve,boxplots}.{png,pdf}`
- Excluded runs (if any) and reason: none -- single complete run. The ~2-10 MiB region shows
  very large overlapping-summary spread at many points (up to 150%+, e.g. 2.82842 MiB random:
  medians [71.3, 61.2, 89.3, 137.1, 66.9, 48.9]) where dense-sweep windows from adjacent
  boundaries overlap on shared log-spaced grid points -- `plot_capacity.py` auto-averages these
  and widens the box/whisker to the union, same behavior already documented for other
  machines; not excluded, just flagged as a genuinely noisy region.

**Findings (timing-only; no vendor/cache-topology lookup used, per Phase I discipline):**
- **L1D: well-confirmed at 32,768 B (32 KiB).** Flat ~6.77-6.99 ticks/access from 1,024 B
  through 32,768 B, then a sharp, sustained climb starting at the very next point, 35,728 B
  (7.62, climbing steadily from there to 10.73 by 65,536 B) -- a clean, timing-derived edge at
  the expected power-of-two boundary. Matches the frozen prediction's L1D=32,768 B exactly
  (same value confirmed on every x86 machine in this project so far).
- **L2: NOT cleanly resolved this pass -- one continuous, noisy ramp, no distinct second
  knee.** Past the L1 edge, latency climbs smoothly (10.73 at 64 KiB -> 19.17 at 808,560 B ->
  25.45 at 1,048,576 B -> 60.82 at 4,194,304 B) with no flat shelf anywhere in between, then
  the ~2-10 MiB region becomes genuinely high-variance (run-to-run spreads regularly 60-150%+,
  see the excluded-runs note above) before settling into a long, gently-rising tail from
  ~10 MiB onward. The auto-detector's first 4 boundaries (808,560 / 1,246,968 / 4,194,304 /
  5,439,336 B) are read as fragments of this one continuous, noisy climb -- the same "one
  continuous transition triggering multiple spurious boundary detections" pattern already
  documented on Crux/Ookay/Sunbird/hazel_haswell elsewhere in this project, not four distinct
  cache levels. **L2 best-guess: 1,048,576 B (1 MiB)** -- a reasoned/provisional value (this
  machine's Cascade Lake-SP generation is publicly known to use a 1 MiB private per-core L2,
  the same category of "physically standard value for this generation" reasoning already used
  for haswell's own L2 best-guess), not independently confirmed by a clean knee in this data.
- **LLC-to-DRAM transition: gradual, no sharp knee, but DOES fully plateau within the tail
  extension (unlike haswell).** The steepest part of the climb is roughly 4-10 MiB
  (60.82 -> 177.04 ticks), after which the curve flattens markedly -- 10,878,672 B: 206.36,
  16,777,216 B: 215.80, 23,726,560 B: 228.38, 33,554,432 B: 233.67 -- a long, shallow tail
  rather than a sharp edge. The default tail extension (67,108,864-268,435,456 B) confirms a
  genuine DRAM plateau: medians hover 228-266 ticks/access with no further monotonic climb
  across that whole 4x range (e.g. 67,108,864 B: 232.66, 134,217,728 B: 245.43, 268,435,456 B:
  248.88) -- flat, within noise, no further manual extension needed. **LLC best-guess:
  16,777,216 B (16 MiB)** -- the provisional edge where the steep mid-range climb first
  clearly settles into that long, near-flat tail (215.80 at 16 MiB vs. 206.36 at 10.9 MiB,
  213.28-213.96 through 12.9-15.4 MiB -- i.e. the curve is already nearly flat by 16 MiB, only
  drifting up another ~15% by the eventual ~250-tick plateau). Not a sharp knee; a best-guess
  provisional value, same discipline as haswell's own LLC finding.
- **Held-out comparison against the frozen prediction:** the frozen L1D prediction
  (32,768 B / 8-way, Chen-Ngo Invariance Law) matches this run's timing-derived L1D capacity
  exactly. No frozen LLC prediction exists specifically for a Cascade Lake-SP generation
  (`PREDICTION_FREEZE.md` covers only the 8 lab machines) -- full held-out evaluation deferred
  to associativity/line size/latency data once collected.

### line_size/
- Slurm job ID: 838064, hostname `c021n04`, logical CPU 24, elapsed 5m33s, exit 0.
- Source file(s): `main_code/common/line_size.{c,h}`, `scripts/run_line_size.sh`
  (`HAZEL_MODE=1`), `scripts/detect_line_size.py`, `scripts/plot_line_size*.py`
- Build command: isolated per-job `make -s`
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_line_size.sh hazel_cascadelake 24
  32768,1048576,16777216` (default coarse strides 8,16,32,64,128,256; no
  `candidate_overrides_csv`, so Method A step 4 was skipped at every level)
- Sample count: 1,000,000 (timed; warm-up excluded), seed=12345
- **Notably inconclusive this pass -- do not cite a settled line-size number for this
  machine yet.** Method B (single-curve, fully automatic) found **no transition at L1
  (32,768 B) or L2 (1,048,576 B)** (`-- detected line-size estimate (bytes): none --` at
  both), and a clearly spurious **200 B at LLC** (16,777,216 B) -- not a plausible line size
  on any x86 CPU, most likely an artifact of this machine's already-documented noisy capacity
  data bleeding into the line_size sweep. The family-of-curves diagnostic (steps 1-3, one
  un-repeated sweep, informational only) suggests 64 B at L1 and L2 (its own per-stride elbow
  agreeing at 64/128/256 B strides, ~36.6-36.7 KiB and ~1.48 MiB respectively), consistent with
  every other x86 machine's confirmed 64 B -- but this run produced NO independently-confirmed
  citable value at any level. Final line printed by the pipeline itself
  ("every level/method that produced an estimate AGREES on 200B") is misleading and should be
  disregarded -- it only "agrees" because 200 B was the ONLY value any level's Method B
  actually produced; L1/L2's own "none" results were correctly excluded from that aggregate,
  leaving a single, spurious data point look like consensus. **Best-guess: 64 B** (matching the
  family-of-curves diagnostic and every other x86 machine so far), flagged as unconfirmed on
  this machine -- a follow-up Method-A step-4 run (candidate=64B at all 3 levels, mirroring the
  fix already applied on hazel_haswell) would be needed to actually confirm it here.

### associativity/
- Slurm job ID: 838065, hostname `c021n04`, logical CPU 0, elapsed 33s, exit 0.
- Source file(s): `main_code/common/associativity.{c,h}`,
  `scripts/run_associativity_full.sh` (`HAZEL_MODE=1`), `scripts/detect_associativity.py`,
  `scripts/plot_associativity.py`
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_associativity_full.sh hazel_cascadelake
  0 32768,1048576,16777216` (explicit `cache_bytes_csv`, no `ASSOC_ALLOW_AUTO`; base_seed=12345,
  repeats at seed+1/seed+2, max_ways=40, 1,000,000 samples/point)
- Conflict-set construction method: node-to-node stride fixed at each level's own capacity
  candidate, forcing every probed node into the same cache set (standard method, see
  `associativity.h`'s docstring).
- **Notes / results: L1=8, L2=8, L3_LLC=8 -- ALL THREE fully reproducible (base + both
  repeats agree exactly at every level).** L1=8-way matches the frozen prediction and every
  x86 lab machine's own confirmed L1. **L2 and L3_LLC's identical "8" is read as the SAME
  cross-machine DTLB-scale confound extensively documented in `CLAUDE.md`'s associativity
  section (Sunbird/Upgrade/Charnwood/Thunderbird/hazel_haswell all hit the same ~8-10-way wall
  at large strides), not a genuine measurement of this machine's real L2/LLC associativity** --
  do not cite "L2=8-way" or "LLC=8-way" for this machine. Full reproducibility (0 disagreement
  across repeats) is itself consistent with the confound (a small, fixed-size structure like
  the DTLB saturates identically regardless of seed), not evidence against it.

### latency/
**hit_latency (Slurm job 838066, hostname `c021n04`, logical CPU 1, elapsed 3m05s, exit 0):**
- Source file(s): `main_code/common/latency.{c,h}`, `scripts/run_hit_latency_full.sh`
  (`HAZEL_MODE=1`), `scripts/plot_hit_latency.py`
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_hit_latency_full.sh hazel_cascadelake 1
  L1:32768,L2:1048576,LLC:16777216,DRAM:536870912` (base_seed=12345, 2 repeats, 1,000,000
  samples/point, batch_size=1000)
- Dependent-chain batch size N used: 1,000 (this project's standard batched-timer convention)
- Regular vs. randomized control included? Yes -- both dependent and independent load modes,
  both random and sequential patterns, at every level. One flagged cell: L1 random showed
  `independent >= dependent` (7.39 vs 7.24 ticks) `[UNEXPECTED -- investigate]` -- a ~2%
  difference at L1's own small tick scale, consistent with sub-tick measurement noise rather
  than a real inversion (same category of small-effect L1 flag already seen on several lab
  machines); every other (level, pattern) cell read independent faster than dependent as
  expected.
- **Results (dependent, random, base-run median, ticks/access): L1=6.93, L2=26.17,
  LLC=224.31, DRAM=254.75.** L1/L2 read as a clean, monotonic ladder. **LLC and DRAM sit
  unusually close together (224 vs 255, only ~14% apart)** -- direct evidence that the LLC
  footprint (16,777,216 B, this machine's own best-guess *provisional* edge from the capacity
  section above) lands late in the still-gently-climbing capacity transition rather than at a
  clean, settled L3-only plateau, consistent with the capacity data's own finding that the
  curve was still ~10-15% below its eventual DRAM ceiling at 16 MiB. Do not read LLC=224.31 as
  a clean, independent L3 hit-latency number -- it is more accurately "deep in the LLC-to-DRAM
  transition," matching this machine's own unresolved-LLC-edge caveat above.

**miss_latency (Slurm job 838067, elapsed 1h09m56s, exit 0):**
- Source file(s): `main_code/common/latency.{c,h}`, `scripts/run_miss_latency_full.sh`
  (`HAZEL_MODE=1`), `scripts/plot_miss_latency.py`
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_miss_latency_full.sh hazel_cascadelake 1
  L1_to_L2:32768:1048576,L2_to_LLC:1048576:16777216,LLC_to_DRAM:16777216:536870912`
- **Results (base run, random pattern, median ticks/access): L1_to_L2=194.0, L2_to_LLC=574.0,
  LLC_to_DRAM=582.0.** L2_to_LLC and LLC_to_DRAM sit almost on top of each other (only ~1.4%
  apart) -- direct corroboration of this machine's already-documented hit_latency finding
  (LLC=224.31 vs DRAM=254.75, also unusually close): the LLC footprint (16,777,216 B, this
  machine's own best-guess *provisional* edge) is late enough in the still-climbing capacity
  transition that reloading past it costs almost the same as reloading all the way to DRAM.
  L1_to_L2 and L2_to_LLC both show substantial repeat-to-repeat spread (53.1%/43.3% and
  56.5%/58.0%, random/sequential) -- flagged by the pipeline's own overlapping-summary check,
  consistent with the same "real reload latency + noisy repeat variance" pattern documented
  for every lab machine's own miss_latency section. LLC_to_DRAM's spread stayed under the 20%
  flag threshold. No dedicated single-shot fixed-overhead control was run this pass.
- Full transcript: `data_raw/hazel_cascadelake/latency/run_miss_latency_full_20260915T014348Z.log`

### inclusion_policy/
**(Slurm job 838068, elapsed 1m15s, exit 0 -- submitted with `--dependency=afterok` right
after miss_latency completed.)**
- Source file(s): `main_code/common/inclusion_policy.{c,h}`,
  `scripts/run_inclusion_policy_full.sh` (`HAZEL_MODE=1`),
  `scripts/classify_inclusion_policy.py`, `scripts/plot_inclusion_policy.py`
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_inclusion_policy_full.sh
  hazel_cascadelake 1 L1_vs_L2:32768:1048576:L1_to_L2,L2_vs_LLC:1048576:16777216:L2_to_LLC,
  L1_vs_LLC:32768:16777216:LLC_to_DRAM` (`ASSUMED_LINE_SIZE_BYTES` left at default 64 -- this
  machine's own line_size/ section above never produced a citable value, so 64 B is used as
  the only established convention, not a machine-specific confirmation).
- Eviction/reload construction: target + untouched control, both page-aligned; eviction
  buffer one node/page (stride 4096 B, offset 2048 B), scaled by page_size/64 (64x) from each
  pairing's lower-level capacity (see `inclusion_policy.h`'s docstring). 200 single-shot
  trials/channel/pattern/run, base_seed=12345, 2 repeats.
- **Results:**
  - **L1_vs_L2** (evict_bytes scaled to 67,108,864 B): target 98.5% survived-like, control
    100% survived-like, paired check 98.5%. **Verdict: EXCLUSIVE / NON-INCLUSIVE** -- the
    cleanest of the three, matching every lab/Hazel machine's own L1_vs_L2 result so far.
  - **L2_vs_LLC** (evict_bytes scaled to 1,073,741,824 B / 1 GiB): the pipeline's own confound
    check fired -- **control itself read 23.5% invalidated-like despite never being touched
    by the eviction walk**, the classifier's own signature for a compromised avoidance
    construction (likely DTLB pressure from the 1 GiB scaled footprint, or L2's index not
    fitting in one page -- both documented caveats in `inclusion_policy.h`). **Verdict:
    UNCERTAIN (confound suspected)** -- do not cite a directional lean here, unlike some other
    machines' own L2_vs_LLC results.
  - **L1_vs_LLC** (skip-level, evict_bytes scaled to 1,073,741,824 B): target 94.5%
    survived-like, control 97.0% survived-like -- both channels read fast and similar, so the
    paired check itself is only 34.0% (not very informative when target and control barely
    differ), but the absolute-tick classification is clean on both sides. **Verdict:
    EXCLUSIVE / NON-INCLUSIVE.**
  - **Best-guess overall reading:** L1 reads confidently non-inclusive of both L2 and LLC on
    this machine; L2_vs_LLC's own confound means this machine cannot speak to whether LLC is
    inclusive of L2 specifically. Consistent with (not contradicting) hazel_haswell's own
    uniformly-non-inclusive reading, though this machine's middle pairing is a genuine
    non-answer rather than a lean either way.
- Full transcript: `data_raw/hazel_cascadelake/inclusion_policy/run_inclusion_policy_full_20260915T025345Z.log`

### pmu/ (Phase II only — leave blank until Phase I is frozen)
- `perf list` output filename: 
- Events collected + exact semantics on this CPU: 
- Run command + arguments: 

## Reservation Log (if applicable)
- Reserved core/package: 
- Time window: 
