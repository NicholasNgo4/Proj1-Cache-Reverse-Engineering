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
| Hazel-Haswell | Xeon E5-2650 v3 | Intel | Haswell-EP | 2014 | 22 nm |
| Hazel-Broadwell | Xeon E5-2650 v4 | Intel | Broadwell-EP | 2016 | 14 nm |
| Hazel-Skylake | Xeon Gold 6130 | Intel | Skylake-SP | 2017 | 14 nm |
| Hazel-Cascadelake | Xeon Gold 6226R | Intel | Cascade Lake-SP | 2019 | 14 nm |
| Hazel-Icelake-6326 | Xeon Gold 6326 | Intel | Ice Lake-SP | 2021 | 10 nm |
| Hazel-Icelake-8358 | Xeon Platinum 8358 | Intel | Ice Lake-SP | 2021 | 10 nm |
| Hazel-Sapphirerapids | Xeon Platinum 8462Y+ | Intel | Sapphire Rapids | 2023 | 10 nm / Intel 7 |
| Hazel-Genoa | AMD EPYC 9654 | AMD | Zen 4 | 2022 | 5 nm |
| Hazel-Turin | AMD EPYC 9655 | AMD | Zen 5 | 2024 | 3 nm |


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
| Hazel-Haswell | 32,768 B (32 KiB) | well-confirmed |
| Hazel-Broadwell | 32,768 B (32 KiB) | well-confirmed |
| Hazel-Skylake | 32,768 B (32 KiB) | well-confirmed, sharpest edge of any Hazel gen |
| Hazel-Cascadelake | 32,768 B (32 KiB) | well-confirmed |
| Hazel-Icelake-6326 | 65,536 B (64 KiB) | best-guess only, small-size region itself noisy |
| Hazel-Icelake-8358 | 65,536 B (64 KiB) | best-guess only, small-size region itself noisy |
| Hazel-Sapphirerapids | 65,536 B (64 KiB) | best-guess; genuine deviation from the usual 32 KiB (Golden-Cove-derived L1D) |
| Hazel-Genoa | 32,768 B (32 KiB) | well-confirmed |
| Hazel-Turin | 49,152 B (48 KiB) | best-guess; same deviation pattern as Hazel-Sapphirerapids |

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
| Hazel-Haswell | 262,144 B (256 KiB)| one continuous noisy ramp, no shelf found |
| Hazel-Broadwell | 262,144 B (256 KiB) | best-guess, noisy region but centered on this value |
| Hazel-Skylake | 1,048,576 B (1 MiB) | best-guess, not an independent knee |
| Hazel-Cascadelake | 1,048,576 B (1 MiB) | provisional/reasoned, generation-typical value only, not independently confirmed |
| Hazel-Icelake-6326 | 1,310,720 B (1.25 MiB) | not resolved; generation-typical placeholder |
| Hazel-Icelake-8358 | 1,310,720 B (1.25 MiB) | not resolved; generation-typical placeholder |
| Hazel-Sapphirerapids | 2,097,152 B (2 MiB) | not resolved; generation-typical placeholder |
| Hazel-Genoa | 262,144 B (256 KiB) | not resolved; generation-typical placeholder |
| Hazel-Turin | 1,048,576 B (1 MiB) | not resolved; generation-typical placeholder |


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
| Hazel-Haswell | ~22-24 MiB (22,020,096-25,165,824 B) | provisional, no clean knee; plateau never reached even at 256 MiB tail. 2026-09-15 reproducibility re-run exists but is uninterpreted and looks contention-poisoned from ~6 MiB onward — do not use it to revise this value without further diagnosis |
| Hazel-Broadwell | 32 MiB (33,554,432 B) | |
| Hazel-Skylake | ~22.6 MiB (23,726,560 B) | well-confirmed, cleanest LLC edge of any Hazel gen; tail still climbing at 256 MiB, no plateau |
| Hazel-Cascadelake | 16 MiB (16,777,216 B) | provisional best-guess (curve nearly flat by this point, not a sharp knee); plateau reached and confirmed (only Hazel gen to fully plateau on the original run) |
| Hazel-Icelake-6326 | ~24.68 MiB (25,874,000 B) | well-confirmed sharp knee, matches this SKU's public 24 MB L3 spec almost exactly; plateau reached and confirmed |
| Hazel-Icelake-8358 | ~48 MiB (50,331,648 B) | not resolved; pure spec placeholder — noisiest Hazel run, "likely needs a full re-run when quiet" per its own README |
| Hazel-Sapphirerapids | ~48 MiB (50,331,648 B) | provisional edge, notably below this SKU's published 60 MB spec; no plateau found |
| Hazel-Genoa | 32 MiB (33,554,432 B) | well-confirmed, exact match to AMD's published per-CCD 32 MB L3 spec; tail still climbing, no plateau |
| Hazel-Turin | 32 MiB (33,554,432 B) | best-guess, lower confidence than Hazel-Genoa's; original run reports plateau reached, but a 2026-09-15 reproducibility re-run (uninterpreted) shows the tail still climbing at 268 MiB, casting doubt on the plateau claim — flagged, not resolved |


## Where the underlying data lives

For machine `<m>`: raw CSVs in `data_raw/<m>/capacity/`, processed summaries in
`data_processed/<m>/capacity/`, plots in `data_processed/<m>/capacity/plots/`
(`capacity_curve.{png,pdf}`, `capacity_boxplots.{png,pdf}`), full reasoning and
caveats in `data_raw/<m>/README.md`'s `capacity/` section.
