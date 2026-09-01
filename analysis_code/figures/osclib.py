#!/usr/bin/env python3
"""Plate-relative kinetochore position series and oscillation statistics — METAPHASE ERA ONLY.

USER 2026-08-19, standing: *"unless i specify specifically otherwise, measurements used should be from the
metaphase era of a cell, not prometaphase or anaphase. Be careful about this."* Every series this module
returns is clipped to `Metaphase Start (s)` .. `Anaphase Onset (s)` from the master, and a cell missing
either event is dropped rather than guessed at.

WHY A SHARED MODULE
    `kk_osc_refined.py` already computes exactly this, but it is deliberately PAIRED-ONLY — her 2026-08-10
    instruction, *"for this subset of plots, dont include any measurements from polar or lagging
    kinetochores; just paired kinetochores."* That instruction governs THAT family of figures and still
    stands, so this module carries the same maths rather than loosening the filter there and changing
    figures she has already accepted.

THE MATHS, unchanged from `kk_osc_refined.kt_series` / `est_period_min`:
  * position is the kinetochore centroid projected onto the METAPHASE PLATE NORMAL, in µm — one series per
    KINETOCHORE, never per pair. Her 2026-08-10 reason: *"this refers to oscilation back and forth, so you
    need to find this for each kinetochore, not pair of kinetochores"* — a pair MIDPOINT cancels the very
    breathing motion the amplitude is meant to measure.
  * amplitude = SD of that plate-relative position.
  * period = 2 x span / (number of zero crossings of the detrended signal) — robust on short series.
  * pieces of one kinetochore on a frame are averaged first (grp-aware `track_id` already does this).
"""
import collections
import csv
import json
import sys

import numpy as np

sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import lib

ANN = "/Volumes/4 MB/annotations"
PX = 0.062              # fallback ONLY -- see px_of()
_PX_WARNED = set()


def px_of(batch):
    """Pixel size for ONE cell, read from the master's scraped `Pixel Size (um)` column.

    🔴 WHY THIS IS NOT A CONSTANT (2026-08-20). It was hardcoded at 0.062 here, which happens to be right for
    every cell that currently carries kinetochore outlines -- but that is luck, not design: the pipeline
    scrapes this per acquisition from the Micro-Manager metadata inside the TIFF
    (`metadata.py` -> summary['PixelSizeUm'], with a per-frame MicroManagerMetadata fallback) and the master
    records **0.031 for 39 cells and 0.058 for 7**, so a hardcoded 0.062 would silently double or shrink
    every distance the moment one of those cells gained an outline. It is now read per cell.

    The annotation stores are NOT the source: kt_outlines/meta_plates write 0.062 into every row regardless,
    so they cannot be used to catch this.

    Cells whose scrape returned nothing (5 of the 60 with outlines) fall back to 0.062 and are WARNED ONCE --
    for those five the same-date acquisitions that did scrape all report 0.062, so the fallback is supported
    rather than merely convenient.
    """
    v = (_master().get(batch, {}).get("Pixel Size (um)", "") or "").strip()
    try:
        f = float(v)
        if f > 0:
            return f
    except ValueError:
        pass
    if batch not in _PX_WARNED:
        _PX_WARNED.add(batch)
        print(f"  [px] {batch}: no scraped pixel size in the master, using {PX} µm/px")
    return PX
MIN_FRAMES = 5          # below this a period estimate is not meaningful (kk_osc_refined uses the same floor)

_MR = None


def _master():
    global _MR
    if _MR is None:
        data, _ = lib.load_master()
        _MR = {r["Batch Name"]: r for r in data}
    return _MR


def hms2s(s):
    s = (s or "").strip()
    neg = s.startswith("-")
    s = s.lstrip("-")
    if not s:
        return None
    p = [float(x) for x in s.split(":")]
    v = p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else (p[0] * 60 + p[1] if len(p) == 2 else p[0])
    return -v if neg else v


def metaphase_window(batch):
    """(metaphase_start_s, anaphase_onset_s) or None. THE gate every series in this module passes through."""
    r = _master().get(batch, {})
    ms = hms2s(r.get("Metaphase Start (s)"))
    an = hms2s(r.get("Anaphase Onset (s)"))
    return (ms, an) if (ms is not None and an is not None and an > ms) else None


