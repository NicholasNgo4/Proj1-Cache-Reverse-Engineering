# Predicting Cache Evolution: The Growing Capacity and Latency Cost of CPU Caching
**Homework I — Cache Reverse Engineering Across Architectures and CPU Generations**
Fall 2026 · Due September 10, 2026, 11:59 PM ET

## Team
| Member | Unity ID | GitHub username |
|---|---|---|
| Member 1 | nsngo | NicholasNgo4 |
| Member 2 | krchen | krchen1 |

## Required Links
- **GitHub repository:** https://github.com/NicholasNgo4/Proj1-Cache-Reverse-Engineering (must also appear on report page 1)
- **Overleaf project:** https://www.overleaf.com/project/6a933c98d84565980e9e4385 (must also appear on report page 1)
- [✓ ] TA has been granted access to GitHub
- [✓ ] TA has been granted access to Overleaf
- [✓ ] Instructor has been granted access to GitHub
- [✓ ] Instructor has been granted access to Overleaf

## Repository Layout
```
HW1_TeamName/
├── README.md                 <- this file
├── MACHINE_RESEARCH.md       <- Table 1: ISA/microarch/year research (Phase-I safe)
├── CAPACITY_INFERENCE_STATUS.md <- per-machine/per-level capacity confidence snapshot (gates associativity L2/LLC runs)
├── PREDICTION_FREEZE.md      <- frozen lab-only prediction log + commit hash/timestamp
├── CONTRIBUTION_APPENDIX.md  <- Tables 6-14, mandatory team contribution appendix
├── AI_DISCLOSURE.md          <- Table 13, AI/LLM assistance disclosure
├── report/                   <- HW1_report.pdf (Overleaf export) + report source
├── slides/                   <- HW1_slides.pdf (final slide deck)
├── main_code/
│   ├── x86_64/                <- Intel/AMD reverse-engineering source (final snapshot)
│   ├── aarch64/                <- Arm reverse-engineering source (final snapshot)
│   ├── common/                <- shared/portable code, headers
│   ├── pmu/                    <- Phase-II PMU verification code/scripts
│   └── software_hit_rate/      <- final timing-only hit-rate estimator (Competition 2)
├── scripts/                   <- processing/plotting/reproduction scripts
├── hpc_slurm/                  <- Slurm job scripts, one per Hazel CPU generation
├── data_raw/<machine>/<experiment>/    <- raw, one-million-sample data per machine
├── data_processed/<machine>/<experiment>/ <- processed data feeding each plot/table
├── plots/                      <- final vector plots used in report/slides
└── competition/                <- Reverse-Engineering Scorecard + hit-rate validation table
```

Each `data_raw/<machine>/README.md` is a reproduction manifest: build command, run
command, compiler/flags, affinity/binding, timer method, sample count, seed, and raw
output filenames for every experiment on that machine. Fill these in as you go — do not
backfill them the night before the deadline.

