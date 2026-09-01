#!/usr/bin/env python3
"""replot.py -- regenerate ANY registered figure from the terminal, with datapoints or groups removed.

Every figure in copy.ai has a recorded data spreadsheet (`ablation_plots/data/<name>.csv`, written by
lib.record_plot) and an entry in PLOT_SETTINGS.json holding its axis labels and plot type.  This reads
those two things, applies whatever filters you ask for, and redraws the figure -- so you can make a
"without this cell" or "without this group" version on the fly without editing any builder.

    # what can I replot?
    python3 replot.py --list
    python3 replot.py --list kk            # only names containing "kk"

    # what is in this figure's spreadsheet?
    python3 replot.py G1_violin2_mitotic_duration --show

    # drop a group, drop a cell, drop rows by value
    python3 replot.py G1_violin2_mitotic_duration --drop-group "Off-target" -o /tmp/no_offtarget.png
    python3 replot.py G4_polar_bar --drop-batch "20251029 triple_ablation_12"
    python3 replot.py G3_chromo_length --min length_um 3 --max length_um 12
    python3 replot.py G2_duration_combined --keep-group "1-Sisterless,3-Sisterless"

    # use your own spreadsheet instead of the recorded one (same column names)
    python3 replot.py G1_violin2_mitotic_duration --input ~/Downloads/my_edit.csv

    # or just re-run the figure's real builder, untouched
    python3 replot.py G4_lagging_bar --rebuild

Notes
  * the default output is /Volumes/4 MB/_scratch/replot/<name>.png -- it does NOT overwrite the deck
    figure unless you pass -o with the deck path, so an exploratory version can never silently become
    the published one.
  * --rebuild runs the registered generating script, which DOES rewrite the deck figure (that is the
    point of it) -- it is the only mode that touches published output.
  * filters are reported in the figure title, so a filtered plot always says what was removed.
"""
import argparse, csv, json, os, subprocess, sys

ROOT = "/Volumes/4 MB"
PLOTS = f"{ROOT}/ablation_plots"
SETTINGS = f"{PLOTS}/PLOT_SETTINGS.json"
OUTDIR = f"{ROOT}/_scratch/replot"
csv.field_size_limit(10 ** 9)


def load_settings():
    with open(SETTINGS) as f:
        return json.load(f)


def data_path(name, S):
    rel = (S.get(name) or {}).get("data") or f"data/{name}.csv"
    return os.path.join(PLOTS, rel)