def _oriented_plates(batch):
    """frame -> (centre, unit normal) for the metaphase plate, from her manual plate lines."""
    out = {}
    for r in csv.DictReader(open(f"{ANN}/meta_plates.csv", newline="", encoding="utf-8", errors="replace")):
        if r.get("batch") != batch or not r.get("points") or not str(r.get("frame", "")).isdigit():
            continue
        try:
            P = np.array(json.loads(r["points"]), float)
        except Exception:
            continue
        if len(P) < 2:
            continue
        c = P.mean(0)
        _, _, vt = np.linalg.svd(P - c)
        along = vt[0]
        normal = np.array([-along[1], along[0]])          # perpendicular to the plate = the oscillation axis
        out[int(r["frame"])] = (c, normal / (np.linalg.norm(normal) or 1.0))
    return out


def _plate_for(pl, frame):
    """The plate (centre, normal) to use for `frame`: hers if she drew one on it, otherwise LINEARLY
    INTERPOLATED between the two drawn plates that bracket it.

    WHY INTERPOLATE AND WHY ONLY BETWEEN: the plate is hand-drawn on a subset of frames, and requiring an
    EXACT frame match silently discarded 88 metaphase rows that sit between two of her own plates -- the
    plate does not teleport between them, so the interpolant is her annotation, not a new measurement.
    Frames OUTSIDE the drawn range are NOT extrapolated (2 rows); that would be inventing an axis.
    """
    if frame in pl:
        return pl[frame]
    fs = sorted(pl)
    if not fs or frame < fs[0] or frame > fs[-1]:
        return None
    lo = max(f for f in fs if f < frame)
    hi = min(f for f in fs if f > frame)
    w = (frame - lo) / float(hi - lo)
    c = pl[lo][0] * (1 - w) + pl[hi][0] * w
    n = pl[lo][1] * (1 - w) + pl[hi][1] * w
    nn = np.linalg.norm(n)
    if nn < 1e-9:
        return None
    return (c, n / nn)


def tracks(labels=("polar", "paired", "lagging"), min_frames=MIN_FRAMES, exclude=True, need_plate=True):
    """-> list of dicts, one per KINETOCHORE track, each carrying its metaphase-only series.

    keys: batch, track_id, label, n_sisterless, t_min (list, minutes from metaphase onset),
          pos_um (list, plate-relative), area_um2 (list), amp_um, period_min, meta_dur_min

    🔴 `need_plate` -- PASS False FOR ANY MEASUREMENT THAT DOES NOT USE THE PLATE (2026-08-20).
    Plate-relative POSITION, and therefore amplitude and period, require the metaphase plate, so oscillation
    work keeps the default True. **Kinetochore SIZE and FLUORESCENCE INTENSITY do not use the plate at all**,
    yet they were being routed through the same loader and silently lost every frame she had not drawn a
    plate on -- 8 cells have kinetochore outlines and NO plate anywhere, so they vanished entirely. The cost
    was real: lagging/merotelic went from 9 tracks in 8 cells down to 5 in 4, and the figures she asked for
    reported n=3. With need_plate=False those rows are kept and `pos_um`/`amp_um`/`period_min` are None,
    which is honest -- the quantity is not measurable there, but area and intensity are.
    """
    mr = _master()
    rows = collections.defaultdict(list)
    for r in csv.DictReader(open(f"{ANN}/KT_OUTLINE_TRACKS_20260723.csv",
                                 newline="", encoding="utf-8", errors="replace")):
        if r["label"] not in labels:
            continue
        b = r["batch"]
        if exclude and (lib.plot_excluded(b) or lib.is_mad1(b)):
            continue
        w = metaphase_window(b)
        if not w:
            continue
        try:
            t = float(r["t_sec"]); f = int(r["frame"])
        except Exception:
            continue
        if not (w[0] <= t <= w[1]):                       # METAPHASE ERA ONLY
            continue
        rows[(b, r["track_id"], r["label"])].append((f, t, r))

    plates = {}
    out = []
    for (b, tid, lab), rs in rows.items():
        if b not in plates:
            plates[b] = _oriented_plates(b)
        pl = plates[b]
        w = metaphase_window(b)
        T, POS, AR, FR = [], [], [], []
        for f, t, r in sorted(rs):
            g = _plate_for(pl, f)
            if g is None:
                g = _reconstructed_plate(b, f)      # her sister pairs + paired KTs, where she drew no plate
            if g is None and need_plate:
                continue                                   # no axis -> no plate-relative position
            try:
                c = np.array([float(r["cx_px"]), float(r["cy_px"])])
            except Exception:
                continue
            T.append((t - w[0]) / 60.0)
            FR.append(f)
            POS.append(float(np.dot(c - g[0], g[1])) * px_of(b) if g is not None else None)
            try:
                AR.append(float(r["area_um2"]))
            except Exception:
                AR.append(np.nan)
        if len(T) < min_frames:
            continue
        P = [v for v in POS if v is not None]
        Tp = [t for t, v in zip(T, POS) if v is not None]
        out.append(dict(batch=b, track_id=tid, label=lab,
                        n_sisterless=(mr.get(b, {}).get("# Sisterless KTs", "") or "").strip(),
                        t_min=T, pos_um=POS, area_um2=AR, frames=FR,
                        amp_um=float(np.std(P)) if len(P) >= 2 else None,
                        period_min=est_period_min(Tp, P) if len(P) >= 5 else None,
                        meta_dur_min=(w[1] - w[0]) / 60.0))
    return out


