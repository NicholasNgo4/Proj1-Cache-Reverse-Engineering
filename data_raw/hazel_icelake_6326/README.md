# hazel_icelake_6326 — Reproduction Manifest

> Fill in every field before freezing results. This README must let a grader go from
> this folder to the exact command that generated the data without guessing.

## Machine Identification
- Hostname: `c060n02` (allocated by Slurm for `--constraint=icelake_6326`, job 833554)
- CPU model (from `lscpu`/`/proc/cpuinfo`): `Intel(R) Xeon(R) Gold 6326 CPU @ 2.90GHz` -- matches NC State's documented
  `icelake_6326` constraint mapping (see PREDICTION_FREEZE.md/assignment Table 4).
- ISA / architecture: x86-64 (`uname -a`: `x86_64 x86_64 x86_64 GNU/Linux`)
- Vendor / microarchitecture / codename (researched, NOT from cache tables): Intel Ice Lake-SP (3rd Gen Xeon Scalable)
- Introduction year (per the team's stated year convention): 2021
- Process node (if reliably documented): 10 nm (Intel 10nm SuperFin)
- Kernel version: `5.14.0-611.5.1.el9_7.x86_64`
- Page size: 4096 bytes (standard x86-64)
- SMT siblings idle during runs? This access-check job requested 1 CPU
  (`--cpus-per-task=1`); Slurm bound it to logical CPU 16 (socket 1, NUMA
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
  Resulting binding: `physcpubind: 16`, socket 1, NUMA node 1
  (via `numactl -s`).
- NUMA/locality method: `numactl -s` plus `lscpu -e=CPU,CORE,SOCKET,NODE` (both on the Phase
  Discipline whitelist) -- logical CPU 16 is socket 1, NUMA node 1 on this node.
- Git commit hash of the code used for these results: `cb7e0c8c82c0269507e665db04563dee78fda9a6` (the `predictions-frozen`
  tag's own commit is an ancestor of this HEAD -- confirmed by this job's own gate check
  before running anything past the smoke test)

**Job record (this pass -- access/build check only, not the full suite):** Slurm job ID
833554, elapsed 29s, exit code 0. Full stdout/stderr: `hw1_icelake_6326_833554.log` /
`hw1_icelake_6326_833554.err.log` (committed alongside this README; `.log` suffix used instead of
Slurm's default `.out` because this repo's `.gitignore` blanket-ignores `*.out`). The job built
`cache_bench` cleanly (in an isolated per-job directory, `hazel_build/833554/`, to avoid
races with sibling generations' jobs building concurrently in this same shared GPFS checkout --
see `hpc_slurm/hw1_icelake_6326.sh`'s header) and ran one tiny (`--samples 1000`, 4096-65536 B)
`--experiment capacity` smoke test under `srun --cpu-bind=cores` to confirm the binary runs
correctly bound to a real core on Hazel -- this is NOT the 1,000,000-sample suite required for
the actual capacity/line_size/associativity/latency/inclusion_policy experiments, which are run
by a separate `hw1_icelake_6326_<experiment>.sh` job script per experiment type (see
`hpc_slurm/README.md`).

## Per-Experiment Reproduction

### capacity/
- Slurm job ID: 837632, logical CPU 16, elapsed 52m52s, exit 0.
- Source file(s): `main_code/common/{main.c,benchmark.c,pointer_chase.c,random.c,capacity.c}`,
  `scripts/run_capacity_full.sh` (`HAZEL_MODE=1`), `scripts/summarize_raw.py`,
  `scripts/detect_cache_hierarchy.py`, `scripts/plot_capacity.py`
- Build command: `make -s` (isolated per-job copy under `hazel_build/837632/`, cleaned up on
  job exit)
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_capacity_full.sh hazel_icelake_6326 16`
  (coarse_max defaulted to 67,108,864 B / 64 MiB, then a 4x tail extension to 256 MiB)
- Sample count: 1,000,000 (timed; warm-up excluded) -- every stage
- Random seed(s): base 12345; reproducibility repeats on the deepest boundary use the same
  seed (this script's own known limitation)
- Raw output filename(s):
  `data_raw/hazel_icelake_6326/capacity/capacity_{coarse,coarse_ext,dense0..dense5,
  dense5_rep1,dense5_rep2,denseTail}_{random,sequential}_20260915T010343Z.csv.gz`; full
  transcript: `data_raw/hazel_icelake_6326/capacity/run_capacity_full_20260915T010343Z.log`
- Processing script -> data_processed path: `scripts/summarize_raw.py` ->
  `data_processed/hazel_icelake_6326/capacity/*_summary.csv`;
  `scripts/detect_cache_hierarchy.py` (default thresholds) -> 6 candidate boundaries (see
  Findings); `scripts/plot_capacity.py` ->
  `data_processed/hazel_icelake_6326/capacity/plots/capacity_{curve,boxplots}.{png,pdf}`
- Excluded runs (if any) and reason: none -- single complete run; see the Findings' anomaly
  note below (flagged, not excluded/re-run).

**Findings (timing-only; no vendor/cache-topology lookup used, per Phase I discipline).
CPU: Intel Xeon Gold 6326 (Ice Lake-SP). This run shows a genuine, unexplained anomaly that
makes the L1/L2 region untrustworthy this pass -- read the anomaly note before citing any
number below 10 MiB from this machine.**
- **Anomaly: a sharp, ~2x latency DROP between two adjacent coarse-sweep points, with no
  plausible cache-capacity explanation.** Latency climbs steadily and plausibly from 60,096 B
  (10.47) all the way to 9,147,840 B (132.71), then the very next point, 9,975,792 B, drops to
  65.98 -- roughly half -- before a SECOND, separate climb resumes from there. A real cache
  boundary does not roughly halve latency at ANY footprint (crossing a boundary only ever
  INCREASES miss cost); this is far more consistent with a session-level interference event
  (another process starting/stopping, a frequency/turbo-state change, or similar) coinciding
  with wherever the coarse sweep happened to be in its own elapsed-time timeline at that point,
  matching the same category of anomaly already documented elsewhere in this project (see
  Charnwood's/Ookay's/Artemisia's own contention write-ups in `CLAUDE.md`) -- not independently
  root-caused this pass (no `mpstat`/`ps` snapshot was taken mid-run to confirm a specific
  contending process). The small-size region below this point is also noisier than every other
  Hazel generation run so far (values oscillate 7.2-9.9 ticks with no clean monotonic trend
  from 1,216 B through 55,104 B, rather than a flat plateau), consistent with contention being
  present from early in the run, not just at the one dramatic drop point.
- **L1D: NOT cleanly confirmed this pass, due to the anomaly above.** The noisy small-size
  region only loosely resembles a plateau (7.2-9.9 ticks, no sharp edge) before a real,
  unambiguous climb resumes at 60,096 B (10.47) -- **best-guess: 32,768 B**, matching the
  frozen prediction and every other x86 Hazel/lab machine, but this run's own data cannot
  independently confirm it the way skylake's or cascadelake's L1 could.
- **L2: NOT resolved.** The climb from 60,096 B through 9,147,840 B (10.47 -> 132.71) is one
  continuous ramp with no distinct flat shelf -- the auto-detector's first 4 boundaries
  (1,143,480 / 1,359,832 / 1,617,120 / 2,493,944 B) are fragments of this one ramp, the same
  "one continuous transition triggering multiple spurious boundary detections" pattern
  documented elsewhere in this project. **L2 best-guess: 1,310,720 B (1.25 MiB)** -- Ice
  Lake-SP's publicly known standard per-core L2 size across the Xeon Scalable 3rd-gen lineup
  (same "generation-typical value" reasoning as every other machine's unresolved L2).
- **LLC: well-confirmed at 25,874,000 B (~24.68 MiB) -- a genuinely sharp knee, once read
  starting from the anomaly's own recovery point.** From 9,975,792 B onward (past the drop),
  the curve is a FLAT, clean shelf: 65.98 -> 59.38 -> 60.17 -> 60.23 -> 60.97 -> 61.13 -> 61.25
  -> 61.88 -> 62.43 -> 62.36 -> 64.29 ticks across 9,975,792-23,726,560 B (barely any drift
  across a 2.4x size range) -- then a sharp, sustained departure starting at 25,874,000 B
  (71.50), continuing 28,215,800 B -> 91.08, 30,769,544 B -> 108.54, 33,554,432 B -> 122.79.
  This matches Xeon Gold 6326's own publicly documented 24 MB L3 almost exactly (24.68 MiB
  measured vs. 24 MB spec) -- as clean a knee as skylake's own confirmed LLC edge.
- **LLC-to-DRAM: confirmed plateau within the default tail extension** -- 67,108,864 B: 219.32,
  117,860,080 B: 246.27, 210,002,800 B: 235.74, 268,435,456 B: 251.57 -- flat within ~15% noise
  across the whole 4x tail range, no further manual extension needed (unlike haswell/skylake).
- **Held-out comparison against the frozen prediction:** the frozen L1D prediction
  (32,768 B / 8-way) is consistent with this run's best-guess L1D, though not independently
  confirmed here due to the anomaly. No frozen LLC prediction exists for an Ice Lake-SP
  generation.

### line_size/
- Source file(s): 
- Build command: 
- Run command + arguments: 
- Sample count: 
- Notes on alignment/candidate strides tested: 

### associativity/
- Slurm job ID: 838349 (resubmit of 838190, which failed on the same non-4096-aligned LLC
  value as skylake's own; 25,874,000 B rounded to 25,874,432 B for this experiment's own
  `--cache-bytes` argument only), logical CPU 16, elapsed 36s, exit 0.
- Source file(s): `main_code/common/associativity.{c,h}`,
  `scripts/run_associativity_full.sh` (`HAZEL_MODE=1`), `scripts/detect_associativity.py`,
  `scripts/plot_associativity.py`
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_associativity_full.sh
  hazel_icelake_6326 16 32768,1310720,25874432` (base_seed=12345, repeats at seed+1/seed+2,
  max_ways=40, 1,000,000 samples/point)
- Conflict-set construction method: node-to-node stride fixed at each level's own capacity
  candidate (standard method).
- **Notes / results: L1=9 (fully reproducible), L2=12 (fully reproducible), L3_LLC=9 base
  but 12/12 on both repeats (flagged disagreement -- do NOT treat as resolved).** None of
  these are citable numbers, and this machine gives an unusually clean arithmetic argument
  for why: **L1's own reported "9" is not even physically possible for a 32,768 B cache with
  64 B lines** -- 32,768/64=512 total lines, and 512/9=56.89, not a whole number of sets. A
  real hardware cache cannot have a non-integer set count -- this is direct, timing-and-
  arithmetic-only proof (no hardware lookup needed) that the "9" reported here is a
  measurement artifact, not this machine's real L1 associativity (independently expected to
  be 8, per the frozen prediction and every other x86 Hazel/lab machine's own confirmed L1).
  L2's "12" (sets=1706.67) and LLC's own two competing values (9: sets=44920.89; 12:
  sets=33690.67) are both arithmetically invalid too. **This is the first Hazel machine where
  even the L1 read fails a basic physical-consistency check**, consistent with this machine's
  own already-documented capacity anomaly (a sharp, unexplained ~2x latency drop) -- read as
  further evidence this machine's timing environment was disturbed for this whole session,
  not just the one capacity run.

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
