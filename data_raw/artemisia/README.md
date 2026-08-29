# artemisia — Reproduction Manifest

> Fill in every field before freezing results. This README must let a grader go from
> this folder to the exact command that generated the data without guessing.

## Machine Identification
- Hostname: 
- CPU model (from `lscpu`/`/proc/cpuinfo`): 
- ISA / architecture: 
- Vendor / microarchitecture / codename (researched, NOT from cache tables): 
- Introduction year (per the team's stated year convention): 
- Process node (if reliably documented): 
- Kernel version: 
- Page size: 
- SMT siblings idle during runs? 

## Environment
- Compiler + version: 
- Compiler flags: `-O0 -g -std=c11 -Wall -Wextra -fno-omit-frame-pointer`
- Timer method used (RDTSC/RDTSCP+LFENCE, CNTVCT_EL0, etc.): 
- Affinity/binding command used: 
- NUMA/locality method: 
- Git commit hash of the code used for these results: 

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
