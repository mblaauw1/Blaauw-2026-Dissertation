"""prophase-ablation metaphase dynamics: (A) abl->NEBD and (B) abl->metaphase vs metaphase duration."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import lib
lib.apply_style()
OUT="/Volumes/4 MB/ablation_figures_20260625/group2"; SCRIPT=__file__
data,_=lib.load_master()
_dbl=lib.double_chromosome_batches()   # l429: destruction of 2 KTs on one chromosome excluded from ALL plots (globally)
def md(r):
    d,ok=lib.mitotic_duration_min(r); return d if ok else None
def sis(r): return r.get("# Sisterless KTs","")
def am_src(r):
    """(abl->meta minutes, source) with the t=0=ablation recovery (D7, 2026-07-07): a prophase ablation is the
    first mitotic event, so where the stored 'Ablation->Meta' is blank we estimate it as Metaphase Start."""
    return lib.abl_to_meta_min(r, fallback_metastart=True)
def abl_to_meta_min(r): return am_src(r)[0]
proph=[r for r in data if r.get("Phase of Ablations","").strip().lower().startswith("proph") and not lib.is_v2_prometaphase(r["Batch Name"]) and r.get("Exclude") not in ("Yes","yes")
       and not lib.excluded(r["Batch Name"]) and not lib.is_mad1(r["Batch Name"])]
# ITEM 6 (feedback 2026-07-06): (1) REMOVE the grey/unassigned points — cells whose '# Sisterless KTs' is
# blank / 'kinetochoreless' (they previously plotted grey via the cmap default) — and (2) DROP the 2-sisterless
# group. Keep only cleanly-assigned 1- and 3-sisterless on-target cells. (Also drop ZM/noc drug cells.)
_before=len(proph)
proph=[r for r in proph if r.get("# Sisterless KTs","") in ("1","3") and not lib.is_drug(r["Batch Name"]) and r["Batch Name"] not in _dbl]  # l429: double-chromosome excluded globally
for _r in [r for r in data if r.get("Phase of Ablations","").strip().lower().startswith("proph") and r.get("Exclude") not in ("Yes","yes") and (r.get("# Sisterless KTs","") not in ("1","3") or lib.is_drug(r["Batch Name"]))]:
    lib.log_review("prophase_dyn_dropped",_r["Batch Name"],_r.get("# Sisterless KTs","")or"(blank)","dropped from prophase-dynamics: grey/unassigned sisterless, 2-sisterless, or drug (ITEM 6)")
print(f"prophase-dynamics: kept {len(proph)}/{_before} prophase cells (1- & 3-sisterless, non-drug)")

def _abl_to_nebd(r):
    am=abl_to_meta_min(r); meta=lib.parse_time(r.get("Metaphase Start (s)","")); neb=lib.parse_time(r.get("NEB Time (s)",""))
    if am is None or meta is None or neb is None: return None
    return am-(meta-neb)/60.0

# audio s35: the abl->NEBD x ~= -25 point is also very high on the right (duration) panel -> EXCLUDE from BOTH panels.
EXCL_BOTH=set()
for r in proph:
    an=_abl_to_nebd(r)
    if an is not None and an<-20:
        lib.log_review("prophase_outlier_both",r["Batch Name"],f"abl->NEBD {an:.1f}min, dur {md(r):.1f}min" if md(r) is not None else f"abl->NEBD {an:.1f}min",
                       "extreme abl->NEBD outlier (< -20min) EXCLUDED from BOTH panels; review"); EXCL_BOTH.add(r["Batch Name"])

# abl->meta (min), neb->meta (min) -> abl->nebd = abl_meta - neb_meta
# D7 (2026-07-07): abl->meta is recovered via the t=0=ablation model where the stored value is blank, so all
# 1-/3-sisterless prophase cells with a duration now plot (not just the ~4 with a stored interval). Points are
# tuples (val, dur, sis, source); estimated (metastart) points render hollow.
A=[];B=[]; rowsA=[];rowsB=[]
for r in proph:
    if r["Batch Name"] in EXCL_BOTH: continue
    dur=md(r); am,src=am_src(r)
    meta=lib.parse_time(r.get("Metaphase Start (s)","")); neb=lib.parse_time(r.get("NEB Time (s)",""))
    if dur is None: continue
    if am is not None and 0<=am<200:
        B.append((am,dur,sis(r),src)); rowsB.append([r["Batch Name"],round(am,2),round(dur,3),src])
    if am is not None and meta is not None and neb is not None:
        nebmeta=(meta-neb)/60.0; an=am-nebmeta
        if an<-5:   # implausible: ablation cannot precede NEBD for a prophase ablation — exclude from panel A (NEBD-derivation issue)
            lib.log_review("prophase_ablNEBD_outlier",r["Batch Name"],f"{an:.1f}min","abl->NEBD < -5min (implausible) EXCLUDED from panel A; review"); continue
        if an<200: A.append((an,dur,sis(r),src)); rowsA.append([r["Batch Name"],round(an,2),round(dur,3),src])

from scipy import stats
from matplotlib.lines import Line2D
CMAP={"1":lib.PALETTE["1-Sister"],"3":lib.PALETTE["3-Sister"]}
fig,axes=plt.subplots(1,2,figsize=(11,5),sharey=True)
for ax,(pts,xl,title) in zip(axes,[(A,"Time from ablation to NEBD (min)","A · abl-to-NEBD  (needs abl-to-meta, NEBD & Metaphase Start)"),
                                    (B,"Time from ablation to metaphase (min)","B · abl-to-metaphase  (needs abl-to-meta & metaphase duration)")]):
    _ntxt=[]
    for g in ("1","3"):   # PER-GROUP scatter + PER-GROUP trendline (no combined trend)
        gp=[p for p in pts if p[2]==g]
        if not gp: continue
        gm=[p for p in gp if p[3]!="metastart"]; ge=[p for p in gp if p[3]=="metastart"]
        if gm: ax.scatter([p[0] for p in gm],[p[1] for p in gm],s=34,color=CMAP[g],alpha=.85,edgecolor="white",lw=.4,zorder=3)
        if ge: ax.scatter([p[0] for p in ge],[p[1] for p in ge],s=34,facecolors="none",edgecolors=CMAP[g],lw=1.0,alpha=.9,zorder=3)
        gx=[p[0] for p in gm]; gy=[p[1] for p in gm]   # USER 2026-07-16: trendline/stats on FILLED (measured) points only; hollow(estimated) excluded
        _rt=""
        if len(gx)>=4:
            m,b=np.polyfit(gx,gy,1); xr=np.linspace(min(gx),max(gx),40); ax.plot(xr,m*np.array(xr)+b,"--",color=CMAP[g],lw=1.5,zorder=2)
            rho,p=stats.spearmanr(gx,gy); _rt=f", rho={rho:.2f}, p={p:.2g}"
        _ntxt.append(f"{g}-sis N={len(gx)}{_rt}")
    ax.text(.03,.97,"\n".join(_ntxt) if _ntxt else "N=0",transform=ax.transAxes,va="top",fontsize=8)
    ax.set_xlabel(xl); ax.set_title(title,fontsize=10)
axes[0].set_ylabel("Metaphase duration (MM:SS)")
axes[0].yaxis.set_major_formatter(FuncFormatter(lambda v,_: lib.mmss(v) if v>=0 else ""))
_nestA=sum(1 for p in A if p[3]=="metastart"); _nestB=sum(1 for p in B if p[3]=="metastart")
axes[1].legend(handles=[Line2D([0],[0],marker="o",color="w",markerfacecolor=CMAP[k],label=f"{k}-sisterless") for k in "13"]
               +[Line2D([0],[0],marker="o",color="w",markerfacecolor="none",markeredgecolor="#555",label="estimated (t=0=abl)")],
               fontsize=7.5,title="on-target group",loc="upper right")
fig.suptitle(f"Prophase-ABLATED cells (1- & 3-sisterless; grey/unassigned & 2-sisterless removed) — color = sisterless group; per-group trends\n"
             f"A (abl-to-NEBD, N={len(A)}; {_nestA} est.): abl-to-meta + NEBD + Metaphase Start.   "
             f"B (abl-to-metaphase, N={len(B)}; {_nestB} est.): abl-to-meta + metaphase duration.\n"
             f"D7 (2026-07-07): abl->meta recovered via 'first ablation = t=0' where the stored interval was blank (hollow markers) so all "
             f"prophase 1-/3-sisterless cells with a duration now plot.",
             x=.01,ha="left",fontweight="bold",fontsize=8.3)
plt.tight_layout(); plt.savefig(f"{OUT}/G2_prophase_dynamics.png",bbox_inches="tight"); plt.close()
lib.record_plot("G2_prophase_dynamics",["batch","x_min","mitotic_duration_min","abl_meta_source"],rowsA+[["--B--","","",""]]+rowsB,
  {"type":"2-panel scatter","A":"abl->NEBD (derived: abl->meta - (meta-NEB))","B":"abl->meta","subset":"prophase-ablated 1-/3-sisterless","trend":"per sisterless group","recovery":"abl->meta estimated as Metaphase Start (t=0=ablation) where blank; hollow markers",
   # the CSV pools both panels, so the x column is deliberately named generically - publish what it MEANS so
   # the zoom companion cannot fall back to labelling its axis "x_min" (user 2026-08-03)
   "x_label":"Time from ablation (min) - panel A: to NEBD, panel B: to metaphase",
   "y_label":"Metaphase duration (min)"},
  SCRIPT,"Prophase-ablation: abl->NEBD and abl->meta vs metaphase duration")
lib.flush_review("/Volumes/4 MB/ablation_figures_20260625/_review/outlier_review_prophase.csv")
from collections import Counter as _C
print(f"prophase dynamics: A(abl->NEBD) N={len(A)} ({_nestA} est), B(abl->meta) N={len(B)} ({_nestB} est) | EXCL_BOTH={sorted(EXCL_BOTH)}")
print(f"  A by sisterless: {dict(_C(p[2] or '?' for p in A))} | B by sisterless: {dict(_C(p[2] or '?' for p in B))}")

# ---- USER 2026-07-16: PROMETAPHASE version of this plot. For a prometaphase-ablated cell NEBD is already past,
# so the abl->NEBD panel (A) is meaningless -> only the abl->metaphase-vs-duration panel applies. Prometaphase
# cohort = Phase startswith 'promet' OR the v2=prometaphase rebin (is_v2_prometaphase). Same 1-/3-sisterless,
# non-drug, non-double, non-excluded filtering; same hollow=estimated (t=0=abl) recovery + measured-only trend.
prometa=[r for r in data if (r.get("Phase of Ablations","").strip().lower().startswith("promet") or lib.is_v2_prometaphase(r["Batch Name"]))
         and r.get("Exclude") not in ("Yes","yes") and not lib.excluded(r["Batch Name"]) and not lib.is_mad1(r["Batch Name"])
         and r.get("# Sisterless KTs","") in ("1","3") and not lib.is_drug(r["Batch Name"]) and r["Batch Name"] not in _dbl]
# PULLED (user 2026-07-17): prometaphase cells whose abl->meta could NOT be verified as t=0. For a
# prometaphase ablation the first ablation should be t=0; if the render/timing doesn't support that, the
# abl->meta is untrustworthy -> drop from this plot and flag for review (see _review/review_prometaphase.csv).
PROMETA_REVIEW_EXCLUDE={
 "20260113 snigle_ablation_visualize chromosome with sisterless kinetochore_1":
   "abl->meta not verifiable as t=0: frames.json is an 18-frame/3.5s z-stack (not the monitoring movie) in all renders, inconsistent with Metaphase Start 29.8min",
}
Bp=[]; rowsBp=[]
for r in prometa:
    if r["Batch Name"] in PROMETA_REVIEW_EXCLUDE:
        lib.log_review("prometa_ablation_not_t0", r["Batch Name"], "PULLED from plot",
                       PROMETA_REVIEW_EXCLUDE[r["Batch Name"]]+" — needs review")
        continue
    dur=md(r); am,src=am_src(r)
    if dur is None or am is None or not (0<=am<200): continue
    Bp.append((am,dur,sis(r),src)); rowsBp.append([r["Batch Name"],round(am,2),round(dur,3),src])
# ── ITEM 30 (user 2026-08-04) ─────────────────────────────────────────────────────────────────────
# "metaphase duration should be scaled from 0-1 for each cell and then whatever you're marking can be
#  placed on that depending on when in metaphase it occurs."
# So each cell's metaphase is normalised to its own 0-1 axis (0 = metaphase onset, 1 = anaphase onset) and
# the ABLATION is placed on that scale — the same transform used for G3_pole_time_vs_duration (item 27) and
# G4_lagging_vs_congression_fraction. These are PROMETAPHASE ablations, so the ablation precedes metaphase
# and lands BELOW 0; the value says how far before onset the ablation happened in units of that cell's own
# metaphase. That is what makes 1- and 3-sisterless comparable despite their different mean durations —
# in raw minutes they are not.
#   frac_abl = (t_ablation - metaphase_start) / (anaphase_onset - metaphase_start) = -(abl->meta) / duration
figp,axp=plt.subplots(figsize=(6.6,5.2))
_ntxt=[]
for g in ("1","3"):
    gp=[p for p in Bp if p[2]==g and p[1] and p[1]>0]
    if not gp: continue
    gm=[p for p in gp if p[3]!="metastart"]; ge=[p for p in gp if p[3]=="metastart"]
    _fx=lambda P:[p[1] for p in P]                 # x = that cell's metaphase duration (min)
    _fy=lambda P:[-(p[0]/p[1]) for p in P]         # y = ablation on the cell's normalised metaphase scale
    if gm: axp.scatter(_fx(gm),_fy(gm),s=34,color=CMAP[g],alpha=.85,edgecolor="white",lw=.4,zorder=3)
    if ge: axp.scatter(_fx(ge),_fy(ge),s=34,facecolors="none",edgecolors=CMAP[g],lw=1.0,alpha=.9,zorder=3)
    gx=_fx(gm); gy=_fy(gm)   # measured (filled) only; hollow(estimated) excluded from trend/stats
    _rt=""
    if len(gx)>=4:
        m,b=np.polyfit(gx,gy,1); xr=np.linspace(min(gx),max(gx),40); axp.plot(xr,m*np.array(xr)+b,"--",color=CMAP[g],lw=1.5,zorder=2)
        rho,p=stats.spearmanr(gx,gy); _rt=f", rho={rho:.2f}, p={p:.2g}"
    _ntxt.append(f"{g}-sis N={len(gx)}{_rt}")
# 2026-08-04: the per-group N/rho block sat at the top-LEFT, exactly where the y=0 and y=1 reference
# labels are drawn (0 and 1 are near the top of this axis, since the data run down to about -10). The three
# texts printed through each other. Reference labels move to the right edge; the stats block stays left.
axp.text(.03,.97,"\n".join(_ntxt) if _ntxt else "N=0",transform=axp.transAxes,va="top",fontsize=8)
axp.axhline(0,ls=":",color="#3b6fb6",lw=1.3)
axp.text(axp.get_xlim()[1],0,"metaphase onset (0) ",color="#3b6fb6",fontsize=7,va="bottom",ha="right")
axp.axhline(1,ls="--",color="#d1495b",lw=1.1)
axp.text(axp.get_xlim()[1],1,"anaphase onset (1) ",color="#d1495b",fontsize=7,va="bottom",ha="right")
axp.set_xlabel("Metaphase duration (MM:SS)")
axp.xaxis.set_major_formatter(FuncFormatter(lambda v,_: lib.mmss(v) if v>=0 else ""))
axp.set_ylabel("Ablation on the cell's normalised metaphase scale\n(0 = onset, 1 = anaphase; <0 = before metaphase)",fontsize=9)
_nestBp=sum(1 for p in Bp if p[3]=="metastart")
axp.legend(handles=[Line2D([0],[0],marker="o",color="w",markerfacecolor=CMAP[k],label=f"{k}-sisterless") for k in "13"]
           +[Line2D([0],[0],marker="o",color="w",markerfacecolor="none",markeredgecolor="#555",label="estimated (t=0=abl)")],
           fontsize=7.5,title="on-target group",loc="lower right")
figp.suptitle(f"Prometaphase-ABLATED cells (1- & 3-sisterless; v2=prometaphase rebin included) — ITEM 30: each cell's metaphase scaled 0-1\n"
              f"The ablation is placed on that per-cell scale, so 1- and 3-sisterless are comparable despite different mean durations. "
              f"Prometaphase ablations sit BELOW 0 (before metaphase onset).\n"
              f"N={len(Bp)} ({_nestBp} est.); NEBD panel omitted (NEBD precedes prometaphase). color = sisterless group; per-group trend on measured pts.",
              x=.01,ha="left",fontweight="bold",fontsize=8.0)
plt.tight_layout(); plt.savefig(f"{OUT}/G2_prometaphase_dynamics.png",bbox_inches="tight"); plt.close()
lib.record_plot("G2_prometaphase_dynamics",["batch","abl_to_meta_min","mitotic_duration_min","abl_meta_source","abl_frac_of_metaphase"],
  [r+[round(-(r[1]/r[2]),4) if r[2] else ""] for r in rowsBp],
  # x_label/y_label: real axis titles for the zoom companion (user 2026-08-03)
  {"type":"scatter","x":"abl->meta (min)","subset":"prometaphase-ablated 1-/3-sisterless (v2=prometaphase rebin incl.)","trend":"per sisterless group (measured only)","recovery":"abl->meta estimated as Metaphase Start (t=0=abl) where blank; hollow markers",
   "x_label":"Metaphase duration (min)",
   "y_label":"Ablation position on the cell's own metaphase scale (0=onset, 1=anaphase; negative=before metaphase)",
   "item30":"each cell's metaphase normalised 0-1; the ablation is placed on that scale"},
  SCRIPT,"Prometaphase-ablation: ablation position on the cell's normalised metaphase scale")
lib.flush_review("/Volumes/4 MB/ablation_figures_20260625/_review/review_prometaphase.csv")
print(f"prometaphase dynamics: B(abl->meta) N={len(Bp)} ({_nestBp} est) | by sisterless: {dict(_C(p[2] or '?' for p in Bp))} | pulled_for_review={list(PROMETA_REVIEW_EXCLUDE)}")


# ── ITEM 31 (user 2026-08-04): panel-B-only zoom, correctly labelled ──────────────────────────────
# The generic zoom companion read this figure's pooled data CSV (panel A rows, a '--B--' separator, then
# panel B rows) and plotted BOTH panels' x-values on one axis — abl->NEBD and abl->metaphase are different
# quantities, so the "single panel" zoom was not one measurement at all. Built here instead, panel B only
# (abl->metaphase, the panel that survives for a prophase ablation), with its own axis title.
_zb=[p for p in B if p[3]!="metastart"]          # measured points only, as in the parent
if len(_zb)>=5:
    _bx=np.array([p[0] for p in _zb]); _by=np.array([p[1] for p in _zb])
    _tr=lib.zoom_trim(_by, floor_zero=True)
    _hi=_tr["fence_hi"]; _keep=_by<=_hi; _ntr=int((~_keep).sum())
    figz,axz=plt.subplots(figsize=(7.0,5.0))
    for g in ("1","3"):
        m=np.array([p[2]==g for p in _zb]) & _keep
        if m.any():
            axz.scatter(_bx[m],_by[m],s=38,color=CMAP[g],alpha=.85,edgecolor="white",lw=.4,
                        label=f"{g}-sisterless (n={int(m.sum())})",zorder=3)
    if _keep.sum()>=4:
        _s,_c0=np.polyfit(_bx[_keep],_by[_keep],1); _xr=np.linspace(_bx[_keep].min(),_bx[_keep].max(),30)
        axz.plot(_xr,_s*_xr+_c0,"--",color="#333",lw=1.4,zorder=2)
        _rho,_pv=stats.spearmanr(_bx[_keep],_by[_keep])
        axz.text(.98,.02,f"Spearman rho={_rho:.2f}, p={_pv:.2g} (N={int(_keep.sum())})",transform=axz.transAxes,
                 ha="right",va="bottom",fontsize=8,bbox=dict(fc="#f6f6f6",ec="#ccc",alpha=.9))
    axz.set_xlabel("Time from ablation to metaphase (min)")     # ITEM 31: names ONE quantity, not two panels
    axz.set_ylabel("Metaphase duration (MM:SS)")
    axz.yaxis.set_major_formatter(FuncFormatter(lambda v,_: lib.mmss(v) if v>=0 else ""))
    axz.legend(fontsize=8)
    axz.set_title("G2_prophase_dynamics — outlier-trimmed zoom, PANEL B ONLY (abl-to-metaphase)\n"
                  f"ITEM 31: the previous zoom pooled panel A (abl-to-NEBD) and panel B on one axis. "
                  f"{_ntr} outlier(s) trimmed.",loc="left",fontweight="bold",fontsize=8.8)
    plt.tight_layout(); plt.savefig(f"{OUT}/G2_prophase_dynamics_zoom.png",bbox_inches="tight"); plt.close()
    lib.record_plot("G2_prophase_dynamics_zoom",["batch","abl_to_meta_min","mitotic_duration_min"],
        [[r[0],r[1],r[2]] for r,k in zip(rowsB,_keep) if k],
        {"type":"scatter (panel B only)","item31":"was pooling abl->NEBD and abl->meta on one axis",
         "x_label":"Time from ablation to metaphase (min)",
         "y_label":"Metaphase duration (min)","outliers_trimmed":_ntr},
        SCRIPT,"Prophase-ablation abl-to-metaphase vs metaphase duration (zoom, panel B only)")
    print(f"ITEM 31: prophase zoom rebuilt panel-B-only, N={int(_keep.sum())}, {_ntr} trimmed")
else:
    print(f"ITEM 31: only {len(_zb)} measured panel-B points — zoom not built")
