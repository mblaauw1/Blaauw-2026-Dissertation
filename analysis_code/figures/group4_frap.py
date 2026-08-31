"""FRAP: recovery of eYFP-Cdc20 at the TARGETED kinetochore vs its (intact) SISTER
kinetochore after laser ablation, measured on the 16-bit FLUOR cropped TIF.

Per ablation event the annotator marks (kt_points.csv):
  pre_abl       — targeted KT (its location, on/just before the ablation frame)
  pre_abl_pair  — the sister kinetochore (intact partner) at the same frame
  cytosol_bg    — cytosol background point(s) (dense per-frame for the FRAP-tracked batches)

MEASUREMENT (C3): on the FLUOR TIF only, total intensity Σ inside a radius-R circular disk at the KT,
MINUS a same-size cytosol-disk Σ (background subtraction). R = 9 (lib.disk_sum default / annotation circle).

TIMING (C1): t=0 is the ABLATION (laser flash). The flash frame SATURATES the targeted disk and is
NEVER measured — it is located (brightest/saturated frame next to the marked frame) and skipped. The
first sample is the frame immediately BEFORE the flash (the pre-ablation baseline, t<0); sampling then
resumes AFTER the flash. Every sequence is aligned to its OWN flash so t=0 lines up across cells.

ARTIFACTS (C2): saturated/clipped disks (laser flash, hot pixels, a neighbouring ablation drifting
through) are dropped via lib.is_saturated; the recovery window is bounded by the NEXT ablation so its
flash can't spike this curve; frame->TIF-plane mapping uses the calibrated pos_of_frame, never t_sec.
"""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, json, os, math, re, difflib, numpy as np, matplotlib.pyplot as plt
from collections import defaultdict
import lib
lib.apply_style()

# ---- B-feedback: batches to DROP from the FRAP GROUP plot (huge ~120x / negative spikes = un-normalized
# artifacts).  Named off the Jun-26/27 individual contact sheet; resolved here to the CLOSEST real batch
# name (printed below) so a name drift can't silently fail.  The empirical spike filter still catches any
# other spike regardless of name. ----
FRAP_DROP_REQUESTS=["20250711 double_ablation_2","20251021 no_manipulation_0",
                    "20251030 metaphase_0","20250711 double_ablation_1"]
def _normname(s): return re.sub(r'[_\s]+',' ',(s or "").strip().lower())
def resolve_drops(requests,batches):
    """closest-batch-name match for each requested drop -> {request: (matched_batch, ratio)}."""
    keys={_normname(b):b for b in set(batches)}; out={}
    for q in requests:
        m=difflib.get_close_matches(_normname(q),list(keys),n=1,cutoff=0.0)
        if m: out[q]=(keys[m[0]],difflib.SequenceMatcher(None,_normname(q),m[0]).ratio())
        else: out[q]=(None,0.0)
    return out

# ---- B-feedback / task 4: USER-SPECIFIED combined FRAP plot (rec8 "slide 9").  The requested traces are
# referenced by version/row on the Jun-26 contact sheet (e.g. "0925 triple v0", "0711 double v0",
# "a ptk_yfpcdc20 up to 20s", "0711 double v3 one point").  Those families have SEVERAL batches each and
# v0/v3 = sequence index, so they are NOT uniquely identifiable without the Jun-26 contact-sheet ordering.
# FLAG: fill each tuple (batch, seq_idx, tmax_s_or_None, single_point_idx_or_None) once the ordering is in
# hand; the contact-sheet index CSV written below gives the current (row,col)->(batch,seq) map to do it.
# ITEM2 feedback: replaced with the EXACT requested set (rNcM refs from the FRAP contact-sheet index).
# (batch, seq, tmax_s_or_None, single_point_idx_or_None). Caps = "only until ~Ns".
# USER 2026-07-14: the EXACT curated FRAP pick-set for the combined plot AND the FRAP-vs-complete plot
# (Group A). Format (batch, seq, op) with op = None | ("keep_first",N) "through point N" |
# ("drop_pts",[i..]) "without points i..". Every curve is 2nd-point to 0 rescaled (second_zero) at display.
# FLAGGED batch names (verify): #5 "20250410 ptk_tfpcdc20_17" to "ptk_yfpcdc20_17" (tfp to yfp; may be a complete-
# ablation, not FRAP — will print NOT FOUND if so).
# #8 "20250935 triple_ablation_7" REMOVED 2026-07-29: 20250935 is not a valid date (month 09 has no day 35)
# and the user resolved this on 2026-07-14 — NOTES.md: "20250935 triple_ablation_7 = invalid date -> excluded".
# It was still in the list, so every run printed "FRAP-VS pick NOT FOUND (A)" and the vs-complete panel
# silently rendered with A=7 instead of 8. Do NOT guess a corrected date (0918/0925/1029 all exist).
USER_FRAP_PICKS=[
  ("20250402 ptk_yfpcdc20_2",0,None),
  ("20250826 test_ablation_2",0,("keep_first",6)),      # through point 6
  ("20251104 ablations_5",2,None),
  ("20251104 ablations_3",1,None),
  ("20250410 ptk_yfpcdc20_17",0,None),                  # de-typo'd from "tfp"; verify (may be complete-ablation)
  ("20250402 ptk_yfpcdc20_13",0,("drop_pts",[5,6,7])),  # without points 5,6,7
  ("20250826 test_ablation_8",1,("keep_first",5)),      # through point 5
]
FRAP_COMBINED_PICKS=USER_FRAP_PICKS
OUT="/Volumes/4 MB/ablation_figures_20260625/group4"; SCRIPT=__file__
OUT=os.environ.get("KT_SWEEP_OUT",OUT); os.makedirs(OUT,exist_ok=True)
CSV="/Volumes/4 MB/annotations/kt_points.csv"          # authoritative annotation source
R=int(os.environ.get("KT_R","9"))                       # KT + cytosol disk radius (lib.disk_sum default)
NREC=int(os.environ.get("FRAP_NREC","42"))              # recovery frames to sample (~120 s at ~3 s/frame)
TC="#d62728"; SC="#1f77b4"                              # targeted=red, sister=blue

# ---------------- load annotations ----------------
rows=list(csv.reader(open(CSV))); ix={c:i for i,c in enumerate(rows[0])}
mark=defaultdict(dict)   # batch -> frame -> {'tgt':(x,y), 'sis':(x,y)}
cyto=defaultdict(list)   # batch -> [(frame,x,y)]
for r in rows[1:]:
    b=r[ix['batch']].strip(); lab=r[ix['label']].strip()
    if lib.is_mad1(b): continue   # keep drug/Exclude in source so contactsheets can MARK them
    if lib.is_misplaced_id(r[ix['id']]): continue
    if r[ix['type']]!='kt_point': continue
    try: f=int(r[ix['frame']]); x=float(r[ix['x']]); y=float(r[ix['y']])
    except: continue
    if lab=='pre_abl': mark[b].setdefault(f,{})['tgt']=(x,y)
    elif lab=='pre_abl_pair': mark[b].setdefault(f,{})['sis']=(x,y)
    elif lab=='cytosol_bg': cyto[b].append((f,x,y))

def pixsize(batch):
    """pixel size (um/px) from the batch frames.json — flag the 0.031 (2x-zoom) batches."""
    fp=lib._fcrop_index().get(batch)
    if not fp: return None
    fj=fp.replace("_Fluor_Cropped.tif","_frames.json")
    if not os.path.isfile(fj): return None
    try: return float(json.load(open(fj)).get("pixel_size_um"))
    except Exception: return None

