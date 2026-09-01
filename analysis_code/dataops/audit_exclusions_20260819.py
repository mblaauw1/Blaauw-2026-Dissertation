"""ITEM 14 AUDIT: is any excluded batch/point still present in a figure's RECORDED data?

USER 2026-08-19 (all-figures item 14): "Across all figures make sure you didnt accidentally include any
points i previously directed you to omit such (for example there are some outlier points on the off-target
single group that i think i told you to omit from plots previously)"

Two exclusion registers exist and each is checked against every figure's recorded data CSV -- the CSV is the
exact data the figure plotted (lib.record_plot), so a hit here is a point really on the page:
  * lib.REVIEW_EXCLUDE            blanket: never in ANY figure
  * MANUAL_PLOT_EXCLUSIONS.csv    per-plot, whole batch or one kinetochore
"""
import csv, os, sys, glob, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import lib

DATA = "/Volumes/4 MB/ablation_plots/data"
EXCL = "/Volumes/4 MB/annotations/MANUAL_PLOT_EXCLUSIONS.csv"

blanket = set(lib.REVIEW_EXCLUDE)
per_plot = collections.defaultdict(set); per_pt = collections.defaultdict(set)
if os.path.isfile(EXCL):
    for r in csv.DictReader(open(EXCL)):
        p = (r.get("plot") or "").strip(); b = (r.get("batch") or "").strip(); k = (r.get("kt") or "").strip()
        if not (p and b): continue
        (per_pt[p].add((b, k)) if k else per_plot[p].add(b))
print(f"blanket exclusions: {len(blanket)}  |  per-plot batch rules: {sum(len(v) for v in per_plot.values())}"
      f"  |  per-point rules: {sum(len(v) for v in per_pt.values())}")

hits_blanket = []; hits_plot = []; hits_pt = []
csvs = sorted(glob.glob(f"{DATA}/*.csv"))
for p in csvs:
    pid = os.path.basename(p)[:-4]
    try:
        rows = list(csv.DictReader(open(p, newline="", encoding="utf-8", errors="replace")))
    except Exception:
        continue
    if not rows: continue
    bcol = next((c for c in ("batch", "Batch Name", "cell", "sample") if c in rows[0]), None)
    if not bcol: continue
    kcol = next((c for c in ("kt", "kt_id", "chr_num") if c in rows[0]), None)
    seen = collections.Counter((r.get(bcol) or "").strip() for r in rows)
    for b in blanket:
        if seen.get(b): hits_blanket.append((pid, b, seen[b]))
    for b in per_plot.get(pid, ()):
        if seen.get(b): hits_plot.append((pid, b, seen[b]))
    if kcol:
        pts = collections.Counter(((r.get(bcol) or "").strip(), str(r.get(kcol) or "").strip()) for r in rows)
        for bk in per_pt.get(pid, ()):
            if pts.get(bk): hits_pt.append((pid, bk[0], bk[1], pts[bk]))

print(f"\nscanned {len(csvs)} recorded figure data files")
print(f"  BLANKET-excluded batch still present : {len(hits_blanket)}")
for h in hits_blanket[:40]: print(f"      {h[0]:52s} {h[1]}  ({h[2]} rows)")
print(f"  PER-PLOT-excluded batch still present: {len(hits_plot)}")
for h in hits_plot[:40]: print(f"      {h[0]:52s} {h[1]}  ({h[2]} rows)")
print(f"  PER-POINT-excluded KT still present  : {len(hits_pt)}")
for h in hits_pt[:40]: print(f"      {h[0]:52s} {h[1]} kt={h[2]}  ({h[3]} rows)")
