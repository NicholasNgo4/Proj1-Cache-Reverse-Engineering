# Hazel Slurm Job Log — Machine Identification per Job

Consolidated record of every Slurm compute job used to collect Phase I data on NC State's
Hazel cluster (`login02.hpc.ncsu.edu`), across all 9 Table-4 generations
(haswell/broadwell/cascadelake/icelake_6326/icelake_8358/sapphirerapids/skylake/genoa/turin).
Compiled 2026-09-16 by reading each job's own committed `.log` file (the
`=== Machine identification (Phase Discipline whitelist only) ===` block every
`hpc_slurm/hw1_<gen>_<experiment>.sh` script writes at start-of-job: `hostname`, `uname -a`,
`/proc/cpuinfo` model name, a full `lscpu -e=CPU,CORE,SOCKET,NODE` table, and the actual
`srun --cpu-bind=cores` assignment) — **not** transcribed from each `data_raw/hazel_<gen>/
README.md`'s own prose summary, which in a few places is stale/wrong (see Corrections below).
Job logs live at `data_raw/hazel_<gen>/hw1_<gen>_<experiment>_<jobid>.log` (`.err.log` sibling
for stderr).

**Topology note**: every generation's own `lscpu -e` table shows `CORE == CPU` (no SMT
enabled on any of these allocations) with a clean socket/NUMA split at exactly half the
logical-CPU count — so physical core number equals logical CPU number directly, and which
half of the range a CPU falls in determines its socket/NUMA node. Per-generation split point
given in each table header below.

**Corrections against the per-machine READMEs' prose (found while cross-checking job logs
directly):**
- **Haswell hit_latency (job 834510)**: the README's `data_raw/hazel_haswell/README.md` says
  "logical CPU 14" — the job's own log shows `Assigned logical CPU: 10` (and the run
  command's own echoed `core=10`). The README is wrong; this file uses the log's value.
- **The script's positional "core" argument does not always match the real
  `srun --cpu-bind=cores` assignment.** `HAZEL_MODE=1` scripts take a `core` argument used
  for output-path/label bookkeeping, but the actual CPU affinity comes from Slurm/`srun`
  itself, which can differ — e.g. icelake_8358's hit_latency job was invoked with core-arg
  `34` but its own log shows it actually ran on logical CPU `61`; smaller such gaps also
  appear on cascadelake, sapphirerapids, skylake, and turin (see tables). The **log's**
  `Assigned logical CPU` is authoritative, not the run-command argument.
- **Node changed mid-generation in 3 cases**, despite identical CPU model/topology
  confirmed at each: icelake_8358 (`c059n02` pilot -> `c059n01` for every downstream job),
  skylake (`c050n01` pilot -> `c050n02` downstream), turin (`n0405` pilot/capacity ->
  `n0406` for associativity/hit_latency/miss_latency, back to `n0405` for inclusion_policy —
  both are legitimate Turin nodes per `CLAUDE.md`'s Hazel status note, not a decoy GPU-node).

Every job across all 9 generations landed on socket 1 / NUMA node 1 of its node, **except**
cascadelake's associativity/hit_latency/miss_latency/inclusion_policy jobs (logical CPUs 0-2,
socket 0 / NUMA 0).

---

## Broadwell — Intel Xeon E5-2650 v4 @ 2.20GHz (Broadwell-EP)
Topology: 24 logical CPUs, 0-11 = socket 0 / NUMA 0, 12-23 = socket 1 / NUMA 1.

| Phase | Job ID | Hostname | Logical CPU | Physical core | Socket | NUMA |
|---|---|---|---|---|---|---|
| access-check | 833551 | c205n04 | 13 | 13 | 1 | 1 |
| capacity | 837629 | c205n03 | 12 | 12 | 1 | 1 |
| line_size | 838232 | c205n10 | 12 | 12 | 1 | 1 |
| associativity | 838351 (resubmit of 838233) | c202n09 | 22 | 22 | 1 | 1 |
| hit_latency | 838234 | c205n14 | 12 | 12 | 1 | 1 |
| miss_latency | 838235 | c202n02 | 22 | 22 | 1 | 1 |
| inclusion_policy | 838236 | c202n02 | 21 | 21 | 1 | 1 |
| capacity relook (follow-up re-run) | 842708 | c205n07 | 22 | 22 | 1 | 1 |
| line_size relook (L3 follow-up re-run) | 839572 | c205n12 | 22 | 22 | 1 | 1 |

