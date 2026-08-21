"""Group 1/4 — successful-ablation KT eYFP-Cdc20 over time (targeted vs sister kinetochore).
Companion to the FRAP plot (group4_frap.py): same measurement, but a FIXED recovery window and a SINGLE
cytosol point (the marking-frame background) normalizing every frame. Source: main kt_points.csv
(pre_abl / pre_abl_pair / cytosol_bg).

C1 timing: t=0 = the ablation flash; the flash frame is LOCATED (brightest/saturated disk next to the
marked frame) and NEVER measured; the first sample is the frame before it. C2: saturated disks dropped;
window bounded by the next ablation. C3: Σ in r=9 disk on the FLUOR TIF minus a same-size cytosol disk.
"""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, os, math, numpy as np, matplotlib.pyplot as plt
from collections import defaultdict
import lib
lib.apply_style()
OUT="/Volumes/4 MB/ablation_figures_20260625/group4"; SCRIPT=__file__
OUT=os.environ.get("KT_SWEEP_OUT",OUT); os.makedirs(OUT,exist_ok=True)
R=int(os.environ.get("KT_R","9")); NFRAMES=int(os.environ.get("ABL_NFRAMES","12"))
TC="#d62728"; SC="#1f77b4"
# Complete-ablation combined plot (rec8 "slide 15") references the Jun-26 individual contact sheet by
# row/col: row3col1, row3col5, row10col2. row/col depend on THAT day's ordering+grid(6 cols), so they are
# NOT resolvable now. FLAG/TODO: fill ABL_COMBINED_PICKS=[(batch,seq), ...] from the contact-sheet index
# CSV written below (G4_ablation_contactsheet_index.csv) once the Jun-26 ordering is confirmed.
ABL_COMBINED_PICKS=[("20250423 ptk_yfpcdc20_20",0),("20250711 double ablation_21",0),("20250925 triple_ablation_26",1)]  # r3c1 / r3c5 / r10c2

rows=list(csv.reader(open("/Volumes/4 MB/annotations/kt_points.csv"))); ix={c:i for i,c in enumerate(rows[0])}
mk=defaultdict(dict); cyto=defaultdict(list)
for r in rows[1:]:
    b=r[ix['batch']].strip(); lab=r[ix['label']].strip()
    if lib.is_prophase_ablation(b): continue   # prophase excluded (no prophase group)
    if lib.is_mad1(b): continue   # keep drug/Exclude in source so contactsheet can MARK them; aggregate skips below
    if lib.is_misplaced_id(r[ix['id']]): continue
    try: f=int(r[ix['frame']]); x=float(r[ix['x']]); y=float(r[ix['y']])
    except: continue
    if lab=='pre_abl': mk[b].setdefault(f,{})['tgt']=(x,y)
    elif lab=='pre_abl_pair': mk[b].setdefault(f,{})['sis']=(x,y)
    elif lab=='cytosol_bg': cyto[b].append((f,x,y))

