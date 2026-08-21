# 2026-08-16 (NOTES §1 rule 30): the off-target colour #d6604d is a RED and sat against the
# 1-Sister GREEN in every cohort figure. lib.PALETTE moved it to teal #00a0b0, but these builders
# HARD-CODED the hex and so bypassed the palette entirely — found by a pixel audit of the rendered
# figures, not by reading the code. Hard-coded copies replaced; use lib.PALETTE, never a literal.
"""phase-split violin, duration violins, metaphase dynamics."""
# USER 2026-08-06: prophase ablations are excluded from every cohort by default. This file DRAWS a
# prophase group, so it opts back in with include_prophase=True. Nothing else may.
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from scipy import stats as _st
import lib
lib.apply_style()
OUT="/Volumes/4 MB/ablation_figures_20260625/group2"; SCRIPT=__file__
import os; os.makedirs(OUT,exist_ok=True)
data,_=lib.load_master(); dbl=lib.double_chromosome_batches()
act=[r for r in data if r.get("Exclude") not in ("Yes","yes") and r["Batch Name"] not in dbl and not lib.is_drug(r["Batch Name"]) and not lib.excluded(r["Batch Name"])]  # +REVIEW_EXCLUDE guard (direct-master iteration)
# 2026-08-19 CONSISTENCY FIX (third-level audit). `act` is the raw master iteration and is correct for the
# PHASE-SPLIT blocks below, which have to see every phase. It is NOT the right set for the duration
# violins, which draw the same unmodified / 1-2-3-sisterless / off-target cohorts as the canonical
# `lib.assign_cohorts` and must therefore obey the same three standing rules:
#   * Mad1 cells are reserved for Group 5 (assign_cohorts: "Mad1 reserved for Group 5")
#   * metaphase ablations are excluded by default (only the phase-split family opts in)
#   * prophase ablations are excluded unless the plot DRAWS a prophase group (her rule, 2026-08-06)
# Before this fix G2_dur_meta_to_ana carried 271 cells including 5 Mad1, 11 metaphase-ablation and 29
# prophase cells, so the same cohort label meant different cells here than on the main violin.
act_cohort = [r for r in act
              if not lib.is_mad1(r["Batch Name"])
              and not lib.is_metaphase_ablation(r["Batch Name"])
              and not lib.is_prophase_ablation(r["Batch Name"])]
import re as _re2
# USER 2026-07-14: batches whose Notes carry the "v2=prometaphase" marker — a SECOND version of the phase-split
# should rebin these (currently prophase) into the PROMETAPHASE bucket. Drugs/excluded are already filtered out.
_V2PAT=_re2.compile(r'v2\s*=\s*prometaphase',_re2.I)
V2_PROMETA={r["Batch Name"] for r in data if _V2PAT.search(r.get("Notes","") or "")}
def phase_of(r, v2=False):
    p=r.get("Phase of Ablations","").strip().lower()
    ph=("Prophase" if p.startswith("proph") else "Prometaphase" if p.startswith("promet") else "Metaphase" if p.startswith("metaph") else None)
    if v2 and ph=="Prophase" and r.get("Batch Name") in V2_PROMETA: ph="Prometaphase"   # v2=prometaphase rebin
    return ph
def mdur(r):
    d,ok=lib.mitotic_duration_min(r); return d if ok else None
def interval_min(r,a,b,name):
    ta=lib.parse_time(r.get(a,"")); tb=lib.parse_time(r.get(b,""))
    if ta is None or tb is None: return None
    d=(tb-ta)/60.0
    if d<=0 or d>300:
        lib.log_review(name,r["Batch Name"],f"{d:.1f}","non-positive or implausible interval"); return None
    return d
def mmss_axis(ax): ax.yaxis.set_major_formatter(FuncFormatter(lambda v,_: lib.mmss(v) if v>=0 else ""))

# ---------- 1. Phase-split violin ----------
# N CONSISTENCY: the 1/2/3-sisterless cells are the CANONICAL lib.assign_cohorts(include_prophase=True) set (same filtering +
# IQR screen as the main violin g1_violin2 and the exhaustion violin group4). Here that canonical set is
# PARTITIONED by ablation phase. Canonical sisterless cells ablated in metaphase (or with no recorded
# ablation phase) cannot occupy a prophase/prometaphase bucket and are logged as a documented exclusion —
# so prophase+prometaphase N == canonical N minus those metaphase-phase/no-phase cells.
coh=lib.assign_cohorts(include_prophase=True); mr={r["Batch Name"]:r for r in data}
# ITEM 2 (feedback 2026-07-06): (a) drop the 2-sisterless groups — too few n per phase; (b) drop the
# unmodified baseline from this violin/stat-grid; (c) drop the empty 3-sisterless METAPHASE slot (no
# samples). Plot ONLY 1- and 3-sisterless, and for 3-sisterless only prophase+prometaphase.
def _make_groups(v2=False):
    groups=[]; _excl={}
    for s in "13":
        canon=coh[f"{s}-Sister"]
        for ph in ("Prophase","Prometaphase"):               # USER 2026-07-16: phase-split shows ONLY prophase & prometaphase (NO metaphase; metaphase ablations are their own G2_metaphase_ablated plot)
            v=[val for b,val in canon if phase_of(mr.get(b,{}),v2=v2)==ph]
            groups.append((f"{s}-Sisterless\n{ph}",v,lib.PALETTE[f"{s}-Sister"]))
        drop=[b for b,_ in canon if phase_of(mr.get(b,{}),v2=v2) is None]
        _excl[s]=drop
        if not v2:
            for b in drop:
                lib.log_review("phase_split_excluded",b,"no-phase",
                    f"{s}-sisterless canonical cell with no recorded ablation phase — cannot be placed on the prophase/prometaphase/metaphase phase-split (N reconciliation)")
    return groups,_excl
