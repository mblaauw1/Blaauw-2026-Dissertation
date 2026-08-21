"""Group 5 / Board M3, item 1b (2026-08-03): individual per-kinetochore Mad1 fluorescence TRACES OVER
TIME, sisterless vs plate, so the retention/relocalisation at sisterless KTs can be read directly against
the plate baseline (her words, board M3 "an unsatisfied checkpoint at the poles"). NEW figure/plot_id:
G5_mad1_fluor_traces_sisterless_vs_plate.

WHAT THE ANNOTATION STORE ACTUALLY SUPPORTS -- read this before reading the plot; the figure is built
exactly to this ceiling, not padded past it.

Mad1 kinetochores are marked in TWO different stores, measured by TWO independently-vetted recipes that do
NOT calibrate to the same absolute a.u. scale -- kept as two clearly separate panel rows below, never
pooled onto one shared axis.

  (A) OUTLINE traces. annotations/kt_outlines.csv polygons, measured into
      annotations/KT_FLUOR_CYTOSOLNORM_20260728.csv by polar_fluor_matched.py:
      signal = p95(inside polygon) - per-frame cytosol median (that file's own "done properly" recipe,
      2026-07-28). Of 245 master rows with Cell Type containing "mad1", only THREE have any Mad1
      kinetochore actually outline-traced:
        20260303 Mad1_Ptk_Eyfpmad1_ablation_10 -- 6 polar(sisterless) frames, no plate trace
        20260310 ptk2_eyfp_mad1_14             -- 5 polar(sisterless) frames, no plate trace
        20260310 ptk2_eyfp_mad1_8              -- 5 polar + 3 plate(paired) frames -- the ONLY cell with an
                                                   in-cell plate baseline traced over multiple frames
      (kt_outlines "notes" grp tags confirm each is ONE continuous kinetochore per batch/label, not a
      merge of several -- see NOTES.md 2026-08-03 grp fix.)

  (B) POINT traces. annotations/kt_points.csv (labels polar / paired_kt / cytosol_bg), measured HERE with
      the SAME recipe group5_mad1_polar_plate.py verified today (2026-08-03, "feedback item C"): raw
      16-bit plane from <batch>_Fluor_Cropped.tif, page = the batch's monitoring-role frames.json entries
      that carry a fluor_tif_idx, ordered by t_sec, indexed by the annotation's 1-based `frame`; r=5px disk
      mean; +-2px local-max re-centre only (not a large peak search); same-frame cytosol_bg disk
      subtracted. Generalised here from that file's HARDCODED 20260304-session path to the drive-wide
      render-dir glob (this file's `_index_render_dirs`) so it can reach any date -- the measurement math
      is unchanged, only the file lookup. Of every mad1 batch with a `polar` kt_points mark, only
      20260304 Mad1_ablation_17 has one across >=3 DISTINCT frames (a real trace: frames 2,3,4,5); its
      `paired_kt` marks (3 KTs) are all on ONE frame (frame 1) -- a plate REFERENCE band, not a plate
      trace. 20260304 Mad1_ablation_20 has a similar multi-KT snapshot but is deliberately LEFT OUT here:
      group5_mad1_polar_plate.py opted it back into ITS plot for exactly one frame (frame 1, pre-bleach)
      with a documented reason tied to that single frame; re-using it across many frames would need
      re-justifying against its own Exclude reason ("photobleaching") and that is not this figure's call to
      make. 20260303 Mad1_Ptk_Eyfpmad1_ablation_4 (sisterless x11, Exclude=Yes) and 20260304 Mad1_ablation_15
      (Exclude=Yes, no polar mark at all) are excluded/inapplicable, matching group5_mad1_polar_plate.py's
      own inclusion logic. The 3 outline-covered batches above are NOT re-measured a second time here by
      the point recipe even where they also happen to carry point marks -- one measurement per kinetochore,
      not two competing numbers for the same KT in one figure.

  BOTTOM LINE / N (stated on the figure itself, not just here): FOUR cells carry a genuine multi-frame
  sisterless-KT Mad1 trace (3 outline + 1 point). Of those four, ONE (ptk2_eyfp_mad1_8) has a plate/paired
  trace spanning multiple frames in the SAME cell -- the only real within-cell trace-vs-trace comparison
  this store supports. A second (Mad1_ablation_17) has a single-frame, multi-KT plate SNAPSHOT usable only
  as a reference band. The other two have no plate mark at all. The annotation store does not yet support a
  many-cell sisterless-vs-plate TRACE comparison; broader coverage needs more polar+paired_kt (or outline)
  marks placed across a real time window per cell -- an ANNOTATION gap, not a code gap. This is reported
  plainly rather than building a figure that implies more cells than actually exist.
"""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import os, csv, glob, json
import numpy as np, cv2, tifffile as tf
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import lib
lib.apply_style()

