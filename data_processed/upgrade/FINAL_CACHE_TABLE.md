# Final Inferred Cache Table — Upgrade (Phase I best guess, 2026-09-13)

Per PROJECT 1.pdf's required final table (`{level, size, line size, associativity,
derived sets, hit latency, miss/next-level latency, sharing scope, inclusion/
exclusion behavior}`). Built entirely from this machine's already-collected
results across every experiment type (`capacity/`, `line_size/`, `associativity/`,
`latency/`, `inclusion_policy/` — see the sibling directories next to this file
for the raw/processed data and plots behind each field) — no new runs beyond
`inclusion_policy/` itself. Ticks are this machine's own TSC-scale counter (not
directly comparable across machines — see `CAPACITY_RESULTS.md`'s units caveat).
Same format as `data_processed/{sunbird,skylark}/FINAL_CACHE_TABLE.md`, so all
three can be read side by side.

**Every field below leads with a concrete best-guess value, never a bare
"unresolved."** Where direct measurement was blocked by a confound (L2/LLC
associativity, the same universal small-way-count wall documented across 5 of
the other 7 team machines in `CLAUDE.md`) or by a capacity boundary this
machine's own data never independently confirmed (L2/LLC size, taken from
`CAPACITY_RESULTS.md` per project-wide direction), the number given is this
team's best reasoned estimate from the available evidence, following
PROJECT 1.pdf's own instruction to "report an effective bound... rather than
guessing." Each such cell says plainly how confident it is and why.

**Full raw numbers, per-pairing detail, and caveats live in
`data_raw/upgrade/README.md`** (the `associativity/` section for the
associativity reasoning below, the `inclusion_policy/` section's "Best-guess
synthesis" for the inclusion/exclusion reasoning) — this file is the
consolidated best-guess table, not a replacement for that evidence.

| Level | Size | Line size | Associativity | Derived sets (S=C/(A×B)) | Hit latency (dependent, random, median) | Miss/next-level latency (same, see overhead caveat) | Sharing scope | Inclusion/exclusion (vs level below) |
|---|---|---|---|---|---|---|---|---|
| L1D | 32,768 B (32 KiB) — confirmed (flat-then-ramp signature; matches Sunbird/Skylark/Charnwood/Crux/Ookay) | 64 B — confirmed, 2 independent methods (Method A family-of-curves + Method B ramp-saturation) plus 2 independent step-4 cross-alignment repeats, all converging cleanly | **8-way — confirmed** (single sharp knee at num_ways=9, identical across base + 2 repeats, both patterns; also independently corroborates the PROVISIONAL 32,768 B capacity estimate) | 64 | ≈6.17 ticks | L1→L2 ≈67 ticks (inflated by an estimated ~48-49 tick fixed single-shot overhead — see latency/ caveat; true incremental cost likely well below this) | Private per core (best guess — architecturally universal for L1D; not directly tested this phase) | **Best guess: NON-INCLUSIVE / exclusive-like w.r.t. L2** (99.0% of trials survived L2-scale eviction, 0% invalidated-like — cleanest and most confident of the three pairings) |
| L2 | 262,144 B (256 KiB) per `CAPACITY_RESULTS.md` (hand-verified; take as given — this machine's own capacity sweep only resolved a candidate, NOT-confirmed ~1.5-4.5 MiB shelf, not a clean 256 KiB edge) | 64 B — best available estimate (this machine's own line_size/ data at this footprint never converged across 7+ repeated runs — genuine noise, not a competing measured value; no evidence for anything other than L1's confirmed 64 B) | **Best guess: 8-way** (see reasoning below) | 512 | ≈16.12 ticks | L2→LLC ≈510 ticks (same overhead caveat) | Private per core (best guess) | **Best guess: leans NON-INCLUSIVE w.r.t. LLC** (95.5% survived-like, 4.0% invalidated-like — but read with the LEAST confidence of the three pairings, since L2's index almost certainly doesn't fit within one page, so the eviction walk's "avoids the upper level's own set" guarantee doesn't structurally hold here; one repeat also showed 90.4% spread on the target/random channel, consistent with genuine shared-machine interference) |
| LLC | ~12 MiB (12,582,912 B) per `CAPACITY_RESULTS.md` — this machine's own capacity sweep never resolved a discrete LLC edge either (only a noisy, unresolved ~5-22 MiB transition region) | 64 B — best available estimate (same reasoning as L2: no measured alternative anywhere on this machine, unlike Skylark's/Thunderbird's genuine per-level 128 B finding) | **Best guess: 8-way** (see reasoning below) | 24,576 (exact integer — see cross-check below) | ≈155.05 ticks | LLC→DRAM ≈605 ticks (same overhead caveat, a smaller fraction of this larger number) | Shared across cores/socket (best guess — architecturally typical for an LLC on a single-socket 6-core part; not directly tested) | **Best guess: leans NON-INCLUSIVE w.r.t. L1 (skip-level)** — classifier itself calls this pairing UNCERTAIN (target sits almost exactly on the classification boundary, 95% of trials ambiguous), but the target's tight 165-174 tick interquartile reload cost is far closer to this machine's own on-chip LLC-hit latency (≈155 ticks) than to either the ~46-tick "survived" or ~605-tick "invalidated" calibration extremes — i.e. the target is landing back in cache, not being forced all the way to DRAM, which argues against inclusive backward-invalidation (see `data_raw/upgrade/README.md`'s inclusion_policy/ section for the full reasoning) |
| DRAM (reference floor, not a cache level) | — | — | — | — | ≈251.56 ticks | — | — | — |

## Associativity reasoning (L2 = 8-way, LLC = 8-way, both best-guess)

Direct measurement of L2 and LLC associativity is confounded on this machine
(and on 5 of the other 7 team machines): every fixed-full-capacity-stride
candidate tried — both the original `run_associativity_full.sh` sweeps and
the `CAPACITY_RESULTS.md`-anchored re-run — breaks around num_ways≈4-9
regardless of the actual candidate byte value, the same universal
small-structure (likely DTLB-related) confound signature documented
throughout `CLAUDE.md`. Unlike most other machines, though, Upgrade also has
a second, more targeted line of evidence: the derived-stride-scan technique
(`scripts/run_associativity_stride_scan.sh`), first tried on this machine
specifically because the standard method's confound was already suspected.

- **Validated against known-good L1 data first.** At `cache_bytes=32768`
  (confirmed L1 stride), `A_guess=1,2,4,8` all correctly recover knee=8
  across a 200-to-25-page arena range — the technique and its
  self-consistency check work as designed before being trusted on unknown
  data.
- **L2 candidate (2,097,152 B) and an LLC-region candidate (16,777,216 B)
  both show the identical two-tier structure.** `A_guess=1` through `256`
  (spanning strides from the full candidate down to 65,536 B — a 256x page-
  count range) all report the same shallow first knee of 4 for both
  candidates; `A_guess` large enough to shrink the stride back down to
  32,768 B (the L1 stride) correctly recovers 8 instead, confirming the
  scan detects when it has degenerated into re-testing L1's own set. A
  **full-rigor confirm run** at the shared 65,536 B stride (1,000,000
  samples, both patterns, 2 repeats) showed this "4" is only the FIRST step
  of a two-step staircase — flat through ways 2-3, a marginal/noisy partial
  rise at way 4 (base/rep1 called it thrashing, rep2 didn't: 47% spread),
  a mid-plateau through way 8, then a second, much sharper jump at **way
  9** — i.e. 8 concurrently-resident lines fit without real conflict, and
  the genuine eviction threshold is 8-way, not the shallow first-step
  artifact `detect_associativity.py` reports by default.
- **L2 → 8-way.** The full-rigor confirm run above is the direct evidence:
  a real plateau survives cleanly through way 8, with the sharp break at
  way 9. Combined with L1's own confirmed 8-way (mid-level caches
  essentially never have lower associativity than L1 in real designs) and
  the S=C/(A×B) cross-check below, 8-way is the best-supported single
  number.
- **LLC → 8-way, reported with the same confidence caveat as every other
  machine's LLC associativity guess.** The derived-stride scan's LLC-region
  candidate produced numerically the *same* 4-then-8 two-tier structure as
  the L2 candidate, which cuts both ways: it is consistent with LLC also
  being 8-way (matching L1/L2, architecturally the common case), but the
  scan cannot rule out that both candidates are simply hitting the same
  confound ceiling before ever reaching a genuinely larger LLC-specific
  associativity — i.e. this machine's evidence for LLC=8 is real but not as
  independent as Sunbird's own reproducibility-based LLC pick. Per
  PROJECT 1.pdf's explicit allowance to "report an effective bound and
  explain the limitation," 8-way is presented as an effective point
  estimate and the best-supported number available, not a fully
  independent measurement.
- **Internal-consistency cross-check (PROJECT 1.pdf explicitly asks for
  S=C/(A×B) as a cross-check):** using 8-way and 64 B uniformly for
  L1/L2/LLC, the derived set counts are 64 / 512 / 24,576. L1→L2's set
  count scales by exactly 8x, matching the L1→L2 capacity ratio
  (262,144/32,768 = 8) exactly. **LLC's own set count comes out to a clean
  integer, 24,576** (12,582,912 / 512 = 24,576.0 exactly) — unlike
  Sunbird's ~30 MiB rounded estimate, this machine's `CAPACITY_RESULTS.md`
  LLC value is already an exact power-of-two-adjacent number, so this
  cleanliness is a genuine (if modest) point in 8-way's favor: trying
  9-way at the same line size gives a non-integer 21,845.3 sets, a mild
  point against it. This mirrors Skylark's own reasoning for preferring an
  integer-friendly associativity/line-size combination when the raw
  detector data can't fully resolve the confound on its own.

## Overall best-guess read of the hierarchy

Upgrade's cache hierarchy is best read as **32 KiB / 8-way L1D, 256 KiB /
8-way L2 (best guess, size itself taken from `CAPACITY_RESULTS.md` rather
than independently confirmed), and a ~12 MiB / 8-way LLC (both best guess,
same capacity-sourcing caveat)** — all three sharing the same 64 B line
size (L1 confirmed; L2/LLC best-guess, since this machine never produced a
citable competing line-size measurement at either level, unlike Skylark's
genuine 64/128 B split). All three inclusion_policy pairings lean the same
direction — **non-inclusive** — with steadily decreasing confidence moving
down the hierarchy: L1 vs L2 is confidently non-inclusive (99% survived,
the cleanest result on this machine or any other team machine tested so
far); L2 vs LLC leans non-inclusive but is this machine's (and every other
machine's) structurally weakest pairing; L1 vs LLC (skip-level) is
classifier-UNCERTAIN by the strict two-class boundary, but a closer read of
its tightly-clustered, on-chip-scale reload cost supports the same
non-inclusive lean rather than contradicting it. Put together, the
best-supported single story is a cache hierarchy where **no level tested
here is inclusive of the level(s) below it** — the same overall shape as
Skylark's own read, though for a different reason: Skylark is AMD Zen 2
(publicly documented non-inclusive L3), while Upgrade is Intel Coffee
Lake, a generation/vendor where Sunbird's own Haswell-EP part instead
leaned toward an inclusive LLC snoop-filter design — noted as a genuine
open cross-machine difference among the team's own Intel parts, not
resolved further here under Phase I's timing-only discipline (no hardware
documentation or CPUID/`lscpu`-cache-field lookup performed). This is this
team's best-supported inference from the data collected, not a certainty;
the associativity values above are the most defensible point estimates
available given a real, well-documented measurement confound, not directly
observed facts.
