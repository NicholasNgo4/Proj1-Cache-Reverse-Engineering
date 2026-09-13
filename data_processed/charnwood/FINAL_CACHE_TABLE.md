# Final Inferred Cache Table — Charnwood (Phase I best guess, 2026-09-13)

Per PROJECT 1.pdf's required final table (`{level, size, line size, associativity,
derived sets, hit latency, miss/next-level latency, sharing scope, inclusion/
exclusion behavior}`). Built entirely from this machine's already-collected
results across every experiment type (`capacity/`, `line_size/`, `associativity/`,
`latency/`, `inclusion_policy/` — see the sibling directories next to this file
for the raw/processed data and plots behind each field) — no new runs beyond
`inclusion_policy/` itself. Ticks are this machine's own TSC-scale counter (not
directly comparable across machines — see `CAPACITY_RESULTS.md`'s units caveat).
Same format as `data_processed/sunbird/FINAL_CACHE_TABLE.md` and
`data_processed/skylark/FINAL_CACHE_TABLE.md`, so all three can be read side by
side.

**Every field below leads with a concrete best-guess value, never a bare
"unresolved."** Where direct measurement was blocked by a confound (L2/LLC
associativity — the same universal small-way-count wall documented across 5 of
the other 7 team machines in `CLAUDE.md`, and now reproduced here with an
unusually clean same-machine A/B comparison — see the associativity/ section
in `data_raw/charnwood/README.md`), the number given is this team's best
reasoned estimate from the available evidence, following PROJECT 1.pdf's own
instruction to "report an effective bound... rather than guessing." Each such
cell says plainly how confident it is and why.

**Full raw numbers, per-pairing detail, and caveats live in
`data_raw/charnwood/README.md`** (the `associativity/` section for the
associativity reasoning below, the `inclusion_policy/` section's "Best-guess
synthesis" for the inclusion/exclusion reasoning) — this file is the
consolidated best-guess table, not a replacement for that evidence.

| Level | Size | Line size | Associativity | Derived sets (S=C/(A×B)) | Hit latency (dependent, random, median) | Miss/next-level latency (same, see overhead caveat) | Sharing scope | Inclusion/exclusion (vs level below) |
|---|---|---|---|---|---|---|---|---|
| L1D | 32,768 B (32 KiB) — confirmed (flat-then-ramp signature; matches Sunbird/Skylark/Crux/Ookay/Upgrade) | 64 B — confirmed, 2 independent lines of evidence (coarse family-of-curves split + step-4 offset check, one flagged-then-explained offset outlier) | **8-way — confirmed** (single sharp knee at num_ways=9, 0 disagreement across base + 2 repeats, both patterns; matches Sunbird's and Upgrade's own hand-confirmed L1 results) | 64 | ≈7.98 ticks (rep1+rep2 average; the base run's own ≈9.55 ticks is a documented P-state/cold-start elevation, not the trustworthy figure — see latency/ section) | L1→L2 ≈107 ticks (base/rep1/rep2 average; inflated by an estimated ~62-tick fixed single-shot overhead — see latency/ caveat; true incremental cost likely well below this) | Private per core (best guess — architecturally universal for L1D; not directly tested this phase) | **Best guess: NON-INCLUSIVE / exclusive-like w.r.t. L2** (86.0% of trials survived L2-scale eviction, control 100% clean, paired-slower 99.0% — the cleanest and most confident result of the three pairings, matching Sunbird's own L1_vs_L2 read) |
| L2 | 262,144 B (256 KiB) per `CAPACITY_RESULTS.md` (hand-verified; take as given — this machine's own capacity sweep never resolved a clean plateau here, one continuous ramp through this region instead, per capacity/ section) | 64 B — best available estimate (no counter-evidence at this footprint; line_size's own sweep here is a settled null — 5/5 step-4 attempts show a non-stride-specific collapse — not evidence for any *different* value) | **Best guess: 8-way** (see reasoning below) | 512 | ≈17.27 ticks (rep1+rep2 average; same base-run P-state caveat as L1) | L2→LLC ≈644 ticks (base/rep1/rep2 average; same overhead caveat) | Private per core (best guess) | **Best guess: leans NON-INCLUSIVE w.r.t. LLC, low confidence** (target 100% invalidated-like, but control itself shows 54.0% invalidated-like — a confirmed confound the classifier flags explicitly; directional read relies on the persistent ~54-tick target-vs-control gap and the paired-slower 98.5% statistic on top of the shared noise floor — see inclusion_policy/ synthesis for the full reasoning; the least trustworthy of the three pairings, both because L2's index structurally doesn't fit in one page and because this specific eviction scale visibly contaminated the control channel) |
| LLC | 8,388,608 B (8 MiB) per `CAPACITY_RESULTS.md` (hand-verified; take as given) | 64 B — best available estimate, leaning not confirmed (75% direct offset-agreement across 6 independent step-4 repeats at this footprint — the leading candidate, with no competing value ever surfacing, but margin held flat rather than firming up with more repeats — see line_size/ section) | **Best guess: 8-way** (effective estimate; see reasoning below) | 16,384 (clean integer at 8-way/64 B) | ≈108 ticks (all 3 runs agree within ~107-109) | LLC→DRAM ≈852 ticks (base/rep1/rep2 average; same overhead caveat, a smaller fraction of this larger number) | Shared across cores/socket (best guess — architecturally typical for an LLC; not directly tested) | **Best guess: leans INCLUSIVE w.r.t. L1 (skip-level), moderate confidence** (target 99.5% invalidated-like, but control also shows 40.0% invalidated-like — same confound flag as L2_vs_LLC, though weaker; the target-vs-control gap here, ~124 ticks, is more than double L2_vs_LLC's ~54-tick gap, and L1's index is confirmed to fit in one page — the clearest directional lean of the two contaminated pairings, though weaker than Sunbird's own clean-control L1_vs_LLC read) |
| DRAM (reference floor, not a cache level) | — | — | — | — | ≈394.7 ticks | — | — | — |

## Associativity reasoning (L2 = 8-way, LLC = 8-way, both best-guess)

Direct measurement of L2 and LLC associativity is confounded on this machine,
same as 5 of the other 7 team machines (see `CLAUDE.md`'s running tally) — and
this machine produced one of the cleanest same-run demonstrations of the
confound on the whole team:

- **Auto-detected numbers are not directly citable.** Both L2 (262,144 B
  stride) and LLC (8,388,608 B stride) auto-detected "4" from a multi-step
  staircase: a first jump at num_ways=4 (7.56 → 15.6 ticks), a second,
  sharper jump at num_ways=9 (15.6 → 21.9 ticks — the same num_ways=9
  anomaly `CLAUDE.md` documents recurring across Sunbird's/Upgrade's/
  Thunderbird's large-stride attempts), then a noisy climb from ~num_ways=24
  on. `detect_associativity.py` only ever reports the first knee, hence "4"
  for both. **The striking, on-this-machine A/B evidence**: L2 and LLC's
  median-latency curves agree to within ~0.05 ticks/access at every
  num_ways from 2 through 23, despite a 32x difference in candidate byte
  capacity — two genuinely different, independently-sized cache levels have
  no mechanism to produce numerically indistinguishable curves, so both runs
  are almost certainly dominated by the same small, capacity-independent
  structure (leading suspect: the DTLB, since `cache_bytes` here is always a
  multiple of the 4096 B page size regardless of which data-cache level it
  nominally targets) rather than either level's real associativity — see
  `data_raw/charnwood/README.md`'s associativity/ section for the full
  writeup and the exact tick values.
- **L2 → 8-way, best guess.** Neither the auto-detected first jump (4) nor
  the raw multi-step shape is trustworthy given the L2/LLC-curve-identity
  finding above — the real signal, if any survives the confound, is more
  plausibly the second jump at num_ways=9 (→ associativity 8), the same
  reasoning Skylark's own LLC best-guess used for an identical "second jump
  at 9" pattern. Combined with L1's own confirmed 8-way (mid-level caches
  essentially never have lower associativity than L1 in real designs) and
  the S=C/(A×B) cross-check below, 8-way is the best-supported single
  number — with the explicit caveat that this cannot be cleanly separated
  from the confound on this machine any more than on the other 5 affected
  machines.
- **LLC → 8-way, best guess**, for the same reasoning as L2 above — the
  numerically-identical L2/LLC curves mean whatever supports 8-way for L2
  applies equally to LLC here; there is no independent LLC-specific signal
  to differentiate the two on this machine (unlike Skylark, where L2's
  reading was explained as pure L1-aliasing while LLC's had at least a
  majority-vote auto-detected number of its own). Per PROJECT 1.pdf's
  explicit allowance to "report an effective bound and explain the
  limitation" when a confound prevents a clean measurement, 8-way is
  presented as an effective point estimate matching L1 and L2, not a fully
  independent measurement.
- **Internal-consistency cross-check (PROJECT 1.pdf explicitly asks for
  S=C/(A×B) as a cross-check):** using 8-way uniformly for L1/L2/LLC and 64 B
  uniformly for the line size (confirmed at L1, best-guess/leaning at
  L2/LLC — see the line-size column above), the derived set counts are
  64 / 512 / 16,384. L1→L2's set count scales by exactly 8x, matching the
  L1→L2 capacity ratio (262,144/32,768 = 8) exactly. L2→LLC's set count
  scales by exactly 32x, matching the L2→LLC capacity ratio
  (8,388,608/262,144 = 32) exactly too — **both ratios come out clean and
  consistent, a stronger cross-check result than Sunbird's own table got**
  (Sunbird's ~30 MiB LLC estimate gave a non-integer set count at 9-way,
  a known artifact of that machine's LLC boundary being a rounded estimate
  rather than an exact `CAPACITY_RESULTS.md` value the way this machine's
  8 MiB figure is). This cleanliness is consistent with 8-way being the
  right pick for both levels, though — per the associativity-reasoning
  caveat above — it cannot rule out the confound simply reproducing a
  self-consistent-looking number by coincidence.

## Overall best-guess read of the hierarchy

Charnwood's cache hierarchy is best read as **32 KiB / 8-way L1D (64 B line,
confirmed), 256 KiB / 8-way L2 (best guess, 64 B line, best available), and
an 8 MiB / 8-way LLC (best guess, 64 B line, leaning)** — all three levels
converging on the same 64 B line size and 8-way associativity, the cleanest
internal-consistency result (via S=C/(A×B)) of any machine's table produced
so far, even though the L2/LLC associativity number itself remains
confound-limited like the rest of the team's. L1 is non-inclusive of L2 with
high confidence. Both LLC-involving pairings lean toward inclusive/invalidated
behavior, matching Sunbird's own directional pattern, but with lower
confidence than Sunbird's table reports: this machine's inclusion_policy run
produced the clearest on-team evidence yet that the DTLB/large-eviction-
footprint confound (caveat 2 in `inclusion_policy.h`) can visibly contaminate
even the *control* channel, not just the target — both LLC-scale pairings'
controls drifted toward the invalidated class (54.0% for L2_vs_LLC, 40.0% for
L1_vs_LLC) despite never being touched by the eviction walk, something
Sunbird's own three pairings didn't show. The directional reads above lean on
the *relative* target-vs-control gap (and the paired-trial statistic) rather
than the classifier's absolute-fraction threshold for that reason. Put
together, the best-supported single story is the same one Sunbird's table
proposed — an LLC that behaves inclusively toward what's cached above it
(consistent with a cross-core snoop-filter design) alongside a non-inclusive
L2 — reproduced on a second machine, with L2 vs. LLC specifically remaining
the pairing with the least trustworthy signal on both machines, for
structurally the same reason (L2's index not fitting in one page). This is
this team's best-supported inference from the data collected, not a
certainty; the associativity values above are the most defensible point
estimates available given a real, well-documented measurement confound, not
directly observed facts.