# ---------------- per-ablation measurement ----------------
allseq=[]   # (batch, seq_idx, T[], Tgt[], Sis[])  bg-subtracted sums, t relative to ablation
rec=[]      # CSV rows (frames identifiable for timestrips)
flagged_px=[]
for b in sorted(mark):
    if lib.excluded(b): continue   # 07-07 feedback: drop user-flagged outlier (e.g. two_sisterless_kinetochores_5 ~80min) from ALL plots
    if b not in cyto:
        lib.log_review("frap_no_cytosol",b,"","no cytosol_bg point — cannot background-subtract"); continue
    ps=pixsize(b)
    if ps is not None and abs(ps-0.031)<0.005:
        flagged_px.append((b,ps)); lib.log_review("frap_pixelsize_0p031",b,f"{ps:.3f}","2x-zoom batch (0.031 um/px) — fixed disk = different physical area; verify")
    ft=lib.FluorTif(b,'ablation')                  # 16-bit cropped fluor TIF (validated vs render MP4)
    if not ft.ok():
        lib.log_review("frap_no_tif",b,"","no/invalid ablation fluor TIF"); continue
    N=len(ft); ts=ft.ts
    iv=float(np.median(np.diff(ts))) if N>1 else 3.0
    # cytosol points -> calibrated TIF positions (per-frame where dense, single applied where sparse)
    cyto_pos=sorted((ft.pos_of_frame(cf),cx,cy) for cf,cx,cy in cyto[b] if ft.pos_of_frame(cf) is not None)
    pre=sorted(F for F,m in mark[b].items() if 'tgt' in m and 'sis' in m)
    for si,F in enumerate(pre):
        m=mark[b][F]; tx,ty=m['tgt']; sx,sy=m['sis']
        fr0=ft.pos_of_frame(F)
        if fr0 is None: continue
        # snap intact KTs onto their punctum ONCE, on a clean frame a couple before the flash
        gsnap=ft.plane_by_pos(max(0,fr0-2))
        if gsnap is None: gsnap=ft.plane_by_pos(fr0)
        if gsnap is None: continue
        txs,tys=lib.snap_to_peak(gsnap,tx,ty); sxs,sys=lib.snap_to_peak(gsnap,sx,sy)
        # ---- locate the FLASH frame near the marked frame (C1) ----
        win=[p for p in range(max(0,fr0-1),min(N,fr0+3))]
        dmx={p:(lib.disk_max(ft.plane_by_pos(p),txs,tys,R) or 0) for p in win}
        sat=[p for p in win if dmx[p]>=lib.SAT]
        if sat: fa=min(sat)
        else:
            pk=max(win,key=lambda p:dmx[p]); med=float(np.median(list(dmx.values()))) or 1.0
            fa=pk if dmx[pk]>1.5*med else fr0
        t0=ft.t_at(fa)
        # ---- pre-ablation baseline frame = first NON-saturated frame before the flash ----
        pre_fr=None
        for p in range(fa-1,max(-1,fa-4),-1):
            if p<0: break
            g=ft.plane_by_pos(p)
            if g is None: continue
            if lib.is_saturated(g,txs,tys,R): continue
            pre_fr=p; break
        # ---- recovery window: after the flash, bounded by the NEXT ablation (no next-flash spike) ----
        nxt=ft.pos_of_frame(pre[si+1]) if si+1<len(pre) else N
        positions=([pre_fr] if pre_fr is not None else [])+[p for p in range(fa+1,min(N,nxt,fa+1+NREC))]
        T=[];Tg=[];Si=[]
        for fr in positions:
            g=ft.plane_by_pos(fr)
            if g is None: continue
            if not cyto_pos: continue
            cpos,cx,cy=min(cyto_pos,key=lambda c:abs(c[0]-fr))
            # skip any clipped disk (flash residue / hot pixel / neighbouring ablation drifting through)
            if lib.is_saturated(g,txs,tys,R) or lib.is_saturated(g,sxs,sys,R) or lib.is_saturated(g,cx,cy,R): continue
            cval=lib.disk_sum(g,cx,cy,R)
            if cval is None: continue
            # Do NOT hard-clamp to 0: clamping made every bleached/near-background frame land at EXACTLY 0, which
            # drew a flat pinned-zero line and hid the true near-zero recovery scatter (user troubleshoot). Keep
            # the real cytosol-subtracted value (a bleached KT hovers just above/below background = small +/- noise);
            # gross spurious negatives are handled downstream (clipped-disk guard + the >8x normalization screens).
            tg=float(lib.disk_sum(g,txs,tys,R)-cval); ss=float(lib.disk_sum(g,sxs,sys,R)-cval)
            rt=ft.t_at(fr)-t0
            T.append(rt); Tg.append(tg); Si.append(ss)
            if not lib.plot_excluded(b):
                rec.append([b,si,F,fa,fr,1 if (pre_fr is not None and fr==pre_fr) else 0,
                        round(rt,1),round(tg,1),round(ss,1)])
        if len(T)>=2: allseq.append((b,si,T,Tg,Si))
    ft.close()

# ---------------- normalization ----------------
# The measurement (above, in the CSV) is the cytosol-disk-subtracted Σ (C3). For DISPLAY we normalize the
# targeted KT to its intact SISTER kinetochore at the same time point. The sister is the internal reference:
# it cancels whole-field PHOTOBLEACHING (both KTs bleach together), which a same-frame cytosol SUBTRACTION
# cannot remove (it is additive, bleaching is multiplicative). With the sister as reference (=1, flat), the
# targeted curve shows the expected biology: DIP right after ablation, then RECOVERY as eYFP-Cdc20 returns.
def ratio_series(T,Tg,Si):
    """Per-sequence targeted/sister, normalized so the pre-ablation (t<0) ratio = 1.
    Frames where the sister disk is too dim/noisy (< 15% of its pre-ablation level) are dropped so the
    ratio stays stable. Returns (t[], targeted_over_sister[]) or None."""
    T=np.array(T,float); Tg=np.array(Tg,float); Si=np.array(Si,float)
    o=np.argsort(T); T,Tg,Si=T[o],Tg[o],Si[o]
    preT=Tg[T<0]; preS=Si[T<0]
    tb=np.mean(preT[preT>0]) if (preT>0).any() else None
    sb=np.mean(preS[preS>0]) if (preS>0).any() else None
    if not tb or not sb or tb<=0 or sb<=0: return None
    q0=tb/sb; keep=Si>0.15*sb
    if keep.sum()<2: return None
    return T[keep],(Tg[keep]/Si[keep])/q0

def start_norm(Tk,Q):
    """B-feedback task 1: force a curve's STARTING (earliest-time) value to exactly 1.
    Tk,Q are time-sorted (ratio_series sorts by T). Returns (Tk, Q/Q[0]) or None if the start is non-finite/0."""
    Q=np.asarray(Q,float)
    if Q.size==0 or not np.isfinite(Q[0]) or Q[0]==0: return None
    return Tk, Q/Q[0]