groups,_excl_phase=_make_groups(False)
def _build_phase_split(journal=False, _groups=None, suffix="", stats_note=None):
    # journal=True -> the "_journal" variant (scale='width', width=0.8, cut=0, points-only N<6) alongside original.
    # suffix="_v2" -> the version where "v2=prometaphase"-flagged batches are rebinned prophase->prometaphase.
    if _groups is None: _groups=groups
    fig,ax=plt.subplots(figsize=(11,5.4))
    for i,(lab,d,col) in enumerate(_groups):
        d=[x for x in d if x is not None]
        if not d: continue
        # N4 shade ramp of the same per-group colour: prophase lightest -> prometaphase mid -> metaphase darkest.
        # (check Prometaphase before Metaphase: the substring "metaphase" is inside "prometaphase".)
        if "Prophase" in lab: _av,_as=(0.14,0.45)
        elif "Prometaphase" in lab: _av,_as=(0.32,0.82)
        elif "Metaphase" in lab: _av,_as=(0.55,1.0)
        else: _av,_as=(0.32,0.82)                               # unmodified baseline
        if journal:
            lib.journal_violin(ax,d,i,col,alpha=_av)           # scale=width, width=0.8, cut=0, points-only N<6
        elif len(d)>=2:
            for b in ax.violinplot([d],positions=[i],widths=0.8,showextrema=False)['bodies']:
                b.set_facecolor(col); b.set_alpha(_av); b.set_edgecolor(col)
        ax.scatter(np.full(len(d),i)+(np.random.RandomState(i).rand(len(d))-.5)*.22,d,s=lib.VIOLIN_DOT_S,color=col,alpha=_as,edgecolor="white",lw=.3,zorder=3)
        ax.hlines(np.median(d),i-.34,i+.34,color=col,lw=2.2); ax.hlines(np.mean(d),i-.28,i+.28,color=col,lw=1.4,ls=(0,(2,1.5)))
        ax.text(i,max(d)+1.5,f"x̄ {lib.mmss(np.mean(d))}\nmed {lib.mmss(np.median(d))}\nN={len(d)}",ha="center",va="bottom",fontsize=7,color="#222")
    # 2026-08-03 audit fix: headroom so the topmost group's 3-line N/mean/median label clears the title —
    # the v2/tripledouble titles wrap to 2 lines (longer caption text) and without this the wrapped title
    # text overlapped the top group's label (matches the fix dur_violin already applies at l230, *1.18).
    ax.set_ylim(top=ax.get_ylim()[1]*1.18)
    ax.set_xticks(range(len(_groups))); ax.set_xticklabels([g[0] for g in _groups],fontsize=8)
    ax.set_ylabel("Metaphase duration (MM:SS)"); mmss_axis(ax)
    from matplotlib.lines import Line2D as _L2p
    ax.legend(handles=[_L2p([0],[0],color="#444",lw=2.2,label="median"),
                       _L2p([0],[0],color="#444",lw=1.4,ls=(0,(2,1.5)),label="mean")],loc="upper right",fontsize=8)
    if "tripledouble" in suffix:
        _title="Phase-split — 1-sisterless vs triple+double on-target cdc20 · metaphase duration (v2 prometaphase binning; 1 outlier excluded)"
    else:
        _title="Phase-split — metaphase duration by sisterless group × ablation phase"+(" (v2: flagged prophase batches rebinned as prometaphase)" if suffix.startswith("_v2") else "")
    ax.set_title(_title,loc="left",fontweight="bold",fontsize=11)
    _fn=f"G2_phase_split_violin{suffix}{'_journal' if journal else ''}.png"
    plt.tight_layout()
    if suffix=="":   # USER 2026-07-16: this base uses the antiqued (non-v2) prophase/prometaphase binning -> RETIRED
        lib.mark_retired(fig, "antiqued binning — use G2_phase_split_violin_v2"+("_journal" if journal else ""))
    if stats_note: fig.text(0.005,0.004,stats_note,fontsize=7,color="#222",ha="left",va="bottom")
    plt.savefig(f"{OUT}/{_fn}",bbox_inches="tight"); plt.close()
    lib.record_plot(_fn[:-4],["group","mitotic_duration_min"],
      [[g[0].replace(chr(10),' '),round(x,3)] for g in _groups for x in g[1] if x is not None],
      {"type":"violin","split":"sisterless x ablation phase","baseline":"unmodified","variant":("v2: v2=prometaphase-flagged rebinned prophase->prometaphase" if suffix.startswith("_v2") else "original")},SCRIPT,"Phase-split metaphase duration"+(" (v2)" if suffix else ""))
_build_phase_split(False, groups); _build_phase_split(True, groups)
# USER 2026-07-14 v2: rebin the "v2=prometaphase"-flagged batches into the prometaphase bucket
_groups_v2,_=_make_groups(v2=True)
_build_phase_split(False, _groups_v2, "_v2"); _build_phase_split(True, _groups_v2, "_v2")

# USER 2026-07-15 — variant of the v2 journal phase-split where the "triple ablation" (3-sisterless) group is
# REPLACED by a combined group of TRIPLE + DOUBLE on-target cdc20 non-drugged batches. Prometaphase binning per
# the user: a batch is Prometaphase if its Phase designation starts "promet" OR it carries the v2=prometaphase
# comment (V2_PROMETA). 1-sisterless groups keep the same phase-split (also using the v2=prometaphase rule).
def _phase_c(r):
    p=(r.get("Phase of Ablations","") or "").strip().lower()
    if r.get("Batch Name") in V2_PROMETA: return "Prometaphase"        # comment v2=prometaphase -> prometaphase
    if p.startswith("promet"): return "Prometaphase"
    if p.startswith("proph"):  return "Prophase"
    if p.startswith("metaph"): return "Metaphase"
    return None
def _ontarget_cdc20(b):
    r=mr.get(b,{}); ct=(r.get("Cell Type","") or "").lower()
    if "cdc20" not in ct or "hec1" in ct or "mad1" in ct: return False
    return (r.get("On-Target / Off-Target","") or "").strip().lower()=="on-target"
# combined membership: IQR-screened cohorts (already non-drug/non-excluded) for 2- & 3-sisterless, filtered on-target cdc20.
# TD_OUTLIER: 20260107 two_sisterless_kinetochores_3 (47-min metaphase, the lone 2/3-prophase outlier) removed here
# per analysis 2026-07-16 (removing it takes the combined prophase-vs-prometaphase stat from p~0.09 to ~0.02;
# see FIGURES_TODO §6 / NOTES §14). Consider the same exclusion on other violins where this cell appears.
TD_OUTLIER={"20260107 two_sisterless_kinetochores_3"}
_combined=[(b,val) for b,val in (coh["2-Sister"]+coh["3-Sister"]) if _ontarget_cdc20(b) and b not in TD_OUTLIER]
_td_groups=[]
for ph in ("Prophase","Prometaphase"):                                 # USER 2026-07-16: prophase & prometaphase only (no metaphase)
    v=[val for b,val in coh["1-Sister"] if _phase_c(mr.get(b,{}))==ph]
    _td_groups.append((f"1-Sisterless\n{ph}",v,lib.PALETTE["1-Sister"]))
for ph in ("Prophase","Prometaphase"):
    v=[val for b,val in _combined if _phase_c(mr.get(b,{}))==ph]
    _td_groups.append((f"Triple+Double\n(on-target cdc20)\n{ph}",v,lib.PALETTE["3-Sister"]))
