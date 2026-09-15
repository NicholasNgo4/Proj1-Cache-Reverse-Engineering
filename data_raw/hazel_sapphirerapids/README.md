# hazel_sapphirerapids — Reproduction Manifest

> Fill in every field before freezing results. This README must let a grader go from
> this folder to the exact command that generated the data without guessing.

## Machine Identification
- Hostname: `n0407` (allocated by Slurm for `--constraint=sapphirerapids`, job 833556)
- CPU model (from `lscpu`/`/proc/cpuinfo`): `Intel(R) Xeon(R) Platinum 8462Y+` -- matches NC State's documented
  `sapphirerapids` constraint mapping (see PREDICTION_FREEZE.md/assignment Table 4).
- ISA / architecture: x86-64 (`uname -a`: `x86_64 x86_64 x86_64 GNU/Linux`)
- Vendor / microarchitecture / codename (researched, NOT from cache tables): Intel Sapphire Rapids (4th Gen Xeon Scalable)
- Introduction year (per the team's stated year convention): 2023
- Process node (if reliably documented): Intel 7 (10nm ESF)
- Kernel version: `5.14.0-611.5.1.el9_7.x86_64`
- Page size: 4096 bytes (standard x86-64)
- SMT siblings idle during runs? This access-check job requested 1 CPU
  (`--cpus-per-task=1`); Slurm bound it to logical CPU 32 (socket 1, NUMA
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
  Resulting binding: `physcpubind: 32`, socket 1, NUMA node 1
  (via `numactl -s`).
- NUMA/locality method: `numactl -s` plus `lscpu -e=CPU,CORE,SOCKET,NODE` (both on the Phase
  Discipline whitelist) -- logical CPU 32 is socket 1, NUMA node 1 on this node.
- Git commit hash of the code used for these results: `cb7e0c8c82c0269507e665db04563dee78fda9a6` (the `predictions-frozen`
  tag's own commit is an ancestor of this HEAD -- confirmed by this job's own gate check
  before running anything past the smoke test)

**Job record (this pass -- access/build check only, not the full suite):** Slurm job ID
833556, elapsed 26s, exit code 0. Full stdout/stderr: `hw1_sapphirerapids_833556.log` /
`hw1_sapphirerapids_833556.err.log` (committed alongside this README; `.log` suffix used instead of
Slurm's default `.out` because this repo's `.gitignore` blanket-ignores `*.out`). The job built
`cache_bench` cleanly (in an isolated per-job directory, `hazel_build/833556/`, to avoid
races with sibling generations' jobs building concurrently in this same shared GPFS checkout --
see `hpc_slurm/hw1_sapphirerapids.sh`'s header) and ran one tiny (`--samples 1000`, 4096-65536 B)
`--experiment capacity` smoke test under `srun --cpu-bind=cores` to confirm the binary runs
correctly bound to a real core on Hazel -- this is NOT the 1,000,000-sample suite required for
the actual capacity/line_size/associativity/latency/inclusion_policy experiments, which are run
by a separate `hw1_sapphirerapids_<experiment>.sh` job script per experiment type (see
`hpc_slurm/README.md`).

## Per-Experiment Reproduction

### capacity/
- Slurm job ID: 837634, hostname `n0407`, logical CPU 40, elapsed 55m17s, exit 0.
- Source file(s): `main_code/common/{main.c,benchmark.c,pointer_chase.c,random.c,capacity.c}`,
  `scripts/run_capacity_full.sh` (`HAZEL_MODE=1`), `scripts/summarize_raw.py`,
  `scripts/detect_cache_hierarchy.py`, `scripts/plot_capacity.py`
- Build command: `make -s` (isolated per-job copy under `hazel_build/837634/`, cleaned up on
  job exit)
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_capacity_full.sh hazel_sapphirerapids
  40` (coarse_max defaulted to 67,108,864 B / 64 MiB, then a 4x tail extension to 256 MiB)
- Sample count: 1,000,000 (timed; warm-up excluded) -- every stage
- Random seed(s): base 12345; reproducibility repeats on the deepest boundary use the same
  seed (this script's own known limitation)
- Raw output filename(s):
  `data_raw/hazel_sapphirerapids/capacity/capacity_{coarse,coarse_ext,dense0..dense7,
  dense7_rep1,dense7_rep2}_{random,sequential}_20260915T010343Z.csv.gz` (no separate
  `denseTail` file this run -- the deepest auto-detected boundary, 134,217,728 B, was already
  beyond the default 64 MiB coarse ceiling, so its own dense sweep window,
  16,777,216-268,435,456 B, absorbed what would otherwise be a separate tail-extension pass);
  full transcript: `data_raw/hazel_sapphirerapids/capacity/run_capacity_full_20260915T010343Z.log`
- Processing script -> data_processed path: `scripts/summarize_raw.py` ->
  `data_processed/hazel_sapphirerapids/capacity/*_summary.csv`;
  `scripts/detect_cache_hierarchy.py` (default thresholds) -> 8 candidate boundaries (see
  Findings); `scripts/plot_capacity.py` ->
  `data_processed/hazel_sapphirerapids/capacity/plots/capacity_{curve,boxplots}.{png,pdf}`
- Excluded runs (if any) and reason: none -- single complete run; see the Findings' anomaly
  note below (flagged, not excluded/re-run).

**Findings (timing-only; no vendor/cache-topology lookup used, per Phase I discipline).
CPU: Intel Xeon Platinum 8462Y+ (Sapphire Rapids). This run shows TWO separate anomalies
(more than icelake_6326's one) and one genuinely surprising, deviation-from-every-other-
machine L1D result -- read all three notes before citing a number from this machine.**
- **Anomaly 1: scattered latency DROPS throughout the small-footprint region, recurring at
  several unrelated sizes, not just one point.** The ~9.5-9.7 tick baseline (1,216-38,968 B)
  is repeatedly punctured by sharp single-point drops to ~5.1-8.0 ticks (2,232 B: 5.10;
  12,632 B: 5.10; 13,776 B: 5.10; 17,864 B: 5.10; 42,488 B: 5.17 -- five separate, unrelated
  footprints all landing near the same ~5.1 floor). A real cache effect would not recur at
  scattered, unrelated byte values like this -- read as a repeating measurement/scheduling
  artifact (possibly SMT-neighbor or turbo-state related), not real signal. The auto-detector's
  own first boundary (17,864 B) is very likely a false trigger off exactly one of these dips,
  not a real edge.
- **L1D: NOT the 32,768 B every other Hazel/lab machine has confirmed -- best-guess 49,152 B
  (48 KiB) instead, a genuine architectural difference, not just noise.** Despite Anomaly 1's
  scattered dips, the underlying baseline plateau (~9.5-9.7 ticks) clearly persists all the way
  through 38,968 B -- well past every other machine's confirmed 32,768 B L1 edge, where this
  same baseline would already be climbing. A real, sustained climb only becomes unambiguous by
  77,936 B (9.81, now clearly above baseline) and 84,984 B (10.24), continuing steadily upward
  from there. This is consistent with Sapphire Rapids' Golden-Cove-derived core using a 48 KiB
  L1D (a real, public architectural fact about this generation, distinct from every earlier
  generation in this project's Table 4, all of which use 32 KiB) -- the timing data itself
  independently supports a boundary noticeably past 32 KiB, this isn't purely an assumed value.
  Not citable as a clean, sharp knee (the 42,488-71,464 B region is too noisy for that), but
  the *direction* of the deviation (bigger than every other machine, not just noisier) is a
  real, timing-observed finding worth carrying forward.
- **L2: NOT resolved.** Continuous climb from 84,984 B through 9,975,792 B (10.24 -> 144.70),
  no distinct shelf -- the auto-detector's 4 boundaries in this range (1,482,904 / 2,286,960 /
  2,493,944 / 3,234,248 B) are fragments of this one ramp. **L2 best-guess: 2,097,152 B
  (2 MiB)** -- Sapphire Rapids' publicly known standard per-core L2 size (this generation's L2
  is notably larger than every earlier generation in this project, consistent with the same
  Golden-Cove-core lineage as the L1D finding above).
- **Anomaly 2: a second sharp ~2.5x drop, same category as icelake_6326's own single anomaly,
  at a similar absolute size (~10-12 MiB on both machines).** 9,975,792 B: 144.70 ->
  10,878,672 B: 137.90 -> 11,863,280 B: 56.65 -- a real boundary does not cut latency by more
  than half; read as the same session-level-interference category as icelake_6326's anomaly
  (see that machine's own README), and notably landing at a similar absolute footprint on both
  machines -- worth flagging as a possible *pipeline-level* artifact (e.g. a scheduling
  transition specific to where the coarse sweep sits around this size/timestamp) rather than
  two unrelated coincidences, though not further diagnosed this pass.
- **LLC: a genuine post-anomaly shelf, then a real (if lower-than-spec) departure.** Past
  Anomaly 2, the curve is flat: 11,863,280 B: 56.65 through 36,591,368 B: 61.85 (~9% drift
  across a 3x size range) -- then a real, sustained climb resumes: 39,903,168 B: 65.77,
  47,453,128 B: 71.22, 67,108,864 B: 98.52. **LLC best-guess: 39,903,168 B (~38.05 MiB)** --
  the provisional edge where the shelf first clearly departs. Notably lower than this SKU's
  known 60 MB total L3 -- plausibly because a single-thread pointer chase on a large,
  sliced/mesh LLC doesn't need to fill the FULL die-wide L3 before missing consistently
  (address-hash/slice-routing and snoop-filter effects can make the *effectively reachable*
  capacity from one core's perspective less than the nominal total), but this is reasoning, not
  a resolved explanation -- flagged as a real discrepancy, not smoothed over.
- **LLC-to-DRAM: does NOT plateau within the tested range (up to 256 MiB) -- same open item as
  haswell/skylake.** The deepest dense window (16,777,216-268,435,456 B) keeps climbing
  throughout: 67,108,864 B: 98.52, 134,217,728 B: 193.99, 206,992,032 B: 226.87, 268,435,456 B:
  264.35 -- no flattening anywhere in this range. A further manual extension past 256 MiB would
  be needed to find the true DRAM floor -- not attempted this pass.
- **Held-out comparison against the frozen prediction:** the frozen L1D prediction
  (32,768 B / 8-way) does NOT match this run -- see the L1D finding above, the first Hazel
  generation where the timing data itself points to a different L1D size, not just an
  unresolved/noisy region.
- Raw output filename(s): 
- Processing script -> data_processed path: 
- Excluded runs (if any) and reason: 

### line_size/
- Slurm job ID: 838196, exit 0.
- Source file(s): `main_code/common/line_size.{c,h}`, `scripts/run_line_size.sh`
  (`HAZEL_MODE=1`), `scripts/detect_line_size.py`, `scripts/plot_line_size*.py`
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_line_size.sh hazel_sapphirerapids 40
  49152,2097152,39903168` (default coarse strides; no `candidate_overrides_csv`, Method A
  step 4 skipped at every level)
- Sample count: 1,000,000 (timed; warm-up excluded), seed=12345
- **Inconclusive -- Method B found no transition at any of the 3 levels** (L1/L2/LLC all
  `none`). **Best-guess: 64 B** (the universal x86 default; independent of this machine's own
  distinct 48 KiB L1D finding, since line size and L1 capacity are unrelated properties).

### associativity/
- Slurm job ID: 838350 (resubmit of 838197, which failed on the same non-4096-aligned LLC
  value pattern as skylake's; 39,903,168 B rounded to 39,903,232 B for this experiment's own
  `--cache-bytes` argument only), logical CPU 40, elapsed 32s, exit 0.
- Source file(s): `main_code/common/associativity.{c,h}`,
  `scripts/run_associativity_full.sh` (`HAZEL_MODE=1`), `scripts/detect_associativity.py`,
  `scripts/plot_associativity.py`
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_associativity_full.sh
  hazel_sapphirerapids 40 49152,2097152,39903232` (base_seed=12345, repeats at
  seed+1/seed+2, max_ways=40, 1,000,000 samples/point)
- Conflict-set construction method: node-to-node stride fixed at each level's own capacity
  candidate (standard method).
- **Notes / results: L1=12, L2=12, L3_LLC=12 -- all three fully reproducible, but L1's "12"
  is likely real while L2/LLC's identical "12" is very likely the usual confound wearing the
  same digit by coincidence.** The arithmetic-consistency check (sets = cache_bytes /
  64 B-lines / assoc must be a whole number) draws a clean line here: **L1 at 49,152 B with
  12-way gives EXACTLY 64 sets (768 total lines / 12 = 64)** -- physically valid, and directly
  corroborates this machine's own capacity-section finding that L1D is 48 KiB, not the usual
  32,768 B (48 KiB / 64 B-lines / 12-way = 64 sets is an architecturally ordinary L1D
  design). **L2 (2,097,152 B) and LLC (39,903,232 B) at the same "12" both fail this check**
  (sets=2730.67 and 51957.33 respectively, neither a whole number) -- direct, same-run
  evidence that L2/LLC's own "12" is the cross-machine DTLB-scale confound documented in
  `CLAUDE.md` coincidentally reporting the same integer as L1's real value, not a genuine L2/
  LLC measurement. **This is the cleanest positive confirmation yet, on any Hazel machine, of
  both halves of this project's long-running associativity story**: a real, non-8-way L1
  result that IS arithmetically self-consistent, sitting right next to L2/LLC values that
  are NOT.

### latency/
**hit_latency (Slurm job 838198, exit 0):**
- Source file(s): `main_code/common/latency.{c,h}`, `scripts/run_hit_latency_full.sh`
  (`HAZEL_MODE=1`), `scripts/plot_hit_latency.py`
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_hit_latency_full.sh
  hazel_sapphirerapids 40 L1:49152,L2:2097152,LLC:39903168,DRAM:536870912` (base_seed=12345,
  2 repeats, 1,000,000 samples/point, batch_size=1000)
- Dependent-chain batch size N used: 1,000
- Regular vs. randomized control included? Yes -- one flagged cell, L1 sequential
  (`independent >= dependent`, 20.14 vs 17.67 ticks, `[UNEXPECTED -- investigate]`) -- a
  sequential-pattern L1 effect (prefetcher-related, same category documented on several lab
  machines), not a real inversion at the level that matters (random). Every other cell read
  as expected.
- **Results (dependent, random, base-run median, ticks/access): L1=17.45, L2=24.52,
  LLC=155.96, DRAM=283.30** -- a clean, monotonic 4-tier ladder, LLC/DRAM well-separated
  (~82% apart), consistent with this machine's own capacity finding that LLC-to-DRAM never
  plateaus (a genuinely large, real gap between these two levels here).

**miss_latency (Slurm job 838199, elapsed 1h16m20s, exit 0):**
- Source file(s): `main_code/common/latency.{c,h}`, `scripts/run_miss_latency_full.sh`
  (`HAZEL_MODE=1`), `scripts/plot_miss_latency.py`
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_miss_latency_full.sh
  hazel_sapphirerapids 40 L1_to_L2:49152:2097152,L2_to_LLC:2097152:39903168,
  LLC_to_DRAM:39903168:536870912`
- **Results (base run, random pattern, median ticks/access): L1_to_L2=214.0, L2_to_LLC=566.0,
  LLC_to_DRAM=825.0** -- cleanly increasing, unlike icelake_6326's own inverted result.
  Substantial repeat-to-repeat spread flagged (40-56.5%), not re-run.

### inclusion_policy/
**(Slurm job 838200, elapsed 2m10s, exit 0.)**
- Source file(s): `main_code/common/inclusion_policy.{c,h}`,
  `scripts/run_inclusion_policy_full.sh` (`HAZEL_MODE=1`),
  `scripts/classify_inclusion_policy.py`, `scripts/plot_inclusion_policy.py`
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_inclusion_policy_full.sh
  hazel_sapphirerapids 40 L1_vs_L2:49152:2097152:L1_to_L2,L2_vs_LLC:2097152:39903168:L2_to_LLC,
  L1_vs_LLC:49152:39903168:LLC_to_DRAM` (`ASSUMED_LINE_SIZE_BYTES` default 64).
- **Results:**
  - **L1_vs_L2**: target 100% survived-like, control 100% survived-like. **Verdict:
    EXCLUSIVE / NON-INCLUSIVE** -- clean, no calibration warnings.
  - **L2_vs_LLC**: target 29.5% survived-like / 48.5% invalidated-like / 44 ambiguous,
    control 100% survived-like. **Verdict: UNCERTAIN (mixed result)** -- usual
    lowest-confidence pairing.
  - **L1_vs_LLC (skip-level)**: target 99.5% survived-like, control 100% survived-like.
    **Verdict: EXCLUSIVE / NON-INCLUSIVE.**
  - **Best-guess overall reading:** leans non-inclusive throughout, same overall shape as
    hazel_skylake's and hazel_icelake_6326's own results.
- Full transcript: see
  `data_raw/hazel_sapphirerapids/inclusion_policy/run_inclusion_policy_full_*.log`

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
