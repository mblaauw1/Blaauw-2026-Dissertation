#!/usr/bin/env python3
"""KINETOCHORE LOADING AXIS and strain along it (USER 2026-08-05).

Replaces the outline's static long axis, which was never the right basis. Measured this session, median
angle to the metaphase-plate normal:

    sister-pair axis (ground truth)   6.5 deg
    windowed displacement axis       12.0 deg
    outline stretch direction        31.5 deg
    outline LONG axis (old code)     58.5 deg

So the loading direction is defined by GEOMETRY AND MOTION, not by outline shape. Her instruction: use
displacement, backed by the sister-pair axis where a sister exists; displacement alone is validated
against that ground truth (median 10.0 deg apart, 88% within 30 deg) and is the only one of the three
available for POLAR kinetochores, which have no sister.

  loading axis  : per track. Sister-pair axis when the track has an identified partner, else the
                  windowed displacement axis (positions smoothed over WIN frames before differencing, so
                  frame-to-frame biological jitter averages out instead of setting the direction).
  load_extent_um: the outline's extent measured ALONG that axis  -> the quantity under load.
  cross_extent_um: extent perpendicular to it.
  load_ratio    : load_extent / cross_extent, dimensionless and size-normalised.

USER: "if there is a clear blip or mishap ... mark that point as abnormal or an outlier and keep it but
dont use it when making calculations/plotting". Nothing is deleted. Every row is written with `outlier`
and `outlier_reason`; consumers filter on `outlier == 0`.

USER: "generally, for making calculations and plotting for this data, just look at the data between
metaphase onset and anaphase onset." Every row carries `in_window`; stats and figures use in-window,
non-outlier rows only.
"""
import sys, os, csv, json, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np
import lib

csv.field_size_limit(10 ** 9)
ROOT = "/Volumes/4 MB"
OUTCSV = f"{ROOT}/annotations/KT_LOADING_AXIS_20260805.csv"
WIN = 3          # frames smoothed before differencing for the displacement axis
MIN_DISP_PX = 4.0    # a track that never moves this far cannot define a direction
JUMP_MAD = 5.0       # load_extent jump this many MADs from typical -> abnormal

MR = {r["Batch Name"]: r for r in lib.load_master()[0]}
def psec(s):
    s = (s or "").strip()
    if not s: return None
    neg = s.startswith("-"); v = lib.parse_time(s.lstrip("-"))
    return None if v is None else (-v if neg else v)
def window(b):
    r = MR.get(b) or {}
    m, a = psec(r.get("Metaphase Start (s)", "")), psec(r.get("Anaphase Onset (s)", ""))
    return (m, a) if (m is not None and a is not None and a > m) else (None, None)
def px(b):
    try: return float((MR.get(b, {}) or {}).get("Pixel Size (um)", "")) or 0.062
    except Exception: return 0.062

# ---- outlines ------------------------------------------------------------------------------------
PTS = {}
for r in csv.DictReader(open(f"{ROOT}/annotations/kt_outlines.csv", encoding="utf-8", errors="replace")):
    try: P = np.asarray(json.loads(r["points"]), float)
    except Exception: continue
    if P.ndim == 2 and len(P) >= 3: PTS[(r["batch"].strip(), r["id"].strip())] = P

TR = collections.defaultdict(list)
for r in csv.DictReader(open(f"{ROOT}/annotations/KT_OUTLINE_TRACKS_20260723.csv")):
    lab = (r.get("label") or "").strip()
    # USER 2026-08-05: the deck's tension figures plot LAGGING as a third series, and the first build of
    # this table kept only polar/paired — 807 of 4750 KT_TENSION rows had no loading axis to join to, so
    # every lagging series would have silently emptied. Lagging has no sister, so it takes the
    # displacement axis, which is the case that validation was for.
    if lab not in ("polar", "paired", "lagging"): continue
    b = r["batch"].strip()
    ids = [x.strip() for x in (r.get("trace_ids") or "").split(";") if x.strip()]
    pts = [PTS[(b, i)] for i in ids if (b, i) in PTS]
    if not pts: continue
    try:
        TR[(b, lab, r["track_id"])].append(
            dict(frame=int(r["frame"]), t=float(r["t_sec"]), P=np.vstack(pts),
                 cx=float(r["cx_px"]), cy=float(r["cy_px"]),
                 npieces=int(float(r.get("n_pieces") or 1))))
    except Exception:
        continue
for k in TR: TR[k].sort(key=lambda z: z["frame"])

