#!/usr/bin/env python3
"""Lagging-chromosome EXAMPLE images, rebuilt from HER MANUAL OUTLINES.

REPLACES group4_lagging_examples.py (user 2026-07-29). The old script read the
kt_points CIRCLE marks labelled 'lagging' and then DERIVED a shape by auto-segmenting
the image around the click point - with a fallback that manufactured an outline at
percentile 62 of a central disk when the signal was too faint. The circle-marking
technique is not sufficient for characterizing lagging kinetochores in ANAPHASE (it is
in metaphase), so those panels reported an unsupported length/aspect. Every panel here
instead overlays the polygon SHE traced; nothing is segmented or invented.

GROUPING (user 2026-07-29 + NOTES.md:249 data model):
  kt_outlines has one row per TRACE. `grp` (parsed from notes: "grp:N;trace:M"; the type is the
  `label` column — the old duplicate `kttype:` key in notes was removed 2026-08-07)
  identifies ONE kinetochore across frames; several traces of one grp on ONE frame are
  pieces of that single kinetochore. For LAGGING those pieces are a kinetochore that has
  FRACTURED under the force of anaphase, so they are unioned and measured as one object.
  Key = (batch, grp, frame). This is stricter than kt_shape_metrics.load_shapes, which
  keys (batch, label, frame) and therefore merges two DIFFERENT lagging kinetochores that
  share a frame - real in `20250901 triple_ablation_11` (grps 10 and 18, the cell the old
  script hardcoded an L1/L2 split for). kt_tracks.build_objects:76 is already grp-aware.

  4 batches carry no grp on any lagging trace (no batch MIXES grp'd and un-grp'd lagging
  rows). User 2026-07-29: within one batch these lagging polygons mark just ONE
  kinetochore on each frame, so several polygons on a frame again mean fracture. The
  frame-level key is therefore the CORRECT rule for them, not a degraded fallback -
  panels are labelled "single KT" rather than flagged as uncertain.

REPRESENTATIVE FRAME: her noted frame from the old script's LAG_SLIDE table where the
batch is covered (nearest traced frame to it); otherwise the PEAK-STRETCH frame of that
track (max fitted major axis), which is the frame the stretch result is about. Which rule
was used is printed per panel.

Frame->TIF mapping goes through lib.FluorTif.plane_by_frame (calibrated, one-based-aware
since the 2026-07-28 off-by-one fix). Metrics come from kt_shape_metrics._combined_metrics
so this figure and the shape family measure a combined object identically.
"""
import sys
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import csv, json, re, os, collections
import numpy as np
import matplotlib.pyplot as plt
import lib
import kt_shape_metrics as K

csv.field_size_limit(10 ** 9)
lib.apply_style()
OUT = "/Volumes/4 MB/ablation_figures_20260625/group4"
os.makedirs(OUT, exist_ok=True)
SCRIPT = __file__
SRC = "/Volumes/4 MB/annotations/kt_outlines.csv"
PX = 0.062

# her representative frames from the retired circle figure (batch_meta notes,
# "slide for lagging kinetochore = monitoring NN"). Kept ONLY as a frame hint.
LAG_SLIDE = {
    "20250409 ptk_yfpcdc20_1": 32, "20250410 ptk_yfpcdc20_17": 110,
    "20250411 ptk_yfpcdc20_11": 108, "20250901 triple_ablation_11": 218,
    "20250923 triple_ablation_collagen_25": 61, "20250929 four_ablation_23": 131,
    "20250930 four_ablation_59": 76, "20251006 triple_ablation_8": 57,
    "20251029 single_ablation_13": 92, "20251029 triple_ablation_12": 178,
}

data, _ = lib.load_master_plots()
mr = {r["Batch Name"]: r for r in data}


def grp_of(row):
    m = re.search(r"grp:([^;]*)", row.get("notes", "") or "")
    g = (m.group(1).strip() if m else "")
    return g or None


# ---- load traces, apply the SAME exclusions as the shape family ----
rows = []
for r in csv.DictReader(open(SRC)):
    if lib.is_prophase_ablation(r.get("batch","")): continue   # prophase excluded (no prophase group)
    if (r.get("label") or "").strip() != "lagging":
        continue
    if r.get("channel") != "fluor":
        continue
    if lib.kt_outline_excluded(r.get("batch")):
        continue
    if lib.focus_excluded(r.get("id")):
        continue
    try:
        pts = json.loads(r["points"])
    except Exception:
        continue
    if not pts or len(pts) < 5:
        continue
    rows.append((r, pts))

