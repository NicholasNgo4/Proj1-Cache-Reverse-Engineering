# Chronological Master Table — All 8 ECE Lab Machines (Table 5, draft)

Consolidated 2026-09-14 from every machine's `data_processed/<machine>/FINAL_CACHE_TABLE.md`
(Phase I, timing-only, frozen) and `data_processed/<machine>/PHASE2_VALIDATION_TABLE.md`
(Phase II, PMU + system-report + literature) — see those files for full reasoning,
raw numbers, and caveats behind every cell here. This file only **consolidates**;
it does not re-derive or re-measure anything.

**Sourcing rule (per `PROJECT 1.pdf`'s Table 5 instruction): every cell's PRIMARY
value is the Phase I timing-only inferred number — never silently replaced by a
Phase II/vendor value.** Where Phase II (PMU/system-report/literature) resolved a
disagreement, it is shown as `Phase I → Phase II` with an explicit match/mismatch
flag. This is deliberate: Phase I is the "observed" series this project's Moore-style
trend-fitting and frozen Hazel prediction (§9) must be built from; Phase II is the
validation/error-quantification layer, kept visually and numerically separate.

**Units.** Ticks are each machine's own native timer (RDTSC-derived on x86,
`CNTVCT_EL0` on Thunderbird) — NOT directly comparable across machines (see
`CAPACITY_RESULTS.md`'s units caveat). ns/access is derived so cross-architecture
plots are possible: for Thunderbird, via the independently-read `CNTFRQ_EL0` =
25 MHz (40 ns/tick, a genuinely calibrated hardware constant); for every x86
machine, via that CPU's own rated base clock (printed in its `lscpu` Model name,
itself an allowed Phase I field), under the standard `constant_tsc`/invariant-TSC
assumption that RDTSC ticks at a fixed rate close to base clock — **an explicit,
documented assumption, not "cycles manufactured from nominal GHz"**: it converts an
already-measured elapsed-time tick count into seconds, it does not fabricate a
cycle count. Backing data (all columns, full precision): `data_processed/master/chronological_master_table.csv`.

## Machines, oldest → newest

| Machine | Year | Vendor | ISA | Microarch | CPU | Process node | Base clock |
|---|---|---|---|---|---|---|---|
| Sunbird | 2014 | Intel | x86-64 | Haswell | 2× Xeon E5-2680 v3 | 22 nm | 2.50 GHz |
| Charnwood | 2015 | Intel | x86-64 | Skylake | Core i7-6700 | 14 nm | 3.40 GHz |
| Ookay | 2017 | Intel | x86-64 | Kaby Lake | Core i7-7700 | 14 nm | 3.60 GHz |
| Upgrade | 2017 | Intel | x86-64 | Coffee Lake | Core i7-8700 | 14 nm | 3.20 GHz |
| Crux | 2019 | Intel | x86-64 | Coffee Lake Refresh | Core i7-9700 | 14 nm | 3.00 GHz |
| Skylark | 2019 | AMD | x86-64 | Zen 2 | 2× EPYC 7532 | 7 nm | 2.40 GHz |
| Thunderbird | 2020 | Ampere | AArch64 | ARM Neoverse N1 | Ampere Q80-30 | 7 nm | n/a (25 MHz `CNTVCT_EL0`) |
| Artemisia | 2023 | Intel | x86-64 | Sapphire Rapids | 2× Xeon Gold 5420+ | 10 nm / Intel 7 | 2.00 GHz |

*(Ookay 2017 vs. Upgrade 2017: Kaby Lake launched Jan 2017, Coffee Lake Oct 2017 —
Ookay ordered first. Crux 2019 vs. Skylark 2019: Coffee Lake Refresh launched
~Apr 2019, Zen 2/Rome Aug 2019 — Crux ordered first.)*

## L1D