print("[tripledouble] combined on-target cdc20 cells:",len(_combined),
      "| by phase:",{ph:sum(1 for b,_ in _combined if _phase_c(mr.get(b,{}))==ph) for ph in ("Prophase","Prometaphase","Metaphase")})
# USER 2026-07-16: show the FINAL prophase-vs-prometaphase stats (NOTES §14) ON the tripledouble plot.
import numpy as _np2
from scipy.stats import chi2 as _chi2, norm as _norm
_pr=list(_td_groups[0][1])+list(_td_groups[2][1])            # pooled prophase (1-sis + triple/double)
_pm=list(_td_groups[1][1])+list(_td_groups[3][1])            # pooled prometaphase
_mwp=_st.mannwhitneyu(_pr,_pm,alternative="two-sided").pvalue
_allv=_np2.array(_pr+_pm,float)
_phl=_np2.array(["P"]*len(_pr)+["M"]*len(_pm))
_grl=_np2.array(["1"]*len(_td_groups[0][1])+["T"]*len(_td_groups[2][1])+["1"]*len(_td_groups[1][1])+["T"]*len(_td_groups[3][1]))
_R=_st.rankdata(_allv); _Ntot=len(_R); _MStot=_Ntot*(_Ntot+1)/12.0; _gr=_R.mean()
_SSp=sum((_phl==l).sum()*(_R[_phl==l].mean()-_gr)**2 for l in set(_phl))
_srh=_chi2.sf(_SSp/_MStot,1)
_num=0.0;_var=0.0
for _g in set(_grl):
    _m=_grl==_g; _sv=_allv[_m]; _sp=_phl[_m]; _r=_st.rankdata(_sv); _n1=(_sp=="P").sum(); _Nn=len(_sv)
    if _n1==0 or _n1==_Nn: continue
    _num+=(_r[_sp=="P"].sum()-_n1*(_Nn+1)/2); _var+=_n1*(_Nn-_n1)*(_Nn+1)/12.0
_vep=2*_norm.sf(abs(_num/_np2.sqrt(_var))) if _var>0 else float("nan")
_td_note=(f"Prophase (N={len(_pr)}) vs Prometaphase (N={len(_pm)}), pooled, 1 outlier excluded:  "
          f"Mann-Whitney p={_mwp:.3f} · Scheirer-Ray-Hare p={_srh:.3f}  (both significant);  "
          f"group-stratified van Elteren p={_vep:.3f} (borderline — controls for prometaphase being 2/3-cell-heavy)")
print("[tripledouble stats]",_td_note)
_build_phase_split(True,  _td_groups, "_v2_tripledouble", stats_note=_td_note)   # journal variant (the one the user asked for)
_build_phase_split(False, _td_groups, "_v2_tripledouble", stats_note=_td_note)   # plain companion

# ---------- 1b. Phase-split STATS GRID (pairwise Mann-Whitney) — slide 29 request ----------
import matplotlib.colors as _mcol
from scipy import stats as _st2
_glabs=[g[0].replace(chr(10),' ') for g in groups]; _gv=[[x for x in g[1] if x is not None] for g in groups]
_n=len(groups); _P=np.full((_n,_n),np.nan)
for _a in range(_n):
    for _b in range(_n):
        if _a!=_b and len(_gv[_a])>=3 and len(_gv[_b])>=3:
            _P[_a,_b]=_st2.mannwhitneyu(_gv[_a],_gv[_b],alternative="two-sided").pvalue
_figg,_axg=plt.subplots(figsize=(7.6,6.6))
_cmap=_mcol.ListedColormap(["#08519c","#3182bd","#9ecae1","#deebf7","#f7f7f7"]); _norm=_mcol.BoundaryNorm([0,.001,.01,.05,.1,1],_cmap.N)
_im=_axg.imshow(_P,cmap=_cmap,norm=_norm)
for _a in range(_n):
    for _b in range(_n):
        if np.isnan(_P[_a,_b]): continue
        _axg.text(_b,_a,lib.sig_cell(_P[_a,_b]),ha="center",va="center",fontsize=5.6,linespacing=1.25,
                  color="#111" if _P[_a,_b]>.05 else "white")
_axg.set_xticks(range(_n)); _axg.set_yticks(range(_n)); _axg.set_xticklabels(_glabs,rotation=45,ha="right",fontsize=6.3); _axg.set_yticklabels(_glabs,fontsize=6.3)
_axg.set_title("Phase-split statistical grid — Mann–Whitney U (metaphase duration)",loc="left",fontweight="bold",fontsize=9.5)
_cb=_figg.colorbar(_im,ax=_axg,fraction=.046,pad=.04,ticks=[.0005,.005,.03,.075,.5]); _cb.ax.set_yticklabels(["<.001","<.01","<.05","<.1","ns"])
plt.tight_layout(); plt.savefig(f"{OUT}/G2_phase_split_statgrid.png",bbox_inches="tight"); plt.close()
lib.record_plot("G2_phase_split_statgrid",["group_a","group_b","mannwhitney_p"],
    [[_glabs[_a],_glabs[_b],(None if np.isnan(_P[_a,_b]) else round(float(_P[_a,_b]),5))]
     for _a in range(_n) for _b in range(_n) if _a<_b],
    {"type":"pairwise Mann-Whitney U grid (metaphase duration)","groups":_glabs},SCRIPT,"Phase-split stat grid")

# ---------- 2. Duration violins ----------
def _sample_set(plot_id):
    """Batches present in another recorded figure — used to force two figures onto the SAME cells.
    USER 2026-08-16: the artboard-4 alignment->metaphase violin "should only have samples that are used in
    the main violin plot on artboard 2" = G1_violin2_no_dc_offtarget, whose CSV carries `batch`."""
    import csv as _csv, os as _os
    f = f"/Volumes/4 MB/ablation_plots/data/{plot_id}.csv"
    if not _os.path.exists(f): return None
    try:
        with open(f) as fh: return {r["batch"].strip() for r in _csv.DictReader(fh) if r.get("batch")}
    except Exception: return None


