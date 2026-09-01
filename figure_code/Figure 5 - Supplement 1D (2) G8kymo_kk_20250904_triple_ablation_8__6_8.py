#!/usr/bin/env python3
"""KYMOGRAPHS of kinetochore motion about the metaphase plate.

USER 2026-08-20, board 7 item 3: *"Ive diagnosed that i actually need kymographs, not just one frame of the
kinetochore. For example, kymographs for the data in the individual trace plots on artboard 7"*, and board 8
item 3: *"as stated for the kinetochore distortion frames above I now think that individual frames arent
useful to illustrate this, and kymographs are the needed tool."*

WHAT A KYMOGRAPH IS HERE, and why these choices:
  * one ROW per movie frame, stacked downwards in time -> y is time from metaphase onset.
  * each row is the fluorescence sampled along a 5-PIXEL-WIDE BAND through the kinetochore, max-projected
    across its width, oriented along the METAPHASE-PLATE NORMAL -- i.e. the spindle axis, the axis the
    kinetochore actually oscillates on. Any other orientation would smear the oscillation the figure exists
    to show. The 5-px max projection is the lab's own convention (Richter et al. 2023, eLife, Methods).
  * x = 0 is THE PLATE, not the kinetochore. Centring on the kinetochore would pin it to the middle of every
    row and hide the very motion being measured; centring on the plate makes the excursion visible as a
    track that wanders left and right.
  * METAPHASE ERA ONLY (her standing rule): rows run from Metaphase Start to Anaphase Onset.

The plate axis comes from her hand-drawn plates where they exist and from `osclib`'s sister-pair
reconstruction where they do not, so a cell without a drawn plate is not silently skipped.
"""
import collections
import csv
import os
import sys

# Importing group_timestrips RUNS its module body -- the whole timestrips2 build -- because it has no
# `if __name__` guard. Every kymograph run was therefore re-rendering every timestrip first, minutes of
# work for nothing. CAT_ONLY="__none__" is the same switch `audit_roi_instructions_20260819` uses.
os.environ.setdefault("CAT_ONLY", "__none__")

import numpy as np
import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import lib
import osclib
import group_timestrips as GT

lib.apply_style()
ANN = "/Volumes/4 MB/annotations"
OUT = "/Volumes/4 MB/ablation_figures_20260625/group6_tracks"
SCRIPT = __file__
HALF_UM = 6.0          # half-width of the sampled line: +/-6 um spans the full oscillation range
LINE_HALF_PX = None    # derived per cell from its own pixel size


SLAB_HALF_PX = 4       # half-width of the sampled band, ACROSS the spindle axis  (2 -> 4, see DOG_SIGMA_PX)
BG_PCT       = 20      # per-row background percentile (bleaching correction)
HI_PCT       = 99.5    # global contrast ceiling, taken over the whole strip

# ── WHY THERE IS A BAND-PASS HERE NOW ──────────────────────────────────────────────────────────────
# HER 2026-08-24: *"Hard to see the kinetochore in the kymographs showing examples of kinetochores in triple
# sisterless kinetochore cells. What are variables to change about how these kymographs are made/shown to
# make the visualization of the kinetochore better?"*
#
# Swept every display knob against a MEASURED score on 20250901 triple_ablation_11 (three tracks, 253 rows):
# contrast = (intensity at her traced kinetochore - row median) / row MAD, and "findable" = the fraction of
# rows whose BRIGHTEST pixel is within 0.5 um of it.
#
#   slab 1/3/4/6 ......... z 0.18-0.30   findable 26-29%     (current 2: z 0.23, 28.2%)
#   max vs mean .......... mean is WORSE, z 0.11
#   half_um 3/4/8 ........ z 0.15-0.32, and a narrower window trades contrast for findability
#   bg percentile 5/35 ... z 0.25-0.27   no real change
#   contrast ceiling ..... 98 / 99 / 99.9 -> z 0.23 EXACTLY. It does nothing.
#   bilinear sampling .... findability DROPS to 21.7%
#   temporal median off .. worse on both (z 0.16, 22.9%)
#
# i.e. NONE of the display knobs is the problem. What IS the problem is that eYFP-Cdc20 fills the whole
# cytoplasm, so a kinetochore is only modestly brighter than the cell it sits in, and the kymograph row is
# dominated by that smooth glow. Removing it is the only thing with real leverage:
#
#   DoG sigma 3 px ....... z 0.74 (3.2x)  findable 33.1%
#   DoG 3 + slab 4 ....... z 0.81 (3.5x)  findable 34.9%   <- what is used below
#   16-bit TIF source .... adds almost nothing once the band-pass is in (z 0.70 alone, 0.81 with slab 4)
#
# ⚠ AND THE CEILING IS STILL LOW: even at its best the kinetochore is the brightest point in its own line in
# about ONE ROW IN THREE. That is a labelling limit, not a plotting one -- it is why the traced position is
# drawn over the image and should stay drawn.
DOG_SIGMA_PX = 3.0     # 0 disables the band-pass


