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

| Machine | L1 estimate | Notes |
|---|---|---|
| Sunbird | 32,768 B (32 KiB) | **CONFIRMED** — corroborated by a clean 8-way associativity knee at this exact stride |
| Upgrade | 32,768 B (32 KiB) | **CONFIRMED** — corroborated 2026-09-12 by a clean 8-way associativity knee at this exact stride |
| Crux | 32,768 B (32 KiB) | PROVISIONAL — clean flat-then-ramp signature only, not independently cross-checked |
| Skylark | 32,768 B (32 KiB) | PROVISIONAL — same signature, not cross-checked |
| Charnwood | 32,768 B (32 KiB) | PROVISIONAL — same signature, not cross-checked (supersedes an earlier, wrong 311,744 B auto-detected value — do not use that value for anything on this machine) |
| Ookay | 32,768 B (32 KiB) | PROVISIONAL — same signature, not cross-checked |
| Thunderbird | ~64–75 KiB | Estimated by eye (auto-detector unusable on this machine's counter — see Caveats). **The one machine that does NOT match the 32 KiB value below** — expected, different vendor/ISA/microarchitecture family (ARM Neoverse N1 vs. every x86 machine here) |
| Artemisia | **Unresolved** | Sub-48 KiB region shows bimodal per-invocation noise (P-state/turbo-ramp effect, confirmed to persist on a verified-idle core — not contention), not a clean flat plateau at any resolution tried so far |

**Cross-machine finding:** 6 of this team's 7 x86 machines (Sunbird, Crux, Skylark,
Upgrade, Charnwood, Ookay) independently converge on the exact same **32,768 bytes**
L1 estimate via the same flat-then-ramp signature in each machine's own data — not
assumed from one another. Two of those six (Sunbird, Upgrade) have since been
independently corroborated via a clean associativity knee at that stride; the other
four remain provisional pending the same cross-check. Artemisia is the one x86
machine where this region is confounded by a separate P-state effect rather than
cleanly resolved either way.

## L2 Capacity

| Machine | Capacity | Notes |
|---|---|---|
| Sunbird | 262144 B (256 KiB) | ~32 KiB–~8 MiB is one continuous ramp per the dense data |
| Crux | No confirmed shelf | ~64 KiB–~4 MiB is a shallow continuous ramp, not a hard plateau |
| Skylark | Candidate, ~4–16.8 MiB | Coarse data (8 pts/octave) looks flat (26.3–33.2 ticks, no monotonic trend) but not yet confirmed at dense resolution — needs a 48-pts/octave sweep across ~1–16 MiB |
| Upgrade | Candidate, ~1.5–4.5 MiB | Only a ~7% rise over 3 octaves at coarse resolution — shallower than the ramp around it, but not confirmed flat; a "derived-stride associativity scan" attempt (2026-09-12) found a reproducible but unresolved two-tier signal here, not yet a citable number (see `data_raw/upgrade/README.md`) |
| Charnwood | Unresolved / contaminated | ~1.83–11.31 MiB region showed 12–157% run-to-run spread from a confirmed concurrent process contending for shared resources; needs a re-run when quiet |
| Ookay | Unresolved | Entire 32,768 B–~5.3 MiB span is one continuous ramp, no confirmed shelf |
| Thunderbird | No confirmed shelf | Long shallow ramp from ~75 KiB through ~8 MiB, no flat shelf detected |
| Artemisia | No confirmed shelf | ~48–55 KiB through ~90 MiB is one continuous ramp on both tested cores; Sapphire Rapids has no cache level beyond the shared L3 per vendor-topology terms, so any boundary found here would be an L2/L3 split, not a further level |

**No machine on this team has a confirmed, dense-resolution L2 or L3 boundary yet.**
This is the single biggest open item in the capacity dataset.

## LLC → DRAM transition and topmost plateau

| Machine | Transition onset (approx.) | Plateau confirmed? | Confirmed range / notes |
|---|---|---|---|
| Sunbird | ~26–27 MiB (corrected 2026-09-10 from an earlier, retracted ~20 MiB estimate — see that README) | **Yes**, within swept range | Flat ~145–256 MiB (40 points, 3.6% avg run-to-run spread); no evidence yet either way past 256 MiB |
| Crux | one steep transition ~4–64 MiB (3 auto-detected sub-boundaries are waypoints on it, not separate levels) | **Yes** | Flat ~100 MiB–1 GiB (3 independent runs agree within 0.2–0.5% at 1 GiB) |
| Skylark | ~16–22 MiB | **Yes**, most fully resolved of all 8 | Flat ~512 MiB–2 GiB (only ~2% rise total, settles by ~1.7 GiB; reproduced within 0.2% across 2 runs at 2 GiB — the only machine extended past 1 GiB) |
| Upgrade | noisy, unresolved ~5–22 MiB (systematic, not scattered, session-level elevation in one of two repeats) | **No** | Still +11.9% first-to-last-quarter at the 256 MiB ceiling; needs the same 256 MiB–1 GiB follow-up every other machine required |
| Charnwood | gentle ~11–15% climb from ~12 MiB, likely TLB/page-walk growth rather than a cache boundary (to confirm in Phase II) | **No** | Still climbing at 1 GiB in 2 of 3 runs; a third shows a further, likely-interference divergence above ~700 MiB — flagged open, needs a re-run when quiet |
| Ookay | ~5.3–11.9 MiB (4 auto-detected sub-boundaries are one continuous transition) | **Yes** | Flat ~286–297 ticks/access confirmed via 256 MiB–1 GiB follow-up (median-of-3 spike-filtered, robust +3.7% last-quarter-vs-prior) |
| Thunderbird | ~16–70 MiB (genuinely noisy zone, 20–65% run-to-run spread even after averaging) | **Yes** | Flat ~256 MiB–1 GiB (~2.0% avg run-to-run spread, +3.4% residual growth over the whole range) |
| Artemisia | ~48–90 MiB (one continuous ramp) | **Split by pattern** | Sequential: **confirmed** flat ~90 MiB–1 GiB (idle-core vs. contended-core runs agree within 0.4%). Random: **still open** past 1 GiB — idle core still grows +10.8% from 256 MiB to 1 GiB, no flattening |

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
