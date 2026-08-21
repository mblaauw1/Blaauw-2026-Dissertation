"""Shared data extraction + journal style for the ablation figure set."""
import csv, re, os
import numpy as np

MASTER="/Volumes/4 MB/ABLATION_MASTER.csv"
ANN="/Volumes/4 MB/annotations"
REVIEW=[]  # (metric, batch, value, reason)

def log_review(metric,batch,value,reason):
    REVIEW.append((metric,str(batch),str(value),reason))

def flush_review(path):
    import csv as _c
    with open(path,"w",newline="") as f:
        w=_c.writer(f); w.writerow(["metric","batch","value","reason"]); w.writerows(REVIEW)


# --- REUSABLE outlier-zoom companion support (FIX_PLAN 12c) ---------------------------------------
# Many plots have a handful of extreme points that stretch the y-axis so far that the BULK of the data
# is crushed into a thin band (see the FRAP / ablation-intensity spikes). zoom_trim() finds those points
# with a robust IQR fence and returns axis limits that fit the bulk PLUS the mask of trimmed points, so a
# caller can (a) draw the trimmed points as hollow "clipped" markers at the axis edge (the missing-point
# convention) and (b) log each one to the review list. These are COMPANION-ONLY readability trims: they do
# NOT propagate to v1 or any other figure (distinct from the user's definitive remove-everywhere points).
def zoom_trim(vals, k=3.0, floor_zero=None, min_distortion=1.35, pad=0.06, min_waste_frac=0.20):
    """Robust outlier fence for the 1-D array of PLOTTED y-values.
    Returns dict with:
      distorting : True only when trimming the outliers shrinks the data span by >= (min_distortion-1),
                   i.e. the outliers really do stretch the axis (otherwise no companion is warranted).
      lo, hi     : new axis limits fitting the bulk (hi below the outliers; lo=0 if data is floored at 0).
      out_mask   : bool array, True where a value is a trimmed outlier (outside q3+k*IQR / q1-k*IQR).
      fence_lo/hi, n, n_out, p50, p95, vmin, vmax : diagnostics.
    """
    import numpy as _np
    v=_np.asarray(vals,dtype=float); fin=_np.isfinite(v)
    out=_np.zeros(v.shape,dtype=bool)
    res={"distorting":False,"lo":None,"hi":None,"out_mask":out,"fence_lo":None,"fence_hi":None,
         "n":int(fin.sum()),"n_out":0,"p50":None,"p95":None,"vmax":None,"vmin":None}
    vv=v[fin]
    if vv.size<6: return res
    q1,q3=_np.percentile(vv,[25,75]); iqr=q3-q1
    res.update(p50=float(_np.median(vv)),p95=float(_np.percentile(vv,95)),
               vmin=float(vv.min()),vmax=float(vv.max()))
    if iqr<=0: return res
    fhi=q3+k*iqr; flo=q1-k*iqr
    res["fence_hi"]=fhi; res["fence_lo"]=flo
    omask=((v>fhi)|(v<flo))&fin
    if not omask.any(): return res
    bulk=vv[(vv<=fhi)&(vv>=flo)]
    if bulk.size<3: return res
    bmin=float(bulk.min()); bmax=float(bulk.max())
    data_range=res["vmax"]-res["vmin"]; bulk_range=bmax-bmin
    if bulk_range<=0 or data_range/bulk_range < min_distortion: return res
    span=bmax-bmin
    lo=bmin-pad*span; hi=bmax+pad*span
    fz = floor_zero if floor_zero is not None else (res["vmin"]>=0 and bmin<=0.15*span)
    if fz: lo=0.0
    # WASTE guard: the outliers must waste a meaningful slice of the plotted axis, else zooming is pointless
    # (e.g. a bounded metric near its ceiling). Require the trimmed tail >= min_waste_frac of the bulk band.
    if (hi-lo)<=0 or (res["vmax"]-hi) < min_waste_frac*(hi-lo): return res
    res.update(distorting=True,lo=lo,hi=hi,out_mask=omask,n_out=int(omask.sum()))
    return res


def omitted_y(x, xs_kept, ys_kept, lo=None, hi=None):
    """y-position for a hollow 'omitted/missing point' marker: the value of the trend AT the point's own x,
    interpolated from the RETAINED (kept) points sorted by x — i.e. np.interp(x, xs_kept_sorted, ys_kept_sorted).
    This places the hollow marker ON the line/trend at its true x, NEVER pinned to the top/bottom axis frame and
    NEVER at its literal off-scale value. [lo,hi] (the axis limits) are applied ONLY as a final safety clamp.
    Degenerate cases: 1 kept point -> that point's y; 0 kept points -> hi (or x) as a last resort."""
    import numpy as _np
    xs=_np.asarray(xs_kept,dtype=float); ys=_np.asarray(ys_kept,dtype=float)
    m=_np.isfinite(xs)&_np.isfinite(ys); xs,ys=xs[m],ys[m]
    if xs.size==0:
        y=float(hi) if hi is not None else float(x)
    elif xs.size==1:
        y=float(ys[0])
    else:
        o=_np.argsort(xs); y=float(_np.interp(float(x),xs[o],ys[o]))
    if lo is not None: y=max(y,float(lo))
    if hi is not None: y=min(y,float(hi))
    return y


# --- SHARED user-flagged oscillation-outlier exclusion (IN ADDITION to the >8µm OSC_HI glitch cap) ------------
# Explicit per-POINT removals of individual per-20s displacement steps the user identified as tracking artifacts.
# Keyed by (batch, t_min_from_metaphase). The underlying step time is stored in seconds/frames, so match on the
# NEAREST timepoint within OSC_POINT_TOL minutes. EVERY builder that constructs per-step polar displacement must
# consult osc_point_excluded() so a removed point disappears from ALL derived figures (chronological line plot,
# the oscillation violins G4_oscillation / G4_oscillation_tracking, and the effective/total companions).
OSC_POINT_EXCLUDE = {
    ("20250901 triple_ablation_11", 25.6),   # light-blue spike, 4.21 µm/20s
    ("20250409 ptk_yfpcdc20_6",     10.5),   # brown spike, 2.50 µm/20s
}
OSC_POINT_TOL = 0.1   # minutes (=6s). Step midpoints are ~20s (0.33 min) apart, so a tolerance well under half
                      # that spacing matches ONLY the flagged step (actual offsets from the given times are ≤0.02 min)
                      # without catching its immediate neighbours.

def osc_point_excluded(batch, t_min):
    """True if this per-step polar displacement point is a user-flagged oscillation outlier
    (same batch + timepoint within OSC_POINT_TOL minutes of an OSC_POINT_EXCLUDE entry)."""
    for _b, _tm in OSC_POINT_EXCLUDE:
        if _b == batch and abs(float(t_min) - _tm) <= OSC_POINT_TOL:
            return True
    return False


_MISPLACED_IDS=None
def misplaced_ids():
    """IDs of intact-KT annotations with NO kinetochore within 9px (from screen_kt_placement.py) —
    excluded from analysis until fixed. File: annotations/MISPLACED_KT_IDS.txt."""
    global _MISPLACED_IDS
    if _MISPLACED_IDS is None:
        _MISPLACED_IDS=set()
        p="/Volumes/4 MB/annotations/MISPLACED_KT_IDS.txt"
        if os.path.isfile(p):
            for ln in open(p):
                ln=ln.strip()
                if ln: _MISPLACED_IDS.add(ln)
    return _MISPLACED_IDS
def is_misplaced_id(i):
    return str(i).strip() in misplaced_ids()

# ---- KINETOCHORE IDENTITY for manual kt_points marks (USER 2026-08-04) --------------------------
# Standing rule: the "+ New KT" group IS the kinetochore — polar/lagging marks must NEVER be merged
# across kinetochores. The builders used to key marks by BATCH alone, so a triple-sisterless cell drew
# ONE trace zig-zagging between up to 6 different kinetochores, and every "displacement" was really a
# KT-to-KT gap. The identity is in the data but implicit, and written in TWO marking modes:
#   * KT-major    — one KT marked through many frames as a run of ids, then the next KT (frame resets)
#   * frame-major — every KT marked on frame 1, then every KT on frame 2 ... (ids cycle A,B,C,A,B,C)
# No id arithmetic splits both. What holds in both is that one kinetochore is spatially continuous
# frame to frame while different kinetochores sit far apart — so link by nearest neighbour across
# frames, exactly how the `paired` outlines were linked into KT_OUTLINE_TRACKS.
# Validated 2026-08-04: p90 per-20s step falls 6.72 -> 1.02 µm, and is INSENSITIVE to the two
# parameters over 2-6 µm / 6-25 frames (so this is not a tuned result). Against the master's
# '# Sisterless KTs': 40 cells agree, 5 find more, 19 find fewer — "fewer" is expected, not every
# ablated KT gets marked.
KT_LINK_MAX_STEP_UM = 4.0     # a KT may move this far between consecutive MARKED frames (scaled by gap)
KT_LINK_MAX_GAP_FR  = 25      # a track survives this many frames unseen before it is closed

def stabilize_axis_angles(seq, aspect=None, jump=45.0):
    """Temporal continuity for a track's ORIENTATION series (USER 2026-08-05).

    `angle_deg` is the direction of the MAX CALIPER — the longest chord of the outline. On a roundish or
    multi-piece kinetochore two chords can be nearly equally long, so the reported direction jumps ~90 deg
    between frames while the object barely moves. (Note this is NOT principal-axis major/minor swapping:
    the caliper axes are not orthogonal. Same symptom, different cause.)

    Her fix, applied to EVERY frame rather than only the obvious jumps: seed the orientation where the
    kinetochore is most clearly elongated -- there the longest chord is unambiguous -- then walk outward in
    both directions and, at each frame, choose between the reported angle and its +90 deg alternative
    whichever continues the running orientation. Angles are axes, so everything is mod 180.

    seq    : [(frame, angle_deg), ...] for ONE track, any order
    aspect : optional [aspect_ratio, ...] parallel to seq; the seed is the highest-aspect frame
    jump   : how far (deg) the running reference may move before the +90 reading is preferred
    returns [(frame, corrected_angle_deg, was_corrected), ...] sorted by frame
    """
    import math
    if not seq: return []
    order = sorted(range(len(seq)), key=lambda i: seq[i][0])
    fr = [seq[i][0] for i in order]; an = [seq[i][1] % 180.0 for i in order]
    asp = [aspect[order.index(i)] if aspect else 1.0 for i in range(len(order))] if aspect else [1.0]*len(an)
    seed = max(range(len(an)), key=lambda i: asp[i]) if aspect else 0
    out = [None]*len(an); out[seed] = (an[seed], False)
    def _pick(a, ref):
        best, corrected = a, False
        for cand, flag in ((a, False), ((a + 90.0) % 180.0, True)):
            d = abs((cand - ref + 90.0) % 180.0 - 90.0)
            if d < abs((best - ref + 90.0) % 180.0 - 90.0): best, corrected = cand, flag
        return best, corrected
    ref = an[seed]
    for i in range(seed + 1, len(an)):                     # forward
        v, c = _pick(an[i], ref); out[i] = (v, c); ref = v
    ref = an[seed]
    for i in range(seed - 1, -1, -1):                      # backward
        v, c = _pick(an[i], ref); out[i] = (v, c); ref = v
    return [(fr[i], out[i][0], out[i][1]) for i in range(len(an))]