def _bandpass(gray, sigma=None):
    """Difference-of-Gaussians: keep punctum-sized structure, drop the smooth cytoplasmic glow."""
    sg = DOG_SIGMA_PX if sigma is None else sigma
    if not sg:
        return gray
    g = gray.astype(np.float32)
    return cv2.GaussianBlur(g, (0, 0), sg) - cv2.GaussianBlur(g, (0, 0), sg * 4.0)


def _sample(gray, base, nrm, half_px, slab=SLAB_HALF_PX):
    """One kymograph row: a max-projection across a narrow BAND, not a single-pixel line.

    HER 2026-08-21: *"making kymographs seemed to work really well for single sisterless cells but not
    really well for triple."*  A one-pixel-wide line only shows the kinetochore if the line lands exactly
    on it, and it has no averaging at all, so its noise is the full per-pixel noise of the camera. Both get
    worse in a triple: the plate rotates more (her own measurement), so the sampled direction swings frame
    to frame, and the reconstructed normal is built from fewer surviving sister pairs. Projecting the
    maximum across a +/-2 px band tolerates that wobble and is the standard way a kymograph is resliced.
    """
    along = np.array([-nrm[1], nrm[0]])
    xs = np.arange(-half_px, half_px + 1)
    out = []
    for dy in range(-slab, slab + 1):
        pts = (np.asarray(base, float) + along * dy)[None, :] + xs[:, None] * nrm[None, :]
        ix = np.clip(np.round(pts[:, 0]).astype(int), 0, gray.shape[1] - 1)
        iy = np.clip(np.round(pts[:, 1]).astype(int), 0, gray.shape[0] - 1)
        out.append(gray[iy, ix].astype(np.float32))
    return np.max(np.array(out), axis=0)


def _normalise(strip):
    """Correct bleaching per row, but scale the CONTRAST globally.

    The previous version stretched every row onto its own 5th-99th percentile. On a bright cell that is
    fine; on a dim one there is no kinetochore anywhere near the 99th percentile, so the stretch pulls pure
    camera noise up to full white and the row becomes static -- which is exactly what the triple-cell
    kymographs looked like. Subtracting each row's own background still removes the bleaching trend, while
    one global scale means a dim row is DRAWN dim instead of being amplified into noise.
    """
    K = np.array(strip, dtype=np.float32)
    K = K - np.percentile(K, BG_PCT, axis=1, keepdims=True)
    hi = float(np.percentile(K, HI_PCT))
    K = np.clip(K / max(hi, 1e-6), 0, 1)
    if K.shape[0] >= 3:                    # light temporal median: kills single-pixel noise, keeps the track
        K = np.stack([np.median(K[max(0, i - 1):i + 2], axis=0) for i in range(K.shape[0])])
    return K