| Machine | Size | Assoc. (Phase I → Phase II) | Sets | Line | Hit latency (ticks / ns) | L1 miss penalty (ticks / ns) |
|---|---|---|---|---|---|---|
| Sunbird | 32,768 B | 8 → 8 ✓ | 64 | 64 B | 10.35 / 4.14 ns | 124 / 49.6 ns |
| Charnwood | 32,768 B | 8 → 8 ✓ | 64 | 64 B | 7.98 / 2.35 ns | 107 / 31.5 ns |
| Ookay | 32,768 B | 8 → 8 ✓ | 64 | 64 B | 7.49 / 2.08 ns | 96 / 26.7 ns |
| Upgrade | 32,768 B | 8 → 8 ✓ | 64 | 64 B | 6.17 / 1.93 ns | 67 / 20.9 ns |
| Crux | 32,768 B | 8 → 8 ✓ | 64 | 64 B | 7.42 / 2.47 ns | 77 / 25.7 ns |
| Skylark | 32,768 B | 8 → 8 ✓ | 64 | 64 B | 6.24 / 2.60 ns | 96 / 40.0 ns |
| Thunderbird | 65,536 B | 4 → 4 ✓ | 256 | 64 B | 0.130 / 5.0 ns | 1.5 / 60 ns (unresolvable — at overhead floor) |
| Artemisia | 49,152 B | 12 → 12 ✓ | 64 | 64 B | 9.87 / 4.94 ns | 188 / 94.0 ns |

**Headline finding: L1D associativity is the one field where Phase I's timing-only
inference agreed EXACTLY with Phase II (PMU + system-report + literature) on all 8
of 8 machines** — the strongest validation of the timing-only method anywhere in
this project. Size/sets/line also matched exactly everywhere. Miss-penalty numbers
all carry a documented fixed single-shot measurement-overhead caveat (~42–66 ticks
depending on machine) not yet subtracted out — see each machine's `latency/` section.

## L2 (per core)

| Machine | Size | Assoc. (Phase I → Phase II) | Sets (Phase II) | Line | Hit latency (ticks / ns) | L2 miss penalty (ticks / ns) |
|---|---|---|---|---|---|---|
| Sunbird | 262,144 B | 8 → 8 ✓ | 512 | 64 B | 26.83 / 10.73 ns | 284 / 113.6 ns |
| Charnwood | 262,144 B | 8 → **4** ✗ | 1,024 | 64 B | 17.27 / 5.08 ns | 644 / 189.4 ns |
| Ookay | 262,144 B | 8 → **4** ✗ | 1,024 | 64 B | 18.53 / 5.15 ns | 723 / 200.8 ns |
| Upgrade | 262,144 B | 8 → **4** ✗ | 1,024 | 64 B | 16.12 / 5.04 ns | 510 / 159.4 ns |
| Crux | 262,144 B | 8 → **4** ✗ | 1,024 | 64 B | 14.30 / 4.77 ns | 260 / 86.7 ns |
| Skylark | 524,288 B | 8 → 8 ✓ | 1,024 | 64 B | 16.15 / 6.73 ns | 120 / 50.0 ns |
| Thunderbird | 1,048,576 B | 12 → **8** ✗ | 2,048 | 64 B | 0.2975 / 11.9 ns | 2.0 / 80 ns (weak signal) |
| Artemisia | 2,097,152 B* | 16 → 16 ✓ | 2,048 | 64 B | 28.05 / 14.03 ns | 381 / 190.5 ns |

\* Artemisia's L2 size is a `CAPACITY_RESULTS.md` placeholder this machine's own
capacity sweep never independently confirmed as a real boundary (a waypoint inside
one continuous ramp) — used per project-wide direction; Phase II system-report and
Intel ARK both match it exactly regardless.

**Headline finding: L2 associativity is where Phase I's confound-blocked "8-way"
reasoning (matching L1, chosen when the associativity method's DTLB-scale confound
blocked a direct reading) turned out wrong on 4 of 8 machines** — every 32 KiB-L1
Intel Coffee-Lake-family machine (Charnwood, Ookay, Upgrade, Crux) has a REAL L2
associativity of 4, not 8; Thunderbird's independently-reasoned 12-way guess was
also too high (real: 8). Only Sunbird, Skylark, and Artemisia's L2 guesses happened
to be correct.

## LLC (sharing domain shown; per-core normalization varies with domain size — see notes)