def second_zero(Tk,Q):
    """USER 2026-07-14: re-baseline a FRAP recovery curve so the LOWEST point (the post-bleach minimum, which
    for a clean curve IS the 2nd point) -> 0 and the PRE-ablation point (index 0) -> 1, all others linearly:
    Qn = (Q - Qmin) / (Q[0] - Qmin).  Recovery then climbs 0 -> 1. Anchoring on the MINIMUM (not literally
    index 1) guarantees the lowest point sits at 0 with no spurious negatives when a noisy curve's true dip
    isn't exactly the 2nd sample. Returns (Tk, Qn) or None (<2 pts / degenerate pre-vs-min gap)."""
    Tk=np.asarray(Tk,float); Q=np.asarray(Q,float)
    if Q.size<2 or not np.isfinite(Q[0]): return None
    Qmin=np.nanmin(Q)
    if not np.isfinite(Qmin) or (Q[0]-Qmin)==0: return None
    return Tk,(Q-Qmin)/(Q[0]-Qmin)

_FIRSTPOST_NEG = []   # (batch, seq, n_negative_points) so the record can state exactly what was clamped

def first_post_zero(Tk,Q):
    """USER 2026-08-05: "make sure that all of the lines are scaled such that at timepoint following that
    first timepoint before 0 has intensity of 0".

    second_zero() anchored 0 on the curve's global MINIMUM, which is the 2nd point only for a clean curve.
    Two picks had their minimum later than the first post-ablation sample, so they started their recovery
    at 0.516 (20250402 ptk_yfpcdc20_13 #0) and 0.753 (20250826 test_ablation_2 #0) instead of 0.

    Anchor explicitly on the FIRST post-ablation point instead: Qn = (Q - v0) / (Q[0] - v0), so the
    pre-ablation point stays 1 and the first point after t=0 becomes exactly 0. A curve whose true minimum
    comes later will now dip below 0 there; those points are clamped to 0 and counted, matching the
    convention on the sibling figure ("if there is a negative readout ... just put it at 0")."""
    Tk=np.asarray(Tk,float); Q=np.asarray(Q,float)
    if Q.size<2 or not np.isfinite(Q[0]): return None
    post=np.where(Tk>0)[0]
    if post.size==0: return None
    v0=float(Q[post[0]]); den=float(Q[0])-v0
    if not np.isfinite(den) or abs(den)<1e-9: return None
    Qn=(Q-v0)/den
    nneg=int((Qn<0).sum())
    return Tk,np.clip(Qn,0,None),nneg

def _apply_op(Tk,Q,op):
    """Per-pick point operation on a time-sorted trace (1-indexed 'plotted point' language, matching the user's
    'through point N' / 'without points 5,6,7'). op=None -> unchanged; ('keep_first',N) -> keep points 1..N;
    ('drop_pts',[i,...]) -> drop those 1-indexed points. Defined here (early) so BOTH the combined FRAP plot
    and the FRAP-vs-complete plot can share it."""
    Tk=np.asarray(Tk,float); Q=np.asarray(Q,float)
    if op is None: return Tk,Q
    kind,val=op
    if kind=="drop_pts":
        idx=[i-1 for i in val if 0<i<=Tk.size]            # 1-indexed plotted points -> 0-indexed
        keep=np.array([i for i in range(Tk.size) if i not in idx])
        return Tk[keep],Q[keep]
    if kind=="keep_first":
        return Tk[:val],Q[:val]
    return Tk,Q

# ---------------- individual per-ablation plots + contact sheet (C4) ----------------
import glob as _glob
IND=f"{OUT}/frap_individual"; os.makedirs(IND,exist_ok=True)
for _f in _glob.glob(f"{IND}/frap_*.png")+_glob.glob(f"{IND}/illustrator/frap_*.svg"): os.remove(_f)  # drop stale runs
NCOL=4
nrows=math.ceil(len(allseq)/NCOL) if allseq else 1
figG,axG=plt.subplots(nrows,NCOL,figsize=(16,3.2*nrows),squeeze=False)
nind=0; cs_index=[]   # (k,row,col,batch,seq) -> contact-sheet ordering for row/col cross-reference
for k,(b,si,T,Tg,Si) in enumerate(allseq):
    rs=ratio_series(T,Tg,Si)
    snk=start_norm(*rs) if rs is not None else None     # task 1: each individual curve STARTS at 1
    fI,aI=plt.subplots(figsize=(4,3))
    if snk is not None:
        Tk,Q=snk; aI.plot(Tk,Q,color=TC,marker="o",ms=4,label="targeted / sister")
    aI.axhline(1,color=SC,lw=1.2,ls="-",label="sister (reference)")
    aI.axvline(0,color="#333",ls=":",lw=1)
    aI.set_xlabel("time from ablation (s)"); aI.set_ylabel("targeted KT eYFP / sister (start=1)")
    aI.legend(fontsize=7); lib.mark_excluded_ax(aI,b,f"{b} #{si}",fontsize=8)
    fI.tight_layout(); fI.savefig(f"{IND}/frap_{k:03d}_{b.replace(' ','_')}_{si}.png",bbox_inches="tight"); plt.close(fI); nind+=1
    rr,cc=k//NCOL,k%NCOL; cs_index.append((k,rr+1,cc+1,b,si))
    a=axG[rr][cc]
    if snk is not None: a.plot(snk[0],snk[1],color=TC,marker="o",ms=3)
    a.axhline(1,color=SC,lw=.8); a.axvline(0,color="#333",ls=":",lw=.8)
    lib.mark_excluded_ax(a,b,f"r{rr+1}c{cc+1} {b} #{si}",fontsize=4.5); a.tick_params(labelsize=6)
