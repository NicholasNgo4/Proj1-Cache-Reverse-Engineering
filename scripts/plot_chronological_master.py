#!/usr/bin/env python3
"""Plot the required Moore-style chronological cross-generation figures
(PROJECT 1.pdf Section 9, Figures 4-7 / plot list items 1-15) from the
consolidated `data_processed/master/chronological_master_table.csv`.

Every column's PRIMARY plotted value is the Phase I timing-only inferred
number -- never silently replaced by a Phase II/vendor value. Where Phase II
(PMU/system-report/literature) resolved a real disagreement, an open/hollow
marker for the Phase-II value is drawn at the same x (year) position and
tied to the solid Phase-I marker with a thin vertical connector, so the
correction is visible without overwriting the observed series feeding the
report's Moore-style trend fit and frozen Hazel prediction.

Per PROJECT 1.pdf's "Plot format" rule, every one of the 15 required plots
that corresponds to a quantity in the team's frozen `PREDICTION_FREEZE.md`
table also draws that frozen model's own dashed extrapolation (solid lab
line -> dashed line starting at the last lab year, 2023, extending only to
the future year, 2028) plus the 6 held-out Hazel generations as gold star
(resolved) or open diamond (untestable for that field, e.g. an
associativity confound) markers -- never used to refit the dashed line.
Cross-architecture encoding (distinct marker shape per vendor: Intel
circle, AMD square, Arm/AArch64 triangle) is applied on every plot,
including the two-field/dual-series and categorical (inclusion) plots,
where earlier versions of this script pooled all vendors into one
undifferentiated line.

Usage:
    python3 scripts/plot_chronological_master.py \\
        data_processed/master/chronological_master_table.csv \\
        -o plots \\
        --final-csv data_processed/master/chronological_master_table_with_hazel.csv
"""
import argparse
import csv
import math
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.lines import Line2D

VENDOR_STYLE = {
    "Intel": dict(marker="o", label="Intel x86-64"),
    "AMD": dict(marker="s", label="AMD x86-64"),
    "Ampere": dict(marker="^", label="Arm / AArch64"),
}

HAZEL_COLOR = "#B8860B"
LAST_LAB_YEAR = 2023
FUTURE_YEAR = 2028

# Several quantities are genuinely near-invariant across vendors (line size:
# 64 B on 8/8 lab machines; L1D capacity/associativity: identical on 6/8) --
# that's real data, not a plotting artifact, so a lone AMD or Arm point can
# legitimately land exactly on top of the Intel line (and, when a same-year
# lab machine also shares that value, e.g. Crux/Skylark both 2019 at 64 B,
# exactly on top of an Intel MARKER too). A tiny fixed per-vendor x-offset
# keeps every vendor's own points visually distinguishable in that case
# without moving any point far enough to misrepresent its real year.
VENDOR_XJITTER = {"Intel": 0.0, "AMD": 0.3, "Ampere": -0.3}


def vendor_x(row):
    return row["year"] + VENDOR_XJITTER.get(row["vendor"], 0.0)