| Machine | Size (Phase I → Phase II) | Assoc. (Phase I → Phase II) | Sets (Phase II) | Line | Sharing domain | MiB/core in domain | Hit latency (ticks / ns) | LLC→DRAM miss penalty (ticks / ns) |
|---|---|---|---|---|---|---|---|---|
| Sunbird | 31,457,280 B ✓ (exact) | 9 → **20** ✗ | 24,576 | 64 B | 1 socket (12 cores/24 threads) | 2.5 MiB/core | 58.42 / 23.37 ns | 622 / 248.8 ns |
| Charnwood | 8,388,608 B ✓ (exact) | 8 → **16** ✗ | 8,192 | 64 B | whole chip (4 cores/8 threads) | 2.0 MiB/core | 108 / 31.76 ns | 852 / 250.6 ns |
| Ookay | 8,388,608 B ✓ (exact) | 8 → **16** ✗ | 8,192 | 64 B | whole chip (4 cores/8 threads) | 2.0 MiB/core | 74.78 / 20.77 ns | 693 / 192.5 ns |
| Upgrade | 12,582,912 B ✓ (exact) | 8 → **16** ✗ | 12,288 | 64 B | whole chip (6 cores/12 threads) | 2.0 MiB/core | 155.05 / 48.45 ns | 605 / 189.1 ns |
| Crux | 8,388,608 B → **12,582,912 B** ✗ (1.5×) | 8 → **12** ✗ | 16,384 | 64 B | whole chip (8 cores, no SMT) | 1.5 MiB/core | 43.23 / 14.41 ns† | 437 / 145.7 ns |
| Skylark | 8,388,608 B → **16,777,216 B** ✗ (2×, confirmed underestimate) | 8 → **16** ✗ | 16,384 | 64 B (Phase I measured 128 B here — unresolved 2× line-size disagreement) | 2 cores per L3 instance (CCX-scale, NOT whole socket) | 8.0 MiB/core | 27.22 / 11.34 ns† | 360 / 150.0 ns |
| Thunderbird | 31,457,280 B (no system-report entry; lit. 32 MiB, ~94% match) | 10 → lit. 16 (unresolved — no system-report tiebreak) | 24,576 (Phase I) | 128 B (unconfirmed by system-report) | ALL 80 cores (lit.) | 0.4 MiB/core | 0.907 / 36.3 ns | 4.0 / 160 ns |
| Artemisia | 31,457,280 B → **55,050,240 B** ✗ (1.75×, confirmed) | 16 → 15 (close) | 57,344 | 64 B | 1 socket (28 cores/56 threads) | 1.875 MiB/core‡ | 94.38 / 47.19 ns† | 582 / 291.0 ns |

† Measured at a footprint inside the real LLC, not at its confirmed capacity edge
(Crux's and Artemisia's Phase-I `CAPACITY_RESULTS.md` LLC candidate was later found
too small by Phase II) — treat as an LLC-resident latency lower bound, not the
edge-of-capacity number.
‡ Artemisia's Phase-II-derived 1.875 MiB/core figure independently matches Chips
and Cheese's own published per-core L3 slice figure for this exact SKU/config,
1.875 MB — an exact external cross-check.

**Headline finding: LLC associativity is even more universally wrong in Phase I
than L2 — only Artemisia's guess (16, vs. real 15) came close; every other
machine's confound-blocked guess (uniformly 8, or 9-10 on Sunbird/Thunderbird) was
off by a large factor once Phase II resolved it (up to 2.5×, Sunbird 9→20).** LLC
*size* was also wrong (not just associativity) on 3 machines: Crux (1.5×), Skylark
(2×, already flagged pre-Phase-II as a likely underestimate and confirmed), and
Artemisia (1.75×) — all three are cases where the machine's own Phase-I capacity
sweep never found a clean plateau at the `CAPACITY_RESULTS.md` value used, a
pattern now explained rather than just flagged.

## DRAM (reference floor, not a cache level)

| Machine | Latency (ticks / ns) |
|---|---|
| Sunbird | 207 / 82.8 ns |
| Charnwood | 394.7 / 116.1 ns |
| Ookay | 284.45 / 79.0 ns |
| Upgrade | 251.56 / 78.6 ns |
| Crux | 236.80 / 78.9 ns |
| Skylark | 274.87 / 114.5 ns |
| Thunderbird | 2.336 / 93.4 ns |
| Artemisia | 305.58 / 152.8 ns |

## Inclusion / exclusion behavior (vs. the level immediately below)