# ---- one object per (batch, grp, frame); traces within it are pieces of ONE KT ----
objs = collections.OrderedDict()
for r, pts in rows:
    try:
        fr = int(float(r.get("frame")))
    except Exception:
        continue
    objs.setdefault((r["batch"], grp_of(r), fr), []).append((r, pts))

records = []
for (batch, grp, fr), members in objs.items():
    pieces = [p for (_, p) in members]
    m = K._combined_metrics(pieces, PX)
    if m is None:
        continue
    r0 = members[0][0]
    try:
        t_sec = float(r0.get("t_sec"))
    except Exception:
        t_sec = float("nan")
    records.append(dict(batch=batch, grp=grp, frame=fr, pieces=pieces, t_sec=t_sec,
                        members=members, major=m["major_um"], aspect=m["aspect_ratio"],
                        n_pieces=m["n_pieces"]))

tracks = collections.OrderedDict()
for rec in records:
    tracks.setdefault((rec["batch"], rec["grp"]), []).append(rec)


def t_since_anaphase(rec):
    """Canonical rule (group4_lagging_shape.py:6): take the time from the annotation's OWN
    `nearest_event` "Anaphase (+Ns)" - it is on the same clock as the annotation - and fall
    back to the master's Anaphase Onset only when that is absent. The master column is an
    elapsed User-Input time on a DIFFERENT clock from t_sec (which is 0 at the first
    ablation event), so the fallback can read negative; panels using it are tagged."""
    for r0, _ in rec["members"]:
        m = re.search(r"Anaphase\s*\(([+-]?\d+)\s*s\)", r0.get("nearest_event") or "")
        if m:
            return float(m.group(1)), "event"
    a = lib.parse_time(mr.get(rec["batch"], {}).get("Anaphase Onset (s)", ""))
    if a is None or not np.isfinite(rec["t_sec"]):
        return None, None
    return rec["t_sec"] - a, "master"


# ---- pick one representative frame per track ----
picks = []
for (batch, grp), recs in tracks.items():
    recs.sort(key=lambda d: d["frame"])
    if batch in LAG_SLIDE:
        want = LAG_SLIDE[batch]
        rec = min(recs, key=lambda d: abs(d["frame"] - want))
        rule = "her frame %d" % want
    else:
        rec = max(recs, key=lambda d: d["major"])
        rule = "peak stretch"
    picks.append((rec, rule, len(recs)))

picks.sort(key=lambda t: (t[0]["batch"], str(t[0]["grp"])))

# ---- crop the fluor TIF and keep her polygon in crop coordinates ----
items = []
for rec, rule, ntr in picks:
    batch = rec["batch"]
    ft = lib.FluorTif(batch, "monitoring")
    if not ft.ok():
        print("  skip %s: no fluor TIF" % batch)
        continue
    g = ft.plane_by_frame(rec["frame"])
    ft.close()
    if g is None:
        print("  skip %s grp=%s frame=%d: no plane" % (batch, rec["grp"], rec["frame"]))
        continue
    allpts = np.vstack([np.asarray(p, float) for p in rec["pieces"]])
    cx, cy = allpts[:, 0].mean(), allpts[:, 1].mean()
    span = max(np.ptp(allpts[:, 0]), np.ptp(allpts[:, 1]))
    W = int(max(34, span * 0.75 + 18))          # always frame the whole traced object
    h, w = g.shape
    x0, x1 = max(0, int(cx) - W), min(w, int(cx) + W)
    y0, y1 = max(0, int(cy) - W), min(h, int(cy) + W)
    sub = g[y0:y1, x0:x1].astype(float)
    if sub.size < 100:
        continue
    lo, hi = np.percentile(sub, [20, 99.7])
    disp = np.clip((sub - lo) / (hi - lo + 1e-6), 0, 1)
    polys = [np.asarray(p, float) - [x0, y0] for p in rec["pieces"]]
    ta, tsrc = t_since_anaphase(rec)
    gl = ("grp %s" % rec["grp"]) if rec["grp"] else "single KT"
    # NEVER truncate the batch name: "20250930 four_ablation_59"[:24] reads as
    # "four_ablation_5", a DIFFERENT real cell. Wrap instead.
    ttl = "%s · %s\n" % (batch, gl)
    ttl += ("t%+.1fmin%s · " % (ta / 60, "" if tsrc == "event" else "*")) if ta is not None else "t=? · "
    ttl += "%.2fµm a%.1f" % (rec["major"], rec["aspect"])
    if rec["n_pieces"] > 1:
        ttl += " · %d pieces" % rec["n_pieces"]
    items.append((ttl, disp, polys, batch))
    print("  %-46s grp=%-5s frame=%-4d pieces=%d major=%.2f  (%s, %d frames traced)"
          % (batch, rec["grp"], rec["frame"], rec["n_pieces"], rec["major"], rule, ntr))

