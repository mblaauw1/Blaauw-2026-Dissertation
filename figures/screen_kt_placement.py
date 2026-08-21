"""Screen intact-KT annotations for MISPLACEMENT: a click that is supposed to sit on a kinetochore but has
NO kinetochore punctum within 9px (snap can't reach a real KT). Records each such annotation (batch, id,
label, frame, t_sec, x, y) to MISPLACED_KT_ANNOTATIONS.csv so it can be found+edited, and exports the id set
so the measurement scripts drop those points from analysis until fixed.
Screened labels (should show a KT): pre_abl, pre_abl_pair, post_abl_pair, polar, sisterless, paired_kt.
NOT screened: cytosol_bg (background), post_abl (the ablated site has no KT)."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, numpy as np
from collections import defaultdict
import lib
ANN="/Volumes/4 MB/annotations"
SCREEN_LABELS={"pre_abl","pre_abl_pair","post_abl_pair","polar","sisterless","paired_kt"}
SNAP_RAD=9            # the measurement's snap search radius (= the user's "within 9px of a KT peak")
# The user's criterion is SPATIAL: a click >9px from any KT peak. We snap within 9px and check whether the
# brightest pixel there is a genuine punctum. z-score is a WEAK discriminator on the crowded metaphase plate
# (neighbouring sister KTs inflate the window median/MAD and deflate z), so a real-but-dim KT can read z~3.
# => exclude only CLEARLY-empty clicks (very low z = flat cytoplasm, no KT). Record borderline ones for review.
Z_EXCLUDE=2.5        # below this the click sits on flat cytoplasm (no KT within 9px) -> dropped from analysis
Z_REVIEW=3.5         # 2.5-3.5 = borderline -> recorded in the CSV for the user to eyeball, but KEPT in analysis

rows=list(csv.reader(open(f"{ANN}/kt_points.csv"))); ix={c:i for i,c in enumerate(rows[0])}
# group annotations per batch so we open each fluor TIF once
byb=defaultdict(list)
for r in rows[1:]:
    lab=r[ix['label']].strip(); b=r[ix['batch']].strip()
    if lab not in SCREEN_LABELS or lib.is_mad1(b): continue
    try: byb[b].append((int(r[ix['id']]),lab,r[ix['frame']],float(r[ix['t_sec']]),float(r[ix['x']]),float(r[ix['y']])))
    except: pass

def prominence(g,x,y,rad=SNAP_RAD,win=20):
    """snap to the brightest pixel within rad; return (offset, modified-z of that peak vs a local window).
    high z => a real bright KT punctum is there; low z => flat cytoplasm (no KT within rad).

    MUST use snap_to_peak_pixel (BRIGHTEST PIXEL), not snap_to_peak. `peak` below is the pixel value AT
    the snapped point, which is only a peak if we snapped to the brightest pixel. lib.snap_to_peak is an
    intensity-weighted CENTROID (centre of mass, systematically dimmer than the peak); pointing this call
    at it deflated every z by ~6 units (median 8.65 -> 2.56), so the fixed Z_EXCLUDE=2.5 went from cutting
    a 0.5% tail to cutting 49.6% of all clicks.

    VALIDATED AGAINST GROUND TRUTH, not against the historical count: the 917 constrained circle/outline
    pairs are known-good clicks (each demonstrably sits on a kinetochore she traced), so a correct screen
    should exclude ~none of them. Brightest-pixel excludes 1 of 917 (0.1% false positive); the centroid
    variant excluded 262 of 917 (28.6%). Measured 2026-07-29.

    This call asks "is a bright punctum here" (DETECTION); the centroid answers "where is its centre"
    (LOCALISATION) and remains correct for measurement. Different questions, different snaps."""
    sx,sy=lib.snap_to_peak_pixel(g,x,y,rad); off=float(np.hypot(sx-x,sy-y))
    h,w=g.shape; x0,y0=max(0,int(sx)-win),max(0,int(sy)-win); sub=g[y0:min(h,int(sy)+win),x0:min(w,int(sx)+win)].astype(float)
    if sub.size<25: return off,None,sx,sy
    med=np.median(sub); mad=np.median(np.abs(sub-med)) or 1.0
    peak=float(g[int(round(sy)),int(round(sx))])
    z=0.6745*(peak-med)/mad
    return off,float(z),sx,sy

# label -> the movie/role the annotation's `frame` indexes (ablation vs monitoring)
ABL_LABELS={"pre_abl","pre_abl_pair","post_abl_pair"}
recs=[]; allz=[]; n=0   # recs: every click with z<Z_REVIEW (excluded + borderline)
for b in sorted(byb):
    ft=lib.FluorTif(b,'ablation')
    fm=lib.FluorTif(b,'monitoring')
    for (aid,lab,frame,t,x,y) in byb[b]:
        f=ft if lab in ABL_LABELS else fm
        if not f.ok(): f=fm if f is ft else ft        # fall back to the other role if needed
        if not f.ok(): continue
        g=f.plane_by_frame(frame)                      # map by FRAME (ground-truth), not t_sec (shifted 1-2 frames)
        if g is None: continue
        off,z,sx,sy=prominence(g,x,y)
        if z is None: continue
        n+=1; allz.append(z)
        if z<Z_REVIEW:
            excl = z<Z_EXCLUDE
            recs.append([b,aid,lab,frame,round(t,2),round(x,1),round(y,1),round(off,1),round(z,2),excl])
    ft.close(); fm.close()

allz=np.array(allz)
recs.sort(key=lambda m:m[8])                      # worst (lowest z) first
excluded=[m for m in recs if m[9]]
# threshold-sensitivity sweep so the cutoff is transparent
print(f"=== KT placement screen: {n} intact-KT annotations checked ===")
print(f"peak modified-z: p1={np.percentile(allz,1):.1f} p5={np.percentile(allz,5):.1f} p10={np.percentile(allz,10):.1f} median={np.median(allz):.1f} p95={np.percentile(allz,95):.1f}")
print("threshold sweep (clicks flagged at each z floor):")
for thr in (2.0,2.5,3.0,3.5):
    print(f"   z<{thr}: {int((allz<thr).sum())}  ({100*float((allz<thr).mean()):.1f}%)")
# write the record (excluded + borderline-for-review)
with open(f"{ANN}/MISPLACED_KT_ANNOTATIONS.csv","w",newline="") as f:
    w=csv.writer(f); w.writerow(["batch","annotation_id","label","frame","t_sec","x","y","snap_offset_px","peak_modified_z","status","note"])
    for m in recs:
        st="EXCLUDED" if m[9] else "review"
        note=("no KT punctum within 9px — fix this annotation, then it re-enters analysis" if m[9]
              else "borderline (dim/crowded) — KEPT in analysis; eyeball if convenient")
        w.writerow(m[:9]+[st,note])
# export ONLY the excluded id set (measurement scripts read this)
with open(f"{ANN}/MISPLACED_KT_IDS.txt","w") as f:
    f.write("\n".join(str(m[1]) for m in excluded))
print(f"EXCLUDED (z<{Z_EXCLUDE}, no KT within 9px): {len(excluded)}  | borderline-for-review (z<{Z_REVIEW}): {len(recs)-len(excluded)}")
print(f"-> {ANN}/MISPLACED_KT_ANNOTATIONS.csv  (+ MISPLACED_KT_IDS.txt = excluded only)")
for m in excluded[:15]: print(f"   EXCL {m[0]}  id={m[1]}  {m[2]}  frame {m[3]}  ({m[5]},{m[6]})  off {m[7]}px  z={m[8]}")
print("SCREEN_DONE")
