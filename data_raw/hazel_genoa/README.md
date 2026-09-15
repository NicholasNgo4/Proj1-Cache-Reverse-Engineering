# hazel_genoa — Reproduction Manifest

> Fill in every field before freezing results. This README must let a grader go from
> this folder to the exact command that generated the data without guessing.

## Machine Identification
- Hostname: `n0398` (allocated by Slurm for `--constraint=genoa`, job 833557)
- CPU model (from `lscpu`/`/proc/cpuinfo`): `AMD EPYC 9654 96-Core Processor` -- matches NC State's documented
  `genoa` constraint mapping (see PREDICTION_FREEZE.md/assignment Table 4).
- ISA / architecture: x86-64 (`uname -a`: `x86_64 x86_64 x86_64 GNU/Linux`)
- Vendor / microarchitecture / codename (researched, NOT from cache tables): AMD Zen 4 (EPYC 9004 'Genoa')
- Introduction year (per the team's stated year convention): 2022
- Process node (if reliably documented): TSMC 5 nm
- Kernel version: `5.14.0-611.5.1.el9_7.x86_64`
- Page size: 4096 bytes (standard x86-64)
- SMT siblings idle during runs? This access-check job requested 1 CPU
  (`--cpus-per-task=1`); Slurm bound it to logical CPU 96 (socket 1, NUMA
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
  Resulting binding: `physcpubind: 96`, socket 1, NUMA node 1
  (via `numactl -s`).
- NUMA/locality method: `numactl -s` plus `lscpu -e=CPU,CORE,SOCKET,NODE` (both on the Phase
  Discipline whitelist) -- logical CPU 96 is socket 1, NUMA node 1 on this node.
- Git commit hash of the code used for these results: `cb7e0c8c82c0269507e665db04563dee78fda9a6` (the `predictions-frozen`
  tag's own commit is an ancestor of this HEAD -- confirmed by this job's own gate check
  before running anything past the smoke test)

**Job record (this pass -- access/build check only, not the full suite):** Slurm job ID
833557, elapsed 16s, exit code 0. Full stdout/stderr: `hw1_genoa_833557.log` /
`hw1_genoa_833557.err.log` (committed alongside this README; `.log` suffix used instead of
Slurm's default `.out` because this repo's `.gitignore` blanket-ignores `*.out`). The job built
`cache_bench` cleanly (in an isolated per-job directory, `hazel_build/833557/`, to avoid
races with sibling generations' jobs building concurrently in this same shared GPFS checkout --
see `hpc_slurm/hw1_genoa.sh`'s header) and ran one tiny (`--samples 1000`, 4096-65536 B)
`--experiment capacity` smoke test under `srun --cpu-bind=cores` to confirm the binary runs
correctly bound to a real core on Hazel -- this is NOT the 1,000,000-sample suite required for
the actual capacity/line_size/associativity/latency/inclusion_policy experiments, which are run
by a separate `hw1_genoa_<experiment>.sh` job script per experiment type (see
`hpc_slurm/README.md`).

## Per-Experiment Reproduction

### capacity/
- Slurm job ID: 837635, logical CPU 96, elapsed 1h12m26s, exit 0.
- Source file(s): `main_code/common/{main.c,benchmark.c,pointer_chase.c,random.c,capacity.c}`,
  `scripts/run_capacity_full.sh` (`HAZEL_MODE=1`), `scripts/summarize_raw.py`,
  `scripts/detect_cache_hierarchy.py`, `scripts/plot_capacity.py`
- Build command: `make -s` (isolated per-job copy under `hazel_build/837635/`, cleaned up on
  job exit)
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_capacity_full.sh hazel_genoa 96`
  (coarse_max defaulted to 67,108,864 B / 64 MiB, then a 4x tail extension to 256 MiB)
- Sample count: 1,000,000 (timed; warm-up excluded) -- every stage
- Random seed(s): base 12345; reproducibility repeats on the deepest boundary use the same
  seed (this script's own known limitation)
- Raw output filename(s):
  `data_raw/hazel_genoa/capacity/capacity_{coarse,coarse_ext,dense0,dense1,dense1_rep1,
  dense1_rep2,denseTail}_{random,sequential}_20260915T010343Z.csv.gz`; full transcript:
  `data_raw/hazel_genoa/capacity/run_capacity_full_20260915T010343Z.log`
- Processing script -> data_processed path: `scripts/summarize_raw.py` ->
  `data_processed/hazel_genoa/capacity/*_summary.csv`; `scripts/detect_cache_hierarchy.py`
  (default thresholds) -> only 2 candidate boundaries this time (see Findings) --
  notably fewer spurious detections than every Intel Hazel generation run so far, consistent
  with this being the smoothest/least-noisy curve of any generation processed this session;
  `scripts/plot_capacity.py` ->
  `data_processed/hazel_genoa/capacity/plots/capacity_{curve,boxplots}.{png,pdf}`
- Excluded runs (if any) and reason: none -- single complete run, no anomalies of the kind
  seen on icelake_6326/sapphirerapids.

**Findings (timing-only; no vendor/cache-topology lookup used, per Phase I discipline).
CPU: AMD EPYC 9654 (Genoa, Zen 4) -- the first AMD/Zen generation run on Hazel, and this
project's AMD-generation requirement for the assignment's minimum-5 spanning set.**
- **L1D: well-confirmed at 32,768 B (32 KiB).** Flat ~7.15-7.22 ticks/access from 1,024 B
  through 30,048 B, then a clean, sustained climb starting at 32,768 B (7.51, already
  departing) and unambiguous by 35,728 B (8.42) -- matches the frozen prediction's
  L1D=32,768 B exactly, and the same 32 KiB every other x86 generation in this project has
  shown (Zen 4 did not change L1D size from earlier Zen generations).
- **L2: NOT cleanly resolved -- one long, continuous ramp from the L1 edge all the way to
  ~30 MiB, no distinct shelf.** Climbs steadily and without a flat region from 35,728 B (8.42)
  through 30,769,544 B (90.89) -- neither auto-detected boundary falls in the expected
  ~1 MiB L2 region at all (both land much deeper, see LLC below), meaning this run's
  auto-detector didn't even produce a spurious L2-region candidate to second-guess this time.
  **L2 best-guess: 1,048,576 B (1 MiB)** -- Zen 4's publicly known standard per-core L2 size
  (doubled from Zen 3's 512 KiB), the same "generation-typical value" reasoning used for every
  other machine's unresolved L2.
- **LLC: well-confirmed at 33,554,432 B (32 MiB) -- a clean, sharp acceleration, and this
  round byte value is not a coincidence.** The climb's growth rate visibly steps up exactly at
  this point: 30,769,544 B -> 90.89, 33,554,432 B -> 96.05 (modest), then 36,591,368 B ->
  113.50 (+18.2%, a real inflection), 39,903,168 B -> 127.42, 43,514,712 B -> 141.82,
  47,453,128 B -> 154.51 -- a sustained, accelerating climb from here on. 33,554,432 B is
  EXACTLY 32 MiB, matching AMD Genoa's publicly documented per-CCD L3 size (32 MB shared
  across each 8-core CCD on this 96-core, 12-CCD part) almost too precisely to be
  coincidental -- the cleanest LLC-to-known-architecture match of any Hazel generation so far.
- **LLC-to-DRAM: does NOT plateau within the tested range (up to 268 MiB) -- same open item
  as haswell/skylake/sapphirerapids.** The tail extension keeps climbing throughout:
  94,906,256 B -> 239.42, 166,679,312 B -> 276.47, 222,490,192 B -> 289.99, 268,435,424 B ->
  296.81 -- still rising (~24% total across that range), no flattening. A further manual
  extension past 256 MiB would be needed to find the true DRAM floor -- not attempted this
  pass.
- **Held-out comparison against the frozen prediction:** the frozen L1D prediction
  (32,768 B / 8-way, Chen-Ngo Invariance Law -- derived from Intel lab machines) matches this
  AMD/Zen 4 machine's L1D capacity exactly, a useful cross-architecture data point for that
  law's generality. No frozen LLC prediction exists for a Genoa/Zen 4 generation.
- Raw output filename(s): 
- Processing script -> data_processed path: 
- Excluded runs (if any) and reason: 

### line_size/
- Source file(s): 
- Build command: 
- Run command + arguments: 
- Sample count: 
- Notes on alignment/candidate strides tested: 

### associativity/
- Slurm job ID: 838202, logical CPU 97, elapsed 40s, exit 0.
- Source file(s): `main_code/common/associativity.{c,h}`,
  `scripts/run_associativity_full.sh` (`HAZEL_MODE=1`), `scripts/detect_associativity.py`,
  `scripts/plot_associativity.py`
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_associativity_full.sh hazel_genoa 97
  32768,1048576,33554432` (base_seed=12345, repeats at seed+1/seed+2, max_ways=40,
  1,000,000 samples/point)
- Conflict-set construction method: node-to-node stride fixed at each level's own capacity
  candidate (standard method).
- **Notes / results: L1=9 (fully reproducible), L2=9 (fully reproducible), L3_LLC=9 base,
  9/8 on repeats (flagged disagreement).** Unlike every other x86 Hazel/lab machine's own
  clean L1=8-way, **this machine's L1 reads 9 -- and the arithmetic-consistency check rules
  it out as genuine**: 32,768 B / 64 B-lines / 9-way = 56.89 sets, not a whole number, so a
  real L1D cannot actually have this associativity at this capacity. This is the first AMD/
  Zen 4 machine to show the same "L1 itself fails the integer-sets check" symptom already
  seen on several Intel Hazel machines (icelake_6326/icelake_8358/turin) -- read as further,
  cross-vendor evidence that whatever structure produces this confound is not
  Intel-microarchitecture-specific. L2's identical "9" (sets=1820.44) and LLC's own two
  disagreeing values (9: sets=58254.22; the rep2 alternative, 8: sets=65536.00 -- notably
  the ONLY arithmetically valid number among the four LLC-level readings across base+2
  repeats) both point the same direction: whatever real L1D/L2/LLC associativities this
  machine has, this run's own data cannot resolve them -- the cross-machine DTLB-scale
  confound documented in `CLAUDE.md` is the more likely explanation for every level here,
  not a genuine measurement.

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