def assign_tracks_to_chromosomes(tracks, chrom_rows):
    """Which traced kinetochore is which annotated chromosome?

    USER 2026-08-05: "you shouldnt be deciding if a chromosome has congressed or should be called
    congressed or not because ive gone through and specified all of that per-chromosome already (even
    giving the time it congresses if it does)".

    She is right, and an earlier version of this function was wrong for exactly that reason: it scored
    each track on whether it LOOKED congressed (did the distance-to-plate drop far enough) and refused to
    match a row when the track disagreed. That re-decides an annotation she has already made, and it made
    the assignment depend on my threshold rather than on her data.

    This function now decides NOTHING about behaviour. Behaviour comes from the annotation, always. The
    only job here is IDENTITY — which of a cell's tracks is which of its chromosomes — and the only
    evidence used is her own `congression_time_s`:

      * a row that HAS a congression time is matched to the track that completes its approach nearest to
        that time. Her time is the key; the track supplies only the timing to compare against.
      * rows with no time (noncongression, at_plate) take the remaining tracks BY ELIMINATION.
      * if elimination is genuinely ambiguous — two or more untimed rows left that DISAGREE on behaviour,
        so which track gets which would be a coin flip — those tracks are returned unmatched rather than
        assigned a label they might not have. Untimed rows that all share one behaviour are not ambiguous,
        because every possible assignment gives the same answer.

    tracks     : [{"t": [t_sec...], "d": [dist_to_plate_um...]}, ...] one entry per linked kinetochore
    chrom_rows : [{"behavior": ..., "congression_time_s": ..., "chr_num": ...}, ...]
    Returns a list parallel to `tracks`, each entry the matched row or None.
    """
    import numpy as _np
    if not tracks or not chrom_rows: return [None] * len(tracks)

    def arrival(t):
        """When this track completes most of its approach to the plate — a timing to compare against her
        recorded congression time. NOT a judgement about whether it congressed."""
        d = _np.asarray(t["d"], float); ts = _np.asarray(t["t"], float)
        if d.size < 3: return None
        k = max(1, len(d) // 4)
        d0 = float(_np.median(d[:k])); dmin = float(_np.min(d))
        if d0 <= dmin: return None
        thr = d0 - 0.7 * (d0 - dmin)
        hit = d <= thr
        return float(ts[_np.argmax(hit)]) if hit.any() else None

    arr = [arrival(t) for t in tracks]

    def ctime(row):
        try: return float(str(row.get("congression_time_s") or "").strip())
        except Exception: return None

    timed = [j for j, r in enumerate(chrom_rows) if ctime(r) is not None]
    untimed = [j for j, r in enumerate(chrom_rows) if ctime(r) is None]
    NEUTRAL = 1e3          # untimed rows are all equally good: assignment falls to elimination

    C = _np.full((len(tracks), len(chrom_rows)), NEUTRAL, float)
    for i, a_ in enumerate(arr):
        for j in timed:
            C[i][j] = abs(a_ - ctime(chrom_rows[j])) / 60.0 if a_ is not None else NEUTRAL * 2
    try:
        from scipy.optimize import linear_sum_assignment
        ri, ci = linear_sum_assignment(C)
    except Exception:
        ri, ci, used = [], [], set()
        for i in _np.argsort(C.min(axis=1)):
            j = int(_np.argmin([C[i][k] if k not in used else _np.inf for k in range(C.shape[1])]))
            ri.append(i); ci.append(j); used.add(j)

    # is elimination ambiguous? only when the untimed rows disagree with each other
    ambiguous = len({(str(chrom_rows[j].get("behavior") or "")).strip().lower() for j in untimed}) > 1

    out = [None] * len(tracks)
    for i, j in zip(ri, ci):
        if j in untimed and ambiguous:
            continue                      # would be a coin flip — say nothing rather than guess
        if j in timed and arr[i] is None:
            continue                      # nothing to match her time against
        out[i] = chrom_rows[j]
    return out


def link_kt_tracks(marks, px_um, max_step_um=KT_LINK_MAX_STEP_UM, max_gap_fr=KT_LINK_MAX_GAP_FR):
    """marks: [(frame, t_sec, x_px, y_px, ...)] for ONE label in ONE batch -> [[mark,...], ...], one
    list per kinetochore, each sorted in time. Extra tuple fields are carried through untouched.

    Greedy nearest-neighbour: each open track takes at most one mark per frame and each mark joins at
    most one track, closest admissible pair first; unmatched marks open new tracks."""
    import math
    from collections import defaultdict as _dd
    by_fr = _dd(list)
    for m in marks: by_fr[int(m[0])].append(m)
    tracks = []
    for fr in sorted(by_fr):
        cand = by_fr[fr]
        open_tr = [t for t in tracks if fr - t["last_fr"] <= max_gap_fr]
        pairs = []
        for ti, t in enumerate(open_tr):
            for mi, m in enumerate(cand):
                gap = max(1, fr - t["last_fr"])
                d = math.hypot(m[2]-t["xy"][0], m[3]-t["xy"][1]) * px_um
                if d <= max_step_um * gap: pairs.append((d, ti, mi))
        pairs.sort()
        used_t, used_m = set(), set()
        for d, ti, mi in pairs:
            if ti in used_t or mi in used_m: continue
            t = open_tr[ti]; m = cand[mi]
            t["pts"].append(m); t["last_fr"] = fr; t["xy"] = (m[2], m[3])
            used_t.add(ti); used_m.add(mi)
        for mi, m in enumerate(cand):
            if mi in used_m: continue
            tracks.append({"pts": [m], "last_fr": fr, "xy": (m[2], m[3])})
    return [sorted(t["pts"], key=lambda z: z[0]) for t in tracks]

def mark_retired(fig, label="RETIRED"):
    """Stamp a large, semi-transparent red diagonal 'RETIRED' watermark across the whole figure.
    USER 2026-07-16: plots that still use the ANTIQUED (v1 / raw-phase) prophase-vs-prometaphase binning are
    KEPT but marked RETIRED so it's unambiguous they are not the v2-binned current version. Draw AFTER all
    axes/artists so it sits on top."""
    fig.text(0.5, 0.5, label, transform=fig.transFigure, fontsize=90, color="#bb0000",
             alpha=0.32, ha="center", va="center", rotation=30, rotation_mode="anchor",
             fontweight="bold", zorder=10000)

def robust_keep(*arrays, k=4.0, min_n=12, verbose_name=None):
    """Boolean KEEP mask over one or more parallel arrays, dropping points that are extreme on ANY of them.

    USER 2026-07-27: "when there are outliers like this, do not plot them so the plot can achieve the correct
    fit" — a handful of very large speeds / areas were setting the axis range and dragging every trendline.
    Rule: keep |x - median| <= k * 1.4826 * MAD (k=4, i.e. ~4 robust SD), which is scale-free and does not
    assume normality. Falls back to keeping everything when the sample is too small to estimate a scale.
    Anything dropped is printed, never silently discarded."""
    arrs = [np.asarray(a, float) for a in arrays]
    keep = np.ones(len(arrs[0]), bool)
    for a in arrs:
        keep &= np.isfinite(a)
    if keep.sum() < min_n:
        return keep
    for a in arrs:
        med = np.median(a[keep])
        mad = np.median(np.abs(a[keep] - med)) * 1.4826
        if mad <= 0:
            continue
        keep &= np.abs(a - med) <= k * mad
    n_drop = int(np.isfinite(arrs[0]).sum() - keep.sum())
    if n_drop and verbose_name:
        print(f"      {verbose_name}: dropped {n_drop} outlier point(s) of "
              f"{int(np.isfinite(arrs[0]).sum())} (>{k} robust SD)")
    return keep


_CELL_TYPE_MAD1 = None
def is_mad1(batch):
    """eYFP-Mad1 cells — a SEPARATE experiment (reserved for Group 5 / Section 5). Exclude from all
    Group 1-4 (eYFP-Cdc20) plots, even though some Mad1 batches now carry annotations.

    USER 2026-08-03 (feedback item 28 / 2026-07-30 review item 28: "G5_mad1_timestrip_...Eyfpcdc2_
    ablation_1metaphase_52 ... are showing cdc20 cells, not mad1"): this used to be a naive substring
    check on the BATCH NAME (`"mad1" in batch.lower()`). Confirmed wrong in BOTH directions against the
    master `Cell Type` column (independently populated at acquisition, not parsed from the batch name):
      - 73 batches from the 20260303 "Mad1_Ptk_..." session are named with a "Mad1_Ptk_" SESSION-FOLDER
        prefix but are themselves "Eyfpcdc2" (cdc20) cells imaged in the same session
        (`20260303 Mad1_Ptk_Eyfpcdc2_ablation_1metaphase_*`) -> Cell Type = "eYFP cdc20" for every one of
        them. The substring check pulled all 73 into every Mad1 measurement (e.g. kt_mad1_plots.py's
        `mad = [o for o in objs if lib.is_mad1(o["batch"])]`) and, the other way, silently dropped them
        from every cdc20 group1-4 plot via the is_mad1() guards used there.
      - 9 batches ("ptk_hek19aplasmid_*", "ptk eyfp mad 1 640 halotag hec1_*" -- note the SPACE in
        "mad 1") are genuinely Mad1 (Cell Type "hec1-halo + eYFP mad1") but the substring never matched
        "mad 1" (space) or "hek19aplasmid" -> they were silently left OUT of every Mad1 measurement and
        IN the cdc20 pool.
    `20260310 ptk2_eyfp_mad1_14` was ALSO flagged in the same feedback but Cell Type says "eYFP mad1" and
    her own annotation Notes describe literal Mad1-localization dynamics ("targeted chromosome remains at
    pole with mad1 localization... until anaphase") -- the 2026-07-30 review already asked her to confirm
    this one specifically and she has not yet answered (see NOTES.md / _reviews_and_reference/_review_20260730 item 28). Left
    classified as Mad1 here pending that confirmation; do not silently flip it without evidence.
    FIX: use the master `Cell Type` column as the source of truth; fall back to the old name-substring
    heuristic ONLY for a batch with no master row, so a brand-new unregistered batch doesn't silently
    vanish from every guard before it's been entered."""
    global _CELL_TYPE_MAD1
    if _CELL_TYPE_MAD1 is None:
        d, _ = load_master()
        _CELL_TYPE_MAD1 = {r["Batch Name"]: ("mad1" in (r.get("Cell Type", "") or "").lower()) for r in d}
    if batch in _CELL_TYPE_MAD1:
        return _CELL_TYPE_MAD1[batch]
    return "mad1" in (batch or "").lower()

def is_drug(batch):
    """ZM, colcemid, low-dose nocodazole, or MUGs treated — excluded from off-target/untreated control pool.
    (colcem added 2026-07-14: colcemid cells were mislabeled 'Unmodified' + leaked into the unModified baseline
    cohort with 200+min colcemid-arrest durations. Exhaustion/slippage plots select colcemid BY NAME, so this
    exclusion does not affect them.)"""
    b=batch.lower()
    return bool(re.search(r'zm_ablation|zm_|colcem|low dose noc|nocod|mugs?|washout', b))

# GLOBAL review-exclusions: batches the user flagged as outliers to pull from ALL plots/violins (added to the
# review list, NOT deleted from the master). Respected by assign_cohorts() and any plot that calls excluded().
REVIEW_EXCLUDE={
    "20260107 two_sisterless_kinetochores_5",  # 07-07 feedback: on-target 2-sisterless meta->ana ~79min outlier
    # 07-22 feedback: paired POLAR kinetochore pair congresses only a few min before anaphase, then one of the pair
    # becomes lagging -> artificially very late metaphase start. Kept in the master + flagged as a paired-polar
    # example (Polar Comments) so it can be pulled back in deliberately; excluded from every plot by default.
    "20251029 triple_ablation_12",
}
def excluded(batch):
    return batch in REVIEW_EXCLUDE

# KT-OUTLINE analysis exclusions: batches pulled from ALL kt_outlines-derived analysis (shape, tracks,
# landmark, chromo, sisters, tension, and every plot built on them). User 2026-07-23. Applied at the raw
# kt_outlines readers (kt_shape_metrics.load_shapes + kt_tracks.build_objects) so it propagates to every
# derived CSV and plot. Logged in the review doc.
KT_OUTLINE_EXCLUDE={
    # USER 2026-08-09: "leave this one out of the plots". Its outlines are mislabelled/incomplete
    # (the touching sister pair is stored as `polar`, the lone distant KT as `paired`, and no trace
    # carries a grp), so it cannot be tracked or paired reliably. Excluded from every kt-outline figure.
    "20250402 ptk_yfpcdc20_7",
    "20260303 Mad1_Ptk_Eyfpmad1_ablation_10",  # user 2026-07-23: remove from all kt-outline analysis
}
# COHORT SWITCH (user 2026-07-27): the kt-outline deck is the eYFP-Cdc20 experiment; the Mad1 cells are a
# SEPARATE experiment and must be plotted on their own. Default run = cdc20 (every mad1 batch dropped);
# set KT_COHORT=mad1 in the environment to invert it and analyse ONLY the Mad1 cells.
KT_COHORT = (os.environ.get("KT_COHORT") or "cdc20").strip().lower()
# OUT-OF-FOCUS FRAMES (user 2026-07-27): a polar kinetochore that drifts out of the focal plane shows up as
# a sudden dim, small outline -- a focus artifact, not a real shape change, and it was distorting 471 and the
# rest. polar_focus_check.py measures every outline's background-subtracted brightness and flags the frames
# that fall far below their own track's level; she approved dropping them. Applied at the raw kt_outlines
# readers, so every derived CSV and figure loses them together. Keyed on the outline ROW ID.
_FOCUS_EXCLUDE = None
def focus_excluded(row_id):
    global _FOCUS_EXCLUDE
    if _FOCUS_EXCLUDE is None:
        _FOCUS_EXCLUDE = set()
        try:
            import csv as _csv
            with open("/Volumes/4 MB/annotations/POLAR_FOCUS_CHECK_20260727.csv", newline="") as f:
                for r in _csv.DictReader(f):
                    if (r.get("suspect_out_of_focus") or "").strip().lower() == "yes":
                        _FOCUS_EXCLUDE.add(str(r["id"]).strip())
        except Exception:
            pass
    return str(row_id).strip() in _FOCUS_EXCLUDE


def kt_outline_excluded(batch):
    if batch in KT_OUTLINE_EXCLUDE:
        return True
    return is_mad1(batch) if KT_COHORT == "cdc20" else not is_mad1(batch)

_FOUR_SIS=None
_V2_PROMETA_SET=None
def is_v2_prometaphase(batch):
    """True if the batch carries the Notes marker 'v2=prometaphase'. USER RULE (2026-07-16): v2 binning is the
    STANDARD for every phase-split plot — a v2=prometaphase-flagged cell (Phase of Ablations may say prophase) is
    binned PROMETAPHASE. Builders apply this in their phase classifier: if phase=='Prophase' and this returns
    True -> 'Prometaphase'; prophase-only plots exclude these cells."""
    global _V2_PROMETA_SET
    if _V2_PROMETA_SET is None:
        import re as _re; d,_=load_master()
        _V2_PROMETA_SET={r["Batch Name"] for r in d if _re.search(r'v2\s*=\s*prometaphase',(r.get("Notes","") or ""),_re.I)}
    return batch in _V2_PROMETA_SET

def is_four_sisterless(batch):
    """True if the batch is a 4-SISTERLESS / 4-on-target-ablation cell. USER RULE (2026-07-16): excluded from
    every plot by default; only the sisterless-1234 plots (which explicitly show 1/2/3/4) opt it back in."""
    global _FOUR_SIS
    if _FOUR_SIS is None:
        d,_=load_master()
        _FOUR_SIS={r["Batch Name"] for r in d if (r.get("# Sisterless KTs","") or "").strip()=="4"}
    return batch in _FOUR_SIS

_PLOT_EXCL=None
def plot_excluded(batch):
    """STANDING RULE: a batch is kept OUT of every plot by default if it is master Exclude=Yes, drug-treated
    (is_drug), a REVIEW_EXCLUDE outlier, a METAPHASE-ablation (user 2026-07-16), or 4-SISTERLESS (user 2026-07-16).
    The conditionally-shown categories opt back in ONLY on the specific plots the user named: metaphase to the
    dedicated G2_metaphase_ablated plot (selects metaphase directly, does NOT call this); 4-sisterless to the
    sisterless-1234 violins (pass assign_cohorts(include_four=True)). No other plot may show them.
    assign_cohorts() enforces metaphase+4-sis+drug+excluded for cohort plots; annotation-based plots
    (frap/prepost/chromo/kk/etc.) must call THIS.

    TIMESTRIPS DO NOT USE THIS -- see timestrip_excluded()."""
    global _PLOT_EXCL
    if _PLOT_EXCL is None:
        d,_=load_master()
        _PLOT_EXCL={r["Batch Name"] for r in d if (r.get("Exclude","") or "").strip().lower() in ("yes","true","1")}
    return (batch in _PLOT_EXCL or is_drug(batch) or excluded(batch)
            or is_metaphase_ablation(batch) or is_prophase_ablation(batch)
            or is_four_sisterless(batch))


def is_if(batch):
    """True for a FIXED immunofluorescence acquisition (master `Is IF` = Yes).

    🔴 DELIBERATELY NOT PART OF plot_excluded() (2026-08-20). These cells are the SUBJECT of the IF figures
    (`G5_item2_IF_KT_561/640`), so excluding them globally would empty the very figures they belong to. The
    hazard they carry is different and narrower: they are **z-stacks at 0.031 µm/px**, half the 0.062 of the
    timelapse cells, so any figure that converts pixels to microns with a fixed scale would report their
    distances at DOUBLE. Guarded by `checks.py` (a µm-valued figure containing an IF cell is an error)
    rather than by silent exclusion. Verified 2026-08-20: no figure on any deck currently contains one.
    """
    global _IF_SET
    try:
        _IF_SET
    except NameError:
        _IF_SET = None
    if _IF_SET is None:
        d, _ = load_master()
        _IF_SET = {r["Batch Name"] for r in d
                   if (r.get("Is IF", "") or "").strip().lower() in ("yes", "true", "1")}
    return batch in _IF_SET


def timestrip_excluded(batch):
    """TIMESTRIPS ARE A SPECIAL CLASS OF FIGURE (user 2026-08-06/07): they are EXEMPT from the cohort-level
    default exclusions that plot_excluded() applies to everything else. A timestrip shows ONE cell the user
    picked deliberately, so its cohort membership -- METAPHASE-ablation, PROPHASE-ablation, 4-SISTERLESS,
    drug-treated -- is an editorial choice, not contamination, and must NOT be stamped [EXCLUDED].
    Her words: "timestrips are like a special class of figure that have special unique rules or are exempt
    from rules that are applied to everything else in many cases."

    What still stamps a timestrip is only a genuine DATA-QUALITY flag:
        * master Exclude=Yes   -- she marked the batch itself unusable
        * excluded(batch)      -- REVIEW_EXCLUDE outlier
    Those mean "this batch's data is bad", which is worth surfacing on any figure including a timestrip.

    Use THIS in every timestrip builder. Use plot_excluded() everywhere else."""
    global _PLOT_EXCL
    if _PLOT_EXCL is None:
        d, _ = load_master()
        _PLOT_EXCL = {r["Batch Name"] for r in d if (r.get("Exclude", "") or "").strip().lower() in ("yes", "true", "1")}
    return batch in _PLOT_EXCL or excluded(batch)


_MANUAL_EXCL = None
def manual_plot_exclusions(plot_id):
    """Batches the user MANUALLY decided to remove from ONE specific plot (a per-plot decision, NOT a blanket
    exclusion). Source of truth: /Volumes/4 MB/annotations/MANUAL_PLOT_EXCLUSIONS.csv
    (columns: batch, plot, reason, date_decided). Returns the set of batch names to drop for `plot_id`.
    Any builder that should honor these per-plot decisions calls this and skips the returned batches."""
    global _MANUAL_EXCL
    if _MANUAL_EXCL is None:
        import csv as _c, os as _o
        _MANUAL_EXCL = {}
        p = "/Volumes/4 MB/annotations/MANUAL_PLOT_EXCLUSIONS.csv"
        if _o.path.isfile(p):
            try:
                for r in _c.DictReader(open(p)):
                    pid = (r.get("plot", "") or "").strip(); b = (r.get("batch", "") or "").strip()
                    # A row carrying a `kt` removes ONE KINETOCHORE, not the batch, and is deliberately NOT
                    # returned here: this function drops whole batches, so letting a point-level row through
                    # would silently delete every other kinetochore in that cell from every plot that calls
                    # it. Point rows are served by manual_point_exclusions() instead.
                    if pid and b and not (r.get("kt", "") or "").strip():
                        _MANUAL_EXCL.setdefault(pid, set()).add(b)
            except Exception:
                pass
    return set(_MANUAL_EXCL.get(plot_id, set()))

_MANUAL_PT_EXCL = None

def manual_point_exclusions(plot_id):
    """SINGLE data points the user decided to remove from one specific plot -- the per-KINETOCHORE
    counterpart of manual_plot_exclusions, for cells where one kinetochore is bad but the rest are fine.

    Same source of truth (/Volumes/4 MB/annotations/MANUAL_PLOT_EXCLUSIONS.csv), with an extra `kt` column;
    a row WITHOUT `kt` stays a whole-batch exclusion and is not returned here. Returns {(batch, kt), ...}
    with kt as a string, so callers compare str(k["kt"]).

    Added 2026-08-10 for the oscillation-period outlier: 20250930 four_ablation_57 kt 4 read 30.3 min
    against a 3.2 min group median, but kt 3 of the SAME cell is a normal point that must be kept.
    """
    global _MANUAL_PT_EXCL
    if _MANUAL_PT_EXCL is None:
        import csv as _c, os as _o
        _MANUAL_PT_EXCL = {}
        p = "/Volumes/4 MB/annotations/MANUAL_PLOT_EXCLUSIONS.csv"
        if _o.path.isfile(p):
            try:
                for r in _c.DictReader(open(p)):
                    pid = (r.get("plot", "") or "").strip()
                    b = (r.get("batch", "") or "").strip()
                    kt = (r.get("kt", "") or "").strip()
                    if pid and b and kt:
                        _MANUAL_PT_EXCL.setdefault(pid, set()).add((b, kt))
            except Exception:
                pass
    return set(_MANUAL_PT_EXCL.get(plot_id, set()))

def mark_excluded_ax(ax, batch, base_title="", fontsize=5):
    """QUALITATIVE plots (contact-sheets / example montages / timestrips) MARK excluded batches instead of
    stripping them (user 2026-07-14). If plot_excluded(batch): red title + '[EXCLUDED]' + faint red tint +
    red border on that cell. Returns True if marked. base_title used if given, else leaves current title."""
    if not plot_excluded(batch):
        if base_title: ax.set_title(base_title, fontsize=fontsize)
        return False
    ax.set_title((base_title+"  [EXCLUDED]").strip(), fontsize=fontsize, color="#c00000", fontweight="bold")
    try: ax.set_facecolor((1.0,0.92,0.92))
    except Exception: pass
    for sp in ax.spines.values():
        sp.set_edgecolor("#c00000"); sp.set_linewidth(1.8); sp.set_visible(True)
    return True

def mark_retired(fig, note="antiqued prophase/prometaphase binning — use the v2 version"):
    """USER 2026-07-16: a plot that still uses the OLD (non-v2) prophase-vs-prometaphase binning is kept but
    flagged so it is unmistakable at a glance. Draws a big red 'RETIRED' diagonally across the whole figure
    plus a small red reason line. Call right before savefig on any antiqued-binning figure."""
    fig.text(0.5, 0.5, "RETIRED", fontsize=72, color="#d00000", alpha=0.28, rotation=30,
             ha="center", va="center", fontweight="bold", zorder=1000)
    fig.text(0.5, 0.015, "RETIRED — "+note, fontsize=8, color="#c00000", fontweight="bold",
             ha="center", va="bottom", zorder=1001)

def parse_time(s):
    """H:MM:SS / MM:SS / seconds -> seconds (float) or None.  Sign-preserving.

    BUGFIX 2026-08-04: the old version split on ':' and did int() per part, so a leading
    minus landed on an hours field of '-0' — and int('-0')==0 — silently turning
    '-0:07:41' into +461.  Event-time rows legitimately carry negative times (an event
    that PRECEDES the t=0 ablation): 17 'Metaphase Start (s)', 13 'NEB Time (s)' and
    4 'First Congression (s)' rows in the master.  The sign is now taken from the string
    and applied to the whole magnitude.  (group2_metaphase_ablated.psec() strips the '-'
    before calling in, so it stays correct either way.)"""
    s=(s or "").strip()
    if not s: return None
    if re.fullmatch(r'-?\d+(\.\d+)?', s): return float(s)
    if not re.fullmatch(r'\s*-?\d{1,2}:\d{2}(:\d{2})?\s*', s): return None
    neg = s.startswith('-')
    parts=[int(x) for x in s.lstrip('-').split(':')]
    if len(parts)==3: v = parts[0]*3600+parts[1]*60+parts[2]
    elif len(parts)==2: v = parts[0]*60+parts[1]
    else: return None
    return -v if neg else v

def abl_to_meta_min(r, fallback_metastart=False):
    """Ablation->metaphase interval in MINUTES + a source tag.
    PRIMARY (accurate): master 'Ablation->Meta (min)' — an elapsed H:MM:SS string (parse_time -> SECONDS, /60)
    — or the comma-formatted 'Ablation->Meta (s)'.
    FALLBACK (fallback_metastart=True; 2026-07-07 feedback D5/D6/D7): when BOTH stored columns are blank but
    'Metaphase Start (s)' is defined, use Metaphase Start as the interval under the temporal-calibration model
    the user specified: a prophase/prometaphase ablation is the FIRST mitotic event, so if the batch is
    calibrated the first ablation is t=0 and 'Metaphase Start' (elapsed from t=0) == ablation->metaphase.
    ('First Ablation (s)' is a UNIX-epoch wall-clock for these blanks, on a different clock than the elapsed
    event times, so it cannot be subtracted directly.) Validated against the cells that DO carry the stored
    interval, this estimate slightly OVER-shoots (recording sometimes began before the ablation) by ~0-6 min
    (mean ~2.9) — acceptable per explicit user direction; recovered points are tagged 'metastart' so callers
    can render/log them distinctly. Returns (minutes, source) with source in {'stored','metastart',None}."""
    sec=parse_time(r.get("Ablation->Meta (min)",""))
    if sec is not None: return sec/60.0,'stored'
    v=r.get("Ablation->Meta (s)","").replace(",","").strip()
    try: return float(v)/60.0,'stored'
    except Exception: pass
    if fallback_metastart:
        ms=parse_time(r.get("Metaphase Start (s)",""))
        if ms is not None and ms>0: return ms/60.0,'metastart'
    return None,None

def load_master():
    rows=list(csv.reader(open(MASTER)))
    hi=next(i for i,r in enumerate(rows) if r and r[0].strip()=="Batch Name")
    hdr=[c.strip() for c in rows[hi]]; idx={c:i for i,c in enumerate(hdr)}
    out=[]
    for r in rows[hi+1:]:
        if not r or not r[0].strip(): continue
        out.append({c:(r[idx[c]].strip() if idx[c]<len(r) else "") for c in hdr})
    return out, hdr

def load_master_plots():
    """load_master() minus PROPHASE-ablation rows — the master reader FIGURE BUILDERS should use.

    USER 2026-08-06: "if a plot didnt already have a prophase 'area' or 'designation', etc, then its meant
    for just prometaphase." Most builders never touch plot_excluded() or assign_cohorts(); they call
    load_master() and roll their own filters, so neither shared gate reaches them and prophase cells leaked
    into ~100 placed figures.

    This is deliberately a SEPARATE function rather than a flag on load_master(): load_master() is also the
    raw reader for the annotation decks, the master audits and dataops, where silently dropping 89 rows
    would be wrong. Builders that DRAW a prophase group (the phase-split family, group2_prophase_dynamics,
    the creation-phase figures, noc-washout, kk-by-phase) must keep calling load_master().

    Returns (rows, header) exactly like load_master()."""
    rows, hdr = load_master()
    keep = [r for r in rows
            if not (r.get("Phase of Ablations", "") or "").strip().lower().startswith("proph")]
    return keep, hdr


def double_chromosome_batches():
    """kinetochoreless tag + comment-flagged 'two KTs on same chromosome'.
    2026-07-29: the bare `same chromosome` alternative was a FALSE-POSITIVE magnet — it pulled in
    `20251029 triple_ablation_26`, whose note ("see first and second measurements of the same chromosome")
    is about re-measuring a chromosome whose ARMS were cut, not about ablating both of its kinetochores.
    That cell is a plain 3-sisterless cell and, because DC cells are dropped from every standard cohort
    violin, it was silently missing from the 3-Sister group as well as wrong in the DC group. The phrase now
    has to be preceded by two/both/2 within 30 characters, which keeps the one genuine catch
    (`20250923 triple_ablation_collagen_2` — "at lease two on the same chromosome") and drops nothing else.
    Verified: the returned set goes 15 -> 14 batches, the only difference being triple_ablation_26."""
    s=set()
    data,_=load_master()
    pat=re.compile(r'(two|both|2)\b[^.]{0,30}same chromosome|two k\w* (on|in).{0,20}(same )?chrom|both kinetochores on one chrom|kinetochoreless|double\s+kinetochore\w*\s+ablation[^.]{0,20}one\s+chrom', re.I)
    for r in data:
        if r.get("# Sisterless KTs","")=="kinetochoreless chromosome": s.add(r["Batch Name"])
        for c in ("Notes","annotation_notes","Exclude Reason"):
            if pat.search(r.get(c,"")): s.add(r["Batch Name"])
    for t in ("batch_meta","cell_outlines","kt_points","chromo_lines"):
        fn=f"{ANN}/{t}.csv"
        if not os.path.isfile(fn): continue
        rr=list(csv.reader(open(fn))); jx={c:i for i,c in enumerate(rr[0])}
        for r in rr[1:]:
            if r and jx['batch']<len(r) and 'notes' in jx and jx['notes']<len(r) and pat.search(r[jx['notes']]):
                s.add(r[jx['batch']].strip())
    return s

def mitotic_duration_min(r):
    """Metaphase->Anaphase in minutes; outlier-screened. Returns (val, ok)."""
    a=parse_time(r.get("Metaphase Start (s)","")); b=parse_time(r.get("Anaphase Onset (s)",""))
    if a is None or b is None: return None,False
    d=(b-a)/60.0
    if d<=0:
        log_review("mitotic_duration_min",r["Batch Name"],f"{d:.1f}","non-positive Meta->Ana (check event times)"); return None,False
    if d>300:
        log_review("mitotic_duration_min",r["Batch Name"],f"{d:.1f}","implausibly long (>300 min) — likely typo"); return None,False
    return d,True

def iqr_outliers(metric, pairs):
    """pairs=[(batch,val)]; flag val > Q3+3*IQR or < Q1-3*IQR; return kept list."""
    vals=np.array([v for _,v in pairs],float)
    if len(vals)<5: return pairs
    q1,q3=np.percentile(vals,[25,75]); iqr=q3-q1; lo,hi=q1-3*iqr,q3+3*iqr
    kept=[]
    for b,v in pairs:
        if v>hi or v<lo:
            log_review(metric,b,f"{v:.2f}",f"statistical outlier (outside [{lo:.1f},{hi:.1f}])")
        else: kept.append((b,v))
    return kept

_PRO_ABL=None
def is_prophase_ablation(batch):
    """True if the batch's ablation was in PROPHASE. USER RULE 2026-08-06: "if a plot didnt already have a
    prophase 'area' or 'designation', etc, then its meant for just prometaphase" — so prophase batches are
    EXCLUDED from every plot by default, exactly like metaphase ones, and only the figures that DRAW a
    prophase group include them (they select phase directly and never call plot_excluded)."""
    global _PRO_ABL
    if _PRO_ABL is None:
        d,_=load_master()
        _PRO_ABL={r["Batch Name"] for r in d if (r.get("Phase of Ablations","") or "").strip().lower().startswith("proph")}
    return batch in _PRO_ABL

def is_metaphase_ablation(batch):
    """True if the batch's ablation was in METAPHASE (not prometaphase). User rule: metaphase-ablation batches are
    EXCLUDED from every plot by default and only shown where explicitly requested (the phase-split family)."""
    global _META_ABL
    try: _META_ABL
    except NameError: _META_ABL=None
    if _META_ABL is None:
        d,_=load_master()
        _META_ABL={r["Batch Name"] for r in d if (r.get("Phase of Ablations","") or "").strip().lower().startswith("metaph")}
    return batch in _META_ABL
_META_ABL=None

def assign_cohorts(include_metaphase=False, include_four=False, include_prophase=False, include_double=False):
    """Return dict cohort_name -> list of (batch, duration_min). Includes matched controls.

    USER RULE (default): METAPHASE-ablation, PROPHASE-ablation and 4-SISTERLESS batches are EXCLUDED from
    every cohort, so they don't leak into plots. The default cohort set is PROMETAPHASE ONLY.
      include_metaphase=True  -> only the phase-split family, which has a metaphase bucket by design
      include_four=True       -> only the sisterless-1234 plots that explicitly show 4-sisterless
      include_double=True     -> only plots that DRAW a double-chromosome group. The 2026-07-06 rule is
                                 "don't plot the destruction of two kinetochores on one chromosome data
                                 unless I specifically say to" — this is how a plot says so, leaving the
                                 global default untouched (user 2026-08-10, for Violin 2 with controls).
      include_prophase=True   -> only plots that DRAW a prophase group (user 2026-08-06: "unless i specify
                                 including prophase in a plot ... then prophase should not be included").
                                 That request came from finding 41 prophase cells inside
                                 G1_violin2_mitotic_duration_journal, which has no prophase group.
    Phase is read from the master's `Phase of Ablations`, which as of 2026-08-06 IS the v2 binning
    (her manual determinations were written into it) — there is no separate v2 designation any more."""
    data,_=load_master()
    dbl=double_chromosome_batches()
    act=[r for r in data if r.get("Exclude","") not in ("Yes","yes") and not is_mad1(r["Batch Name"]) and not excluded(r["Batch Name"])]   # Mad1 reserved for Group 5; REVIEW_EXCLUDE = user-flagged outliers
    coh={k:[] for k in ["unModified","1-Sister","2-Sister","3-Sister","4-Sister","Double Chromosome","Off-Target"]}
    offall=[]  # (batch, dur_or_None, ntargets_or_None) — EVERY off-target (non-drug, non-excluded)
    for r in act:
        b=r["Batch Name"]; tt=r.get("On-Target / Off-Target",""); sis=r.get("# Sisterless KTs","")
        if is_drug(b):
            continue  # ZM/noc excluded from ALL baseline cohorts (handled in Group-4 drug analysis)
        _ph=(r.get("Phase of Ablations","") or "").strip().lower()
        if not include_metaphase and _ph.startswith("metaph"):
            continue  # USER RULE: metaphase ablations excluded by default (only the phase-split family opts in)
        if not include_prophase and _ph.startswith("proph"):
            continue  # USER RULE 2026-08-06: prophase excluded unless the plot draws a prophase group
        dur,ok=mitotic_duration_min(r)
        if b in dbl:
            if ok: coh["Double Chromosome"].append((b,dur)); continue
        if tt=="Unmodified":
            if ok: coh["unModified"].append((b,dur))
        elif tt=="On-target" and sis in ("1","2","3","4"):
            if sis=="4" and not include_four:
                continue  # USER RULE: 4-sisterless (4 on-target ablations) excluded by default (only sisterless-1234 opts in)
            if ok: coh[f"{sis}-Sister"].append((b,dur))
        elif tt=="On-target":
            # ROOT-CAUSE FIX (2026-08-03, item M2-12 "unassigned group is unacceptable"): every
            # double-chromosome / "kinetochoreless chromosome" On-target row is already routed to
            # coh["Double Chromosome"] above (then correctly emptied by EXCLUDE_DOUBLE_CHROMOSOME) and
            # never reaches here. This branch is reached ONLY when '# Sisterless KTs' is blank or holds a
            # value her 1/2/3/4-Sister scheme doesn't define (observed: '', '0', '5'). Previously these
            # fell through this whole if/elif chain with NO log call and NO cohort -- silent data loss that
            # resurfaced downstream as a literal "unassigned" bucket wherever a builder did
            # coh.get(b, "unassigned"). There is no defensible 1/2/3/4 bin to force these into without
            # guessing (her rule: bin from the '# Sisterless KTs' column only, never batch name), so they
            # stay excluded from every cohort -- but now with a specific, permanent, logged reason instead
            # of vanishing silently. (Audited full master: this is 7 rows total -- 5 blank, 2 valued '0';
            # a further 2 rows valued '5' are independently master Exclude=Yes / is_drug and never reach
            # here at all.)
            if not sis:
                log_review("cohort_assign_gap",b,"# Sisterless KTs blank",
                    "On-target ablation with no '# Sisterless KTs' value in the master -- ablation number "
                    "cannot be binned from the required column (batch-name inference is disallowed per her "
                    "rule); excluded from every cohort plot pending the master annotation being filled in")
            else:
                log_review("cohort_assign_gap",b,f"# Sisterless KTs={sis}",
                    "On-target ablation whose '# Sisterless KTs' value ("+sis+") is outside the defined "
                    "1/2/3/4-Sister bins and is not a double-chromosome/'kinetochoreless chromosome' tag -- "
                    "no defensible cohort exists for this value without guessing; excluded from every "
                    "cohort plot pending her review of the master value")
        elif tt=="Off-target":
            nt=r.get("# Unique Targets","")
            offall.append((b, dur if ok else None, int(nt) if nt.isdigit() else None))
            if ok: coh["Off-Target"].append((b,dur))
    # IQR screen per experimental cohort
    for k in ["unModified","1-Sister","2-Sister","3-Sister","4-Sister","Double Chromosome","Off-Target"]:
        coh[k]=iqr_outliers(f"dur:{k}",coh[k])
    # ── MATCHED CONTROLS BY IMAGING SESSION (rewritten 2026-08-10) ────────────────────────────────
    # USER 2026-08-10, comparing this against the rebuilt ablation-dose plot: "it seems like a better
    # distribution so if it doesnt match then reorganize the off-target samples so that theyre organized
    # that way when plotted on the main violin plot on the second board".
    #
    # The old rule allocated off-target cells to 1/2/3-Sister Controls by PROPORTIONAL QUOTA and then by
    # nearest `# Unique Targets` to each on-target group's median. That is an arithmetic allocation, not an
    # experimental one: it can put a control in the 3-Sister group purely because the quota there was unfilled,
    # and it logged "poor attempt-match (forced)" when it had to. An off-target control is not defined by how
    # many spots it received -- it is defined by THE EXPERIMENT IT WAS ACQUIRED IN, and the imaging session
    # (the date prefix) is what identifies that experiment. So each control now inherits the ablation number
    # of the ON-TARGET cells shot the same day, read from `# Sisterless KTs` (the standing rule); the old
    # nearest-#targets logic is kept only as the fallback for a session with no on-target 1/2/3 cell.
    _sess = {}
    for _s in ("1", "2", "3"):
        for _b, _ in coh[f"{_s}-Sister"]:
            _d = _b.split()[0] if _b.split() else ""
            _sess.setdefault(_d, []).append(_s)
    # DETERMINISM FIX (2026-08-10): this was max(set(_v), ...). Iterating a SET of strings is ordered by
    # Python's per-process string hash, so when a session had a TIE (equal counts of two on-target
    # sizes) the winner flipped between runs — and that cascaded into which control group every
    # off-target landed in. Observed live: 1/2/3-Sisterless controls came out 31/11/18 on one run and
    # 31/10/19 on the next, from identical inputs, so N and the p-values moved on every rebuild.
    # sorted() makes the tie-break the lowest label, stably, run to run.
    _DATE_EXP = {_d: max(sorted(set(_v)), key=_v.count) for _d, _v in _sess.items()}
    on_sizes={s:len(coh[f"{s}-Sister"]) for s in ("1","2","3")}
    centers={}
    for s in ("1","2","3"):
        nts=[int(load_master_target(b)) for b,_ in coh[f"{s}-Sister"] if load_master_target(b) is not None]
        centers[s]=np.median(nts) if nts else 3.0
    P=len(offall)
    assigned={}; filled={s:[] for s in ("1","2","3")}
    _by_sess=0; _by_targets=0
    for (b,d,nt) in offall:
        _d = b.split()[0] if b.split() else ""
        s = _DATE_EXP.get(_d)
        if s in ("1","2","3"):
            _by_sess += 1
        else:
            # fallback: no on-target cell from that session, so fall back to the old nearest-#targets rule
            if nt is not None:
                s=min(("1","2","3"),key=lambda q:abs(nt-centers[q]))
            else:
                s=min(("1","2","3"),key=lambda q:len(filled[q]))
                log_review("control_match",b,"","no session match and no #targets — assigned to smallest control group")
            _by_targets += 1
        assigned[b]=s; filled[s].append(b)
    log_review("control_match_method","", f"session={_by_sess} fallback={_by_targets}",
               "off-target controls assigned by imaging session (user 2026-08-10)")
    durmap={b:d for (b,d,nt) in offall}
    ctrl={f"{s}-Sister Controls":[(b,durmap[b]) for b in filled[s] if durmap[b] is not None] for s in ("1","2","3")}
    # completeness check: every off-target assigned exactly once
    assert len(assigned)==len({b for (b,_,_) in offall})==P, "off-target partition incomplete"
    out={"unModified":coh["unModified"],
         "1-Sister":coh["1-Sister"],"1-Sister Controls":ctrl["1-Sister Controls"],
         "2-Sister":coh["2-Sister"],"2-Sister Controls":ctrl["2-Sister Controls"],
         "3-Sister":coh["3-Sister"],"3-Sister Controls":ctrl["3-Sister Controls"],
         "4-Sister":coh["4-Sister"],
         "Double Chromosome":coh["Double Chromosome"],
         "Off-Target/Control":coh["Off-Target"]}
    # GLOBAL (user feedback 2026-07-06): "A note for nearly all plots: don't plot the destruction of
    # two kinetochores on one chromosome data unless I specifically say to." Empty the cohort so it
    # drops out of every plot that iterates assign_cohorts(). Individual plots that explicitly want it
    # back can read coh_raw["Double Chromosome"] via double_chromosome_batches().
    if EXCLUDE_DOUBLE_CHROMOSOME and not include_double:
        out["Double Chromosome"]=[]
    return out

# GLOBAL feedback flag — see assign_cohorts(). Flip to False only if a specific plot is told to show it.
EXCLUDE_DOUBLE_CHROMOSOME=True

_TGT={}
def load_master_target(batch):
    global _TGT
    if not _TGT:
        data,_=load_master()
        for r in data:
            nt=r.get("# Unique Targets","")
            _TGT[r["Batch Name"]]=int(nt) if nt.isdigit() else None
    return _TGT.get(batch)

# ---------- per-plot data / code / settings master (on 4 MB) ----------
PLOT_BASE="/Volumes/4 MB/ablation_plots"
def _backfill_stats_at_exit():
    """Attach this run's FULL test log to any figure it recorded that still has no statistics.

    A builder that calls record_plot BEFORE it runs its tests (very common - the figure is saved, then the
    stats grid is computed) leaves the per-figure window empty. The tests still belong to that builder, so
    they are recorded as `statistics_in_builder_run` - deliberately a DIFFERENT key from
    `statistics_observed`, because this is SCRIPT-scoped evidence, not a p attributed to one comparison."""
    try:
        if not os.environ.get("CAPTURE_STATS") or not STAT_LOG_ALL or not RECORDED_THIS_RUN: return
        import json as _js   # `_o`/`_j` are aliases local to record_plot, not module-level (fixed 2026-08-05)
        sp=f"{PLOT_BASE}/PLOT_SETTINGS.json"
        if not os.path.isfile(sp): return
        allset=_js.load(open(sp))
        seen=set(); tests=[]
        for t,stt,pv in STAT_LOG_ALL:
            k=(t,round(pv,12))
            if k in seen: continue
            seen.add(k); tests.append({"test":t,"statistic":stt,"p":pv})
        n=0
        for pid in dict.fromkeys(RECORDED_THIS_RUN):
            e=allset.get(pid)
            if not e: continue
            st=e.get("settings") or {}
            if "statistics_observed" in st: continue
            st=dict(st); st["statistics_in_builder_run"]=tests[:40]
            e["settings"]=st; n+=1
        if n:
            _js.dump(allset,open(sp,"w"),indent=1)
            print(f"  [stats backfill] attached {len(tests)} tests to {n} figure(s) with none of their own")
    except Exception as _e:
        print(f"  [stats backfill] failed: {_e}")

import atexit as _atexit
_atexit.register(_backfill_stats_at_exit)


def source_hash(path):
    """CANONICAL content hash of a source spreadsheet — order-independent, cell-level, so an annotation
    SERVER re-writing the file with the SAME data (different row order / formatting) does NOT change the
    hash; only a REAL data edit does. CSVs are parsed + row-sorted; non-CSVs fall back to a raw byte hash."""
    import hashlib as _hl, csv as _cv, os as _o
    if not _o.path.isfile(path): return None
    try:
        if path.lower().endswith(".csv"):
            rows=list(_cv.reader(open(path,newline="")))
            # normalize each cell (strip whitespace) + drop fully-blank rows + sort -> hash reflects DATA only,
            # immune to a server re-writing with different row order / trailing whitespace / blank lines.
            if path==MASTER and rows:  # FIGURE-RELEVANT: drop Mad1/drug rows (never plotted; servers micro-churn them)
                try: _bi=rows[0].index('Batch Name')
                except Exception: _bi=0
                rows=[rows[0]]+[r for r in rows[1:] if _bi<len(r) and not (is_mad1(r[_bi]) or is_drug(r[_bi]))]
            norm=["".join(c.strip() for c in r) for r in rows if any(c.strip() for c in r)]
            return _hl.md5("\n".join(sorted(norm)).encode("utf-8","replace")).hexdigest()
        h=_hl.md5()
        with open(path,"rb") as f:
            for ch in iter(lambda:f.read(1<<20),b""): h.update(ch)
        return h.hexdigest()
    except Exception: return None
# The SOURCE spreadsheets every plot ultimately derives from. A plot's data CSV is the 'plot spreadsheet'
# (the figure is rendered from it, and you can filter/exclude points there), but it MUST keep ties to these
# sources so additions/edits to the source propagate. record_plot stamps the source file mtimes at build
# time; verify_source_lineage.py flags any plot whose source changed since the plot CSV was built.
SOURCE_MASTER=MASTER
SOURCE_ANNOT_KT=f"{ANN}/kt_points.csv"
SOURCE_ANNOT_OUT=f"{ANN}/cell_outlines.csv"
SOURCE_ANNOT_PLATE=f"{ANN}/SISTERLESS_PLATE_JOIN_TIMES.csv"
def figure_data_rows(fig):
    """Extract what a figure ACTUALLY DREW, as (header, rows) — the last-resort provenance source.

    Dozens of builders call record_plot with a hardcoded empty rows list, so their data CSV is a header and
    nothing else: the figure cannot be checked against its own data, the significance scan cannot see it,
    and any `_zoom` companion is built from nothing (NOTES §8). Reconstructing each builder's source data by
    hand would mean guessing what every call site meant; reading it off the Artist objects records exactly
    what the reader sees, which is the thing the CSV is supposed to describe.

    Covers the marks these figures actually use: Line2D (lines, markers, trend lines), PathCollection
    (scatter), and Rectangle (bars/histograms). Returns (None, []) if the figure holds none of them.
    """
    import numpy as _np
    rows = []
    for ai, ax in enumerate(fig.get_axes()):
        panel = ax.get_title() or ax.get_ylabel() or f"axes{ai}"
        for ln in ax.get_lines():
            lab = ln.get_label()
            if isinstance(lab, str) and lab.startswith("_"):
                lab = ""
            x, y = ln.get_xdata(), ln.get_ydata()
            for xi, yi in zip(_np.atleast_1d(x), _np.atleast_1d(y)):
                try:
                    if _np.isfinite(float(xi)) and _np.isfinite(float(yi)):
                        rows.append([panel, lab, "line", float(xi), float(yi)])
                except Exception:
                    pass
        for col in getattr(ax, "collections", []):
            off = getattr(col, "get_offsets", lambda: None)()
            if off is None:
                continue
            lab = col.get_label() if isinstance(col.get_label(), str) else ""
            if lab.startswith("_"):
                lab = ""
            for pt in _np.atleast_2d(off):
                try:
                    if len(pt) == 2 and _np.isfinite(pt[0]) and _np.isfinite(pt[1]):
                        rows.append([panel, lab, "point", float(pt[0]), float(pt[1])])
                except Exception:
                    pass
        for pa in getattr(ax, "patches", []):
            try:
                if pa.__class__.__name__ == "Rectangle" and float(pa.get_height()) != 0.0:
                    rows.append([panel, pa.get_label() if isinstance(pa.get_label(), str) and
                                 not pa.get_label().startswith("_") else "", "bar",
                                 float(pa.get_x()) + float(pa.get_width()) / 2.0, float(pa.get_height())])
            except Exception:
                pass
    if not rows:
        return None, []
    return ["panel", "series", "mark", "x", "y"], rows


# ---- STATISTICS CAPTURE (2026-08-05) ---------------------------------------------------------------
# 146 placed figures had no recorded statistics: their builders compute a test and then throw the number
# away instead of passing it to record_plot. Rather than edit ~146 builders, wrap the scipy.stats functions
# once here. Every call is logged with its exact p; record_plot() then attaches whatever was computed SINCE
# THE PREVIOUS record_plot to the figure being written.
# HONESTY NOTE: when a builder computes several tests before recording one figure, this yields a CANDIDATE
# LIST for that figure, not a single attributed p. The recorded key is named `statistics_observed` for that
# reason, and the legend doc presents it as "tests computed during this figure's build".
STAT_LOG = []
STAT_LOG_ALL = []          # every test this process ran, never cleared
RECORDED_THIS_RUN = []     # plot_ids written by record_plot during this process
def _install_stat_capture():
    try:
        from scipy import stats as _st
    except Exception:
        return
    if getattr(_st, "_ablation_capture", False): return
    def _mk(name, fn):
        def _w(*a, **k):
            r = fn(*a, **k)
            try:
                p = getattr(r, "pvalue", None)
                if p is None and isinstance(r, tuple) and len(r) >= 2: p = r[1]
                stat = getattr(r, "statistic", None)
                if p is not None:
                    _e=(name, float(stat) if stat is not None else None, float(p))
                    STAT_LOG.append(_e); STAT_LOG_ALL.append(_e)
            except Exception: pass
            return r
        return _w
    for _n in ("mannwhitneyu","kruskal","wilcoxon","spearmanr","pearsonr","ttest_ind","ttest_rel",
               "chi2_contingency","fisher_exact","ranksums"):
        _f = getattr(_st, _n, None)
        if _f is not None:
            try: setattr(_st, _n, _mk(_n, _f))
            except Exception: pass
    _st._ablation_capture = True
if os.environ.get("CAPTURE_STATS"):
    _install_stat_capture()



def register_panel(plot_id, parent, caption="", settings=None, script=None):
    """Register a PANEL of an already-recorded figure, without writing a second data CSV.

    A split panel is one view of its parent's dataset (NOTES 2026-08-09), so it must not duplicate the
    data — but it MUST exist in PLOT_SETTINGS, or it is a placed figure with no provenance and the legend
    builder has nothing to say about it. 2026-08-18: 17 figures on the live decks were in exactly that
    state (the kk_osc_* panels, G6_three_group_model, the nf9 __pieceN files, the AB5 excerpts).
    Writes `panel_of` so `dataops/build_legend_bullets_20260808.py` inherits the parent's rows and stats.
    """
    import json as _j, os as _o, datetime as _dt
    _ps = f"{PLOT_BASE}/PLOT_SETTINGS.json"
    try:
        reg = _j.load(open(_ps)) if _o.path.exists(_ps) else {}
    except Exception:
        reg = {}
    ent = reg.get(plot_id) or {}
    ent.update({"panel_of": parent,
                "caption": caption or ent.get("caption", ""),
                "settings": dict(settings or {}, panel_of=parent),
                "code": _o.path.basename(script) if script else ent.get("code", ""),
                "registered_on": _dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "registered_as_panel": True})
    # Write the SAME KEY SHAPE record_plot writes. The first version omitted `data`/`n_rows`/`source`,
    # and the very next record_plot call crashed with KeyError 'data' while writing PLOT_SETTINGS.md —
    # a partial entry must never be able to break an unrelated build.
    ent.setdefault("data", (reg.get(parent) or {}).get("data", ""))
    ent.setdefault("n_rows", None)
    ent.setdefault("source", (reg.get(parent) or {}).get("source", {"files": [], "key_column": None}))
    reg[plot_id] = ent
    tmp = _ps + ".tmp"
    with open(tmp, "w") as fh:
        _j.dump(reg, fh, indent=1)
    _o.replace(tmp, _ps)
    return plot_id


def congression_times(prefer="structured"):
    """One congression time per (batch, chromosome), unioned across BOTH stores that hold it.

    2026-08-18, from her question "are these annotation types truly different?": they are not. Where both
    `annotations/CHROMOSOME_MASTER.csv` (congression_time_s / congression_hms) and
    `annotations/SISTERLESS_PLATE_JOIN_TIMES.csv` (chromosome_N_plate_join) hold a time for the SAME
    chromosome, the median difference is 0 s and 35 of 45 agree within a minute — they are two records of
    one measurement. Their COVERAGE differs, though: 43 cells vs 29, union 44, so a builder that reads one
    store alone is thinner than the data allows.

    Returns {batch: {chr_num: (seconds, source)}}. The structured per-chromosome table wins on conflict
    (NOTES 2026-08-14: "her structured per-chromosome tables are data; a regex over her free text is my
    inference"), and the 10 chromosomes where the two disagree by more than a minute are listed in
    `4_TABLES_AND_REPORTS/CONGRESSION_STORE_COMPARE_20260818.csv` for her to reconcile.
    """
    import csv as _c, io as _io, os as _o, collections as _col
    A = "/Volumes/4 MB/annotations/"
    def _rd(p):
        if not _o.path.exists(p): return []
        with _io.open(p, encoding="utf-8", errors="replace") as f: return list(_c.DictReader(f))
    def _sec(v):
        s = str(v or "").strip()
        if not s or s.lower() in ("n/a", "na", "-", "0"): return None
        neg = s.startswith("-"); s = s.lstrip("-")
        try:
            if ":" in s:
                p = [float(x or 0) for x in s.split(":")]
                while len(p) < 3: p.insert(0, 0)
                sec = p[0]*3600 + p[1]*60 + p[2]
            else: sec = float(s)
        except ValueError: return None
        return -sec if neg else sec
    out = _col.defaultdict(dict)
    for r in _rd(A + "SISTERLESS_PLATE_JOIN_TIMES.csv"):
        b = (r.get("batch") or "").strip()
        if not b: continue
        for i in (1, 2, 3):
            t = _sec(r.get(f"chromosome_{i}_plate_join_s")) or _sec(r.get(f"chromosome_{i}_plate_join"))
            if t is not None: out[b][str(i)] = (t, "SISTERLESS_PLATE_JOIN_TIMES")
    for r in _rd(A + "CHROMOSOME_MASTER.csv"):
        b = (r.get("batch") or "").strip(); c = (r.get("chr_num") or "").strip()
        if not b or not c: continue
        t = _sec(r.get("congression_time_s")) or _sec(r.get("congression_hms"))
        if t is None: continue
        if prefer == "structured" or c not in out[b]:
            out[b][c] = (t, "CHROMOSOME_MASTER")
    return dict(out)

def record_plot(plot_id, header, rows, settings, script=None, caption="", source=None, key_column="batch",
                fig=None):
    # A PERCELL re-render is an ARCHIVE copy of the retired look, so it must register under its own id --
    # otherwise it would overwrite the live figure's caption/settings in PLOT_SETTINGS.json with a
    # description of the version she asked to have moved out of the decks.
    if PERCELL_LINES and not str(plot_id).endswith("_percell"):
        plot_id = f"{plot_id}_percell"
    # A PUB render is the SAME figure with the words moved to the legend -- it is not a different plot, and
    # rewriting the registry from it would lose the real captions. Skip registration entirely.
    if PUB:
        return
    """Persist a plot's data CSV ('plot spreadsheet') + generating code + visual settings + SOURCE LINEAGE.
    source     = list of source-spreadsheet paths the data ultimately comes from (default: the master).
    key_column = the column in THIS csv that ties each row back to a source row (default 'batch'); if absent
                 from `header` it is recorded as None (aggregate/derived plot).
    The plot is BUILT FROM this csv, but the csv is DERIVED FROM `source` — the source mtimes are stamped so
    a later source change is detectable and the plot re-derived (keeps the tie the user asked for)."""
    import os as _o, csv as _c, shutil as _s, json as _j
    _o.makedirs(f"{PLOT_BASE}/data",exist_ok=True); _o.makedirs(f"{PLOT_BASE}/code",exist_ok=True)
    # 2026-08-03: a figure can render perfectly while its recorded CSV is EMPTY, because the builder passed
    # an empty rows list. The figure is fine; the PROVENANCE is not - the plot can no longer be checked
    # against its own data, and any _zoom companion built from that CSV is built from nothing. 124 CSVs were
    # in this state (28 of them placed in a deck, 7 still advertising an N or a p-value in their settings).
    # Warn loudly rather than let it stay silent; louder still when settings claim a statistic.
    if not rows and fig is not None:
        # nothing was passed, but the figure knows what it drew — record that rather than an empty table
        _h, _r = figure_data_rows(fig)
        if _r:
            header, rows, key_column = _h, _r, None
    if not rows:
        _stat={k:v for k,v in (settings or {}).items()
               if str(k).lower() in ("n","p","rho","stat","pvalue","kruskal_p","mannwhitney_p")}
        log_review("record_plot_empty_rows", plot_id, f"header={len(header)} cols, 0 rows",
                   ("recorded NO data rows while settings advertise " + str(_stat) +
                    " - the figure may draw fine but its provenance cannot be verified and any _zoom "
                    "companion is built from nothing") if _stat else
                   "recorded NO data rows - figure may draw fine but its provenance cannot be verified")
        print(f"  [record_plot WARNING] {plot_id}: 0 data rows written"
              + (f" while settings claim {_stat}" if _stat else ""))
    with open(f"{PLOT_BASE}/data/{plot_id}.csv","w",newline="") as f:
        w=_c.writer(f); w.writerow(header); w.writerows(rows)
    code_name=""
    if script and _o.path.isfile(script):
        code_name=f"{plot_id}__{_o.path.basename(script)}"; _s.copy(script,f"{PLOT_BASE}/code/{code_name}")
    src=[s for s in (source if source is not None else [SOURCE_MASTER]) if s]
    src_mtimes={s:(round(_o.path.getmtime(s),1) if _o.path.isfile(s) else None) for s in src}
    # CANONICAL CONTENT HASH per source (robust to annotation-server re-serialization: only a REAL data edit
    # changes it). Authoritative staleness signal (see source_hash()).
    src_hashes={s:source_hash(s) for s in src}
    sp=f"{PLOT_BASE}/PLOT_SETTINGS.json"
    try: allset=_j.load(open(sp)) if _o.path.isfile(sp) else {}
    except Exception: allset={}
    if os.environ.get("CAPTURE_STATS"):
        RECORDED_THIS_RUN.append(plot_id)
    if os.environ.get("CAPTURE_STATS") and STAT_LOG:
        # everything computed since the previous record_plot belongs to THIS figure's build window
        settings=dict(settings or {})
        settings["statistics_observed"]=[{"test":t,"statistic":st_,"p":pv} for t,st_,pv in STAT_LOG]
        del STAT_LOG[:]
    allset[plot_id]={"caption":caption,"settings":settings,"n_rows":len(rows),
                     "data":f"data/{plot_id}.csv","code":f"code/{code_name}" if code_name else "",
                     "source":{"files":src,"mtimes_at_build":src_mtimes,"hashes_at_build":src_hashes,
                               "key_column":(key_column if key_column in header else None)}}
    _tmp=f"{sp}.{_o.getpid()}.tmp"; _j.dump(allset,open(_tmp,"w"),indent=1); _o.replace(_tmp,sp)
    with open(f"{PLOT_BASE}/PLOT_SETTINGS.md","w") as f:
        f.write("# Ablation figures — plot data / code / visual-settings master\n")
        f.write("Auto-maintained. Data CSVs in `data/` ('plot spreadsheet' — filter/exclude points here), code in `code/`.\n")
        f.write("Each plot is BUILT FROM its data CSV but DERIVED FROM the SOURCE spreadsheet(s) below; keep the tie.\n\n")
        for pid,info in sorted(allset.items()):
            # .get() everywhere: an entry written by register_panel (or an older schema) has no data file,
            # and one missing key used to abort the whole PLOT_SETTINGS.md rewrite mid-run.
            f.write(f"## {pid}\n- caption: {info.get('caption','')}\n"
                    f"- data: `{info.get('data','')}` ({info.get('n_rows')} rows)\n")
            f.write(f"- code: `{info.get('code','')}`\n- visual settings: {info.get('settings',{})}\n")
            sc=info.get("source",{})
            f.write(f"- SOURCE: {sc.get('files')}  (tie key: `{sc.get('key_column')}`)\n\n")
    # source -> plots lineage manifest (so a source edit shows which plots must be re-derived)
    inv={}
    for pid,info in allset.items():
        for sfile in info.get("source",{}).get("files",[]): inv.setdefault(sfile,[]).append(pid)
    with open(f"{PLOT_BASE}/PLOT_LINEAGE.md","w") as f:
        f.write("# Source-spreadsheet -> plot lineage\n")
        f.write("If a SOURCE file below changes (rows added/edited), every plot listed under it must be\n")
        f.write("regenerated so the change is reflected. `verify_source_lineage.py` flags stale ones.\n\n")
        for sfile in sorted(inv):
            f.write(f"## {sfile}\n"+"".join(f"- {p}\n" for p in sorted(inv[sfile]))+"\n")
    return f"{PLOT_BASE}/data/{plot_id}.csv"

# ---------- journal style ----------
# USER 2026-08-11: text ~2.2x on the violin figures placed in META_FIGURES. Gated by an ALLOWLIST and applied
# in the savefig wrapper rather than in each builder: these ten come from six different scripts, several of
# which also emit figures that must NOT change, so patching their savefig calls would have rescaled the lot.
# Keyed on the output basename, so every variant (png, the mirrored svg and the _ai_relink pdf) matches.
FONT_SCALE_FIGS = {
    "G1_violin2_mitotic_duration_journal":            dict(k=2.2, grow=1.5),
    "G1_violin2_mitotic_duration_journal_statgrid":   dict(k=2.2, grow=1.5, wrap_xticks=18),
    "G1_violin1_attempts_vs_duration":                dict(k=2.2, grow=1.5),
    "G1_violin_double_chromosome":                    dict(k=2.2, grow=1.6),
    "G2_dur_align_to_meta_journal":                   dict(k=2.2, grow=1.5),
    "G2_dur_ana_to_cyto_journal":                     dict(k=2.2, grow=1.5),
    "G4_exhaustion_violin_journal":                   dict(k=2.2, grow=1.55),
    "G5shape_circularity":                            dict(k=2.2, grow=1.5),
    "G7_prophase_vs_prometaphase_triple":             dict(k=2.2, grow=1.5),
    # USER 2026-08-11: the ZM figure WITH CONTROLS, at 2.5x.
    "G4_zm_full":                                     dict(k=2.5, grow=1.7),
    # USER 2026-08-11: ablation dose by cohort, 2.5x. 7 cohorts with long labels ("3 off-target
    # (control)", "ALL off-target (pooled)"), so wrap them tighter than the default.
    "ablation_count_by_cohort":                       dict(k=2.5, grow=1.5, wrap_xticks=14, wrap_title=62),

    # ── USER 2026-08-16: "make the font throughout bigger (except on timestrips)", clarified as "violin
    # plot, line plot, bar plot, etc etc text" — i.e. the text INSIDE the data plots. The mechanism already
    # existed from her 2026-08-11 request; only ELEVEN figures were ever enrolled, which is also why the
    # deck's typography was inconsistent (a few at 2.2x, the rest at the 11pt base). Enrolled below: every
    # DATA PLOT placed on META_FIGURES_20260814.ai, taken from the artboard dump. The 8 timestrips on that
    # deck (nf9_/nf10_/G5_mad1_timestrip/G9_drug_timestrip/G3_slippage_timestrip) are deliberately ABSENT —
    # their labels are drawn by the strip builders, not by matplotlib text artists.
    # `grow` makes room so the larger text does not collide (her 08-11 condition); figures that need
    # tighter wrapping get it individually after the render is inspected.
    "G1_area_combined_trendscaled":                    dict(k=2.2, grow=1.5),
    "G1_centroid_movement_combined_meta":              dict(k=2.2, grow=1.5),
    "G1_plate_rotation_combined_meta":                 dict(k=2.2, grow=1.5),
    "G1_roundness_combined_trendscaled":               dict(k=2.2, grow=1.5),
    "G2_kk_distance_by_phase":                         dict(k=2.2, grow=1.5),
    "G2_noc_washout_vs_prophase":                      dict(k=2.2, grow=1.5),
    "G2_trend_single_vs_triple":                       dict(k=2.2, grow=1.5),
    "G3_kt_fate":                                      dict(k=2.2, grow=1.5),
    "G3_lagging_by_creation_phase":                    dict(k=2.2, grow=1.5),
    "G3_length_vs_congression_time__p1":               dict(k=2.2, grow=1.5),
    "G4_lagging_bar":                                  dict(k=2.2, grow=1.5),
    "G4_prepost_intensity":                            dict(k=2.2, grow=1.5),
    "G4_zm_full__p1":                                  dict(k=2.2, grow=1.5),
    "G6_anaphase_kt_speed_single_vs_triple":           dict(k=2.2, grow=1.5),
    "G6_polar_distortion_vs_chromolen_1v3":            dict(k=2.2, grow=1.5),
    "G6_polar_equivalent_kk_single_vs_triple":         dict(k=2.2, grow=1.5),
    "G6_polepole_approx_absolute_time":                dict(k=2.2, grow=1.5),
    "G6tenM_equivalent_kk":                            dict(k=2.2, grow=1.5),
    "G6tenM_equivalent_kk_over_time":                  dict(k=2.2, grow=1.5),
    "G6tenM_polar_tension_timelines":                  dict(k=2.2, grow=1.5),
    "G6ten_withincell_over_time__p12":                 dict(k=2.2, grow=1.5),
    "G6ten_withincell_over_time__p15":                 dict(k=2.2, grow=1.5),
    "G6ten_withincell_over_time__p2":                  dict(k=2.2, grow=1.5),
    "G6ten_withincell_over_time__p3":                  dict(k=2.2, grow=1.5),
    "G6ten_withincell_over_time__p5":                  dict(k=2.2, grow=1.5),
    "G6ten_withincell_over_time__p9":                  dict(k=2.2, grow=1.5),
    "G7_prometa_single_vs_meta_triple__p1":            dict(k=2.2, grow=1.5),
    "G7_prometa_single_vs_meta_triple__p3":            dict(k=2.2, grow=1.5),
    "G7_prometa_single_vs_meta_triple__p4":            dict(k=2.2, grow=1.5),
    "G7_prophase_vs_prometaphase_triple__p1":          dict(k=2.2, grow=1.5),
    "collagen_vs_triple_2or3_ontarget_area_meta_to_ana": dict(k=2.2, grow=1.5),
    "collagen_vs_triple_2or3_ontarget_roundness_meta_to_ana": dict(k=2.2, grow=1.5),
    "kk_osc_about_plate":                              dict(k=2.2, grow=1.5),
    "kk_osc_model":                                    dict(k=2.2, grow=1.5),
}


def scale_fonts(fig, k=2.2, grow=1.45, wrap_xticks=22, pad=1.4, wrap_title=80):
    """Enlarge EVERY text in `fig` by k, and make room so nothing collides.

    USER 2026-08-11: "make the text ... about twice or 2.5 times the font size ... but at the same time
    making sure that when you increase the font size, the text doesnt overlap with other text, a plot
    object, an axes, etc."

    Why a post-build pass and not rcParams: the builders hard-code sizes in individual calls
    (fontsize=8 on the per-group N labels, FS_MAIN on strip labels, inset stat boxes), and rcParams only
    supplies DEFAULTS — anything passed explicitly ignores them. Walking the artists catches every one.

    `grow` < `k` on purpose. Growing the canvas by the same factor as the text would leave the text the
    same size RELATIVE to the plot, which is not what was asked; growing it less means the text really does
    read larger while still gaining absolute room. Long categorical ticks are wrapped rather than rotated
    so they stay horizontal and readable.
    """
    import textwrap
    # Wrap the TITLE too (2026-08-11). A long single-line title/subtitle is what actually sets the figure
    # width once bbox_inches="tight" is used: scaled 2.5x it measured ~2000pt, the canvas grew to fit it and
    # the axes were squeezed into the left third with the tick labels colliding. Wrapping the title first
    # keeps the width driven by the DATA, which is what `grow` is supposed to control.
    for ax in fig.get_axes():
        if not wrap_title:
            break
        # ax.get_title() defaults to loc="center". A title set with loc="left" lives in a DIFFERENT artist,
        # so the plain call returns "" and the wrap silently no-ops — which is exactly what happened here
        # (2026-08-11). Check all three positions. Setting .set_text() on the artist also preserves the
        # fontweight/size the builder chose, which set_title() would have reset.
        for _loc in ("center", "left", "right"):
            t = ax.get_title(loc=_loc)
            if not t:
                continue
            art = {"center": ax.title, "left": ax._left_title, "right": ax._right_title}[_loc]
            art.set_text("\n".join("\n".join(textwrap.wrap(ln, wrap_title)) if ln.strip() else ln
                                    for ln in t.split("\n")))
    st = getattr(fig, "_suptitle", None)
    if st is not None and wrap_title and st.get_text():
        st.set_text("\n".join("\n".join(textwrap.wrap(ln, wrap_title)) if ln.strip() else ln
                               for ln in st.get_text().split("\n")))
    for ax in fig.get_axes():
        if wrap_xticks:
            labs = [t.get_text() for t in ax.get_xticklabels()]
            if labs and any(len(l) > wrap_xticks for l in labs):
                ax.set_xticks(ax.get_xticks())
                ax.set_xticklabels(["\n".join(textwrap.wrap(l, wrap_xticks)) if l else l for l in labs])
    for t in fig.findobj(match=lambda o: hasattr(o, "get_fontsize") and hasattr(o, "get_text")):
        try:
            if t.get_text() == "": continue
            t.set_fontsize(t.get_fontsize() * k)
        except Exception:
            pass
    w, h = fig.get_size_inches()
    fig.set_size_inches(w * grow, h * grow)
    try:
        fig.tight_layout(pad=pad)
    except Exception:
        pass
    return fig


def apply_style():
    import matplotlib as mpl
    mpl.rcParams.update({
        "figure.dpi":150,"savefig.dpi":300,"figure.facecolor":"white","savefig.facecolor":"white",
        # 2026-08-17: ARIAL BEFORE HELVETICA, and it is not cosmetic. macOS
        # /System/Library/Fonts/Helvetica.ttc HAS NO U+2192 GLYPH, so every label containing "→" rendered as a
        # TOFU BOX (e.g. G3_length_by_behavior's "never congressed (polar→anaphase)"), with matplotlib warning
        # "Glyph 8594 (\N{RIGHTWARDS ARROW}) missing from font(s) Helvetica". `font.sans-serif` is a
        # FIRST-FOUND-WINS preference list, NOT a per-glyph fallback chain — matplotlib never reaches Arial or
        # DejaVu on its own, so listing them after Helvetica never helped. Arial DOES carry the glyph, is
        # metric-compatible with Helvetica (no layout shift) and is equally standard for journal figures.
        # 35 builders use "→" in labels, so this one line is the fix for all of them. Verified by rendering the
        # same string under both orders. Per-glyph fallback IS available, but only by passing a LIST to an
        # artist's fontfamily — it cannot be set globally here.
        "font.family":"sans-serif","font.sans-serif":["Arial","Helvetica","DejaVu Sans"],
        "font.size":11,"axes.titlesize":13,"axes.labelsize":12,"axes.linewidth":1.0,
        "axes.spines.top":False,"axes.spines.right":False,
        "xtick.direction":"out","ytick.direction":"out","xtick.major.size":4,"ytick.major.size":4,
        "legend.frameon":False,"axes.grid":False,"pdf.fonttype":42,"ps.fonttype":42,
        "svg.fonttype":"none",          # SVG keeps TEXT as editable text (Illustrator: change font/size/wording)
    })
    # Illustrator export: every PNG a matplotlib figure saves ALSO emits a vector .svg alongside it, into an
    # `illustrator/` subfolder mirroring the PNG path. SVG with svg.fonttype='none' opens in Illustrator with
    # every line/marker/label as a separate, fully-editable object (move, restyle, retype, add data) — as if
    # the figure were drawn natively in Illustrator. cv2 images (timestrips) are raster microscopy, not wrapped.
    from matplotlib.figure import Figure as _Fig
    if not getattr(_Fig.savefig, "_svgwrap", False):
        _orig=_Fig.savefig
        def _wrap(self, fname, *a, **k):
            # PERCELL=1 re-renders the RETIRED per-sample-line look. It must NEVER overwrite the live
            # figure, so every output name gains a `_percell` suffix -- that is the copy that goes to
            # "repeated figures 081726", and the live names keep the fit+SEM version. group1_roundness
            # applies the same suffix itself (it names its own files); doing it here covers every other
            # builder without touching any of them.
            try:
                if PERCELL_LINES and isinstance(fname,str) and fname.lower().endswith(".png") \
                        and "_percell" not in os.path.basename(fname):
                    fname=fname[:-4]+"_percell.png"
            except Exception: pass
            try:
                if isinstance(fname,str) and fname.lower().endswith(".png"):
                    _cfg=FONT_SCALE_FIGS.get(os.path.basename(fname)[:-4])
                    if _cfg and not getattr(self,"_fonts_scaled",False):
                        scale_fonts(self, **_cfg); self._fonts_scaled=True
            except Exception: pass
            r=_orig(self, fname, *a, **k)
            try:
                if isinstance(fname,str) and fname.lower().endswith(".png"):
                    _base=os.path.basename(fname)[:-4]
                    _k={kk:vv for kk,vv in k.items() if kk!="dpi"}
                    ad=os.path.join(os.path.dirname(fname),"illustrator"); os.makedirs(ad,exist_ok=True)
                    _orig(self, os.path.join(ad, _base+".svg"), *a, **_k)
                    # ALSO emit a matplotlib-native editable PDF (pdf.fonttype=42) straight into the folder the
                    # arranged/library .ai LINK to — so the .ai refresh their linked figures when opened, with NO
                    # Illustrator driving needed. Re-running any plot after feedback keeps its .ai figure current.
                    # FREEZE_DECK=1 (user 2026-08-05): re-run a builder to capture its statistics WITHOUT
                    # touching the PDFs the .ai files link, so nothing the decks display can move mid-process.
                    if not os.environ.get("FREEZE_DECK"):
                        _pl=stage_path(_PUB_DIR if PUB else "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf"); os.makedirs(_pl,exist_ok=True)
                        _orig(self, os.path.join(_pl, _base+".pdf"), *a, **_k)
            except Exception: pass
            return r
        _wrap._svgwrap=True; _Fig.savefig=_wrap
    # ── SD ERROR BARS ON EVERY VIOLIN, INCLUDING THE ~20 BUILDERS THAT CALL MATPLOTLIB DIRECTLY ──────
    # Patching each call site would have meant 20 edits in files that also draw figures which must not
    # change, and any new builder would start out non-compliant again. Wrapping the Axes method makes the
    # rule structural: a violin cannot be drawn in this project without its SD bar.
    from matplotlib.axes import Axes as _Axes
    if not getattr(_Axes.violinplot, "_sdwrap", False):
        _ovp=_Axes.violinplot
        def _vwrap(self, dataset, positions=None, *a, **k):
            r=_ovp(self, dataset, positions=positions, *a, **k)
            try:
                if SD_BARS:
                    ds=dataset if (isinstance(dataset,(list,tuple)) and len(dataset)
                                   and hasattr(dataset[0],"__len__")) else [dataset]
                    ps=list(positions) if positions is not None else list(range(len(ds)))
                    for _d,_p in zip(ds,ps): sd_bar(self,_d,_p)
            except Exception: pass
            return r
        _vwrap._sdwrap=True; _Axes.violinplot=_vwrap

LABEL={  # display labels (keys stay internal)
 "Collagen (2/3-sis on-target)":"collagen (2/3-sis)",
 "unModified":"unmodified",
 "1-Sister":"1-Sisterless","1-Sister Controls":"1-Sisterless\noff-target",
 "2-Sister":"2-Sisterless","2-Sister Controls":"2-Sisterless\noff-target",
 "3-Sister":"3-Sisterless","3-Sister Controls":"3-Sisterless\noff-target",
 "4-Sister":"4-Sisterless",
 "Double Chromosome":"Destruction of two\nkinetochores on\none chromosome",
 "Off-Target/Control":"All off-target"}
def lbl(k): return LABEL.get(k,k)

def sig_stars(p):
    """*** <.001, ** <.01, * <.05, else ns."""
    if p is None or (isinstance(p,float) and np.isnan(p)): return "–"
    return "***" if p<.001 else "**" if p<.01 else "*" if p<.05 else "ns"

def sig_cell(p,digits=2):
    """Cell text for a significance MATRIX: the stars AND the actual p-value on a second line.
    USER 2026-08-03: 'For all stats grids, in addition to * markings, list actual p-value' - a grid that shows
    only stars cannot be read back to a number, so every grid cell now carries both."""
    if p is None or (isinstance(p,float) and np.isnan(p)): return "–"
    return f"{sig_stars(p)}\np={p:.{digits}g}"
def mmss(minutes):
    s=int(round(minutes*60)); return f"{s//60}:{s%60:02d}"

# ---------- journal-standard violin BODY (reusable across every violin builder) ----------
# The DESIGN the user likes (jittered raw points, solid median, dashed/diamond mean, N labels, cohort
# colours) is drawn by each caller as before — this helper ONLY draws the shaded violin body, applying the
# four journal-spacing conventions UNIFORMLY so every violin in the deck matches. Toggle it on with the
# per-figure `journal=` flag each builder now takes; call it INSTEAD of ax.violinplot for the body.
# USER 2026-08-05: "i like the dot size used on the double-kinetochore ablation on ONE chromosome violin
# plot, use this dot size throughout on other violin plots of all types." That plot draws its jittered
# points at s=26. ONE constant so the next change is one edit, not 37.
#
# Dense violins (some carry >1000 points) would smear into a solid block at this size, so their overlay
# alpha is lowered instead of their size — the size is what she specified, the alpha is not.
VIOLIN_DOT_S = 26
VIOLIN_DOT_ALPHA_DENSE = 0.18     # applied where a violin's overlay was previously drawn at s<=8


# ── USER 2026-08-17: "Make sure that for error bars on violin and dot plots, SD is being used." ────────
# ONE implementation, called from every violin path, so no figure can drift back to SEM/CI/IQR:
#   * `violin_stats` (the median/mean marker helper most builders call),
#   * `journal_violin` (the shaded body helper), and
#   * a wrapper around `Axes.violinplot` itself, installed in apply_style(), which catches the ~20 builders
#     that call matplotlib directly and draw their own median.
# The bar is MEAN ± 1 SD (ddof=1) — the spread of the observations, which is what SD means; it is NOT
# rescaled by sqrt(n) anywhere. Drawn in a neutral dark grey rather than the cohort colour so it reads as
# an annotation over the body instead of a second data series, and so the wrapper (which runs before the
# builder has coloured anything) draws the same thing the explicit calls do.
# ── USER 2026-08-17: LINE PLOTS = FIT + SEM BAND, NOT ONE LINE PER SAMPLE ────────────────────────────
# "For all line plots that AREN'T individual sample line plots (where just one batch's data is plotted on
#  the line plot), ... instead of individually plotting every line for the individual samples, it should
#  just have the line of best fit and then a region of error shaded around it thats SEM."
# Shared so the ~8 builders that draw multi-sample line plots all express it the same way, and so the
# RETIRED per-cell look stays reproducible (PERCELL=1) instead of having to be recovered from a backup.
PERCELL_LINES = bool(os.environ.get("PERCELL"))

# ── PUB=1 : PUBLICATION COPY OF EVERY FIGURE (her, 2026-08-17) ──────────────────────────────────────
# "Make a version of the main figure and main supplemental figure ai files that dont have any of the
#  'extra words' - you know, like the titles for the figures, or explanation sentences beneath them, etc
#  etc, as these things are not commonly included in the figures published in literature (theyre included
#  in the legend instead). ... And in these versions, make x and y-axis labels extremely standardized."
#
# It has to happen in the GENERATOR, not on the deck: the titles and the explanation sentences are
# matplotlib text INSIDE each linked PDF, so no Illustrator pass can remove them without releasing the
# placed art. One hook covers every builder, and PUB output goes to a SEPARATE pdf library so the working
# decks are untouched.
#
# 🔴 INSTALLED AT IMPORT, NOT INSIDE apply_style(). Several builders (kk_osc_refined, the panel families,
# G5_lagging_*) never call apply_style and write their own PDF straight into `_ai_relink/pdf` — with the
# hook living in apply_style those simply had no publication twin, which is exactly the 27+61 figures the
# first two publication-deck passes could not relink. Installing on import catches every builder that
# imports lib, i.e. all of them, and the .pdf redirect below catches the ones that write the deck PDF
# themselves.
PUB = bool(os.environ.get("PUB"))

# ==================================================================================================
# DECK HALT -- she is working in the Illustrator files and must not be disturbed
# ==================================================================================================
# USER 2026-08-20: *"i need to open the adobe illustrator files and work on them undisturbed by your direct
# processes ... or by the popups that say a figure has been updated elsewhere and asking me if i want to
# update the version in whatever im working on."*
#
# TWO different things disturb her, and stopping only the obvious one is not enough:
#   1. anything that OPENS or SAVES a .ai (a JSX pass) -- that is a discipline rule, enforced by me, and it
#      is written into NOTES and memory so it survives a /clear.
#   2. RE-RENDERING A LINKED ASSET. Illustrator watches its links; overwriting `_ai_relink/pdf/<fig>.pdf`
#      while she has the deck open is precisely what raises "this file has been modified, update?". So while
#      the halt is on, NO figure may be written to a path any deck links to.
#
# So every figure output is redirected into a STAGING MIRROR of the same tree. Builders keep running, plots
# keep being made and verified, provenance (PLOT_SETTINGS / data CSVs) keeps updating -- only the linked
# assets are left untouched. `_claude_tools/deckhalt on|off|status`; on all-clear, `deckhalt promote` copies
# the staged files over the live ones in one pass and prints the placement queue.
HALT_FLAG = "/Volumes/4 MB/_claude_tmp/DECK_HALT"
_FIG_ROOT = "/Volumes/4 MB/ablation_figures_20260625"
_STAGE_ROOT = f"{_FIG_ROOT}/_ai_relink/_staging"


def deck_halted():
    """True while she is working in the .ai files. Read live, not cached: a long builder run must pick up a
    halt that was switched on after it started."""
    return os.path.exists(HALT_FLAG)


def stage_path(p):
    """Map an output path into the staging mirror while the halt is on; return it unchanged otherwise."""
    if not p or not deck_halted():
        return p
    p = str(p)
    if p.startswith(_STAGE_ROOT):
        return p
    if p.startswith(_FIG_ROOT):
        q = os.path.join(_STAGE_ROOT, os.path.relpath(p, _FIG_ROOT))
        os.makedirs(os.path.dirname(q), exist_ok=True)
        return q
    return p


_PUB_DIR = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf_pub"
_WORK_PDF = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf"
PUB_MAX_TEXT = 70      # characters; longer in-axes text is a sentence, not a data label

def _pub_short(s):
    """Trim an axis label or legend entry that has grown into a sentence, at the LAST natural delimiter
    before PUB_MAX_TEXT so the quantity (and its unit) survive and the commentary goes.
    Found by re-reading the publication PDFs: after titles and figure text were stripped, seven figures
    still read as prose because the sentence lived in the AXIS LABEL or the LEGEND rather than in a
    title. Nothing is lost -- the full wording stays in PLOT_SETTINGS.json for the legend."""
    if not s or len(s) <= PUB_MAX_TEXT: return s
    for d in (" — ", " - ", " · ", "; ", ": ", " ("):
        i = s.rfind(d, 0, PUB_MAX_TEXT)
        if i >= 12:
            out = s[:i].rstrip()
            # keep a trailing unit if the cut removed it, e.g. "... (µm)"
            m = re.search(r"\((?:µm|µm²|min|s|°|a\.u\.|µm/min)\)\s*$", s)
            if m and not out.endswith(m.group(0)): out = out + " " + m.group(0)
            return out
    return s[:PUB_MAX_TEXT].rstrip()

def _install_pub_hook():
    from matplotlib.figure import Figure as _Fig
    if getattr(_Fig.savefig, "_pubwrap", False): return
    _origp = _Fig.savefig
    def _pubwrap(self, fname, *a, **k):
        if PUB:
            try:
                if isinstance(fname, str):
                    low = fname.lower()
                    if low.endswith(".png"):
                        # keep the BASENAME (so the pub library maps 1:1 onto the working library) but
                        # redirect the PNG into a `_pub/` subfolder, so the working PNGs are never replaced
                        _d, _b = os.path.split(fname)
                        if os.path.basename(_d) != "_pub":
                            _d = os.path.join(_d, "_pub"); os.makedirs(_d, exist_ok=True)
                            fname = os.path.join(_d, _b)
                    elif low.endswith(".pdf") and os.path.dirname(os.path.abspath(fname)) in (_WORK_PDF, stage_path(_WORK_PDF)):
                        os.makedirs(stage_path(_PUB_DIR), exist_ok=True)
                        fname = os.path.join(stage_path(_PUB_DIR), os.path.basename(fname))
                    elif low.endswith(".svg"):
                        _d, _b = os.path.split(fname)
                        if os.path.basename(_d) != "_pub":
                            _d = os.path.join(_d, "_pub"); os.makedirs(_d, exist_ok=True)
                            fname = os.path.join(_d, _b)
            except Exception: pass
            try:
                pub_strip(self)
            except Exception: pass
            return _origp(self, fname, *a, **k)

        # ── NOT in PUB mode: emit BOTH renderings in this ONE call ──────────────────────────────
        # USER 2026-08-18: "there should not be any cases where the publication twin is missing or
        # stale, no reason for this to happen."  She is right, and the old design guaranteed drift:
        # PUB=1 REDIRECTED output, so every figure had to be built TWICE and the second run was easy
        # to forget.  Now the working PDF and its publication twin are written by the same savefig,
        # so a twin cannot be missing or older than its source.  The figure's text is snapshotted and
        # restored around the strip, because some builders keep drawing after savefig.
        _r = _origp(self, fname, *a, **k)
        try:
            if isinstance(fname, str) and fname.lower().endswith(".pdf") \
               and os.path.dirname(os.path.abspath(fname)) in (_WORK_PDF, stage_path(_WORK_PDF)):
                _snap = []
                for _t in self.findobj(match=lambda o: hasattr(o, "get_text") and hasattr(o, "set_text")):
                    try: _snap.append((_t, _t.get_text()))
                    except Exception: pass
                try:
                    pub_strip(self)
                    os.makedirs(stage_path(_PUB_DIR), exist_ok=True)
                    _origp(self, os.path.join(stage_path(_PUB_DIR), os.path.basename(fname)), *a, **k)
                finally:
                    for _t, _v in _snap:
                        try: _t.set_text(_v)
                        except Exception: pass
        except Exception: pass
        return _r
    _pubwrap._pubwrap = True
    _Fig.savefig = _pubwrap


def pub_strip(fig):
    """Apply the publication transform to a live figure: drop titles and figure-level explanation text,
    and rewrite axis labels, tick labels and legend entries through canon_labels. Exposed separately so the
    panel splitter (dataops/split_panels_20260809.py), which saves through a captured raw savefig, can
    apply exactly the same transform to each split-out panel."""
    if True:
            try:
                import canon_labels as _CL
                for _ax in fig.get_axes():
                    for _loc in ("center", "left", "right"):
                        try: _ax.set_title("", loc=_loc)
                        except Exception: pass
                    _ax.set_xlabel(_pub_short(_CL.canon_axis(_ax.get_xlabel())))
                    _ax.set_ylabel(_pub_short(_CL.canon_axis(_ax.get_ylabel())))
                    for _axis, _get in ((_ax.xaxis, _ax.get_xticklabels), (_ax.yaxis, _ax.get_yticklabels)):
                        _labs = [t.get_text() for t in _get()]
                        _new = [_CL.canon_group(l) for l in _labs]
                        # AN AXIS LABELLED "(min)" MUST HAVE MINUTE TICKS. Several figures carry an mm:ss
                        # tick formatter under a "(min)" label -- caught by LOOKING at the first publication
                        # render, not by the text scan, which sees both as fine on their own. Her rule is one
                        # time representation per quantity, so the ticks follow the label.
                        _lab = (_ax.get_xlabel() if _axis is _ax.xaxis else _ax.get_ylabel()) or ""
                        if "(min)" in _lab and any(re.match(r"^-?\d+:\d{2}$", l or "") for l in _new):
                            _conv = []
                            for l in _new:
                                m = re.match(r"^(-?)(\d+):(\d{2})$", l or "")
                                if m:
                                    _v = int(m.group(2)) + int(m.group(3)) / 60.0
                                    if m.group(1): _v = -_v
                                    # one decimal, and no trailing ".0" -- "1.41667" is not a tick label
                                    _conv.append(f"{_v:.1f}".rstrip("0").rstrip(".") or "0")
                                else: _conv.append(l)
                            _new = _conv
                        if _labs and _new != _labs:
                            if _axis is _ax.xaxis: _ax.set_xticks(_ax.get_xticks()); _ax.set_xticklabels(_new)
                            else: _ax.set_yticks(_ax.get_yticks()); _ax.set_yticklabels(_new)
                    # EVERY legend on the axes, not just ax.get_legend(). A second ax.legend() call
                    # REPLACES the current legend and the first one survives as a plain artist, so figures
                    # with a cohort legend AND a trend legend kept their long names until this was widened.
                    from matplotlib.legend import Legend as _Leg
                    _lgs = [c for c in _ax.get_children() if isinstance(c, _Leg)]
                    _cur = _ax.get_legend()
                    if _cur is not None and _cur not in _lgs: _lgs.append(_cur)
                    for _lg in _lgs:
                        for _t in _lg.get_texts(): _t.set_text(_pub_short(_CL.canon_group(_t.get_text())))
                        try:
                            _ti = _lg.get_title()
                            if _ti is not None and len(_ti.get_text()) > PUB_MAX_TEXT: _ti.set_text("")
                        except Exception: pass
                # matplotlib TABLES keep their text in cell artists, not in ax.texts -- the statgrids are
                # tables, so their cohort headers need their own pass.
                for _ax in fig.get_axes():
                    for _tb in list(getattr(_ax, "tables", [])):
                        try:
                            for _cell in _tb.get_celld().values():
                                _ct = _cell.get_text()
                                _cs = _ct.get_text()
                                if len(_cs) > PUB_MAX_TEXT: _ct.set_text("")
                                elif _CL.canon_group(_cs) != _cs: _ct.set_text(_CL.canon_group(_cs))
                        except Exception: pass
                try:
                    from matplotlib.legend import Legend as _Leg2
                    for _fl in list(getattr(fig, "legends", [])):
                        for _t in _fl.get_texts(): _t.set_text(_pub_short(_CL.canon_group(_t.get_text())))
                except Exception: pass
                if getattr(fig, "_suptitle", None) is not None: fig.suptitle("")
                # THE EXPLANATION SENTENCES COME IN TWO FLAVOURS and the first pass only caught one.
                # Figure-level text (fig.text) is always commentary -> blanked outright. But 37 figures
                # draw their inclusion notes, method notes and test statistics as AXES-level text instead
                # (ax.text), and those survived -- found by re-reading the publication PDFs, not assumed.
                # Rule: blank any text artist longer than PUB_MAX_TEXT characters, wherever it lives. Data
                # annotations on these figures are short (N counts, significance stars, "20250923
                # triple_ablation_collagen_2 · grp 1" is 43 characters); a sentence is not. Nothing is lost
                # -- every caption and every statistic stays in PLOT_SETTINGS.json and goes in the legend.
                for _t in list(fig.texts):
                    try: _t.set_text("")
                    except Exception: pass
                # A FACETED FIGURE PUTS ITS AXIS LABEL ON ONE PANEL ONLY, so asking each axes for its own
                # label missed the mm:ss annotations on every other panel. Decide once, per FIGURE.
                _figlab = " ".join(((a.get_xlabel() or "") + " " + (a.get_ylabel() or "")) for a in fig.get_axes())
                for _ax in fig.get_axes():
                    _xl = _figlab
                    for _t in list(getattr(_ax, "texts", [])):
                        try:
                            _s = _t.get_text()
                            if len(_s) > PUB_MAX_TEXT:
                                _t.set_text("")
                            elif _CL.canon_group(_s) != _s:
                                # a SHORT in-axes string that is a cohort name -- statistic-grid row and
                                # column headers are drawn this way, not as tick labels, so they kept the
                                # long names until this was added
                                _t.set_text(_CL.canon_group(_s))
                            elif "(min)" in _xl and re.search(r"\b\d+:\d{2}\b", _s or ""):
                                # mm:ss ANYWHERE in a short annotation on a minutes axis -- the dashed
                                # median-time labels are bare ("22:50"), but the violin summaries embed it
                                # ("mean 11:00", "med 10:00"). Convert every token, keep the wording.
                                _t.set_text(re.sub(r"\b(\d+):(\d{2})\b",
                                                   lambda m: f"{int(m.group(1)) + int(m.group(2))/60.0:.1f}",
                                                   _s))
                        except Exception: pass
            except Exception: pass
            # 🔴 HER 2026-08-21: the PUBLICATION render of `G6_anaphase_kt_speed_single_vs_triple` had its
            # y-axis label CLIPPED at both ends by the page edge -- "naphase kinetochore speed (µm/". The
            # working render (880x540) was fine; the publication twin (660x414) was not, and the deck links
            # the publication twin. Cause: the builder calls tight_layout() with its footnote present, then
            # pub_strip BLANKS that text and rewrites the labels -- so the saved figure is laid out for text
            # that is no longer there, and a long rotated y-label ends up outside the canvas. Re-run the
            # layout after the rewrite so the geometry matches the text that will actually be drawn.
            # Guarded: tight_layout raises on figures with incompatible axes (colorbars, manual add_axes),
            # and a failure here must never lose the figure.
            try:
                fig.tight_layout()
            except Exception:
                pass

try:
    _install_pub_hook()
except Exception:
    pass
def cell_line(ax, x, y, color, **kw):
    """Draw one sample's trace ONLY in PERCELL mode. Call this instead of ax.plot for per-sample spaghetti."""
    if PERCELL_LINES:
        ax.plot(x, y, color=color, **kw)

def binned_mean_sem(pts3, nb=8, lo=None, hi=None, minpts=3):
    """(bx, by, bsem) over `pts3` = [(x, y, sample_id), ...].
    SEM IS ACROSS SAMPLES, NOT ACROSS POINTS: a bin usually holds several points from the SAME cell, so
    pooling raw points would divide by the number of MEASUREMENTS and draw a band several times too narrow
    (the pseudoreplication this project already warns about on its own axes). Each sample is collapsed to
    its mean inside the bin first; n = number of SAMPLES in that bin. Bins with <2 samples get sem 0."""
    import numpy as _np
    if not pts3: return [], [], []
    x = _np.array([p[0] for p in pts3], float)
    y = _np.array([p[1] for p in pts3], float)
    c = _np.array([p[2] for p in pts3], object)
    ok = _np.isfinite(x) & _np.isfinite(y)
    x, y, c = x[ok], y[ok], c[ok]
    if x.size == 0: return [], [], []
    lo = float(_np.min(x)) if lo is None else lo
    hi = float(_np.max(x)) if hi is None else hi
    if hi <= lo: return [], [], []
    edges = _np.linspace(lo, hi, max(2, int(nb)) + 1)
    idx = _np.digitize(x, edges)
    bx, by, bs = [], [], []
    for k in range(1, len(edges)):
        m = idx == k
        if m.sum() < minpts: continue
        cs = {}
        for cc, vv in zip(c[m], y[m]): cs.setdefault(cc, []).append(vv)
        mm = _np.array([_np.mean(v) for v in cs.values()], float)
        bx.append(float(x[m].mean())); by.append(float(y[m].mean()))
        bs.append(float(mm.std(ddof=1) / _np.sqrt(mm.size)) if mm.size >= 2 else 0.0)
    return bx, by, bs

def fit_sem_band(ax, pts3, color, nb=8, lo=None, hi=None, lw=2.6, alpha=0.22, label=None, zorder=3):
    """Binned mean line + shaded +/- 1 SEM band. Returns (bx, by, bsem) so the caller can fit its axes."""
    bx, by, bs = binned_mean_sem(pts3, nb=nb, lo=lo, hi=hi)
    if not bx: return bx, by, bs
    if any(v > 0 for v in bs):
        ax.fill_between(bx, [v - e for v, e in zip(by, bs)], [v + e for v, e in zip(by, bs)],
                        color=color, alpha=alpha, lw=0, zorder=zorder - 1)
    ax.plot(bx, by, color=color, lw=lw, zorder=zorder, label=label)
    return bx, by, bs

SD_BAR_COLOR = "#333333"
SD_BARS = True                    # set False in a builder that must not get them
def sd_bar(ax, vals, pos, color=None, cap=0.10, lw=1.4, zorder=6):
    """Mean ± 1 SD error bar for one violin/dot column at x=`pos`. No-op for n<2."""
    import numpy as _np
    v = _np.asarray([x for x in vals if x is not None], float)
    v = v[_np.isfinite(v)]
    if v.size < 2: return
    m = float(v.mean()); s = float(v.std(ddof=1))
    if not _np.isfinite(s) or s <= 0: return
    # Most builders call BOTH ax.violinplot (wrapped) and violin_stats for the same column, so guard
    # against drawing the identical bar twice on one axes -- harmless visually, but it doubles the strokes
    # in the vector PDF and would confuse anyone editing the artwork in Illustrator.
    _seen = getattr(ax, "_sd_bars_drawn", None)
    if _seen is None: _seen = ax._sd_bars_drawn = set()
    _sig = (round(float(pos), 4), round(m, 6), round(s, 6))
    if _sig in _seen: return
    _seen.add(_sig)
    c = color or SD_BAR_COLOR
    ax.vlines(pos, m - s, m + s, color=c, lw=lw, zorder=zorder)
    ax.hlines([m - s, m + s], pos - cap, pos + cap, color=c, lw=lw, zorder=zorder)


def violin_stats(ax, vals, pos, color, half=0.32, show_mean=True):
    """Median (solid) and mean (dashed + hollow diamond) markers for one violin, drawn identically
    everywhere. USER 2026-08-05: "the above mentioned violin plot is missing mean lines ... so add this"."""
    import numpy as _np
    v = _np.asarray([x for x in vals if x is not None], float)
    if v.size == 0: return
    ax.hlines(_np.median(v), pos - half, pos + half, color=color, lw=2.4, zorder=4)
    if show_mean and v.size >= 2:
        ax.hlines(_np.mean(v), pos - half * 0.8, pos + half * 0.8, color=color, lw=1.3,
                  ls=(0, (2, 1.5)), zorder=4)
        ax.scatter([pos], [_np.mean(v)], marker="D", s=28, facecolor="white", edgecolor=color,
                   lw=1.2, zorder=5)
    if SD_BARS: sd_bar(ax, v, pos)          # her 2026-08-17 rule: violin/dot error bars are SD


def journal_violin(ax, vals, pos, color, width=0.8, min_n=6, alpha=0.30, lw=1.0, zorder=2):
    """Draw ONE journal-standard violin body at x=`pos`. Enforces, identically for every violin:
      1. scale='width' — the KDE is renormalised so EVERY violin has the same max half-width (`width`/2),
         regardless of N or spread (no density/area weighting, so no cohort renders 'fatter' than another).
      2. width=0.8     — the body occupies `width` of the 1.0 category slot, leaving a clean gap to neighbours.
      3. cut=0         — the KDE is evaluated ONLY within [min,max] of the data, so the violin is CAPPED at
         the extreme data points (no smoothed tails past the data; every violin ends flat at its last point).
      4. points-only for N<min_n — for N<`min_n` (default 6) NO body is drawn (a KDE on <6 points is
         meaningless and reviewers flag it); returns False so the caller shows just its jittered points +
         median tick. Also returns False for a degenerate (zero-spread) cohort.
    Returns True iff a body was drawn."""
    import numpy as _np
    d=_np.asarray([v for v in vals if v is not None],float); d=d[_np.isfinite(d)]
    if len(d)<min_n: return False
    lo,hi=float(d.min()),float(d.max())
    if hi<=lo: return False
    from scipy.stats import gaussian_kde
    try: kde=gaussian_kde(d)
    except Exception: return False
    ys=_np.linspace(lo,hi,256)                       # cut=0: support truncated at the data extremes
    dens=kde(ys); mx=float(dens.max())
    if mx<=0: return False
    dens=dens/mx*(width/2.0)                          # scale='width': identical max half-width everywhere
    ax.fill_betweenx(ys,pos-dens,pos+dens,facecolor=color,alpha=alpha,edgecolor=color,linewidth=lw,zorder=zorder)
    if SD_BARS: sd_bar(ax,d,pos)            # her 2026-08-17 rule: violin/dot error bars are SD
    return True

# ---- STANDARD intensity measurement (consistent across ALL plots) ----
# Total intensity SUM inside a radius-r CIRCLE (matches the annotation circle). Background is
# subtracted using the SAME-size circle on the cytosol marker (not a ratio). r=9 everywhere.
def disk_sum(gray, x, y, r=9):
    import numpy as _np, cv2 as _cv2
    if gray is None: return None
    h,w=gray.shape[:2]; m=_np.zeros((h,w),_np.uint8)
    _cv2.circle(m,(int(round(x)),int(round(y))),r,1,-1)
    sel=gray[m>0]
    return float(sel.sum()) if sel.size else None
SAT=60000   # 16-bit camera saturation level (max 65535); a KT disk touching this is CLIPPED = unquantifiable
def disk_max(gray, x, y, r=9):
    import numpy as _np, cv2 as _cv2
    if gray is None: return None
    h,w=gray.shape[:2]; m=_np.zeros((h,w),_np.uint8)
    _cv2.circle(m,(int(round(x)),int(round(y))),r,1,-1)
    sel=gray[m>0]
    return float(sel.max()) if sel.size else None
def is_saturated(gray, x, y, r=9, level=SAT):
    """True if the r-disk at (x,y) contains a saturated (clipped) pixel -> the intensity is unquantifiable.
    Real eYFP-Cdc20 KT disks peak ~3-15k (max observed ~95k); a saturated blob (laser-flash artifact, hot
    pixel, debris) clips at 65535 and gives absurd Σ (>1e6). Exclude such points symmetrically, never measure them."""
    mx=disk_max(gray,x,y,r)
    return mx is not None and mx>=level
def kt_intensity(gray, kx, ky, bgx, bgy, r=9):
    """Background-subtracted total intensity sum: KT disk Σ minus same-size cytosol disk Σ, FLOORED at 0.
    Fluorescence intensity cannot be physically negative (0 = no signal); a dim KT minus a brighter cytosol
    patch would otherwise give a meaningless negative value, so it is clamped to 0 ('no signal above bg')."""
    k=disk_sum(gray,kx,ky,r); b=disk_sum(gray,bgx,bgy,r)
    if k is None or b is None: return None
    return max(0.0, k-b)

_CIRCLE_MATCH=None
def circle_outline_match():
    """{circle_point_id: (x, y, outline_id)} — the CONSTRAINED circle->outline assignment produced by
    circle_outline_matching.py. Her rules (2026-07-28): same frame only, same kinetochore type only
    (polar/sisterless->polar, paired_kt->paired, lagging->lagging), ONE-TO-ONE within a frame, and a
    distance ceiling; a circle with no legitimate partner stays unmatched rather than being forced.
    The old greedy nearest-outline rule broke those constraints on 393 cross-type matches and 360
    double-claims, i.e. it really was snapping circles onto OTHER kinetochores."""
    global _CIRCLE_MATCH
    if _CIRCLE_MATCH is None:
        import csv as _csv
        _csv.field_size_limit(10**9)
        _CIRCLE_MATCH={}
        try:
            with open(f"{ANN}/CIRCLE_OUTLINE_MATCH_20260728.csv", newline="") as f:
                for r in _csv.DictReader(f):
                    if r["status"]=="matched" and r["snap_x"]:
                        _CIRCLE_MATCH[str(r["circle_id"]).strip()]=(
                            float(r["snap_x"]), float(r["snap_y"]), r["outline_id"])
        except FileNotFoundError:
            pass
    return _CIRCLE_MATCH


def polygon_centroid(P):
    """Centroid of the ENCLOSED AREA (shoelace) — the middle of the region the outline encloses.
    NOT the mean of the vertices, which is biased wherever vertices are unevenly spaced (hand-traced
    outlines always are, and multi-part lagging outlines badly so)."""
    import numpy as _np
    P=_np.asarray(P, float)
    x,y=P[:,0],P[:,1]; x2,y2=_np.roll(x,-1),_np.roll(y,-1)
    cr=x*y2-x2*y; Ar=cr.sum()/2.0
    if abs(Ar)<1e-9: return P.mean(0)
    return _np.array([((x+x2)*cr).sum()/(6*Ar), ((y+y2)*cr).sum()/(6*Ar)])


def kt_center(gray, x, y, point_id=None, rad=10):
    """RETIRED 2026-07-29 - NOT CALLED BY ANYTHING. Kept for reference only; do not add new callers
    without deciding the question below first.

    Built 2026-07-28 to implement the user's rule: place the measurement disk at the middle of the
    area her kt_outline encloses when one exists, and fall back to the image centroid when it does not.
    It was never wired in: every measurement script calls lib.snap_to_peak directly, so the exact
    outline branch has never run in production. Verified 2026-07-29 - zero callers across
    ablation_figures_20260625, dataops, kt_outline and _scratch.

    THE OPEN QUESTION it encodes: for a circle that HAS a traced outline, should the measurement sit
    at her traced centroid (exact, what this function does) or at the image-derived snap (consistent
    with the 77% of circles that have no outline)? Using this function makes 917 of 4054 measurements
    exact and the rest estimated; not using it keeps one method everywhere. That is a scientific
    choice, not a code cleanup.

    ORIGINAL DOCSTRING FOLLOWS. USER 2026-07-28:
    "the best way is to place the circle so that it is roughly at the middle of the enclosed area by the
    kt outline" — but ONLY when that outline is legitimately the same kinetochore.

    1. If this circle has a CONSTRAINED match to one of her manual outlines (same frame, same type,
       one-to-one, within the distance ceiling), return that outline's AREA CENTROID. Exact.
    2. Otherwise the circle marks a kinetochore she did not trace on that frame — fall back to the
       intensity-weighted centroid of the +/-rad image window.

    Never matches across frames, never across kinetochore types, never lets two circles share an outline.
    Returns (x, y, source) with source in {"outline", "image-centroid"}."""
    if point_id is not None:
        m = circle_outline_match().get(str(point_id).strip())
        if m:
            return m[0], m[1], "outline"
    sx, sy = snap_to_peak(gray, x, y, rad)
    return sx, sy, "image-centroid"


def snap_to_peak_pixel(gray, x, y, rad=9):
    """LEGACY brightest-pixel snap. Kept only for comparison — validated WORSE than the centroid snap
    (see snap_to_peak). Do not use for new work."""
    import numpy as _np
    if gray is None: return x,y
    h,w=gray.shape[:2]; xi,yi=int(round(x)),int(round(y))
    x0,x1=max(0,xi-rad),min(w,xi+rad+1); y0,y1=max(0,yi-rad),min(h,yi+rad+1)
    sub=gray[y0:y1, x0:x1]
    if sub.size==0: return x,y
    my,mx=_np.unravel_index(int(_np.argmax(sub)), sub.shape)
    return float(x0+mx), float(y0+my)


def snap_to_peak(gray, x, y, rad=10, sigma=1.5):
    """Recenter an intact-KT circle annotation onto the kinetochore, correcting ~4-6px click imprecision so
    the r-disk is centred on it. Returns the INTENSITY-WEIGHTED CENTROID of the +/-rad window, computed on
    a GAUSSIAN-SMOOTHED window after subtracting its 20th-percentile floor.

    THE SMOOTHING IS NOT COSMETIC - it is most of the accuracy. Measured 2026-07-29 against her manual
    kt_outlines on the 917 constrained circle/outline pairs (23 cells), scored to polygon_centroid with
    focus_excluded applied, at the corrected frame offset:
        rad  9, sigma 0.0  ->  3.00 px, 49.9% within 3px   <- the un-smoothed version used until now
        rad  9, sigma 1.0  ->  2.47 px, 60.6%              (2.22 px with robust_keep = handoff-7 section 10)
        rad 10, sigma 1.5  ->  2.21 px, 66.8%              <- THIS, and it reproduces section 2's 2.24/65.8%
        rad 11, sigma 1.0  ->  2.27 px, 65.6%
    2.21 px beats her own per-frame tracing jitter (2.88 px), which is the whole claim in handoff-7 section 2;
    the un-smoothed 3.00 px does NOT, and that discrepancy is what exposed the omission. Parameters match
    annotations/KT_CENTER_BEST_CONFIG.json (radius 10, sigma ~2, bg_pct 20) from the 7200-config search.

    Do NOT drop the smoothing to "simplify": without it every downstream intensity measurement is centred
    ~0.8 px worse and the within-3px rate falls 66.8% -> 49.9%.
    The legacy brightest-pixel version is snap_to_peak_pixel() - it is the right call ONLY for detection
    (is a punctum here), never for localisation; see screen_kt_placement.prominence.
    DO NOT use for cytosol_bg (background) or post_abl (the ablated site has no KT)."""
    import numpy as _np
    if gray is None: return x,y
    h,w=gray.shape[:2]; xi,yi=int(round(x)),int(round(y))
    x0,x1=max(0,xi-rad),min(w,xi+rad+1); y0,y1=max(0,yi-rad),min(h,yi+rad+1)
    sub=gray[y0:y1, x0:x1].astype(float)
    if sub.size==0: return x,y
    if sigma and sigma>0:
        try:
            from scipy.ndimage import gaussian_filter as _gf
            sub=_gf(sub, sigma)
        except Exception:
            pass
    sub=sub-_np.percentile(sub,20); sub[sub<0]=0
    if sub.sum()<=0: return x,y
    yy,xx=_np.mgrid[y0:y1, x0:x1]
    return float((xx*sub).sum()/sub.sum()), float((yy*sub).sum()/sub.sum())

def disk_local_bg(gray, x, y, r=5, gap=3, width=6, pct=40):
    """KT integrated intensity ABOVE the LOCAL background (the correct, floors-at-~0 method).
    = Σ(radius-r disk at x,y) − n_disk × local_bg, where local_bg = the pct-th percentile of a
    surrounding annulus [r+gap, r+gap+width] (a low percentile robustly rejects neighbouring bright
    KTs in the crowded metaphase plate). An empty/dim spot to disk≈background to result≈0; a real KT to >0.
    This replaces subtracting a DISTANT cytosol patch, which caused large spurious negatives because the
    cytosol's background level differed from the background right around each KT. Returns float or None."""
    import numpy as _np
    if gray is None: return None
    h,w=gray.shape[:2]; rr=int(np.ceil(r+gap+width))+1
    xi,yi=int(round(x)),int(round(y))
    x0,x1=max(0,xi-rr),min(w,xi+rr+1); y0,y1=max(0,yi-rr),min(h,yi+rr+1)
    if x1<=x0 or y1<=y0: return None
    sub=gray[y0:y1, x0:x1].astype(_np.float64)
    yy,xx=_np.ogrid[y0:y1, x0:x1]; d2=(xx-x)**2+(yy-y)**2
    disk=d2<=r*r; ann=(d2>(r+gap)**2)&(d2<=(r+gap+width)**2)
    if not disk.any() or not ann.any(): return None
    bg=_np.percentile(sub[ann], pct)
    return float(sub[disk].sum() - int(disk.sum())*bg)


def disk_fold_over_bg(gray, x, y, r=5, gap=3, width=6, pct=40):
    """KT intensity as a FOLD OVER the local background: Sum(disk) / (n_disk * local_bg).

    Same disk and same annulus as `disk_local_bg` -- this is that measurement expressed as a RATIO
    instead of a difference, which is the form her standing rule asks for ("fold over background").

    WHY IT MATTERS HERE (user 2026-08-20, board 1 item 3: "Make a version of this plot without the weird
    y-axis scale. Just use a linear scale for the y-axis"). Hec1 and Mad1 differ ~27x in raw a.u., so a
    single linear axis of BACKGROUND-SUBTRACTED counts squashes Mad1 onto the floor -- which is why that
    figure ended up with two independently min-max-calibrated axes, the "weird scale" she is objecting to.
    A fold is dimensionless: both fluorophores land on the same honest linear axis, 1.0 means "no brighter
    than its own local background", and no per-fluorophore rescaling is involved at all.

    Returns float, or None where the disk/annulus does not fit or the background is non-positive.
    """
    import numpy as _np
    if gray is None: return None
    h, w = gray.shape[:2]; rr = int(_np.ceil(r + gap + width)) + 1
    xi, yi = int(round(x)), int(round(y))
    x0, x1 = max(0, xi-rr), min(w, xi+rr+1); y0, y1 = max(0, yi-rr), min(h, yi+rr+1)
    if x1 <= x0 or y1 <= y0: return None
    sub = gray[y0:y1, x0:x1].astype(_np.float64)
    yy, xx = _np.ogrid[y0:y1, x0:x1]; d2 = (xx-x)**2 + (yy-y)**2
    disk = d2 <= r*r; ann = (d2 > (r+gap)**2) & (d2 <= (r+gap+width)**2)
    if not disk.any() or not ann.any(): return None
    bg = float(_np.percentile(sub[ann], pct))
    if bg <= 0: return None
    return float(sub[disk].sum() / (int(disk.sum()) * bg))

# ---- 16-bit fluorescence from the cropped TIF (the TRUE source of the 8-bit render) ----
# Measure fluorescence on <batch>_Fluor_Cropped.tif, NOT the MP4: the MP4 is an 8-bit
# contrast-stretched (fluor_contrast window) + H.264-compressed copy that clips bright KTs to 255
# and crushes dim ones to 0. The cropped TIF is the raw 16-bit plane, ROI-cropped — VERIFIED
# bit-for-bit identical to the raw OME-TIF page cropped to roi (maxabsdiff=0), and its pixel
# coordinates equal the rendered-movie/annotation coordinates exactly (same ROI crop, scale 1.0).
# Page index for a frame = frames.json fluor_tif_idx.
_FCROP_IDX=None
_FRAME_CALIB=None
_FRAME_CALIB_FIXED=None
FRAME_CALIB_CONVENTION="onebased_corrected_20260728"
def _frame_calib_is_fixed():
    """True when FRAME_CALIBRATION.csv was rebuilt with the 1-based movie read, i.e. its corrected_pos
    values are already true 0-based TIF pages. Legacy tables (no `convention` column) are one too high."""
    global _FRAME_CALIB_FIXED
    if _FRAME_CALIB_FIXED is None:
        _FRAME_CALIB_FIXED=False
        p="/Volumes/4 MB/annotations/FRAME_CALIBRATION.csv"
        if os.path.isfile(p):
            import csv as _csv
            try:
                r=next(iter(_csv.DictReader(open(p))),None)
                _FRAME_CALIB_FIXED = bool(r) and (r.get("convention")==FRAME_CALIB_CONVENTION)
            except Exception: pass
    return _FRAME_CALIB_FIXED

def _frame_calib():
    """ground-truth (batch,role,frame)->corrected TIF position, from FRAME_CALIBRATION.csv (built by
    build_frame_calibration.py via annotation-movie correlation). Empty dict if the file is absent."""
    global _FRAME_CALIB
    if _FRAME_CALIB is None:
        _FRAME_CALIB={}
        p="/Volumes/4 MB/annotations/FRAME_CALIBRATION.csv"
        if os.path.isfile(p):
            import csv as _csv
            for r in _csv.DictReader(open(p)):
                try: _FRAME_CALIB[(r["batch"],r["role"].lower(),int(r["frame"]))]=int(r["corrected_pos"])
                except (KeyError,ValueError): pass
    return _FRAME_CALIB

def _fcrop_index():
    global _FCROP_IDX
    if _FCROP_IDX is None:
        import glob as _g
        _FCROP_IDX={}
        for f in _g.glob("/Volumes/4 MB/**/*_Fluor_Cropped.tif",recursive=True):
            if "_pre_rerun_backup" in f or "_ARCHIVED" in f: continue
            _FCROP_IDX.setdefault(os.path.basename(f).replace("_Fluor_Cropped.tif",""),f)
    return _FCROP_IDX

class FluorTif:
    """16-bit ROI-cropped fluorescence stack for a batch. Coordinates == rendered-movie/annotation
    coordinates. Use .plane_at(t_sec) (nearest frame in time) or .plane_by_pos(i) (i-th role frame);
    measure with lib.disk_sum on the returned uint16 plane. Call .close() when done with a batch."""
    def __init__(self, batch, role=None, validate=True):
        import json as _j
        self.tif=None; self.ts=np.array([]); self._idx=[]; self._cache={}
        self.batch=batch; self.role=(role or "").lower()
        fp=_fcrop_index().get(batch)
        if not fp: return
        fj=fp.replace("_Fluor_Cropped.tif","_frames.json")
        if not os.path.isfile(fj): return
        _meta=_j.load(open(fj)); frames=_meta.get("frames",[])
        # CHANNEL GUARD: NEVER measure fluorescence in brightfield. Any FLUORESCENCE channel is allowed
        # (488/GFP, 561/mCherry, 640/Cy5, 405/DAPI, YFP, ...) — we measure different fluor channels over time —
        # but the channel must NOT be brightfield/phase/DIC/transmitted. (For the current eYFP-Cdc20 deck every
        # annotated batch's fluor_ch is 488/GFP; this guard future-proofs multi-channel work + catches swaps.)
        _BRIGHTFIELD=("brightfield","bright field","phase","dic","trans","widefield bf")
        _chn=_meta.get("ch_names") or []; _fc=_meta.get("fluor_ch")
        if _chn and _fc is not None and _fc<len(_chn):
            _fn=_chn[_fc].lower()
            if any(k in _fn for k in _BRIGHTFIELD) or _fn.strip() in ("bf",):
                log_review("brightfield_not_fluor",batch,_chn[_fc],"fluor_ch is a BRIGHTFIELD channel — EXCLUDED (never measure fluorescence in brightfield)")
                return
        else:   # no ch_names recorded: content check — a real fluor channel is dimmer than the brightfield crop
            _pcrop=fp.replace("_Fluor_Cropped.tif","_Phase_Cropped.tif")
            if os.path.isfile(_pcrop):
                try:
                    import tifffile as _tf0
                    _fm=float(_tf0.TiffFile(fp).pages[0].asarray().mean()); _pm=float(_tf0.TiffFile(_pcrop).pages[0].asarray().mean())
                    if _fm>_pm*1.3:   # "fluor" clearly brighter than brightfield => channels swapped
                        log_review("fluor_channel_swapped",batch,f"fluor {_fm:.0f} vs phase {_pm:.0f}","fluor crop brighter than brightfield — likely the wrong channel; EXCLUDED")
                        return
                except Exception: pass
        import tifffile as _tf
        tif=_tf.TiffFile(fp); npages=len(tif.pages)
        # page index into the cropped fluor stack:
        #  new schema: explicit fluor_tif_idx per frame.
        #  old schema: frame 'idx' + a constant leading offset = (npages - nframes). Some old renders are
        #  'synthesized' with extra leading pre-frames in the TIF that aren't in the frames list; the offset
        #  realigns them (validated vs the MP4 by correlation). offset<0 (fewer pages than frames) => can't map.
        new_schema=any('fluor_tif_idx' in f for f in frames)
        if new_schema:
            def _pg(f):
                v=f.get('fluor_tif_idx'); return v if v is not None else f.get('idx')
        else:
            off=npages-len(frames)
            if off<0: tif.close(); return
            def _pg(f):
                i=f.get('idx'); return None if i is None else i+off
        rows=sorted((f['t_sec'],_pg(f)) for f in frames
                    if (role is None or f['role']==role) and _pg(f) is not None)
        rows=[(t,p) for t,p in rows if 0<=p<npages]
        if not rows: tif.close(); return
        self.tif=tif; self.ts=np.array([r[0] for r in rows],float); self._idx=[r[1] for r in rows]
        # SAFETY: verify the cropped-TIF planes spatially match the role MP4 the annotations were placed on.
        # Refuse (ok()==False) if they don't — a mismatched/corrupt crop would silently corrupt measurements.
        # Sample several positions and take the BEST corr so a flash/early frame can't trigger a false reject.
        if validate and role is not None:
            mp4=fp.replace("_Fluor_Cropped.tif",f"_Fluor_{role.capitalize()}.mp4")
            if os.path.isfile(mp4):
                import cv2 as _cv
                cap=_cv.VideoCapture(mp4); nmp4=int(cap.get(7)); cors=[]
                for pos in sorted({0,len(self._idx)//2,max(0,len(self._idx)-1),min(2,len(self._idx)-1)}):
                    if pos>=nmp4: continue
                    cap.set(_cv.CAP_PROP_POS_FRAMES,pos); o,fr=cap.read()
                    if not o: continue
                    m=_cv.cvtColor(fr,_cv.COLOR_BGR2GRAY).astype(float); g=self._plane(self._idx[pos])
                    if g is None or g.shape!=m.shape: continue
                    ga=g.astype(float)
                    if ga.std()<1e-6 or m.std()<1e-6: continue
                    cors.append(abs(float(np.corrcoef(ga.ravel(),m.ravel())[0,1])))
                cap.release()
                if cors and max(cors)<0.4:
                    log_review("fluor_tif_mismatch",batch,f"max corr {max(cors):.2f} role={role}","cropped TIF does not match render MP4 — EXCLUDED from TIF measurement")
                    self.tif.close(); self.tif=None; self.ts=np.array([]); self._idx=[]; return
    def ok(self): return self.tif is not None and len(self.ts)>0
    def __len__(self): return len(self.ts)
    def _plane(self,pg):
        if pg is None or pg>=len(self.tif.pages): return None
        if pg not in self._cache: self._cache[pg]=self.tif.pages[pg].asarray()
        return self._cache[pg]
    def plane_at(self,t):
        if not self.ok(): return None
        return self._plane(self._idx[int(np.argmin(np.abs(self.ts-t)))])
    def plane_by_pos(self,i):
        if not self.ok() or i<0 or i>=len(self._idx): return None
        return self._plane(self._idx[i])
    def plane_by_frame(self,frame):
        """Return the plane for an ANNOTATION's `frame` field, via the calibrated TIF position (pos_of_frame).
        The annotation `frame`->TIF-position relationship is BATCH-DEPENDENT (some batches align by frame, a
        few by t_sec, some are off by 1-2 or even 31-55 frames). FRAME_CALIBRATION.csv stores the
        ground-truth position (found by correlating the real annotation-movie frame vs the TIF); when present
        we use it, else fall back to the raw frame index. Map fluorescence by THIS, never plane_at(t_sec)."""
        i=self.pos_of_frame(frame)
        return self._plane(self._idx[i]) if (i is not None and self.ok()) else None
    def pos_of_frame(self,frame):
        """Calibrated integer TIF position for an annotation frame (so callers can step fr0+k by position).
        Consults FRAME_CALIBRATION.csv (batch,role,frame -> corrected pos); falls back to the clamped frame."""
        try: i=int(round(float(frame)))
        except (TypeError,ValueError): return None
        if not self.ok(): return None
        # OFF-BY-ONE FIX (user 2026-07-28). The annotation tool writes ONE-BASED frame numbers -
        # make_annotation_html.py: `const f = Math.round(v.currentTime * fpsForVideo(v)) + 1;` - and
        # kt_outlines.csv duly starts at frame 1, never 0. This lookup treated them as ZERO-BASED
        # positions, so every fluorescence measurement was taken one plane LATE.
        # Measured on 917 circle/outline pairs across all 23 cells: centering error against her traced
        # outline was 5.33 px at the old offset and 2.24 px with the -1 correction, and ALL 23 cells
        # preferred -1 whether or not they had a FRAME_CALIBRATION row. She spotted this.
        # ORDER MATTERS. FRAME_CALIBRATION is keyed by the ORIGINAL annotation frame and its
        # `corrected_pos` is an ABSOLUTE TIF position, so it must be looked up BEFORE the -1 and used
        # as-is. Decrementing first (the first version of this fix) missed all 139 correcting rows and
        # could match a neighbouring frame's row instead.
        cal=_frame_calib().get((self.batch,self.role,i))
        if cal is not None:
            # A calibration row gives a TIF position, but in WHICH convention? The table shipped before
            # 2026-07-28 was built by reading the movie at cv2 index `frame` - itself one frame late,
            # because annotation frames are 1-based - so its positions are ONE TOO HIGH. Trusting them
            # as-is silently re-introduced the very bug this fix removes (measured: 4.22 px vs 2.24 px).
            # _frame_calib_is_fixed() reads the file's `convention` column so the code can tell.
            i = cal if _frame_calib_is_fixed() else (cal - 1 if cal > 0 else cal)
        else:
            i = i - 1 if i > 0 else i  # 1-based annotation frame -> 0-based TIF page
        return max(0,min(i,len(self._idx)-1))
    def t_at(self,i): return float(self.ts[i])
    def close(self):
        if self.tif is not None:
            try: self.tif.close()
            except Exception: pass
        self.tif=None; self._cache={}

PALETTE={  # consistent across all figures
 # USER 2026-08-16 (NOTES §1 rule 30, red-green colourblindness): "Off-Target/Control" was #d6604d (RED)
 # while "1-Sister" is #1b7837 (GREEN) — a red/green pair that appears together in every cohort figure on
 # the deck. Off-target moved to teal #00a0b0, which separates cleanly from both the greens and the
 # 2-Sister blue under deuteranopia and protanopia. The sisterless colours are deliberately UNCHANGED:
 # they carry meaning across the whole deck and repainting them would break every existing figure's key.
 "unModified":"#6e6e6e","1-Sister":"#1b7837","1-Sister Controls":"#a6dba0",
 "2-Sister":"#2166ac","2-Sister Controls":"#92c5de","3-Sister":"#762a83","3-Sister Controls":"#c2a5cf",
 "4-Sister":"#40004b","Double Chromosome":"#b35806","Off-Target/Control":"#00a0b0",
 # 2026-08-16: collagen split out of the 2-/3-Sister cohorts as its own line on the artboard-4 plots.
 # Amber is distinguishable from the greens/purples AND from grey under deuteranopia; it was previously
 # registered only inside group1_roundness, so any other consumer fell back to grey and collided with
 # "unModified".
 "Collagen (2/3-sis on-target)":"#e69f00"}


# ---- "it is not missing, it is on 2 MB" ------------------------------------------------------------
# USER 2026-07-22: when something that was archived to the 2 MB drive is looked for here, say WHERE IT
# WENT instead of reporting it as gone.  dataops/moved_index.py keeps the index; this is the hook every
# loader can call on a miss.
def moved_note(path):
    """Return a sentence naming the 2 MB location if `path` was archived, else ''. Never raises."""
    try:
        import importlib.util as _il
        _sp = _il.spec_from_file_location("_moved_index", "/Volumes/4 MB/dataops/moved_index.py")
        _m = _il.module_from_spec(_sp); _sp.loader.exec_module(_m)
        msg = _m.explain(path)
        return msg if msg.startswith("This is not missing") else ""
    except Exception:
        return ""


def require_path(path, what=""):
    """os.path check that explains an archived path instead of just failing."""
    import os as _os
    if _os.path.exists(path):
        return path
    note = moved_note(path)
    raise FileNotFoundError(note or f"{what or 'path'} not found: {path}")


# ── METAPHASE-ALIGNED TRENDLINES: a group's trend may not outrun that group's median metaphase ──────
# USER 2026-08-10: "any plot that has 'time from metaphase start' or similar on the x-axis, the trendline
# for a group cannot go past that group's median metaphase time."
#
# WHY IT MATTERS (and why the cap is PER GROUP, not global): past a group's median metaphase duration, more
# than half that group's cells have already entered anaphase and stopped contributing. The trend beyond that
# point is carried by a shrinking, self-selected subset -- the longest-metaphase cells -- so it reads as a
# real time-course when it is really a survivorship effect, and it drifts hardest exactly where it looks most
# interesting. Single- and triple-sisterless have DIFFERENT median durations (roughly 10 vs 23 min), so one
# shared cap would over-trim one group and under-trim the other.
#
# The DATA POINTS may still be drawn past the cap -- this limits the TREND (fit line, rolling mean, binned
# mean +/- SD envelope), which is the thing that implies "this is what the group does at time t".
def median_metaphase_minutes(batches):
    """Median metaphase duration (Metaphase Start -> Anaphase Onset) in MINUTES over `batches`.
    Returns None when no batch in the group carries both landmarks."""
    import numpy as _np
    d, _ = load_master()
    _mr = {r["Batch Name"]: r for r in d}
    durs = []
    for b in {str(x).strip() for x in batches if str(x).strip()}:
        r = _mr.get(b)
        if not r:
            continue
        ms = parse_time(r.get("Metaphase Start (s)", "")); an = parse_time(r.get("Anaphase Onset (s)", ""))
        if ms is not None and an is not None and an > ms:
            durs.append((an - ms) / 60.0)
    return float(_np.median(durs)) if durs else None


def trend_cap(batches, default=None):
    """The x-value a metaphase-aligned trend for THIS group must stop at. `default` when unknown."""
    m = median_metaphase_minutes(batches)
    return m if m is not None else default


def clip_trend(xs, ys, batches, cap=None):
    """Drop the part of a trend that runs past the group's median metaphase time.
    Returns (xs, ys, cap_used). Pass `cap` to reuse an already-computed value."""
    import numpy as _np
    cap = cap if cap is not None else trend_cap(batches)
    x = _np.asarray(xs, float); y = _np.asarray(ys, float)
    if cap is None:
        return x, y, None
    m = x <= cap
    return x[m], y[m], cap


def annotate_trend_cap(ax, cap, color="#888", label=None, y=None):
    """Mark where a group's trend stops, so the cap is visible rather than silently applied."""
    if cap is None:
        return
    ax.axvline(cap, ls=":", lw=1.0, color=color, alpha=.8, zorder=1)
    if label:
        ax.text(cap, (y if y is not None else ax.get_ylim()[1]), f" {label}",
                fontsize=6.5, color=color, va="top", ha="left", rotation=90)


# ---------------------------------------------------------------------------------------------------
# The outermost savefig hook: while the deck halt is on, EVERY figure destination under the figures tree
# is rewritten into the staging mirror. It is installed last so it runs FIRST, before the svg/pub wrappers
# compute any mirror path from the filename -- otherwise a staged PNG would still have dropped a live PDF
# next to her open document, which is the exact popup she asked to stop.
def _install_halt_redirect():
    from matplotlib.figure import Figure as _F
    if getattr(_F.savefig, "_haltwrap", False):
        return
    _inner = _F.savefig

    def _w(self, fname, *a, **k):
        try:
            if isinstance(fname, str):
                fname = stage_path(fname)
        except Exception:
            pass
        return _inner(self, fname, *a, **k)

    _w._haltwrap = True
    for _attr in ("_svgwrap", "_pubwrap"):
        if getattr(_inner, _attr, False):
            setattr(_w, _attr, True)
    _F.savefig = _w


_install_halt_redirect()
