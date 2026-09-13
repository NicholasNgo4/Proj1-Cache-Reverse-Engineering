#!/usr/bin/env python3
"""Cross-alignment confirmation plot for line-size family-of-curves evidence
(homework step 4: "repeat with different alignments"). Consumes summary CSVs
produced by scripts/run_line_size.sh, which re-runs a bracket
of candidate strides around one already-interesting stride at several
different offset_bytes (node 0's position relative to the aligned buffer
base -- see main_code/common/line_size.h). If the detected elbow --
and which bracket stride's elbow separates from the others -- lands in the
same place regardless of offset_bytes, that is the confirmation that the
transition is a genuine, alignment-independent spatial-locality effect
rather than an artifact of always starting node 0 at the same position
relative to a physical cache line.

Produces:
  line_size_offset_elbow.{png,pdf} -- detected elbow footprint vs. candidate
      stride, one line per tested offset_bytes. Coincident lines across
      offsets is the confirmation signal for step 4; lines that diverge mean
      the transition is offset-sensitive and the coarse-pass "line size"
      reading should not be trusted without more work.
  line_size_offset_boxplots.{png,pdf} -- at the candidate stride itself, box-
      and-whisker latency by offset at a representative footprint just above
      the baseline elbow, so the distributions behind the elbow comparison
      are visible, not just the elbow points.

Also prints a plain-language stability verdict (elbow spread ratio across
offsets at the candidate stride) to stderr.

Usage:
    python3 scripts/plot_line_size_offset.py \\
        data_processed/sunbird/line_size/refine_*_summary.csv \\
        -o data_processed/sunbird/line_size/plots --machine sunbird \\
        --candidate-stride 64
"""
import argparse
import csv
import math
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from plot_line_size_family import detect_elbow, human_bytes, style_axes


def label_log_yaxis_from_data(ax, values, n_ticks=6):
    """Force readable y-tick labels on a log2 axis regardless of how narrow
    the data range is.

    matplotlib's default log-scale locator only labels exact powers of the
    base -- fine when the plotted range spans a decade/octave, but this
    plot's y-values are raw detected-elbow byte counts that routinely sit
    entirely WITHIN one octave (e.g. every offset's elbow landing between
    23.7 and 26.6 MiB, both comfortably inside [2**24, 2**25)). When that
    happens, no power-of-two tick falls inside the visible range and the
    axis renders with a title but no numbers at all (see
    data_raw/skylark/README.md's line_size/ section, step-4 L3 plots,
    2026-09-13). Fix: place ticks at values spaced evenly in log2 space
    across the ACTUAL plotted data (not matplotlib's padded axis limits),
    and label them with human_bytes instead of relying on the default
    power-of-two formatter.
    """
    finite = sorted(v for v in values if v is not None and math.isfinite(v) and v > 0)
    if not finite:
        return
    lo, hi = finite[0], finite[-1]
    if lo == hi:
        # Degenerate single-value case (e.g. a perfectly offset-independent
        # elbow): still show a labeled tick at that value plus neighbors.
        lo, hi = lo * 0.98, hi * 1.02
    log_lo, log_hi = math.log2(lo), math.log2(hi)
    ticks = [2 ** (log_lo + i * (log_hi - log_lo) / (n_ticks - 1)) for i in range(n_ticks)]
    ax.set_yticks(ticks)
    ax.set_yticklabels([human_bytes(int(round(t))) for t in ticks])
    ax.tick_params(axis="y", which="minor", left=False, labelleft=False)

REQUIRED_COLS = {"footprint_bytes", "stride_bytes", "offset_bytes", "pattern",
                  "median", "q1", "q3", "p5", "p95"}