allseq=[]; rec=[]; ncell=0
for b in sorted(mk):
    if lib.excluded(b): continue   # 07-07 feedback: drop user-flagged outlier (e.g. two_sisterless_kinetochores_5 ~80min) from ALL plots
    pre=sorted(F for F,m in mk[b].items() if 'tgt' in m and 'sis' in m)
    if not pre or b not in cyto: continue
    ft=lib.FluorTif(b,'ablation')                          # 16-bit cropped fluor TIF (not the 8-bit MP4)
    if not ft.ok(): continue
    N=len(ft); used=False
    cyto_pos=sorted((ft.pos_of_frame(cf),cx,cy) for cf,cx,cy in cyto[b] if ft.pos_of_frame(cf) is not None)
    for si,F in enumerate(pre):
        m=mk[b][F]; tx,ty=m['tgt']; sx,sy=m['sis']
        fr0=ft.pos_of_frame(F)
        if fr0 is None: continue
        gsnap=ft.plane_by_pos(max(0,fr0-2))
        if gsnap is None: gsnap=ft.plane_by_pos(fr0)
        if gsnap is None: continue
        txs,tys=lib.snap_to_peak(gsnap,tx,ty); sxs,sys=lib.snap_to_peak(gsnap,sx,sy)
        # single cytosol background = nearest marked cytosol point to this ablation frame
        cpos,cx,cy=min(cyto_pos,key=lambda c:abs(c[0]-fr0))
        # locate the flash frame near the marked frame (brightest/saturated targeted disk)
        win=[p for p in range(max(0,fr0-1),min(N,fr0+3))]
        dmx={p:(lib.disk_max(ft.plane_by_pos(p),txs,tys,R) or 0) for p in win}
        sat=[p for p in win if dmx[p]>=lib.SAT]
        if sat: fa=min(sat)
        else:
            pk=max(win,key=lambda p:dmx[p]); med=float(np.median(list(dmx.values()))) or 1.0
            fa=pk if dmx[pk]>1.5*med else fr0
        t0=ft.t_at(fa)
        pre_fr=None
        for p in range(fa-1,max(-1,fa-4),-1):
            if p<0: break
            g=ft.plane_by_pos(p)
            if g is None: continue
            if lib.is_saturated(g,txs,tys,R): continue
            pre_fr=p; break
        nxt=ft.pos_of_frame(pre[si+1]) if si+1<len(pre) else N
        positions=([pre_fr] if pre_fr is not None else [])+[p for p in range(fa+1,min(N,nxt,fa+1+NFRAMES))]
        T=[];Tg=[];Si=[]
        for fr in positions:
            g=ft.plane_by_pos(fr)
            if g is None: continue
            if lib.is_saturated(g,txs,tys,R) or lib.is_saturated(g,sxs,sys,R) or lib.is_saturated(g,cx,cy,R): continue
            cval=lib.disk_sum(g,cx,cy,R)
            if cval is None: continue
            # FLOOR at 0: negative background-subtracted fluorescence is physically impossible (no signal
            # above background = 0), so clamp instead of letting distant-cytosol over-subtraction go negative.
            tg=max(0.0,lib.disk_sum(g,txs,tys,R)-cval); ss=max(0.0,lib.disk_sum(g,sxs,sys,R)-cval); rt=ft.t_at(fr)-t0
            T.append(rt); Tg.append(tg); Si.append(ss)
            if not lib.plot_excluded(b): rec.append([b,si,F,fa,fr,1 if (pre_fr is not None and fr==pre_fr) else 0,round(rt,1),round(tg,1),round(ss,1)])
        if len(T)>=2: allseq.append((b,si,T,Tg,Si)); used=True
    ft.close()
    if used: ncell+=1

# Display normalization: targeted KT / intact SISTER at the same time point (internal reference that
# cancels whole-field photobleaching; sister=1 flat, targeted dips then recovers). Measurement/CSV stay
# the cytosol-disk-subtracted Σ (C3).
def ratio_series(T,Tg,Si):
    T=np.array(T,float); Tg=np.array(Tg,float); Si=np.array(Si,float)
    o=np.argsort(T); T,Tg,Si=T[o],Tg[o],Si[o]
    preT=Tg[T<0]; preS=Si[T<0]
    tb=np.mean(preT[preT>0]) if (preT>0).any() else None
    sb=np.mean(preS[preS>0]) if (preS>0).any() else None
    if not tb or not sb or tb<=0 or sb<=0: return None
    q0=tb/sb; keep=Si>0.15*sb
    if keep.sum()<2: return None
    return T[keep],(Tg[keep]/Si[keep])/q0

NORM_CAP=float(os.environ.get("ABL_NORM_CAP","5"))    # start-normalized point above this = artifact frame
NEG_FLOOR=float(os.environ.get("ABL_NEG_FLOOR","-2"))  # ...or below this (bg>>signal at one frame)
def norm_series(T,Tg,Si):
    """B-feedback: the complete-ablation plot shows targeted AND sister SEPARATELY (308 lines = 154 abl x2),
    each curve normalized so its STARTING (pre-ablation, earliest-time) value = 1.
    Returns ((Tk,Q,status), (Tk,Q,status)) for (targeted, sister). status is one of:
      'baseline' -> non-positive pre-ablation baseline (bg>signal = the measurement bug behind the user's
                    −6000/−8000 spikes); curve cannot be normalized -> Tk,Q=None, DROP + log.
      'empty'    -> after rejecting artifact frames <2 points remain -> DROP + log.
      'rejected' -> one or more artifact frames (norm outside [NEG_FLOOR,NORM_CAP]) removed; curve KEPT.
      'clean'    -> nothing rejected.
    Per-FRAME outlier rejection (vs dropping the whole curve) keeps ~280 of ~310 lines visible while removing
    the scale-wrecking spikes — exactly what the user asked ('so we can see the trends of ~200 lines')."""
    T=np.array(T,float); Tg=np.array(Tg,float); Si=np.array(Si,float)
    o=np.argsort(T); T,Tg,Si=T[o],Tg[o],Si[o]
    def ch(v):
        if v.size==0 or not np.isfinite(v[0]) or v[0]<=0: return None,None,'baseline'
        n=v/v[0]; good=np.isfinite(n)&(n>=NEG_FLOOR)&(n<=NORM_CAP); good[0]=True  # always keep the start anchor
        if good.sum()<2: return None,None,'empty'
        return T[good],n[good],('clean' if bool(good.all()) else 'rejected')
    return ch(Tg),ch(Si)

