#!/usr/bin/env python3
"""Inventory of WHERE EVERY FIGURE'S DATA COMES FROM. Report only — changes nothing.

USER 2026-08-09: "lets not make any changes to which annotation types plots are using; just store what
you find so i can ask questions about where certain plot data is coming from in case i decide it should
come from multiple places or i want to troubleshoot it."

Two independent views of provenance per figure, because they can disagree and the disagreement is itself
worth seeing:
  * DECLARED  -- the `source` list recorded by `lib.record_plot` when the figure was last built.
  * READ      -- annotation stores actually referenced in the builder's source code.

Also records, for each figure, which OTHER annotation stores hold marks that its builder never opens.
That is a QUESTION, not a defect: the k-k case (2026-08-09) showed that a second store can hold a
genuinely different measurement -- the ablation TARGET pair (kt_points pre_abl, ablation clip) is not the
untargeted pair (kt_outlines paired, monitoring clip) and the two must never share an axis or an N.

Writes `ablation_plots/PLOT_DATA_PROVENANCE_20260809.csv` and a readable `.md` summary.
"""
import csv, json, os, re, sys, glob, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import lib

csv.field_size_limit(10 ** 9)
A = "/Volumes/4 MB/annotations/"
OUTC = "/Volumes/4 MB/ablation_plots/PLOT_DATA_PROVENANCE_20260809.csv"
OUTM = "/Volumes/4 MB/ablation_plots/PLOT_DATA_PROVENANCE_20260809.md"

# annotation stores worth tracking, with what each one actually IS
STORES = {
    "kt_outlines.csv":        "her freehand KT outline traces (labels paired/polar/lagging/sisterless)",
    "kt_points.csv":          "her KT point marks (pre_abl/pre_abl_pair = ABLATION TARGET pair; paired_kt = untargeted control; sisterless/polar/lagging; cytosol_bg)",
    "cell_outlines.csv":      "her whole-cell outlines",
    "meta_plates.csv":        "her metaphase-plate lines",
    "chromo_lines.csv":       "her chromosome length lines",
    "poles.csv":              "her spindle-pole marks",
    "lagging_lengths.csv":    "her lagging-chromosome length marks",
    "KT_OUTLINE_TRACKS":      "DERIVED from kt_outlines: per-frame tracks, track identity = her grp",
    "KT_SISTER_KK":           "DERIVED from the outline tracks: UNTARGETED sister pairs + per-frame k-k",
    "CHROMOSOME_MASTER":      "consolidated chromosome lengths / behaviour",
    "SISTERLESS_PLATE_JOIN":  "her plate-join times for sisterless KTs",
    "kt_shape_metrics":       "DERIVED from kt_outlines: per-polygon shape metrics",
    "META_PLATE_NORMALIZED":  "DERIVED from meta_plates: plate normal axis",
    "ABLATION_MASTER.csv":    "the master spreadsheet",
}

# ---- which unique source builders read which stores ----------------------------------------------
files = sorted(glob.glob("/Volumes/4 MB/ablation_plots/code/*.py")) + \
        sorted(glob.glob("/Volumes/4 MB/ablation_figures_20260625/*.py"))
real = {}
for p in files:
    stem = os.path.basename(p)[:-3]
    real.setdefault(stem.split("__")[-1] + ".py", p)      # strip record_plot provenance prefixes

reads = {}
for name, p in real.items():
    try:
        s = open(p, encoding="utf-8", errors="replace").read()
    except Exception:
        continue
    reads[name] = {k for k in STORES if k in s}

# ---- which cells each store actually covers -------------------------------------------------------
def batches_in(path, labelfilter=None):
    out = set()
    try:
        for r in csv.DictReader(open(path, newline="", encoding="utf-8", errors="replace")):
            if labelfilter and (r.get("label") or "").strip() != labelfilter:
                continue
            b = (r.get("batch") or "").strip()
            if b:
                out.add(b)
    except Exception:
        pass
    return out

COVER = {}
for k in STORES:
    cands = glob.glob(A + k) + glob.glob(A + k + "*.csv") + glob.glob(A + k + "*")
    f = next((c for c in cands if os.path.isfile(c) and c.endswith(".csv")), None)
    if f:
        COVER[k] = batches_in(f)
COVER["ABLATION_MASTER.csv"] = set()

# ---- per-figure rows ------------------------------------------------------------------------------
PS = "/Volumes/4 MB/ablation_plots/PLOT_SETTINGS.json"
ps = json.load(open(PS)) if os.path.exists(PS) else {}
DATA = "/Volumes/4 MB/ablation_plots/data"

# plot_id -> builder, resolved by finding the record_plot call in the builder source.
# (PLOT_SETTINGS has no usable `script` field -- it is None on every entry.)
SRC_TEXT = {}
for name, p_ in real.items():
    try:
        SRC_TEXT[name] = open(p_, encoding="utf-8", errors="replace").read()
    except Exception:
        pass
pid2builder = {}
for name, txt in SRC_TEXT.items():
    for m in re.finditer(r'record_plot\(\s*[\"\']([A-Za-z0-9_\-\.]+)[\"\']', txt):
        pid2builder.setdefault(m.group(1), name)