def load_rows(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["year"] = int(r["year"])
    rows.sort(key=lambda r: r["year"])
    return rows


def fnum(v):
    """Parses a CSV field to float, returning None for blank/NA cells
    (e.g. Thunderbird's missing LLC system-report columns, or a Hazel
    generation's confound-flagged/untestable associativity cell) rather
    than raising or silently coercing to 0."""
    if v is None or v.strip() == "":
        return None
    try:
        return float(v)
    except ValueError:
        return None


def style_axes(ax):
    ax.grid(False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_linewidth(1.2)
        ax.spines[side].set_color("black")
    ax.tick_params(width=1.1, labelsize=11)


def human_bytes(n):
    if n is None:
        return ""
    n = float(n)
    if n >= 1024 * 1024 * 1024:
        return f"{n / (1024 ** 3):g} GiB"
    if n >= 1024 * 1024:
        return f"{n / (1024 ** 2):g} MiB"
    if n >= 1024:
        return f"{n / 1024:g} KiB"
    return f"{n:g} B"


def short_label(row):
    return row["microarch"]


def annotate_points(ax, pts_with_rows):
    """Labels each (x, y, row) point with its microarchitecture, alternating
    the vertical offset for points that share an x (year) -- e.g. Ookay/
    Upgrade both 2017, Crux/Skylark both 2019 -- so the text doesn't overlap
    into an unreadable stack."""
    seen_at_year = {}
    for x, y, row in pts_with_rows:
        k = seen_at_year.get(x, 0)
        seen_at_year[x] = k + 1
        dy = 6 + 15 * k
        ax.annotate(short_label(row), (x, y), textcoords="offset points",
                    xytext=(6, dy), fontsize=7.5, color="0.25")


def base_plot(figsize=(8.5, 5.5)):
    fig, ax = plt.subplots(figsize=figsize)
    style_axes(ax)
    return fig, ax


def const_model(value):
    """A frozen-prediction model that is a flat, year-independent constant
    (PREDICTION_FREEZE.md's "no chronological trend -- <machine> analog"
    rows). Still drawn as a dashed segment from the last lab year to the
    future year so the visual grammar (solid observed -> dashed predicted)
    stays identical to a genuine growth-model prediction."""
    return lambda _t, _v=value: _v


def _draw_hazel_overlay(ax, hazel_rows, field, model_fn, hazel_jitter_years,
                         marker="*", markersize=18, star_label=None,
                         diamond_label=None, annotate=True):
    """Shared Hazel-reveal drawing logic: a filled gold star at a held-out
    Hazel generation's own real measurement for `field`, or (only when a
    frozen model exists to place it against) an open gray diamond when that
    generation's own value for this field was never resolved/was
    confound-flagged untestable. Never fabricates a star from a blank
    cell. Returns (drew_star, drew_diamond)."""
    drew_star = drew_diamond = False
    for r in hazel_rows:
        y = fnum(r[field])
        hx = r["year"] + hazel_jitter_years
        label = "Hazel " + short_label(r)
        if y is not None:
            ax.plot([hx], [y], marker=marker, markersize=markersize, color=HAZEL_COLOR,
                     markeredgecolor="black", markeredgewidth=1.0, linestyle="none",
                     zorder=5, label=star_label if not drew_star else None)
            if annotate:
                ax.annotate(label, (hx, y), textcoords="offset points",
                            xytext=(6, -13), fontsize=7, color="#7a5c00")
            drew_star = True
        elif model_fn is not None:
            hy = model_fn(r["year"])
            ax.plot([hx], [hy], marker="D", markersize=10, markerfacecolor="none",
                     markeredgecolor="0.4", markeredgewidth=1.6, linestyle="none",
                     zorder=5, label=diamond_label if not drew_diamond else None)
            if annotate:
                ax.annotate(f"{label} (untestable)", (hx, hy), textcoords="offset points",
                            xytext=(6, -13), fontsize=7, color="0.3")
            drew_diamond = True
    return drew_star, drew_diamond


def plot_series(rows, field_phase1, out_path, ylabel, title, log_y=False,
                 field_phase2=None, annotate=True, y_is_bytes=False,
                 model_fn=None, hazel_rows=None, hazel_field=None,
                 last_lab_year=LAST_LAB_YEAR, future_year=FUTURE_YEAR,
                 future_uncertainty=None, hazel_jitter_years=0.25,
                 legend_fontsize=None):
    """Generic scalar-metric-vs-year plot. field_phase1 is always drawn as
    the solid, vendor-shaped marker series (the observed/primary value),
    one connected line PER VENDOR (never a single line spanning different
    vendor families, per PROJECT 1.pdf: "Do not connect unrelated
    architectural families with a line that implies direct lineage").

    If field_phase2 is given and differs from field_phase1 at a point, an
    open marker + thin connector is added at that same year to show the
    Phase-II-resolved value without replacing the Phase-I point.

    If model_fn is given, this is treated as a "held-out prediction figure"
    (PROJECT 1.pdf Section 9's required visual logic): the frozen model's
    own dashed extrapolation is drawn from `last_lab_year` to `future_year`,
    and -- when `hazel_rows` is also given -- every held-out Hazel
    generation is overlaid as its own star (resolved) or open diamond
    (untestable for this field) at its own real introduction year. Hazel
    points are never used to refit the dashed line."""
    fig, ax = base_plot()

    by_vendor = {}
    for r in rows:
        y1 = fnum(r[field_phase1])
        if y1 is None:
            continue
        by_vendor.setdefault(r["vendor"], []).append(r)

    all_pts_for_annotation = []
    for vendor, vrows in by_vendor.items():
        vrows = sorted(vrows, key=lambda r: r["year"])
        style = VENDOR_STYLE.get(vendor, dict(marker="D", label=vendor))
        xs = [vendor_x(r) for r in vrows]
        ys = [fnum(r[field_phase1]) for r in vrows]
        ax.plot(xs, ys, color="black", marker=style["marker"], markersize=8,
                 markerfacecolor="black", linewidth=1.4, linestyle="-",
                 label=style["label"], zorder=2)
        all_pts_for_annotation.extend(zip(xs, ys, vrows))
    if annotate:
        all_pts_for_annotation.sort(key=lambda t: t[0])
        annotate_points(ax, all_pts_for_annotation)

    if field_phase2:
        drew_p2_label = False
        for r in rows:
            y1 = fnum(r[field_phase1])
            y2 = fnum(r[field_phase2])
            if y1 is None or y2 is None:
                continue
            if abs(y1 - y2) < 1e-9:
                continue
            vx = vendor_x(r)
            ax.plot([vx, vx], [y1, y2], color="0.4", linewidth=1.0,
                     linestyle=":", zorder=1)
            ax.plot(vx, y2, marker="o", markersize=8, markerfacecolor="white",
                     markeredgecolor="black", markeredgewidth=1.3, linestyle="none",
                     label="Phase II (PMU/system-report/literature) resolved value"
                           if not drew_p2_label else None, zorder=3)
            drew_p2_label = True

    if model_fn is not None:
        dash_xs = [last_lab_year, future_year]
        dash_ys = [model_fn(last_lab_year), model_fn(future_year)]
        ax.plot(dash_xs, dash_ys, color="black", linestyle="--", linewidth=1.6,
                 marker="x", markersize=8, markeredgewidth=1.6, zorder=2,
                 label=f"Frozen model, dashed extrapolation to {future_year}")
        if future_uncertainty is not None:
            lo, hi = future_uncertainty
            yv = model_fn(future_year)
            ax.errorbar([future_year], [yv], yerr=[[yv - lo], [hi - yv]],
                         color="0.35", capsize=5, linewidth=1.6, zorder=2)

    drew_star = drew_diamond = False
    if hazel_rows:
        drew_star, drew_diamond = _draw_hazel_overlay(
            ax, hazel_rows, hazel_field or field_phase1, model_fn, hazel_jitter_years,
            star_label="Hazel (validated, held-out)",
            diamond_label="Hazel (untestable this field)", annotate=annotate)

    if log_y:
        ax.set_yscale("log", base=2)
        if y_is_bytes:
            ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: human_bytes(v)))
            distinct_vals = {fnum(r[field_phase1]) for r in rows if fnum(r[field_phase1])}
            if field_phase2:
                distinct_vals |= {fnum(r[field_phase2]) for r in rows if fnum(r[field_phase2])}
            if model_fn is not None:
                distinct_vals |= {model_fn(last_lab_year), model_fn(future_year)}
            if hazel_rows:
                hf = hazel_field or field_phase1
                distinct_vals |= {fnum(r[hf]) for r in hazel_rows if fnum(r[hf]) is not None}
            if future_uncertainty is not None:
                distinct_vals |= set(future_uncertainty)
            ax.set_yticks(sorted(v for v in distinct_vals if v))
            ax.set_yticks([], minor=True)

    ax.set_xlabel("Year (processor generation / microarchitecture introduction)")
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=12)
    all_years = [r["year"] for r in rows]
    if model_fn is not None:
        all_years.append(future_year)
    if hazel_rows:
        all_years += [r["year"] for r in hazel_rows]
    ax.set_xlim(min(all_years) - 1, max(all_years) + 1)
    ax.legend(frameon=False, fontsize=legend_fontsize or (7.5 if hazel_rows else 9), loc="best")
    fig.tight_layout()
    fig.savefig(f"{out_path}.pdf")
    fig.savefig(f"{out_path}.png", dpi=200)
    plt.close(fig)
    print(f"Wrote {out_path}.pdf/.png", file=sys.stderr)


