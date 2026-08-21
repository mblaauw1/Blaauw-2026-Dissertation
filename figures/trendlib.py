#!/usr/bin/env python3
"""Shared trend + SEM-band maths for the artboard-4 line-plot family.

Lifted verbatim out of `group1_roundness.py` on 2026-08-19 so that the DELTA siblings
(`custom_delta_axis_variants_20260816.py`) draw the identical band, from the identical binning, instead of
their own ad-hoc median-of-bin line. Her 2026-08-19 figure item 5 is exactly that mismatch:
"these plots dont have error region as other plots do".
"""
import numpy as np

def trend_to_mean_sem(pts3,md,nb=None,minpts=3,start=0.0):
    """As trend_to_mean, but pts3 = [(t, v, cell_id), ...] and it also returns the per-bin SEM over cells.
    Returns (bx, by, bsem); bsem entries are 0.0 where a bin holds fewer than 2 cells."""
    if md is None or md<=start: return [],[],[]
    if nb is None:
        TARGET_BIN_MIN=4.0
        nb=int(np.clip(round((md-start)/TARGET_BIN_MIN),3,9))+1
    a=sorted(pts3, key=lambda q:q[0])
    t=np.array([q[0] for q in a],float); y=np.array([q[1] for q in a],float)
    cid=np.array([q[2] for q in a],object)
    bins=np.linspace(start,md,nb)
    # 🔴 HER 2026-08-19, board 4 item 5: *"On the plots that include collagen cell roundness ... its nearly
    # horizontal now, unlike when it was plotted in its last modification iteration"*. She was right, and it
    # was this binning. EQUAL-WIDTH bins over a SPARSE cohort leave some bins under `minpts`, and those bins
    # are dropped -- for the 7 collagen cells (37 rows over 0-13 min) the 5-10 min bin held 2 points and was
    # discarded, leaving only the two LOW bins, so the line was drawn flat at ~0.01. The cohort's own median
    # delta at t>=10 min is +0.1455, HIGHER than 3-sisterless's +0.1100: the flatness was an artefact of
    # which bins survived, not of the cells.
    #
    # So: if equal-width binning would discard a third or more of the bins, re-cut the SAME data on
    # equal-COUNT (quantile) edges instead. Every bin then clears `minpts` by construction, nothing is
    # dropped, and no bin's membership changes for a cohort that was already dense enough -- dense series
    # take the original path untouched.
    _idx0=np.digitize(t,bins)
    _kept=sum(1 for k in range(1,len(bins)) if (_idx0==k).sum()>=minpts)
    # Trigger whenever ANY bin would be discarded and there are enough points to fill every bin instead.
    # (A "two-thirds" threshold was too lax: collagen kept 2 of 3 bins, which is exactly two-thirds, so the
    # fallback never fired and the line stayed flat.)
    if len(bins)>2 and _kept < (len(bins)-1) and t.size >= minpts*(len(bins)-1):
        _q=np.linspace(0.0,1.0,nb)
        bins=np.unique(np.quantile(t,_q))
        if bins.size < 2: bins=np.linspace(start,md,nb)
    idx=np.digitize(t,bins); bx=[];by=[];bs=[]
    def _sem(mask):
        cs={}
        for c,v in zip(cid[mask],y[mask]): cs.setdefault(c,[]).append(v)
        mm=np.array([np.mean(v) for v in cs.values()],float)
        return float(mm.std(ddof=1)/np.sqrt(mm.size)) if mm.size>=2 else 0.0
    for k in range(1,len(bins)):
        m=idx==k
        if m.sum()>=minpts:
            bx.append(float(t[m].mean())); by.append(float(y[m].mean())); bs.append(_sem(m))
    if bx and bx[-1]<md-1e-6:
        mlast=(t>=bins[-2])&(t<=md+1e-6)
        if mlast.sum()>=1:
            bx.append(md); by.append(float(y[mlast].mean())); bs.append(_sem(mlast))
        else:
            bx.append(md); by.append(by[-1]); bs.append(bs[-1])
    return bx,by,bs

