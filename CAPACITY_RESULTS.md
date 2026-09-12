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
| Charnwood | Core i7-6700 | Intel | Sky Lake | 2015 | 14 nm |
| Ookay | Core i7-7700 | Intel | Kaby Lake | 2017 | 14 nm |
| Upgrade | Core i7-8700 | Intel | Coffee Lake | 2017 | 14 nm |
| Crux | Core i7-9700 | Intel | Coffee Lake | 2019 | 14 nm |
| Skylark | 2× AMD EPYC 7532 | AMD | Zen 2 | 2019 | 7 nm |
| Thunderbird | Ampere Q80-30 | Ampere | ARM Neoverse N1 | 2020 | 7 nm |
| Artemisia | 2× Xeon Gold 5420+ | Intel | Sapphire Rapids | 2023 | 10 nm / Intel 7 |

## L1 capacity

| Machine | Suspected Capacity | Notes |
|---|---|---|
| Sunbird | 32,768 B (32 KiB) | CONFIRMED — corroborated by a clean 8-way associativity knee at this exact stride |
| Thunderbird | 65,536 B (64 KiB) | Read directly off the capacity-sweep graph; falls within the ~64–75 KiB range estimated by eye (auto-detector unusable on this machine's counter — see Caveats). Expected outlier vs. the x86 machines — different vendor/ISA (ARM Neoverse N1) |
| Skylark | 32,768 B (32 KiB) | PROVISIONAL — clean flat-then-ramp signature, not independently cross-checked |
| Artemisia | Unresolved | Sub-48 KiB region shows bimodal per-invocation noise (P-state/turbo-ramp effect, confirmed on a verified-idle core — not contention), no clean plateau found |
| Charnwood | 32,768 B (32 KiB) | PROVISIONAL — clean flat-then-ramp signature, not cross-checked (supersedes an earlier, wrong 311,744 B auto-detected value) |
| Crux | 32,768 B (32 KiB) | PROVISIONAL — clean flat-then-ramp signature, not independently cross-checked |
| Ookay | 32,768 B (32 KiB) | PROVISIONAL — clean flat-then-ramp signature, not independently cross-checked |
| Upgrade | 32,768 B (32 KiB) | CONFIRMED — corroborated 2026-09-12 by a clean 8-way associativity knee at this exact stride |

**Cross-machine finding:** 6 of this team's 7 x86 machines (Sunbird, Crux, Skylark,
Upgrade, Charnwood, Ookay) independently converge on the exact same **32,768 bytes**
L1 estimate via the same flat-then-ramp signature in each machine's own data — not
assumed from one another. Two of those six (Sunbird, Upgrade) have since been
independently corroborated via a clean associativity knee at that stride; the other
four remain provisional pending the same cross-check. Artemisia is the one x86
machine where this region is confounded by a separate P-state effect rather than
cleanly resolved either way.

## L2 capacity

| Machine | Suspected Capacity | Notes |
|---|---|---|
| Sunbird | 262,144 B (256 KiB) | Region judged positively characteristic of a real L2 boundary from the capacity-sweep graph; supersedes the 2026-09-11 `data_raw/sunbird/README.md` re-verification, which had called this point part of the continuous L1→L2 ramp |
| Thunderbird | 1,048,576 B (1 MiB) | Read directly off the capacity-sweep graph; supersedes the prior write-up's "no confirmed shelf" call, which had read the ~75 KiB–~8 MiB span as one long shallow ramp |
| Skylark | Candidate, ~4–16.8 MiB | Coarse data (8 pts/octave) looks flat (26.3–33.2 ticks) but not yet confirmed at dense resolution — needs a 48-pts/octave sweep across ~1–16 MiB |
| Artemisia | No confirmed shelf | ~48–55 KiB through ~90 MiB is one continuous ramp on both tested cores; Sapphire Rapids has no cache level beyond the shared L3, so any boundary here would be an L2/L3 split, not a further level |
| Charnwood | 262,144 B (256 KiB) | Team judgment call, overriding the raw-data reading — the ~180–370 KiB window itself is a smooth, low-noise monotonic ramp with no plateau at 256 KiB; supersedes this table's prior "Unresolved / contaminated" call, which was about the separate ~1.83–11.31 MiB region (12–157% run-to-run spread from a confirmed concurrent process), not this one |
| Crux | No confirmed shelf | ~64 KiB–~4 MiB is a shallow continuous ramp, not a hard plateau |
| Ookay | Unresolved | Entire 32,768 B–~5.3 MiB span is one continuous ramp, no confirmed shelf |
| Upgrade | Candidate, ~1.5–4.5 MiB | Only a ~7% rise over 3 octaves at coarse resolution — shallower than the surrounding ramp, but not confirmed flat; a "derived-stride associativity scan" (2026-09-12) found a reproducible but unresolved two-tier signal here, not yet a citable number (see `data_raw/upgrade/README.md`) |