def plot_dual_series(rows, field_a, label_a, field_b, label_b, out_path, ylabel, title,
                      model_fn_a=None, model_fn_b=None, hazel_rows=None,
                      hazel_field_a=None, hazel_field_b=None,
                      last_lab_year=LAST_LAB_YEAR, future_year=FUTURE_YEAR):
    """Two metrics vs year on the same axes (used for LLC hit-latency +
    LLC-to-memory miss penalty, and for the two PMU-derived normalized
    metrics). Both metrics are drawn SOLID and per-vendor -- dashed is
    reserved exclusively for a frozen-model future-year extrapolation, per
    PROJECT 1.pdf's plot-format rule ("do not draw the prediction as a
    dashed overlay across already measured years"); an earlier version of
    this function used a dashed line for the observed field_b series, which
    both violated that rule and (by pooling every vendor into one line)
    connected unrelated architectural families across the same year, e.g.
    2019's Intel Crux and AMD Skylark points, with a line that implied a
    single lineage. Marker shape now encodes vendor for both fields, and
    each field keeps its own line only within one vendor's own points."""
    fig, ax = base_plot()
    field_specs = [
        (field_a, "black", model_fn_a, hazel_field_a or field_a),
        (field_b, "0.45", model_fn_b, hazel_field_b or field_b),
    ]
    legend_handles = [Line2D([0], [0], color="black", lw=1.4, label=label_a),
                       Line2D([0], [0], color="0.45", lw=1.4, label=label_b)]

    for field, color, model_fn, _hf in field_specs:
        by_vendor = {}
        for r in rows:
            if fnum(r[field]) is None:
                continue
            by_vendor.setdefault(r["vendor"], []).append(r)
        for vendor, vrows in by_vendor.items():
            vrows = sorted(vrows, key=lambda r: r["year"])
            style = VENDOR_STYLE.get(vendor, dict(marker="D"))
            xs = [vendor_x(r) for r in vrows]
            ys = [fnum(r[field]) for r in vrows]
            ax.plot(xs, ys, color=color, marker=style["marker"], markersize=8,
                     markerfacecolor=color, linewidth=1.4, linestyle="-", zorder=2)
        if model_fn is not None:
            dash_xs = [last_lab_year, future_year]
            dash_ys = [model_fn(last_lab_year), model_fn(future_year)]
            ax.plot(dash_xs, dash_ys, color=color, linestyle="--", linewidth=1.6,
                     marker="x", markersize=7, markeredgewidth=1.4, zorder=2)

    if model_fn_a is not None or model_fn_b is not None:
        legend_handles.append(Line2D([0], [0], color="black", lw=1.6, linestyle="--",
                                      marker="x", label=f"Frozen model, dashed extrapolation to {future_year}"))

    hazel_markers = [("*", 16), ("P", 11)]
    if hazel_rows:
        for (field, color, model_fn, hf), (mk, ms), lab in zip(
                field_specs, hazel_markers, (label_a, label_b)):
            drew_star, _ = _draw_hazel_overlay(
                ax, hazel_rows, hf, None, 0.25, marker=mk, markersize=ms,
                star_label=None, annotate=False)
            if drew_star:
                legend_handles.append(Line2D([0], [0], color=HAZEL_COLOR, marker=mk,
                                              markeredgecolor="black", linestyle="none",
                                              markersize=ms * 0.7,
                                              label=f"Hazel {lab} (validated, held-out)"))

    ax.set_xlabel("Year (processor generation / microarchitecture introduction)")
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=12)
    all_years = [r["year"] for r in rows]
    if model_fn_a is not None or model_fn_b is not None:
        all_years.append(future_year)
    if hazel_rows:
        all_years += [r["year"] for r in hazel_rows]
    ax.set_xlim(min(all_years) - 1, max(all_years) + 1)
    ax.legend(handles=legend_handles, frameon=False, fontsize=8, loc="best")
    fig.tight_layout()
    fig.savefig(f"{out_path}.pdf")
    fig.savefig(f"{out_path}.png", dpi=200)
    plt.close(fig)
    print(f"Wrote {out_path}.pdf/.png", file=sys.stderr)