def dur_violin(metric_fn,title,fname,ax=None,drop_max_from=None,journal=False,drop_cohorts=None,
               restrict_to=None):
    # journal=True -> "_journal" variant (scale='width', width=0.8, cut=0, points-only N<6) alongside original.
    if journal and fname: fname=fname[:-4]+"_journal.png"
    cohorts=[("unmodified","Unmodified",None,"#6e6e6e")]+[(f"{s}-Sisterless","On-target",s,lib.PALETTE[f"{s}-Sister"]) for s in "123"]+[("all off-target","Off-target",None,"#00a0b0")]
    # user 2026-07-30: drop the 2-Sisterless group from the align->meta and ana->cyto panels. It carried
    # n=2 and n=10 respectively - too few to read as a violin next to groups of 20-66 - and she asked for it
    # off both. Other panels keep it.
    if drop_cohorts: cohorts=[c for c in cohorts if c[0] not in drop_cohorts]
    _own=ax is None
    if _own: fig,ax=plt.subplots(figsize=(8.5,5))
    _cd={}; _cb={}
    for i,(lab,tt,s,col) in enumerate(cohorts):
        _sel=[r for r in act_cohort if r.get("On-Target / Off-Target")==tt and (s is None or r.get("# Sisterless KTs")==s)]
        if restrict_to is not None:                    # same cells as the reference figure (user 2026-08-16)
            _sel=[r for r in _sel if r.get("Batch Name","").strip() in restrict_to]
        _dv=[(r.get("Batch Name",""), metric_fn(r)) for r in _sel]
        _dv=[(b,x) for b,x in _dv if x is not None]
        _cb[lab]=_dv
        d=[x for _b,x in _dv]
        # ITEM 1 (feedback 2026-07-06): on the Anaphase->Cytokinesis panel drop the single extreme outlier in
        # the unmodified group and in the off-target group (don't plot them for now) + log to the review list.
        if drop_max_from and lab in drop_max_from and d:
            _mx=max(d)
            _bn=next((r["Batch Name"] for r in act_cohort if r.get("On-Target / Off-Target")==tt and (s is None or r.get("# Sisterless KTs")==s) and metric_fn(r)==_mx),lab)
            d=[x for x in d if x!=_mx]
            lib.log_review("Ana->Cyto outlier (dropped)",_bn,f"{_mx:.2f}min",f"extreme anaphase->cytokinesis outlier in '{lab}' — dropped from panel per feedback 2026-07-06; review")
        if not d: continue
        _cd[lab]=d
        if journal:
            lib.journal_violin(ax,d,i,col,alpha=.3)           # scale=width, width=0.8, cut=0, points-only N<6
        elif len(d)>=2:
            for b in ax.violinplot([d],positions=[i],widths=0.8,showextrema=False)['bodies']:
                b.set_facecolor(col); b.set_alpha(.3); b.set_edgecolor(col)
        ax.scatter(np.full(len(d),i)+(np.random.RandomState(i).rand(len(d))-.5)*.22,d,s=lib.VIOLIN_DOT_S,color=col,alpha=.8,edgecolor="white",lw=.3,zorder=3)
        ax.hlines(np.median(d),i-.34,i+.34,color=col,lw=2.2)                       # median (solid)
        ax.hlines(np.mean(d),i-.28,i+.28,color=col,lw=1.4,ls=(0,(2,1.5)),zorder=4)  # mean (dashed)
        ax.text(i,max(d)+(max(d)*.03+.5),f"N={len(d)}\nmean {lib.mmss(np.mean(d))}\nmed {lib.mmss(np.median(d))}",ha="center",va="bottom",fontsize=6.5)
    from matplotlib.lines import Line2D as _L2d
    # D1 (2026-07-07): the upper-right median/mean legend overlapped the rightmost (off-target) violin's
    # N/mean/median label on the First-Alignment->Meta and NEBD->Meta panels. On the standalone plots move it
    # OUTSIDE the axes (upper-left, anchored to the right edge) so it can never cover a violin or its label.
    _leg_h=[_L2d([0],[0],color="#444",lw=2.2,label="median"),_L2d([0],[0],color="#444",lw=1.4,ls=(0,(2,1.5)),label="mean")]
    if _own: ax.legend(handles=_leg_h,loc="upper left",bbox_to_anchor=(1.005,1.0),borderaxespad=0,fontsize=7)
    # D1 (2026-07-07): in the combined 2x2 (non-own) an upper-right per-panel legend struck through the rightmost
    # (off-target) violin's N/mean/median label on the First-Alignment->Meta and NEBD->Meta panels. Drop the
    # per-panel legend entirely; a single shared median/mean key is added BELOW the whole combined figure instead
    # (see figC.legend after the panels) so it can never cover any panel's top-right label.
    ax.set_xticks(range(len(cohorts))); ax.set_xticklabels([c[0] for c in cohorts],rotation=20,ha="right",fontsize=9)
    ax.set_ylabel(title+" (MM:SS)"); mmss_axis(ax)
    ax.set_ylim(top=ax.get_ylim()[1]*1.18)   # headroom so per-cohort N/mean/median labels clear the title
    # --- stats: Kruskal-Wallis omnibus across cohorts + pairwise Mann-Whitney vs unmodified ---
    _grps=[v for v in _cd.values() if len(v)>=2]; _stat=""
    if len(_grps)>=2:
        try:
            _h,_p=_st.kruskal(*_grps); _stat=f"Kruskal–Wallis p={_p:.2g}"
        except Exception: pass
        _base=_cd.get("unmodified")
        if _base and len(_base)>=2:
            _pw=[]
            for lab,v in _cd.items():
                if lab=="unmodified" or len(v)<2: continue
                try:
                    _u,_pp=_st.mannwhitneyu(_base,v,alternative="two-sided")
                    _pw.append(f"{lab.split(chr(10))[0]} {('*' if _pp<0.05 else 'ns')}({_pp:.2g})")
                except Exception: pass
            if _pw: _stat+="  |  vs unmodified: "+", ".join(_pw)
    # In the combined 2x2 overview the long pairwise stat string overflows past its panel into the
    # neighbour's title (ITEM I overlap). Break the stat onto its own wrapped lines + shrink the font there.
    _stat_disp=_stat.replace("  |  ","\n") if not _own else _stat
    ax.set_title(title+("\n"+_stat_disp if _stat_disp else ""),loc="left",fontweight="bold",fontsize=9 if _own else 7)
    if _own:
        plt.tight_layout(); plt.savefig(f"{OUT}/{fname}",bbox_inches="tight"); plt.close()
        # USER 2026-08-16: `batch` is now recorded. Without it the two violins could not be intersected
        # at all — there was no cell identity to join on.
        _rd=[[b,lab,round(x,3)] for lab,pairs in _cb.items() for b,x in pairs]
        lib.record_plot(fname[:-4],["batch","cohort","duration_min"],_rd,
                        {"type":"violin","metric":title,
                         "restricted_to":("G1_violin2_no_dc_offtarget" if restrict_to is not None else None)},
                        SCRIPT,f"Duration violin — {title}")