## Cascadelake — Intel Xeon Gold 6226R @ 2.90GHz (Cascade Lake-SP Refresh)
Topology: 32 logical CPUs, 0-15 = socket 0 / NUMA 0, 16-31 = socket 1 / NUMA 1.

| Phase | Job ID | Hostname | Logical CPU | Physical core | Socket | NUMA |
|---|---|---|---|---|---|---|
| access-check | 833553 | c020n01 | 29 | 29 | 1 | 1 |
| capacity | 837631 | c022n01 | 20 | 20 | 1 | 1 |
| line_size | 838064 | c021n03 | 24 | 24 | 1 | 1 |
| associativity | 838065 | c021n04 | 0 | 0 | 0 | 0 |
| hit_latency | 838066 | c021n04 | 1 | 1 | 0 | 0 |
| miss_latency | 838067 | c021n04 | 2 | 2 | 0 | 0 |
| inclusion_policy | 838068 | c021n04 | 2 | 2 | 0 | 0 |
| capacity relook (follow-up re-run) | 842709 | c021n01 | 16 | 16 | 1 | 1 |
| line_size relook (L3 follow-up re-run) | 839573 | c022n01 | 24 | 24 | 1 | 1 |

## Genoa — AMD EPYC 9654 (Zen 4)
Topology: 192 logical CPUs, 0-95 = socket 0 / NUMA 0, 96-191 = socket 1 / NUMA 1.

| Phase | Job ID | Hostname | Logical CPU | Physical core | Socket | NUMA |
|---|---|---|---|---|---|---|
| access-check | 833557 | n0398 | 96 | 96 | 1 | 1 |
| capacity | 837635 | n0398 | 96 | 96 | 1 | 1 |
| line_size | 838201 | n0398 | 96 | 96 | 1 | 1 |
| associativity | 838202 | n0398 | 97 | 97 | 1 | 1 |
| hit_latency | 838203 | n0398 | 98 | 98 | 1 | 1 |
| miss_latency | 838204 | n0398 | 99 | 99 | 1 | 1 |
| inclusion_policy | 838205 | n0398 | 96 | 96 | 1 | 1 |
| capacity relook (follow-up re-run) | 842714 | n0398 | 96 | 96 | 1 | 1 |
| line_size relook, run 1 (L2+L3 follow-up re-run) | 839574 | n0398 | 97 | 97 | 1 | 1 |
| line_size relook, run 2 (L2+L3 follow-up re-run) | 839813 | n0398 | 97 | 97 | 1 | 1 |

## Haswell — Intel Xeon E5-2650 v3 @ 2.30GHz (Haswell-EP)
Topology: 20 logical CPUs, 0-9 = socket 0 / NUMA 0, 10-19 = socket 1 / NUMA 1.

