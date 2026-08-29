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

## Build & Run (fill in once code exists)
```bash
# Example — replace with actual final commands
gcc -O0 -g -std=c11 -Wall -Wextra -fno-omit-frame-pointer \
    -o cache_bench main_code/x86_64/cache_bench.c
taskset -c 4 ./cache_bench --experiment capacity --samples 1000000
```

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
| `scripts/` | *(fill in as scripts are added — one row per script)* |

## AI/LLM Assistance
See `AI_DISCLOSURE.md`. If none was used, that file says "None."