def plot_final_combined(lab_rows, hazel_rows, field, out_path, ylabel, title,
                         log_y=False, y_is_bytes=False, untestable_years=None):
    """Final post-validation historical-comparison figure: combines every
    successfully measured system -- the 8 lab machines (solid, vendor-shaped,
    connected line, exactly as fit) plus any already-validated Hazel
    generation (drawn as an unconnected filled star, never blended into the
    lab trend line) -- sorted by year, in the same empirical spirit as
    Moore's original plot. `untestable_years` optionally lists Hazel years
    whose value for this specific field was never resolved (shown as an
    open gray diamond + annotation instead of a fabricated star)."""
    fig, ax = base_plot()

    by_vendor = {}
    for r in lab_rows:
        if fnum(r[field]) is None:
            continue
        by_vendor.setdefault(r["vendor"], []).append(r)

    all_pts_for_annotation = []
    for vendor, vrows in by_vendor.items():
        vrows = sorted(vrows, key=lambda r: r["year"])
        style = VENDOR_STYLE.get(vendor, dict(marker="D", label=vendor))
        xs = [vendor_x(r) for r in vrows]
        ys = [fnum(r[field]) for r in vrows]
        ax.plot(xs, ys, color="black", marker=style["marker"], markersize=8,
                 markerfacecolor="black", linewidth=1.4, linestyle="-",
                 label=style["label"], zorder=2)
        all_pts_for_annotation.extend(zip(xs, ys, vrows))
    all_pts_for_annotation.sort(key=lambda t: t[0])
    annotate_points(ax, all_pts_for_annotation)

    untestable_years = untestable_years or set()
    drew_star_label = drew_diamond_label = False
    fig.canvas.draw()  # force autoscale from lab data before placing Hazel markers
    for r in hazel_rows:
        y = fnum(r[field])
        hx = r["year"] + 0.3
        if r["year"] in untestable_years or y is None:
            ylo, yhi = ax.get_ylim()
            hy = (ylo * yhi) ** 0.5 if log_y else (ylo + yhi) / 2.0
            ax.plot([hx], [hy], marker="D", markersize=11, markerfacecolor="none",
                     markeredgecolor="0.4", markeredgewidth=1.6, linestyle="none",
                     zorder=5,
                     label="Hazel (untestable this field)" if not drew_diamond_label else None)
            ax.annotate(f"{short_label(r)} (untestable)", (hx, hy),
                        textcoords="offset points", xytext=(6, 6), fontsize=7.5, color="0.3")
            drew_diamond_label = True
        else:
            ax.plot([hx], [y], marker="*", markersize=18, color="#B8860B",
                     markeredgecolor="black", markeredgewidth=1.0, linestyle="none",
                     zorder=5,
                     label="Hazel (validated, held-out)" if not drew_star_label else None)
            ax.annotate(short_label(r), (hx, y), textcoords="offset points",
                        xytext=(6, -16), fontsize=7.5, color="#7a5c00")
            drew_star_label = True

    if log_y:
        ax.set_yscale("log", base=2)
        if y_is_bytes:
            ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: human_bytes(v)))
            distinct_vals = {fnum(r[field]) for r in lab_rows if fnum(r[field]) is not None}
            distinct_vals |= {fnum(r[field]) for r in hazel_rows if fnum(r[field]) is not None}
            ax.set_yticks(sorted(distinct_vals))
            ax.set_yticks([], minor=True)

    ax.set_xlabel("Year (processor generation / microarchitecture introduction)")
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=12)
    all_years = [r["year"] for r in lab_rows] + [r["year"] + 0.3 for r in hazel_rows]
    ax.set_xlim(min(all_years) - 1, max(all_years) + 1)
    ax.legend(frameon=False, fontsize=7.5, loc="best")
    fig.tight_layout()
    fig.savefig(f"{out_path}.pdf")
    fig.savefig(f"{out_path}.png", dpi=200)
    plt.close(fig)
    print(f"Wrote {out_path}.pdf/.png", file=sys.stderr)