n = len(items)
if n == 0:
    sys.exit("no lagging outline examples built")
ncol = 4
nrow = (n + ncol - 1) // ncol
barpx = 2.0 / PX


def build(show_outline, fname, note):
    fig, axs = plt.subplots(nrow, ncol, figsize=(ncol * 3.0, nrow * 3.2), squeeze=False)
    for k, (ttl, disp, polys, batch) in enumerate(items):
        a = axs[k // ncol][k % ncol]
        a.imshow(disp, cmap="gray", interpolation="nearest")
        if show_outline:
            for p in polys:                       # HER trace, closed; nothing segmented
                q = np.vstack([p, p[:1]])
                a.plot(q[:, 0], q[:, 1], color="#ff3b3b", lw=1.1)
        lib.mark_excluded_ax(a, batch, ttl, fontsize=6.4)
        a.set_xticks([]); a.set_yticks([])
        a.set_xlim(0, disp.shape[1]); a.set_ylim(disp.shape[0], 0)
        a.plot([3, 3 + barpx], [disp.shape[0] - 5, disp.shape[0] - 5], color="white", lw=2.5)
        a.text(3 + barpx / 2, disp.shape[0] - 7, "2 µm", color="white", fontsize=6.5,
               ha="center", va="bottom")
    for k in range(n, nrow * ncol):
        axs[k // ncol][k % ncol].axis("off")
    fig.suptitle("Lagging-chromosome examples from MANUAL outlines (16-bit fluor TIF; %s; "
                 "white bar = 2µm) — %d lagging KTs, one per (cell, grp)\n"
                 "t = from the annotation's own Anaphase event; t* = fallback to the master's "
                 "Anaphase Onset (different clock — sign may not be meaningful)" % (note, n),
                 x=.01, ha="left", fontweight="bold", fontsize=10)
    plt.tight_layout()
    plt.savefig("%s/%s" % (OUT, fname), bbox_inches="tight", dpi=130)
    plt.close()


build(False, "G4_lagging_examples_outlines.png", "no overlay")
build(True, "G4_lagging_examples_outlines_traced.png",
      "red = HER traced outline, fractured pieces drawn separately")

# ---- register both figures so the deck's placed==registered invariant holds ----
HEADER = ["batch", "grp", "frame", "n_pieces", "major_um", "aspect_ratio",
          "t_since_anaphase_min", "t_source"]
TABLE = []
for rec, rule, ntr in picks:
    ta, tsrc = t_since_anaphase(rec)
    TABLE.append([rec["batch"], rec["grp"] or "", rec["frame"], rec["n_pieces"],
                  round(rec["major"], 3), round(rec["aspect"], 3),
                  "" if ta is None else round(ta / 60.0, 2), tsrc or ""])
SRC = ["/Volumes/4 MB/annotations/kt_outlines.csv", "/Volumes/4 MB/ABLATION_MASTER.csv"]
CAP = ("Lagging-chromosome examples measured from her MANUAL kt_outlines, one panel per (cell, grp). "
       "Fractured pieces of one kinetochore are unioned before measuring. Replaces the retired "
       "G4_lagging_examples, which derived anaphase lagging shape from circle marks by "
       "auto-segmentation - a technique that is not sufficient for lagging KTs in anaphase.")
for pid, note in (("G4_lagging_examples_outlines", "no overlay"),
                  ("G4_lagging_examples_outlines_traced", "her traced outline in red")):
    lib.record_plot(pid, HEADER, TABLE,
                    {"kind": "image montage", "ncol": ncol, "nrow": nrow,
                     "scale_bar_um": 2.0, "pixel_size_um": PX, "overlay": note},
                    script=SCRIPT, caption=CAP + " Panels: " + note,
                    source=SRC, key_column="batch")

print("lagging outline examples: %d objects -> G4_lagging_examples_outlines.png + _traced.png "
      "(both registered)" % n)