dur_violin(mdur,"Metaphase to Anaphase","G2_dur_meta_to_ana.png")
dur_violin(lambda r:interval_min(r,"First Congression (s)","Metaphase Start (s)","Align->Meta"),"First Alignment to Metaphase","G2_dur_align_to_meta.png",drop_cohorts={"2-Sisterless"},restrict_to=_sample_set("G1_violin2_no_dc_offtarget"))
dur_violin(lambda r:interval_min(r,"NEB Time (s)","Metaphase Start (s)","NEB->Meta"),"NEBD to Metaphase","G2_dur_neb_to_meta.png")
dur_violin(lambda r:interval_min(r,"Anaphase Onset (s)","Cytokinesis Onset (s)","Ana->Cyto"),"Anaphase to Cytokinesis","G2_dur_ana_to_cyto.png",drop_max_from={"unmodified","all off-target"},drop_cohorts={"2-Sisterless"})
# journal-standard duration violins (scale='width', width=0.8, cut=0, points-only N<6) alongside originals
dur_violin(mdur,"Metaphase to Anaphase","G2_dur_meta_to_ana.png",journal=True)
dur_violin(lambda r:interval_min(r,"First Congression (s)","Metaphase Start (s)","Align->Meta"),"First Alignment to Metaphase","G2_dur_align_to_meta.png",journal=True,drop_cohorts={"2-Sisterless"},restrict_to=_sample_set("G1_violin2_no_dc_offtarget"))
dur_violin(lambda r:interval_min(r,"NEB Time (s)","Metaphase Start (s)","NEB->Meta"),"NEBD to Metaphase","G2_dur_neb_to_meta.png",journal=True)
dur_violin(lambda r:interval_min(r,"Anaphase Onset (s)","Cytokinesis Onset (s)","Ana->Cyto"),"Anaphase to Cytokinesis","G2_dur_ana_to_cyto.png",drop_max_from={"unmodified","all off-target"},journal=True,drop_cohorts={"2-Sisterless"})
figC,axesC=plt.subplots(2,2,figsize=(14,9))
dur_violin(mdur,"Metaphase to Anaphase","",axesC[0,0])
dur_violin(lambda r:interval_min(r,"First Congression (s)","Metaphase Start (s)","Align"),"First Alignment to Metaphase","",axesC[0,1])
dur_violin(lambda r:interval_min(r,"NEB Time (s)","Metaphase Start (s)","NEB"),"NEBD to Metaphase","",axesC[1,0])
dur_violin(lambda r:interval_min(r,"Anaphase Onset (s)","Cytokinesis Onset (s)","AC"),"Anaphase to Cytokinesis","",axesC[1,1],drop_max_from={"unmodified","all off-target"})
figC.suptitle("Duration comparisons",x=.01,ha="left",fontweight="bold")
# D1 (2026-07-07): single shared median/mean key BELOW all four panels (bbox_inches="tight" captures it) so no
# per-panel legend can strike through the off-target N/mean/median label (First-Alignment->Meta / NEBD->Meta).
from matplotlib.lines import Line2D as _L2C
figC.legend(handles=[_L2C([0],[0],color="#444",lw=2.2,label="median"),
                     _L2C([0],[0],color="#444",lw=1.4,ls=(0,(2,1.5)),label="mean")],
            loc="lower center",ncol=2,fontsize=9,bbox_to_anchor=(0.5,-0.01),frameon=False)
plt.tight_layout(); plt.savefig(f"{OUT}/G2_duration_combined.png",bbox_inches="tight"); plt.close()
# journal-standard combined 2x2 (scale='width', width=0.8, cut=0, points-only N<6) alongside the original
figCJ,axesCJ=plt.subplots(2,2,figsize=(14,9))
dur_violin(mdur,"Metaphase to Anaphase","",axesCJ[0,0],journal=True)
dur_violin(lambda r:interval_min(r,"First Congression (s)","Metaphase Start (s)","Align"),"First Alignment to Metaphase","",axesCJ[0,1],journal=True)
dur_violin(lambda r:interval_min(r,"NEB Time (s)","Metaphase Start (s)","NEB"),"NEBD to Metaphase","",axesCJ[1,0],journal=True)
dur_violin(lambda r:interval_min(r,"Anaphase Onset (s)","Cytokinesis Onset (s)","AC"),"Anaphase to Cytokinesis","",axesCJ[1,1],drop_max_from={"unmodified","all off-target"},journal=True)
figCJ.suptitle("Duration comparisons",x=.01,ha="left",fontweight="bold")
figCJ.legend(handles=[_L2C([0],[0],color="#444",lw=2.2,label="median"),
                      _L2C([0],[0],color="#444",lw=1.4,ls=(0,(2,1.5)),label="mean")],
             loc="lower center",ncol=2,fontsize=9,bbox_to_anchor=(0.5,-0.01),frameon=False)
plt.tight_layout(); plt.savefig(f"{OUT}/G2_duration_combined_journal.png",bbox_inches="tight"); plt.close()
# Direct data CSV for the 4-panel combined figure: reconstruct EXACTLY the points plotted in each panel
# (same cohorts + same per-cohort max-outlier drop dur_violin applies for the Anaphase->Cytokinesis panel).
_DC_PANELS=[("Metaphase to Anaphase",mdur,None),
            ("First Alignment to Metaphase",lambda r:interval_min(r,"First Congression (s)","Metaphase Start (s)","Align"),None),
            ("NEBD to Metaphase",lambda r:interval_min(r,"NEB Time (s)","Metaphase Start (s)","NEB"),None),
            ("Anaphase to Cytokinesis",lambda r:interval_min(r,"Anaphase Onset (s)","Cytokinesis Onset (s)","AC"),{"unmodified","all off-target"})]
_DC_COH=[("unmodified","Unmodified",None)]+[(f"{s}-Sisterless","On-target",s) for s in "123"]+[("all off-target","Off-target",None)]
_dcrows=[]
for _pname,_mfn,_dropfrom in _DC_PANELS:
    for _lab,_tt,_s in _DC_COH:
        _d=[_mfn(r) for r in act_cohort if r.get("On-Target / Off-Target")==_tt and (_s is None or r.get("# Sisterless KTs")==_s)]
        _d=[x for x in _d if x is not None]
        if _dropfrom and _lab in _dropfrom and _d:
            _mx=max(_d); _d=[x for x in _d if x!=_mx]   # matches dur_violin's per-cohort outlier drop
        for x in _d: _dcrows.append([_pname,_lab,round(x,3)])
