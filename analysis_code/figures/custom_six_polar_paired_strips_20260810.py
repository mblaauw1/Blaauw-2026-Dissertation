#!/usr/bin/env python3
"""Polar vs paired kinetochore ZOOM timestrips for the six cells on META board 7.

USER 2026-08-10: "ive left, on the meta file, six of the individual trace plots plotting polar kt distortion
with corresponding paired kt distortion over time ... use the cropping box that we use then we do the
kinetochore zoom frames in timestrips, and go to the batches for those six movies. During the monitoring
movie ... use the cropping region and center it on (1) the polar kinetochore, and (2) the paired
kinetochore, so you have close-ups of both ... Take snapshots like this of each on the first frame where
they occur together, and then about every 2 minutes after that (where you aim for 2 minutes, but its also
important that both appear on teh same frame when you take the snapshots so its at the same timepoint)
until anaphase. Assemble these into timestrips."

THE SIX CELLS are panels p2/p3/p5/p9/p12/p15 of G6ten_withincell_over_time. The panel->cell map is not in
the recorded CSV (its order disagrees), so each panel image was read and cross-checked against the builder's
own sort before this list was fixed.

WHICH TRACK. "if there are multiple traces of this type on a frame, take teh snapshot of the one used to
make the line on the plot" -- that panel draws one polar and one paired series per cell, built from the
longest track of each label, so the same rule picks the track here.

FRAME CHOICE. Only frames where BOTH kinetochores are outlined qualify, so every column is one timepoint for
both rows, as she required. From the first such frame, the next is taken once >= 110 s has passed -- aiming
at 2 min but accepting 1:50, because insisting on exactly 120 s would skip a shared frame and break the
pairing that matters more than the spacing. Frames after anaphase onset are excluded.

CROP. The standard kinetochore-zoom window, ts_render.STD_ZOOM_HALF_UM = 4.34 um half-width -> an 8.7 um
box, centred on that kinetochore's own centroid in that frame. Same window for both rows and every column,
so sizes are comparable across the strip and against every other zoom timestrip.
"""
import sys, os, json, csv
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, cv2
import lib

PLAN = "/Volumes/4 MB/_claude_tmp/six_strip_plan.json"
OUT = "/Volumes/4 MB/ablation_figures_20260625/group6_tracks/six_polar_paired_strips"
RELINK = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf"
os.makedirs(OUT, exist_ok=True); os.makedirs(RELINK, exist_ok=True)
csv.field_size_limit(10 ** 9)

try:
    import ts_render
    HALF_UM = float(getattr(ts_render, "STD_ZOOM_HALF_UM", 4.34))
except Exception:
    HALF_UM = 4.34

data, _ = lib.load_master(); MR = {r["Batch Name"]: r for r in data}
PKG_ROOTS = ["/Volumes/4 MB/_working/_annotation_packages/kt_outline_annot_pkgs_20260722",
             "/Volumes/4 MB/_working/_annotation_packages/meta_ontarget_cdc20_pkgs_20260723",
             "/Volumes/4 MB/_working/_annotation_packages/kt_outline_annot_pkgs_cdc20_two_three_ontarget_20260725"]

def px_um(b):
    try: return float((MR.get(b, {}) or {}).get("Pixel Size (um)", "") or 0.062)
    except Exception: return 0.062

def movie_for(b):
    for r in PKG_ROOTS:
        p = os.path.join(r, b, "mon_fluor.mp4")
        if os.path.isfile(p): return p
    return None

FONT = cv2.FONT_HERSHEY_SIMPLEX

def crop(frame_img, cx, cy, half_px):
    h, w = frame_img.shape[:2]
    x0 = int(round(cx - half_px)); y0 = int(round(cy - half_px))
    x1 = x0 + int(round(2 * half_px)); y1 = y0 + int(round(2 * half_px))
    # clamp inside the image, keeping the box size fixed so every tile is the same scale
    if x0 < 0: x1 -= x0; x0 = 0
    if y0 < 0: y1 -= y0; y0 = 0
    if x1 > w: x0 -= (x1 - w); x1 = w
    if y1 > h: y0 -= (y1 - h); y1 = h
    x0 = max(0, x0); y0 = max(0, y0)
    return frame_img[y0:y1, x0:x1]

