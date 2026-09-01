"""Violin 2 (3 variants): metaphase duration by cohort. Mean/median shown as MM:SS.
N for 1/2/3/4-sisterless is the CANONICAL lib.assign_cohorts() set (Exclude/drug/mad1/double-chromosome
filtered + IQR-screened) — IDENTICAL to the phase-split (group2_build) and exhaustion (group4) violins."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from scipy import stats as _st
import matplotlib.colors as _mcol
import lib
lib.apply_style()
# cohort membership = lib.assign_cohorts() (Exclude/drug/mad1/double-chromosome filtered + IQR screened).
# Explicit hec1 guard per 2026-07-06 feedback ("not drug treated, mad1, or hec1"): drop any hec1 batch.
# (Currently a no-op — every hec1 batch also carries 'mad1' and is already excluded — but future-proofs it.)
# include_double=True (user 2026-08-10): the 'with matched controls' violin should show the
# double-chromosome cohort. Only the orders below that NAME it will draw it; every other variant in
# this file is unchanged because make() selects by `order`.
coh={k:[(b,v) for b,v in lst if "hec1" not in b.lower()]
     for k,lst in lib.assign_cohorts(include_four=True, include_double=True).items()}
data,_=lib.load_master_plots(); dbl=lib.double_chromosome_batches()
OUT="/Volumes/4 MB/ablation_figures_20260625/group1"; SCRIPT=__file__

NC_GRAY="#9a9a9a"   # clear gray for not-captured / right-censored markers (was rendering brown/low-contrast)

def _cohort_of(r):
    """Classify a master row into a main-violin cohort (same rule as lib.assign_cohorts), or None."""
    b=r["Batch Name"]; tt=r.get("On-Target / Off-Target",""); sis=r.get("# Sisterless KTs","")
    if lib.is_drug(b) or lib.is_mad1(b): return None
    if r.get("Exclude") in ("Yes","yes"): return None
    if b in dbl: return None
    if tt=="Unmodified": return "unModified"
    if tt=="On-target" and sis in ("1","2","3","4"): return f"{sis}-Sister"
    if tt=="Off-target": return "Off-Target/Control"
    return None

def uncaptured_by_cohort():
    """Per cohort: counts of cells that entered metaphase but whose anaphase was NOT captured.
    'censored' = anaphase recorded as 'greater than X' (right-censored lower bound);
    'notcaptured' = metaphase start present but no usable anaphase time."""
    out={}
    for r in data:
        k=_cohort_of(r)
        if k is None: continue
        if lib.parse_time(r.get("Metaphase Start (s)","")) is None: continue
        _,ok=lib.mitotic_duration_min(r)
        if ok: continue
        a=(r.get("Anaphase Onset (s)","") or "").strip().lower()
        out.setdefault(k,{"censored":0,"notcaptured":0})
        if "greater than" in a or a.startswith(">"): out[k]["censored"]+=1
        else: out[k]["notcaptured"]+=1
    return out
UNCAP=uncaptured_by_cohort()

def make(order,outname,title,width=11,show_uncaptured=False,statgrid=None,journal=False,min_n=6):
    # journal=True -> emit the "_journal" variant (uniform-width scale='width', width=0.8, cut=0,
    # points-only for N<6) ALONGSIDE the original; the original call (journal=False) is untouched.
    # USER 2026-08-03: "Need to re-include Stats grid for G1_violin2_mitotic_duration_journal; it disappeared
    # at some point." It never disappeared - the journal branch NULLED statgrid unconditionally, so no journal
    # variant could ever emit one. The caller now supplies the exact grid filename and it is honoured.
    if journal: outname=outname[:-4]+"_journal.png"
    # USER 2026-08-10: honour the per-plot manual exclusions (annotations/MANUAL_PLOT_EXCLUSIONS.csv).
    # These are per-PLOT decisions, not blanket removals — the batch stays in every other figure.
    # `outname` already carries the _journal suffix when journal=True, so each variant is keyed
    # separately and both are listed in the CSV. data_v feeds the violins AND the stats grid, so
    # filtering here keeps the drawn points, the Ns and the p-values consistent.
    _excl=lib.manual_plot_exclusions(outname[:-4])
    if _excl:
        _drop=[(k,b) for k in order for b,_ in coh[k] if b in _excl]
        print(f'  {outname}: manual exclusions -> {_drop}')
    data_v=[[v for b,v in coh[k] if b not in _excl] for k in order]
    fig,ax=plt.subplots(figsize=(width,5.4))
    dmax=max((max(d) for d in data_v if d),default=10)
    band=dmax*1.06 if show_uncaptured else dmax       # uncaptured markers live in a band above the data
    for i,(k,d) in enumerate(zip(order,data_v)):
        if not d: continue
        col=lib.PALETTE[k]
        if journal:
            # min_n is per-plot (user 2026-08-10): the matched-controls violin passes 5 so the
            # double-chromosome group (N=5 after its outlier was removed) draws a body instead of
            # bare points. Applies to every cohort in that figure, not just the small one.
            lib.journal_violin(ax,d,i,col,alpha=0.30,lw=1.0,min_n=min_n)
        elif len(d)>=2:
            vp=ax.violinplot([d],positions=[i],widths=0.8,showextrema=False)
            for b in vp['bodies']:
                b.set_facecolor(col); b.set_alpha(0.30); b.set_edgecolor(col); b.set_linewidth(1.0)
        jit=(np.random.RandomState(i).rand(len(d))-0.5)*0.22
        ax.scatter(np.full(len(d),i)+jit,d,s=14,color=col,alpha=0.8,edgecolor="white",linewidth=0.3,zorder=3)
        mean=float(np.mean(d)); med=float(np.median(d))
        ax.hlines(med,i-0.34,i+0.34,color=col,lw=2.2,zorder=4)                       # median (solid bar)
        ax.hlines(mean,i-0.28,i+0.28,color=col,lw=1.4,ls=(0,(2,1.5)),zorder=4)        # mean (dashed bar)
        ax.scatter([i],[mean],marker="D",s=34,facecolor="white",edgecolor=col,lw=1.4,zorder=5)  # MEAN marker
        ax.text(i,max(d)+1.5,f"x̄ {lib.mmss(mean)}\nmed {lib.mmss(med)}\nN={len(d)}",
                ha="center",va="bottom",fontsize=7.5,color="#222")
        # not-captured / right-censored markers in a clear-gray band above the data
        if show_uncaptured and k in UNCAP:
            uc=UNCAP[k]; step=max(dmax*0.035,0.8)
            if uc["censored"]:
                ax.scatter(np.full(uc["censored"],i)+(np.random.RandomState(99+i).rand(uc["censored"])-.5)*0.22,
                           np.full(uc["censored"],band),marker=">",s=26,facecolor="none",edgecolor=NC_GRAY,lw=1.1,zorder=3)
            if uc["notcaptured"]:
                ax.scatter(np.full(uc["notcaptured"],i)+(np.random.RandomState(7+i).rand(uc["notcaptured"])-.5)*0.22,
                           np.full(uc["notcaptured"],band+step),marker="o",s=22,facecolor="none",edgecolor=NC_GRAY,lw=1.1,zorder=3)
    ax.set_xticks(range(len(order))); ax.set_xticklabels([lib.lbl(k) for k in order],rotation=30,ha="right",fontsize=8.5)
    ax.set_ylabel("Metaphase duration (MM:SS)")
    ax.set_title(title,loc="left",fontweight="bold")
    ymax=(band+max(dmax*0.07,1.6)*2 if show_uncaptured else dmax)+12; ax.set_ylim(0,ymax)
    from matplotlib.ticker import FuncFormatter
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v,_: lib.mmss(v) if v>=0 else ""))
    _leg=[Line2D([0],[0],color="#444",lw=2.2,label="median"),
          Line2D([0],[0],marker="D",color="#444",lw=1.4,ls=(0,(2,1.5)),markerfacecolor="white",markeredgecolor="#444",label="mean")]
    if show_uncaptured:
        _leg+=[Line2D([0],[0],marker=">",color="none",markerfacecolor="none",markeredgecolor=NC_GRAY,markersize=8,label="right-censored (anaphase not reached)"),
               Line2D([0],[0],marker="o",color="none",markerfacecolor="none",markeredgecolor=NC_GRAY,markersize=8,label="not captured (no anaphase time)")]
    ax.legend(handles=_leg,loc="upper right",fontsize=8)
    plt.tight_layout(); plt.savefig(f"{OUT}/{outname}",bbox_inches="tight"); plt.close()
    # 2026-08-18: the recorded CSV used to be built from `coh` (EVERYTHING) while the figure drew
    # `data_v` (after the manual exclusions), so the plot spreadsheet listed cells the figure does not
    # show -- `20251029 single_ablation_8` and `20260303 ...ablation_1metaphase_52` both sat in the CSV
    # after she had asked for them to be removed.  The CSV is the source-data record for this figure
    # (and the committee package reads it), so it must contain exactly the plotted cells.  The dropped
    # cells stay documented in the settings and in MANUAL_PLOT_EXCLUSIONS.csv.
    rec=[[b,k,round(v,3)] for k in order for b,v in coh[k] if b not in _excl]
    lib.record_plot(outname[:-4],["batch","cohort","metaphase_duration_min"],rec,
      {"type":"violin+points","annot":"mean(diamond)/median MM:SS + N","palette":"per-cohort",
       "outlier":"IQR 3x; non-positive/>300min excluded","y_format":"MM:SS",
       "manual_exclusions":sorted(_excl),
       "uncaptured":"clear-gray ▶ censored / ○ not-captured" if show_uncaptured else "n/a"},SCRIPT,title)
    print(outname,"->",{lib.lbl(k).replace(chr(10),' '):len(d) for k,d in zip(order,data_v)})
    # ---------- statgrid (pairwise Mann-Whitney) ----------
    if statgrid:
        labs=[lib.lbl(k).replace(chr(10),' ') for k in order]; gv=data_v; n=len(order)
        P=np.full((n,n),np.nan)
        for a in range(n):
            for b in range(n):
                if a!=b and len(gv[a])>=3 and len(gv[b])>=3:
                    P[a,b]=_st.mannwhitneyu(gv[a],gv[b],alternative="two-sided").pvalue
        fg,axg=plt.subplots(figsize=(7.2,6.2))
        cmap=_mcol.ListedColormap(["#08519c","#3182bd","#9ecae1","#deebf7","#f7f7f7"]); norm=_mcol.BoundaryNorm([0,.001,.01,.05,.1,1],cmap.N)
        im=axg.imshow(P,cmap=cmap,norm=norm)
        for a in range(n):
            for b in range(n):
                if np.isnan(P[a,b]): continue
                axg.text(b,a,lib.sig_cell(P[a,b]),ha="center",va="center",fontsize=5.8,linespacing=1.25,
                         color="#111" if P[a,b]>.05 else "white")
        axg.set_xticks(range(n)); axg.set_yticks(range(n)); axg.set_xticklabels(labs,rotation=45,ha="right",fontsize=7); axg.set_yticklabels(labs,fontsize=7)
        # D3 (2026-07-07): the 4-sisterless MAIN-cohort grid is RETIRED (that cohort has only 1-2 batches, so
        # cross-cohort MW is not meaningful) and is kept only as a stamped placeholder. The stamp is specific to
        # THAT grid - it must not be painted over any other grid this function draws.
        _retired = (statgrid == "G1_violin2_statgrid.png")
        if _retired:
            axg.set_title("Violin 2 statistical grid — Mann–Whitney U (metaphase duration)  [RETIRED]",loc="left",fontweight="bold",fontsize=9.5,color="#b00")
            axg.text(0.5,0.5,"RETIRED",transform=axg.transAxes,ha="center",va="center",fontsize=54,color="#b00",alpha=0.32,rotation=30,fontweight="bold",zorder=10)
            axg.text(0.5,-0.22,"Retired: 4-sisterless cohort has only 1-2 batches — pairwise Mann-Whitney across the main cohorts is not meaningful.",
                     transform=axg.transAxes,ha="center",va="top",fontsize=7,color="#b00")
        else:
            axg.set_title(f"{title} — statistical grid, Mann–Whitney U (metaphase duration)",
                          loc="left",fontweight="bold",fontsize=9.5)
        cb=fg.colorbar(im,ax=axg,fraction=.046,pad=.04,ticks=[.0005,.005,.03,.075,.5]); cb.ax.set_yticklabels(["<.001","<.01","<.05","<.1","ns"])
        plt.subplots_adjust(bottom=0.24)
        plt.tight_layout(); plt.savefig(f"{OUT}/{statgrid}",bbox_inches="tight"); plt.close()
        _rg=[[labs[a],labs[b],("" if np.isnan(P[a,b]) else round(float(P[a,b]),6))] for a in range(n) for b in range(n) if a!=b]
        lib.record_plot(statgrid[:-4],["group_a","group_b","p_value"],_rg,
          {"type":"significance matrix","test":"Mann-Whitney U two-sided","metric":"metaphase duration"}
          | ({"status":"RETIRED (D3 2026-07-07): 4-sisterless has 1-2 batches; not meaningful"} if _retired else {}),
          SCRIPT,
          ("[RETIRED] Pairwise Mann-Whitney U across the main violin cohorts — 4-sisterless too small"
           if _retired else f"Pairwise Mann-Whitney U — {title}"))

# (a) MAIN violin: unmodified, ALL-OFF-TARGET, 1,2,3,4-sisterless (off-target right of unmodified)
# ITEM 1 (2026-07-06 feedback): the stray open-circle / open-triangle markers floating far above the
# groups were the "not-captured / right-censored" band (show_uncaptured). User asked to remove them (and
# they left a blank-looking legend entry) -> show_uncaptured=False so no markers and no extra legend rows.
make(["unModified","Off-Target/Control","1-Sister","2-Sister","3-Sister","4-Sister"],
     "G1_violin2_sisterless_1234.png","Violin 2 — metaphase duration by cohort",9,
     show_uncaptured=False,statgrid="G1_violin2_statgrid.png")
# (b) full with matched controls, INCLUDING double-chromosome (user 2026-08-10). The old note here said
#     "double-chromosome globally empty per feedback -> dropped so no blank slot" — that was true only
#     because assign_cohorts() empties the cohort by default; the underlying data is not empty.
# ITEM 4: this "full" violin includes ALL samples relevant to each group (Exclude/drug/mad1/hec1 removed);
# its per-cohort N == the N used by Violin 1 (both iterate the identical lib.assign_cohorts() membership).
make(["unModified","1-Sister","1-Sister Controls","2-Sister","2-Sister Controls",
      "3-Sister","3-Sister Controls","Double Chromosome","Off-Target/Control"],
     "G1_violin2_mitotic_duration.png","Violin 2 — metaphase duration by cohort (with matched controls)",12.6,min_n=5)
# (c) sisterless groups + matched off-target only
make(["unModified","1-Sister","1-Sister Controls","2-Sister","2-Sister Controls","3-Sister","3-Sister Controls"],
     "G1_violin2_no_dc_offtarget.png","Violin 2 — sisterless groups + matched off-target only",10)
# ---- journal-standard variants (scale='width', width=0.8, cut=0, points-only for N<6) ALONGSIDE originals ----
make(["unModified","Off-Target/Control","1-Sister","2-Sister","3-Sister","4-Sister"],
     "G1_violin2_sisterless_1234.png","Violin 2 — metaphase duration by cohort",9,
     show_uncaptured=False,journal=True)
make(["unModified","1-Sister","1-Sister Controls","2-Sister","2-Sister Controls",
      "3-Sister","3-Sister Controls","Double Chromosome","Off-Target/Control"],
     "G1_violin2_mitotic_duration.png","Violin 2 — metaphase duration by cohort (with matched controls)",12.6,journal=True,min_n=5,
     statgrid="G1_violin2_mitotic_duration_journal_statgrid.png")   # USER 2026-08-03: re-include this grid
make(["unModified","1-Sister","1-Sister Controls","2-Sister","2-Sister Controls","3-Sister","3-Sister Controls"],
     "G1_violin2_no_dc_offtarget.png","Violin 2 — sisterless groups + matched off-target only",10,journal=True)
lib.flush_review("/Volumes/4 MB/ablation_figures_20260625/_review/outlier_review.csv")
