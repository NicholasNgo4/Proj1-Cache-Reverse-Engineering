# hazel_broadwell — Reproduction Manifest

> Fill in every field before freezing results. This README must let a grader go from
> this folder to the exact command that generated the data without guessing.

## Machine Identification
- Hostname: `c205n04` (allocated by Slurm for `--constraint=broadwell`, job 833551)
- CPU model (from `lscpu`/`/proc/cpuinfo`): `Intel(R) Xeon(R) CPU E5-2650 v4 @ 2.20GHz` -- matches NC State's documented
  `broadwell` constraint mapping (see PREDICTION_FREEZE.md/assignment Table 4).
- ISA / architecture: x86-64 (`uname -a`: `x86_64 x86_64 x86_64 GNU/Linux`)
- Vendor / microarchitecture / codename (researched, NOT from cache tables): Intel Broadwell-EP
- Introduction year (per the team's stated year convention): 2016
- Process node (if reliably documented): 14 nm
- Kernel version: `5.14.0-611.5.1.el9_7.x86_64`
- Page size: 4096 bytes (standard x86-64)
- SMT siblings idle during runs? This access-check job requested 1 CPU
  (`--cpus-per-task=1`); Slurm bound it to logical CPU 13 (socket 1, NUMA
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
  Resulting binding: `physcpubind: 13`, socket 1, NUMA node 1
  (via `numactl -s`).
- NUMA/locality method: `numactl -s` plus `lscpu -e=CPU,CORE,SOCKET,NODE` (both on the Phase
  Discipline whitelist) -- logical CPU 13 is socket 1, NUMA node 1 on this node.
- Git commit hash of the code used for these results: `cb7e0c8c82c0269507e665db04563dee78fda9a6` (the `predictions-frozen`
  tag's own commit is an ancestor of this HEAD -- confirmed by this job's own gate check
  before running anything past the smoke test)

**Job record (this pass -- access/build check only, not the full suite):** Slurm job ID
833551, elapsed 35s, exit code 0. Full stdout/stderr: `hw1_broadwell_833551.log` /
`hw1_broadwell_833551.err.log` (committed alongside this README; `.log` suffix used instead of
Slurm's default `.out` because this repo's `.gitignore` blanket-ignores `*.out`). The job built
`cache_bench` cleanly (in an isolated per-job directory, `hazel_build/833551/`, to avoid
races with sibling generations' jobs building concurrently in this same shared GPFS checkout --
see `hpc_slurm/hw1_broadwell.sh`'s header) and ran one tiny (`--samples 1000`, 4096-65536 B)
`--experiment capacity` smoke test under `srun --cpu-bind=cores` to confirm the binary runs
correctly bound to a real core on Hazel -- this is NOT the 1,000,000-sample suite required for
the actual capacity/line_size/associativity/latency/inclusion_policy experiments, which are run
by a separate `hw1_broadwell_<experiment>.sh` job script per experiment type (see
`hpc_slurm/README.md`).

## Per-Experiment Reproduction

### capacity/
- Slurm job ID: 837629, logical CPU 12, elapsed 1h23m07s, exit 0.
- Source file(s): `main_code/common/{main.c,benchmark.c,pointer_chase.c,random.c,capacity.c}`,
  `scripts/run_capacity_full.sh` (`HAZEL_MODE=1`), `scripts/summarize_raw.py`,
  `scripts/detect_cache_hierarchy.py`, `scripts/plot_capacity.py`
- Build command: `make -s` (isolated per-job copy under `hazel_build/837629/`, cleaned up on
  job exit)
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_capacity_full.sh hazel_broadwell 12`
  (coarse_max defaulted to 67,108,864 B / 64 MiB, then a 4x tail extension to 256 MiB)
- Sample count: 1,000,000 (timed; warm-up excluded) -- every stage
- Random seed(s): base 12345; reproducibility repeats on the deepest boundary use the same
  seed (this script's own known limitation)
- Raw output filename(s):
  `data_raw/hazel_broadwell/capacity/capacity_{coarse,coarse_ext,dense0..dense4,dense4_rep1,
  dense4_rep2,denseTail}_{random,sequential}_20260915T010343Z.csv.gz`; full transcript:
  `data_raw/hazel_broadwell/capacity/run_capacity_full_20260915T010343Z.log`
- Processing script -> data_processed path: `scripts/summarize_raw.py` ->
  `data_processed/hazel_broadwell/capacity/*_summary.csv`;
  `scripts/detect_cache_hierarchy.py` (default thresholds) -> 5 candidate boundaries (see
  Findings); `scripts/plot_capacity.py` ->
  `data_processed/hazel_broadwell/capacity/plots/capacity_{curve,boxplots}.{png,pdf}`
- Excluded runs (if any) and reason: none -- single complete run, no anomalies of the
  icelake_6326/sapphirerapids kind (some noise, but no implausible ~2x drops).

**Findings (timing-only; no vendor/cache-topology lookup used, per Phase I discipline).
CPU: Intel Xeon E5-2650 v4 (Broadwell-EP) -- same E5-2650 SKU line, one generation newer,
as hazel_haswell's own E5-2650 v3.**
- **L1D: well-confirmed at 32,768 B (32 KiB).** Flat ~7.66-7.83 ticks/access from 1,024 B
  through 32,768 B, then a clean, sustained climb starting at 35,728 B (8.26) -- matches the
  frozen prediction and hazel_haswell's own confirmed L1D exactly (same family, one
  generation apart).
- **L2: a real, if noisy, transition centered almost exactly on the architecturally-standard
  256 KiB.** The 142,928-285,864 B region shows large point-to-point oscillation (e.g.
  169,976 B: 14.80 vs. 202,136 B: 13.10 vs. 220,432 B: 16.78 -- 20-30% swings between adjacent
  points), but the auto-detector's own two candidates here (202,136 / 339,952 B) bracket
  262,144 B almost symmetrically, and 262,144 B (18.70) sits right in the middle of the
  climbing trend. **L2 best-guess: 262,144 B (256 KiB)** -- Broadwell-EP's publicly known
  per-core L2 size (matching haswell's own L2 best-guess exactly, same family), read with
  higher confidence than a pure best-guess given how well the noisy region's center lines up
  with this exact round value, but still not a single clean knee.
- **LLC: a genuine, long flat shelf (2-24 MiB) followed by a real departure.** From
  1,923,096 B (43.30) the curve settles into a long, quite flat plateau -- 38-43 ticks/access
  continuously from ~2 MiB through 23,726,560 B (41.41), a 12x size range with minimal drift
  -- then a clear, sustained departure: 25,874,000 B -> 46.78, 28,215,800 B -> 49.60,
  33,554,432 B -> 58.56, 36,591,368 B -> 89.76. **LLC best-guess: 25,874,000 B (~24.68 MiB)**
  -- the provisional edge where the shelf first clearly departs (same methodology as
  hazel_haswell's own LLC pick), somewhat below this SKU's own often-cited ~30 MB L3 spec but
  in the same order of magnitude.
- **LLC-to-DRAM: noisy, does not cleanly plateau within the tested range (up to 268 MiB).**
  Tail extension values swing substantially (103,496,016 B: 149.99, 181,765,096 B: 264.63,
  210,002,800 B: 173.66, 268,435,448 B: 202.65) with no clear monotonic trend but also no
  settled floor -- consistent with a real but noisy plateau, not confidently resolved. A
  further manual extension/repeat would be needed to pin down the true DRAM floor cleanly --
  not attempted this pass.
- **Held-out comparison against the frozen prediction:** the frozen L1D prediction
  (32,768 B / 8-way, Chen-Ngo Invariance Law, derived from hazel_haswell's own sibling SKU)
  matches this run's timing-derived L1D capacity exactly.
- Raw output filename(s): 
- Processing script -> data_processed path: 
- Excluded runs (if any) and reason: 

### line_size/
- Slurm job ID: 838232, exit 0.
- Source file(s): `main_code/common/line_size.{c,h}`, `scripts/run_line_size.sh`
  (`HAZEL_MODE=1`), `scripts/detect_line_size.py`, `scripts/plot_line_size*.py`
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_line_size.sh hazel_broadwell 22
  32768,262144,25874000` (default coarse strides; no `candidate_overrides_csv`, Method A
  step 4 skipped at every level)
- Sample count: 1,000,000 (timed; warm-up excluded), seed=12345
- **L1 produced a real, citable 64 B; LLC produced a different, implausible value (136 B),
  flagged by the pipeline as a genuine disagreement.** L1 (32,768 B): 64 B, matching the
  frozen prediction and hazel_haswell's own confirmed L1 line size exactly. L2 (262,144 B):
  no transition. LLC (25,874,000 B): 136 B -- not a standard line size on any real hardware,
  most likely a noisy/spurious large-footprint detection (same category as
  hazel_cascadelake's own implausible 200 B and hazel_genoa's own 112 B). **Best-guess: 64 B
  for all levels** -- L1's own clean detection, trusted over LLC's implausible outlier.

**Follow-up re-run (2026-09-15), L3 only:** the family-of-curves plot at this level was
flagged as not looking clean; re-ran with `hpc_slurm/hw1_line_size_relook.sh` into a
separate `data_raw/hazel_broadwell/line_size_rerun/` / `data_processed/hazel_broadwell/
line_size_rerun/` subdirectory (original data above kept, not overwritten). **Result: WORSE,
not better** -- the new run's own 8 B-stride curve shows a sharp, reproducible cliff-drop
(mean ~43 with a TIGHT stddev of ~1.2-1.4, not a single wild outlier) at exactly two
adjacent footprints (14,521,288 / 16,299,592 B), sandwiched between neighboring points
reading ~170-180. A real cache/line-size effect cannot cause latency to drop ~4x at one
footprint and recover at the next; the low stddev rules out simple single-sample noise. Most
consistent with a brief, genuine easing of contention on this SHARED (non-exclusive) compute
node during the sweep -- the same "idle core doesn't insulate from chip-shared contention"
category of finding already documented extensively elsewhere in this project (see
`CLAUDE.md`'s `eight_counters`/PMU sections) -- not a bug in this pipeline. A single re-run
is not guaranteed to avoid this, since it depends on what other users' jobs happen to be
doing on the same physical node at the time. Compare
`data_processed/hazel_broadwell/line_size_rerun/line_size/level_25874000/plots/
line_size_family_curve.png` against the original plot referenced above.

### associativity/
- Slurm job ID: 838351 (resubmit of 838233, which failed on the same non-4096-aligned LLC
  value pattern as icelake_6326's own; 25,874,000 B rounded to 25,874,432 B for this
  experiment's own `--cache-bytes` argument only), logical CPU 22, elapsed 40s, exit 0.
- Source file(s): `main_code/common/associativity.{c,h}`,
  `scripts/run_associativity_full.sh` (`HAZEL_MODE=1`), `scripts/detect_associativity.py`,
  `scripts/plot_associativity.py`
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_associativity_full.sh hazel_broadwell
  22 32768,262144,25874432` (base_seed=12345, repeats at seed+1/seed+2, max_ways=40,
  1,000,000 samples/point)
- Conflict-set construction method: node-to-node stride fixed at each level's own capacity
  candidate (standard method).
- **Notes / results: L1=8 (fully reproducible), L2=4 (fully reproducible), L3_LLC=9 base
  but one repeat found no knee at all and the other agreed at 9 (flagged disagreement).**
  L1=8-way matches the frozen prediction and hazel_haswell's own confirmed L1 exactly (sets=64,
  arithmetically valid). **L2=4-way is a genuinely distinct value from L1, not a repeat of
  it** -- and it's arithmetically valid (262,144 B / 64 B-lines / 4-way = 1,024 sets, a clean
  integer) -- this is the SAME "4-way L2" resolution this project's Phase II PMU work already
  found on several Skylake-family lab machines (Crux/Charnwood/Ookay/Upgrade all corrected
  their own confound-blocked "8-way" guess to a system-reported 4-way, see `CLAUDE.md`'s Phase
  II section) -- a plausible, if not independently PMU-confirmed here, real L2 associativity
  for this Broadwell-EP part, not just another instance of the confound repeating L1's digit.
  **LLC's own "9" fails the arithmetic check** (25,874,432 B / 64 / 9 = 44,920.89, not a whole
  number) -- read as the usual confound, not a real LLC associativity, consistent with every
  other machine's own LLC finding regardless of the specific digit reported.

### latency/
**hit_latency (Slurm job 838234, exit 0):**
- Source file(s): `main_code/common/latency.{c,h}`, `scripts/run_hit_latency_full.sh`
  (`HAZEL_MODE=1`), `scripts/plot_hit_latency.py`
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_hit_latency_full.sh hazel_broadwell 22
  L1:32768,L2:262144,LLC:25874000,DRAM:536870912` (base_seed=12345, 2 repeats, 1,000,000
  samples/point, batch_size=1000)
- Dependent-chain batch size N used: 1,000
- Regular vs. randomized control included? Yes -- no `[UNEXPECTED]` flags, independent read
  faster than dependent everywhere.
- **Results (dependent, random, base-run median, ticks/access): L1=7.85, L2=18.09,
  LLC=47.58, DRAM=186.79** -- a clean, monotonic 4-tier ladder. LLC's own ratio to L2 (~2.6x)
  is smaller than most other machines' own LLC/L2 ratios (often 5-10x), plausibly because
  this machine's LLC boundary (a provisional "shelf departure" edge, not vendor-spec-matched)
  undershoots the real L3 capacity somewhat -- consistent with the capacity section's own
  caveat that 25,874,000 B sits below this SKU's often-cited ~30 MB spec.

**miss_latency (Slurm job 838235, elapsed 1h23m01s, exit 0):**
- Source file(s): `main_code/common/latency.{c,h}`, `scripts/run_miss_latency_full.sh`
  (`HAZEL_MODE=1`), `scripts/plot_miss_latency.py`
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_miss_latency_full.sh hazel_broadwell
  22 L1_to_L2:32768:262144,L2_to_LLC:262144:25874000,LLC_to_DRAM:25874000:536870912`
- **Results (base run, random pattern, median ticks/access): L1_to_L2=76.0, L2_to_LLC=289.5,
  LLC_to_DRAM=1001.0** -- cleanly increasing. Substantial repeat spread flagged throughout
  (24.1-54.8%), not re-run.

### inclusion_policy/
**(Slurm job 838236, elapsed 2m15s, exit 0. All three pairings came back UNCERTAIN -- the
least informative inclusion_policy result of any Hazel generation, worse even than
icelake_8358's own noisy result.)**
- Source file(s): `main_code/common/inclusion_policy.{c,h}`,
  `scripts/run_inclusion_policy_full.sh` (`HAZEL_MODE=1`),
  `scripts/classify_inclusion_policy.py`, `scripts/plot_inclusion_policy.py`
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_inclusion_policy_full.sh
  hazel_broadwell 22 L1_vs_L2:32768:262144:L1_to_L2,L2_vs_LLC:262144:25874000:L2_to_LLC,
  L1_vs_LLC:32768:25874000:LLC_to_DRAM` (`ASSUMED_LINE_SIZE_BYTES` default 64).
- **Results:**
  - **L1_vs_L2**: target only 26.5% survived-like / 72.5% ambiguous, control 39.0%
    survived-like / 59.5% ambiguous -- both channels mostly ambiguous, unlike every other
    machine's own clean L1_vs_L2 pairing. **Verdict: UNCERTAIN (mixed result)**.
  - **L2_vs_LLC**: the classifier's confound warning fired at its most extreme -- **control
    itself read 100.0% invalidated-like**, despite never being touched by the eviction walk.
    **Verdict: UNCERTAIN (confound suspected)** -- total construction failure, not just a
    partial one.
  - **L1_vs_LLC (skip-level)**: control also compromised -- **86.0% invalidated-like**.
    **Verdict: UNCERTAIN (confound suspected)**.
  - **Best-guess overall reading: none -- this machine's inclusion_policy data supports no
    directional claim at any pairing.** The severity here (100%/86% control contamination,
    worse than any other machine's own confound-suspected result) is plausibly related to
    this machine's own provisional (below-spec) LLC boundary requiring a larger-than-real
    scaled eviction footprint, or to Broadwell-EP's own DTLB being smaller/more easily
    saturated than newer generations -- not independently diagnosed this pass.
- Full transcript: see
  `data_raw/hazel_broadwell/inclusion_policy/run_inclusion_policy_full_*.log`

### pmu/ (Phase II only — leave blank until Phase I is frozen)
- `perf list` output filename: 
- Events collected + exact semantics on this CPU: 
- Run command + arguments: 

## Reservation Log (if applicable)
- Reserved core/package: 
- Time window: 
