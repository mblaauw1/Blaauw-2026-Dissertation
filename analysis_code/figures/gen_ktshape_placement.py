#!/usr/bin/env python3
"""Generate the copy.ai placement JSON for the NEW kinetochore-shape figure family (17 figs).
Places into a NEW artboard in the free region right of artboard 28 (within-canvas, so no CoOA)."""
import json, os

PDF = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf"

# (base, caption)  -- ordered: by-state violins, ECDFs, shape-space scatters, per-cell class, temporal
FIGS = [
    ("G5shape_area",                "Kinetochore area by state — polar KTs largest (Kruskal p=8e-56)"),
    ("G5shape_perimeter",           "Outline perimeter by state — polar largest (p=1e-54)"),
    ("G5shape_circularity",         "Circularity by state — plate roundest, lagging least (p=1e-50)"),
    ("G5shape_solidity",            "Solidity by state — lagging most ragged (p=1e-33)"),
    ("G5shape_aspect",              "Aspect ratio (STRETCH) by state — lagging most stretched (p=6e-31)"),
    ("G5shape_elongation",          "Elongation by state — lagging highest (p=5e-31)"),
    ("G5shape_major",               "Stretch length (major axis) by state (p=2e-40)"),
    ("G5shape_aspect_ecdf",         "Aspect-ratio ECDF — lagging shifted right"),
    ("G5shape_area_ecdf",           "Area ECDF — polar shifted right"),
    ("G5shape_area_vs_circularity", "Shape space: area vs circularity"),
    ("G5shape_major_vs_minor",      "Shape space: major vs minor axis (stretch = above diagonal)"),
    ("G5shape_aspect_vs_solidity",  "Shape space: aspect ratio vs solidity"),
    ("G5shape_maxaspect_by_class",  "Peak stretch per cell, by her stretch-class (p=0.03)"),
    ("G5shape_fracstretched_by_class", "Fraction stretched (AR>2) per cell, by class (p=0.03)"),
    ("G5shape_polar_vs_paired_area", "Polar vs paired area within cell — polar larger"),
    ("G5shape_polar_vs_paired_aspect", "Polar vs paired stretch within cell — n.s. (p=0.18)"),
    ("G5shape_lagging_stretch_time", "Lagging-KT stretch over time (per cell)"),
]

# grid: 5 columns x 4 rows, within-canvas free region right of AB28
COLS = 5
X0, Y0 = 8500, 50          # top-left of first cell (Illustrator coords; y decreases downward)
COLP, ROWP = 800, 720      # column / row pitch
FIGW = 700                 # target figure width (JSX preserves each PDF's own aspect for height)
CAP_DY = 665               # caption sits this far below the figure top

items, caps = [], []
for i, (base, cap) in enumerate(FIGS):
    r, c = divmod(i, COLS)
    x = X0 + c * COLP
    y = Y0 - r * ROWP
    items.append({"file": f"{PDF}/{base}.pdf", "base": base, "x": x, "y": y, "w": FIGW})
    caps.append({"txt": cap, "pos": [x, y - CAP_DY]})

nrows = (len(FIGS) + COLS - 1) // COLS
ab_left, ab_top = X0 - 100, Y0 + 210
ab_right = X0 + (COLS - 1) * COLP + FIGW + 60
ab_bottom = Y0 - (nrows - 1) * ROWP - CAP_DY - 80
title = {"txt": "Kinetochore SHAPE (from freehand KT outline traces, 2026-07-23) — polar / plate / paired / lagging",
         "pos": [ab_left + 60, ab_top - 70]}

out = {
    "new_artboard": {"name": "Kinetochore shape (outline morphometrics)",
                     "rect": [ab_left, ab_top, ab_right, ab_bottom]},
    "title": title, "items": items, "caps": caps,
}
os.makedirs("/Volumes/4 MB/_scratch", exist_ok=True)
json.dump(out, open("/Volumes/4 MB/_scratch/place_ktshape.json", "w"), indent=1)
missing = [it["base"] for it in items if not os.path.isfile(it["file"])]
print(f"artboard rect {out['new_artboard']['rect']}  {len(items)} figs, {len(caps)} caps")
print(f"missing PDFs: {missing}")