def sem_band(ax,bx,by,bs,col,alpha=0.22):
    """Shade +/- 1 SEM around a trend. Skips the band entirely if no bin had >=2 cells."""
    if not bx or not any(v>0 for v in bs): return
    lo=[v-e for v,e in zip(by,bs)]; hi=[v+e for v,e in zip(by,bs)]
    ax.fill_between(bx,lo,hi,color=col,alpha=alpha,lw=0,zorder=2)



def anchor_trend(bx, by, bs, x, value=None, at_start=True):
    """Extend a binned trend so it actually REACHES x (the alignment point) instead of starting or ending at
    the first/last BIN CENTRE, which sits half a bin away from it.

    USER 2026-08-19, figure item 5: "For these plots starting at metaphase onset, you must also make sure the
    trendline starts at t=0" (and, for the delta versions, "dont start at a y-value of 0 at metaphase start").

    `value=None` carries the nearest bin's own mean out to x -- an honest extension that asserts nothing new.
    `value=0.0` is used by the DELTA figures, where every trace is baselined on its own sample at x, so the
    group mean there is zero by construction. The SEM at the anchor is 0.0 either way: it is not an
    independent estimate, it is the same bin restated at its edge.
    """
    bx, by, bs = list(bx), list(by), list(bs)
    if not bx: return bx, by, bs
    if at_start:
        if bx[0] <= x + 1e-9: return bx, by, bs
        return [x] + bx, [(by[0] if value is None else value)] + by, [0.0] + bs
    if bx[-1] >= x - 1e-9: return bx, by, bs
    return bx + [x], by + [(by[-1] if value is None else value)], bs + [0.0]


def plate_rotation_trace(marks, smooth_k=3):
    """Plate rotation over time, in degrees, as NET |angle(t) - angle(t0)| on a smoothed angle series.

    🔴 REPLACES A CUMULATIVE ABSOLUTE SUM, WHICH WAS NOISE-DOMINATED (her 2026-08-20, board 4 item 3.2:
    *"something is wrong with how plate rotation is being quantified. From frame to frame its changing as much
    as 140 degrees but even just visually i can clearly see that its rotating maybe like 5 degrees from each
    frame to the next."*)

    SHE WAS RIGHT, AND THE NUMBERS SAY SO. On `20250901 triple_ablation_11` (142 plate marks): the median
    frame-to-frame step is **2.0 deg** -- exactly the few degrees she can see -- and the NET rotation across
    the whole movie is **7.9 deg**. The reported cumulative was **404 deg**, 51x the net. Summing |steps|
    RECTIFIES the annotation jitter: every measurement error adds positively and none cancels, so the metric
    grows without bound with the number of marks. Smoothing alone cannot rescue it (7-point still gives
    111 deg against a 7.9 deg signal) -- the quantity itself is not measurable at this annotation precision.

    WHY THIS STILL HONOURS HER EARLIER INSTRUCTION (2026-08-19: *"Cumulative plate rotation must be calculated
    by summing the ABSOLUTE values ... no measurements in that should be negative"*): the PURPOSE of that
    instruction was that the line must never go negative, which it had. |angle(t) - angle(t0)| is >= 0 by
    construction, so the line still cannot go negative -- it simply no longer integrates noise.

    Smoothing is a 3-point moving average, the convention she cites from the lab (Jon Kuhn's three-point
    smoothing), applied to the UNWRAPPED angle -- the plate is a LINE, so its orientation is defined mod 180
    and must be unwrapped before any averaging or a plate near 0/180 flips by ~180.

    marks: [(t, angle_deg_mod180), ...] sorted by t  ->  [(t, rotation_deg >= 0), ...]
    """
    import numpy as _np
    if len(marks) < 2:
        return [(t, 0.0) for t, _ in marks]
    ts = [t for t, _ in marks]
    ang = [a for _, a in marks]
    un = [ang[0]]
    for a in ang[1:]:
        un.append(un[-1] + ((a - un[-1] + 90.0) % 180.0 - 90.0))
    un = _np.array(un, float)
    if smooth_k > 1 and len(un) >= smooth_k:
        un = _np.convolve(un, _np.ones(smooth_k) / smooth_k, mode="same")
    net = _np.abs(un - un[0])
    return list(zip(ts, [float(x) for x in net]))