import glob as _glob
IND=f"{OUT}/ablation_individual"; os.makedirs(IND,exist_ok=True)
for _f in _glob.glob(f"{IND}/abl_*.png")+_glob.glob(f"{IND}/illustrator/abl_*.svg"): os.remove(_f)  # drop stale runs
NCOL=6
nrows=math.ceil(len(allseq)/NCOL) if allseq else 1
figG,axG=plt.subplots(nrows,NCOL,figsize=(20,2.6*nrows),squeeze=False)
cs_index=[]   # (k,row,col,batch,seq) ordering for the row/col cross-reference
for k,(b,si,T,Tg,Si) in enumerate(allseq):
    (Tt,Qt,_st),(Tss,Qs,_ss)=norm_series(T,Tg,Si)       # task 1: targeted & sister each START at 1
    fI,aI=plt.subplots(figsize=(3.6,2.6)); _lab=False
    if Qt is not None: aI.plot(Tt,Qt,color=TC,marker="o",ms=3,label="targeted"); _lab=True
    if Qs is not None: aI.plot(Tss,Qs,color=SC,marker="o",ms=3,label="sister"); _lab=True
    aI.axhline(1,color="#999",lw=.8,ls="--"); aI.axvline(0,color="#333",ls=":",lw=1)
    aI.set_xlabel("t from ablation (s)",fontsize=7); aI.set_ylabel("eYFP-Cdc20 (start=1)",fontsize=7)
    if _lab: aI.legend(fontsize=6)
    lib.mark_excluded_ax(aI,b,f"{b} #{si}",fontsize=7); aI.tick_params(labelsize=6)
    fI.tight_layout(); fI.savefig(f"{IND}/abl_{k:03d}_{b.replace(' ','_')}_{si}.png",bbox_inches="tight"); plt.close(fI)
    rr,cc=k//NCOL,k%NCOL; cs_index.append((k,rr+1,cc+1,b,si))
    a=axG[rr][cc]
    if Qt is not None: a.plot(Tt,Qt,color=TC,lw=.8,marker="o",ms=2)
    if Qs is not None: a.plot(Tss,Qs,color=SC,lw=.8,marker="o",ms=2)
    a.axhline(1,color="#999",lw=.5,ls="--"); a.axvline(0,color="#333",ls=":",lw=.6)
    lib.mark_excluded_ax(a,b,f"r{rr+1}c{cc+1} {b[:12]} #{si}",fontsize=5); a.tick_params(labelsize=4)