# SECOND, BROADER PASS. Many builders call record_plot with a variable (loops, f-strings), so the literal
# scan above misses them. But `lib.record_plot` writes a provenance COPY of the builder named
# "<plot_id>__<...>__<real_script>.py" -- the first "__" segment IS the plot_id and the last IS the
# builder that produced it. That filename convention resolves the figures the source scan cannot.
for _p in files:
    _stem = os.path.basename(_p)[:-3]
    _parts = _stem.split("__")
    if len(_parts) >= 2:
        pid2builder.setdefault(_parts[0], _parts[-1] + ".py")

rows = []
for pid, ent in sorted(ps.items()):
    if not isinstance(ent, dict):
        continue
    panel_parent = ent.get("panel_of") or (ent.get("settings") or {}).get("panel_of") or ""
    key = pid2builder.get(pid) or (pid2builder.get(panel_parent) if panel_parent else "") or ""
    script = key
    # `source` is a DICT recorded by record_plot: {"files":[...], "mtimes_at_build":{...}, ...}
    _src = ent.get("source") or []
    if isinstance(_src, dict):
        declared = list(_src.get("files") or [])
    elif isinstance(_src, str):
        declared = [_src]
    else:
        declared = list(_src)
    dnames = sorted({k for k in STORES for s in declared if k in str(s)})
    rnames = sorted(reads.get(key, set()))
    panel_of = panel_parent
    # cells the figure's own data CSV covers
    dpath = os.path.join(DATA, pid + ".csv")
    if not os.path.exists(dpath) and panel_of:
        dpath = os.path.join(DATA, str(panel_of) + ".csv")
    ncell = ""
    if os.path.exists(dpath):
        try:
            rr = list(csv.DictReader(open(dpath, newline="", encoding="utf-8", errors="replace")))
            if rr and "batch" in rr[0]:
                ncell = len({(x.get("batch") or "").strip() for x in rr if (x.get("batch") or "").strip()})
        except Exception:
            pass
    unread = sorted(set(rnames and STORES or STORES) - set(rnames) - set(dnames)) if rnames else []
    rows.append([pid, panel_of, script, ";".join(dnames), ";".join(rnames),
                 ncell, len(rnames), ";".join(unread)])

with open(OUTC, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["plot_id", "panel_of", "builder", "declared_sources", "stores_read_by_builder",
                "cells_in_its_data_csv", "n_stores_read", "stores_NOT_read"])
    w.writerows(rows)
print(f"wrote {OUTC}  ({len(rows)} figures)")

# ---- markdown summary -----------------------------------------------------------------------------
L = ["# Where every figure's data comes from — 2026-08-09",
     "",
     "REPORT ONLY. Nothing was changed about which annotation stores any plot reads (the single",
     "exception is the k-k work done separately today, which is recorded at the bottom).",
     "",
     "Query this file, or `PLOT_DATA_PROVENANCE_20260809.csv`, to ask where a figure's numbers come from.",
     "",
     "## What each annotation store is", ""]
for k, v in STORES.items():
    L.append(f"- **`{k}`** — {v}" + (f"  _(covers {len(COVER[k])} cells)_" if COVER.get(k) else ""))
L += ["", "## The distinction that caused a real error today", "",
      "`kt_points` `pre_abl`/`pre_abl_pair` are the **ablation TARGET pair**, marked on the **ablation**",
      "clip. `kt_outlines` label `paired` and `kt_points` `paired_kt` are **UNTARGETED** pairs on the",
      "**monitoring** clip. These are different kinetochores, not two estimates of one quantity: pooling",
      "them produced a spurious -0.44 um shift (Wilcoxon p=1.5e-4). They must never share an axis or an N.",
      "A figure quoting 'k-k' should say WHICH pair it means.", "",
      "## Builders by number of annotation stores read", ""]
byn = collections.Counter(len(v) for v in reads.values() if v)
for n in sorted(byn):
    L.append(f"- reads {n} store(s): {byn[n]} builders")
L += ["", "## Single-store builders (each is a QUESTION, not a defect)", ""]
single = sorted([(n, sorted(v)[0]) for n, v in reads.items() if len(v) == 1])
bys = collections.defaultdict(list)
for n, st in single:
    bys[st].append(n)
for st, ns in sorted(bys.items(), key=lambda x: -len(x[1])):
    L.append(f"### only `{st}`  ({len(ns)} builders)")
    for n in ns:
        L.append(f"- {n}")
    L.append("")
L += ["## Known unused annotation data", "",
      "- `kt_points` label `sisterless` is a genuine MULTI-FRAME track store (median 26 frames/cell,",
      "  28 single- and 23 triple-sisterless cells) that **no movement figure reads**. It is a different",
      "  measurement from the outline tracks (point centroid vs traced polygon), so it would be its own",
      "  figure rather than extra N on an existing one. Left untouched pending her decision.",
      "- `kt_points` label `paired_kt` (untargeted control pairs, 15 cells) is read by very few builders;",
      "  only 1 cell has both `paired_kt` marks and paired outlines.", ""]
open(OUTM, "w").write("\n".join(L) + "\n")
print(f"wrote {OUTM}")
print(f"\nbuilders reading >=1 annotation store: {sum(1 for v in reads.values() if v)}")
print(f"single-store builders: {len(single)}")