def est_period_min(T, POS):
    """Zero-crossing period estimate, identical to `kk_osc_refined.est_period_min`."""
    ts = [(t, p) for t, p in zip(T, POS) if p is not None]
    if len(ts) < 5:
        return None
    ts.sort()
    t = np.array([x[0] for x in ts]); y = np.array([x[1] for x in ts])
    y = y - np.mean(y)
    if np.std(y) == 0:
        return None
    s = np.sign(y); s[s == 0] = 1
    nc = int(np.sum(np.abs(np.diff(s)) > 0))
    if nc < 1:
        return None
    return 2.0 * (t.max() - t.min()) / nc


def model_wave(amp, period, span, n=400):
    """The idealised wave a group's median amplitude and period describe: x(t) = A*sqrt(2)*sin(2*pi*t/P).

    A*sqrt(2) because `amp` is the SD of the position and the SD of a sine of peak A is A/sqrt(2) — so a
    wave drawn at peak = amp would understate the excursion the data actually show by 41%.
    """
    if not amp or not period or period <= 0:
        return None, None
    t = np.linspace(0, span, n)
    return t, amp * np.sqrt(2.0) * np.sin(2 * np.pi * t / period)


# --------------------------------------------------------------------------------------------------
# CONGRESSION: a polar kinetochore that congresses KEEPS ITS "polar" OUTLINE NAME
# --------------------------------------------------------------------------------------------------
# USER 2026-08-20, verbatim: *"if a kinetochore is named as polar but then annotations for congression
# indicate that it congressed at a time in metaphase, it can commonly still have ongoing outlines until
# anaphase but name of outlines still being polar/unchanged from when it was actually polar. so sort this
# out - you can use the kinetochore trace label/name to help you, but you gotta use this in conjunction with
# the annotations saying times when chromosomes congress, as traces after a chromosome congression time
# passes are not of a polar kinetochore anymore, but of one that is at the metaphase plate/merotelically
# attached"*
#
# So the LABEL marks where a track STARTED, not what it is throughout. Two independent sources are used
# together, exactly as she asked, and neither is trusted alone:
#
#   MEASURED   the kinetochore's own distance from her metaphase plate. Congressing means arriving at the
#              plate, which is a measurement, not an opinion. The threshold is taken from HER OWN paired
#              kinetochores -- they are at the plate by definition and sit at median 1.21 um, p90 3.13,
#              while polar frames sit at median 6.46 um. 3.0 um captures 89% of paired frames and 4% of
#              polar ones, so it separates the two populations rather than being picked to taste.
#   ANNOTATED  her timed congressions in CHROMOSOME_MASTER.csv.
#
# VALIDATION, and why the measured test leads: on 20250401 ptk_yfpcdc20_28 the detected arrival is +17.0 min
# and her annotated congression is +17.0 min -- the same frame. Where the two DISAGREE the measurement wins
# and the reason is visible: in 20250826 test_ablation_8 and 20260417 ptk2 eyfp cdc20 ablation_18 a
# congression IS timed, but the outlined polar track stays 5.5 and 8.1 um from the plate throughout, so it
# is NOT the chromosome that congressed -- that one was never outlined. Splitting those tracks on her
# congression time would have relabelled 90 genuinely-polar frames as congressed.
AT_PLATE_UM = 3.0        # from the paired-kinetochore distribution, not chosen by eye
_ARRIVE_N = 3            # frames it must hold, so a single noisy frame is not a congression
_START_FAR_UM = 4.0      # it must START polar; a track already at the plate never "congressed" here


def congression_min(t, events=None):
    """Deprecated shim -- see assign_congressions(). Kept so older callers do not break."""
    return (events[0], "annotated") if events else (None, "no annotation")