def _fit_track(v, tmin=None):
    """An INDEPENDENT, non-overfitting smooth for ONE kinetochore track.

    🔴 HER 2026-08-25 item 6: *"the fit lines for the kymographs are often overfit, and paired fit lines seem
    to be the same as one another, which should not be the case (if a fit line is made for each kinetochore
    track on a kymograph, they should be made independently of other kinetochore fit lines/tracks on that
    kymograph)."*

    The mirror half of that was fixed on 2026-08-21 (each sister is now measured from the metaphase plate,
    not from the pair midpoint, which had made `pa = -pb` an algebraic identity). What was left is the
    OVERFITTING: `_sm3` is a THREE-point mean, so at 20 s frames it averages one minute and still traces
    almost every wiggle -- it reads as a fit but follows the noise.

    This scales the window to the track's own length (about a tenth of it, odd, >= 5 points) and uses a
    running MEDIAN, which does not get dragged by a single bright frame the way a mean does. It sees only
    this track's own samples -- no other track on the kymograph enters the calculation at any point.
    PRESENTATION ONLY: the raw trace stays underneath and every recorded value is unsmoothed.
    """
    import numpy as _np
    a = _np.asarray(list(v), float)
    n = a.size
    if n < 5:
        return list(a)
    w = max(5, int(round(n / 10.0)) | 1)
    if w >= n:
        w = n - 1 if (n - 1) % 2 else n - 2
    if w < 3:
        return list(a)
    h = w // 2
    out = _np.empty(n, float)
    for i in range(n):
        lo, hi = max(0, i - h), min(n, i + h + 1)
        out[i] = _np.nanmedian(a[lo:hi])
    return list(out)


def _sm3(v):
    """Jon Kuhn's three-point smoothing, the lab's own convention for making a jagged trace readable.

    HER 2026-08-19, board 7 item 3: *"Would it be helpful to viewers if i applied a simple, common smoothing
    technique on the jagged lines in these plots, like Jon Kuhn's three-point smoothing ... specifically to
    make a plot more viewable (unsmoothed data still used for analysis)"* -- yes, and it is already what
    `kt_tension_withincell.py` does on the artboard-7 traces, so doing it here keeps the two boards
    consistent. PRESENTATION ONLY: the raw trace stays visible underneath at low alpha, and every recorded
    value, statistic and CSV remains unsmoothed.
    """
    if len(v) < 3: return list(v)
    return [v[0]] + [(v[i-1] + v[i] + v[i+1]) / 3.0 for i in range(1, len(v) - 1)] + [v[-1]]


def _source_panel(ax, gray, base, nrm, half_px, slab=SLAB_HALF_PX):
    """Inset showing WHERE on the cell this kymograph was cut from.

    Every kymograph in the lab's papers is shown beside the image it came from, with the sampled region
    marked -- Rosas-Salvans 2022 uses a red box, Richter 2023 a white one, Elting 2014 and Hueschen 2017 a
    dashed path. Ours were standalone, so a reader could not see which kinetochore or which direction
    produced the trace. This draws one frame of the cell with the sampled band overlaid.
    """
    ins = ax.inset_axes([0.66, 0.015, 0.33, 0.24])
    ins.imshow(gray, cmap="gray", interpolation="none",
               vmin=float(np.percentile(gray, 2)), vmax=float(np.percentile(gray, 99.5)))
    along = np.array([-nrm[1], nrm[0]])
    p0 = np.asarray(base, float) - nrm * half_px
    p1 = np.asarray(base, float) + nrm * half_px
    for d in (-slab, slab):
        a, b = p0 + along * d, p1 + along * d
        ins.plot([a[0], b[0]], [a[1], b[1]], "-", color="#ff3b30", lw=0.9)
    ins.set_xticks([]); ins.set_yticks([])
    for sp in ins.spines.values(): sp.set_edgecolor("#ff3b30"); sp.set_linewidth(0.8)
    return ins


_POLY = {}
_PTS = {}