def plot_hit_rate(rows, field, field_lo, field_hi, out_path, ylabel, title):
    """Plot #14: the software-only timing-derived hit-rate estimator (Hhat,
    PROJECT 1.pdf Sec. 8.5) vs. year, evaluated at ONE identical standardized
    workload size across every machine (262,144 B / 256 KiB -- the largest
    common footprint tested on every machine's sweep that still shows real
    cross-machine variation rather than having already collapsed near 0 or
    1; see CHRONOLOGICAL_MASTER_TABLE.md for the size-selection rationale).
    Bootstrap 95% CI error bars come directly from the estimator's own
    output, not fabricated. Not part of PREDICTION_FREEZE.md's frozen
    numeric table (the estimator/PMU-normalized plots were never frozen
    lab-only predictions to test against Hazel), so no dashed
    extrapolation or Hazel overlay is drawn here."""
    fig, ax = base_plot()
    by_vendor = {}
    for r in rows:
        y = fnum(r[field])
        if y is None:
            continue
        by_vendor.setdefault(r["vendor"], []).append(r)

    all_pts_for_annotation = []
    for vendor, vrows in by_vendor.items():
        vrows = sorted(vrows, key=lambda r: r["year"])
        style = VENDOR_STYLE.get(vendor, dict(marker="D", label=vendor))
        xs = [vendor_x(r) for r in vrows]
        ys = [fnum(r[field]) for r in vrows]
        lo = [fnum(r[field]) - fnum(r[field_lo]) for r in vrows]
        hi = [fnum(r[field_hi]) - fnum(r[field]) for r in vrows]
        ax.errorbar(xs, ys, yerr=[lo, hi], color="black", marker=style["marker"],
                     markersize=8, markerfacecolor="black", linewidth=1.4,
                     linestyle="-", capsize=4, elinewidth=1.0, label=style["label"])
        all_pts_for_annotation.extend(zip(xs, ys, vrows))
    all_pts_for_annotation.sort(key=lambda t: t[0])
    annotate_points(ax, all_pts_for_annotation)

    ax.set_ylim(0.65, 1.05)
    ax.set_xlabel("Year (processor generation / microarchitecture introduction)")
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=12)
    all_years = [r["year"] for r in rows]
    ax.set_xlim(min(all_years) - 1, max(all_years) + 1)
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    fig.tight_layout()
    fig.savefig(f"{out_path}.pdf")
    fig.savefig(f"{out_path}.png", dpi=200)
    plt.close(fig)
    print(f"Wrote {out_path}.pdf/.png", file=sys.stderr)


INCL_ORDER = ["NON-INCLUSIVE", "UNCERTAIN", "INCLUSIVE"]


def incl_category(cell):
    c = cell.upper()
    if c.startswith("NON-INCLUSIVE"):
        return "NON-INCLUSIVE"
    if c.startswith("UNCERTAIN"):
        return "UNCERTAIN"
    if c.startswith("INCLUSIVE"):
        return "INCLUSIVE"
    return "UNCERTAIN"