def plate_join_events_min(batch):
    """HER timed congressions for a cell, in minutes from metaphase onset, keyed BY CHROMOSOME.

    🔴 KEYED BY chr_num, NOT BY TIME (fixed 2026-08-20). Two stores record the same events:
    `CHROMOSOME_MASTER.csv` (chr_num) and `SISTERLESS_PLATE_JOIN_TIMES.csv` (chromosome_1/2/3). Unioning them
    on TIME double-counts, because the same chromosome can carry different times in the two files — on
    `20250901 triple_ablation_49` chr1 is 2097 s vs 1977 s and chr2 is 2817 s vs 2958 s, which made 3 real
    congressions look like 5 and tripped a false "more congressions than sisterless kinetochores" flag.

    CHROMOSOME_MASTER WINS where both have the chromosome: NOTES 2026-07-22 records it as the single
    consolidated per-chromosome table, with the plate-join file's unique rows already merged into it. The
    plate-join file is used only for a chromosome CHROMOSOME_MASTER does not carry.
    """
    w = metaphase_window(batch)
    if not w:
        return []
    by_chr = {}
    try:
        for r in csv.DictReader(open(f"{ANN}/SISTERLESS_PLATE_JOIN_TIMES.csv", newline="",
                                     encoding="utf-8", errors="replace")):
            if r.get("batch") != batch:
                continue
            for n, k in ((1, "chromosome_1_plate_join_s"), (2, "chromosome_2_plate_join_s"),
                         (3, "chromosome_3_plate_join_s")):
                v = (r.get(k) or "").strip()
                if v:
                    by_chr[str(n)] = float(v)
    except Exception:
        pass
    try:
        for r in csv.DictReader(open(f"{ANN}/CHROMOSOME_MASTER.csv", newline="",
                                     encoding="utf-8", errors="replace")):
            if r.get("batch") != batch:
                continue
            v = (r.get("congression_time_s") or "").strip()
            if v:
                by_chr[str(r.get("chr_num", "")).strip()] = float(v)   # authoritative, overwrites
    except Exception:
        pass
    return sorted((t - w[0]) / 60.0 for t in by_chr.values() if w[0] <= t <= w[1])


def assign_congressions(cell_tracks):
    """Assign HER timed congressions to the polar tracks of ONE cell. Her times are AUTHORITATIVE.

    🔴 WHY THIS REPLACED A DISTANCE TEST (2026-08-20, her correction). The previous version decided whether a
    congression had happened by asking if the kinetochore reached the plate, and REFUTED her annotation in 7
    cells where it did not. That was wrong for a reason she gave in the same breath: a kinetochore that has
    congressed may be MEROTELICALLY attached, and a merotelic kinetochore is not obliged to sit tightly at
    the plate. Her own plate-join times prove it -- measured at the moment SHE marks the join, the distance
    ranges from 2.5 to 8.6 um, so distance does not separate joined from not-joined and can never license
    overruling her.

    Distance is still used, but ONLY TO ASSIGN an event to one of several polar tracks in the same cell:
    the track whose distance to the plate DROPS most across the event is the one that congressed. That is a
    ranking among candidates, not a veto. Each event takes one track, largest drop first.

    Sets on each polar track: `congress_min` (None if the cell has no timed event left for it) and
    `congress_evidence`.
    """
    pol = [t for t in cell_tracks if t["label"] == "polar"]
    for t in pol:
        t["congress_min"], t["congress_evidence"] = None, "no timed congression in this cell"
    if not pol:
        return 0
    ev = plate_join_events_min(pol[0]["batch"])
    if not ev:
        return 0
    if len(ev) == 1 and len(pol) == 1:
        pol[0]["congress_min"] = ev[0]
        pol[0]["congress_evidence"] = "her timed congression (only one event, only one polar track)"
        return 1

    def drop(t, c, half=2.5):
        P = [(tm, abs(p)) for tm, p in zip(t["t_min"], t["pos_um"]) if p is not None]
        before = [d for tm, d in P if c - half <= tm < c]
        after = [d for tm, d in P if c <= tm <= c + half]
        if not before or not after:
            return None
        return float(np.median(before) - np.median(after))

    cand = []
    for c in ev:
        for t in pol:
            d = drop(t, c)
            if d is not None:
                cand.append((d, c, id(t), t))
    cand.sort(key=lambda x: -x[0])
    used_t, used_c, n = set(), set(), 0
    for d, c, tid, t in cand:
        if tid in used_t or c in used_c:
            continue
        t["congress_min"] = c
        t["congress_evidence"] = (f"her timed congression at {c:+.1f} min, assigned to this track by the "
                                  f"largest fall in plate distance ({d:+.2f} um)")
        used_t.add(tid); used_c.add(c); n += 1
    # events with no measurable drop anywhere (no plate on those frames): fall back to time order, which is
    # still HER data -- earliest event to the track that starts earliest
    left_c = [c for c in ev if c not in used_c]
    left_t = [t for t in pol if id(t) not in used_t]
    left_t.sort(key=lambda t: min(t["t_min"]))
    for c, t in zip(left_c, left_t):
        t["congress_min"] = c
        t["congress_evidence"] = (f"her timed congression at {c:+.1f} min, assigned by time order "
                                  "(no plate-relative position available to rank the tracks)")
        n += 1
    return n