| Phase | Job ID | Hostname | Logical CPU | Physical core | Socket | NUMA |
|---|---|---|---|---|---|---|
| access-check | 833461 | c207n02 | 10 | 10 | 1 | 1 |
| capacity | 833680 | c207n01 | 10 | 10 | 1 | 1 |
| line_size | 834508 | c207n01 | 10 | 10 | 1 | 1 |
| line_size step 4 (offset-invariance follow-up) | 837261 | c207n08 | 10 | 10 | 1 | 1 |
| associativity | 834509 | c207n02 | 10 | 10 | 1 | 1 |
| hit_latency | 834510 | c207n03 | 10 (corrects README's "14") | 10 | 1 | 1 |
| miss_latency (timed out at 1h, killed mid-rep2) | 834511 | c207n05 | 14 | 14 | 1 | 1 |
| miss_latency (resubmit w/ 1h55m budget, succeeded) | 836433 | c207n08 | 10 | 10 | 1 | 1 |
| inclusion_policy | 836440 | c207n01 | 10 | 10 | 1 | 1 |
| capacity relook, run 1 (follow-up re-run) | 842707 | c207n05 | 10 | 10 | 1 | 1 |
| capacity relook, run 2 (`capacity_rerun2`) | 845905 | c207n01 | 14 | 14 | 1 | 1 |
| capacity relook, run 3 (`capacity_rerun3`) | 847895 | c207n01 | 16 | 16 | 1 | 1 |

## Icelake_6326 — Intel Xeon Gold 6326 @ 2.90GHz (Ice Lake-SP)
Topology: 32 logical CPUs, 0-15 = socket 0 / NUMA 0, 16-31 = socket 1 / NUMA 1.

| Phase | Job ID | Hostname | Logical CPU | Physical core | Socket | NUMA |
|---|---|---|---|---|---|---|
| access-check | 833554 | c060n02 | 16 | 16 | 1 | 1 |
| capacity | 837632 | c060n02 | 16 | 16 | 1 | 1 |
| line_size | 838189 | c060n02 | 16 | 16 | 1 | 1 |
| associativity | 838349 (resubmit of 838190) | c060n02 | 16 | 16 | 1 | 1 |
| hit_latency | 838191 | c060n02 | 18 | 18 | 1 | 1 |
| miss_latency | 838192 | c060n02 | 19 | 19 | 1 | 1 |
| inclusion_policy | 838193 | c060n02 | 16 | 16 | 1 | 1 |
| capacity relook (follow-up re-run) | 842711 | c060n02 | 16 | 16 | 1 | 1 |
| line_size relook (L3 follow-up re-run) | 839575 | c060n02 | 16 | 16 | 1 | 1 |

## Icelake_8358 — Intel Xeon Platinum 8358 @ 2.60GHz (Ice Lake-SP)
Topology: 64 logical CPUs, 0-31 = socket 0 / NUMA 0, 32-63 = socket 1 / NUMA 1.

| Phase | Job ID | Hostname | Logical CPU | Physical core | Socket | NUMA |
|---|---|---|---|---|---|---|
| access-check | 833555 | c059n02 | 56 | 56 | 1 | 1 |
| capacity | 837633 | c059n01 (different node than pilot) | 63 | 63 | 1 | 1 |
| line_size | 838211 | c059n01 | 32 | 32 | 1 | 1 |
| associativity | 838212 | c059n01 | 34 | 34 | 1 | 1 |
| hit_latency | 838213 | c059n01 | 61 | 61 | 1 | 1 |
| miss_latency | 838214 | c059n01 | 62 | 62 | 1 | 1 |
| inclusion_policy | 838215 | c059n01 | 46 | 46 | 1 | 1 |
| capacity relook, run 1 (follow-up re-run) | 842712 | c059n01 | 33 | 33 | 1 | 1 |
| capacity relook, run 2 (`capacity_rerun2`) | 845906 | c059n04 (different node) | 56 | 56 | 1 | 1 |
| capacity relook, run 3 (`capacity_rerun3`) | 847896 | c059n04 | 56 | 56 | 1 | 1 |
| line_size relook, run 1 (L2+L3 follow-up re-run) | 839576 | c059n01 | 34 | 34 | 1 | 1 |
| line_size relook, run 2 (L2+L3 follow-up re-run) | 839814 | c059n01 | 34 | 34 | 1 | 1 |

## Sapphirerapids — Intel Xeon Platinum 8462Y+ (Sapphire Rapids)
Topology: 64 logical CPUs, 0-31 = socket 0 / NUMA 0, 32-63 = socket 1 / NUMA 1.

| Phase | Job ID | Hostname | Logical CPU | Physical core | Socket | NUMA |
|---|---|---|---|---|---|---|
| access-check | 833556 | n0407 | 32 | 32 | 1 | 1 |
| capacity | 837634 | n0407 | 40 | 40 | 1 | 1 |
| line_size | 838196 | n0407 | 40 | 40 | 1 | 1 |
| associativity | 838350 (resubmit of 838197) | n0407 | 40 | 40 | 1 | 1 |
| hit_latency | 838198 | n0407 | 42 | 42 | 1 | 1 |
| miss_latency | 838199 | n0407 | 43 | 43 | 1 | 1 |
| inclusion_policy | 838200 | n0407 | 40 | 40 | 1 | 1 |
| capacity relook (follow-up re-run) | 842713 | n0407 | 40 | 40 | 1 | 1 |
| line_size relook, run 1 (L2+L3 follow-up re-run) | 839577 | n0407 | 40 | 40 | 1 | 1 |
| line_size relook, run 2 (L2+L3 follow-up re-run) | 839815 | n0407 | 40 | 40 | 1 | 1 |

## Skylake — Intel Xeon Gold 6130 @ 2.10GHz (Skylake-SP)
Topology: 32 logical CPUs, 0-15 = socket 0 / NUMA 0, 16-31 = socket 1 / NUMA 1.

| Phase | Job ID | Hostname | Logical CPU | Physical core | Socket | NUMA |
|---|---|---|---|---|---|---|
| access-check | 833552 | c050n01 | 16 | 16 | 1 | 1 |
| capacity | 837630 | c050n02 (different node than pilot) | 16 | 16 | 1 | 1 |
| line_size | 838181 | c050n02 | 16 | 16 | 1 | 1 |
| associativity | 838348 (resubmit of 838182) | c050n02 | 16 | 16 | 1 | 1 |
| hit_latency | 838183 | c050n02 | 18 | 18 | 1 | 1 |
| miss_latency | 838184 | c050n02 | 19 | 19 | 1 | 1 |
| inclusion_policy | 838185 | c050n02 | 16 | 16 | 1 | 1 |
| capacity relook (follow-up re-run) | 842710 | c051n03 (different node) | 16 | 16 | 1 | 1 |
| line_size relook (L3 follow-up re-run) | 839578 | c050n02 | 16 | 16 | 1 | 1 |

## Turin — AMD EPYC 9655 (Zen 5)
Topology: 192 logical CPUs, 0-95 = socket 0 / NUMA 0, 96-191 = socket 1 / NUMA 1.

| Phase | Job ID | Hostname | Logical CPU | Physical core | Socket | NUMA |
|---|---|---|---|---|---|---|
| access-check | 833558 | n0405 | 128 | 128 | 1 | 1 |
| capacity | 837636 | n0405 (confirmed correct Turin node, not a `gpu35-39` decoy) | 160 | 160 | 1 | 1 |
| line_size | 838244 | n0405 | 160 | 160 | 1 | 1 |
| associativity | 838245 | n0406 (different node) | 144 | 144 | 1 | 1 |
| hit_latency | 838246 | n0406 | 144 | 144 | 1 | 1 |
| miss_latency | 838247 | n0406 | 144 | 144 | 1 | 1 |
| inclusion_policy | 838248 | n0405 | 168 | 168 | 1 | 1 |
| capacity relook (follow-up re-run) | 842715 | n0406 (different node) | 128 | 128 | 1 | 1 |
| line_size relook, run 1 (L2+L3 follow-up re-run) | 839579 | n0405 | 144 | 144 | 1 | 1 |
| line_size relook, run 2 (L2+L3 follow-up re-run) | 839816 | n0406 (different node) | 144 | 144 | 1 | 1 |

---

## Scope note

This log covers the original Phase I job sequence per generation (access-check pilot through
capacity/line_size/associativity/hit_latency/miss_latency/inclusion_policy, including the
resubmits/follow-ups needed to get a clean run — line_size step 4 and the miss_latency
timeout resubmit on haswell, and the 4 associativity resubmits elsewhere that hit the
non-4096-aligned `--cache-bytes` bug) **plus every `capacity_relook`/`capacity_rerun{,2,3}`/
`line_size_relook`/`line_size_rerun` follow-up job** (the jobs behind each machine's own
README "Follow-up re-run (2026-09-15)" note under capacity/ or line_size/ — haswell and
icelake_8358 needed 3 capacity relook attempts each, `capacity_rerun2`/`capacity_rerun3`;
genoa/icelake_8358/sapphirerapids/turin needed 2 line_size relook runs each, since both their
L2 and L3 levels were flagged for re-checking rather than just L3).

It does **not** yet cover the newer `_v2`/`phase1_v2` job sequence (job IDs in the 848xxx
range, present in `data_raw/hazel_{broadwell,cascadelake,icelake_6326,sapphirerapids,
skylake}/hw1_<gen>_<experiment>_v2_<jobid>.log` and `data_raw/hazel_<gen>/phase1_v2/`) — that
would need the same log-extraction pass repeated if a full accounting of every job ever run is
needed.