## Build & Run
```bash
make                    # builds ./cache_bench from main_code/common/*.c (portable: timer.h
                         # dispatches to x86_64/timer_x86.h or aarch64/timer_arm.h at compile time)

# Capacity sweep; prints raw per-batch CSV to stdout.
# latency/inclusion are not yet implemented — see main_code/common/capacity.c
# for the pattern each will follow.
taskset -c 4 ./cache_bench --experiment capacity --samples 1000000

# Line-size sweep (fixed footprint, swept byte stride between nodes);
# prints raw per-batch CSV to stdout. Footprint must be chosen near a
# known capacity boundary or the line-size knee is invisible — see
# scripts/run_line_size_full.sh, which picks it automatically from an
# existing capacity summary.
taskset -c 4 ./cache_bench --experiment line_size --footprint-bytes 39321 \
    --min-stride 8 --max-stride 1024 --stride-step 1

# Associativity sweep (fixed node-to-node stride equal to a cache level's own
# capacity, swept same-set node count); prints raw per-batch CSV to stdout.
# cache-bytes MUST be that level's real capacity (a power of two) — see
# main_code/common/associativity.h for why, and scripts/run_associativity_full.sh,
# which prefers an explicit hand-confirmed override over auto-detection.
taskset -c 4 ./cache_bench --experiment associativity --cache-bytes 32768 \
    --min-ways 2 --max-ways 64

# End-to-end on a lab machine, writing into data_raw/ and data_processed/:
./scripts/run_capacity_sweep.sh <machine_name> <core> --samples 1000000
python3 scripts/summarize_raw.py data_raw/<machine_name>/capacity/capacity_*.csv \
    -o data_processed/<machine_name>/capacity/summary.csv
python3 scripts/detect_cache_hierarchy.py data_processed/<machine_name>/capacity/summary.csv

./scripts/run_line_size_full.sh <machine_name> <core>

# cache_bytes_csv is optional (comma-separated per-level capacities); omit it
# to auto-detect from an existing capacity run (prints a warning — prefer an
# explicit, hand-confirmed override, see the script's header comment).
./scripts/run_associativity_full.sh <machine_name> <core> <L1_bytes>,<L2_bytes>,<LLC_bytes>
```
On Hazel, replace `taskset -c 4` with `srun --cpu-bind=cores` (see `hpc_slurm/`).

ECE lab machines: `ssh <unityid>@<hostname>.ece.ncsu.edu` (VPN group `8-Workshop-Temp`
required). Hazel HPC: `ssh <unityid>@login.hpc.ncsu.edu`, submit via `sbatch` — never
benchmark on the login node. See `hpc_slurm/` for job scripts.

## Phase Discipline (do not violate)
1. **Phase I — timing only.** No `perf`, no PMU, no cache-topology files, no Agner Fog,
   no vendor cache tables until the timing-only inference is frozen and tagged in Git
   (tag: `phase1-timing-only`).
2. **Phase II — counters + literature verification.** Only after Phase I is tagged.
3. **Phase III — Hazel.** Lab-only prediction must be frozen and committed **before**
   any cache experiment runs on Hazel. Record the freeze commit hash in
   `PREDICTION_FREEZE.md`.

## Script Index
| Script | Purpose |
|---|---|
| `scripts/run_capacity_sweep.sh` | Build, pin (`taskset`), and run the capacity sweep on a lab machine; writes `data_raw/<machine>/capacity/`. |
| `scripts/run_capacity_full.sh` | One-command per-machine capacity pipeline: coarse sweep → boundary detection → dense sweeps → repeats → plots. |
| `scripts/summarize_raw.py` | Reduce a raw per-batch CSV to one distribution-stats row per swept point (`data_raw` → `data_processed`). |
| `scripts/detect_cache_hierarchy.py` | Infer cache-level boundaries from a processed capacity summary. |
| `scripts/plot_capacity.py` | Plot the capacity curve and box plots from processed capacity summaries. |
| `scripts/run_line_size_sweep.sh` | Build, pin (`taskset`), and run the line-size sweep on a lab machine; writes `data_raw/<machine>/line_size/`. |
| `scripts/run_line_size_full.sh` | One-command per-machine line-size pipeline: auto-picks footprint from an existing capacity boundary → coarse sweep → transition detection → dense sweep → repeats → plots. |
| `scripts/detect_line_size.py` | Infer the cache line size from a processed line-size summary (corrects for the footprint/boundary multiplier). |
| `scripts/plot_line_size.py` | Plot the line-size curve and box plots from processed line-size summaries. |
| `scripts/run_associativity_full.sh` | One-command per-machine, per-cache-level associativity pipeline: sweeps same-set node count at a fixed capacity-sized stride → knee detection → repeats → plots. |
| `scripts/detect_associativity.py` | Infer a cache level's associativity (ways) from a processed associativity summary. |
| `scripts/plot_associativity.py` | Plot the associativity curve and box plots for one cache level. |

## AI/LLM Assistance
See `AI_DISCLOSURE.md`. If none was used, that file says "None."
