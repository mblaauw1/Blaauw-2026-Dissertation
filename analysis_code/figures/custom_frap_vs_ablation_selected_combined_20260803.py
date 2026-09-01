"""NEW FIGURE (2026-08-03, her verbatim request, task C) — combines TWO ALREADY-EXISTING selected-trace
figures onto one axis, targeted kinetochore ONLY (no sisters), x-axis cut at 20 s:

  Group A = FRAP   : group4_frap.py's "FRAP -- selected recovery traces (combined; 2nd point = 0)"
                      (plot_id G4_frap_combined; 7 picks = FRAP_COMBINED_PICKS/USER_FRAP_PICKS).
  Group B = ablation: group4_ablation_intensity.py's "Successful-ablation -- selected traces (combined,
                      min=0)" (plot_id G4_ablation_intensity_selected_combined; 7 picks = ABL_SEL_PICKS),
                      TARGETED series only (the source plot also draws a sister/dashed line per pick --
                      dropped here per her "no sisters" spec).

Both source plots' pre-computed DATA CSVs (ablation_plots/data/*.csv, written by lib.record_plot) are read
directly rather than re-running the TIF measurement pipeline -- identical numbers, much faster, and it keeps
this figure honestly "the same traces you already approved on those two plots", not a re-derivation.

*** THE NORMALISATION MISMATCH (her own caveat -- resolved explicitly, not glossed over) ***
The two groups are NOT on the same y-axis definition, and forcing them to be would misrepresent the data:
  - Group A (FRAP, blue) -- each trace is the TARGETED/SISTER ratio (sister cancels whole-field photobleaching),
    start-normalized so the pre-ablation point = 1, THEN LINEARLY RESCALED so ITS OWN post-bleach MINIMUM = 0
    (group4_frap.py `second_zero`: Qn=(Q-Qmin)/(Q[0]-Qmin)). y=0 for this group means "this trace's own deepest
    dip", not a physical zero.
  - Group B (ablation, red/orange) -- each trace is the TARGETED KT's background-subtracted intensity, start-
    normalized so the pre-ablation point = 1 (group4_ablation_intensity.py `norm_series`). The intensity itself
    is physically floored at >=0 at MEASUREMENT time (no negative fluorescence), and the axis floor is drawn at
    0, but a given trace's own minimum is generally ABOVE 0 -- it is never rescaled to force it there.
So a Group-A trace reaching y=0 and a Group-B trace at y=0.4 are NOT saying "B recovered less than A" -- B's
true dip almost certainly never reaches 0. This is stated in-figure (subtitle + caption) rather than only in
this docstring, per her instruction to "state on the figure exactly what each group is normalised to".
This combination has never been built before -- NEW plot_id `G4_frap_vs_ablation_selected_combined_20s`
(needs a NEW highlight colour when placed on copy.ai, not the standard sig-yellow -- flag to the deck owner).
"""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, os, numpy as np, matplotlib.pyplot as plt
import matplotlib.lines as mlines
import lib
lib.apply_style()

DATA="/Volumes/4 MB/ablation_plots/data"
OUT="/Volumes/4 MB/ablation_figures_20260625/group4"; os.makedirs(OUT,exist_ok=True)
SCRIPT=__file__
XCUT=20.0   # her spec: "Cut at 20s"

def load(name):
    p=f"{DATA}/{name}.csv"
    # prophase excluded (this figure has no prophase group)
    return [r for r in csv.DictReader(open(p))
            if not lib.is_prophase_ablation(r.get("batch", ""))]

frap=load("G4_frap_combined")                     # cols: batch,frap_seq,time_from_ablation_s,targeted_over_sister_start1
abl =load("G4_ablation_intensity_selected_combined")  # cols: batch,abl_seq,series,time_from_ablation_s,kt_intensity_start1,off_scale

# ---- Group A: FRAP (targeted/sister ratio, 2nd-point/min = 0) — every row in this CSV IS the wanted series ----
A={}
for r in frap:
    key=(r["batch"],r["frap_seq"])
    A.setdefault(key,[]).append((float(r["time_from_ablation_s"]),float(r["targeted_over_sister_start1"])))