for k in range(len(allseq),nrows*NCOL): axG[k//NCOL][k%NCOL].axis("off")
with open(f"{OUT}/G4_frap_contactsheet_index.csv","w",newline="") as _f:
    _w=csv.writer(_f); _w.writerow(["k","row","col","batch","seq"]); _w.writerows(cs_index)
figG.suptitle("FRAP — individual ablations: targeted KT / sister (red), sister reference=1 (blue) — pick samples",x=.01,ha="left",fontweight="bold")
figG.tight_layout(); figG.savefig(f"{OUT}/G4_frap_individual_contactsheet.png",bbox_inches="tight"); plt.close(figG)
print(f"FRAP individual plots: {nind} in {IND}")

# ---------------- aggregate: dip-then-recover (targeted relative to flat sister reference) ----------------
# Resolve the requested drop list to real batch names (closest match) and exclude them from the group plot.
_drops=resolve_drops(FRAP_DROP_REQUESTS,[s[0] for s in allseq])
FRAP_DROP_BATCHES=set()
print("FRAP requested group-plot drops (closest-batch-name match):")
for q,(mb,rt) in _drops.items():
    print(f"  '{q}' -> {mb!r} (match {rt:.2f})")
    if mb:
        FRAP_DROP_BATCHES.add(mb)
        lib.log_review("frap_requested_drop",mb,f"req='{q}'","user-flagged ~120x/negative spike — excluded from FRAP group plot (closest-name match)")
fig,ax=plt.subplots(figsize=(8.5,5.4))
allT=[]; allQ=[]; nused=0
for b,si,T,Tg,Si in allseq:
    if b in FRAP_DROP_BATCHES or lib.plot_excluded(b): continue    # spike + drug/Exclude (shown+MARKED on contactsheet only)
    rs=ratio_series(T,Tg,Si)
    if rs is None: continue
    Tk,Q=rs
    if np.max(np.abs(Q))>8:                                # residual spike wrecks the scale -> drop + log
        lib.log_review("frap_spike_excluded",b,f"seq {si}",">8x targeted/sister spike — excluded from aggregate"); continue
    ax.plot(Tk,Q,color=TC,alpha=.15,lw=.7)
    for t,q in zip(Tk,Q): allT.append(t); allQ.append(q)
    nused+=1
allT=np.array(allT); allQ=np.array(allQ)
bins=np.arange(-6,126,6); bc=[]; mq=[]
for lo in bins:
    mmask=(allT>=lo)&(allT<lo+6)
    if mmask.sum()>=3: bc.append(lo+3); mq.append(np.median(allQ[mmask]))
ax.plot(bc,mq,color=TC,lw=3,marker="o",ms=6,label="targeted / sister (median)",zorder=5)
ax.axhline(1,color=SC,lw=2.0,label="sister kinetochore (intact reference)",zorder=4)
ax.axvline(0,color="#333",ls=":",lw=1)
ax.text(1.0,ax.get_ylim()[1]*.98,"ablation",rotation=90,va="top",fontsize=7,color="#333")
ax.legend(fontsize=9,loc="lower right")
ax.set_xlabel("Time from ablation (s)")
ax.set_ylabel(f"Targeted KT eYFP-Cdc20 / sister kinetochore\n(pre-ablation = 1; Σ in r={R} disk, cytosol-disk bg-subtracted)")
ax.set_title(f"FRAP — targeted kinetochore recovery vs intact sister "
             f"(N={nused} sequences, {len(set(s[0] for s in allseq))} cells)",loc="left",fontweight="bold",fontsize=10.5)
plt.tight_layout(); plt.savefig(f"{OUT}/G4_frap.png",bbox_inches="tight"); plt.close()

lib.record_plot("G4_frap",
  ["batch","frap_seq","abl_pre_frame","flash_tif_pos","tif_pos","is_pre_ablation","rel_time_s","targeted_bgsub_sum","sister_bgsub_sum"],rec,
  {"type":"line (intensity vs time)","color":"targeted=red / sister=blue",
   "measure":f"TOTAL intensity Σ in r={R} circular disk on the 16-bit FLUOR TIF",
   "background":f"same-size cytosol disk Σ subtracted (r={R})",
   "t0":"ablation flash (located + EXCLUDED; first sample = frame before flash; saturated disks dropped)",
   "frame_mapping":"calibrated pos_of_frame / plane_by_pos (NOT t_sec)",
   "expected":"sister flat, targeted dips then recovers",
   "frames_for_timestrips":"tif_pos column = every measured TIF plane; flash_tif_pos = excluded flash; is_pre_ablation flags the baseline sample"},
  SCRIPT,"FRAP recovery of targeted vs sister kinetochore, cytosol-disk background-subtracted")

# ---------------- sanity check (printed): targeted/sister (sister=1 reference, flat) ----------------
def med_at(center,half=6):
    m=(allT>=center-half)&(allT<center+half)
    if not m.sum(): return None,0
    return float(np.median(allQ[m])),int(m.sum())
print(f"FRAP: {nused}/{len(allseq)} sequences used across {len(set(s[0] for s in allseq))} cells; {len(rec)} measurements")
print("  sister reference = 1.0 (flat) at all times; targeted = targeted/sister (pre-ablation=1):")
for c in (0,30,45,90,120):
    q,n=med_at(c)
    print(f"  t~{c:>3}s  n={n:4d}  targeted/sister_med={q if q is None else round(q,3)}")
if flagged_px: print("  FLAGGED 0.031 um/px:", ", ".join(f"{b}({p})" for b,p in flagged_px))

# ---------------- USER-SPECIFIED combined plot (rec8 "slide 9") ----------------
seqmap={(b,si):(T,Tg,Si) for (b,si,T,Tg,Si) in allseq}

# ---- FA2: two selected picks (20250402 ptk_yfpcdc20_2 #0 & 20260417 ...ablation_18 #1) render in the SAME
# color; remove whichever has the >2.5 start-normalized outlier point. Also remove 20260420 ...ablation_8 #0
# (does not recover fast enough). The SAME removals are applied to BOTH the ratio-combined (G4_frap_combined)
# and the both-normalized combined (G4_frap_both_combined) plots.
FRAP_COMBINED_DROP={("20260420 ptk2 eyfp cdc20 1 ablation_8",0)}
_fa2_pair=[("20250402 ptk_yfpcdc20_2",0),("20260417 ptk2 eyfp cdc20 ablation_18",1)]
def _both_norm_max(T,Tg,Si):
    """max of the BOTH-normalized curves (each KT / its own pre-ablation baseline), ignoring >8x artifact
    frames (the same guard the both-combined plot uses). Mirrors norm_both, defined here so FA2 can use it."""
    T=np.array(T,float); Tg=np.array(Tg,float); Si=np.array(Si,float)
    o=np.argsort(T); T,Tg,Si=T[o],Tg[o],Si[o]
    preT=Tg[T<0]; preS=Si[T<0]
    tb=np.mean(preT[preT>0]) if (preT>0).any() else None
    sb=np.mean(preS[preS>0]) if (preS>0).any() else None
    if not tb or not sb or tb<=0 or sb<=0: return None
    bn=np.concatenate([Tg/tb,Si/sb]); bn=bn[np.isfinite(bn)&(np.abs(bn)<=8)]
    return float(np.nanmax(bn)) if bn.size else None
_fa2_cand=[]
for _b,_si in _fa2_pair:
    if (_b,_si) in seqmap:
        _mx=0.0
        _rs=ratio_series(*seqmap[(_b,_si)]); _snk=start_norm(*_rs) if _rs else None
        if _snk is not None and np.isfinite(_snk[1]).any(): _mx=max(_mx,float(np.nanmax(_snk[1])))
        _bnm=_both_norm_max(*seqmap[(_b,_si)])          # task: check the BOTH-normalized data too (y can exceed 2.5 there)
        if _bnm is not None: _mx=max(_mx,_bnm)
        _fa2_cand.append((_b,_si,_mx))
_fa2_over=[c for c in _fa2_cand if c[2]>2.5]
if _fa2_over:
    _b,_si,_mx=max(_fa2_over,key=lambda c:c[2])   # drop the single pick with the >2.5 outlier
    FRAP_COMBINED_DROP.add((_b,_si))
    lib.log_review("frap_combined_outlier_drop",_b,f"seq{_si}",f">2.5 start-normalized outlier (max={_mx:.2f}); same color as pairmate — removed from FRAP combined plots")
print("FRAP combined drops (FA2):",sorted(FRAP_COMBINED_DROP),"| pair maxima:",[(c[0],c[1],round(c[2],2)) for c in _fa2_cand])

# FA-color (2026-07-08): the combined plots reused matplotlib's 10-color default cycle for ~12 traces, so
# samples 11-12 collided with samples 1-2 (two blue, two orange — feedback line 119 "two lines are the same
# color"). Give EVERY sample a DISTINCT color from a >=14-color qualitative palette (tab20 = 20 colors).
_TAB20=list(plt.get_cmap('tab20').colors)
def _trend_med(TT,QQ,w=6):
    """binned-median aggregate trend across a set of traces (same 6s binning as the main aggregates)."""
    TT=np.asarray(TT,float); QQ=np.asarray(QQ,float); bc=[]; mq=[]
    for lo in np.arange(-6,126,w):
        m=(TT>=lo)&(TT<lo+w)
        if m.sum()>=3: bc.append(lo+w/2); mq.append(np.median(QQ[m]))
    return bc,mq

if FRAP_COMBINED_PICKS:
    fC,aC=plt.subplots(figsize=(7.5,5.0)); _ccrows=[]; _ci=0; _aggT=[]; _aggQ=[]
    for pick in FRAP_COMBINED_PICKS:
        b,si,op=(list(pick)+[None])[:3]
        if (b,si) in FRAP_COMBINED_DROP: continue   # FA2: same-color outlier pick + too-slow ablation_8 removed
        if (b,si) not in seqmap:
            print(f"  COMBINED PICK NOT FOUND: {b!r} #{si}"); continue
        rs=ratio_series(*seqmap[(b,si)]); snk=start_norm(*rs) if rs else None
        if snk is None: continue
        Tk,Q=_apply_op(snk[0],snk[1],op)             # user point-trims: through point N / without points 5,6,7
        # USER 07-14: post-bleach point -> 0, pre-ablation -> 1.
        # USER 2026-08-05: anchor that 0 on the FIRST POST-ABLATION point, not the global minimum.
        sz=first_post_zero(Tk,Q)
        if sz is None: continue
        Tk,Q,_nneg=sz
        if _nneg: _FIRSTPOST_NEG.append((b,si,_nneg))
        aC.plot(Tk,Q,marker="o",ms=4,color=_TAB20[_ci%20],alpha=.55,label=f"{b} #{si}"); _ci+=1   # FA-color + lower opacity (user)
        _aggT+=list(np.asarray(Tk,float)); _aggQ+=list(np.asarray(Q,float))
        _ccrows+=[[b,si,round(float(t),1),round(float(q),4)] for t,q in zip(Tk,Q)]
    # aggregate TRENDLINE across ALL targeted/sister ratio traces (user's terminal request). The sister
    # reference is the flat=1 line (labelled below) -> the two requested trends = ratio-median + sister=1.
    _bt,_mt=_trend_med(_aggT,_aggQ)
    if _bt: aC.plot(_bt,_mt,color="#111111",lw=3,marker="o",ms=6,zorder=10,label="targeted/sister (median trend)")
    aC.axhline(1,color="#888",lw=1.2,ls="--",label="pre-ablation level (=1)"); aC.axhline(0,color="#888",lw=1.0,ls=":")
    aC.axvline(0,color="#333",ls=":",lw=1)
    aC.set_xlabel("Time from ablation (s)"); aC.set_ylabel("Targeted KT eYFP-Cdc20 recovery\n(pre-ablation = 1, first post-ablation point = 0)")
    aC.legend(fontsize=6.5,loc="upper left",bbox_to_anchor=(1.01,1.0)); aC.set_title("FRAP — selected recovery traces (combined; first post-ablation point = 0)",loc="left",fontweight="bold",fontsize=10.5)
    fC.tight_layout(); fC.savefig(f"{OUT}/G4_frap_combined.png",bbox_inches="tight"); plt.close(fC)
    lib.record_plot("G4_frap_combined",["batch","frap_seq","time_from_ablation_s","targeted_over_sister_start1"],_ccrows,
        {"type":"selected FRAP recovery traces","norm":"targeted/sister, start=1, floored at 0 (no negative fluorescence)",
         "zero_anchor":("USER 2026-08-05: 0 is anchored on the FIRST timepoint after ablation, not on the curve's "
                        "global minimum. Every trace starts at -3 s = 1 and reads exactly 0 at its first post-0 point."),
         "negative_clamped_to_zero":(f"{sum(x[2] for x in _FIRSTPOST_NEG)} point(s) fell below 0 after that "
                                     f"re-anchoring (their true minimum comes later than the first post-ablation "
                                     f"sample) and were set to 0: {_FIRSTPOST_NEG}")},
        SCRIPT,"FRAP selected combined traces",source=[lib.SOURCE_ANNOT_KT],key_column="batch")
    print(f"FRAP combined plot: {len(FRAP_COMBINED_PICKS)} picks -> {OUT}/G4_frap_combined.png")
else:
    print("FRAP combined plot: FLAG/TODO — FRAP_COMBINED_PICKS empty. Requested traces ('0925 triple v0', "
          "'0711 double v0', 'a ptk_yfpcdc20 up to 20s', '0711 double v3 one pt') reference the Jun-26 "
          "contact-sheet ordering; fill FRAP_COMBINED_PICKS from G4_frap_contactsheet_index.csv to build it.")

# ---------------- NEW: both-curves aggregate — targeted + sister each start-normalized to 1 ----------------
# Companion to the ratio plot. Each KT's cytosol-subtracted Σ is divided by its OWN pre-ablation baseline,
# so both curves START at 1 and 0 = NO FLUORESCENCE (background level). Same spike/drop guards as the ratio.
def norm_both(T,Tg,Si):
    T=np.array(T,float); Tg=np.array(Tg,float); Si=np.array(Si,float)
    o=np.argsort(T); T,Tg,Si=T[o],Tg[o],Si[o]
    preT=Tg[T<0]; preS=Si[T<0]
    tb=np.mean(preT[preT>0]) if (preT>0).any() else None
    sb=np.mean(preS[preS>0]) if (preS>0).any() else None
    if not tb or not sb or tb<=0 or sb<=0: return None
    return T, Tg/tb, Si/sb
def _binmed(TT,QQ):
    TT=np.asarray(TT,float); QQ=np.asarray(QQ,float); bc=[]; mq=[]
    for lo in np.arange(-6,126,6):
        m=(TT>=lo)&(TT<lo+6)
        if m.sum()>=3: bc.append(lo+3); mq.append(np.median(QQ[m]))
    return bc,mq

# ---------------- ITEM3: NEW both-curves COMBINED plot (same selected picks as ITEM2) ----------------------
# Companion to G4_frap_combined but from the version where the sister is NOT forced to a constant 1: each KT
# (targeted + sister) is normalized to its OWN pre-ablation baseline (norm_both), so BOTH start at 1. Rescaled
# so the y-floor = 0 (minimum fluorescence possible = 0 = background). Same tmax caps as ITEM2.
import matplotlib.lines as _ml3
if FRAP_COMBINED_PICKS:
    fBc,aBc=plt.subplots(figsize=(9.2,5.4)); _n_bc=0; _bcrows=[]
    _ci=0; _aggTt=[]; _aggQt=[]; _aggTs=[]; _aggQs=[]   # FA-color palette index + aggregate-trend accumulators
    for pick in FRAP_COMBINED_PICKS:
        b,si,op=(list(pick)+[None])[:3]
        if (b,si) in FRAP_COMBINED_DROP: continue   # FA2: same removals as the ratio-combined plot
        if (b,si) not in seqmap: print(f"  BOTH-COMBINED PICK NOT FOUND: {b!r} #{si}"); continue
        nb=norm_both(*seqmap[(b,si)])
        if nb is None: print(f"  BOTH-COMBINED no baseline: {b!r} #{si}"); continue
        Tn,Qt,Qs=nb; Tn=np.asarray(Tn,float); Qt=np.asarray(Qt,float); Qs=np.asarray(Qs,float)
        # both-curves plot keeps its OWN normalization (each KT to own baseline, start=1); only apply the user's
        # point-trims (op), consistently across Tn/Qt/Qs. (second_zero is applied to the RATIO/recovery plots.)
        _Tn0=Tn.copy(); Tn,Qt=_apply_op(_Tn0,Qt,op); _,Qs=_apply_op(_Tn0,Qs,op)
        # per-FRAME artifact rejection (same >8x guard the codebase uses elsewhere): in the both-version a
        # bad-baseline frame can spike one KT to ~40-110x and flatten every other trace. Drop just those
        # frames (keep the start anchor + rest of the curve) so all requested samples stay visible.
        keep=(np.abs(Qt)<=8)&(np.abs(Qs)<=8)
        if keep.size and not bool(keep.all()):
            print(f"  BOTH-COMBINED artifact-frame drop: {b!r} #{si} removed {int((~keep).sum())} frame(s) >8x")
            keep[0]=True; Tn,Qt,Qs=Tn[keep],Qt[keep],Qs[keep]
        # FA3: on 20250826 test_ablation_14 #0 remove the single ~15s ~5y outlier point (on whichever curve
        # carries it) with the hollow-marker technique, drawn ON THE LINE at that x; the other curve keeps its
        # point. With the outlier gone the y-axis (floored at 0) autoscales down to fit the rest of the data.
        _dt=np.zeros(Tn.shape,bool); _ds=np.zeros(Tn.shape,bool); _holes=[]
        if (b,si)==("20250826 test_ablation_14",0):
            for _flag,_Q in (("t",Qt),("s",Qs)):
                _mm=(Tn>=10)&(Tn<=20)&(_Q>3)
                if _mm.any():
                    _i=int(np.argmax(np.where(_mm,_Q,-np.inf)))
                    (_dt if _flag=="t" else _ds)[_i]=True; _holes.append((_flag,float(Tn[_i])))
        Tt2,Qt2=Tn[~_dt],Qt[~_dt]; Ts2,Qs2=Tn[~_ds],Qs[~_ds]
        col=_TAB20[_ci%20]; _ci+=1                    # FA-color: distinct color per sample (was default 10-cycle -> collisions)
        aBc.plot(Tt2,Qt2,marker="o",ms=4,color=col,label=f"{b} #{si}")
        aBc.plot(Ts2,Qs2,marker="s",ms=4,ls="--",color=col); _n_bc+=1
        _aggTt+=list(Tt2); _aggQt+=list(Qt2); _aggTs+=list(Ts2); _aggQs+=list(Qs2)
        for _x,_y in zip(Tt2,Qt2): _bcrows.append([b,si,"targeted",round(float(_x),3),round(float(_y),4),0])
        for _x,_y in zip(Ts2,Qs2): _bcrows.append([b,si,"sister",round(float(_x),3),round(float(_y),4),0])
        for _flag,_xo in _holes:
            _yl=float(np.interp(_xo,Tt2,Qt2)) if _flag=="t" else float(np.interp(_xo,Ts2,Qs2))
            aBc.plot([_xo],[_yl],marker=("o" if _flag=="t" else "s"),mfc="none",mec=col,ms=5,mew=1.2,ls="none",zorder=6)
            _bcrows.append([b,si,("targeted_hole" if _flag=="t" else "sister_hole"),round(float(_xo),3),round(_yl,4),1])
    # aggregate TRENDLINES (user's terminal request): one across ALL targeted (on-target) traces, one across
    # ALL sister (off-target) traces, binned-median (_binmed, 6s bins). Drawn bold on top of the light samples.
    _btt,_mtt=_binmed(_aggTt,_aggQt); _bts,_mts=_binmed(_aggTs,_aggQs)
    if _btt: aBc.plot(_btt,_mtt,color=TC,lw=3,marker="o",ms=6,zorder=8,label="targeted (median trend)")
    if _bts: aBc.plot(_bts,_mts,color=SC,lw=3,marker="s",ms=6,ls="--",zorder=8,label="sister (median trend)")
    aBc.axhline(1,color="#999",lw=1.0,ls="--"); aBc.axhline(0,color="#555",lw=.9); aBc.axvline(0,color="#333",ls=":",lw=1)
    aBc.set_ylim(bottom=0)        # ITEM3: values floored at 0 (no negative fluorescence), start=1
    _h,_l=aBc.get_legend_handles_labels()
    # FA3: the open/hollow marker drawn ON THE LINE marks a point removed as an outlier (e.g. 20250826
    # test_ablation_14 #0 sister ~15s, ~4.8x) — call it out in the legend so the gap is self-explanatory.
    _h+=[_ml3.Line2D([],[],color="#333",ls="-",marker="o",ms=4),_ml3.Line2D([],[],color="#333",ls="--",marker="s",ms=4),
         _ml3.Line2D([],[],color="#333",ls="none",marker="o",mfc="none",mec="#333",ms=6,mew=1.2)]
    _l+=["targeted (solid)","sister (dashed)","hollow = missing point"]
    aBc.legend(_h,_l,fontsize=6.3,loc="upper left",bbox_to_anchor=(1.01,1.0))
    aBc.set_xlabel("Time from ablation (s)"); aBc.set_ylabel("KT eYFP-Cdc20 (start=1; 0 = no fluorescence)")
    aBc.set_title("FRAP — selected traces, targeted+sister both start=1 (min=0)",loc="left",fontweight="bold",fontsize=10.5)
    fBc.tight_layout(); fBc.savefig(f"{OUT}/G4_frap_both_combined.png",bbox_inches="tight"); plt.close(fBc)
    lib.record_plot("G4_frap_both_combined",["batch","frap_seq","series","time_from_ablation_s","intensity_start1","is_hole_marker"],_bcrows,
      {"type":"selected targeted(solid)+sister(dashed) traces, both start=1, min=0","normalization":"each KT divided by its OWN pre-ablation baseline (norm_both)",
       "guards":">8x artifact-frame drop; FA3 15s outlier -> hollow marker on line","picks":str([(list(p)+[None,None])[:2] for p in FRAP_COMBINED_PICKS])},
      SCRIPT,"FRAP selected traces (both start=1, min=0)")
    print(f"FRAP both-curves COMBINED plot: {_n_bc} traces -> {OUT}/G4_frap_both_combined.png")

# individual both-curves contact sheet + full-size PNGs (parallels the complete-ablation page-48 individual)
INB=f"{OUT}/frap_both_individual"; os.makedirs(INB,exist_ok=True)
for _f in _glob.glob(f"{INB}/frapboth_*.png"): os.remove(_f)
_nbok=[(b,si,norm_both(T,Tg,Si)) for (b,si,T,Tg,Si) in allseq if b not in FRAP_DROP_BATCHES]
_nbok=[(b,si,nb) for (b,si,nb) in _nbok if nb is not None and np.max(np.abs(nb[1]))<=8 and np.max(np.abs(nb[2]))<=8]
_nrowsB=math.ceil(len(_nbok)/NCOL) if _nbok else 1
figBI,axBI=plt.subplots(_nrowsB,NCOL,figsize=(16,3.2*_nrowsB),squeeze=False)
for k,(b,si,(Tn,Qt,Qs)) in enumerate(_nbok):
    fI,aI=plt.subplots(figsize=(4,3))
    aI.plot(Tn,Qt,color=TC,marker="o",ms=4,label="targeted"); aI.plot(Tn,Qs,color=SC,marker="o",ms=4,label="sister")
    aI.axhline(1,color="#999",ls="--",lw=.8); aI.axhline(0,color="#555",lw=.8); aI.axvline(0,color="#333",ls=":",lw=1)
    aI.set_xlabel("time from ablation (s)"); aI.set_ylabel("KT eYFP-Cdc20 (start=1; 0=no fluor)")
    aI.legend(fontsize=7); lib.mark_excluded_ax(aI,b,f"{b} #{si}",fontsize=8)
    fI.tight_layout(); fI.savefig(f"{INB}/frapboth_{k:03d}_{b.replace(' ','_')}_{si}.png",bbox_inches="tight"); plt.close(fI)
    a=axBI[k//NCOL][k%NCOL]
    a.plot(Tn,Qt,color=TC,lw=.8,marker="o",ms=2); a.plot(Tn,Qs,color=SC,lw=.8,marker="o",ms=2)
    a.axhline(1,color="#999",ls="--",lw=.6); a.axhline(0,color="#555",lw=.6); a.axvline(0,color="#333",ls=":",lw=.6)
    lib.mark_excluded_ax(a,b,f"{b} #{si}",fontsize=4.5); a.tick_params(labelsize=6)
for k in range(len(_nbok),_nrowsB*NCOL): axBI[k//NCOL][k%NCOL].axis("off")
figBI.suptitle(f"FRAP — {len(_nbok)} individual ablations: targeted (red) + sister (blue), each start=1 (0=no fluorescence)",x=.01,ha="left",fontweight="bold")
figBI.tight_layout(); figBI.savefig(f"{OUT}/G4_frap_both_individual_contactsheet.png",bbox_inches="tight"); plt.close(figBI)
print(f"FRAP both-curves individual plots: {len(_nbok)} in {INB}")

figB,axB=plt.subplots(figsize=(8.5,5.4))
aTt=[];aQt=[];aTs=[];aQs=[];nboth=0; _bothrows=[]
for b,si,T,Tg,Si in allseq:
    if b in FRAP_DROP_BATCHES or lib.plot_excluded(b): continue
    nb=norm_both(T,Tg,Si)
    if nb is None: continue
    Tn,Qt,Qs=nb
    if np.max(np.abs(Qt))>8 or np.max(np.abs(Qs))>8: continue     # same >8x spike guard as the ratio aggregate
    axB.plot(Tn,Qt,color=TC,alpha=.13,lw=.6); axB.plot(Tn,Qs,color=SC,alpha=.13,lw=.6)
    aTt+=list(Tn); aQt+=list(Qt); aTs+=list(Tn); aQs+=list(Qs); nboth+=1
    for _x,_y in zip(Tn,Qt): _bothrows.append([b,si,"targeted",round(float(_x),3),round(float(_y),4)])
    for _x,_y in zip(Tn,Qs): _bothrows.append([b,si,"sister",round(float(_x),3),round(float(_y),4)])
bt,mt=_binmed(aTt,aQt); bs,ms=_binmed(aTs,aQs)
axB.plot(bs,ms,color=SC,lw=3,marker="o",ms=6,label="sister KT (median)",zorder=5)
axB.plot(bt,mt,color=TC,lw=3,marker="o",ms=6,label="targeted KT (median)",zorder=6)
axB.axhline(1,color="#999",ls="--",lw=1,zorder=1)
axB.axhline(0,color="#555",ls="-",lw=.9,zorder=1); axB.text(126,0,"no fluorescence",va="center",ha="right",fontsize=7,color="#555")
axB.axvline(0,color="#333",ls=":",lw=1)
axB.text(1.0,axB.get_ylim()[1]*.98,"ablation",rotation=90,va="top",fontsize=7,color="#333")
axB.legend(fontsize=9,loc="upper right")
axB.set_xlabel("Time from ablation (s)")
axB.set_ylabel(f"KT eYFP-Cdc20 intensity, start-normalized to 1\n(0 = no fluorescence; Σ in r={R} disk, cytosol-disk bg-subtracted)")
axB.set_title(f"FRAP — targeted vs sister KT intensity, both start-normalized "
              f"(N={nboth} sequences, {len(set(s[0] for s in allseq))} cells)",loc="left",fontweight="bold",fontsize=10.5)
plt.tight_layout(); plt.savefig(f"{OUT}/G4_frap_both.png",bbox_inches="tight"); plt.close()
lib.record_plot("G4_frap_both",["batch","frap_seq","series","time_from_ablation_s","intensity_start1"],_bothrows,
  {"type":"per-sequence light traces (targeted=red/sister=blue) + binned-median trend","normalization":"each KT divided by its OWN pre-ablation baseline (norm_both), both start=1; 0=no fluorescence",
   "guard":">8x spike sequences dropped (same as ratio aggregate)","n_sequences":nboth},SCRIPT,"FRAP targeted vs sister, both start-normalized")
print(f"FRAP both-curves plot: N={nboth} -> {OUT}/G4_frap_both.png")

# ================= NEW: FRAP recovery vs complete ablation — TARGETED ONLY (no sisters) =================
# Two groups on one axis, each start-normalized to 1, targeted kinetochore ONLY (sister/paired traces are
# NOT drawn). Each individual curve is faint; ONE bold binned-median trendline per group.
#   Group A (FRAP recovery)   : norm_both -> the TARGETED trace only (Tg / own pre-ablation baseline = 1).
#                               The measurement floor was removed (no clamp to 0) so near-zero recovery
#                               values show honestly.
#   Group B (complete ablation): the on-target COMPLETE-ablation TARGETED traces, start-normalized to 1
#                               with the SAME measurement/normalization the ablation-intensity plot uses
#                               (norm_series, replicated below; ABL_SEL_PICKS copied verbatim). Read the
#                               same annotation source (kt_points.csv) read-only via the shared `allseq`.
# POINT NUMBERING: point 1 = the first plotted point = the pre-ablation/start=1 point; count from there.

# --- Group A picks (FRAP recovery). op: None=all points | ("drop_pts",[..])=drop those 1-indexed plotted
#     points | ("keep_first",n)=keep only points 1..n. ---
FRAP_TARGETED_PICKS=USER_FRAP_PICKS   # same curated 8-sample set as the combined plot (user 2026-07-14)
# 2 more FRAP samples to be added later (user will confirm): 20250402 x2 and 20251104 #2.
# Add them here as (batch, seq, op) tuples — one-line edit, no other change needed. Empty for now.
FRAP_VS_PENDING=[]   # e.g. ("20250402 ptk_yfpcdc20_2",0,None), ("20250402 ...",0,None), ("20251104 ...",2,None)

# --- Group B picks (complete ablation): EXACT ABL_SEL_PICKS from group4_ablation_intensity.py.
#     (batch, seq, tmax_s_or_None, special_or_None). ---
ABL_SEL_PICKS=[
  ("20250404 ptk_yfpcdc20_16",0,None,None),
  ("20250410 ptk_yfpcdc20_17",0,None,None),
  ("20250423 ptk_yfpcdc20_20",0,26,None),
  ("20250904 triple_ablation_8",2,20,None),
  ("20250923 triple_ablation_collagen_2",0,None,None),
  ("20251002 max_ablation_1_2",5,None,"drop_targeted_near_10"),
  ("20260420 ptk2 eyfp cdc20 1 ablation_8",0,21,None),
]

# norm_series replicated from group4_ablation_intensity.py (the "same measurement the ablation-intensity plot
# uses"): each channel start-normalized so its earliest-time value = 1, with per-frame artifact rejection.
_NORM_CAP=float(os.environ.get("ABL_NORM_CAP","5")); _NEG_FLOOR=float(os.environ.get("ABL_NEG_FLOOR","-2"))
def _abl_norm_targeted(T,Tg):
    """targeted start-normalized to 1 (norm_series 'targeted' channel). Returns (Tk,Q) or (None,None)."""
    T=np.array(T,float); Tg=np.array(Tg,float); o=np.argsort(T); T,Tg=T[o],Tg[o]
    if Tg.size==0 or not np.isfinite(Tg[0]) or Tg[0]<=0: return None,None
    n=Tg/Tg[0]; good=np.isfinite(n)&(n>=_NEG_FLOOR)&(n<=_NORM_CAP); good[0]=True
    if good.sum()<2: return None,None
    return T[good],n[good]

# _apply_op moved up next to second_zero (shared by the combined FRAP plot + this vs-complete plot).
_BLUES=["#6baed6","#4292c6","#2171b5","#08519c","#3182bd","#4a90d9"]   # Group A = blues
_REDS =["#fb6a4a","#ef3b2c","#cb181d","#a50f15","#f16913","#d94801","#99000d"]  # Group B = reds/oranges
_A_TREND="#08306b"; _B_TREND="#7f0000"                                  # bold trendlines (dark blue / dark red)

figV,axV=plt.subplots(figsize=(9.0,5.6))
_vrows=[]                       # record_plot data
_aggAt=[]; _aggAq=[]; _aggBt=[]; _aggBq=[]     # aggregate accumulators per group
_nA=0; _nB=0

# ---- Group A: FRAP recovery (norm_both -> targeted only) ----
for _i,(b,si,op) in enumerate(FRAP_TARGETED_PICKS+FRAP_VS_PENDING):
    if (b,si) not in seqmap: print(f"  FRAP-VS pick NOT FOUND (A): {b!r} #{si}"); continue
    nb=norm_both(*seqmap[(b,si)])
    if nb is None: print(f"  FRAP-VS no baseline (A): {b!r} #{si}"); continue
    Tn,Qt,_Qs=nb                                    # targeted trace ONLY (drop sister)
    Tk,Q=_apply_op(np.asarray(Tn,float),np.asarray(Qt,float),op)
    # USER 2026-08-05: same rule as the FRAP combined plot — anchor 0 on the FIRST POST-ABLATION point,
    # not on the curve's global minimum, so every trace here starts from the same defined zero.
    sz=first_post_zero(Tk,Q)
    if sz is None: continue
    Tk,Q,_nneg=sz
    if _nneg: _FIRSTPOST_NEG.append((b,si,_nneg))
    axV.plot(Tk,Q,color=_BLUES[_i%len(_BLUES)],alpha=.35,lw=1.0,marker="o",ms=3,zorder=3)  # lower opacity (user)
    _aggAt+=list(Tk); _aggAq+=list(Q); _nA+=1
    for _x,_y in zip(Tk,Q): _vrows.append([b,"frap_recovery",si,round(float(_x),2),round(float(_y),4)])

# ---- Group B: complete ablation (norm_series targeted, ABL_SEL_PICKS) ----
for _j,(b,si,tmax,special) in enumerate(ABL_SEL_PICKS):
    if (b,si) not in seqmap: print(f"  FRAP-VS pick NOT FOUND (B): {b!r} #{si}"); continue
    T,Tg,Si=seqmap[(b,si)]
    Tk,Q=_abl_norm_targeted(T,Tg)
    if Tk is None: print(f"  FRAP-VS no baseline (B): {b!r} #{si}"); continue
    if tmax is not None: m=Tk<=tmax; Tk,Q=Tk[m],Q[m]
    if special=="drop_targeted_near_10" and Tk.size:                  # same special the ablation plot uses
        idx=int(np.argmin(np.abs(Tk-10.0))); Tk=np.delete(Tk,idx); Q=np.delete(Q,idx)
    if Tk.size<1: continue
    # USER 2026-08-05: the complete-ablation group takes the SAME anchor as the FRAP group above.
    # Group A and Group B are drawn on one axis, so they have to share a definition of y=0 — anchoring one
    # on its minimum and the other on its first post-ablation point would make the two incomparable at 0,
    # which is exactly the mismatch already flagged in this figure's own note.
    sz=first_post_zero(Tk,Q)
    if sz is None: continue
    Tk,Q,_nneg=sz
    if _nneg: _FIRSTPOST_NEG.append((b,si,_nneg))
    axV.plot(Tk,Q,color=_REDS[_j%len(_REDS)],alpha=.35,lw=1.0,marker="o",ms=3,zorder=3)  # lower opacity (user)
    _aggBt+=list(Tk); _aggBq+=list(Q); _nB+=1
    for _x,_y in zip(Tk,Q): _vrows.append([b,"complete_ablation",si,round(float(_x),2),round(float(_y),4)])

# ---- one bold binned-median TRENDLINE per group (_binmed = 6s bins, defined above) ----
_bA,_mA=_binmed(_aggAt,_aggAq); _bB,_mB=_binmed(_aggBt,_aggBq)
if _bA: axV.plot(_bA,_mA,color=_A_TREND,lw=3.2,marker="o",ms=6,zorder=8)
if _bB: axV.plot(_bB,_mB,color=_B_TREND,lw=3.2,marker="s",ms=6,zorder=8)
axV.axhline(1,color="#999",ls="--",lw=1.0,zorder=1); axV.axvline(0,color="#333",ls=":",lw=1)
axV.text(1.0,axV.get_ylim()[1]*.98,"ablation",rotation=90,va="top",fontsize=7,color="#333")
axV.set_ylim(bottom=0)
import matplotlib.lines as _mlV
_leg=[_mlV.Line2D([],[],color=_BLUES[2],alpha=.7,lw=1.1,marker="o",ms=3),
      _mlV.Line2D([],[],color=_A_TREND,lw=3.2,marker="o",ms=6),
      _mlV.Line2D([],[],color=_REDS[2],alpha=.7,lw=1.1,marker="o",ms=3),
      _mlV.Line2D([],[],color=_B_TREND,lw=3.2,marker="s",ms=6)]
_legl=[f"FRAP recovery — individual ({_nA})","FRAP recovery — median trend",
       f"Complete ablation — individual ({_nB})","Complete ablation — median trend"]
axV.legend(_leg,_legl,fontsize=8.5,loc="upper right")
axV.set_xlabel("Time from ablation (s)")
axV.set_ylabel("Targeted KT eYFP-Cdc20 recovery\n(pre-ablation = 1, post-bleach min = 0)")
axV.set_title("FRAP recovery vs complete ablation — TARGETED kinetochore only "
              f"(no sisters; A={_nA} FRAP, B={_nB} complete-ablation traces)",loc="left",fontweight="bold",fontsize=10.5)
figV.tight_layout(); figV.savefig(f"{OUT}/G4_frap_vs_complete_targeted.png",bbox_inches="tight"); plt.close(figV)
lib.record_plot("G4_frap_vs_complete_targeted",["batch","group","seq","time_s","intensity_start1"],_vrows,
  {"type":"targeted-only recovery vs complete-ablation, start=1, one binned-median trendline per group",
   "group_A":"FRAP recovery (norm_both -> targeted only; measurement floor removed so near-zero shows honestly)",
   "group_B":"complete ablation (norm_series targeted; ABL_SEL_PICKS from group4_ablation_intensity.py)",
   "colors":"FRAP=blues / complete-ablation=reds-oranges; faint individual lines + bold trend each",
   "no_sisters":"sister/paired traces NOT drawn"},
  SCRIPT,"FRAP recovery vs complete ablation, targeted kinetochore only",
  source=[lib.SOURCE_ANNOT_KT],key_column="batch")
print(f"FRAP-vs-complete targeted plot: A={_nA} FRAP + B={_nB} complete-ablation traces -> {OUT}/G4_frap_vs_complete_targeted.png")

lib.flush_review(f"{OUT}/G4_frap_review.csv")
