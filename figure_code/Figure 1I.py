"""pre- vs post-ablation intensity at marked KT points (targeted & paired), cytosol-normalized.
pre_abl/pre_abl_pair measured on their frame, post_abl/post_abl_pair on theirs; each normalized to the
cytosol_bg on that same frame. Pairs matched by nearest xy. Shows ablation success (targeted signal loss)."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, glob, json, os, numpy as np, cv2, matplotlib.pyplot as plt
import matplotlib.lines as mlines
from collections import defaultdict
from scipy import stats
import lib
lib.apply_style()
OUT="/Volumes/4 MB/ablation_figures_20260625/group4"; SCRIPT=__file__
import os as _osR; OUT=_osR.environ.get("KT_SWEEP_OUT",OUT); _osR.makedirs(OUT,exist_ok=True)
R=int(__import__("os").environ.get("KT_R","9"))   # standard r=9 (lib.disk_sum default)
rows=list(csv.reader(open("/Volumes/4 MB/annotations/kt_points.csv"))); ix={c:i for i,c in enumerate(rows[0])}
P=defaultdict(lambda: defaultdict(list))   # batch -> label -> [(frame,t,x,y)]
for r in rows[1:]:
    b=r[ix['batch']].strip(); lab=r[ix['label']].strip()
    if lib.is_prophase_ablation(b): continue   # prophase excluded (no prophase group)
    if lib.is_mad1(b) or lib.plot_excluded(b): continue
    if lib.is_misplaced_id(r[ix['id']]): continue
    if lab not in ("pre_abl","pre_abl_pair","post_abl","post_abl_pair","cytosol_bg"): continue
    try: P[b][lab].append((int(r[ix['frame']]),float(r[ix['t_sec']]),float(r[ix['x']]),float(r[ix['y']])))
    except: pass
def nn(a,B):  # nearest in B to a by xy
    return min(B,key=lambda b:(a[2]-b[2])**2+(a[3]-b[3])**2) if B else None

rec=[]; tgt_pre=[];tgt_post=[];par_pre=[];par_post=[];par_b=[];par_link=[]; tgt_b=[]; ncell=0
for b in sorted(P):
    if lib.excluded(b): continue   # 07-07 feedback: drop user-flagged outlier (e.g. two_sisterless_kinetochores_5 ~80min) from ALL plots
    pa,pap=P[b].get("pre_abl",[]),P[b].get("pre_abl_pair",[])
    qa,qap=P[b].get("post_abl",[]),P[b].get("post_abl_pair",[])
    cy=P[b].get("cytosol_bg",[])
    if not (pa and qa and cy): continue
    ft=lib.FluorTif(b,'ablation')                # 16-bit cropped fluor TIF (validated vs render MP4)
    if not ft.ok(): continue
    def meas(f,x,y,snap):
        """KT disk Σ (snapped to punctum for intact KTs) minus the marked cytosol disk Σ on the same frame.
        Located by FRAME (ground-truth index), NOT t_sec (frames.json t_sec is shifted 1-2 frames)."""
        g=ft.plane_by_frame(f)
        if g is None: return None
        c=min(cy,key=lambda c:abs(c[0]-f)); cval=lib.disk_sum(g,c[2],c[3],R)   # cytosol bg on the KT's frame (no snap)
        if cval is None: return None
        if snap: x,y=lib.snap_to_peak(g,x,y)
        if lib.is_saturated(g,x,y,R) or lib.is_saturated(g,c[2],c[3],R): return None   # clipped pixel -> unquantifiable
        return lib.disk_sum(g,x,y,R)-cval
    used=False
    for pre in pa:                                   # each targeted ablation
        post=nn(pre,qa)
        if post is None: continue
        prep=nn(pre,pap); postp=nn(post,qap)          # the paired KT pre/post
        # pre_abl intact -> snap; post_abl is the ABLATED site -> NO snap
        tp=meas(pre[0],pre[2],pre[3],True); tq=meas(post[0],post[2],post[3],False)
        if tp is None or tq is None: continue
        tgt_pre.append(tp); tgt_post.append(tq); tgt_b.append(b)
        _ti=len(tgt_pre)-1                            # index of this targeted ablation (for pair linkage)
        if prep and postp:
            # pre_abl_pair intact -> snap; post_abl_pair (sister) still intact -> snap OK
            pp=meas(prep[0],prep[2],prep[3],True); pq=meas(postp[0],postp[2],postp[3],True)
            if pp is not None and pq is not None:
                par_pre.append(pp); par_post.append(pq); par_b.append(b); par_link.append(_ti)
        used=True
    ft.close()
    if used: ncell+=1

# --- s65 broken-background screen + 07-07 feedback removals (PP1/PP2) ---
# s65: an INTACT kinetochore before ablation IS bright (that is the whole signal) and a successful ablation
# drops it to ~background — so we keep the clipped-pixel guard (in meas()) and drop ONLY pairs with a broken
# background (post hugely negative => the cytosol-bg disk overlapped signal => measurement error), never a
# point for being legitimately bright pre-ablation.
# All screens set keep-masks over the ORIGINAL indexing (par_link references it), then arrays are materialized
# once at the end so the targeted<->paired cascades stay index-consistent.
# 2026-07-08 feedback (user's (a)/(b) call): a NEGATIVE post is a fully-ablated KT reading BELOW background =
# a SUCCESSFUL ablation, NOT an error. So do NOT delete negatives — FLOOR them at 0 (the KT went to ~zero, which
# is the truth). A negative PRE is spurious and is caught by the increase screen below (post>pre=0 -> removed).
tgt_pre=[max(0.0,float(x)) for x in tgt_pre]; tgt_post=[max(0.0,float(x)) for x in tgt_post]
par_pre=[max(0.0,float(x)) for x in par_pre]; par_post=[max(0.0,float(x)) for x in par_post]
_tk=[True]*len(tgt_pre)     # keep-mask over targeted ablations
_pk=[True]*len(par_pre)     # keep-mask over paired (sister) KTs

# (BLUE-DATACLEAN 2026-07-14, user: "the sister/paired group changed recently and now looks worse/incorrect")
# The paired/sister group is 100% MANUAL (pre_abl_pair/post_abl_pair). Recently-added marks introduced three
# kinds of BROKEN MEASUREMENTS (not 'legit blue rises' — that rule is about real biological increases, which
# we still keep). Remove + log each for RE-ANNOTATION; the MATCH pass below then drops the now-unpaired red so
# #red==#blue. NO percentile/sharpest-rise trimming (that over-filter was reverted 2026-07-10).
#  (i) PRE at/below background (floored pre==0): the pre_abl_pair mark landed OFF the intact sister KT — an
#      intact sister is bright (thousands) before ablation, it cannot read ~background. 8 such sisters.
for j in range(len(par_pre)):
    if _pk[j] and par_pre[j]<=0:
        _pk[j]=False
        lib.log_review("prepost_paired_pre_background",par_b[j],f"pre={par_pre[j]:.0f} post={par_post[j]:.0f}",
            "sister pre_abl_pair reads at/below background (mismark: annotation off the intact sister KT) — removed; RE-ANNOTATE")
#  (ii) EXACT DUPLICATE (same batch + identical pre/post) — e.g. 20260420 ablation_73 appears twice (the ~10^6
#       spike double-counted). Keep the first occurrence only.
_seen=set()
for j in range(len(par_pre)):
    if not _pk[j]: continue
    key=(par_b[j],round(par_pre[j],1),round(par_post[j],1))
    if key in _seen:
        _pk[j]=False
        lib.log_review("prepost_paired_duplicate",par_b[j],f"pre={par_pre[j]:.0f} post={par_post[j]:.0f}","exact-duplicate paired point — de-duplicated")
    else: _seen.add(key)
#  (iii) IMPOSSIBLE >20x rise: a sister jumping >20x pre->post (e.g. 20260420 ablation_73, x242 to ~910,969)
#        is the post_abl_pair mark snapping onto a saturated/neighbouring punctum, NOT a real control rise
#        (legit sister rises are modest). Absolute-impossibility threshold, NOT a percentile trim.
for j in range(len(par_pre)):
    if _pk[j] and par_pre[j]>0 and par_post[j]/par_pre[j]>20:
        _pk[j]=False
        lib.log_review("prepost_paired_impossible_rise",par_b[j],f"pre={par_pre[j]:.0f} post={par_post[j]:.0f} x{par_post[j]/par_pre[j]:.0f}",
            "sister post_abl_pair jumped >20x pre->post (mark snapped to a saturated/neighbour punctum) — removed; RE-ANNOTATE")

# (PP2) any TARGETED pair that INCREASES pre->post is physically wrong for an ablated KT -> remove it AND its paired
for i in range(len(tgt_pre)):
    if _tk[i] and tgt_post[i]>tgt_pre[i]:
        _tk[i]=False
        lib.log_review("prepost_targeted_increase",tgt_b[i],f"pre={tgt_pre[i]:.0f} post={tgt_post[i]:.0f}","targeted KT intensity INCREASED pre->post (physically wrong for ablation) — pair removed; review")
        for j in range(len(par_pre)):
            if par_link[j]==i: _pk[j]=False

# (RED-FLAT) 2026-07-10 (user, corrected): in the TARGETED (red) group ONLY, a pre/post pair that stays
# roughly the SAME — a near-horizontal connector, against the group's steep drop trend (median post/pre≈0.01,
# a ~100x drop) — means the ablation was ineffective. Flag the batch for review, remove that red pair, AND
# remove its corresponding blue (sister) pair so the red/blue pairs stay matched. Threshold is calibrated to
# the trend: post/pre > 0.5 = dropped by LESS THAN HALF = clearly not following the ~100x-drop trend = flat.
# (This is red-only; blue/control rises stay — see PP2b note below.)
FLAT_RATIO=0.5
for i in range(len(tgt_pre)):
    if _tk[i] and tgt_pre[i]>0 and tgt_post[i]/tgt_pre[i]>FLAT_RATIO:
        _tk[i]=False
        _fr=tgt_post[i]/tgt_pre[i]
        lib.log_review("prepost_targeted_flat",tgt_b[i],
            f"pre={tgt_pre[i]:.0f} post={tgt_post[i]:.0f} post/pre={_fr:.2f}",
            f"targeted (red) pre≈post (post/pre>{FLAT_RATIO:.1f}; group trend drops ~100x) = near-horizontal "
            f"connector = ineffective ablation — red pair removed + review; matched blue sister removed to keep red/blue paired")
        for j in range(len(par_pre)):
            if par_link[j]==i: _pk[j]=False

# (PP2b) REMOVED 2026-07-10 (user): the paired/blue group is the ACCOMPANYING (control/sister) group, which is
# NOT ablated — so a sister rising pre->post is legitimate biology, not an artifact. Rises are only physically
# wrong in the ON-TARGET (red) group, which PP2 already handles. Blanket-removing paired rises deleted valid
# control data (had cut the blue group to 55/110). Do NOT re-add a paired-increase filter.

# (PP1) REMOVED 2026-07-10 (user): trimming the 2 sharpest paired rises + 2 sharpest falls touched the control
# group (rises there are legitimate) and its cascade cut on-target points too. Reverting to the ~36-hr-ago look.
# Only bad_bg (broken measurement) + PP2 (impossible on-target rise) remain.

# (BLUE-PLUMMET) 2026-07-10 (user): the accompanying/control (blue) sister is NOT ablated, so it must not
# CRASH pre->post. Remove a blue pair that starts HIGH (pre>5000) and either hits ~0 (post<2000, Tier A) or
# plummets hard (post/pre<=0.10, Tier B, ending elevated) — such a crash is an artifact (sister lost focus /
# mistracked / actually clipped by the beam). Remove it AND its matched red. KEEP sisters that sit near zero on
# BOTH sides (low pre) or only modestly decline (ratio>0.10 & post>=2000) — those are legitimate control data.
BLUE_PRE_HI, BLUE_POST_LO, BLUE_RATIO_LO = 5000.0, 2000.0, 0.10
for j in range(len(par_pre)):
    if _pk[j] and par_pre[j]>BLUE_PRE_HI and (par_post[j]<BLUE_POST_LO or par_post[j]/par_pre[j]<=BLUE_RATIO_LO):
        _pk[j]=False
        _br=par_post[j]/par_pre[j] if par_pre[j] else float('nan')
        lib.log_review("prepost_paired_plummet",par_b[j],
            f"pre={par_pre[j]:.0f} post={par_post[j]:.0f} post/pre={_br:.3f}",
            f"accompanying/control (blue) sister CRASHED pre->post (pre>{BLUE_PRE_HI:.0f} & (post<{BLUE_POST_LO:.0f} "
            f"or ratio<={BLUE_RATIO_LO:.2f})); not ablated so should not crash = artifact — removed + matched red removed")
        _i=par_link[j]
        if 0<=_i<len(_tk): _tk[_i]=False   # remove the matched red too

# (MATCH) 2026-07-10 (user): the plot should show only MATCHED red<->blue pairs. A surviving targeted (red)
# with no surviving accompanying/paired (blue) point — or a surviving blue whose targeted was dropped — is
# unpaired. Remove it + flag for review so #red == #blue. (par_link[j] = the targeted index for paired j.)
_has_sister={i:False for i in range(len(tgt_pre))}
for j in range(len(par_pre)):
    if _pk[j] and 0<=par_link[j]<len(_tk) and _tk[par_link[j]]: _has_sister[par_link[j]]=True
for i in range(len(tgt_pre)):
    if _tk[i] and not _has_sister[i]:
        _tk[i]=False
        lib.log_review("prepost_unpaired_targeted",tgt_b[i],f"pre={tgt_pre[i]:.0f} post={tgt_post[i]:.0f}","targeted (red) has no plottable accompanying/blue pair (checked kt_points.csv: either the pre_abl_pair/post_abl_pair manual annotation is incomplete, or the annotated pair KT disk is saturated/unmeasurable) — removed so #red==#blue")
for j in range(len(par_pre)):
    if _pk[j] and not (0<=par_link[j]<len(_tk) and _tk[par_link[j]]):
        _pk[j]=False
        lib.log_review("prepost_unpaired_paired",par_b[j],f"pre={par_pre[j]:.0f} post={par_post[j]:.0f}","accompanying/blue point has no corresponding targeted (red) on the plot — removed so #red==#blue")

# materialize the filtered arrays (original indexing preserved above so cascades stayed consistent)
tgt_pre=[tgt_pre[i] for i in range(len(tgt_pre)) if _tk[i]]
tgt_post=[tgt_post[i] for i in range(len(tgt_post)) if _tk[i]]
tgt_b=[tgt_b[i] for i in range(len(tgt_b)) if _tk[i]]
par_pre=[par_pre[j] for j in range(len(par_pre)) if _pk[j]]
par_post=[par_post[j] for j in range(len(par_post)) if _pk[j]]
par_b=[par_b[j] for j in range(len(par_b)) if _pk[j]]
# The plotted N labels already use the POST-removal arrays (len(tgt_pre) etc.), but the title's "cells" count
# was `ncell` from the PRE-removal loop. Recompute it over the KEPT batches so the title fully reflects the
# removals (N=<targeted> ablations, <cells> cells) — was showing the pre-mask 68.
ncell=len({*tgt_b,*par_b})
# rebuild CSV rows from the final filtered data
rec=[[tgt_b[i],"targeted",round(tgt_pre[i],1),round(tgt_post[i],1)] for i in range(len(tgt_pre))]
rec+=[[par_b[j],"paired",round(par_pre[j],1),round(par_post[j],1)] for j in range(len(par_pre))]

# ITEM 5: the "dotted"/thin diagonal lines are the PAIRED CONNECTORS — each line ties ONE kinetochore's
# pre value to its own post value (all targeted KTs in red, all paired sister KTs in blue). They are NOT a
# single highlighted example; they show the within-KT pre->post change. Render two versions: with and without.
TC="#d62728"; SC="#1f77b4"
def _dark(c, f=0.62):
    """A darker version of a plot colour -- used for the mean/median markers so they read as ANNOTATION on
    top of the same-coloured scatter (user 2026-08-19, item 11: "increasing the widths of the mean/median
    lines and perhaps making these mean/median lines a darker version of the color used")."""
    import matplotlib.colors as _mc
    r, g, b = _mc.to_rgb(c)
    return (r * f, g * f, b * f)


def render(draw_lines, fname):
    """USER 2026-08-19 (to-do list 0819 1pm), item 11 -- every point of it:
         "making the y-axis label standard with other y-axis labels"        -> canon_labels form
         "making sure no text overlapped with either other text or plot features"
                                                                            -> the med values moved into the
                                                                               axis footer with the Ns; the
                                                                               leader-line callouts are gone
         "placing the legend notes for mean and median line types in the upper right hand corner as it is in
          other plots"                                                      -> loc="upper right"
         "removing the stat data you list above the plots"                  -> the two Wilcoxon blocks are gone
         "increasing the widths of the mean/median lines and perhaps making these mean/median lines a darker
          version of the color used"                                        -> lw 2.5->4.2 / 1.2->2.4, _dark()
         "labels on it are too sparse"                                      -> explicit dense symlog ticks
       The Wilcoxon statistics are NOT lost -- they are still computed and recorded into the figure's data
       record via record_plot, they are simply no longer drawn on the artboard."""
    fig,ax=plt.subplots(figsize=(7.4,5.6))
    # symlog, not log: post-ablation intensities floor at ~0 after background subtraction and a pure log axis
    # would drop them entirely. Linear below `linthresh`, logarithmic above it.
    ax.set_yscale("symlog",linthresh=2000)
    if draw_lines:
        for pre,post in zip(tgt_pre,tgt_post): ax.plot([0,1],[pre,post],color=TC,alpha=.4,lw=1,marker="o",ms=3,zorder=2)
        for pre,post in zip(par_pre,par_post): ax.plot([2,3],[pre,post],color=SC,alpha=.4,lw=1,marker="s",ms=3,zorder=2)
    _meds={}
    def box(x,vals,col):
        if not vals: return
        ax.scatter([x]*len(vals),vals,color=col,s=10,alpha=.5,zorder=1)
        md_=np.median(vals); mn_=np.mean(vals); _meds[x]=(md_,mn_)
        dc=_dark(col)
        ax.hlines(md_,x-.26,x+.26,color=dc,lw=4.2,zorder=4)                          # median = solid, wide
        ax.hlines(mn_,x-.22,x+.22,color=dc,lw=2.4,ls=(0,(2,1.5)),zorder=4)           # mean   = dashed
    box(0,tgt_pre,TC);box(1,tgt_post,TC);box(2,par_pre,SC);box(3,par_post,SC)
    ax.set_xticks([0,1,2,3]); ax.set_xticklabels(["targeted\npre","targeted\npost","paired\npre","paired\npost"],fontsize=10)
    ax.set_xlim(-0.5,3.5)
    # ── y ticks: her "labels on it are too sparse" ────────────────────────────────────────────────────
    # symlog defaults to one label per decade, which on this range is 3 labels for the whole axis. Label the
    # linear part explicitly and then every decade AND its 2x/5x steps above the threshold.
    _top=max([v for vs in (tgt_pre,tgt_post,par_pre,par_post) for v in vs] or [1e4])
    _ticks=[0,500,1000,2000]
    _d=1e3
    while _d<=_top*10:
        for _m in (2,5,10):
            _t=_d*_m
            if 2000<_t<=_top*1.6: _ticks.append(_t)
        _d*=10
    _ticks=sorted(set(_ticks))
    ax.set_yticks(_ticks)
    ax.set_yticklabels([f"{int(t):,}" for t in _ticks],fontsize=7.5)
    ax.set_ylim(bottom=min(0,min([v for vs in (tgt_pre,tgt_post,par_pre,par_post) for v in vs] or [0])))
    # ── legend: upper RIGHT, as in the other plots (item 11) ──────────────────────────────────────────
    ax.legend(handles=[mlines.Line2D([],[],color="#333",lw=4.2,ls="-"),
                       mlines.Line2D([],[],color="#333",lw=2.4,ls=(0,(2,1.5)))],
              labels=["median","mean"],fontsize=7.5,ncol=1,loc="upper right",framealpha=.9)
    # ── N and median value in the axis FOOTER, where nothing can overlap them (item 11) ───────────────
    for x,vals in [(0,tgt_pre),(1,tgt_post),(2,par_pre),(3,par_post)]:
        if not vals: continue
        md_=_meds.get(x,(float("nan"),))[0]
        # offset must clear the TWO-LINE x tick labels below the axis, or the footer prints on top of them
        # (that is exactly the "no text overlapped with either other text or plot features" case, item 11).
        ax.annotate(f"N={len(vals)}  ·  med {md_:,.0f}",xy=(x,0),xycoords=("data","axes fraction"),
                    xytext=(0,-62),textcoords="offset points",ha="center",va="top",fontsize=8,color="#444")
    import canon_labels as _CL
    ax.set_ylabel(_CL.canon_axis("Kinetochore eYFP-Cdc20 (a.u.)"))
    _sub="lines connect each KT's own pre-to-post" if draw_lines else "paired connector lines removed"
    ax.set_title(f"Pre- vs post-ablation KT intensity (N={len(tgt_pre)} ablations, {ncell} cells)\n{_sub}",loc="left",fontweight="bold",fontsize=10.5)
    plt.tight_layout(); plt.savefig(f"{OUT}/{fname}",bbox_inches="tight"); plt.close()

# the Wilcoxon results are still COMPUTED and recorded (they left the artboard, not the record) -- item 11
_W_TGT = float(stats.wilcoxon(tgt_pre,tgt_post).pvalue) if len(tgt_pre)>5 else None
_W_PAR = float(stats.wilcoxon(par_pre,par_post).pvalue) if len(par_pre)>5 else None
render(True,"G4_prepost_intensity.png")           # with paired connector lines (original)
render(False,"G4_prepost_intensity_nolines.png")  # without the connector lines (companion)
lib.record_plot("G4_prepost_intensity",["batch","kt","pre_over_cytosol","post_over_cytosol"],rec,
  {"type":"paired pre/post (connected)","background":"local annulus (p40), floors at ~0","match":"pre/post & pair by nearest xy","stat":"Wilcoxon targeted pre vs post","wilcoxon_p_targeted":_W_TGT,"wilcoxon_p_paired":_W_PAR,"note_2026_08_19":"stat text removed FROM THE FIGURE at her request (item 11); the p-values live here"},
  SCRIPT,"Pre- vs post-ablation intensity at marked KT points (targeted & paired)")
# nolines companion plots the IDENTICAL data (only the paired connector lines are omitted) -> same rows, own CSV
lib.record_plot("G4_prepost_intensity_nolines",["batch","kt","pre_over_cytosol","post_over_cytosol"],rec,
  {"type":"paired pre/post (connector lines removed)","background":"local annulus (p40), floors at ~0","match":"pre/post & pair by nearest xy","stat":"Wilcoxon targeted pre vs post","companion_of":"G4_prepost_intensity"},
  SCRIPT,"Pre- vs post-ablation intensity at marked KT points (no connector lines)")
lib.flush_review("/Volumes/4 MB/ablation_figures_20260625/_review/g4_review.csv")
# audit-named copy: the PP1 (sharp paired) + PP2 (increasing targeted) + broken-background removals are logged
# here under an explicit prepost-review filename so the removals are directly verifiable.
lib.flush_review("/Volumes/4 MB/ablation_figures_20260625/_review/G4_prepost_intensity_review.csv")
print(f"pre/post: targeted N={len(tgt_pre)}, paired N={len(par_pre)}, cells={ncell}")
print(f"pre/post removals -> targeted kept {sum(_tk)}/{len(_tk)}, paired kept {sum(_pk)}/{len(_pk)} "
      f"(review: _review/G4_prepost_intensity_review.csv)")
