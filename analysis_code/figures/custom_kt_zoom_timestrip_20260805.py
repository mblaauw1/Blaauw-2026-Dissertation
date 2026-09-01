#!/usr/bin/env python3
"""Three-row monitoring timestrip for 20250417 ptk_yfpcdc20_3 (USER 2026-08-05).

  "make a timestrip thats the monitoring video of the cell in ptk_yfp20_3, with one part showing the cell,
   and then one part showing a zoom of the polar kinetochore for each cell frame, and then another zoom of
   the sister kts (zoom such that both of the sister kts can be seen in the frame) for each cell frame. for
   the zooms, keep the same zoom amount from frame to frame for each type of zoom, but the actual location
   that the roi is placed on within the larger cell can move to keep the object of interest in the center.
   maybe, then, on the whole cell frames, draw the box outline of the rois of each of the zoom frames, so
   the viewer can see where its being placed at."

WHICH CELL. Five master batches are named `ptk_yfpcdc20_3` on different dates (the standing rule: a file
name never identifies a file across dates). Only 20250417 carries enough annotation for both zooms —
67 polar + 41 sisterless kt_points, 76 polar + 77 paired outlines; 20250423 has 0 polar marks.

ROI RULES, as asked:
  * each zoom keeps ONE window size for the whole strip (so magnification is constant and frames are
    comparable), and only the window's POSITION moves, following its object.
  * the polar window follows the polar KT track's centroid.
  * the sister window is centred on the MIDPOINT of the two paired tracks, and its size is fixed from the
    largest sister separation seen anywhere in the strip (plus margin), so both sisters are inside the
    frame in every column rather than only in the frames where they happen to be close.
  * both windows are drawn back onto the whole-cell row in their own colours.
"""
import sys, os, csv, json, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, cv2, tifffile
import lib, ts_render

lib.apply_style()
ROOT = "/Volumes/4 MB"; csv.field_size_limit(10 ** 9)
OUT = f"{ROOT}/ablation_figures_20260625/group6_tracks"; os.makedirs(OUT, exist_ok=True)
SCRIPT = __file__
B = "20250417 ptk_yfpcdc20_3"
NCOL = 8
POLAR_UM = 4.0          # fixed polar zoom window (µm across)
SIS_MARGIN = 1.9        # sister window = max separation * this
COL_POLAR = (0, 165, 255)     # BGR orange
COL_SIS = (230, 120, 60)      # BGR blue-ish

MR = {r["Batch Name"]: r for r in lib.load_master()[0]}
def px(b):
    try: return float(MR.get(b, {}).get("Pixel Size (um)", "")) or 0.062
    except Exception: return 0.062
PXS = px(B)
D = (MR.get(B, {}) or {}).get("Drive Path", "").strip()
FJ = json.load(open(f"{D}/{B}_frames.json"))
MON = [f for f in FJ["frames"] if f["role"] == "monitoring"]
print(f"{B}: {len(MON)} monitoring frames, pixel {PXS} um")

# ---- tracks -------------------------------------------------------------------------------------
tr = collections.defaultdict(dict)   # (label, tid) -> frame -> (x,y)
for r in csv.DictReader(open(f"{ROOT}/annotations/KT_OUTLINE_TRACKS_20260723.csv")):
    if r["batch"].strip() != B: continue
    lab = (r.get("label") or "").strip()
    try: tr[(lab, r["track_id"])][int(r["frame"])] = (float(r["cx_px"]), float(r["cy_px"]))
    except Exception: pass
polar = sorted([k for k in tr if k[0] == "polar"], key=lambda k: -len(tr[k]))
pairs = sorted([k for k in tr if k[0] == "paired"], key=lambda k: -len(tr[k]))
if not polar or len(pairs) < 2:
    raise SystemExit("need one polar track and two paired tracks")
POL = tr[polar[0]]; S1 = tr[pairs[0]]; S2 = tr[pairs[1]]
both = sorted(set(S1) & set(S2))
sep = [np.hypot(S1[f][0]-S2[f][0], S1[f][1]-S2[f][1]) for f in both]
SIS_PX = int(round(max(sep) * SIS_MARGIN))
POL_PX = int(round(POLAR_UM / PXS))
print(f"  polar track {polar[0][1].split('|')[-1]} n={len(POL)};  sisters {pairs[0][1].split('|')[-1]}+{pairs[1][1].split('|')[-1]} "
      f"share {len(both)} frames, max sep {max(sep):.0f}px")
print(f"  window sizes: polar {POL_PX}px ({POLAR_UM:.1f}um)  sisters {SIS_PX}px ({SIS_PX*PXS:.1f}um)")

# frames where EVERY object is present, so all three rows show the same timepoints
usable = sorted(set(POL) & set(both))
if len(usable) < 3: raise SystemExit(f"only {len(usable)} frames have polar + both sisters")
sel = [usable[i] for i in np.linspace(0, len(usable)-1, min(NCOL, len(usable))).astype(int)]
print(f"  {len(usable)} frames have all three objects; showing {len(sel)}: {sel}")