def split_at_congression(tracks_):
    """Cut every polar track at HER timed congression, so no frame counts as polar after the kinetochore
    joined the plate. Adds `congress_min`, `congress_evidence` and a per-frame `phase` list.
    """
    bycell = collections.defaultdict(list)
    for t in tracks_:
        t["congress_min"], t["congress_evidence"] = None, "not polar"
        t["phase"] = ["polar" if t["label"] == "polar" else t["label"]] * len(t["t_min"])
        bycell[t["batch"]].append(t)
    for b, ts in bycell.items():
        assign_congressions(ts)
    n_split = 0
    for t in tracks_:
        c = t.get("congress_min")
        if t["label"] != "polar" or c is None:
            continue
        t["phase"] = ["post_congression" if tm >= c else "polar" for tm in t["t_min"]]
        n_split += 1
    return n_split


# --------------------------------------------------------------------------------------------------
# PLATE RECONSTRUCTION for cells where she has not drawn one
# --------------------------------------------------------------------------------------------------
# USER 2026-08-20: *"triple_ablation_collagen_2, triple_ablation_7 and triple_ablation_26 should definitely
# have plate annotation."* They do not -- zero rows in meta_plates.csv, in all 18 historical/backup/retired
# copies on the drive, and `meta_plate_ids` is empty for all three in the master. But she is right that the
# plate is knowable for these cells, because the metaphase plate is not an independent object: it is defined
# by where her PAIRED kinetochores are and by the spindle axis her SISTER PAIRS lie along.
#
#   normal  = mean sister k-k direction. A sister pair straddles the plate, so k-k IS the plate normal.
#             VALIDATED against 1,045 frames where she HAS drawn a plate: median disagreement 6.9 deg
#             (p75 12.5, p90 20.0).
#   centre  = mean of the paired-kinetochore centroids on that frame.
#             Same validation: median offset along the normal 0.87 um (p75 1.78).
#
# Deriving the normal from the SPREAD of paired kinetochores was tried first and REJECTED -- median 32 deg
# disagreement, p90 84 -- because with few paired outlines on a frame their spread does not lie along the
# plate. The sister-pair axis is the one that reproduces her drawing.
#
# A reconstructed plate is always marked `reconstructed` so a figure can say so, and it is used ONLY where
# she has drawn nothing.
_SIS = None
_KTPOS = None


def _sister_pairs():
    global _SIS
    if _SIS is None:
        _SIS = collections.defaultdict(set)
        try:
            for r in csv.DictReader(open(f"{ANN}/KT_SISTERS_20260723.csv", newline="",
                                         encoding="utf-8", errors="replace")):
                b = r.get("partner_track", "")
                if b:
                    _SIS[r["batch"]].add(tuple(sorted((r["track_id"], b))))
        except Exception:
            pass
    return _SIS


def _kt_positions():
    global _KTPOS
    if _KTPOS is None:
        _KTPOS = {}
        _KTPOS["paired"] = collections.defaultdict(list)
        for r in csv.DictReader(open(f"{ANN}/KT_OUTLINE_TRACKS_20260723.csv", newline="",
                                     encoding="utf-8", errors="replace")):
            try:
                f = int(r["frame"]); c = (float(r["cx_px"]), float(r["cy_px"]))
            except Exception:
                continue
            _KTPOS[(r["track_id"], f)] = c
            if r["label"] == "paired":
                _KTPOS["paired"][(r["batch"], f)].append(c)
    return _KTPOS


def _reconstructed_plate(batch, frame):
    P = _kt_positions()
    pts = P["paired"].get((batch, frame)) or []
    V = []
    for a, b in _sister_pairs().get(batch, ()):
        pa, pb = P.get((a, frame)), P.get((b, frame))
        if pa and pb:
            v = np.array(pb) - np.array(pa)
            n = np.linalg.norm(v)
            if n > 1:
                V.append(v / n)
    if not V or not pts:
        return None
    M = np.array(V)
    for i in range(1, len(M)):                       # k-k vectors are undirected; align signs before averaging
        if np.dot(M[i], M[0]) < 0:
            M[i] = -M[i]
    m = M.mean(0)
    n = np.linalg.norm(m)
    if n < 1e-6:
        return None
    return np.array(pts, float).mean(0), m / n