lib.record_plot("G2_duration_combined",["panel","cohort","duration_min"],_dcrows,
  {"type":"4-panel violin (Meta->Ana / Align->Meta / NEBD->Meta / Ana->Cyto)","cohorts":"unmodified,1/2/3-sisterless,all off-target",
   "note":"Ana->Cyto panel drops the per-cohort max outlier in unmodified + all-off-target (matches plot)"},SCRIPT,"Duration comparisons — 4-panel combined")

# ---------- 2b. DURATION STATS GRID (ITEM 1 feedback): four stat panels, one per duration comparison ----------
# "for each of these four plots, there should be a stats grid ... a figure that has four stat plots for the
# respective violin plots." Each panel = pairwise Mann-Whitney U across the same 5 cohorts as the violins.
import matplotlib.colors as _mc2
def _cohort_data(metric_fn,drop_max_from=None):
    _co=[("unmodified","Unmodified",None),("1-Sisterless","On-target","1"),("2-Sisterless","On-target","2"),
         ("3-Sisterless","On-target","3"),("all off-target","Off-target",None)]
    labs=[];vals=[]
    for lab,tt,s in _co:
        d=[metric_fn(r) for r in act_cohort if r.get("On-Target / Off-Target")==tt and (s is None or r.get("# Sisterless KTs")==s)]
        d=[x for x in d if x is not None]
        if drop_max_from and lab in drop_max_from and d:   # keep the stats grid consistent with the outlier-dropped violin
            _mx=max(d); d=[x for x in d if x!=_mx]
        labs.append(lab); vals.append(d)
    return labs,vals
_metrics=[(mdur,"Metaphase to Anaphase",None),
          (lambda r:interval_min(r,"First Congression (s)","Metaphase Start (s)","Align(grid)"),"First Alignment to Metaphase",None),
          (lambda r:interval_min(r,"NEB Time (s)","Metaphase Start (s)","NEB(grid)"),"NEBD to Metaphase",None),
          (lambda r:interval_min(r,"Anaphase Onset (s)","Cytokinesis Onset (s)","AC(grid)"),"Anaphase to Cytokinesis",{"unmodified","all off-target"})]
figS,axesS=plt.subplots(2,2,figsize=(13,11),constrained_layout=True)
_cmapS=_mc2.ListedColormap(["#08519c","#3182bd","#9ecae1","#deebf7","#f7f7f7"]); _normS=_mc2.BoundaryNorm([0,.001,.01,.05,.1,1],_cmapS.N)
_imS=None; _dgrows=[]
for _ax,(mfn,mt,dmf) in zip(axesS.ravel(),_metrics):
    _labs,_vals=_cohort_data(mfn,dmf); _n=len(_labs); _P=np.full((_n,_n),np.nan)
    for a in range(_n):
        for b in range(_n):
            if a!=b and len(_vals[a])>=3 and len(_vals[b])>=3:
                _P[a,b]=_st.mannwhitneyu(_vals[a],_vals[b],alternative="two-sided").pvalue
    _dgrows+=[[mt,_labs[a],_labs[b],len(_vals[a]),len(_vals[b]),
               (None if np.isnan(_P[a,b]) else round(float(_P[a,b]),5))]
              for a in range(_n) for b in range(_n) if a<b]
    _imS=_ax.imshow(_P,cmap=_cmapS,norm=_normS)
    for a in range(_n):
        for b in range(_n):
            if np.isnan(_P[a,b]):
                _ax.text(b,a,"–",ha="center",va="center",fontsize=7,color="#999"); continue
            _ax.text(b,a,lib.sig_cell(_P[a,b]),ha="center",va="center",fontsize=5.8,linespacing=1.25,
                     color="#111" if _P[a,b]>.05 else "white")
    _ax.set_xticks(range(_n)); _ax.set_yticks(range(_n))
    _ax.set_xticklabels([f"{l}\n(n={len(v)})" for l,v in zip(_labs,_vals)],rotation=45,ha="right",fontsize=6.6)
    _ax.set_yticklabels([f"{l} (n={len(v)})" for l,v in zip(_labs,_vals)],fontsize=6.6)
    _ax.set_title(mt,fontsize=10,fontweight="bold")
figS.suptitle("Duration comparisons — pairwise Mann–Whitney U statistical grids (– = n<3, not tested)",x=.01,ha="left",fontweight="bold")
_cbS=figS.colorbar(_imS,ax=axesS,fraction=.03,pad=.02,ticks=[.0005,.005,.03,.075,.5]); _cbS.ax.set_yticklabels(["<.001","<.01","<.05","<.1","ns"])
plt.savefig(f"{OUT}/G2_duration_statgrid.png",bbox_inches="tight"); plt.close()
lib.record_plot("G2_duration_statgrid",["metric","group_a","group_b","n_a","n_b","mannwhitney_p"],_dgrows,
    {"type":"four pairwise Mann-Whitney U grids (Meta->Ana, Align->Meta, NEBD->Meta, Ana->Cyto)"},SCRIPT,"Duration stat grids")

# ---------- 3. Metaphase dynamics (prophase + prometaphase ablations) ----------
# INCLUSION RULE: act row (not excluded / not double-chromosome / not drug), Phase of Ablations in
# {prophase, prometaphase}, with a parseable Ablation->Meta interval AND a valid Meta->Ana duration,
# and 0 <= abl->meta <= 200 min. NOTE: the master 'Ablation->Meta (min)' column is stored as an
# elapsed H:MM:SS string (lib.parse_time -> SECONDS); the old code treated that as minutes, so every
# real value (e.g. 0:16:48 -> 1008) failed the x<=200 filter and only ~10 points survived. Convert to
# minutes (sec/60) — and fall back to the comma-formatted 'Ablation->Meta (s)' column.
# abl->meta now lives in lib.abl_to_meta_min(r, fallback_metastart=...) — returns (minutes, source).
# fallback_metastart=True (2026-07-07 feedback D5/D6/D7) recovers cells whose stored 'Ablation->Meta' is
# blank by using 'Metaphase Start' under the "first ablation = t=0" temporal-calibration model.
def abl_to_meta_min(r, fallback_metastart=False):
    return lib.abl_to_meta_min(r, fallback_metastart=fallback_metastart)[0]
# ITEM 3 (feedback 2026-07-06): the points span MULTIPLE sisterless groups (1/2/3/4-sisterless on-target +
# off-target) — verified — so code each marker by its ABLATION GROUP (colour), and by phase (shape:
# o=prophase, ^=prometaphase). Also confirmed the trendline: it is the pooled ordinary-least-squares fit
# (np.polyfit == scipy.linregress, verified identical); annotate BOTH the OLS Pearson r,p and Spearman ρ so
# the (weak, non-significant) pooled correlation is transparent — a single line across heterogeneous groups
# is descriptive only.
def _grp_of(r):
    if r.get("On-Target / Off-Target")=="Off-target": return "off"
    s=r.get("# Sisterless KTs",""); return s if s in ("1","2","3","4") else "off"