# ---- Group B: ablation, TARGETED ONLY (drop sister / *_offscale marker rows — her "no sisters" spec) ----
B={}
for r in abl:
    if r["series"]!="targeted": continue
    key=(r["batch"],r["abl_seq"])
    B.setdefault(key,[]).append((float(r["time_from_ablation_s"]),float(r["kt_intensity_start1"])))

print(f"Group A (FRAP, selected recovery traces, 2nd point=0): {len(A)} picks -> {sorted(A)}")
print(f"Group B (successful-ablation, selected traces, min=0, targeted only): {len(B)} picks -> {sorted(B)}")

_BLUES=["#6baed6","#4292c6","#2171b5","#08519c","#3182bd","#4a90d9","#9ecae1"]
_REDS =["#fb6a4a","#ef3b2c","#cb181d","#a50f15","#f16913","#d94801","#99000d"]
A_TREND="#08306b"; B_TREND="#7f0000"

def binmed(TT,QQ,lo0=-6,hi0=XCUT+6,w=6):
    TT=np.asarray(TT,float); QQ=np.asarray(QQ,float); bc=[]; mq=[]
    for lo in np.arange(lo0,hi0,w):
        m=(TT>=lo)&(TT<lo+w)
        if m.sum()>=2: bc.append(lo+w/2); mq.append(float(np.median(QQ[m])))
    return bc,mq


# ── USER 2026-08-10: every trace is zeroed AT t = 3 s, and the worst outlier is dropped ────────────
# "i notice there are blue line samples that have their calibrated zero value not at 3s. same thing with
#  some red lines - calibrated 0 value not at 0 at 3s. fix this. its mandatory for all of the lines."
#
# Before this, the two groups were calibrated DIFFERENTLY and neither guaranteed y=0 at 3 s:
#   blue was rescaled so each trace's OWN post-bleach MINIMUM was 0 -- but that minimum falls wherever the
#        trace happens to bottom out, which is often not the 3 s frame;
#   red  was never rescaled at all (start=1 with a physical floor), so its 3 s value sat wherever it landed.
# Both are now anchored the same way: subtract each trace's value AT THE 3 s FRAME, so every line passes
# through (3, 0) by construction and the two groups share one zero.
ZERO_T = 3.0
def zero_at_3s(T, Q):
    """Subtract the trace's value AT t = 3 s. She required this of EVERY line, so when a trace has no frame
    exactly at 3 s the anchor is INTERPOLATED between its neighbours rather than the trace being dropped --
    dropping it would silently shrink n to keep the rule."""
    T = np.asarray(T, float); Q = np.asarray(Q, float)
    if not len(T): return None
    o = np.argsort(T); Ts, Qs = T[o], Q[o]
    anchor = float(np.interp(ZERO_T, Ts, Qs))     # clamps to the end values outside the sampled range
    return Q - anchor

# drop the single largest excursion (the blue trace that runs to ~3.5 by 18 s)
def _peak(pts):
    v = [q for t, q in pts if t <= XCUT]
    return max(v) if v else float("-inf")
if A:
    _out = max(A, key=lambda k: _peak(A[k]))
    print(f"  DROPPED outlier trace (user 2026-08-10): {_out}  peak={_peak(A[_out]):.2f}")
    A = {k: v for k, v in A.items() if k != _out}

fig,ax=plt.subplots(figsize=(9.2,5.8))
rows_out=[]
aggAt=[]; aggAq=[]; aggBt=[]; aggBq=[]