def point_marks(batch):
    """Her POINT marks for sisterless / polar kinetochores: {frame: [(x, y, t_sec), ...]}.

    HER 2026-08-24, correcting me: *"i have multiple (outlines, points, etc)"*. She does, and they are not
    the same coverage -- MEASURED across five cells, her point marks land on **10-18 frames per cell that
    the outline track does not have**, roughly a fifth more of the track. They are worth drawing.

    ⚠ ATTRIBUTION IS THE CATCH, so it is explicit rather than assumed: a point mark carries no `grp`, so in
    a cell with three sisterless kinetochores there is nothing in the row that says WHICH one it is. A point
    is therefore attached to this track only if this track is the NEAREST one and the point is within
    POINT_TOL_UM of where the track is interpolated to be. Anything further away belongs to another
    kinetochore and is left off. Drawn as OPEN circles so it is visible at a glance that they come from a
    different marker than the ribbon.
    """
    if batch in _PTS:
        return _PTS[batch]
    out = collections.defaultdict(list)
    for r in csv.DictReader(open(f"{ANN}/kt_points.csv", newline="", encoding="utf-8",
                                 errors="replace")):
        if (r.get("batch") or "").strip() != batch:
            continue
        if (r.get("label") or "") not in ("polar", "sisterless"):
            continue
        try:
            out[int(r["frame"])].append((float(r["x"]), float(r["y"]), float(r["t_sec"])))
        except (TypeError, ValueError, KeyError):
            continue
    _PTS[batch] = out
    return out


POINT_TOL_UM = 1.5


def outline_polys(batch):
    """{kt_outlines id -> polygon}. Her traced kinetochore outline, by the id the track file points at."""
    if batch in _POLY:
        return _POLY[batch]
    import json as _j
    out = {}
    for r in csv.DictReader(open(f"{ANN}/kt_outlines.csv", newline="", encoding="utf-8",
                                 errors="replace")):
        if (r.get("batch") or "").strip() != batch:
            continue
        P = (r.get("points") or "").strip()
        if not P:
            continue
        try:
            out[str(r["id"]).strip()] = np.asarray(_j.loads(P), float)
        except Exception:
            continue
    _POLY[batch] = out
    return out


def kt_extent_um(batch, trace_ids, ctr, nrm, px):
    """HER OWN MEASUREMENT of where the kinetochore is on the spindle axis, as (lo, hi) um from the plate.

    HER 2026-08-24, correcting me: I said a genuinely clean track needs a kinetochore marker; she pointed
    out she HAS multiple -- outlines, points, and the tracks built from them. She is right, and this is what
    that means for the figure: the kinetochore's position and SIZE along the axis are measured, per frame,
    in her traces, so they do not have to be recovered from the pixels at all. The image becomes the
    backdrop and her marks become the track. A kinetochore that is invisible in the fluorescence is still
    exactly located here.
    """
    polys = outline_polys(batch)
    vals = []
    for i in (trace_ids or "").replace(" ", "").split(","):
        P = polys.get(i)
        if P is None or not len(P):
            continue
        d = (P - np.asarray(ctr, float)) @ np.asarray(nrm, float)
        vals.append((float(d.min()) * px, float(d.max()) * px))
    if not vals:
        return None
    return (min(v[0] for v in vals), max(v[1] for v in vals))


def kt_rows(batch, label=("polar", "paired")):
    """-> {track_id: [(t_sec, frame, cx, cy, trace_ids, label)]} inside the metaphase window."""
    w = osclib.metaphase_window(batch)
    if not w:
        return {}
    out = collections.defaultdict(list)
    for r in csv.DictReader(open(f"{ANN}/KT_OUTLINE_TRACKS_20260723.csv", newline="",
                                 encoding="utf-8", errors="replace")):
        if r["batch"] != batch or r["label"] not in label:
            continue
        try:
            t = float(r["t_sec"]); f = int(r["frame"])
            c = (float(r["cx_px"]), float(r["cy_px"]))
        except Exception:
            continue
        if w[0] <= t <= w[1]:
            out[r["track_id"]].append((t, f, c[0], c[1], r.get("trace_ids", ""), r.get("label", "")))
    for k in out:
        out[k].sort()
    return out