def read_rows(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def numeric(rows, col):
    out = []
    for r in rows:
        try:
            out.append(float(r[col]))
        except Exception:
            pass
    return out


def guess_cols(rows):
    """(category column, value column) -- first mostly-text col and last mostly-numeric col."""
    if not rows:
        return None, None
    cols = list(rows[0].keys())
    num = []
    for c in cols:
        vals = [r.get(c, "") for r in rows[:200]]
        ok = 0
        for v in vals:
            try:
                float(v); ok += 1
            except Exception:
                pass
        num.append(ok > 0.8 * max(1, len(vals)))
    # a group column is TEXT, has few distinct values, and is not the per-row identifier
    PREF = ("cohort", "group", "category", "behavior", "behaviour", "phase", "label", "condition", "state")
    text = [c for c, n in zip(cols, num) if not n]
    def nuniq(c):
        return len({r.get(c, "") for r in rows})
    named = [c for c in text if c.lower() in PREF]
    fewish = [c for c in text if nuniq(c) <= max(2, len(rows) * 0.4) and c.lower() not in ("batch", "cell", "batch_name")]
    cat = (named or fewish or text or [None])[0]
    val = next((c for c, n in reversed(list(zip(cols, num))) if n), None)
    return cat, val


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("plot", nargs="?", help="figure name, e.g. G1_violin2_mitotic_duration")
    ap.add_argument("--list", nargs="?", const="", metavar="SUBSTR", help="list replottable figures")
    ap.add_argument("--show", action="store_true", help="print the figure's spreadsheet columns + groups")
    ap.add_argument("--input", help="use this CSV instead of the recorded one")
    ap.add_argument("-o", "--out", help="output PNG path")
    ap.add_argument("--drop-group", default="", help="comma-separated group values to remove")
    ap.add_argument("--keep-group", default="", help="comma-separated group values to keep (all others dropped)")
    ap.add_argument("--drop-batch", default="", help="comma-separated batch names to remove")
    ap.add_argument("--group-col", help="which column holds the group (default: guessed)")
    ap.add_argument("--value-col", help="which column holds the value (default: guessed)")
    ap.add_argument("--min", nargs=2, action="append", metavar=("COL", "V"), default=[])
    ap.add_argument("--max", nargs=2, action="append", metavar=("COL", "V"), default=[])
    ap.add_argument("--kind", choices=["violin", "box", "bar", "scatter"], help="override the drawing")
    ap.add_argument("--rebuild", action="store_true", help="run the figure's registered builder instead")
    a = ap.parse_args()

    S = load_settings()

    if a.list is not None:
        q = a.list.lower()
        names = sorted(n for n in S if not S[n].get("retired"))
        for n in names:
            if q and q not in n.lower():
                continue
            p = data_path(n, S)
            mark = " " if os.path.exists(p) else "*"      # * = no recorded spreadsheet, use --rebuild
            num = S[n].get("plot_number")
            print(f"{mark}{('#'+str(num)) if num else '':>6s}  {n}")
        print("\n(* = no recorded data spreadsheet; use --rebuild for those)")
        return

    if not a.plot:
        ap.print_help(); return

    if a.plot not in S:
        near = [n for n in S if a.plot.lower() in n.lower()]
        print(f"unknown figure {a.plot!r}." + (f" did you mean: {near[:8]}" if near else
              " run --list to see the names."))
        sys.exit(1)

    if a.rebuild:
        code = (S[a.plot].get("code") or "")
        gen = code.split("__")[-1] if "__" in code else ""
        script = os.path.join(f"{ROOT}/ablation_figures_20260625", os.path.basename(gen)) if gen else ""
        if not script or not os.path.exists(script):
            print(f"no live builder recorded for {a.plot} (code={code!r})"); sys.exit(1)
        print(f"running {script}")
        sys.exit(subprocess.call([sys.executable, "-u", script]))

    src = a.input or data_path(a.plot, S)
    if not os.path.exists(src):
        print(f"no data spreadsheet at {src} — this figure is an image/timestrip; use --rebuild")
        sys.exit(1)
    rows = read_rows(src)
    if not rows:
        print(f"{src} is empty"); sys.exit(1)

    gcol = a.group_col or guess_cols(rows)[0]
    vcol = a.value_col or guess_cols(rows)[1]

    if a.show:
        print(f"{src}\n  rows: {len(rows)}\n  columns: {list(rows[0].keys())}")
        print(f"  guessed group column: {gcol}   value column: {vcol}")
        if gcol:
            seen = {}
            for r in rows:
                seen[r.get(gcol, "")] = seen.get(r.get(gcol, ""), 0) + 1
            print("  groups:")
            for k, v in sorted(seen.items(), key=lambda kv: -kv[1]):
                print(f"     {v:5d}  {k}")
        return

    # ---- filters ----
    notes = []
    n0 = len(rows)
    if a.drop_group and gcol:
        drop = {x.strip() for x in a.drop_group.split(",") if x.strip()}
        rows = [r for r in rows if r.get(gcol, "").strip() not in drop]
        notes.append("dropped group(s): " + ", ".join(sorted(drop)))
    if a.keep_group and gcol:
        keep = {x.strip() for x in a.keep_group.split(",") if x.strip()}
        rows = [r for r in rows if r.get(gcol, "").strip() in keep]
        notes.append("kept only: " + ", ".join(sorted(keep)))
    if a.drop_batch:
        drop = {x.strip() for x in a.drop_batch.split(",") if x.strip()}
        bcol = next((c for c in rows[0] if c.lower() in ("batch", "batch_name", "cell")), None) if rows else None
        if bcol:
            rows = [r for r in rows if r.get(bcol, "").strip() not in drop]
            notes.append("dropped: " + ", ".join(sorted(drop)))
        else:
            print("warning: no batch column in this spreadsheet; --drop-batch ignored")
    for col, v in a.min:
        rows = [r for r in rows if _f(r.get(col)) is not None and _f(r.get(col)) >= float(v)]
        notes.append(f"{col} >= {v}")
    for col, v in a.max:
        rows = [r for r in rows if _f(r.get(col)) is not None and _f(r.get(col)) <= float(v)]
        notes.append(f"{col} <= {v}")
    if not rows:
        print("every row was filtered out"); sys.exit(1)

    import numpy as np, matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    sys.path.insert(0, f"{ROOT}/ablation_figures_20260625")
    import matplotlib.figure as _mf
    _stock_savefig = _mf.Figure.savefig      # capture BEFORE lib patches it
    try:
        import lib
        lib.apply_style()
        # lib.apply_style() monkey-patches Figure.savefig to ALSO emit an SVG and a PDF into
        # _ai_relink/pdf -- that is how a DECK figure keeps its links fresh.  An exploratory replot must
        # not do that, or a filtered look-alike lands next to the published PDFs.  Put the stock one back.
        _mf.Figure.savefig = _stock_savefig
    except Exception:
        lib = None

    kind = a.kind
    if not kind:
        t = str((S[a.plot].get("settings") or {}).get("type", "")).lower()
        kind = ("violin" if "violin" in t else "bar" if "bar" in t else
                "box" if "box" in t else "scatter" if "scatter" in t else
                ("violin" if gcol else "scatter"))

    fig, ax = plt.subplots(figsize=(8.4, 5.2))
    if kind == "scatter" or not gcol:
        cols = [c for c in rows[0] if _f(rows[0].get(c)) is not None]
        xc, yc = (cols + [None, None])[:2]
        if a.value_col:
            yc = a.value_col
        x = [_f(r.get(xc)) for r in rows]; y = [_f(r.get(yc)) for r in rows]
        keep = [(i, j) for i, j in zip(x, y) if i is not None and j is not None]
        ax.scatter([p[0] for p in keep], [p[1] for p in keep], s=26, alpha=.8)
        ax.set_xlabel(xc); ax.set_ylabel(yc)
    else:
        order = []
        for r in rows:
            g = r.get(gcol, "")
            if g not in order:
                order.append(g)
        data = [[_f(r.get(vcol)) for r in rows if r.get(gcol, "") == g] for g in order]
        data = [[v for v in d if v is not None] for d in data]
        for i, d in enumerate(data):
            if not d:
                continue
            col = f"C{i%10}"
            if kind == "violin" and lib is not None and len(d) >= 6:
                lib.journal_violin(ax, d, i, col, width=0.8, min_n=6, alpha=0.28)
            elif kind == "box":
                ax.boxplot([d], positions=[i], widths=.55, showfliers=False)
            elif kind == "bar":
                ax.bar(i, np.mean(d), width=.6, color=col, alpha=.6)
            jit = (np.random.RandomState(i).rand(len(d)) - .5) * .26
            ax.scatter(np.full(len(d), i) + jit, d, s=20, color=col, alpha=.85,
                       edgecolor="white", lw=.3, zorder=3)
            ax.hlines(np.median(d), i - .3, i + .3, color=col, lw=2.2, zorder=4)
            ax.text(i, max(d), f"n={len(d)}", ha="center", va="bottom", fontsize=8, color=col)
        ax.set_xticks(range(len(order)))
        ax.set_xticklabels(order, fontsize=8)
        ax.set_ylabel(vcol)

    ttl = a.plot + (f"   [{n0}->{len(rows)} rows]" if len(rows) != n0 else "")
    ax.set_title(ttl, loc="left", fontweight="bold", fontsize=11)
    if notes:
        fig.text(0.005, 0.004, "filters:  " + "  ·  ".join(notes), fontsize=7.5, ha="left", va="bottom")
    os.makedirs(OUTDIR, exist_ok=True)
    out = a.out or os.path.join(OUTDIR, a.plot + ".png")
    plt.tight_layout()
    fig.savefig(out, bbox_inches="tight", dpi=140)
    print(f"wrote {out}   ({len(rows)} of {n0} rows{'; ' + '; '.join(notes) if notes else ''})")


def _f(v):
    try:
        return float(v)
    except Exception:
        return None


if __name__ == "__main__":
    main()