def load(paths, pattern="random"):
    """Returns {offset_bytes: {stride_bytes: {footprint_bytes: row}}}, restricted
    to one pattern (default random -- the offset check is only meaningful for
    the prefetcher-defeating dependent-chase order; see this module's docstring
    and run_line_size.sh)."""
    out = {}
    for path in paths:
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None or not REQUIRED_COLS.issubset(reader.fieldnames):
                missing = REQUIRED_COLS - set(reader.fieldnames or [])
                raise ValueError(f"{path}: missing column(s) {missing} -- is this a "
                                  f"line_size_family refine summary (needs offset_bytes, "
                                  f"from run_line_size.sh)?")
            for row in reader:
                if row["pattern"] != pattern:
                    continue
                offset = int(float(row["offset_bytes"]))
                stride = int(float(row["stride_bytes"]))
                footprint = int(float(row["footprint_bytes"]))
                out.setdefault(offset, {}).setdefault(stride, {})[footprint] = row
    if not out:
        raise ValueError(f"no '{pattern}'-pattern rows found across {len(paths)} file(s)")
    return out


def plot_elbow_comparison(by_offset, machine, out_prefix, title_suffix, candidate_stride):
    offsets = sorted(by_offset.keys())
    cmap = matplotlib.colormaps["plasma"].resampled(max(len(offsets), 2))

    # Union of every stride tested at ANY offset -- used as a common x-axis so a
    # stride where THIS offset's curve never produced a detectable elbow shows
    # up as an actual gap (NaN) rather than being silently dropped and having
    # its neighbors bridged by a straight line, which would draw a trend
    # through two points that were never actually connected by any measurement.
    all_strides = sorted({s for by_stride in by_offset.values() for s in by_stride.keys()})

    fig, ax = plt.subplots(figsize=(7.5, 5))
    elbow_table = {}
    for i, offset in enumerate(offsets):
        by_stride = by_offset[offset]
        ys = []
        present = {}
        for stride in all_strides:
            if stride in by_stride:
                pts = sorted((fp, float(r["median"])) for fp, r in by_stride[stride].items())
                elbow = detect_elbow(pts)
            else:
                elbow = None
            ys.append(elbow if elbow is not None else float("nan"))
            if elbow is not None:
                present[stride] = elbow
        elbow_table[offset] = present
        n_present = len(present)
        if n_present:
            ax.plot(all_strides, ys, marker="o", color=cmap(i), linewidth=1.8,
                     label=f"offset={offset}B" + ("" if n_present == len(all_strides)
                                                    else f" ({n_present}/{len(all_strides)} strides)"))

    ax.axvline(candidate_stride, color="black", linestyle="--", linewidth=1.0, alpha=0.5,
               label=f"candidate {candidate_stride}B")
    ax.set_xlabel("Candidate stride (bytes)")
    ax.set_ylabel("Detected elbow footprint (bytes)")
    ax.set_yscale("log", base=2)
    label_log_yaxis_from_data(ax, [v for present in elbow_table.values() for v in present.values()])
    title = f"{machine}: line-size elbow vs. stride, by node-0 offset"
    if title_suffix:
        title += f"\n{title_suffix}"
    ax.set_title(title, fontsize=11)
    style_axes(ax)
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(f"{out_prefix}.pdf")
    fig.savefig(f"{out_prefix}.png", dpi=200)
    plt.close(fig)
    print(f"Wrote {out_prefix}.pdf and .png", file=sys.stderr)
    return elbow_table