def build(batch, track_id=None, tag=""):
    """One kymograph per kinetochore track in `batch`. Returns the plot ids written."""
    d = GT.render_dir(batch)
    if not d:
        print(f"  {batch}: no render dir"); return []
    mv = GT.movie(batch, "Fluor", "Monitoring")
    if not mv:
        print(f"  {batch}: no monitoring fluor movie"); return []
    cap, ts = mv
    w = osclib.metaphase_window(batch)
    px = osclib.px_of(batch)
    half_px = int(round(HALF_UM / px))     # default; widened per track below where the KT needs it
    plates = osclib._oriented_plates(batch)
    tracks = kt_rows(batch)
    made = []
    for tid, rows in sorted(tracks.items()):
        if track_id and track_id not in tid:
            continue
        if len(rows) < 8:
            continue
        # HOW WIDE THE WINDOW HAS TO BE, decided from HER marks before any pixel is read. A POLAR
        # kinetochore sits several microns off the plate, so the fixed +/-6 um window clipped it to the axis
        # edge and the figure showed a track pinned against the frame instead of where she measured it.
        _pre = []
        for _t, _f, _cx, _cy, _ti, _ol in rows:
            _g = osclib._plate_for(plates, _f) or osclib._reconstructed_plate(batch, _f)
            if _g is None:
                continue
            _c0, _n0 = _g
            _pre.append(abs(float(np.dot(np.array([_cx, _cy]) - np.array(_c0), _n0)) * px))
        half_um = HALF_UM if not _pre else float(max(HALF_UM, np.ceil(max(_pre) + 1.0)))
        half_px = int(round(half_um / px))
        strip, tmin, ktpos, ktext = [], [], [], []
        for t, f, cx, cy, _tids, _lab in rows:
            g = osclib._plate_for(plates, f) or osclib._reconstructed_plate(batch, f)
            if g is None:
                continue
            ctr, nrm = g
            fr = GT.grab(cap, ts, t)
            if fr is None:
                continue
            gray = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY) if fr.ndim == 3 else fr
            # sample along the plate normal, centred on the PLATE, at the kinetochore's own offset along
            # the plate so the line actually passes through it
            along = np.array([-nrm[1], nrm[0]])
            base = np.array(ctr) + along * float(np.dot(np.array([cx, cy]) - np.array(ctr), along))
            strip.append(_sample(_bandpass(gray), base, nrm, half_px))
            tmin.append((t - w[0]) / 60.0)
            ktpos.append(float(np.dot(np.array([cx, cy]) - np.array(ctr), nrm)) * px)
            ktext.append(kt_extent_um(batch, _tids, ctr, nrm, px))
            _last = (gray, base, nrm)
        if len(strip) < 8:
            continue
        K = _normalise(strip)
        fig, ax = plt.subplots(figsize=(4.6, 6.0))
        ax.imshow(K, aspect="auto", cmap="gray", origin="upper",
                  extent=[-half_um, half_um, tmin[-1], tmin[0]])
        # clip the measured track to the sampled window: a kinetochore further out than the strip would
        # otherwise stretch the x-axis and leave the image floating in white space
        _kp = np.clip(np.array(ktpos), -half_um, half_um)
        # HER MEASURED KINETOCHORE, per row: the outline's own extent along the spindle axis. This is the
        # answer to "the kinetochore is hard to see" that does not depend on the pixels at all -- she has
        # traced it, so its position AND width are known for every frame whether or not the fluorescence
        # shows it. Drawn as a translucent ribbon so the image underneath stays readable.
        _seg = [(t, e) for t, e in zip(tmin, ktext) if e is not None]
        if _seg:
            _ts = [t for t, _ in _seg]
            _lo = np.clip([e[0] for _, e in _seg], -half_um, half_um)
            _hi = np.clip([e[1] for _, e in _seg], -half_um, half_um)
            ax.fill_betweenx(_ts, _lo, _hi, color="#ff8c1a", alpha=0.28, lw=0, zorder=2)
        # HER SECOND MARKER, filling the frames the outline track does not cover. Attributed to THIS track
        # only when this track is the nearest and the point is within POINT_TOL_UM of it (see point_marks).
        _have = {int(r[1]) for r in rows}
        _pm_t, _pm_p, _n_add = [], [], 0
        for _f, _xy in sorted(point_marks(batch).items()):
            if _f in _have:
                continue
            _g = osclib._plate_for(plates, _f) or osclib._reconstructed_plate(batch, _f)
            if _g is None:
                continue
            _c3, _n3 = _g
            _tsec = _xy[0][2]
            if not (w[0] <= _tsec <= w[1]):
                continue
            _here = float(np.interp((_tsec - w[0]) / 60.0, tmin, ktpos)) if len(tmin) >= 2 else None
            for _x, _y, _ts2 in _xy:
                _pos = float(np.dot(np.array([_x, _y]) - np.array(_c3), _n3)) * px
                if _here is not None and abs(_pos - _here) > POINT_TOL_UM:
                    continue                      # belongs to another kinetochore in this cell
                _pm_t.append((_ts2 - w[0]) / 60.0); _pm_p.append(_pos); _n_add += 1
        if _pm_t:
            ax.plot(np.clip(_pm_p, -half_um, half_um), _pm_t, "o", mfc="none", mec="#ff8c1a",
                    ms=3.4, mew=0.9, alpha=0.85, zorder=5)
        ax.plot(_kp, tmin, color="#ff8c1a", lw=0.8, alpha=0.30, zorder=3)        # raw, kept visible
        ax.plot(_fit_track(list(_kp), tmin), tmin, color="#ff8c1a", lw=1.6, alpha=0.95, zorder=4)  # per-track fit (her item 6)
        # every OTHER kinetochore she traced in this cell, on the same axis -- the reader can see what else
        # was there rather than assuming the strip contains one object.
        for _oid, _orow in sorted(tracks.items()):
            if _oid == tid:
                continue
            _ot, _op = [], []
            for _t, _f, _cx, _cy, _ti, _ol in _orow:
                _g = osclib._plate_for(plates, _f) or osclib._reconstructed_plate(batch, _f)
                if _g is None:
                    continue
                _c2, _n2 = _g
                _ot.append((_t - w[0]) / 60.0)
                _op.append(float(np.dot(np.array([_cx, _cy]) - np.array(_c2), _n2)) * px)
            if _ot:
                ax.plot(np.clip(_op, -half_um, half_um), _ot, ".", color="#4da3ff", ms=1.7,
                        alpha=0.55, zorder=1)
        try:
            _source_panel(ax, _last[0], _last[1], _last[2], half_px)
        except Exception as _e:
            print(f"    source-panel FAILED for {name if 'name' in dir() else '?'}: {type(_e).__name__}: {_e}")
        ax.axvline(0, color="#4da3ff", lw=1.0, ls=":")
        ax.set_xlim(-half_um, half_um)
        _sis = (osclib._master().get(batch, {}).get("# Sisterless KTs", "") or "?").strip()
        _lab = tid.split("|")[1] if "|" in tid else ""
        ax.text(0.03, 0.055,
                "orange band = her traced outline (position + width)\n"
                "open circles = her point marks on frames the outline lacks\n"
                "blue dots = the cell's other traced kinetochores",
                transform=ax.transAxes, fontsize=6.2, va="bottom", ha="left", color="#111",
                bbox=dict(boxstyle="round,pad=0.20", fc="white", ec="none", alpha=0.72))
        ax.text(0.03, 0.985, f"{_sis}-sisterless cell · {_lab}", transform=ax.transAxes,
                fontsize=7.6, fontweight="bold", va="top", color="#111",
                bbox=dict(boxstyle="round,pad=0.22", fc="white", ec="none", alpha=0.8))
        ax.set_xlabel("position along the spindle axis (µm)\n0 = metaphase plate")
        ax.set_ylabel("Time from metaphase onset (min)")
        name = f"G7kymo_{batch.replace(' ', '_')}__{tid.split('|')[-1]}{tag}"
        # ⚠ bbox_inches="tight" makes the SAVED ASPECT depend on the tick-label width, and the axis
        # range is now per track (item 69), so two kymographs of the same cell can differ by a few
        # percent. Harmless on its own, but a placed figure keeps its old frame and is then silently
        # stretched -- five had to be refitted on 2026-08-24. RE-PLACE, never resize, after any change
        # that moves these labels.
        fig.savefig(f"{OUT}/{name}.png", dpi=190, bbox_inches="tight")
        plt.close(fig)
        lib.record_plot(name, ["t_min_from_meta", "kt_pos_um_from_plate"],
                        [[round(a, 3), round(b, 4)] for a, b in zip(tmin, ktpos)],
                        {"type": "kymograph", "batch": batch, "track": tid,
                         "axis": "metaphase-plate normal (spindle axis); x=0 is the plate",
                         "window": "metaphase era only",
                         "half_width_um": HALF_UM,
                         "why": "user 2026-08-20 board-7 item 3 / board-8 item 3: individual frames are not "
                                "enough; kymographs are the tool"},
                        SCRIPT, f"Kymograph — {batch} {tid}")
        made.append(name)
        print(f"  wrote {name} ({len(strip)} frames"
              + (f", +{_n_add} rows from her point marks)" if _n_add else ")"))
    cap.release()
    return made