# ---- raw fluor planes (one shared stretch across the strip, as the other timestrips do) ----------
# NOT tifffile.imread(): the *_Cropped.tif are written as MANY single-page TIFF SERIES, so imread()
# returns ONE page and every column of the strip would show the same image (verified here: it came back
# shape (1056,1248), a single plane). lib.FluorTif is the reader that walks the pages and maps BY FRAME.
FT = lib.FluorTif(B, "monitoring")
if not FT.ok(): raise SystemExit("FluorTif not available for this batch")
# frames.json keys the frame index as `idx` (there is no "frame" key); the annotation stores
# use that same index, and KT->fluor mapping must go by FRAME, never t_sec (standing rule).
byfr = {int(f["idx"]): f for f in MON if "idx" in f}
def plane(fr):
    a = FT.plane_by_frame(int(fr))
    return None if a is None else a.astype(np.float32)
planes = {fr: plane(fr) for fr in sel}
vals = np.concatenate([p[np.isfinite(p)].ravel() for p in planes.values() if p is not None])
# the KTs are small bright puncta on a bright cytosol; a low floor washes them out entirely.
LO, HI = np.percentile(vals, 92), np.percentile(vals, 99.9)
def green(p):
    g = np.clip((p - LO) / max(HI - LO, 1e-6) * 255, 0, 255).astype(np.uint8)
    out = np.zeros((*g.shape, 3), np.uint8); out[..., 1] = g
    return out
def box(c, half):
    x, y = c
    return (int(round(x-half)), int(round(y-half)), int(round(x+half)), int(round(y+half)))
def tsec(fr):
    f = byfr.get(fr); return float(f["t_sec"]) if f else 0.0

# ---- three portions ------------------------------------------------------------------------------
whole, pz, sz = [], [], []
for fr in sel:
    p = planes.get(fr)
    if p is None: continue
    img = green(p)
    pc = POL[fr]; mid = ((S1[fr][0]+S2[fr][0])/2.0, (S1[fr][1]+S2[fr][1])/2.0)
    bp = box(pc, POL_PX/2.0); bs = box(mid, SIS_PX/2.0)
    marked = img.copy()
    cv2.rectangle(marked, (bp[0], bp[1]), (bp[2], bp[3]), COL_POLAR, 4)
    cv2.rectangle(marked, (bs[0], bs[1]), (bs[2], bs[3]), COL_SIS, 4)
    whole.append({"t": tsec(fr), "phase": None, "fluor": marked, "phase_label": None})
    pz.append({"t": tsec(fr), "phase": None, "fluor": ts_render.crop_pad(img, bp).copy(), "phase_label": None})
    sz.append({"t": tsec(fr), "phase": None, "fluor": ts_render.crop_pad(img, bs).copy(), "phase_label": None})

# The whole-cell row was rendering the FULL 1248x1056 frame, which made the two ROI boxes a few pixels
# across and unreadable. Crop it to the cell (square, so the resize stays uniform) before assembling, and
# put all three rows on the same ALIGN_N footprint so they lay out at one consistent panel height.
N = ts_render.ALIGN_N
_first = planes[sel[0]]
CELL = ts_render.tight_square(ts_render.fluor_cell_bbox_pts(_first), _first.shape[1], _first.shape[0], margin=1.15)
CELL_PX = CELL[2] - CELL[0]
whole = [dict(w, fluor=ts_render.crop_pad(w["fluor"], CELL).copy()) for w in whole]

portions = []
w2 = ts_render.resize_panels(whole, N)
r1 = ts_render.assemble(w2, PXS*CELL_PX/N, 10.0, chan_labels=("", "eYFP-Cdc20"), fluor_only=True)
if r1: portions.append(("whole cell (boxes = zoom ROIs)", r1[0], r1[1]))
pz2 = ts_render.resize_panels(pz, N); r2 = ts_render.assemble(pz2, PXS*POL_PX/N, 1.0, chan_labels=("", "polar KT"), fluor_only=True)
if r2: portions.append(("polar KT zoom", r2[0], r2[1]))
sz2 = ts_render.resize_panels(sz, N); r3 = ts_render.assemble(sz2, PXS*SIS_PX/N, 1.0, chan_labels=("", "sister KTs"), fluor_only=True)
if r3: portions.append(("sister-KT zoom", r3[0], r3[1]))

ok = ts_render.emit(portions, f"{OUT}/G6_kt_zoom_timestrip_20250417_ptk_yfpcdc20_3",
                    title=f"Monitoring — {B}\norange box = polar-KT zoom · blue box = sister-KT zoom "
                          f"(zoom fixed per row; ROI follows its object)")
print(f"{len(portions)} portions {'ok' if ok else 'FAIL'} -> {OUT}/G6_kt_zoom_timestrip_20250417_ptk_yfpcdc20_3.png")
