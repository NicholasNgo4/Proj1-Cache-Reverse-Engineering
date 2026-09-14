# hazel_haswell — Reproduction Manifest

> Fill in every field before freezing results. This README must let a grader go from
> this folder to the exact command that generated the data without guessing.

## Machine Identification
- Hostname: `c207n02` (allocated by Slurm for `--constraint=haswell`, job 833461)
- CPU model (from `lscpu`/`/proc/cpuinfo`): `Intel(R) Xeon(R) CPU E5-2650 v3 @ 2.30GHz` --
  matches NC State's documented `haswell` constraint mapping (Intel Xeon E5 v3), and is the
  same family as Sunbird's own lab machine (Xeon E5-2680 v3), a different SKU in the same
  v3 generation.
- ISA / architecture: x86-64 (`uname -a`: `x86_64 x86_64 x86_64 GNU/Linux`)
- Vendor / microarchitecture / codename (researched, NOT from cache tables): Intel Haswell-EP
  (server), per the public Xeon E5-2650 v3 product naming -- not read from any cache-topology
  command.
- Introduction year (per the team's stated year convention): 2014 (Haswell-EP launch, same
  generation year the team already uses for Sunbird's own Xeon E5-2680 v3)
- Process node (if reliably documented): 22 nm (Haswell family, same as Sunbird's row in
  `CHRONOLOGICAL_MASTER_TABLE.md` -- not independently verified on this specific SKU this pass)
- Kernel version: `5.14.0-611.5.1.el9_7.x86_64` (`uname -a`)
- Page size: 4096 bytes (standard x86-64; also the alignment `main_code/common/main.c`'s
  `ASSOC_CACHE_BYTES_ALIGN` already assumes)
- SMT siblings idle during runs? This access-check job requested 1 CPU
  (`--cpus-per-task=1`); Slurm bound it to logical CPU 10 (`physcpubind: 10`, socket 1, NUMA
  node 1) via `--cpu-bind=cores`. Sibling-thread idleness not independently checked this pass
  (no full-suite timing run yet to require it) -- see the pending Environment note below.

## Environment
- Compiler + version: `gcc (GCC) 11.5.0 20240719 (Red Hat 11.5.0-11)` (system gcc on the
  allocated compute node, confirmed via the job's own `gcc --version` -- not just the login
  node's)
- Compiler flags: `-O0 -g -std=c11 -Wall -Wextra -fno-omit-frame-pointer`
- Timer method used (RDTSC/RDTSCP+LFENCE, CNTVCT_EL0, etc.): RDTSC-family (x86-64), same
  `main_code/x86_64/timer_x86.h` used on every x86 lab machine -- not yet independently
  sanity-checked on this specific node (pending the full-suite pass).
- Affinity/binding command used: `srun --cpu-bind=cores` (NOT `taskset` -- that is the lab
  machines' pinning method only; see `scripts/run_capacity_sweep.sh`'s header comment).
  Resulting binding per the job's own `numactl -s` output: `physcpubind: 10`, `cpubind: 1`,
  `nodebind: 1`, `membind: 0 1`.
- NUMA/locality method: `numactl -s` (available on the compute node) plus
  `lscpu -e=CPU,CORE,SOCKET,NODE` (both on the Phase Discipline whitelist) -- logical CPU 10 is
  physical core 10, socket 1, NUMA node 1 on this node.
- Git commit hash of the code used for these results: `b4bf2a3851988965442b06cedf6d272da94b7248`
  (the `predictions-frozen` tag itself -- this job's own gate check confirmed HEAD was tagged
  before running anything past the smoke test)

**Job record (this pass -- access/build check only, not the full suite):** Slurm job ID
833461, submitted 2026-09-14T14:25:38 UTC, started 14:25:53, completed 14:25:56 (elapsed 3s,
exit code 0). Full stdout/stderr: `hw1_haswell_833461.log` / `hw1_haswell_833461.err.log` (committed
alongside this README; renamed from Slurm's default `%x_%j.out`/`.err` naming because this
repo's `.gitignore` blanket-ignores `*.out` -- `hpc_slurm/hw1_haswell.sh`'s `#SBATCH --output`/
`--error` directives now write directly into `data_raw/hazel_haswell/` with a `.log` suffix). The job built `cache_bench` cleanly and ran one tiny (`--samples 1000`,
4096-65536 B) `--experiment capacity` smoke test under `srun --cpu-bind=cores` to confirm the
binary runs correctly bound to a real core on Hazel -- this is NOT the 1,000,000-sample suite
required for the actual capacity/line_size/associativity/latency/inclusion_policy experiments,
which have not run on this machine yet (see `hpc_slurm/hw1_haswell.sh`'s own header for the
Phase-Discipline gate that will permit that next).

## Per-Experiment Reproduction

### capacity/
- Source file(s): 
- Build command: 
- Run command + arguments: 
- Sample count: 1,000,000 (timed; warm-up excluded)
- Random seed(s): 
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
- Source file(s): 
- Run command + arguments: 
- Conflict-set construction method: 
- Notes: 

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