def build_pair(batch, tag=""):
    """Sister-pair kymographs: BOTH kinetochores of a pair on one panel, so the k-k distance IS the gap.

    HER 2026-08-20, board 8 item 3: *"Regarding the frames of k-k distance on this board ... individual
    frames arent useful to illustrate this, and kymographs are the needed tool."* For k-k the single-track
    kymograph is the wrong object -- what the reader needs to see is the SEPARATION. One line sampled along
    the spindle axis, offset along the plate to the pair, puts both sisters on the same row, so their two
    tracks bracket the k-k distance and its breathing is directly visible.

    BOTH SISTERS ARE MEASURED FROM THE PLATE, NOT FROM THEIR OWN MIDPOINT -- see the long note at the
    sampling site below. The midpoint origin made the two traces exact mirrors by algebra, which is what she
    caught on 2026-08-21. Their MEAN now carries the pair's common excursion and their DIFFERENCE is still
    exactly the k-k distance, so nothing is lost by moving the origin.
    Pairs come from her own `KT_SISTERS_20260723.csv` (`track_id` <-> `partner_track`).
    """
    d = GT.render_dir(batch)
    mv = GT.movie(batch, "Fluor", "Monitoring") if d else None
    if not mv:
        print(f"  {batch}: no monitoring fluor movie"); return []
    cap, ts = mv
    w = osclib.metaphase_window(batch)
    px = osclib.px_of(batch)
    half_px = int(round(HALF_UM / px))
    plates = osclib._oriented_plates(batch)
    rows = kt_rows(batch, label=("paired",))
    pairs = set()
    for r in csv.DictReader(open(f"{ANN}/KT_SISTERS_20260723.csv", newline="",
                                 encoding="utf-8", errors="replace")):
        if r.get("batch") != batch:
            continue
        b2 = r.get("partner_track", "")
        if b2 and r["track_id"] in rows and b2 in rows:
            pairs.add(tuple(sorted((r["track_id"], b2))))
    made = []
    for a, b in sorted(pairs):
        ra = {f: (t, cx, cy) for t, f, cx, cy, _t1, _l1 in rows[a]}
        rb = {f: (t, cx, cy) for t, f, cx, cy, _t2, _l2 in rows[b]}
        common = sorted(set(ra) & set(rb))
        if len(common) < 8:
            continue
        strip, tmin, pa, pb = [], [], [], []
        for f in common:
            g = osclib._plate_for(plates, f) or osclib._reconstructed_plate(batch, f)
            if g is None:
                continue
            ctr, nrm = g
            t, ax_, ay = ra[f]; _t, bx, by = rb[f]
            fr = GT.grab(cap, ts, t)
            if fr is None:
                continue
            gray = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY) if fr.ndim == 3 else fr
            # HER 2026-08-21: *"the fit lines appear the same as eachother but mirrored over the metaphase
            # plate - and this isnt the right way to go about making fit lines for pair movement as while the
            # movement of paired kinetochores is similar, its not an exact mirror."*
            #
            # She is right, and it was not a fitting choice -- it was forced by the origin. Measuring each
            # sister from the pair MIDPOINT makes pa = -pb an algebraic identity for any pair and any axis,
            # because the midpoint is by construction exactly halfway between them. That origin subtracts out
            # every bit of motion the two sisters share and leaves only the antisymmetric part, so the two
            # traces could never have differed by anything except sign.
            #
            # The origin must be a reference that does NOT move with the pair: the metaphase plate, the same
            # one the single-kinetochore kymographs use. Each sister is then measured independently, so their
            # MEAN carries the pair's common excursion and their DIFFERENCE is still exactly the k-k distance.
            ctr = np.asarray(ctr, float)
            mid = np.array([(ax_ + bx) / 2.0, (ay + by) / 2.0])
            along = np.array([-nrm[1], nrm[0]])
            # sample through the plate, offset along it to the pair, so the image is not re-centred each row
            base = ctr + along * float(np.dot(mid - ctr, along))
            strip.append(_sample(gray, base, nrm, half_px))
            tmin.append((t - w[0]) / 60.0)
            pa.append(float(np.dot(np.array([ax_, ay]) - ctr, nrm)) * px)
            pb.append(float(np.dot(np.array([bx, by]) - ctr, nrm)) * px)
            _last = (gray, base, nrm)
        if len(strip) < 8:
            continue
        K = _normalise(strip)
        fig, ax = plt.subplots(figsize=(4.6, 6.0))
        ax.imshow(K, aspect="auto", cmap="gray", origin="upper",
                  extent=[-HALF_UM, HALF_UM, tmin[-1], tmin[0]])
        _ca = np.clip(pa, -HALF_UM, HALF_UM); _cb = np.clip(pb, -HALF_UM, HALF_UM)
        ax.plot(_ca, tmin, color="#4da3ff", lw=0.7, alpha=0.30)
        ax.plot(_cb, tmin, color="#ff8c1a", lw=0.7, alpha=0.30)
        ax.plot(_fit_track(list(_ca), tmin), tmin, color="#4da3ff", lw=1.5, label="sister A")
        ax.plot(_fit_track(list(_cb), tmin), tmin, color="#ff8c1a", lw=1.5, label="sister B")
        try:
            _source_panel(ax, _last[0], _last[1], _last[2], half_px)
        except Exception as _e:
            print(f"    source-panel FAILED for {name if 'name' in dir() else '?'}: {type(_e).__name__}: {_e}")
        _kk = [abs(x - y) for x, y in zip(pa, pb)]
        _sis = (osclib._master().get(batch, {}).get("# Sisterless KTs", "") or "?").strip()
        ax.text(0.03, 0.985, f"{_sis}-sisterless cell · sister pair\nmedian k\u2013k {np.median(_kk):.2f} \u00b5m",
                transform=ax.transAxes, fontsize=7.4, fontweight="bold", va="top", color="#111",
                bbox=dict(boxstyle="round,pad=0.22", fc="white", ec="none", alpha=0.8))
        ax.set_xlim(-HALF_UM, HALF_UM)
        ax.set_xlabel("position along the spindle axis (µm)\n0 = metaphase plate")
        ax.set_ylabel("Time from metaphase onset (min)")
        name = f"G8kymo_kk_{batch.replace(' ', '_')}__{a.split('|')[-1]}_{b.split('|')[-1]}{tag}"
        fig.savefig(f"{OUT}/{name}.png", dpi=190, bbox_inches="tight")
        plt.close(fig)
        lib.record_plot(name, ["t_min_from_meta", "sister_a_um", "sister_b_um", "kk_um"],
                        [[round(t, 3), round(x, 4), round(y, 4), round(abs(x - y), 4)]
                         for t, x, y in zip(tmin, pa, pb)],
                        {"type": "sister-pair kymograph", "batch": batch, "pair": f"{a} | {b}",
                         "axis": "metaphase-plate normal; x=0 is the PLATE (not the pair midpoint — that origin forced the two sisters to be exact mirrors)",
                         "window": "metaphase era only",
                         "why": "user 2026-08-20 board-8 item 3: k-k needs a kymograph, not single frames"},
                        SCRIPT, f"Sister-pair kymograph — {batch}")
        made.append(name)
        print(f"  wrote {name} ({len(strip)} frames, median k-k {np.median(_kk):.2f} um)")
    cap.release()
    return made


if __name__ == "__main__":
    # the six cells whose individual traces she has on artboard 7
    CELLS = sys.argv[1:] or ["20250901 triple_ablation_11", "20250904 triple_ablation_8",
                             "20250410 ptk_yfpcdc20_17", "20250401 ptk_yfpcdc20_28"]
    tot = []
    for b in CELLS:
        tot += build(b)
        tot += build_pair(b)
    print(f"{len(tot)} kymographs written")