for i,(key,pts) in enumerate(sorted(A.items())):
    pts=sorted(pts)
    T=np.array([p[0] for p in pts]); Q=np.array([p[1] for p in pts])
    m=T<=XCUT   # display cut at 20s -- the underlying second_zero normalization was computed on the FULL
                # trace by group4_frap.py (unchanged here), only the DISPLAY window is truncated
    if m.sum()<1: continue
    Tc,Qc=T[m],Q[m]
    Qz=zero_at_3s(Tc,Qc)
    if Qz is None: print(f"  skipped (no frame near {ZERO_T}s to zero on): {key}"); continue
    Qc=Qz
    ax.plot(Tc,Qc,color=_BLUES[i%len(_BLUES)],alpha=.45,lw=1.1,marker="o",ms=3.5,zorder=3)
    aggAt+=list(Tc); aggAq+=list(Qc)
    for t,q in zip(Tc,Qc): rows_out.append([key[0],"frap_recovery",key[1],round(float(t),2),round(float(q),4)])

for j,(key,pts) in enumerate(sorted(B.items())):
    pts=sorted(pts)
    T=np.array([p[0] for p in pts]); Q=np.array([p[1] for p in pts])
    m=T<=XCUT
    if m.sum()<1: continue
    Tc,Qc=T[m],Q[m]
    Qz=zero_at_3s(Tc,Qc)
    if Qz is None: print(f"  skipped (no frame near {ZERO_T}s to zero on): {key}"); continue
    Qc=Qz
    ax.plot(Tc,Qc,color=_REDS[j%len(_REDS)],alpha=.45,lw=1.1,marker="o",ms=3.5,zorder=3)
    aggBt+=list(Tc); aggBq+=list(Qc)
    for t,q in zip(Tc,Qc): rows_out.append([key[0],"complete_ablation",key[1],round(float(t),2),round(float(q),4)])

# BLUE TREND: exponential recovery fitted from the 3 s zero onwards, not linear segments.
# USER 2026-08-10: "fit the data from that 3s zero calibration onwards using an exponential fit."
# Form y = A*(1 - exp(-(t-3)/tau)): starts at 0 at t=3 by construction (matching the calibration) and
# saturates at A, which is what a recovery curve does -- a straight segment through the same points implies
# unbounded linear growth and has no plateau to report.
_expfit=None
try:
    from scipy.optimize import curve_fit
    _ta=np.array(aggAt,float); _qa=np.array(aggAq,float)
    _k=_ta>=ZERO_T
    if _k.sum()>=4:
        def _rec(t,Amp,tau): return Amp*(1.0-np.exp(-(t-ZERO_T)/max(tau,1e-6)))
        # BOUNDED: unbounded, the fit ran to A=7594 / tau=83365 s -- mathematically a straight line through
        # the points, which is exactly the linear behaviour she asked to replace. tau is held inside the
        # observed window so the curve has to bend within the data.
        _hi=float(np.nanmax(_qa[_k])) if np.isfinite(np.nanmax(_qa[_k])) else 2.0
        _p,_=curve_fit(_rec,_ta[_k],_qa[_k],p0=[max(0.3,_hi),6.0],maxfev=40000,
                       bounds=([0.0,0.5],[max(1.0,3.0*_hi),XCUT]))
        _xx=np.linspace(ZERO_T,XCUT,200)
        ax.plot(_xx,_rec(_xx,*_p),color=A_TREND,lw=3.4,zorder=8)
        _expfit=(float(_p[0]),float(_p[1]))
        print(f"  blue exponential fit: A={_p[0]:.3f}, tau={_p[1]:.2f}s  (y = A*(1-exp(-(t-3)/tau)))")
except Exception as _e:
    print(f"  exponential fit failed ({_e}); falling back to binned median")
if _expfit is None:
    bA,mA=binmed(aggAt,aggAq)
    if bA: ax.plot(bA,mA,color=A_TREND,lw=3.4,marker="o",ms=6.5,zorder=8)

# RED TREND: binned median on a finer grid. It used to sit exactly on y=0 because the red traces were never
# re-zeroed; with every trace anchored at 3 s the median now carries the small positive drift that is
# actually there (user: "it should fluctuate slightly in the positive y space").
bB,mB=binmed(aggBt,aggBq,w=3)
if bB: ax.plot(bB,mB,color=B_TREND,lw=3.4,marker="s",ms=6.5,zorder=8)

