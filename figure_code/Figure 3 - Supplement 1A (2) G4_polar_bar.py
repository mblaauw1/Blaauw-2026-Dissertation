"""polar / lagging bar plots (normalized to N) + presence vs metaphase duration."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import lib
lib.apply_style()
OUT="/Volumes/4 MB/ablation_figures_20260625/group4"; SCRIPT=__file__
data,_=lib.load_master(); dbl=lib.double_chromosome_batches()
act=[r for r in data if r.get("Exclude") not in ("Yes","yes") and not lib.is_drug(r["Batch Name"]) and not lib.is_mad1(r["Batch Name"]) and not lib.excluded(r["Batch Name"])]
# 🔴 HER 2026-08-25: *"the n for triple kinetochore group on that plot should be 28*3, or 84"*. The comparison
# is between numbers of SISTERLESS KINETOCHORES, so the group's kinetochore count belongs on the bar. But the
# bar itself cannot become per-kinetochore: `Lagging Chromosomes` is a per-CELL Yes/No (the per-KT count
# `# Lagging Chromosomes` is filled for only 45 rows), and making the statistical unit the kinetochore would
# be the pseudoreplication she ruled out. So both units are printed and labelled: the fraction and every test
# stay per CELL, and the sisterless-kinetochore count is shown beside it.
KT_PER_CELL = {"1-Sister": 1, "2-Sister": 2, "3-Sister": 3}


def _n_label(k, n):
    kt = KT_PER_CELL.get(k)
    return f"N={n} cells\n({n * kt} sisterless KTs)" if kt else f"N={n} cells"


def yn(v):
    v=v.strip().lower(); return "Yes" if v=="yes" else "No" if v=="no" else None


def lagging_yn(r):
    """Yes/No for lagging, falling back to her COUNT column when the Yes/No cell is blank.

    🔴 2026-08-25 (her: *"the n for triple kinetochore group on that plot should be 28*3, or 84"*, then
    *"search more for lagging determination for 20251028 triple_ablation_9"*). That cell was the one
    3-sisterless cell missing from the bar, holding N at 27 cells / 81 KTs instead of her 28 / 84.
    Its `Lagging Chromosomes` is blank -- its Notes say *"lagging chromosomes left empty as imaging did not
    go past anaphase onset"* (2026-06-27) -- but the later `8817 lagging-count pass` of 2026-07-30 filled
    **`# Lagging Chromosomes` = 0**.

    The count column is not a guess: across the 45 rows that carry it, it agrees with the Yes/No column
    EVERY time -- 0 <-> No in 16 rows, >=1 <-> Yes in 28 -- and this cell is the single row with a count and
    no Yes/No. So the count is read as the determination where the Yes/No is blank, which is the later pass
    superseding the older note.
    """
    v = yn(r.get("Lagging Chromosomes", ""))
    if v is not None:
        return v
    n = (r.get("# Lagging Chromosomes", "") or "").strip()
    if n.isdigit():
        return "Yes" if int(n) > 0 else "No"
    return None
# 🔴 2026-08-25 (her: *"G4_lagging_bar 1-sis has an N of 51, which does not make sense"*). It did not.
# This builder rolled its OWN cohort assignment from the master columns and therefore applied none of the
# standing phase exclusions, so METAPHASE- and PROPHASE-ablation cells were counted in the ablation bars:
#   1-Sister  N=51 = 36 real + 9 metaphase + 6 prophase
#   3-Sister  N=30 = 27 real + 3 prophase
#   Off-Target N=64 = 48 real + 14 prophase + 2 metaphase
#   unModified N=75 -- correct, an unmodified cell has no ablation phase to exclude on
# `lib.assign_cohorts()` is the one place those rules live (metaphase and prophase out by default, 4-sis
# out, v2 honoured, no mitotic duration out). Take membership from it instead of re-deriving it here.
_COH_OF = {}
for _k, _lst in lib.assign_cohorts().items():
    for _e in _lst:
        _COH_OF[_e[0] if isinstance(_e, (list, tuple)) else _e] = _k

def cohort(r):
    return _COH_OF.get(r["Batch Name"])
# 🔴 HER 2026-08-20, board-5 item 7: *"plot the bars in the order of unmovified, off-target, 1 sisterless,
# and 3 sisterless from left to right"* -- and she added that it applies to "other applicable plots, mainly
# where off-target is combined into one group". The order is therefore taken from the canonical table in
# canon_labels (least- to most-manipulated: the two controls, then the ablation cohorts) rather than being
# retyped here, so a figure cannot have canonical NAMES and a non-canonical ORDER.
import canon_labels as _CL
ORDER=_CL.sort_groups(["unModified","1-Sister","2-Sister","3-Sister","Off-Target/Control"])

def bar(col_name,fname,title,valmap=None,ylab=None,note=None):
    """valmap: optional {batch -> 'Yes'/'No'/None} used INSTEAD of a master Yes/No column, so a class
    scored per-chromosome (e.g. congression, from CHROMOSOME_MASTER) can use this identical figure style."""
    from scipy import stats as _st
    def _stars(p): return "***" if p<.001 else "**" if p<.01 else "*" if p<.05 else "ns"
    frac={};Ns={};cnt={}   # cnt[k]=(n_yes,n_no)
    for k in ORDER:
        if valmap is not None:
            vals=[valmap.get(r["Batch Name"]) for r in act if cohort(r)==k]
        else:
            vals=[(lagging_yn(r) if col_name=="Lagging Chromosomes" else yn(r.get(col_name,"")))
                  for r in act if cohort(r)==k]
        vals=[v for v in vals if v]
        if vals:
            ny=sum(v=="Yes" for v in vals); frac[k]=ny/len(vals); Ns[k]=len(vals); cnt[k]=(ny,len(vals)-ny)
    present=[k for k in ORDER if k in cnt]
    # ---- BETWEEN-group proportion test: overall chi-square across cohorts' Yes/No counts ----
    overall_txt=""
    if len(present)>=2:
        table=np.array([[cnt[k][0],cnt[k][1]] for k in present],float)
        try:
            chi2,p_all,dof,exp=_st.chi2_contingency(table)
            low=bool((exp<5).any())
            overall_txt=f"Between-cohort χ²={chi2:.2f}, df={dof}, p={p_all:.3g}"+("  (some expected<5 -> see Fisher pairwise)" if low else "")
            print(f"{title} bar — overall chi-square p={p_all:.4g} (chi2={chi2:.2f}, df={dof}, low_expected={low})")
        except Exception as _e:
            print(f"{title} bar — overall chi-square failed: {_e}")
    # ---- pairwise vs unmodified: Fisher's exact (robust for small N) ----
    pw={}
    if "unModified" in cnt:
        uy,un=cnt["unModified"]
        for k in present:
            if k=="unModified": continue
            ky,kn=cnt[k]
            try:
                _,pk=_st.fisher_exact([[uy,un],[ky,kn]]); pw[k]=pk
                print(f"    {title} {lib.lbl(k).replace(chr(10),' ')} vs unmodified: Fisher p={pk:.4g} {_stars(pk)}")
            except Exception: pass
    fig,ax=plt.subplots(figsize=(8,5.2)); rows=[]
    for i,k in enumerate(ORDER):
        if k not in frac: continue
        ax.bar(i,frac[k],color=lib.PALETTE[k],alpha=.85,width=.7)
        lab=f"{frac[k]*100:.0f}%\n"+_n_label(k,Ns[k])
        if k in pw: lab+=f"\nvs unmod {_stars(pw[k])}\np={pw[k]:.2g}"
        ax.text(i,frac[k]+.02,lab,ha="center",va="bottom",fontsize=7.5)
        rows.append([k,round(frac[k],3),Ns[k],cnt[k][0],cnt[k][1],("" if k not in pw else round(pw[k],5))])
    if overall_txt: ax.text(.01,.99,overall_txt,transform=ax.transAxes,ha="left",va="top",fontsize=8,color="#222")
    ax.set_xticks(range(len(ORDER))); ax.set_xticklabels([lib.lbl(k) for k in ORDER],rotation=25,ha="right",fontsize=8.5)
    # 2026-08-25: the fallback used to print the raw column test, "Fraction with Lagging = Yes", on the
    # face of a publication figure. N here counts CELLS, so say so in prose (canon_labels rule: one
    # canonical axis label; a column name is not one).
    ax.set_ylabel(ylab or f"Fraction of cells with a {title.lower()} kinetochore"); ax.set_ylim(0,1.32)
    ax.set_title(f"{title} chromosomes by cohort (normalized to N)",loc="left",fontweight="bold",fontsize=11)
    if note: ax.text(.01,.93,note,transform=ax.transAxes,ha="left",va="top",fontsize=7.5,color="#666")
    plt.tight_layout(); plt.savefig(f"{OUT}/{fname}",bbox_inches="tight"); plt.close()
    lib.record_plot(fname[:-4],["cohort","fraction_yes","N","n_yes","n_no","fisher_p_vs_unmod"],rows,
      {"type":"bar (fraction Yes)","normalize":"within cohort",
       "between_group_test":"chi-square across cohorts (overall) + Fisher exact pairwise vs unmodified",
       "overall":overall_txt},SCRIPT,f"{title} chromosomes — fraction Yes by cohort (with between-group proportion test)")
bar("Polar Chromosomes","G4_polar_bar.png","Polar")
# 🔴 2026-08-18 COLLISION FIX (NOTES §8: two scripts writing one plot_id, the last one silently wins).
# This generic bar() used to write plot_id "G4_lagging_bar" with the FULL cohort list, which clobbered
# `figures/G4_lagging_bar.py` — the dedicated 1:1 owner that drops 2-Sister (her 2026-08-16 item [10])
# and carries the polar-at-anaphase annotation (item [20]). Both had been done on 08-16, and an 08-17
# re-run of THIS script silently reverted them on the deck. Per §8 the fix is to remove the superseded
# WRITE, never to depend on run order. This now writes an ALL-COHORT companion under its own id, which
# is what `figures/G4_lagging_bar.py` reads as its input; that script alone owns "G4_lagging_bar".
bar("Lagging Chromosomes","G4_lagging_bar_allcohorts.png","Lagging")

# ── CONGRESSED, same style (USER 2026-08-05: "make another plot in this same exact style thats for
# congressed kinetochores by cohort") ────────────────────────────────────────────────────────────
# There is no Yes/No master column for congression — it is scored PER CHROMOSOME in CHROMOSOME_MASTER
# (congressed / noncongression / at_plate). A cell is Yes when at least one of its scored chromosomes
# congressed, No when it has scored chromosomes and none did, and is left out when nothing was scored —
# the same rule `yn()` applies to a blank master cell.
# COHORT COVERAGE (measured 2026-08-05): only the on-target cohorts carry chromosome scores
# (1-Sister 34, 2-Sister 10, 3-Sister 31 cells); unModified has 0 and Off-Target/Control has 1, because a
# cell with no sisterless chromosome has nothing that can congress. So this figure has three bars where
# polar/lagging have five, and the "vs unmodified" Fisher column is absent by construction, not omitted.
import csv as _csvC
from collections import defaultdict as _ddC
_behC=_ddC(list)
for _r in _csvC.DictReader(open("/Volumes/4 MB/annotations/CHROMOSOME_MASTER.csv",encoding="utf-8",errors="replace")):
    _v=(_r.get("behavior") or "").strip().lower()
    if _v: _behC[_r["batch"].strip()].append(_v)
CONGRESSED={b:("Yes" if "congressed" in v else "No") for b,v in _behC.items() if v}
bar(None,"G4_congressed_bar.png","Congressed",valmap=CONGRESSED,
    ylab="Fraction of cells with a congressed chromosome",
    note="scored per chromosome in CHROMOSOME_MASTER; a cell is Yes if any of its chromosomes congressed. "
         "unModified / off-target carry no chromosome scores (no sisterless chromosome to congress).")

# ITEM 3 (2026-08-03, her M2-17 "[A] combine with [B]"): G4_polar_bar and G4_lagging_bar are the same 5
# cohorts, same near-identical Ns, same Fisher-exact-vs-unmodified design -- only the KT class differs
# (caption similarity 0.94 per REVIEW_MESSAGE2_IDENTIFICATION.md). Combined into ONE grouped-bar figure below
# (`combined_class_bar`) so both classes read off the same cohort axis instead of two separate artboards.
# G4_neither_bar is INCLUDED as a third bar per cohort, not left out: Polar=Yes and Lagging=Yes are not
# mutually exclusive (a cell can have both), so "fraction polar" + "fraction lagging" does not add up to
# "fraction with any abnormality" -- Neither (Polar=No AND Lagging=No) is the only bar that closes that gap,
# and since it was already built on the same board as the logical complement, folding it into the same
# grouped-bar figure lets a reader see polar / lagging / neither for a cohort in one glance instead of
# flipping between three images. The three original single-class bars (below and in bar_neither()) are still
# built and recorded (their CSVs + per-class Fisher stats stay available for provenance), only the DECK now
# points at the combined figure -- see deck.py.

def bar_neither(fname="G4_neither_bar.png"):
    """Third companion to the polar/lagging bars: fraction of each cohort with NEITHER a polar NOR a
    lagging chromosome (Polar=No AND Lagging=No). Denominator = batches where BOTH statuses are known."""
    from scipy import stats as _st
    def _stars(p): return "***" if p<.001 else "**" if p<.01 else "*" if p<.05 else "ns"
    frac={};Ns={};cnt={}
    for k in ORDER:
        pairs=[(yn(r.get("Polar Chromosomes","")),yn(r.get("Lagging Chromosomes",""))) for r in act if cohort(r)==k]
        pairs=[(p,l) for (p,l) in pairs if p and l]
        if pairs:
            nn=sum(p=="No" and l=="No" for p,l in pairs)
            frac[k]=nn/len(pairs); Ns[k]=len(pairs); cnt[k]=(nn,len(pairs)-nn)
    present=[k for k in ORDER if k in cnt]; overall_txt=""
    if len(present)>=2:
        table=np.array([[cnt[k][0],cnt[k][1]] for k in present],float)
        try:
            chi2,p_all,dof,exp=_st.chi2_contingency(table); low=bool((exp<5).any())
            overall_txt=f"Between-cohort χ²={chi2:.2f}, df={dof}, p={p_all:.3g}"+("  (some expected<5 -> see Fisher pairwise)" if low else "")
            print(f"Neither bar — overall chi-square p={p_all:.4g}")
        except Exception as _e: print(f"Neither bar — chi-square failed: {_e}")
    pw={}
    if "unModified" in cnt:
        uy,un=cnt["unModified"]
        for k in present:
            if k=="unModified": continue
            ky,kn=cnt[k]
            try: _,pk=_st.fisher_exact([[uy,un],[ky,kn]]); pw[k]=pk
            except Exception: pass
    fig,ax=plt.subplots(figsize=(8,5.2)); rows=[]
    for i,k in enumerate(ORDER):
        if k not in frac: continue
        ax.bar(i,frac[k],color=lib.PALETTE[k],alpha=.85,width=.7)
        lab=f"{frac[k]*100:.0f}%\nN={Ns[k]}"
        if k in pw: lab+=f"\nvs unmod {_stars(pw[k])}\np={pw[k]:.2g}"
        ax.text(i,frac[k]+.02,lab,ha="center",va="bottom",fontsize=7.5)
        rows.append([k,round(frac[k],3),Ns[k],cnt[k][0],cnt[k][1],("" if k not in pw else round(pw[k],5))])
    if overall_txt: ax.text(.01,.99,overall_txt,transform=ax.transAxes,ha="left",va="top",fontsize=8,color="#222")
    ax.set_xticks(range(len(ORDER))); ax.set_xticklabels([lib.lbl(k) for k in ORDER],rotation=25,ha="right",fontsize=8.5)
    ax.set_ylabel("Fraction with NEITHER polar nor lagging"); ax.set_ylim(0,1.32)
    ax.set_title("Neither polar nor lagging chromosomes by cohort (normalized to N)",loc="left",fontweight="bold",fontsize=11)
    plt.tight_layout(); plt.savefig(f"{OUT}/{fname}",bbox_inches="tight"); plt.close()
    lib.record_plot(fname[:-4],["cohort","fraction_neither","N","n_neither","n_other","fisher_p_vs_unmod"],rows,
      {"type":"bar (fraction neither)","definition":"Polar=No AND Lagging=No","normalize":"within cohort (both statuses known)",
       "between_group_test":"chi-square across cohorts (overall) + Fisher exact pairwise vs unmodified","overall":overall_txt},
      SCRIPT,"Neither polar nor lagging chromosomes — fraction by cohort")
bar_neither()

# ---------- Combined figure (ITEM 3): Polar + Lagging + Neither, grouped bars per cohort ----------
def combined_class_bar(fname="G4_polar_lagging_neither_bar.png"):
    from scipy import stats as _st
    def _stars(p): return "***" if p<.001 else "**" if p<.01 else "*" if p<.05 else "ns"
    CLASSES=[("Polar","Polar Chromosomes","#e6820e"),("Lagging","Lagging Chromosomes","#d1495b"),("Neither",None,"#888888")]
    stats={}   # stats[class_label][cohort] = (frac,N,n_yes,n_no,p_vs_unmod or None)
    for clabel,col_name,_c in CLASSES:
        frac={};Ns={};cnt={}
        for k in ORDER:
            if clabel=="Neither":
                pairs=[(yn(r.get("Polar Chromosomes","")),yn(r.get("Lagging Chromosomes",""))) for r in act if cohort(r)==k]
                pairs=[(p,l) for (p,l) in pairs if p and l]
                if pairs:
                    nn=sum(p=="No" and l=="No" for p,l in pairs)
                    frac[k]=nn/len(pairs); Ns[k]=len(pairs); cnt[k]=(nn,len(pairs)-nn)
            else:
                vals=[yn(r.get(col_name,"")) for r in act if cohort(r)==k]
                vals=[v for v in vals if v]
                if vals:
                    ny=sum(v=="Yes" for v in vals); frac[k]=ny/len(vals); Ns[k]=len(vals); cnt[k]=(ny,len(vals)-ny)
        present=[k for k in ORDER if k in cnt]
        overall_txt=""
        if len(present)>=2:
            table=np.array([[cnt[k][0],cnt[k][1]] for k in present],float)
            try:
                chi2,p_all,dof,exp=_st.chi2_contingency(table); low=bool((exp<5).any())
                overall_txt=f"{clabel}: between-cohort χ²={chi2:.2f}, df={dof}, p={p_all:.3g}"+(" (low N)" if low else "")
            except Exception: pass
        pw={}
        if "unModified" in cnt:
            uy,un=cnt["unModified"]
            for k in present:
                if k=="unModified": continue
                ky,kn=cnt[k]
                try: _,pk=_st.fisher_exact([[uy,un],[ky,kn]]); pw[k]=pk
                except Exception: pass
        stats[clabel]=dict(frac=frac,Ns=Ns,cnt=cnt,pw=pw,overall=overall_txt)

    fig,ax=plt.subplots(figsize=(11,6.2)); rows=[]
    nC=len(CLASSES); gw=0.8; bw=gw/nC
    for i,k in enumerate(ORDER):
        for j,(clabel,col_name,color) in enumerate(CLASSES):
            st_k=stats[clabel]
            if k not in st_k["frac"]: continue
            x=i-gw/2+bw*(j+0.5)
            f=st_k["frac"][k]; N=st_k["Ns"][k]
            ax.bar(x,f,width=bw*0.92,color=color,alpha=.85)
            lab=f"{f*100:.0f}%\nN={N}"
            p=st_k["pw"].get(k)
            if p is not None: lab+=f"\n{_stars(p)} p={p:.2g}"   # print the p directly, not just stars
            ax.text(x,f+.02,lab,ha="center",va="bottom",fontsize=6.3)
            ny,nn=st_k["cnt"][k]
            rows.append([k,clabel,round(f,3),N,ny,nn,("" if p is None else round(p,5))])
    # cohort group separators + labels
    for i in range(1,len(ORDER)): ax.axvline(i-0.5,color="#ddd",lw=.7,zorder=0)
    ax.set_xticks(range(len(ORDER))); ax.set_xticklabels([lib.lbl(k) for k in ORDER],rotation=25,ha="right",fontsize=8.5)
    ax.set_ylabel("Fraction of cohort"); ax.set_ylim(0,1.32)
    ax.set_title("Polar / Lagging / Neither chromosomes by cohort (normalized to N; combined — was 2-3 separate bar figures)",
                 loc="left",fontweight="bold",fontsize=11)
    from matplotlib.patches import Patch as _Patch
    ax.legend(handles=[_Patch(facecolor=c,alpha=.85,label=f"{cl} (Yes)" if cl!="Neither" else "Neither (Polar=No AND Lagging=No)")
                        for cl,_,c in CLASSES], fontsize=8, loc="upper right")
    txt="\n".join(stats[cl]["overall"] for cl,_,_ in CLASSES if stats[cl]["overall"])
    if txt: ax.text(.01,.99,txt,transform=ax.transAxes,ha="left",va="top",fontsize=7.3,color="#222")
    plt.tight_layout(); plt.savefig(f"{OUT}/{fname}",bbox_inches="tight"); plt.close()
    lib.record_plot(fname[:-4],["cohort","class","fraction","N","n_yes_or_neither","n_other","fisher_p_vs_unmod"],rows,
      {"type":"grouped bar (fraction Yes per class)","classes":"Polar, Lagging, Neither (Polar=No AND Lagging=No)",
       "normalize":"within cohort per class","between_group_test":"chi-square across cohorts per class (overall) + Fisher exact pairwise vs unmodified per class",
       "combines":"G4_polar_bar + G4_lagging_bar + G4_neither_bar (her M2-17 'combine [A] with [B]')"},
      SCRIPT,"Polar / Lagging / Neither chromosomes — fraction Yes by cohort, combined into one grouped-bar figure")
combined_class_bar()

# ---------- Plot 3: presence of polar/lagging vs metaphase duration (1 & 3 sisterless) ----------
def mdur(r):
    d,ok=lib.mitotic_duration_min(r); return d if ok else None
def phase_of(r):
    p=(r.get("Phase of Ablations","") or "").strip().lower()
    ph="Prophase" if p.startswith("proph") else "Prometaphase" if p.startswith("promet") else "Metaphase" if p.startswith("metaph") else None
    return "Prometaphase" if (ph=="Prophase" and lib.is_v2_prometaphase(r.get("Batch Name",""))) else ph   # USER 2026-07-16: v2 binning
# ITEM 1: drop 2-sisterless (too few samples) and exclude metaphase-ablated cells' points.
fig,axes=plt.subplots(1,2,figsize=(9,5),sharey=True); rows3=[]
# headroom so per-violin N labels + "Yes vs No" text clear the top (no legend collision)
_alld=[mdur(r) for r in act if cohort(r) in ("1-Sister","3-Sister") and phase_of(r)!="Metaphase"]; _alld=[x for x in _alld if x is not None]
_gmax=(max(_alld) if _alld else 60)
for _ax in axes: _ax.set_ylim(0,_gmax*1.55)
for ax,(col_name,title) in zip(axes,[("Polar Chromosomes","Polar"),("Lagging Chromosomes","Lagging")]):
    pos=0; xticks=[]; xlabs=[]
    for s in "13":
        gd={}
        for j,(pres,off) in enumerate([("Yes",-.18),("No",.18)]):
            d=[mdur(r) for r in act if cohort(r)==f"{s}-Sister" and yn(r.get(col_name,""))==pres and phase_of(r)!="Metaphase"]
            d=[x for x in d if x is not None]; gd[pres]=d
            col=lib.PALETTE[f"{s}-Sister"]; al=.85 if pres=="Yes" else .35
            if d:
                lib.journal_violin(ax,d,pos+off,col,width=.34,alpha=al*.4)   # scale=width (uniform max half-width per slot), cut=0, N<6 points-only
                ax.scatter(np.full(len(d),pos+off)+(np.random.RandomState(pos+j).rand(len(d))-.5)*.1,d,s=lib.VIOLIN_DOT_S,color=col,alpha=al,edgecolor="white",lw=.3)
                ax.hlines(np.median(d),pos+off-.13,pos+off+.13,color=col,lw=2)                       # median
                ax.hlines(np.mean(d),pos+off-.10,pos+off+.10,color=col,lw=1.1,ls=(0,(2,1.5)))        # mean
                ax.text(pos+off,max(d)+_gmax*0.03,f"N={len(d)}\nx̄{lib.mmss(np.mean(d))}\nm{lib.mmss(np.median(d))}",ha="center",va="bottom",fontsize=5.2)  # LZ1: small pad off the top data point
                for x in d: rows3.append([title,f"{s}-Sisterless",pres,round(x,3)])
        # S50: WITHIN-group stat (Yes vs No present)
        if len(gd.get("Yes",[]))>=2 and len(gd.get("No",[]))>=2:
            from scipy import stats as _st
            try: _u,_pp=_st.mannwhitneyu(gd["Yes"],gd["No"],alternative="two-sided"); ax.text(pos,ax.get_ylim()[1]*.98,f"Yes vs No\np={_pp:.2g}",ha="center",va="top",fontsize=6.5,color="#333")
            except Exception: pass
        # S56: N is reported ABOVE each of the 6 violins (in the per-violin label), NOT beneath the 3 groups
        xticks.append(pos); xlabs.append(f"{s}-Sisterless"); pos+=1
    ax.set_xticks(xticks); ax.set_xticklabels(xlabs); ax.set_title(title,fontsize=10)
    ax.set_xlabel("sisterless group")
# single shared legend OUTSIDE the panels (was overlapping the per-violin N + Yes/No labels)
from matplotlib.patches import Patch as _Patch
from matplotlib.lines import Line2D as _L2pl
fig.legend(handles=[_Patch(facecolor="#666",alpha=.85,label="present (Yes) — opaque"),
                    _Patch(facecolor="#666",alpha=.30,label="absent (No) — faint"),
                    _L2pl([0],[0],color="#444",lw=2,label="median"),
                    _L2pl([0],[0],color="#444",lw=1.1,ls=(0,(2,1.5)),label="mean")],
           fontsize=7.5,loc="center left",bbox_to_anchor=(1.0,0.5),frameon=False)
axes[0].set_ylabel("Metaphase duration (MM:SS)")
axes[0].yaxis.set_major_formatter(FuncFormatter(lambda v,_: lib.mmss(v) if v>=0 else ""))
fig.suptitle("Polar/Lagging presence vs metaphase duration (1 & 3-sisterless; metaphase-ablated points excluded)",x=.01,ha="left",fontweight="bold")
plt.tight_layout(); plt.savefig(f"{OUT}/G4_polar_lagging_vs_duration.png",bbox_inches="tight"); plt.close()
lib.record_plot("G4_polar_lagging_vs_duration",["marker","group","present","mitotic_duration_min"],rows3,
  {"type":"split violin Yes/No","groups":"1 & 3-sisterless (2-sisterless dropped; metaphase-ablated points excluded)"},SCRIPT,"Polar/Lagging presence vs metaphase duration")
# ---------- Plot 4 (companion to Plot 3): presence vs metaphase duration, grouped by ABLATION PHASE ----------
# ITEM 2: remove Metaphase group; drop 2-sisterless points; code marker style by single (1-sis) vs triple (3-sis) ablation.
PH=["Prophase","Prometaphase"]; PHCOL={"Prophase":"#1b7837","Prometaphase":"#2166ac","Metaphase":"#762a83"}
sisact=[r for r in act if cohort(r) in ("1-Sister","3-Sister")]
MARK={"1-Sister":"o","3-Sister":"^"}   # single-sisterless = circle, triple-sisterless = triangle
figp,axesp=plt.subplots(1,2,figsize=(10,5),sharey=True); rows4=[]
_alld2=[mdur(r) for r in sisact if phase_of(r) in PH]; _alld2=[x for x in _alld2 if x is not None]
_gmax2=(max(_alld2) if _alld2 else 60)
for _ax in axesp: _ax.set_ylim(0,_gmax2*1.55)
for ax,(col_name,title) in zip(axesp,[("Polar Chromosomes","Polar"),("Lagging Chromosomes","Lagging")]):
    pos=0; xticks=[]; xlabs=[]
    for ph in PH:
        gd={}
        for pres,off in [("Yes",-.18),("No",.18)]:
            pts=[(mdur(r),cohort(r)) for r in sisact if phase_of(r)==ph and yn(r.get(col_name,""))==pres]
            pts=[(x,c) for (x,c) in pts if x is not None]
            d=[x for x,c in pts]; gd[pres]=d
            col=PHCOL[ph]; al=.85 if pres=="Yes" else .35
            if d:
                lib.journal_violin(ax,d,pos+off,col,width=.34,alpha=al*.4)   # scale=width (uniform max half-width per slot), cut=0, N<6 points-only
                # scatter split by sisterless-count marker (single vs triple ablation)
                rs=np.random.RandomState(pos)
                for cohk,mk in MARK.items():
                    dd=[x for x,c in pts if c==cohk]
                    if dd:
                        ax.scatter(np.full(len(dd),pos+off)+(rs.rand(len(dd))-.5)*.1,dd,s=14,color=col,alpha=al,edgecolor="white",lw=.3,marker=mk)
                ax.hlines(np.median(d),pos+off-.13,pos+off+.13,color=col,lw=2)
                ax.hlines(np.mean(d),pos+off-.10,pos+off+.10,color=col,lw=1.1,ls=(0,(2,1.5)))
                ax.text(pos+off,max(d)+_gmax2*0.03,f"N={len(d)}\nx̄{lib.mmss(np.mean(d))}\nm{lib.mmss(np.median(d))}",ha="center",va="bottom",fontsize=5.2)  # LZ1: small pad off the top data point
                for x,c in pts: rows4.append([title,ph,pres,c,round(x,3)])
        if len(gd.get("Yes",[]))>=2 and len(gd.get("No",[]))>=2:
            from scipy import stats as _st
            try: _u,_pp=_st.mannwhitneyu(gd["Yes"],gd["No"],alternative="two-sided"); ax.text(pos,ax.get_ylim()[1]*.98,f"Yes vs No\np={_pp:.2g}",ha="center",va="top",fontsize=6.5,color="#333")
            except Exception: pass
        xticks.append(pos); xlabs.append(ph); pos+=1
    ax.set_xticks(xticks); ax.set_xticklabels(xlabs,fontsize=8.5); ax.set_title(title,fontsize=10)
    ax.set_xlabel("ablation phase")
# single shared legend OUTSIDE the panels (was overlapping the per-violin N + Yes/No labels)
from matplotlib.patches import Patch as _Patch
from matplotlib.lines import Line2D as _L2pl
figp.legend(handles=[_Patch(facecolor="#666",alpha=.85,label="present (Yes) — opaque"),
                     _Patch(facecolor="#666",alpha=.30,label="absent (No) — faint"),
                     _L2pl([0],[0],color="#666",marker="o",ls="none",label="1-sisterless (single)"),
                     _L2pl([0],[0],color="#666",marker="^",ls="none",label="3-sisterless (triple)"),
                     _L2pl([0],[0],color="#444",lw=2,label="median"),
                     _L2pl([0],[0],color="#444",lw=1.1,ls=(0,(2,1.5)),label="mean")],
            fontsize=7,loc="center left",bbox_to_anchor=(1.0,0.5),frameon=False)
axesp[0].set_ylabel("Metaphase duration (MM:SS)")
axesp[0].yaxis.set_major_formatter(FuncFormatter(lambda v,_: lib.mmss(v) if v>=0 else ""))
figp.suptitle("Polar/Lagging presence vs metaphase duration — by ABLATION PHASE (1 & 3-sisterless; circle=single, triangle=triple)",x=.01,ha="left",fontweight="bold")
plt.tight_layout(); plt.savefig(f"{OUT}/G4_polar_lagging_vs_duration_byphase.png",bbox_inches="tight"); plt.close()
lib.record_plot("G4_polar_lagging_vs_duration_byphase",["marker","phase","present","sisterless_cohort","mitotic_duration_min"],rows4,
  {"type":"split violin Yes/No","groups":"by ablation phase (prophase, prometaphase); 1 & 3-sisterless pooled; metaphase group removed","marker_style":"circle=1-sisterless (single), triangle=3-sisterless (triple)"},SCRIPT,
  "Polar/Lagging presence vs metaphase duration, grouped by ablation phase")

lib.flush_review("/Volumes/4 MB/ablation_figures_20260625/_review/outlier_review.csv")
print("polar/lagging done")
