# hazel_skylake — Reproduction Manifest

> Fill in every field before freezing results. This README must let a grader go from
> this folder to the exact command that generated the data without guessing.

## Machine Identification
- Hostname: `c050n01` (allocated by Slurm for `--constraint=skylake`, job 833552)
- CPU model (from `lscpu`/`/proc/cpuinfo`): `Intel(R) Xeon(R) Gold 6130 CPU @ 2.10GHz` -- matches NC State's documented
  `skylake` constraint mapping (see PREDICTION_FREEZE.md/assignment Table 4).
- ISA / architecture: x86-64 (`uname -a`: `x86_64 x86_64 x86_64 GNU/Linux`)
- Vendor / microarchitecture / codename (researched, NOT from cache tables): Intel Skylake-SP (Skylake, 1st Gen Xeon Scalable)
- Introduction year (per the team's stated year convention): 2017
- Process node (if reliably documented): 14 nm
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
833552, elapsed 39s, exit code 0. Full stdout/stderr: `hw1_skylake_833552.log` /
`hw1_skylake_833552.err.log` (committed alongside this README; `.log` suffix used instead of
Slurm's default `.out` because this repo's `.gitignore` blanket-ignores `*.out`). The job built
`cache_bench` cleanly (in an isolated per-job directory, `hazel_build/833552/`, to avoid
races with sibling generations' jobs building concurrently in this same shared GPFS checkout --
see `hpc_slurm/hw1_skylake.sh`'s header) and ran one tiny (`--samples 1000`, 4096-65536 B)
`--experiment capacity` smoke test under `srun --cpu-bind=cores` to confirm the binary runs
correctly bound to a real core on Hazel -- this is NOT the 1,000,000-sample suite required for
the actual capacity/line_size/associativity/latency/inclusion_policy experiments, which are run
by a separate `hw1_skylake_<experiment>.sh` job script per experiment type (see
`hpc_slurm/README.md`).

## Per-Experiment Reproduction

### capacity/
- Slurm job ID: 837630, hostname (see job log), logical CPU 16, elapsed 53m13s, exit 0.
- Source file(s): `main_code/common/{main.c,benchmark.c,pointer_chase.c,random.c,capacity.c}`,
  `scripts/run_capacity_full.sh` (`HAZEL_MODE=1`), `scripts/summarize_raw.py`,
  `scripts/detect_cache_hierarchy.py`, `scripts/plot_capacity.py`
- Build command: `make -s` (isolated per-job copy under `hazel_build/837630/`, cleaned up on
  job exit)
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_capacity_full.sh hazel_skylake 16`
  (coarse_max defaulted to 67,108,864 B / 64 MiB, then a 4x tail extension to 256 MiB)
- Sample count: 1,000,000 (timed; warm-up excluded) -- every stage
- Random seed(s): base 12345; reproducibility repeats on the deepest boundary use the same
  seed (this script's own known limitation)
- Raw output filename(s):
  `data_raw/hazel_skylake/capacity/capacity_{coarse,coarse_ext,dense0..dense3,dense3_rep1,
  dense3_rep2,denseTail}_{random,sequential}_20260915T010343Z.csv.gz`; full transcript:
  `data_raw/hazel_skylake/capacity/run_capacity_full_20260915T010343Z.log`
- Processing script -> data_processed path: `scripts/summarize_raw.py` ->
  `data_processed/hazel_skylake/capacity/*_summary.csv`;
  `scripts/detect_cache_hierarchy.py` (default thresholds) -> 4 candidate boundaries (see
  Findings); `scripts/plot_capacity.py` ->
  `data_processed/hazel_skylake/capacity/plots/capacity_{curve,boxplots}.{png,pdf}`
- Excluded runs (if any) and reason: none -- single complete run, no repeats discarded.

**Findings (timing-only; no vendor/cache-topology lookup used, per Phase I discipline). This
is the cleanest capacity curve of any Hazel generation run so far -- both boundaries below are
confirmed by an actual sharp knee, not a best-guess pick from a noisy/continuous ramp:**
- **L1D: well-confirmed at 32,768 B (32 KiB).** Flat ~4.77-4.80 ticks/access from 1,216 B
  through 30,048 B, then a clean, sustained climb starting at 32,768 B itself (4.92, already
  departing) and clearly climbing by the next point, 35,728 B (5.32) -- matches the frozen
  prediction's L1D=32,768 B exactly.
- **L2: a genuine (if not perfectly sharp) transition region, 512 KiB-2 MiB, distinct from
  both L1's plateau below and a second, much flatter shelf above.** Latency climbs steadily
  from 524,288 B (12.19) through 1,923,096 B (32.14), then the growth rate drops sharply --
  2,097,152 B (29.61, actually a slight DIP) through 21,757,352 B (46.20) is a comparatively
  flat, slow-climbing shelf (only +56% across a 10x size range, vs. +78% across less than 2x
  in the transition just below it) -- read as the genuine LLC-resident plateau, not still-L2.
  **L2 best-guess: 1,048,576 B (1 MiB)** -- sits inside the observed 512 KiB-2 MiB transition
  region at the architecturally-standard per-core L2 size for Skylake-SP (same reasoning
  category as haswell's/cascadelake's own L2 best-guesses), not an independently sharp knee.
- **LLC: well-confirmed at 23,726,560 B (~22.6 MiB) -- a genuinely sharp, clean knee, the
  cleanest LLC edge of any Hazel generation so far.** The shelf above holds flat through
  21,757,352 B (46.20), then the very next tested point, 23,726,560 B, already departs (50.03),
  followed by a sharp, sustained acceleration: 25,874,000 B -> 65.93, 28,215,800 B -> 78.44,
  30,769,544 B -> 89.85, 33,554,432 B -> 102.69. This is a real inflection, not a noise
  artifact -- the auto-detector's own 2 boundaries in this region (23,726,560 / 30,769,544 B)
  bracket exactly this one clean transition.
- **LLC-to-DRAM: does NOT fully plateau within the default tail extension (up to 256 MiB) --
  same open item as haswell.** Medians keep climbing through the whole tail: 67,108,864 B ->
  145.47, 136,169,968 B -> 170.39, 181,765,096 B -> 181.80, 268,435,456 B -> 182.53 -- still
  rising, though the rate has clearly slowed (roughly +26% total across the last 4x of the
  range vs. the sharp +180% climb from 21.7 to 33.5 MiB). A further manual extension past
  256 MiB (mirroring every lab machine's own capacity/ follow-up) would be needed to find the
  true DRAM floor -- not attempted this pass.
- **Held-out comparison against the frozen prediction:** the frozen L1D prediction
  (32,768 B / 8-way, Chen-Ngo Invariance Law) matches this run's timing-derived L1D capacity
  exactly. No frozen LLC prediction exists specifically for a Skylake-SP generation
  (`PREDICTION_FREEZE.md` covers only the 8 lab machines).
- Run command + arguments: 
- Sample count: 1,000,000 (timed; warm-up excluded)
- Random seed(s): 
- Raw output filename(s): 
- Processing script -> data_processed path: 
- Excluded runs (if any) and reason: 

### line_size/
- Slurm job ID: 838181, elapsed (see log), exit 0.
- Source file(s): `main_code/common/line_size.{c,h}`, `scripts/run_line_size.sh`
  (`HAZEL_MODE=1`), `scripts/detect_line_size.py`, `scripts/plot_line_size*.py`
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_line_size.sh hazel_skylake 16
  32768,1048576,23726560` (default coarse strides 8,16,32,64,128,256; no
  `candidate_overrides_csv`, so Method A step 4 was skipped at every level)
- Sample count: 1,000,000 (timed; warm-up excluded), seed=12345
- **Inconclusive -- Method B found no transition at any of the 3 levels** (`-- detected
  line-size estimate (bytes): none --` at L1/L2/LLC). No citable value from this run at all.
  **Best-guess: 64 B** (matching the frozen prediction and every other x86 machine so far),
  unconfirmed by this machine's own data.

### associativity/
- Slurm job ID: 838348 (resubmit of 838182, which failed with "Invalid associativity
  parameter values (--cache-bytes must be a multiple of 4096)" -- the reasoned LLC edge,
  23,726,560 B, wasn't page-aligned; rounded to 23,728,128 B for this experiment's own
  `--cache-bytes` argument only, see `hpc_slurm/hw1_skylake_associativity.sh`'s own note),
  logical CPU 16, elapsed 50s, exit 0.
- Source file(s): `main_code/common/associativity.{c,h}`,
  `scripts/run_associativity_full.sh` (`HAZEL_MODE=1`), `scripts/detect_associativity.py`,
  `scripts/plot_associativity.py`
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_associativity_full.sh hazel_skylake 16
  32768,1048576,23728128` (explicit `cache_bytes_csv`, base_seed=12345, repeats at
  seed+1/seed+2, max_ways=40, 1,000,000 samples/point)
- Conflict-set construction method: node-to-node stride fixed at each level's own capacity
  candidate, forcing every probed node into the same cache set (standard method).
- **Notes / results: L1=8, L2=8, L3_LLC=8 -- all three fully reproducible (base + both
  repeats agree exactly).** L1=8-way matches the frozen prediction and is arithmetically
  valid (32,768 B / 64 B lines / 8-way = 64 sets, a clean integer). **L2 and L3_LLC's
  identical "8" is the same cross-machine DTLB-scale confound extensively documented in
  `CLAUDE.md`'s associativity section** -- do not cite either as this machine's real L2/LLC
  associativity (both values are also arithmetically "valid" in isolation, since 8 divides
  the page-line-count 64 evenly regardless of scale, so the integer-sets check alone can't
  rule them out here the way it can on other machines below -- the cross-level identity with
  L1 is the load-bearing evidence, not the arithmetic).

### latency/
**hit_latency (Slurm job 838183, exit 0):**
- Source file(s): `main_code/common/latency.{c,h}`, `scripts/run_hit_latency_full.sh`
  (`HAZEL_MODE=1`), `scripts/plot_hit_latency.py`
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_hit_latency_full.sh hazel_skylake 16
  L1:32768,L2:1048576,LLC:23726560,DRAM:536870912` (base_seed=12345, 2 repeats, 1,000,000
  samples/point, batch_size=1000)
- Dependent-chain batch size N used: 1,000
- Regular vs. randomized control included? Yes -- both load modes, both patterns, every
  level. No `[UNEXPECTED]` flags -- independent read faster than dependent everywhere.
- **Results (dependent, random, base-run median, ticks/access): L1=9.54, L2=17.41,
  LLC=152.41, DRAM=194.99** -- a clean, monotonic 4-tier ladder, and unlike hazel_cascadelake's
  own result, LLC and DRAM are well-separated here (~28% apart), consistent with this
  machine's independently-confirmed (not best-guess) LLC boundary.

**miss_latency: pending as of this writing.**

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