| Machine | L1 vs. L2 | L2 vs. LLC | L1 vs. LLC (skip-level) |
|---|---|---|---|
| Sunbird | NON-INCLUSIVE (confident) | UNCERTAIN | UNCERTAIN (leans INCLUSIVE) |
| Charnwood | NON-INCLUSIVE (confident) | NON-INCLUSIVE (leans; low conf.) | INCLUSIVE (leans; moderate conf.) |
| Ookay | NON-INCLUSIVE (confident; cleanest) | INCLUSIVE (weak lean) | INCLUSIVE (leans; moderate-strong) |
| Upgrade | NON-INCLUSIVE (confident) | NON-INCLUSIVE (leans; weak conf.) | UNCERTAIN (reasoned lean NON-INCLUSIVE) |
| Crux | NON-INCLUSIVE (confident; cleanest) | NON-INCLUSIVE (leans; moderate conf.) | UNCERTAIN (barely leans NON-INCLUSIVE) |
| Skylark | UNCERTAIN (weak lean NON-INCLUSIVE) | NON-INCLUSIVE (confident; 99.5%) | NON-INCLUSIVE (confident; cleanest, 100%) |
| Thunderbird | NON-INCLUSIVE (confident, 84.5%) | UNCERTAIN (leans INCLUSIVE, 76.5%) | NON-INCLUSIVE (leans, 80.5% — opposite of Sunbird's own skip-level lean) |
| Artemisia | UNCERTAIN (77.5% ambiguous — methodological gap, oversized eviction footprint) | INCLUSIVE (confident, 100%) | INCLUSIVE (confident; cleanest, 100%) |

**L1 vs. L2 is essentially universally non-inclusive** where a confident call was
possible (6 of 8 machines) — the one cross-architecture finding in this whole
project with the least ambiguity. **The LLC-involving pairings split into two
camps**, not obviously by vendor or year: Sunbird/Charnwood/Ookay read as an
LLC that behaves inclusively toward L1 (consistent with a cross-core snoop-filter
design), while Upgrade/Crux/Skylark read as uniformly non-inclusive at every level,
and Artemisia reads as confidently, cleanly inclusive at both LLC pairings.
Thunderbird is the one machine whose own two LLC-involving results point in
*different* directions from each other.

## Two PMU-derived normalized metrics vs. machine (for §8.4/§9's cross-machine PMU comparison)

| Machine | L1 miss rate @ L1 footprint (sanity check, expect ~0%) | Generic cache-miss rate @ LLC footprint |
|---|---|---|
| Sunbird | 0.61% | 14.21% |
| Charnwood | 1.13% | 33.56% |
| Ookay | 0.97% | 61.50% |
| Upgrade | 1.13% | 39.71% |
| Crux | 1.07% | 11.60%§ |
| Skylark | 0.42% | 46.59% |
| Thunderbird | 0.20% | 5.50%¶ |
| Artemisia | 0.60% | 53.96%# |

§ Crux's LLC-footprint run used the (Phase-I-wrong, too-small) 8 MiB candidate,
which sits *inside* the real 12 MiB LLC — this metric is evidence of crossing L2's
own edge, not the true LLC edge. ¶ Thunderbird's generic `cache-references` PMU
alias tracks `L1-dcache-loads` almost exactly on this SoC (a documented ARM-PMU
limitation) — not a real LLC-scope signal, kept for completeness. # Artemisia's
LLC-footprint run had confirmed concurrent same-socket contention from another
student's job — likely inflated above the clean single-tenant value.

## Notable cross-machine data-quality findings (worth citing in §9's write-up)

1. **L1D is the one cache level this entire project measured essentially perfectly
   via timing alone** — associativity, size, sets, and line size all matched Phase
   II ground truth on all 8 machines, 0 exceptions.
2. **L2 and LLC associativity were wrong far more often than right once Phase II
   could check them** — 5 of 8 L2 guesses and 7 of 8 LLC guesses disagreed with
   system-report/literature. This is the direct, now-quantified cost of the
   documented small-fixed-structure (DTLB-scale) confound that blocked direct
   measurement above L1 on every machine (see `CLAUDE.md`'s associativity section)
   — Phase I's own writeups already flagged every one of these as a low-confidence
   "effective bound," so the disagreement rate confirms rather than contradicts
   that self-assessment.
3. **LLC capacity itself (not just associativity) was wrong on 3 of 8 machines**
   (Crux, Skylark, Artemisia) — in each case because that machine's own Phase-I
   capacity sweep never found a clean plateau at the value used, a genuine
   measurement gap Phase II's system-report closed.
4. **The LLC sharing *domain* is not "one socket" on every machine** — Skylark's
   is 2 cores/CCX (an AMD Rome "cache-doubled" binning choice), Thunderbird's is
   all 80 cores of the SoC (a distributed SLC, architecturally unlike every other
   machine's LLC) — MiB/core in the table above is normalized to each machine's
   own actual sharing domain, not blindly to "total cores in the box."