def plot_inclusion(rows, out_path, hazel_rows=None, predicted=None,
                    last_lab_year=LAST_LAB_YEAR, future_year=FUTURE_YEAR):
    """Categorical inclusion/exclusion-vs-year plot. `predicted`, when
    given, is {field: predicted_category} from PREDICTION_FREEZE.md's own
    frozen call for that pairing -- drawn as a short dashed guideline from
    the last lab year to the future year (the categorical equivalent of a
    numeric plot's dashed extrapolation: the model here is "stays at this
    frozen category," not a fitted curve). Each held-out Hazel generation's
    ACTUAL measured category is then overlaid as an open, gold-edged marker
    at its own real year, never used to move the dashed guideline."""
    fig, ax = base_plot(figsize=(9.5, 5))
    # A small fixed x-jitter per pairing keeps all three pairings visible
    # side-by-side even when two land on the identical (year, category) cell
    # -- e.g. Crux and Skylark both reading L2-vs-LLC as NON-INCLUSIVE in
    # 2019 -- rather than one marker silently occluding another.
    pairings = [("incl_l1_l2", "L1 vs L2", "o", -0.10), ("incl_l2_llc", "L2 vs LLC", "s", 0.0),
                ("incl_l1_llc", "L1 vs LLC (skip-level)", "^", 0.10)]
    y_of = {cat: i for i, cat in enumerate(INCL_ORDER)}
    for field, label, marker, jitter in pairings:
        pts = [(r["year"] + jitter, y_of[incl_category(r[field])]) for r in rows]
        pts.sort()
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        ax.plot(xs, ys, color="black", marker=marker, markersize=9,
                 markerfacecolor="black", linewidth=0, label=label)

        if predicted and field in predicted:
            pred_y = y_of[predicted[field]]
            ax.plot([last_lab_year + jitter, future_year + jitter], [pred_y, pred_y],
                     color="black", linestyle="--", linewidth=1.4, marker="x",
                     markersize=7, zorder=2)

        if hazel_rows:
            hxs, hys = [], []
            for r in hazel_rows:
                cell = r.get(field, "")
                if not cell:
                    continue
                hxs.append(r["year"] + jitter)
                hys.append(y_of[incl_category(cell)])
            if hxs:
                ax.plot(hxs, hys, marker=marker, markersize=11, markerfacecolor=HAZEL_COLOR,
                         markeredgecolor="black", markeredgewidth=1.0, linestyle="none", zorder=5)

    legend_handles = [Line2D([0], [0], color="black", marker=m, markersize=9,
                              markerfacecolor="black", linestyle="none", label=label)
                       for _f, label, m, _j in pairings]
    if predicted:
        legend_handles.append(Line2D([0], [0], color="black", linestyle="--", marker="x",
                                      label=f"Frozen prediction, dashed to {future_year}"))
    if hazel_rows:
        legend_handles.append(Line2D([0], [0], color=HAZEL_COLOR, marker="D", markeredgecolor="black",
                                      linestyle="none", markersize=9,
                                      label="Hazel (validated, held-out; shape = pairing)"))

    ax.set_yticks(range(len(INCL_ORDER)))
    ax.set_yticklabels(INCL_ORDER)
    ax.set_ylim(-0.5, len(INCL_ORDER) - 0.5)
    ax.set_xlabel("Year (processor generation / microarchitecture introduction)")
    ax.set_ylabel("Inclusion / exclusion behavior (categorical)")
    ax.set_title("Inclusion/exclusion behavior vs. year, per cache-level pairing", fontsize=12)
    all_years = [r["year"] for r in rows]
    if predicted:
        all_years.append(future_year)
    if hazel_rows:
        all_years += [r["year"] for r in hazel_rows]
    ax.set_xlim(min(all_years) - 1, max(all_years) + 1)
    ax.legend(handles=legend_handles, frameon=False, fontsize=8.5, loc="center left",
              bbox_to_anchor=(1.0, 0.5))
    fig.tight_layout()
    fig.savefig(f"{out_path}.pdf")
    fig.savefig(f"{out_path}.png", dpi=200)
    plt.close(fig)
    print(f"Wrote {out_path}.pdf/.png", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv_path")
    ap.add_argument("-o", "--out-dir", required=True)
    ap.add_argument("--final-csv",
                     help="Post-validation combined dataset (8 lab rows + the 6 "
                          "held-out Hazel generations), e.g. "
                          "chronological_master_table_with_hazel.csv, used both for "
                          "the dashed frozen-prediction overlay on every applicable "
                          "chrono_* plot and for the final historical-comparison plots.")
    args = ap.parse_args()

    import os
    os.makedirs(args.out_dir, exist_ok=True)
    rows = load_rows(args.csv_path)

    def p(name):
        return os.path.join(args.out_dir, name)

    # Held-out Hazel generations (broadwell, skylake, cascadelake,
    # icelake_6326, genoa, sapphirerapids -- the 6 generations that actually
    # ran the full Phase-I suite; loaded once here (BEFORE the main plot
    # set) and reused by every chrono_* plot's dashed frozen-prediction
    # overlay, by the Law 1/Law 2 evidence plots, and by the final combined
    # comparison. Per PREDICTION_FREEZE.md, none of this data is ever used
    # to refit a frozen model -- only to evaluate it at each generation's
    # own real introduction year.
    hazel_rows = []
    lab_rows = rows
    if args.final_csv:
        final_rows = load_rows(args.final_csv)
        lab_machines = {r["machine"] for r in rows}
        lab_rows = [r for r in final_rows if r["machine"] in lab_machines]
        hazel_rows = [r for r in final_rows if r["machine"] not in lab_machines]

    # Frozen models from PREDICTION_FREEZE.md's "Frozen Lab-Only Prediction
    # Table" -- each is either the Chen-Ngo Capacity Doubling Law (L2
    # capacity only), the Chen-Ngo Invariance Law (a flat constant), or one
    # of the table's "no chronological trend -- Sunbird analog" flat
    # constants (Sunbird's own 2014 value, since Sunbird was the frozen
    # model's home-generation anchor). All target generation is `haswell`
    # in the freeze table, evaluated here at every held-out generation's own
    # real year, exactly as the freeze record requires.
    def law1_model(t):
        return 256 * 1024 * (2 ** ((t - 2014) / 3.0))

    def law2_model(_t):
        return 32768

    MODELS = {
        "l1_size_b": law2_model,
        "l1_assoc_phase1": const_model(8),
        "l1_hit_ns": const_model(4.14),
        "l1_missp_ns": const_model(49.6),
        "l2_size_b": law1_model,
        "l2_assoc_phase1": const_model(8),
        "l2_hit_ns": const_model(10.73),
        "l2_missp_ns": const_model(113.6),
        "llc_size_phase1_b": const_model(31457280),
        "llc_assoc_phase1": const_model(20),  # Phase-II-corrected prediction, not Sunbird's raw Phase-I 9
        "llc_hit_ns": const_model(23.37),
        "llc_missp_ns": const_model(248.8),
        "l1_line_b": const_model(64),
    }

    # 1. L1D capacity vs year
    plot_series(rows, "l1_size_b", p("chrono_01_l1_capacity"),
                "L1D capacity (bytes, log2)", "L1D capacity vs. year",
                log_y=True, y_is_bytes=True,
                model_fn=MODELS["l1_size_b"], hazel_rows=hazel_rows,
                future_uncertainty=(32768, 65536))
    # 2. L1D associativity vs year
    plot_series(rows, "l1_assoc_phase1", p("chrono_02_l1_associativity"),
                "L1D associativity (ways)", "L1D associativity vs. year",
                field_phase2="l1_assoc_pmu",
                model_fn=MODELS["l1_assoc_phase1"], hazel_rows=hazel_rows,
                future_uncertainty=(4, 12))
    # 3. L1D hit latency vs year (ns/access)
    plot_series(rows, "l1_hit_ns", p("chrono_03_l1_hit_latency"),
                "L1D hit latency (ns/access)", "L1D hit latency vs. year",
                model_fn=MODELS["l1_hit_ns"], hazel_rows=hazel_rows)
    # 4. L1 miss penalty vs year
    plot_series(rows, "l1_missp_ns", p("chrono_04_l1_miss_penalty"),
                "L1 miss penalty, L1→L2 (ns/access)", "L1 miss penalty vs. year",
                model_fn=MODELS["l1_missp_ns"], hazel_rows=hazel_rows)
    # 5. L2 capacity per core vs year
    plot_series(rows, "l2_size_b", p("chrono_05_l2_capacity"),
                "L2 capacity per core (bytes, log2)", "L2 capacity per core vs. year",
                log_y=True, y_is_bytes=True,
                model_fn=MODELS["l2_size_b"], hazel_rows=hazel_rows,
                future_uncertainty=(law1_model(LAST_LAB_YEAR), 2 * law1_model(FUTURE_YEAR)))
    # 6. L2 associativity vs year
    plot_series(rows, "l2_assoc_phase1", p("chrono_06_l2_associativity"),
                "L2 associativity (ways)", "L2 associativity vs. year",
                field_phase2="l2_assoc_pmu",
                model_fn=MODELS["l2_assoc_phase1"], hazel_rows=hazel_rows,
                future_uncertainty=(4, 8))
    # 7. L2 hit latency vs year
    plot_series(rows, "l2_hit_ns", p("chrono_07_l2_hit_latency"),
                "L2 hit latency (ns/access)", "L2 hit latency vs. year",
                model_fn=MODELS["l2_hit_ns"], hazel_rows=hazel_rows)
    # 8. L2 miss penalty vs year
    plot_series(rows, "l2_missp_ns", p("chrono_08_l2_miss_penalty"),
                "L2 miss penalty, L2→LLC (ns/access)", "L2 miss penalty vs. year",
                model_fn=MODELS["l2_missp_ns"], hazel_rows=hazel_rows)
    # 9. LLC capacity vs year (sharing domain) + normalized MiB/core
    plot_series(rows, "llc_size_phase1_b", p("chrono_09a_llc_capacity_domain"),
                "LLC capacity, sharing domain (bytes, log2)",
                "LLC capacity (sharing domain) vs. year",
                log_y=True, y_is_bytes=True, field_phase2="llc_size_pmu_b",
                model_fn=MODELS["llc_size_phase1_b"], hazel_rows=hazel_rows,
                future_uncertainty=(8 * 1024 * 1024, 52 * 1024 * 1024))
    plot_series(rows, "llc_mib_per_core", p("chrono_09b_llc_capacity_per_core"),
                "LLC capacity per core within its sharing domain (MiB)",
                "LLC capacity per core (normalized) vs. year")
    # 10. LLC associativity/effective vs year
    plot_series(rows, "llc_assoc_phase1", p("chrono_10_llc_associativity"),
                "LLC associativity (ways, effective)", "LLC associativity vs. year",
                field_phase2="llc_assoc_pmu",
                model_fn=MODELS["llc_assoc_phase1"], hazel_rows=hazel_rows,
                future_uncertainty=(15, 20))
    # 11. LLC hit latency and LLC-to-memory miss penalty vs year
    plot_dual_series(rows, "llc_hit_ns", "LLC hit latency",
                      "llc_missp_ns", "LLC→DRAM miss penalty",
                      p("chrono_11_llc_latency_and_miss_penalty"),
                      "Latency (ns/access)",
                      "LLC hit latency and LLC→DRAM miss penalty vs. year",
                      model_fn_a=MODELS["llc_hit_ns"], model_fn_b=MODELS["llc_missp_ns"],
                      hazel_rows=hazel_rows)
    # 12. Cache line/block size vs year
    plot_series(rows, "l1_line_b", p("chrono_12_line_size"),
                "Cache line size (bytes)", "L1D line size vs. year (LLC line size noted per-machine "
                "in CHRONOLOGICAL_MASTER_TABLE.md where it differs)",
                model_fn=MODELS["l1_line_b"], hazel_rows=hazel_rows)
    # 13. Inclusion/exclusion behavior vs year (categorical)
    PREDICTED_INCL = {
        "incl_l1_l2": "NON-INCLUSIVE",
        "incl_l2_llc": "UNCERTAIN",
        "incl_l1_llc": "UNCERTAIN",
    }
    plot_inclusion(rows, p("chrono_13_inclusion_exclusion"),
                   hazel_rows=hazel_rows, predicted=PREDICTED_INCL)
    # 14. Timing-derived hit-rate/residency metric vs year, one identical
    # standardized workload (262,144 B / 256 KiB) across all 8 machines.
    # Not part of the frozen PREDICTION_FREEZE.md table -- no dashed
    # extrapolation/Hazel overlay (see plot_hit_rate's own docstring).
    plot_hit_rate(rows, "hhat_256kib", "hhat_256kib_ci_lower", "hhat_256kib_ci_upper",
                  p("chrono_14_software_hit_rate"),
                  "Estimated hit rate, Ĥ (256 KiB workload, bootstrap 95% CI)",
                  "Software-only timing-derived hit rate vs. year\n"
                  "(identical 262,144 B standardized workload, every machine)")
    # 15. At least 2 PMU-derived normalized metrics vs year. Also not part
    # of the frozen prediction table -- no dashed extrapolation/Hazel
    # overlay, but vendor marker-shape encoding is still applied (fixed
    # from an earlier version that pooled every vendor into one
    # undifferentiated line for each metric).
    plot_dual_series(rows, "pmu_l1missrate_at_l1fp_pct", "L1 miss rate @ L1 footprint (sanity check)",
                      "pmu_cachemissrate_at_llcfp_pct", "Generic cache-miss rate @ LLC footprint",
                      p("chrono_15_pmu_normalized_metrics"),
                      "Miss rate (%)",
                      "PMU-derived normalized metrics vs. year")

    # Law 1 (Chen-Ngo Cache Capacity Doubling Law): frozen model
    # C(t) = 256 KiB * 2^((t-2014)/3), dashed extrapolation 2023->2028,
    # overlaid with each held-out Hazel generation's own L2 reading at its
    # own introduction year (star if resolved, open diamond where that
    # generation's own L2 boundary was never cleanly resolved -- see each
    # machine's own Cache Hierarchy and Capacity subsection). Kept as its
    # own dedicated figure (Section 9.1's "Our team's cache laws" evidence
    # plot) in addition to the identical overlay now also drawn on
    # chrono_05_l2_capacity above.
    plot_series(
        rows, "l2_size_b", p("law1_l2_capacity_heldout"),
        "L2 capacity per core (bytes, log2)",
        "Law 1 (Chen–Ngo Capacity Doubling): frozen prediction and held-out reveal",
        model_fn=law1_model, hazel_rows=hazel_rows,
        future_uncertainty=(law1_model(LAST_LAB_YEAR), 2 * law1_model(FUTURE_YEAR)),
        log_y=True, y_is_bytes=True,
    )

    # Law 2 (Chen-Ngo Cache Invariance Law): frozen model is the constant
    # 6-of-8 majority baseline (32,768 B), not a per-machine curve fit.
    # Every held-out Hazel generation has a resolved L1D reading (4 of 6
    # match the 32,768 B baseline exactly; icelake_6326 and
    # sapphirerapids are genuine deviations, same as this law's own two
    # lab-fleet exceptions), so all 6 are drawn as stars, never diamonds.
    # Kept as its own dedicated figure alongside the identical overlay now
    # also drawn on chrono_01_l1_capacity above.
    plot_series(
        rows, "l1_size_b", p("law2_l1d_invariance_heldout"),
        "L1D capacity (bytes, log2)",
        "Law 2 (Chen–Ngo Invariance): frozen prediction and held-out reveal",
        model_fn=law2_model, hazel_rows=hazel_rows,
        future_uncertainty=(32768, 65536),
        log_y=True, y_is_bytes=True,
    )

    # Final post-validation historical comparison: now that the frozen
    # lab-only prediction has been checked against all 6 held-out Hazel
    # generations (Section "Held-Out Prediction Evaluation"), combine
    # every successfully measured system -- 8 lab machines + 6 validated
    # Hazel generations -- into one chronological dataset, sorted oldest
    # to newest, in the same empirical spirit as Moore's own plot.
    if args.final_csv:
        plot_final_combined(
            lab_rows, hazel_rows, "l1_size_b", p("final_01_l1_capacity_with_hazel"),
            "L1D capacity (bytes, log2)",
            "Final combined comparison: L1D capacity vs. year (lab + validated Hazel)",
            log_y=True, y_is_bytes=True,
        )
        plot_final_combined(
            lab_rows, hazel_rows, "l2_size_b", p("final_02_l2_capacity_with_hazel"),
            "L2 capacity per core (bytes, log2)",
            "Final combined comparison: L2 capacity per core vs. year (lab + validated Hazel)",
            log_y=True, y_is_bytes=True,
            untestable_years={r["year"] for r in hazel_rows if fnum(r["l2_size_b"]) is None},
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