for k in range(len(allseq),nrows*NCOL): axG[k//NCOL][k%NCOL].axis("off")
with open(f"{OUT}/G4_ablation_contactsheet_index.csv","w",newline="") as _f:
    _w=csv.writer(_f); _w.writerow(["k","row","col","batch","seq"]); _w.writerows(cs_index)
figG.suptitle(f"Successful-ablation — {len(allseq)} individual ablations: targeted (red) + sister (blue), each start=1",x=.01,ha="left",fontweight="bold")
figG.tight_layout(); figG.savefig(f"{OUT}/G4_ablation_individual_contactsheet.png",bbox_inches="tight",dpi=120); plt.close(figG)
print(f"individual ablation plots: {len(allseq)} in {IND}")

# ---------------- aggregate: 308 lines = 154 ablations x (targeted + sister), each START-normalized to 1 ----
# Negatives the user saw (sister ~-8000 / targeted ~-6000) were UN-normalized raw Σ whose huge absolute
# scale also let a few bad-baseline curves dominate. Fix: plot every targeted & sister curve start-normalized
# to 1 (so all share one scale); a curve with a non-positive pre-ablation baseline (bg>signal = the
# measurement bug behind the spurious negatives) is dropped+logged, and individual artifact frames (norm
# outside [NEG_FLOOR,NORM_CAP]x) are rejected per-point so the rest of the curve stays visible.
fig,ax=plt.subplots(figsize=(8.5,5.4))
allT_t=[];allQ_t=[];allT_s=[];allQ_s=[]
n_tgt=n_sis=0; n_possible=2*sum(1 for _x in allseq if not lib.plot_excluded(_x[0]))
drop_baseline=drop_empty=n_rejected=0
for b,si,T,Tg,Si in allseq:
    if lib.plot_excluded(b): continue   # excluded/drug: shown+MARKED on contactsheet only, not in aggregate
    tch,sch=norm_series(T,Tg,Si)
    for name,(Tk,Q,st),col,aT,aQ in (("targeted",tch,TC,allT_t,allQ_t),("sister",sch,SC,allT_s,allQ_s)):
        if Q is None:
            if st=='baseline':
                drop_baseline+=1
                lib.log_review("ablation_intensity_baseline",b,f"seq{si}/{name}","non-positive pre-ablation baseline (bg>signal at baseline) — spurious-negative curve dropped")
            else:
                drop_empty+=1
                lib.log_review("ablation_intensity_artifact",b,f"seq{si}/{name}",f"<2 frames left after rejecting artifact points outside [{NEG_FLOOR:g},{NORM_CAP:g}]x — dropped")
            continue
        if st=='rejected':
            n_rejected+=1
            lib.log_review("ablation_intensity_pointreject",b,f"seq{si}/{name}",f"artifact frame(s) outside [{NEG_FLOOR:g},{NORM_CAP:g}]x rejected; curve kept")
        lib.cell_line(ax,Tk,Q,col,alpha=.18,lw=.6)
        for t,q in zip(Tk,Q): aT.append(t); aQ.append(q)
        if name=="targeted": n_tgt+=1
        else: n_sis+=1
allT_t=np.array(allT_t);allQ_t=np.array(allQ_t);allT_s=np.array(allT_s);allQ_s=np.array(allQ_s)
def med_trend(allT,allQ,lo0=-6,hi0=48,w=6):
    bc=[];mq=[]
    for lo in np.arange(lo0,hi0,w):
        mm=(allT>=lo)&(allT<lo+w)
        if mm.sum()>=3: bc.append(lo+w/2); mq.append(np.median(allQ[mm]))
    return bc,mq
bc_t,mq_t=med_trend(allT_t,allQ_t); bc_s,mq_s=med_trend(allT_s,allQ_s)
ax.plot(bc_t,mq_t,color=TC,lw=3,marker="o",ms=6,zorder=5,label=f"targeted KT (median, n={n_tgt})")
ax.plot(bc_s,mq_s,color=SC,lw=3,marker="o",ms=6,zorder=5,label=f"sister KT (median, n={n_sis})")
ax.axhline(1,color="#999",lw=1.0,ls="--",zorder=3); ax.axvline(0,color="#333",ls=":",lw=1)
ax.legend(fontsize=9,loc="upper right")
ax.set_xlabel("Time from ablation (s)"); ax.set_ylabel(f"eYFP-Cdc20 KT intensity, start-normalized to 1\n(Σ r={R} disk on FLUOR TIF, cytosol-disk bg-subtracted)")
ax.set_title(f"Successful-ablation KT intensity over time — targeted vs sister "
             f"({n_tgt+n_sis} lines drawn of {n_possible}; {ncell} cells)",loc="left",fontweight="bold",fontsize=10)
plt.tight_layout(); plt.savefig(f"{OUT}/G4_ablation_intensity.png",bbox_inches="tight"); plt.close()
lib.record_plot("G4_ablation_intensity",
  ["batch","abl_seq","abl_pre_frame","flash_tif_pos","tif_pos","is_pre_ablation","rel_time_s","targeted_bgsub_sum","sister_bgsub_sum"],rec,
  {"type":"line intensity vs time (308 lines: targeted+sister per ablation)","color":"targeted=red/sister=blue",
   "normalization":"each curve start-normalized so its pre-ablation value = 1",
   "frames":f"frame before flash + {NFRAMES} recovery frames; flash located & skipped",
   "cytosol":"single nearest marked cytosol disk, applied to all frames",
   "measure":f"Σ in r={R} disk on FLUOR TIF minus same-size cytosol disk (SAME as FRAP)",
   "frame_mapping":"calibrated pos_of_frame / plane_by_pos (NOT t_sec)",
   "excluded":f"dropped curves: {drop_baseline} non-positive-baseline + {drop_empty} artifact-dominated; {n_rejected} curves kept after per-frame artifact-point rejection (outside [{NEG_FLOOR:g},{NORM_CAP:g}]x) — all logged",
   "frames_for_timestrips":"tif_pos = measured planes; flash_tif_pos = excluded flash; is_pre_ablation flags baseline"},
  SCRIPT,"Successful-ablation targeted vs sister KT intensity over time (308 start-normalized lines)")

# ---------------- USER-SPECIFIED combined plot (rec8 "slide 15": row3col1, row3col5, row10col2) ----------
seqmap={(b,si):(T,Tg,Si) for (b,si,T,Tg,Si) in allseq}
# ITEM1 feedback: for these (batch,seq) picks drop the SISTER line only (keep the targeted line).
ABL_COMBINED_NO_SISTER={("20250711 double ablation_21",0)}
if ABL_COMBINED_PICKS:
    fC,aC=plt.subplots(figsize=(7.5,5.0)); _ccrows=[]
    for b,si in ABL_COMBINED_PICKS:
        if (b,si) not in seqmap: print(f"  COMBINED PICK NOT FOUND: {b!r} #{si}"); continue
        (Tt,Qt,_),(Tss,Qs,_)=norm_series(*seqmap[(b,si)])
        if Qt is not None:
            aC.plot(Tt,Qt,marker="o",ms=4,label=f"{b} #{si} targeted")
            for _x,_y in zip(Tt,Qt): _ccrows.append([b,si,"targeted",round(float(_x),3),round(float(_y),4)])
        if Qs is not None and (b,si) not in ABL_COMBINED_NO_SISTER:
            aC.plot(Tss,Qs,marker="s",ms=4,ls="--",label=f"{b} #{si} sister")
            for _x,_y in zip(Tss,Qs): _ccrows.append([b,si,"sister",round(float(_x),3),round(float(_y),4)])
    aC.axhline(1,color="#999",lw=1.0,ls="--"); aC.axvline(0,color="#333",ls=":",lw=1)
    aC.set_xlabel("Time from ablation (s)"); aC.set_ylabel("eYFP-Cdc20 KT intensity (start=1)")
    # 2026-08-04: a 12-entry legend inside the axes covered the traces it was labelling. Move it outside.
    aC.legend(fontsize=6.6,loc="upper left",bbox_to_anchor=(1.01,1.0),frameon=False)
    aC.set_title("Successful-ablation — selected traces (combined)",loc="left",fontweight="bold",fontsize=10)
    fC.tight_layout(); fC.savefig(f"{OUT}/G4_ablation_intensity_combined.png",bbox_inches="tight"); plt.close(fC)
    lib.record_plot("G4_ablation_intensity_combined",["batch","abl_seq","series","time_from_ablation_s","kt_intensity_start1"],_ccrows,
      {"type":"selected targeted+sister traces (combined)","normalization":"each curve start-normalized to 1 (norm_series)",
       "picks":str(ABL_COMBINED_PICKS),"no_sister":str(sorted(ABL_COMBINED_NO_SISTER))},SCRIPT,"Successful-ablation selected traces (combined)")
    print(f"complete-ablation combined plot: {len(ABL_COMBINED_PICKS)} picks")
else:
    print("complete-ablation combined plot: FLAG/TODO — ABL_COMBINED_PICKS empty. Requested row3col1, "
          "row3col5, row10col2 need the Jun-26 contact-sheet ordering; fill from G4_ablation_contactsheet_index.csv.")

# ---------------- ITEM4: NEW selected successful-ablation combined plot (rescaled so min=0) ----------------
# Analogue of the FRAP combined but on the successful-ablation data: targeted (solid) + sister (dashed), each
# start-normalized to 1 (norm_series). Picks from the successful-ablation contact sheet (G4_ablation_contactsheet_index):
#   r1c4 20250404 ptk #0 / r2c4 20250410 ptk #0 / r3c1 20250423 ptk #0 (<=26s) / r8c3 20250904 tri #2 (<=20s) /
#   r8c6 20250923 tri #0 / r12c6 20251002 max #5 (drop ~10s targeted point -> open circle) / r23c6 20260420 ptk #0 (<=21s)
import matplotlib.lines as _mlS
ABL_SEL_PICKS=[
  ("20250404 ptk_yfpcdc20_16",0,None,None),
  ("20250410 ptk_yfpcdc20_17",0,None,None),
  ("20250423 ptk_yfpcdc20_20",0,26,None),
  # USER 2026-08-05: "remove the sample with the pink line" -> 20250904 triple_ablation_8 #2 dropped.
  ("20250923 triple_ablation_collagen_2",0,None,None),
  ("20251002 max_ablation_1_2",5,None,"drop_targeted_near_10"),
  ("20260420 ptk2 eyfp cdc20 1 ablation_8",0,21,None),
]
# USER 2026-08-05, four more changes to this figure:
#  * "stop the plot before 30s (many of the lines have a datapoint just after 25s, at like 27-28s and i
#    want that still displayed)" -> XMAX_SEL is an AXIS limit, not a data cut, so those 27-28 s points stay.
#  * "dim the tracking lines for the individual samples so that the trendlines are easier to see".
#  * "make sure that the ... targeted kinetochore flourescence is at 0 at the first timepoint after 0s ...
#    for each sample" -> ZERO_AT_FIRST_POST below.
#  * "if there is a negative readout for this plot ... just put it at 0" -> CLAMP_NEG.
XMAX_SEL   = 29.5      # axis stops before 30 s; the ~27-28 s points are still inside it
# USER 2026-08-05: "20260420 ptk2 eyfp cdc20 1 ablation_8 #0: just 'shift' the timepoints of the line such
# that the first timepoint is at -3 with the other points [following]". Its series started at +3.03 s, so
# every one of its timepoints moves by a constant -6.03 s. A SHIFT, not a rescale: the spacing between its
# points is untouched, only the origin moves, which is what puts its pre-ablation point where the other
# samples' pre-ablation points sit. Keyed by (batch, seq) so it cannot leak onto another trace.
ABL_SEL_TSHIFT = {("20260420 ptk2 eyfp cdc20 1 ablation_8", 0): -6.03}
DIM_ALPHA  = 0.35      # per-sample traces
DIM_LW     = 1.0
ZERO_AT_FIRST_POST = True
CLAMP_NEG  = True
_neg_clamped = 0       # counted so the legend note can state how many points were affected
_sister_dropouts = []  # (batch, seq, t) of removed drop-to-zero sister points
fS,aS=plt.subplots(figsize=(9.0,5.2)); _n_sel=0; _selrows=[]
_aggTt=[]; _aggQt=[]; _aggTs=[]; _aggQs=[]   # aggregate-trend accumulators (targeted / sister)
# ITEM4b (2026-07-07): the y-axis was stretched to ~2.0 by ONE off-scale sister point (20251002
# max_ablation_1_2 #5 sister ~1.97), so the axis never tightened to the real recovery range (~0-1.3). Cap the
# axis at YCAP_SEL and, for ANY point above it (on targeted OR sister curves), remove that point from the line
# and mark it with a small hollow open circle placed ON the line (interpolated between the kept neighbours) —
# the same technique already used for the FA1 dropped targeted point. The curve stays continuous, the marker
# flags the off-scale point, and the axis calibrates to the bulk of the data.
YCAP_SEL=1.4
def _clip_cap(Tk,Q):
    """Return (Tk_kept, Q_kept, [(x,y_on_line),...]) with points > YCAP_SEL removed and replaced by an
    on-the-line marker position (interpolated from the kept points)."""
    if Tk is None or Q is None: return Tk,Q,[]
    Tk=np.asarray(Tk,float); Q=np.asarray(Q,float)
    over=Q>YCAP_SEL
    if not over.any(): return Tk,Q,[]
    keepT=Tk[~over]; keepQ=Q[~over]; marks=[]
    if keepT.size>=2:
        _o=np.argsort(keepT)
        for _x in Tk[over]: marks.append((float(_x),float(np.interp(_x,keepT[_o],keepQ[_o]))))
    return keepT,keepQ,marks
for b,si,tmax,special in ABL_SEL_PICKS:
    if (b,si) not in seqmap: print(f"  SELECTED PICK NOT FOUND: {b!r} #{si}"); continue
    (Tt,Qt,_),(Tss,Qs,_)=norm_series(*seqmap[(b,si)])
    # ORDER MATTERS. `tmax` in ABL_SEL_PICKS was chosen by eye on each sample's OWN unshifted clock, so it
    # is applied first, inside _cap. The shift is applied AFTER that cut and BEFORE the XMAX_SEL cut, which
    # is a display window on the common clock. Shifting first would have let tmax=21 admit points out to
    # the original 27 s for the one shifted sample.
    _sh=ABL_SEL_TSHIFT.get((b,si))
    def _cap(Tk,Q):
        if Tk is None or Q is None: return None,None
        Tk=np.asarray(Tk,float); Q=np.asarray(Q,float)
        if tmax is not None: mm=Tk<=tmax; Tk,Q=Tk[mm],Q[mm]
        if _sh: Tk=Tk+_sh
        # USER 2026-08-05: "after the last point of a line in that range dont continue the line".
        # Setting only an axis limit still drew the segment running from the last in-range point out to
        # the next off-axis one, so the line appeared to leave the plot. Cut the DATA at XMAX_SEL: each
        # trace now ends at its own last real point inside the range.
        mm=Tk<=XMAX_SEL; Tk,Q=Tk[mm],Q[mm]
        return Tk,Q
    Tt,Qt=_cap(Tt,Qt); Tss,Qs=_cap(Tss,Qs)
    if _sh and Tt is not None and np.asarray(Tt).size:
        print(f"  time-shifted {b} #{si} by {_sh:+.2f} s (first point now {float(np.min(Tt)):+.2f} s)")
    # USER 2026-08-05: several SISTER traces dive to zero just before 10 s and shoot straight back up —
    # a single-frame dropout (the KT left the plane / lost the dot), not biology. Remove the offending
    # point so the line no longer spikes. Identified structurally, not by hard-coded time: a point at
    # ~zero whose BOTH neighbours are high. Every removal is logged so the edit is auditable.
    if Qs is not None and np.asarray(Qs).size >= 3:
        _T=np.asarray(Tss,float); _Q=np.asarray(Qs,float); _keep=np.ones(_Q.size,bool)
        for _i in range(1,_Q.size-1):
            if _Q[_i]<=0.05 and _Q[_i-1]>=0.30 and _Q[_i+1]>=0.30:
                _keep[_i]=False; _sister_dropouts.append((b,si,float(_T[_i])))
        Tss,Qs=_T[_keep],_Q[_keep]
    # USER 2026-08-05: scale EACH sample so its TARGETED curve reads 0 at the first timepoint after 0 s
    # ("make sure that this on-target scaling ... is done for each sample" — the lime trace sat at 0.59).
    # y' = (y - v0)/(1 - v0): the pre-ablation start stays 1 and the first post-ablation point becomes 0.
    # The SAME affine is applied to that cell's sister curve so the pair stays on one common scale.
    if ZERO_AT_FIRST_POST and Qt is not None and np.asarray(Qt).size:
        _T=np.asarray(Tt,float); _Q=np.asarray(Qt,float); _post=np.where(_T>0)[0]
        if _post.size:
            _v0=float(_Q[_post[0]]); _den=1.0-_v0
            if abs(_den)>1e-6:
                Qt=(np.asarray(Qt,float)-_v0)/_den
                if Qs is not None and np.asarray(Qs).size: Qs=(np.asarray(Qs,float)-_v0)/_den
    if CLAMP_NEG:
        # USER 2026-08-05: "if there is a negative readout for this plot ... just put it at 0."
        # (background-subtracted intensity can go slightly below zero; the per-sample zeroing above can
        # also push a point negative.) Counted so the legend note can state the exact number.
        if Qt is not None and np.asarray(Qt).size:
            _a=np.asarray(Qt,float); _neg_clamped += int((_a<0).sum()); Qt=np.clip(_a,0,None)
        if Qs is not None and np.asarray(Qs).size:
            _a=np.asarray(Qs,float); _neg_clamped += int((_a<0).sum()); Qs=np.clip(_a,0,None)
    removed=None
    if special=="drop_targeted_near_10" and Qt is not None and Tt.size:
        idx=int(np.argmin(np.abs(Tt-10.0))); removed=float(Tt[idx])   # FA1: keep only the x; y goes ON THE LINE
        Tt=np.delete(Tt,idx); Qt=np.delete(Qt,idx)
    # ITEM4b: pull off-scale (>YCAP_SEL) points off both curves; each becomes a hollow marker on the line
    Tt,Qt,_over_t=_clip_cap(Tt,Qt); Tss,Qs,_over_s=_clip_cap(Tss,Qs)
    col=None
    if Qt is not None and np.asarray(Qt).size:
        ln,=aS.plot(Tt,Qt,marker="o",ms=3,lw=DIM_LW,alpha=DIM_ALPHA,label=f"{b} #{si}"); col=ln.get_color(); _n_sel+=1
        _aggTt+=list(np.asarray(Tt,float)); _aggQt+=list(np.asarray(Qt,float))
        for _x,_y in zip(Tt,Qt): _selrows.append([b,si,"targeted",round(float(_x),3),round(float(_y),4),0])
        if removed is not None:
            _yl=float(np.interp(removed,Tt,Qt))   # FA1: marker ON THE LINE at that x (not the removed y) -> lets y-axis autoscale
            aS.plot([removed],[_yl],marker="o",mfc="none",mec=col,ms=5,mew=1.2,ls="none",zorder=6)  # FA1: smaller (~other markers)
            _selrows.append([b,si,"targeted_offscale",round(float(removed),3),round(_yl,4),1])
        for _x,_yl in _over_t: aS.plot([_x],[_yl],marker="o",mfc="none",mec=col,ms=5,mew=1.2,ls="none",zorder=6); _selrows.append([b,si,"targeted_offscale",round(float(_x),3),round(float(_yl),4),1])
    if Qs is not None and np.asarray(Qs).size:
        aS.plot(Tss,Qs,marker="s",ms=3,ls="--",lw=DIM_LW,alpha=DIM_ALPHA,color=col)
        _aggTs+=list(np.asarray(Tss,float)); _aggQs+=list(np.asarray(Qs,float))
        for _x,_y in zip(Tss,Qs): _selrows.append([b,si,"sister",round(float(_x),3),round(float(_y),4),0])
        for _x,_yl in _over_s: aS.plot([_x],[_yl],marker="o",mfc="none",mec=(col or SC),ms=5,mew=1.2,ls="none",zorder=6); _selrows.append([b,si,"sister_offscale",round(float(_x),3),round(float(_yl),4),1])
# aggregate TRENDLINES (user's terminal request): one across ALL targeted (on-target) traces, one across ALL
# sister (off-target) traces, binned-median (med_trend, 6s bins). Drawn bold on top of the per-sample lines.
_bt,_mt=med_trend(np.array(_aggTt),np.array(_aggQt)); _bs,_ms=med_trend(np.array(_aggTs),np.array(_aggQs))
if _bt: aS.plot(_bt,_mt,color="#8b0000",lw=3,marker="o",ms=6,zorder=8,label="targeted (median trend)")
if _bs: aS.plot(_bs,_ms,color="#08306b",lw=3,marker="s",ms=6,ls="--",zorder=8,label="sister (median trend)")
aS.axhline(1,color="#999",lw=1.0,ls="--"); aS.axvline(0,color="#333",ls=":",lw=1)
aS.set_xlim(right=XMAX_SEL)   # USER 2026-08-05: stop before 30 s, keeping the 27-28 s points
aS.set_ylim(0,YCAP_SEL)          # ITEM4/4b: floor at 0 (no negative fluorescence), cap at the recovery range; off-scale pts -> hollow markers on the line
_h,_l=aS.get_legend_handles_labels()
_h+=[_mlS.Line2D([],[],color="#333",ls="-",marker="o",ms=4),
     _mlS.Line2D([],[],color="#333",ls="--",marker="s",ms=4),
     _mlS.Line2D([],[],color="#333",ls="none",marker="o",mfc="none",ms=5,mew=1.2)]
_l+=["targeted (solid)","sister (dashed)","open circle = off-scale / missing point (on line)"]
aS.legend(_h,_l,fontsize=6.3,loc="upper left",bbox_to_anchor=(1.01,1.0))
aS.set_xlabel("Time from ablation (s)"); aS.set_ylabel("eYFP-Cdc20 KT intensity (start=1)")
aS.set_title("Successful-ablation — selected traces (combined, min=0)",loc="left",fontweight="bold",fontsize=10)
fS.tight_layout(); fS.savefig(f"{OUT}/G4_ablation_intensity_selected_combined.png",bbox_inches="tight"); plt.close(fS)
lib.record_plot("G4_ablation_intensity_selected_combined",["batch","abl_seq","series","time_from_ablation_s","kt_intensity_start1","off_scale"],_selrows,
  {"type":"selected targeted(solid)+sister(dashed) traces, min=0 rescale","normalization":"each curve start-normalized to 1 (norm_series)",
   "ycap":YCAP_SEL,"off_scale":">YCAP or FA1-dropped point plotted as hollow marker ON the line","picks":str([(p[0],p[1]) for p in ABL_SEL_PICKS]),
   # USER 2026-08-05: "if there is a negative readout ... just put it at 0. and then make a note in the
   # legend notes file". The legend-notes file is generated FROM these recorded settings, so the note has
   # to live here to reach it. Stating the count, not just the rule, so the legend can be specific.
   "negative_clamped_to_zero": (f"{_neg_clamped} point(s) read below 0 after background subtraction and the "
                                "per-sample zeroing, and were set to 0. Negative fluorescence above "
                                "background is not physical; the alternative (letting cytosol "
                                "over-subtraction go negative) would put points below the axis floor."),
   "zero_at_first_post_ablation": ("each sample is affinely rescaled so its TARGETED curve reads 1 at the "
                                   "pre-ablation start and 0 at its first timepoint after 0 s; the SAME "
                                   "affine is applied to that cell's sister curve so the pair shares one scale"),
   "sister_dropouts_removed": (f"{len(_sister_dropouts)} single-frame sister drop-out point(s) removed "
                               "(a ~zero point whose both neighbours are high — the KT left the plane); "
                               f"removed at {[(x[0], x[1], round(x[2],1)) for x in _sister_dropouts]}"),
   "x_shift": str(ABL_SEL_TSHIFT)},
  SCRIPT,"Successful-ablation selected traces (combined, min=0)")
print(f"  selected-combined: {_neg_clamped} negative point(s) clamped to 0; "
      f"{len(_sister_dropouts)} sister drop-out point(s) removed {[(x[0][-12:],x[2]) for x in _sister_dropouts]}")
print(f"successful-ablation SELECTED combined plot: {_n_sel} traces -> {OUT}/G4_ablation_intensity_selected_combined.png")

def med_at(allT,allQ,center,half=6):
    m=(allT>=center-half)&(allT<center+half)
    return (None,0) if not m.sum() else (float(np.median(allQ[m])),int(m.sum()))
print(f"successful-ablation intensity: {n_tgt+n_sis} of {n_possible} possible lines drawn ({n_tgt} targeted + {n_sis} sister) across {ncell} cells, {len(rec)} measurements")
print(f"  dropped curves: {drop_baseline} non-positive-baseline (bg>signal) + {drop_empty} artifact-dominated; {n_rejected} curves kept after rejecting artifact frames (all logged)")
print("  targeted (red) / sister (blue), each start-normalized to 1:")
for c in (0,30,45):
    qt,nt=med_at(allT_t,allQ_t,c); qs,ns=med_at(allT_s,allQ_s,c)
    print(f"  t~{c:>2}s  targeted n={nt:3d} med={None if qt is None else round(qt,3)}   sister n={ns:3d} med={None if qs is None else round(qs,3)}")
lib.flush_review(f"{OUT}/G4_ablation_intensity_review.csv")