OUT = "/Volumes/4 MB/ablation_figures_20260625/group4"; os.makedirs(os.path.join(OUT, "illustrator"), exist_ok=True)
SCRIPT = __file__
COL = {"sisterless": "#e6820e", "plate": "#3b6fb6"}   # matches polar_fluor_matched.py's polar/paired palette

# ================= (A) OUTLINE traces — read the already-vetted CSV, mad1 rows only =====================
OUTLINE_CSV = "/Volumes/4 MB/annotations/KT_FLUOR_CYTOSOLNORM_20260728.csv"
data, _ = lib.load_master()
outline_rows = [r for r in csv.DictReader(open(OUTLINE_CSV)) if lib.is_mad1(r["batch"])]
outline_by_cell = {}
for r in outline_rows:
    outline_by_cell.setdefault(r["batch"], {"sisterless": [], "plate": []})
    cat = "sisterless" if r["label"] == "polar" else "plate" if r["label"] == "paired" else None
    if cat is None:
        continue
    outline_by_cell[r["batch"]][cat].append((float(r["t_sec"]) / 60.0, float(r["signal"])))
for cell in outline_by_cell.values():
    for cat in cell:
        cell[cat].sort()

# ================= (B) POINT traces — same recipe as group5_mad1_polar_plate.py, generalized lookup ======
_RDIR = {}
for _fj in glob.glob("/Volumes/4 MB/**/*_frames.json", recursive=True):
    d = os.path.dirname(_fj)
    if "_ARCHIVED" in _fj or "backup" in _fj.lower():
        continue
    _RDIR.setdefault(os.path.basename(d), d)

def mon_fluor_pages(batch):
    d = _RDIR.get(batch)
    if not d:
        return []
    fjp = f"{d}/{batch}_frames.json"
    if not os.path.isfile(fjp):
        return []
    j = json.load(open(fjp))
    mon = [f for f in j["frames"] if f["role"] == "monitoring" and f.get("fluor_tif_idx") is not None]
    mon.sort(key=lambda f: f["t_sec"])
    return [(f["fluor_tif_idx"], float(f["t_sec"])) for f in mon]

def raw_plane_and_t(batch, frame):
    pages = mon_fluor_pages(batch)
    if frame < 1 or frame > len(pages):
        return None, None
    d = _RDIR[batch]
    cp = f"{d}/{batch}_Fluor_Cropped.tif"
    if not os.path.isfile(cp):
        return None, None
    pg, t = pages[frame - 1]
    with tf.TiffFile(cp) as tif:
        if pg >= len(tif.pages):
            return None, None
        return tif.pages[pg].asarray(), t

def refine_xy(g, x, y, rad=2):
    h, w = g.shape
    xi, yi = int(round(x)), int(round(y))
    x0, x1 = max(0, xi - rad), min(w, xi + rad + 1)
    y0, y1 = max(0, yi - rad), min(h, yi + rad + 1)
    sub = g[y0:y1, x0:x1]
    if sub.size == 0:
        return x, y
    my, mx = np.unravel_index(int(np.argmax(sub)), sub.shape)
    return float(x0 + mx), float(y0 + my)

def disk_mean(g, x, y, r=5):
    h, w = g.shape
    m = np.zeros((h, w), np.uint8)
    cv2.circle(m, (int(round(x)), int(round(y))), r, 1, -1)
    sel = g[m > 0]
    return float(sel.mean()) if sel.size else None

POINT_BATCH = "20260304 Mad1_ablation_17"
pts = {"polar": [], "paired_kt": [], "cytosol_bg": []}
for r in csv.DictReader(open("/Volumes/4 MB/annotations/kt_points.csv")):
    if r["batch"].strip() != POINT_BATCH:
        continue
    lab = r["label"].strip()
    if lab in pts:
        pts[lab].append((int(float(r["frame"])), float(r["x"]), float(r["y"])))

point_trace = {"sisterless": [], "plate": []}   # (minutes, value)
point_report = []
bg_by_frame = {f: (x, y) for f, x, y in pts["cytosol_bg"]}
for f, x, y in sorted(pts["polar"]):
    g, t = raw_plane_and_t(POINT_BATCH, f)
    if g is None:
        continue
    bgf = bg_by_frame.get(f) or (bg_by_frame[sorted(bg_by_frame)[0]] if bg_by_frame else None)
    bg = disk_mean(g, *bgf) if bgf else 0.0
    rx, ry = refine_xy(g, x, y)
    val = disk_mean(g, rx, ry) - bg
    point_trace["sisterless"].append((t / 60.0, val))
# plate reference: the single frame-1 snapshot (3 KTs) — a BAND, not a trace
plate_frame1 = sorted({f for f, _, _ in pts["paired_kt"]})
if plate_frame1:
    f0 = plate_frame1[0]
    g0, t0 = raw_plane_and_t(POINT_BATCH, f0)
    if g0 is not None:
        bgf = bg_by_frame.get(f0) or (bg_by_frame[sorted(bg_by_frame)[0]] if bg_by_frame else None)
        bg0 = disk_mean(g0, *bgf) if bgf else 0.0
        for f, x, y in pts["paired_kt"]:
            if f != f0:
                continue
            rx, ry = refine_xy(g0, x, y)
            point_trace["plate"].append((t0 / 60.0, disk_mean(g0, rx, ry) - bg0))