def axis_of(vecs):
    A = np.asarray(vecs, float)
    if A.ndim != 2 or len(A) < 2: return None
    A = A[np.linalg.norm(A, axis=1) > 1e-9]
    if len(A) < 2: return None
    ang = np.arctan2(A[:, 1], A[:, 0]); w = np.linalg.norm(A, axis=1)
    s = (w * np.sin(2 * ang)).sum(); c = (w * np.cos(2 * ang)).sum()
    return (np.degrees(np.arctan2(s, c)) / 2.0) % 180.0

def disp_axis(v):
    xy = np.array([[d["cx"], d["cy"]] for d in v])
    if len(xy) < WIN + 1: return None, 0.0
    k = np.ones(WIN) / WIN
    sm = np.stack([np.convolve(xy[:, 0], k, "valid"), np.convolve(xy[:, 1], k, "valid")], 1)
    dd = np.diff(sm, axis=0)
    return axis_of(dd), float(np.abs(dd).sum())

# sister partner per cell (the two longest paired tracks, as elsewhere)
PAIR_AXIS = {}
bycell = collections.defaultdict(list)
for (b, lab, tid), v in TR.items():
    if lab == "paired": bycell[b].append((tid, v))
for b, lst in bycell.items():
    if len(lst) < 2: continue
    lst = sorted(lst, key=lambda z: -len(z[1]))[:2]
    dA = {d["frame"]: (d["cx"], d["cy"]) for d in lst[0][1]}
    dB = {d["frame"]: (d["cx"], d["cy"]) for d in lst[1][1]}
    com = sorted(set(dA) & set(dB))
    if len(com) < 4: continue
    ax = axis_of([[dB[f][0] - dA[f][0], dB[f][1] - dA[f][1]] for f in com])
    if ax is not None:
        for tid, _ in lst: PAIR_AXIS[(b, tid)] = ax

rows = []; nflag = collections.Counter()
for (b, lab, tid), v in sorted(TR.items()):
    mt, at = window(b)
    pxs = px(b)
    ax_pair = PAIR_AXIS.get((b, tid))
    ax_disp, dtot = disp_axis(v)
    axis = ax_pair if ax_pair is not None else ax_disp
    src = "sister_pair" if ax_pair is not None else "displacement"
    weak = (axis is None) or (ax_pair is None and dtot < MIN_DISP_PX)
    if axis is None:
        nflag["no axis"] += len(v); axis = 0.0; src = "none"
    u = np.array([np.cos(np.radians(axis)), np.sin(np.radians(axis))])
    w = np.array([-u[1], u[0]])
    ext = []
    for d in v:
        pu = d["P"] @ u; pw = d["P"] @ w
        ext.append((float(pu.max() - pu.min()) * pxs, float(pw.max() - pw.min()) * pxs))
    E = np.array(ext)
    de = np.abs(np.diff(E[:, 0])) if len(E) > 1 else np.array([])
    med = float(np.median(de)) if de.size else 0.0
    mad = float(np.median(np.abs(de - med))) or 1e-9
    for i, d in enumerate(v):
        reason = []
        if weak: reason.append("axis_ill_defined")
        if d["npieces"] > 1: reason.append("multi_piece")
        if i > 0 and de.size and abs(E[i, 0] - E[i-1, 0]) > med + JUMP_MAD * mad: reason.append("extent_jump")
        if E[i, 1] <= 0: reason.append("degenerate")
        inwin = 1 if (mt is not None and mt <= d["t"] <= at) else 0
        for r_ in reason: nflag[r_] += 1
        rows.append([b, lab, tid, d["frame"], round(d["t"], 3), round(axis, 2), src,
                     round(E[i, 0], 4), round(E[i, 1], 4),
                     round(E[i, 0] / E[i, 1], 4) if E[i, 1] > 0 else "",
                     inwin, 1 if reason else 0, ";".join(reason)])

hdr = ["batch", "label", "track_id", "frame", "t_sec", "loading_axis_deg", "axis_source",
       "load_extent_um", "cross_extent_um", "load_ratio", "in_window", "outlier", "outlier_reason"]
with open(OUTCSV, "w", newline="") as f:
    w_ = csv.writer(f); w_.writerow(hdr); w_.writerows(rows)

use = [r for r in rows if r[10] == 1 and r[11] == 0]
print(f"tracks={len(TR)}  rows={len(rows)}  usable (in metaphase window, not outlier)={len(use)}")
print(f"axis source: " + str(collections.Counter(r[6] for r in rows).most_common()))
print(f"flags: {dict(nflag)}")
for lab in ("polar", "paired", "lagging"):
    v = [float(r[9]) for r in use if r[1] == lab and r[9] != ""]
    if v: print(f"  {lab:7s} load_ratio n={len(v):5d}  median={np.median(v):.3f}  CV={np.std(v)/np.mean(v)*100:.0f}%")
print(f"-> {OUTCSV}")