_GCOL={"1":lib.PALETTE["1-Sister"],"2":lib.PALETTE["2-Sister"],"3":lib.PALETTE["3-Sister"],"4":lib.PALETTE["4-Sister"],"off":"#00a0b0"}
_GLAB={"1":"1-sisterless","2":"2-sisterless","3":"3-sisterless","4":"4-sisterless","off":"off-target"}
_PHM={"Prophase":"o","Prometaphase":"^"}
fig,ax=plt.subplots(figsize=(8.2,5.2))
xs=[];ys=[];pts=[]; _n_est=0
for r in act:
    ph=phase_of(r,v2=True)   # USER 2026-07-16: v2 binning is the standard for every phase-split plot (2026-08-03
    # audit fix — this scatter's marker shape/color IS a phase split and was still reading the antiqued
    # non-v2 classification, silently mislabeling 27 v2=prometaphase-flagged cells as prophase-shaped 'o'
    # markers here even though every other phase-split plot in this file already uses v2=True)
    if ph not in ("Prophase","Prometaphase"): continue   # include the prophase group (slide-31: ~20 more samples)
    # This POOLED plot keeps the established measured-only cohort (N~45): a blanket t=0 fallback here would
    # sweep in the whole off-target control pool. abl->meta recovery is applied on the focused 1-/3-sisterless
    # single-phase plots (D5/D6/D7) instead.
    x,src=lib.abl_to_meta_min(r,fallback_metastart=False); y=mdur(r)
    if x is None or y is None: continue
    if x<0 or x>200: lib.log_review("Abl->Meta",r["Batch Name"],x,"implausible"); continue
    if src=="metastart":
        _n_est+=1; lib.log_review("Abl->Meta(recovered)",r["Batch Name"],f"{x:.1f}min",f"stored abl->meta blank — estimated as Metaphase Start (first ablation=t=0); {ph}")
    xs.append(x); ys.append(y); pts.append((x,y,_grp_of(r),ph,src))
# estimated (metastart-recovered) points get a hollow face so measured vs estimated is transparent on-plot
for g in ("1","2","3","4","off"):
    for ph,mk in _PHM.items():
        _mp=[p for p in pts if p[2]==g and p[3]==ph and p[4]!="metastart"]   # measured (filled)
        _ep=[p for p in pts if p[2]==g and p[3]==ph and p[4]=="metastart"]   # estimated (hollow)
        if _mp: ax.scatter([p[0] for p in _mp],[p[1] for p in _mp],s=30,color=_GCOL[g],marker=mk,alpha=.85,edgecolor="white",lw=.4,zorder=3)
        if _ep: ax.scatter([p[0] for p in _ep],[p[1] for p in _ep],s=30,facecolors="none",edgecolors=_GCOL[g],marker=mk,alpha=.9,lw=1.0,zorder=3)
_corr=""
if len(xs)>=4:
    _lr=_st.linregress(xs,ys); _xr=np.linspace(min(xs),max(xs),40)
    ax.plot(_xr,_lr.slope*_xr+_lr.intercept,"--",color="#333",lw=1.4,zorder=2)
    _rho,_pp=_st.spearmanr(xs,ys)
    _corr=f"  ·  OLS r={_lr.rvalue:.2f}, p={_lr.pvalue:.2g}  ·  Spearman ρ={_rho:.2f}, p={_pp:.2g}"
from matplotlib.lines import Line2D as _L2m
# D4 (2026-07-07): N next to EACH group label, expanded per group x phase so no group's count is lumped.
_gpresent=[g for g in ("1","2","3","4","off") if any(p[2]==g for p in pts)]
def _gn(g,ph=None): return sum(1 for p in pts if p[2]==g and (ph is None or p[3]==ph))
_hleg=[_L2m([0],[0],marker="o",color="w",markerfacecolor=_GCOL[g],markeredgecolor="w",
            label=f"{_GLAB[g]} (N={_gn(g)}: proph {_gn(g,'Prophase')} / prometa {_gn(g,'Prometaphase')})",ms=8) for g in _gpresent]
_hleg+=[_L2m([0],[0],marker="o",color="#555",lw=0,label=f"prophase (N={sum(1 for p in pts if p[3]=='Prophase')})",ms=8),
        _L2m([0],[0],marker="^",color="#555",lw=0,label=f"prometaphase (N={sum(1 for p in pts if p[3]=='Prometaphase')})",ms=8)]
if _n_est: _hleg+=[_L2m([0],[0],marker="o",color="w",markerfacecolor="none",markeredgecolor="#555",label=f"estimated abl-meta (t=0=abl; N={_n_est})",ms=8)]
ax.legend(handles=_hleg,fontsize=6.6,loc="upper right",ncol=1,title="ablation group (N) / phase",title_fontsize=7)
ax.set_xlabel("Time from ablation to metaphase start (min)"); ax.set_ylabel("Metaphase duration (MM:SS)"); mmss_axis(ax)
ax.set_title(f"Metaphase dynamics — prophase + prometaphase ablations (v2 binning; N={len(xs)}){_corr}",loc="left",fontweight="bold",fontsize=9.2)
plt.tight_layout(); plt.savefig(f"{OUT}/G2_metaphase_dynamics_prometa.png",bbox_inches="tight"); plt.close()
lib.record_plot("G2_metaphase_dynamics_prometa",["abl_to_meta_min","mitotic_duration_min","group","phase","abl_meta_source"],[[round(p[0],3),round(p[1],3),_GLAB[p[2]],p[3],p[4]] for p in pts],
  {"type":"scatter","subset":"prophase+prometaphase ablations","marker_color":"sisterless group","marker_shape":"phase (v2 binning: v2=prometaphase-flagged batches counted as prometaphase)","trendline":"pooled OLS (descriptive)","recovery":"abl->meta estimated as Metaphase Start (t=0=ablation) where stored value blank; hollow markers"},SCRIPT,"Metaphase dynamics — prophase+prometaphase ablations, coded by group (v2 binning)")