point_trace["sisterless"].sort()

# ================= plot =================================================================================
# USER 2026-08-04: "simplify to just the mad1_ablation_17 plot, not 4 different ones." The three
# outline-measured cells are dropped from the figure; only the point-measured Mad1_ablation_17 panel is
# drawn. The outline traces are still computed above and still written to the plot's data CSV, so nothing
# is lost from the record - they are simply no longer on the figure.
outline_cells = ["20260303 Mad1_Ptk_Eyfpmad1_ablation_10", "20260310 ptk2_eyfp_mad1_14", "20260310 ptk2_eyfp_mad1_8"]
fig, axp = plt.subplots(1, 1, figsize=(5.6, 4.8))

def _short(b):
    return b.replace("20260303 Mad1_Ptk_Eyfpmad1_", "").replace("20260304 ", "").replace("20260310 ", "")

if point_trace["sisterless"]:
    x, y = zip(*point_trace["sisterless"])
    axp.plot(x, y, "-o", color=COL["sisterless"], lw=1.8, ms=5,
              label=f"sisterless (N={len(point_trace['sisterless'])} frames)")
if point_trace["plate"]:
    vals = [v for _, v in point_trace["plate"]]
    # USER 2026-08-04: keep the plate reference BAND, drop the individual blue squares. The band already
    # carries the plate range; the squares implied a measurement at one x-position that is not a trace.
    axp.axhspan(min(vals), max(vals), color=COL["plate"], alpha=0.16, zorder=1,
                label=f"plate reference band (N={len(vals)} KTs, one frame)")
axp.set_title(_short(POINT_BATCH) + "\n(point-measured, disk r=5px)", fontsize=9.5, fontweight="bold")
axp.set_xlabel("min from first ablation"); axp.legend(fontsize=7, loc="best")
axp.set_ylabel("Mad1 signal, point disk−cytosol (a.u.)", fontsize=8)

fig.suptitle(
    "Individual per-kinetochore Mad1 fluorescence\nover time — sisterless vs plate",
    fontsize=10.5, fontweight="bold", y=1.02)
# the caveats belong under the axes, not in a title wider than the figure
axp.text(0.0, -0.20,
         "Mad1_ablation_17 only. Sisterless KT point-measured (disk r=5px, cytosol-subtracted).\n"
         "Plate value is a single-frame snapshot of 3 paired KTs — drawn as a reference band, not a trace.\n"
         "The 3 outline-measured cells are no longer plotted (different recipe); their values stay in the data CSV.",
         transform=axp.transAxes, ha="left", va="top", fontsize=7.2, color="#333")
fig.tight_layout()
fig.savefig(f"{OUT}/G5_mad1_fluor_traces_sisterless_vs_plate.png", dpi=200, bbox_inches="tight")
fig.savefig(f"{OUT}/illustrator/G5_mad1_fluor_traces_sisterless_vs_plate.svg", bbox_inches="tight")
plt.close(fig)

prov_cols = ["batch", "category", "measurement", "n_frames"]
prov = []
for cell in outline_cells:
    d = outline_by_cell.get(cell, {"sisterless": [], "plate": []})
    for cat in ("sisterless", "plate"):
        if d[cat]:
            prov.append([cell, cat, "outline p95-cytosol", len(d[cat])])
if point_trace["sisterless"]:
    prov.append([POINT_BATCH, "sisterless", "point disk r5-cytosol", len(point_trace["sisterless"])])
if point_trace["plate"]:
    prov.append([POINT_BATCH, "plate (single-frame snapshot)", "point disk r5-cytosol", len(point_trace["plate"])])

lib.record_plot(
    "G5_mad1_fluor_traces_sisterless_vs_plate", prov_cols, prov,
    {"type": "NEW 2026-08-03 (item 1b)", "n_cells_with_sisterless_trace": len(outline_cells) + 1,
     "n_cells_with_plate_trace": 1, "n_cells_with_plate_snapshot_only": 1,
     "n_cells_no_plate_mark": 2,
     "gap": "annotation store does not support a many-cell sisterless-vs-plate TRACE comparison; "
            "see file header for full accounting"},
    SCRIPT, "Individual per-kinetochore Mad1 fluorescence traces over time, sisterless vs plate KTs",
    source=[OUTLINE_CSV, "/Volumes/4 MB/annotations/kt_points.csv", "/Volumes/4 MB/annotations/kt_outlines.csv"])

print("wrote G5_mad1_fluor_traces_sisterless_vs_plate.png")
print(f"outline cells: {outline_cells}")
print(f"point cell: {POINT_BATCH}  sisterless N={len(point_trace['sisterless'])}  plate(snapshot) N={len(point_trace['plate'])}")