# ── joined table: KT_TENSION + the loading-axis columns ───────────────────────────────────────────
# USER 2026-08-05: "i want all the same plots but just with the updated info, so just makring them as
# retured isnt really a solution". Every deck tension figure reads KT_TENSION_20260723.csv, which carries
# `spindle_strain` (extent along the PLATE NORMAL / extent along the plate) and, through the retired
# calibration, `equivalent k-k`. Rather than rewire each builder to a differently-keyed file, emit the
# same schema with the loading-axis columns appended — KT_TENSION already carries `track_id` and `frame`,
# the exact keys this table uses, so the join is exact and every builder swaps one column name.
#
# CORRECTION 2026-08-05 (user was right): an earlier version of this comment said spindle_strain "cannot
# follow a plate that rotates". That is FALSE — kt_tension.py picks the plate line nearest in time to each
# frame, so the plate normal is already per-frame. And using the sister-pair axis for paired kinetochores
# but the displacement axis for polar ones made polar-vs-paired a comparison between two DIFFERENT axis
# definitions, which is a confound. Her instruction: one axis for every kinetochore, the pole axis /
# plate normal, for paired and polar alike. That is exactly what `spindle_strain` already is.
#
# So this table's job changed. `load_ratio` is no longer the metric the figures use; `spindle_strain` is,
# renamed in every label to DISTORTION ALONG THE SPINDLE AXIS. What this file still contributes is:
#   * the per-row outline-quality flags (multi-piece, degenerate, extent jump) — axis-independent QC
#   * `in_window` — the metaphase-onset-to-anaphase-onset restriction she asked for
#   * the loading-axis columns themselves, kept because the displacement direction is useful elsewhere
# The jump flag is recomputed on the SPINDLE extent below, so the QC matches the metric it guards.
TENIN = f"{ROOT}/annotations/KT_TENSION_20260723.csv"
JOINED = f"{ROOT}/annotations/KT_TENSION_LOADAXIS_20260805.csv"
LK = {(r[0], r[2], str(r[3])): r for r in rows}
tin = list(csv.DictReader(open(TENIN)))

# recompute the extent-jump flag on spindle_extent_um, per track, same MAD rule as the loading axis
_bytrack = collections.defaultdict(list)
for i, r in enumerate(tin):
    try: _bytrack[(r["batch"], r["track_id"])].append((int(r["frame"]), i, float(r["spindle_extent_um"])))
    except Exception: pass
_jump = set()
for k, v in _bytrack.items():
    v.sort()
    e = np.array([z[2] for z in v])
    if len(e) < 3: continue
    de = np.abs(np.diff(e))
    med = float(np.median(de)); mad = float(np.median(np.abs(de - med))) or 1e-9
    for j in range(1, len(v)):
        if abs(e[j] - e[j-1]) > med + JUMP_MAD * mad: _jump.add(v[j][1])
print(f"spindle-extent jumps flagged: {len(_jump)} rows")

extra = ["load_ratio", "load_extent_um", "cross_extent_um", "loading_axis_deg",
         "axis_source", "in_window", "outlier", "outlier_reason"]
nj = 0
with open(JOINED, "w", newline="") as f:
    w_ = csv.writer(f); w_.writerow(list(tin[0].keys()) + extra)
    for i, r in enumerate(tin):
        m = LK.get((r["batch"], r["track_id"], str(r["frame"])))
        if m: nj += 1
        # outline-quality reasons carry over, minus the loading-axis-specific ones; the jump flag is the
        # spindle-extent one computed just above.
        reasons = [x for x in ((m[12] if m else "no_loading_axis").split(";"))
                   if x and x not in ("extent_jump", "axis_ill_defined")]
        if i in _jump: reasons.append("spindle_extent_jump")
        inwin = (m[10] if m else "")
        if not m:
            # no loading axis, but spindle_strain still exists — recover in_window from the master window
            _mt, _at = window(r["batch"]); _t = None
            try: _t = float(r["t_sec"])
            except Exception: pass
            inwin = 1 if (_mt is not None and _t is not None and _mt <= _t <= _at) else 0
        w_.writerow(list(r.values()) + [(m[9] if m else ""), (m[7] if m else ""), (m[8] if m else ""),
                                        (m[5] if m else ""), (m[6] if m else "none"), inwin,
                                        1 if reasons else 0, ";".join(reasons)])
print(f"joined table: {nj}/{len(tin)} KT_TENSION rows carry a loading axis ({nj/len(tin)*100:.1f}%)")
print(f"  rows usable for the DISTORTION figures (spindle_strain present, not flagged): "
      + str(sum(1 for i, r in enumerate(tin) if r["spindle_strain"] != "" and i not in _jump)))
print(f"-> {JOINED}")