# ---------- 3b. DEDICATED single (1-)sisterless PROPHASE abl->meta vs duration (slide-31 request) ----------
# The broad plot above (3) pools all prophase+prometaphase, all sisterless counts (N~45) — that satisfies s35.
# Slide-31 specifically wants ONLY the single (1-)sisterless PROPHASE cells ("those ~20 samples"). To keep N
# consistent with s29 we take the CANONICAL lib.assign_cohorts(include_prophase=True) 1-Sister set intersected with prophase, and
# plot ablation->metaphase (min) vs Meta->Ana metaphase duration (min) for cells with BOTH values.
coh_1sis={b for b,_ in lib.assign_cohorts(include_prophase=True)["1-Sister"]}
def _one_sis_phase_abl_meta(phase_name, fname, plot_id):
    """Single (1-)sisterless <phase> on-target cells: ablation->metaphase-start (x) vs Meta->Ana duration (y).
    D5 (prophase) / D6 (prometaphase), 2026-07-07: recover cells whose stored abl->meta is blank by estimating
    it as Metaphase Start under the 'first ablation = t=0' temporal-calibration model (lib.abl_to_meta_min
    fallback). Measured points are filled; estimated points are hollow, so the recovery is transparent."""
    fig,ax=plt.subplots(figsize=(7.5,5.2))
    xm=[];ym=[];xe=[];ye=[];_n_set=0;_n_est=0;_n_drop=0;rows=[]
    for r in act:
        b=r["Batch Name"]
        if b not in coh_1sis: continue                              # canonical 1-Sisterless set (== s29's count)
        if phase_of(r,v2=True)!=phase_name: continue                # USER 2026-07-16: v2 binning (v2=prometaphase-flagged prophase cells -> prometaphase), like the phase-split & KK-by-phase
        if r.get("On-Target / Off-Target")!="On-target": continue   # on-target (1-sisterless is on-target by construction)
        _n_set+=1
        x,src=lib.abl_to_meta_min(r,fallback_metastart=True); y=mdur(r)
        if y is None: _n_drop+=1; lib.log_review(f"abl_to_meta_1sis_{phase_name.lower()}",b,"no-duration","no Meta->Ana duration — cannot place on plot"); continue
        if x is None: _n_drop+=1; lib.log_review(f"abl_to_meta_1sis_{phase_name.lower()}",b,"no-abl-interval","blank stored abl->meta AND no Metaphase Start — cannot recover"); continue
        if x<0 or x>200: _n_drop+=1; lib.log_review(f"Abl->Meta(1sis-{phase_name.lower()})",b,x,"implausible"); continue
        if src=="metastart":
            _n_est+=1; xe.append(x); ye.append(y); lib.log_review(f"abl_to_meta_1sis_{phase_name.lower()}(recovered)",b,f"{x:.1f}min","stored abl->meta blank — estimated as Metaphase Start (first ablation=t=0)")
        else: xm.append(x); ym.append(y)
        rows.append([b,round(x,3),round(y,3),src])
    x1=xm+xe; y1=ym+ye
    if xm: ax.scatter(xm,ym,s=34,color=lib.PALETTE["1-Sister"],alpha=.85,edgecolor="white",lw=.4,zorder=3,label=f"measured (N={len(xm)})")
    if xe: ax.scatter(xe,ye,s=34,facecolors="none",edgecolors=lib.PALETTE["1-Sister"],lw=1.1,alpha=.9,zorder=3,label=f"estimated: t=0=ablation (N={len(xe)})")
    _corr1=""
    if len(xm)>=4:   # USER 2026-07-16: trendline/stats on FILLED (measured) points only; hollow(estimated) excluded
        _m1,_b1=np.polyfit(xm,ym,1); _xr1=np.linspace(min(xm),max(xm),40); ax.plot(_xr1,_m1*np.array(_xr1)+_b1,"--",color="#333",lw=1.4)
        _rho1,_p1=_st.spearmanr(xm,ym); _corr1=f"  ·  Spearman ρ={_rho1:.2f}, p={_p1:.2g} (measured N={len(xm)})"
    ax.set_xlabel("Time from ablation to metaphase start (min)"); ax.set_ylabel("Metaphase duration (MM:SS)"); mmss_axis(ax)
    ax.set_title(f"Single (1-)sisterless {phase_name.upper()} ablations — abl->meta vs metaphase duration (N={len(x1)} of {_n_set}){_corr1}",loc="left",fontweight="bold",fontsize=9.2)
    if xe:
        ax.text(.03,.04,f"{_n_est} of {len(x1)} points have a BLANK stored ablation->metaphase interval and are\nestimated as Metaphase Start ('first ablation = t=0'; hollow markers). Validated against the\n{len(xm)} measured cells this over-estimates by ~0-6 min (mean ~2.9). {_n_drop} cell(s) dropped (no duration).",
            transform=ax.transAxes,fontsize=7.0,va="bottom",ha="left",color="#555",
            bbox=dict(boxstyle="round",fc="#f6f6f6",ec="#999",lw=.7,alpha=.95))
    ax.legend(fontsize=8,loc="upper right")
    plt.tight_layout(); plt.savefig(f"{OUT}/{fname}",bbox_inches="tight"); plt.close()
    lib.record_plot(plot_id,["batch","abl_to_meta_min","metaphase_duration_min","abl_meta_source"],rows,
      {"type":"scatter","subset":f"1-sisterless {phase_name.lower()} (canonical cohort ∩ {phase_name.lower()})","x":"ablation->metaphase (min)","y":"Meta->Ana duration (min)","recovery":"blank stored abl->meta estimated as Metaphase Start (t=0=ablation); hollow markers"},
      SCRIPT,f"Single (1-)sisterless {phase_name.lower()}: ablation->metaphase vs metaphase duration")
    print(f"1-sisterless {phase_name}: canonical∩{phase_name} set={_n_set}, plotted N={len(x1)} ({_n_est} estimated via t=0=ablation, {_n_drop} dropped)")
_one_sis_phase_abl_meta("Prophase","G2_abl_to_meta_1sis_prophase.png","G2_abl_to_meta_1sis_prophase")        # D5
_one_sis_phase_abl_meta("Prometaphase","G2_abl_to_meta_1sis_prometaphase.png","G2_abl_to_meta_1sis_prometaphase")  # D6

# distinct review file so this script's entries (ITEM-1 dropped ana->cyto outliers, ITEM-4 abl->meta gaps)
# aren't overwritten by the other group2_*.py scripts that also flush to outlier_review.csv (shared, last-writer-wins).
lib.flush_review("/Volumes/4 MB/ablation_figures_20260625/_review/outlier_review_g2build.csv")
print("Group 2 (phase-split, duration violins, metaphase dynamics) done.")
print("phase-split N:",[(g[0].replace(chr(10),' '),len([x for x in g[1] if x])) for g in groups])
print("prometaphase-dynamics N:",len(xs))
