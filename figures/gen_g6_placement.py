#!/usr/bin/env python3
"""Place the 28 track/landmark/chromosome figures (G6trk_*) below the kinetochore-shape artboard (AB30),
which is grown downward (safe pattern). Numbers 406-433; updates PLOT_SETTINGS + PLOT_NUMBERS; writes the
placement JSON with numbered deck-standard captions."""
import json, csv, os

PDF = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf"
PS = "/Volumes/4 MB/ablation_plots/PLOT_SETTINGS.json"
PN = "/Volumes/4 MB/ablation_plots/PLOT_NUMBERS_20260722.csv"

FIGS = [
    "G6trk_perimeter", "G6trk_area", "G6trk_dist_to_plate",
    "G6trk_stretch_radial", "G6trk_anisotropy", "G6trk_vase", "G6trk_reflection_asym",
    "G6trk_speed_by_phase", "G6trk_postanaphase_speed", "G6trk_distance_total", "G6trk_distance_per20s",
    "G6trk_fractures",
    "G6trk_circ_vs_ttana", "G6trk_aspect_vs_ttana", "G6trk_area_vs_ttana",
    "G6trk_chromolen_vs_speed", "G6trk_chromolen_vs_circ", "G6trk_chromolen_vs_aspect",
    "G6trk_toward_vs_away",
    "G6trk_circ_vs_time", "G6trk_aspect_vs_time", "G6trk_area_vs_time", "G6trk_dist_vs_time", "G6trk_speed_vs_time",
    "G6trk_chromo_orient", "G6trk_chromo_farend", "G6trk_chromo_nearend", "G6trk_chromo_length",
]

# numbering (IDEMPOTENT: reuse an already-assigned plot_number; only new figs get the next free number)
S = json.load(open(PS))
used = max((v.get("plot_number", 0) for v in S.values() if isinstance(v.get("plot_number"), int)
           and v.get("plot_number", 0) < 406), default=405)
nxt = used + 1
nums = {}
for base in FIGS:
    if base in S and isinstance(S[base].get("plot_number"), int):
        nums[base] = S[base]["plot_number"]
    else:
        nums[base] = nxt; nxt += 1
        if base in S:
            S[base]["plot_number"] = nums[base]
# ensure contiguous 406.. by assignment order if any were missing
json.dump(S, open(PS + ".tmp", "w"), indent=1); os.replace(PS + ".tmp", PS)
have = {r["figure"] for r in csv.DictReader(open(PN))}
with open(PN, "a", newline="") as f:
    w = csv.writer(f)
    for base, n in nums.items():
        if base not in have:
            w.writerow([n, base])

# layout: NEW artboard ABOVE the top row (free canvas up to y~12000; going BELOW the deck throws CoOA).
COLS = 7
X0, Y0 = 300, 11800
COLP, ROWP, FIGW, CAP_DY = 1620, 820, 720, 660
items, caps = [], []
for i, base in enumerate(FIGS):
    r, c = divmod(i, COLS)
    x = X0 + c * COLP; y = Y0 - r * ROWP
    items.append({"file": f"{PDF}/{base}.pdf", "base": base, "x": x, "y": y, "w": FIGW})
    caps.append({"txt": f"{nums[base]}. {base}   [data: manual annotations]", "pos": [x, y - CAP_DY]})
nrows = (len(FIGS) + COLS - 1) // COLS
ab_bottom = Y0 - (nrows - 1) * ROWP - CAP_DY - 90
ab_right = X0 + (COLS - 1) * COLP + FIGW + 80
title = {"txt": "Kinetochore TRACKS · landmark (plate-anchored) shape · motion by phase · chromosome geometry (2026-07-23)",
         "pos": [X0 + 40, Y0 + 120]}
out = {"new_artboard": {"name": "Kinetochore tracks / landmark / motion / chromosome",
                        "rect": [X0 - 100, Y0 + 160, ab_right, ab_bottom]},
       "title": title, "items": items, "caps": caps}
json.dump(out, open("/Volumes/4 MB/_scratch/place_g6.json", "w"), indent=1)
missing = [it["base"] for it in items if not os.path.isfile(it["file"])]
print(f"{len(items)} figs numbered {min(nums.values())}-{max(nums.values())}; artboard bottom -> {ab_bottom}; missing: {missing}")