**No machine on this team has a confirmed, dense-resolution L2 or L3 boundary yet.**
This is the single biggest open item in the capacity dataset.

## L3 (LLC) capacity

| Machine | Suspected Capacity | Notes |
|---|---|---|
| Sunbird | ~30 MiB | Region judged positively characteristic of a real L3 boundary from the capacity-sweep graph; supersedes the 2026-09-11 `data_raw/sunbird/README.md` re-verification, which had called this point part of the continuous climb toward DRAM rather than its own knee. Plateau **confirmed**: flat ~145–256 MiB (40 points, 3.6% avg run-to-run spread) |
| Thunderbird | ~30 MiB | Read directly off the capacity-sweep graph; supersedes the prior write-up's ~16–70 MiB noisy-transition-zone estimate (20–65% run-to-run spread even after averaging). Plateau **confirmed**: flat ~256 MiB–1 GiB (~2.0% avg spread, +3.4% residual growth over the range) |
| Skylark | ~16–22 MiB | Plateau **confirmed**, most fully resolved of all 8: flat ~512 MiB–2 GiB (only ~2% total rise, settles by ~1.7 GiB; reproduced within 0.2% across 2 runs at 2 GiB — only machine extended past 1 GiB) |
| Artemisia | ~48–90 MiB | Transition onset (one continuous ramp). Plateau **split by pattern**: sequential confirmed flat ~90 MiB–1 GiB (idle- vs. contended-core agree within 0.4%); random still open past 1 GiB (+10.8% from 256 MiB to 1 GiB on idle core, no flattening) |
| Charnwood | ~8 MiB | Team judgment call within the documented noisy/contaminated ~4–13 MiB transition (12–157% run-to-run spread, no clean knee); supersedes this table's prior "~12 MiB onset" pick from the same noisy region. Plateau **not confirmed**: still climbing at 1 GiB in 2 of 3 runs; a third shows a further, likely-interference divergence above ~700 MiB — needs a re-run when quiet |
| Crux | ~4–64 MiB | One steep transition (3 auto-detected sub-boundaries are waypoints on it, not separate levels). Plateau **confirmed**: flat ~100 MiB–1 GiB (3 independent runs agree within 0.2–0.5% at 1 GiB) |
| Ookay | ~5.3–11.9 MiB | 4 auto-detected sub-boundaries are one continuous transition. Plateau **confirmed**: flat ~286–297 ticks/access via 256 MiB–1 GiB follow-up (median-of-3 spike-filtered, robust +3.7% last-quarter-vs-prior) |
| Upgrade | ~5–22 MiB | Noisy, unresolved (systematic, not scattered, session-level elevation in one of two repeats). Plateau **not confirmed**: still +11.9% first-to-last-quarter at the 256 MiB ceiling; needs the same 256 MiB–1 GiB follow-up every other machine required |

## Bottom line for anyone revising these numbers

1. **L1 = 32,768 B is the best-supported number in the whole dataset** — 6/7 x86
   machines agree, 2 of those independently cross-checked via associativity.
   Thunderbird's ARM chip is the expected outlier (~64–75 KiB).
2. **No machine has a confirmed L2 or L3 boundary.** Skylark and Upgrade have
   unconfirmed candidates; every other machine shows one continuous ramp with no
   flat shelf at the resolution tried so far. This is the top priority for further
   dense-sweep work if the report needs a full L1/L2/L3 picture rather than just
   L1 + LLC→DRAM.
3. **Topmost DRAM-plateau status is uneven**: confirmed flat on 6 of 8 machines
   (Sunbird, Crux, Skylark, Ookay, Thunderbird, Artemisia-sequential-only); still
   open on Upgrade, Charnwood, and Artemisia's random pattern past 1 GiB.
4. Every number above came from **timing-only Phase I inference** — no `perf`, PMU,
   or cache-topology file was consulted for any of it, per `README.md`'s Phase
   discipline.

## Where the underlying data lives

For machine `<m>`: raw CSVs in `data_raw/<m>/capacity/`, processed summaries in
`data_processed/<m>/capacity/`, plots in `data_processed/<m>/capacity/plots/`
(`capacity_curve.{png,pdf}`, `capacity_boxplots.{png,pdf}`), full reasoning and
caveats in `data_raw/<m>/README.md`'s `capacity/` section.
