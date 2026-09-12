# Cache Capacity Results — Consolidated (Table 2, draft)

**This file is a synthesized snapshot, not the source of truth.** It was assembled
2026-09-12 by reading every machine's `data_raw/<machine>/README.md` capacity/
section. Where a number or caveat here conflicts with a machine's own README, the
README wins — that's where the full reasoning, run commands, and raw-data pointers
live. Revise this file (or regenerate it) whenever a machine's capacity section
changes.

**Units caveat — read before comparing tick values across rows.** `ticks/access` is
each machine's own hardware counter, at that machine's own frequency. Byte values
(working-set sizes, boundaries) ARE directly comparable across machines; raw tick
counts are NOT — Thunderbird's ARM `CNTVCT_EL0` runs at 25 MHz vs. every x86
machine's multi-GHz TSC, so e.g. Thunderbird's "~2.3-2.4 ticks" DRAM plateau and
Sunbird's "~190-205 ticks" plateau are not on the same scale and must not be
compared as numbers. Converting to nanoseconds/access (tick count / counter
frequency) before cross-machine comparison is on the TODO list — not done in this
file yet.

## Machines, oldest → newest (per `MACHINE_RESEARCH.md`'s year convention)

| Machine | CPU | Vendor | Microarch | Year | Node |
|---|---|---|---|---|---|
| Sunbird | 2× Xeon E5-2680 v3 | Intel | Haswell | 2014 | 22 nm |
| Thunderbird | Ampere Q80-30 | Ampere | ARM Neoverse N1 | 2020 | 7 nm |
| Skylark | 2× AMD EPYC 7532 | AMD | Zen 2 | 2019 | 7 nm |
| Artemisia | 2× Xeon Gold 5420+ | Intel | Sapphire Rapids | 2023 | 10 nm / Intel 7 |
| Charnwood | Core i7-6700 | Intel | Sky Lake | 2015 | 14 nm |
| Crux | Core i7-9700 | Intel | Coffee Lake | 2019 | 14 nm |
| Ookay | Core i7-7700 | Intel | Kaby Lake | 2017 | 14 nm |
| Upgrade | Core i7-8700 | Intel | Coffee Lake | 2017 | 14 nm |


## L1 capacity

| Machine | Suspected Capacity | Notes |
|---|---|---|
| Sunbird | 32,768 B (32 KiB) | |
| Thunderbird | 65,536 B (64 KiB) | |
| Skylark | 32,768 B (32 KiB) | |
| Artemisia | 49,152 B (48 KiB) | |
| Charnwood | 32,768 B (32 KiB) | |
| Crux | 32,768 B (32 KiB) | |
| Ookay | 32,768 B (32 KiB) | |
| Upgrade | 32,768 B (32 KiB) | |

**Cross-machine finding:** 6 of this team's 7 x86 machines (Sunbird, Skylark, Charnwood, Crux, Ookay,
Upgrade) independently converge on the exact same **32,768 bytes**
L1 estimate via the same flat-then-ramp signature in each machine's own data — not
assumed from one another. Two of those six (Sunbird, Upgrade) have since been
independently corroborated via a clean associativity knee at that stride.

## L2 capacity

| Machine | Suspected Capacity | Notes |
|---|---|---|
| Sunbird | 262,144 B (256 KiB) | |
| Thunderbird | 1,048,576 B (1 MiB) | |
| Skylark | 524,288 B(512 KiB) | |
| Artemisia | 2,097,152 B (2 MiB) | |
| Charnwood | 262,144 B (256 KiB) | |
| Crux | 262,144 B (256 KiB) | |
| Ookay | 262,144 B (256 KiB) | |
| Upgrade | 262,144 B (256 KiB) | |


## L3 (LLC) capacity

| Machine | Suspected Capacity | Notes |
|---|---|---|
| Sunbird | ~30 MiB | |
| Thunderbird | ~30 MiB | |
| Skylark | ~8 MiB | |
| Artemisia | ~30 MiB | |
| Charnwood | ~8 MiB | |
| Crux | ~8 MiB | |
| Ookay | ~8 MiB | |
| Upgrade | ~12 MiB | |


## Where the underlying data lives

For machine `<m>`: raw CSVs in `data_raw/<m>/capacity/`, processed summaries in
`data_processed/<m>/capacity/`, plots in `data_processed/<m>/capacity/plots/`
(`capacity_curve.{png,pdf}`, `capacity_boxplots.{png,pdf}`), full reasoning and
caveats in `data_raw/<m>/README.md`'s `capacity/` section.