def plot_boxplots(by_offset, machine, out_prefix, title_suffix, candidate_stride):
    offsets = sorted(by_offset.keys())
    ref_offset = offsets[0]
    if candidate_stride not in by_offset[ref_offset]:
        print(f"candidate stride {candidate_stride}B not present at offset "
              f"{ref_offset}B; skipping boxplots", file=sys.stderr)
        return

    pts = sorted((fp, float(r["median"]))
                 for fp, r in by_offset[ref_offset][candidate_stride].items())
    elbow = detect_elbow(pts)
    all_fps = sorted({fp for fp, _ in pts})
    target_fp = min(all_fps, key=lambda fp: abs(fp - elbow)) if elbow is not None \
        else all_fps[len(all_fps) // 2]

    box_data, labels, colors = [], [], []
    cmap = matplotlib.colormaps["plasma"].resampled(max(len(offsets), 2))
    for i, offset in enumerate(offsets):
        row = by_offset[offset].get(candidate_stride, {}).get(target_fp)
        if row is None:
            continue
        q1, med, q3 = float(row["q1"]), float(row["median"]), float(row["q3"])
        p5, p95 = float(row["p5"]), float(row["p95"])
        box_data.append(dict(med=med, q1=q1, q3=q3, whislo=p5, whishi=p95))
        labels.append(f"{offset}B")
        colors.append(cmap(i))

    if not box_data:
        print("No matching (offset, footprint) rows for boxplot; skipping.", file=sys.stderr)
        return

    fig, ax = plt.subplots(figsize=(1.4 * len(box_data) + 2, 4.5))
    bp = ax.bxp(box_data, showfliers=False, patch_artist=True)
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.5)
    ax.set_xticklabels(labels, rotation=0, fontsize=9)
    ax.set_xlabel("Node-0 offset past aligned base")
    ax.set_ylabel("Latency (timer ticks / access)")
    title = (f"{machine}: candidate stride {human_bytes(candidate_stride)} at "
             f"footprint {human_bytes(target_fp)}, by offset")
    if title_suffix:
        title += f"\n{title_suffix}"
    ax.set_title(title, fontsize=10)
    style_axes(ax)
    fig.tight_layout()
    fig.savefig(f"{out_prefix}.pdf")
    fig.savefig(f"{out_prefix}.png", dpi=200)
    plt.close(fig)
    print(f"Wrote {out_prefix}.pdf and .png", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("summaries", nargs="+")
    ap.add_argument("-o", "--output-dir", required=True)
    ap.add_argument("--machine", required=True)
    ap.add_argument("--candidate-stride", type=int, required=True,
                     help="the stride (bytes) being confirmed/refuted, from the "
                          "coarse family-of-curves pass")
    ap.add_argument("--title-suffix", default="")
    args = ap.parse_args()

    by_offset = load(args.summaries)
    if len(by_offset) < 2:
        print(f"WARNING: only {len(by_offset)} distinct offset_bytes value(s) found -- "
              f"step 4 needs multiple alignments to be a meaningful check", file=sys.stderr)

    elbow_table = plot_elbow_comparison(by_offset, args.machine,
                                         f"{args.output_dir}/line_size_offset_elbow",
                                         args.title_suffix, args.candidate_stride)
    plot_boxplots(by_offset, args.machine,
                  f"{args.output_dir}/line_size_offset_boxplots",
                  args.title_suffix, args.candidate_stride)

    print("-- elbow footprint by (offset, stride):", file=sys.stderr)
    for offset in sorted(elbow_table.keys()):
        print(f"   offset={offset}B: {elbow_table[offset]}", file=sys.stderr)

    cand_elbows = {offset: tbl.get(args.candidate_stride)
                   for offset, tbl in elbow_table.items()}
    known = {o: e for o, e in cand_elbows.items() if e is not None}
    n_total = len(cand_elbows)
    missing = sorted(o for o, e in cand_elbows.items() if e is None)
    if missing:
        print(f"-- candidate stride {args.candidate_stride}B: {len(missing)}/{n_total} "
              f"offset(s) produced NO detectable elbow at all within this window's footprint "
              f"range ({', '.join(f'{o}B' for o in missing)}) -- these are gaps in the plot, "
              f"not agreement; the spread below is computed only over the "
              f"{len(known)}/{n_total} offsets that did report a value", file=sys.stderr)
    if len(known) >= 2:
        lo, hi = min(known.values()), max(known.values())
        ratio = hi / lo if lo > 0 else float("inf")
        if ratio <= 1.3:
            print(f"-- candidate stride {args.candidate_stride}B: elbow stable across the "
                  f"{len(known)}/{n_total} offsets with a detectable elbow "
                  f"({lo}-{hi} bytes, {ratio:.2f}x spread) -- consistent with a genuine, "
                  f"alignment-independent transition, but see the gap warning above before "
                  f"treating this as full 8/8 agreement", file=sys.stderr)
        else:
            print(f"-- candidate stride {args.candidate_stride}B: elbow varies "
                  f"{ratio:.2f}x across offsets ({lo}-{hi} bytes) -- transition may be "
                  f"alignment-sensitive, do not cite this candidate as a clean line-size "
                  f"result without further investigation", file=sys.stderr)
    else:
        print(f"-- fewer than 2 offsets produced a detectable elbow at "
              f"{args.candidate_stride}B; cannot assess alignment-stability", file=sys.stderr)


if __name__ == "__main__":
    main()
