# Final Inferred Cache Table — Thunderbird (Phase I best guess, 2026-09-13)

Per PROJECT 1.pdf's required final table (`{level, size, line size, associativity,
derived sets, hit latency, miss/next-level latency, sharing scope, inclusion/
exclusion behavior}`). Built entirely from this machine's already-collected
results across every experiment type (`capacity/`, `line_size/`, `associativity/`,
`latency/`, `inclusion_policy/` — see the sibling directories next to this file,
and `data_raw/thunderbird/README.md`, for the raw/processed data, plots, and
full per-experiment write-ups behind each field) — no new runs. Ticks are this
machine's own `CNTVCT_EL0`-based counter at 25 MHz (40 ns/tick) — coarse relative
to an x86 TSC, and NOT directly comparable across machines (see
`CAPACITY_RESULTS.md`'s units caveat); nanoseconds are given alongside ticks
throughout this file for that reason.

**Every field below leads with a concrete best-guess value, never a bare
"unresolved."** Where direct measurement was blocked by a confound (associativity
above L1 — the same multi-machine confound documented in `CLAUDE.md`'s
associativity section, reproduced here on a THIRD machine and a different
architecture) or by this machine's own coarse timer resolution (parts of
`miss_latency`/`inclusion_policy`), the number given is this team's best reasoned
estimate from the available evidence, following PROJECT 1.pdf's own instruction
to "report an effective bound... rather than guessing" — not a guess pulled from
nowhere, and not a refusal to answer. Each such cell says plainly how confident
it is and why.

**Full raw numbers, per-pairing detail, and the confound investigation itself
live in `data_raw/thunderbird/README.md`** (the `associativity/` section for
the associativity reasoning below, the `inclusion_policy/` section for the
inclusion/exclusion reasoning and its own machine-specific caveats) — this file
is the consolidated best-guess table, not a replacement for that evidence.

| Level | Size | Line size | Associativity | Derived sets (S=C/(A×B)) | Hit latency (dependent, random, median) | Miss/next-level latency (see overhead + resolution caveats) | Sharing scope | Inclusion/exclusion (vs. level below) |
|---|---|---|---|---|---|---|---|---|
| L1D | 65,536 B (64 KiB) per `CAPACITY_RESULTS.md` (hand-verified; take as given) | 64 B — confirmed, offset-independent elbow at 8/8 tested sub-page offsets | **4-way — confirmed** (clean knee, identical across base + both repeats, both patterns) | 256 | ≈0.124-0.136 ticks (~5.0 ns) | L1→L2 ≈1-2 ticks (~40-80 ns) — **statistically indistinguishable from this machine's own ~1-tick single-shot measurement overhead floor; not a resolvable number** | Private per core (best guess — architecturally universal for L1D; not directly tested this phase) | **Best guess: NON-INCLUSIVE / exclusive-like w.r.t. L2** (84.5% of trials survived L2-scale eviction — same qualitative result as Sunbird's own L1_vs_L2, the cleanest pairing on this machine too) |
| L2 | 1,048,576 B (1 MiB) per `CAPACITY_RESULTS.md` (hand-verified; take as given) | 64 B — same as L1, offset-independent elbow at 6/8 tested offsets | **Best guess: 12-way** (see reasoning below) | 1,365 (non-integer at 12-way — see reasoning below for why this doesn't discriminate the guess either way) | ≈0.2975 ticks (~11.9 ns) | L2→LLC ≈2.0 ticks (~80 ns) — one tick above the ~1-tick overhead floor; a small, reproducible, but weak signal, not a precise number | Private per core (best guess) | **Best guess: leans INCLUSIVE w.r.t. LLC, but formally UNCERTAIN** (76.5% of resolved trials invalidated-like vs. 0% survived-like — a strong directional lean, but 23.5% of trials fell in the ambiguous zone and this machine's own weaker avoidance guarantee, see caveat 3 in `data_raw/thunderbird/README.md`'s inclusion_policy/ section, makes this the least trustworthy of the three pairings here too, same as on Sunbird) |
| LLC | ~30 MiB (31,457,280 B representative) per `CAPACITY_RESULTS.md` | **128 B — the one level on this machine that does NOT share the 64 B line size found at L1/L2** (offset-independent elbow at 8/8 tested offsets, reproduced across 2 independent seeds) | **Best guess: 10-way** (effective lower bound; see reasoning below) | 24,576 (clean integer at 10-way) | ≈0.907 ticks (~36.3 ns, rep1/rep2 median — base run's 1.642 excluded as a single-run interference spike, see latency/ section) | LLC→DRAM ≈4.0 ticks (~160 ns) — the ONE confidently resolvable miss-latency number on this machine (~3 ticks / ~120 ns above the overhead floor); overhead-corrected estimate ≈2.1 ticks (~84 ns) | Shared across cores/socket (best guess — architecturally typical for an LLC; not directly tested) | **Best guess: leans NON-INCLUSIVE / exclusive-like w.r.t. L1 (skip-level test)** (80.5% survived-like, just clearing the 80% firm-call threshold) — **the opposite directional lean from Sunbird's own skip-level result** (Sunbird leaned inclusive at 75%); see the synthesis note below before treating either machine's skip-level result as the more "correct" one |
| DRAM (reference floor, not a cache level) | — | — | — | — | ≈2.336 ticks (~93.4 ns) | — | — | — |

## Associativity reasoning (L2 = 12-way, LLC = 10-way, both best-guess)

Direct measurement of L2 and LLC associativity is confounded on this machine —
the same shared, small-fixed-structure confound (leading suspect: DTLB or a
similar page-count-limited structure, not the real cache) that `CLAUDE.md`'s
associativity section documents across Sunbird, Upgrade, Charnwood, and
Artemisia. Thunderbird's own confound investigation
(`data_raw/thunderbird/README.md`'s associativity/ section, note 2) found every
level's curve — including L1's own, at low `num_ways` — shares a spurious small
first bump, and that L2's/LLC's real "second knee" (after skipping that bump)
lands at ~10-12 `num_ways` regardless of a 30x difference in candidate byte
capacity between them — this project's third machine (after Sunbird and
Upgrade, both x86) and FIRST ARM machine to reproduce this exact signature,
which is itself useful cross-architecture evidence the confound is not
x86/DTLB-microarchitecture-specific.

- **L2 → 12-way.** Base sweep reported 11-way; both reproducibility repeats
  (independently seeded) reported 12-way — a 2-of-3 majority, and repeats are
  generally the more trustworthy reading since the base run is more exposed to
  a single-run transient (the same reasoning this project applies elsewhere,
  e.g. Sunbird's/Thunderbird's own hit_latency base-run exclusions). 12-way
  clears the confirmed L1 floor (4-way) with real margin, consistent with the
  general design expectation that a mid-level cache is at least as associative
  as L1, not less.
- **LLC → 10-way**, fully reproducible across base + both repeats (the cleanest
  reproducibility of the three levels' post-L1 numbers on this machine). Per
  PROJECT 1.pdf's explicit allowance to "report an effective bound and explain
  the limitation" when a confound prevents a clean measurement, 10-way is
  presented as an **effective lower bound and best point estimate**: the true
  value could be higher and masked by the same confound, but 10-way is what
  the data most directly and repeatedly supports.
- **Internal-consistency cross-check (S=C/(A×B)), and an honest limitation of
  it on this machine's specific numbers:** L1's own check is clean — 256 sets
  at 4-way, and scaling to L2 at the SAME 4-way hypothetically would give
  1,048,576/(4×64) = 4,096 sets, exactly 16x L1's 256, matching the L1→L2
  capacity ratio (1,048,576/65,536 = 16x) exactly — a real, if weak, structural
  consistency point in favor of an unchanged associativity being at least
  plausible. However, **both L2's capacity (1,048,576 B = 2^20, a power of two)
  and LLC's capacity (31,457,280 B = 2^21×3×5, highly composite) are divisible
  by nearly every plausible candidate associativity** (8, 10, 12, 15, 16, 20,
  24... all divide LLC's byte/line-size quotient of 245,760 cleanly; any
  power-of-two divides L2's quotient cleanly) — unlike Sunbird's LLC estimate,
  where the ~30 MiB figure being a rounded, non-power-of-two-friendly value
  gave the consistency check some real discriminating power, **this check
  does not meaningfully discriminate between candidate associativities for
  either Thunderbird level**, and should not be read as independent
  confirmation of 12-way or 10-way specifically — it is reported for
  completeness and because PROJECT 1.pdf asks for it, not because it is doing
  real evidentiary work here. The confound-wall reproducibility above is the
  actual basis for both best-guess numbers.
- **Apparent non-monotonicity (L2's best guess, 12, is HIGHER than LLC's, 10)
  — flagged, not smoothed over.** Real cache hierarchies essentially never
  have a lower-level cache with strictly lower associativity than the level
  above it (LLC is normally >= L2). Given both numbers come from the same
  unresolved confound rather than direct measurement, the more likely
  explanation is that the confound's own effective "wall" happens to land at
  a slightly different apparent `num_ways` depending on incidental details of
  each candidate's exact byte value/page count (a 30x difference in nominal
  capacity, but not necessarily a 30x difference in whatever page-count-driven
  quantity actually saturates), not that L2 is genuinely more associative than
  LLC. **This is itself evidence that neither number should be treated as a
  precise measurement, only as an "in the same rough 10-12 neighborhood, above
  the L1 floor" best-effort estimate** — consistent with how `CLAUDE.md`
  already treats every other machine's post-confound L2/LLC numbers.

## Overall best-guess read of the hierarchy

Thunderbird's cache hierarchy is best read as **64 KiB / 4-way L1D (64 B lines),
1 MiB / ~12-way L2 (best guess, 64 B lines), and a ~30 MiB / ~10-way LLC (best
guess, 128 B lines — the one level where this machine's line size differs from
the other two)**. L1 is non-inclusive of L2 with reasonably high confidence
(84.5%, though see the caveat below about this machine's own weaker avoidance
guarantee). The two LLC-involving pairings each lean in a specific direction —
L2 vs. LLC leans inclusive (weak confidence, formally UNCERTAIN, also the
pairing most structurally undermined by L2's index not fitting in one page,
same as on Sunbird) while the skip-level L1 vs. LLC test leans NON-inclusive
(80.5%, just clearing the firm-call threshold) — but unlike Sunbird, where all
three pairings combined into one internally consistent story (non-inclusive L2,
LLC acting as an L1 snoop-filter), **Thunderbird's own two LLC-involving
results point in different directions from each other**, and the machine has an
extra, Thunderbird-specific reason to distrust precision here: this machine's
real L1 (65,536 B, 4-way, 256 sets) needs 14 address bits of index+offset,
2 bits more than fits in one 4096 B page — unlike Sunbird's L1, which fits
exactly in 12 bits — so even the L1-target pairings' "eviction structurally
avoids the target's own set" guarantee only holds approximately here, not
exactly (see `data_raw/thunderbird/README.md`'s inclusion_policy/ caveat 3 for
the full argument). Combined with this machine's coarse 25 MHz timer compressing
every classification into just a handful of achievable tick values, the most
defensible overall statement is: **L1 is confidently non-inclusive of L2; this
machine's data does not support a single confident inclusion/exclusion story
for the LLC**, rather than forcing Sunbird's cleaner cross-core-snoop-filter
narrative onto a different CPU vendor/microarchitecture where the data itself
does not point as consistently in one direction. This is this team's
best-supported inference from the data collected, not a certainty — the
associativity values above are the most defensible point estimates available
given a real, well-documented, now cross-architecture-reproduced measurement
confound, not directly observed facts.