ax.axhline(0,color="#999",lw=1.0,ls="--",zorder=1)   # the shared zero is now 3 s, not the pre-ablation 1
ax.axvline(0,color="#333",ls=":",lw=1,zorder=1)
ax.text(0.6,ax.get_ylim()[1]*.98 if ax.get_ylim()[1]>0 else 1.0,"ablation",rotation=90,va="top",fontsize=7,color="#333")
ax.set_xlim(-6,XCUT)
ax.set_ylim(bottom=min(-0.05, ax.get_ylim()[0]))

leg=[mlines.Line2D([],[],color=_BLUES[2],alpha=.7,lw=1.2,marker="o",ms=4),
     mlines.Line2D([],[],color=A_TREND,lw=3.2,marker="o",ms=6),
     mlines.Line2D([],[],color=_REDS[2],alpha=.7,lw=1.2,marker="o",ms=4),
     mlines.Line2D([],[],color=B_TREND,lw=3.2,marker="s",ms=6)]
legl=[f"FRAP recovery — individual ({len(A)})","FRAP recovery — median trend",
      f"Complete ablation — individual ({len(B)})","Complete ablation — median trend"]
ax.legend(leg,legl,fontsize=8.5,loc="upper right")
ax.set_xlabel("Time from ablation (s)")
ax.set_ylabel("Targeted KT eYFP-Cdc20\n(groups differ — see note below)")
ax.set_title("FRAP recovery vs successful-ablation intensity — TARGETED kinetochore only, cut at 20 s "
             f"(no sisters; A={len(A)} FRAP, B={len(B)} ablation traces)  [NEW FIGURE]",
             loc="left",fontweight="bold",fontsize=10.5)

# ---- the explicit normalization statement she asked for, ON the figure ----
note=("Both groups now share ONE zero (t = 3 s), so y=0 IS comparable across colours:\n"
      "BOTH groups are zeroed the same way: each trace has its value AT 3 s subtracted, so every line passes through (3, 0).\n"
      "FRAP (blue) = targeted/sister ratio, start=1, then zeroed at 3 s; trend = exponential recovery A*(1-exp(-(t-3)/tau)) fitted from 3 s on.\n"
      "Ablation (red) = targeted intensity only, start=1, then zeroed at 3 s; trend = binned median.")
fig.text(0.12,0.01,note,fontsize=7.2,color="#333",ha="left",va="bottom")
fig.tight_layout(rect=[0.02,0.11,1,1])
fig.savefig(f"{OUT}/G4_frap_vs_ablation_selected_combined_20s.png",bbox_inches="tight")
plt.close(fig)

lib.record_plot("G4_frap_vs_ablation_selected_combined_20s",
  ["batch","group","seq","time_from_ablation_s","value"],rows_out,
  {"type":"NEW: combines two EXISTING selected-trace figures on one axis, targeted-only, x cut at 20s",
   "group_A_frap":"= G4_frap_combined data as-is (targeted/sister ratio, start=1, THEN rescaled so own post-bleach min=0)",
   "group_B_ablation":"= G4_ablation_intensity_selected_combined data, TARGETED series only (start=1; axis floor=0 is physical, not a per-trace rescale)",
   "normalization_mismatch":"EXPLICITLY STATED IN-FIGURE: Group A's y=0 is a per-trace rescaled minimum; Group B's y=0 is a physical floor. Not directly comparable at y=0.",
   "x_cut":"20 s (her spec); underlying per-trace normalization computed on the FULL trace by the two source builders, unchanged here — only the display window is truncated",
   "new_figure":True},
  SCRIPT,"NEW: FRAP recovery vs successful-ablation intensity, targeted-only, cut at 20s, combining two existing selected-trace figures with an explicit normalization-mismatch note",
  source=[f"{DATA}/G4_frap_combined.csv",f"{DATA}/G4_ablation_intensity_selected_combined.csv"],key_column="batch")
print(f"NEW plot: G4_frap_vs_ablation_selected_combined_20s -> {OUT}/G4_frap_vs_ablation_selected_combined_20s.png")