plan = json.load(open(PLAN))
made = []
for b, v in plan.items():
    mv = movie_for(b)
    if not mv:
        print(f"  {b}: no monitoring movie"); continue
    frames = v["frames"]
    if not frames:
        print(f"  {b}: no co-occurring frames"); continue
    ps = px_um(b); half_px = HALF_UM / ps
    cap = cv2.VideoCapture(mv)
    nfr = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    ms = lib.parse_time((MR.get(b, {}) or {}).get("Metaphase Start (s)", ""))
    tiles = {"polar": [], "paired": []}
    labels = []
    for f in frames:
        idx = max(0, min(nfr - 1, f - 1))          # frame numbers are 1-based in the annotations
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, im = cap.read()
        im = ts_render.drop_burnin(im) if ok else im   # strip burned-in overlay
        if not ok: continue
        for row in ("polar", "paired"):
            t, cx, cy = v[f"{row}_xy"][str(f)]
            tiles[row].append(crop(im, cx, cy, half_px))
        t = v["polar_xy"][str(f)][0]
        labels.append(f"{(t-ms)/60:+.1f} min" if ms is not None else f"f{f}")
    cap.release()
    if not tiles["polar"]:
        print(f"  {b}: no frames could be read"); continue
    H = max(t.shape[0] for r in tiles for t in tiles[r])
    W = max(t.shape[1] for r in tiles for t in tiles[r])
    def norm(t):
        out = np.zeros((H, W, 3), np.uint8)
        out[:t.shape[0], :t.shape[1]] = t
        return out
    GUT = 92
    rows_img = []
    for row, colour in (("polar", (60, 170, 255)), ("paired", (255, 170, 60))):
        strip = np.hstack([norm(t) for t in tiles[row]])
        gut = np.full((H, GUT, 3), 22, np.uint8)
        cv2.putText(gut, row.upper(), (6, H // 2), FONT, 0.80, colour, 1, cv2.LINE_AA)
        rows_img.append(np.hstack([gut, strip]))
        rows_img.append(np.full((4, GUT + strip.shape[1], 3), 18, np.uint8))
    fig = np.vstack(rows_img[:-1])
    # timepoint labels along the top
    hdr = np.full((26, fig.shape[1], 3), 18, np.uint8)
    for i, lab in enumerate(labels):
        cv2.putText(hdr, lab, (GUT + i * W + 4, 18), FONT, 0.76, (235, 235, 235), 2, cv2.LINE_AA)
    fig = np.vstack([hdr, fig])
    # scale bar on the last polar tile: 2 um
    barpx = int(round(2.0 / ps))
    x1 = fig.shape[1] - 10; x0 = x1 - barpx; y = 26 + H - 10
    cv2.rectangle(fig, (x0, y - 5), (x1, y), (255, 255, 255), -1)
    cv2.putText(fig, "2 um", (x0, y - 8), FONT, 0.68, (255, 255, 255), 2, cv2.LINE_AA)
    name = "G6six_polar_paired_" + b.replace(" ", "_")
    cv2.imwrite(os.path.join(OUT, name + ".png"), fig)
    made.append((b, name, len(labels)))
    print(f"  {b[:44]:44s} {len(labels)} timepoints  {fig.shape[1]}x{fig.shape[0]}")
    lib.record_plot(name, ["batch", "frame", "t_min_from_metaphase", "row", "cx_px", "cy_px"],
                    [[b, f, round((v[f"polar_xy"][str(f)][0] - ms) / 60.0, 2) if ms is not None else "",
                      row, round(v[f"{row}_xy"][str(f)][1], 1), round(v[f"{row}_xy"][str(f)][2], 1)]
                     for f in frames for row in ("polar", "paired") if str(f) in v["polar_xy"]],
                    {"kind": "polar vs paired kinetochore zoom timestrip",
                     "window_um": round(2 * HALF_UM, 2), "spacing": "first shared frame, then >=110 s",
                     "rule": "only frames where BOTH kinetochores are outlined; stops at anaphase onset",
                     "polar_track": v["polar_track"], "paired_track": v["paired_track"]},
                    __file__,
                    f"Polar and paired kinetochore close-ups for {b}, same timepoint per column, "
                    f"{2*HALF_UM:.1f} um window, to anaphase.",
                    source=["/Volumes/4 MB/annotations/KT_OUTLINE_TRACKS_20260723.csv"], key_column="batch")

print(f"\n{len(made)} strips -> {OUT}")
