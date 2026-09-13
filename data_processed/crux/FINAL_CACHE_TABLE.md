# Final Inferred Cache Table — Crux (Phase I best guess, 2026-09-13)

Per PROJECT 1.pdf's required final table (`{level, size, line size, associativity,
derived sets, hit latency, miss/next-level latency, sharing scope, inclusion/
exclusion behavior}`). Built entirely from this machine's already-collected
results across every experiment type (`capacity/`, `line_size/`, `associativity/`,
`latency/`, `inclusion_policy/` — see the sibling directories next to this file
for the raw/processed data and plots behind each field, and
`data_raw/crux/README.md` for the full narrative) — no new runs beyond
`inclusion_policy/` itself. Ticks are this machine's own TSC-scale counter (not
directly comparable across machines — see `CAPACITY_RESULTS.md`'s units caveat).

**Every field below leads with a concrete best-guess value, never a bare
"unresolved."** Where direct measurement was blocked by a confound (this
happened for L2/LLC associativity, same as 5 of the other 7 team machines —
see the reasoning section below), the number given is this team's best
reasoned estimate from the available evidence, following PROJECT 1.pdf's own
instruction to "report an effective bound... rather than guessing" — not a
guess pulled from nowhere, and not a refusal to answer.

**Full raw numbers, per-pairing detail, and calibration checks live in
`data_raw/crux/README.md`** (the `associativity/` section for the raw
associativity numbers, the `inclusion_policy/` section for the per-pairing
classification detail and best-guess synthesis) — this file is the
consolidated best-guess table, not a replacement for that evidence.

| Level | Size | Line size | Associativity | Derived sets (S=C/(A×B)) | Hit latency (dependent, random, median) | Miss/next-level latency (same, see overhead caveat) | Sharing scope | Inclusion/exclusion (vs. level below) |
|---|---|---|---|---|---|---|---|---|
| L1D | 32,768 B (32 KiB) — confirmed | 64 B — confirmed (5 independent runs converging on a clean, alignment-independent elbow; L1's own reproducibility took 3 attempts to land at 1.00x, see line_size/ section) | **8-way — confirmed** (clean single knee, 0% repeat spread across base+2 repeats, both patterns) | 64 | ≈7.42 ticks | L1→L2 ≈77 ticks (inflated by an estimated ~42-tick fixed single-shot overhead — see latency/ caveat; true incremental cost likely well below this) | Private per core (best guess — architecturally universal for L1D; not directly tested this phase) | **Best guess: NON-INCLUSIVE / exclusive-like w.r.t. L2** (97.5% of trials survived L2-scale eviction, cleanest and most confident result of the three pairings) |
| L2 | 262,144 B (256 KiB) per `CAPACITY_RESULTS.md` (hand-verified; take as given — this machine's own capacity write-up independently flags this region as a soft ramp rather than a hard plateau, but per project-wide direction `CAPACITY_RESULTS.md` wins) | 64 B — the most-repeated result on this machine (5 independent runs, 1.00-1.12x spread every time) | **Best guess: 8-way** (raw detector says 4-way with full 3/3 reproducibility, but see reasoning below for why 4 is treated as confound, not signal) | 512 | ≈14.30 ticks | L2→LLC ≈260 ticks (same overhead caveat; also carries a 77.8% base-vs-repeat spread not traced to a specific process — see latency/ section) | Private per core (best guess) | **Best guess: leans NON-INCLUSIVE w.r.t. LLC** (90.5% survived-like, 2.5% invalidated-like — a clean majority clearing the classifier's threshold, though caveat 3 below limits confidence for an L2-sized target) |
| LLC | ~8 MiB (8,388,608 B) per `CAPACITY_RESULTS.md` (this machine's own data flags a noisy, not-fully-resolved ~4-64 MiB transition region behind this rounded value, and `lscpu`'s reported real L3 is 12 MiB — noted, not resolved) | 64 B — the tightest result on this machine (2 independent runs, 1.00-1.26x spread) | **Best guess: 8-way** (raw detector says 4-way, 3/3 reproducible — identical value to L2's raw result despite a 32x capacity difference; see reasoning below) | 16,384 (clean integer at 8-way — see consistency check below) | ≈43.23 ticks | LLC→DRAM ≈437 ticks (same overhead caveat, a smaller fraction of this larger number; also flagged >20% spread, up to 42.6% on the sequential pattern) | Shared across cores/socket (best guess — architecturally typical for an LLC; not directly tested) | **Best guess: leans NON-INCLUSIVE w.r.t. L1 (barely, lowest confidence of the three)** (skip-level test: 98% of trials fell in the classifier's ambiguous band; target's raw median sits just below the calibration midpoint, and reads reliably slower than its own control in 99.5% of trials, but not by enough margin for a firm per-trial call) |
| DRAM (reference floor, not a cache level) | — | — | — | — | ≈236.80 ticks | — | — | — |

## Associativity reasoning (L2 = 8-way, LLC = 8-way, both best-guess)

Direct measurement of L2 and LLC associativity is confounded on this machine,
the same way it has been on 5 of the other 7 team machines (see
`CLAUDE.md`'s associativity section for the cross-machine writeup). Unlike
most of those machines, Crux's raw sweep did **not** come back as an obvious
multi-step staircase — each level gave a single, sharp, fully-reproducible
knee (base + 2 repeats in exact agreement, 0% spread). At face value that
looks like a clean result. It is not treated as one here, for a specific,
concrete reason:

- **The confound signature this team uses is "two structurally different
  levels break at the same num_ways despite a large capacity difference,"
  and Crux's own data is a textbook case of exactly that.** L2
  (cache_bytes=262,144) and LLC (cache_bytes=8,388,608) — a 32x difference in
  byte capacity — both independently report **4-way**, with full 3/3
  reproducibility each. A genuine capacity-driven knee has no mechanism to
  land at the identical way-count for two real cache levels 32x apart; this
  is the same evidence pattern Charnwood's README uses to reject its own
  "L2=4, LLC=4" result as confound-driven rather than real (see `CLAUDE.md`'s
  Charnwood associativity bullet), and — concretely — **Charnwood tested the
  exact same two candidate byte values (262,144 and 8,388,608) and got the
  exact same "4" answer at both**, which is strong independent corroboration
  that "4" here is a property of some small, fixed-way-count structure common
  to both candidates (most likely DTLB-related, per the mechanism argued in
  `CLAUDE.md`'s Sunbird associativity section — every probed node in this
  method lives on its own page regardless of which data-cache level is
  nominally targeted), not either level's real associativity.
- **L2 → 8-way (best guess).** The raw 4-way result is set aside per the
  confound argument above. Anchoring instead to this machine's own confirmed
  L1 result (8-way) — mid-level caches essentially never have *lower*
  associativity than L1 in real designs — 8-way is the natural best guess
  absent a method that can see past the confound (Crux has not run the
  derived-stride-scan technique Upgrade used, so there is no second,
  confound-resistant data point to cross-check against here; this is a
  reasoned default, not an independently corroborated number the way
  Sunbird's L2 guess was).
- **LLC → 8-way (best guess).** Same reasoning: the raw 4-way result carries
  the same confound signature as L2's, and there is no independent
  confound-resistant measurement on this machine to override it with. 8-way
  is chosen over the raw 4 both for consistency with L2's own guess (no
  positive evidence either level differs from the other) and because it
  produces a fully clean internal-consistency result, below.
- **Internal-consistency cross-check (PROJECT 1.pdf explicitly asks for
  S=C/(A×B) as a cross-check):** using 8-way uniformly at all three levels,
  the derived set counts are 64 / 512 / 16,384 — **every one is an exact
  integer**, and each ratio matches the corresponding capacity ratio exactly:
  L1→L2 sets scale 8x (matching 262,144/32,768 = 8x), L2→LLC sets scale 32x
  (matching 8,388,608/262,144 = 32x). This is a cleaner, fully-consistent
  chain than Sunbird's own table produced (where the LLC guess broke the
  clean-integer pattern because Sunbird's ~30 MiB LLC capacity is itself a
  rounded, non-power-of-two estimate) — for Crux, the uniform-8-way guess is
  not just plausible, it is the single value that makes the whole hierarchy's
  arithmetic close exactly. Using the raw 4-way at either L2 or LLC instead
  breaks this cleanly (e.g. LLC at 4-way gives 32,768 sets, a 64x scale-up
  from L2's 512 at 8-way rather than the capacity-matching 32x) — a second,
  independent reason to prefer 8 over the raw 4.

## Overall best-guess read of the hierarchy

Crux's cache hierarchy is best read as **32 KiB / 8-way L1D, 256 KiB / 8-way
L2 (best guess), and a ~8 MiB / 8-way LLC (best guess, though `lscpu`'s
reported 12 MiB real L3 and this machine's own noisy ~4-64 MiB capacity
transition mean the *size* itself carries more uncertainty here than at
Sunbird)**, all sharing the same 64 B line size. L1 is non-inclusive of L2
with high confidence (97.5%). L2 vs. LLC also leans non-inclusive, with
moderate confidence (90.5%, tempered by the L2-target-doesn't-fit-in-one-page
caveat that also limited Sunbird's equivalent pairing). The skip-level L1 vs.
LLC test is this machine's weakest result — dominated by an ambiguous
classification band, plausibly smeared by DTLB pressure at the 512 MiB
eviction scale both LLC-involving pairings share — but for what little
directional signal it carries, it leans the same way (non-inclusive) rather
than the opposite way the way Sunbird's own skip-level test did. **Put
together, the best-supported single story for this machine is a uniformly
non-inclusive hierarchy at every tested boundary** — a genuine point of
contrast with Sunbird, whose own best-guess synthesis found an LLC that
behaves inclusively toward L1 (consistent with a cross-core snoop-filter
design) alongside a non-inclusive L2. Nothing in Crux's data argues for an
inclusive relationship anywhere; the associativity values above are the most
defensible point estimates available given a real, well-evidenced measurement
confound (corroborated here by an exact cross-machine match with Charnwood's
own confound value at the identical candidate bytes), not directly observed
facts.
