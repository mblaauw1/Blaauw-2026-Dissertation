"""#44 — Does WHEN the sisterless KT is created relate to its behavior?
Creation = ablation. Two questions the user posed:
  (A) Ablation PHASE as a category: prophase-created vs prometaphase-created behavior (prophase = just prophase).
  (B) WITHIN prometaphase: creation→metaphase interval (Ablation->Meta) vs behavior (timing reference to metaphase).
Time source: master 'Ablation->Meta (s)' (interval from ablation to metaphase onset) — NOT First Ablation (absolute epoch).
Behavior: consolidated CHROMOSOME_ANNOTATIONS_MASTER.
"""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, os, numpy as np, matplotlib.pyplot as plt
from collections import defaultdict, Counter
from scipy import stats
import lib
OUT="/Volumes/4 MB/ablation_figures_20260625/group3"; os.makedirs(OUT,exist_ok=True); SCRIPT=__file__
SRC="/Volumes/4 MB/annotations/CHROMOSOME_MASTER.csv"
data,_=lib.load_master(); mr={r["Batch Name"]:r for r in data}
def gv(b,c): return (mr.get(b,{}).get(c,"") or "").strip()
def num(b,c):
    v=gv(b,c)
    try: return float(v)
    except: return lib.parse_time(v)
def phase(b):
    if lib.is_v2_prometaphase(b): return 'Prometaphase'   # USER RULE: v2 binning is the standard (2026-07-22 sweep)
    p=gv(b,'Phase of Ablations').lower()
    return 'Prophase' if p.startswith('proph') else 'Prometaphase' if p.startswith('promet') else 'Metaphase' if p.startswith('metaph') else None

chrom=defaultdict(list)
for r in csv.DictReader(open(SRC)):
    d=r.get('congression_delay_from_meta_onset_s','').strip()
    chrom[r['batch'].strip()].append(dict(bh=r.get('behavior','').strip() or None,delay=(float(d) if d else None)))
cr=[]
# 🔴 HER 2026-08-25 item 13: *"G3_lagging_by_creation_phase the N for each group does not make sense"*. It
# did not: prometaphase 3-sisterless read **30** against a 3-Sister cohort of **28**. This loop tested only
# `On-Target / Off-Target == on-target` and applied NONE of the standing exclusions -- Exclude=Yes, Mad1,
# REVIEW_EXCLUDE, drug, metaphase-ablation, 4-sisterless, double-chromosome -- so cells that belong to no
# cohort were being counted. Membership now comes from `lib.assign_cohorts()`, the one place those rules
# live, with `include_prophase=True` because this figure DRAWS a prophase group (that flag is exactly what
# it is for; without it every prophase cell would vanish from a figure about creation phase).
_COH_OF = {}
for _k, _lst in lib.assign_cohorts(include_prophase=True).items():
    for _e in _lst:
        _COH_OF[_e[0] if isinstance(_e, (list, tuple)) else _e] = _k
for b,cs in chrom.items():
    if _COH_OF.get(b) not in ("1-Sister", "3-Sister"): continue
    ph=phase(b); am=num(b,'Ablation->Meta (s)')
    for c in cs:
        if c['bh']: cr.append(dict(b=b,ph=ph,am=am,bh=c['bh'],delay=c['delay'],ns=gv(b,'# Sisterless KTs').strip()))

CATS=[("at_plate","at plate","#1b7837"),("congressed","congressed","#2166ac"),("noncongression","stayed polar","#762a83")]
# USER 2026-08-05: "this is two figures bundled into one so split them apart into each their own figure",
# and panel A goes from 2 bars to 4 (phase x ablation number).
figA,axA=plt.subplots(figsize=(7.0,5.3))
figB,axB=plt.subplots(figsize=(6.4,5.3))
GROUPS4=[("Prophase","1"),("Prophase","3"),("Prometaphase","1"),("Prometaphase","3")]

# ---- A: behavior composition by ablation phase x ablation number (4 bars, USER 2026-08-05) ----
tab=[]; labs=[]
for i,(ph,ns) in enumerate(GROUPS4):
    sub=[c for c in cr if c['ph']==ph and c['ns']==ns]; tot=len(sub) or 1; cc=Counter(c['bh'] for c in sub); bottom=0
    for k,lab,col in CATS:
        frac=cc[k]/tot; axA.bar(i,frac,bottom=bottom,color=col,edgecolor="white",width=.62,label=(lab if i==0 else None))
        if frac>.06: axA.text(i,bottom+frac/2,f"{100*frac:.0f}%",ha="center",va="center",color="white",fontsize=8.5,fontweight="bold")
        bottom+=frac
    axA.text(i,1.02,f"n={len(sub)}",ha="center",fontsize=8,color="#555")
    tab.append([cc['noncongression'],len(sub)-cc['noncongression']]); labs.append(f"{ph.lower()}\n{ns}-sisterless")
_use=[t for t in tab if sum(t)>0]
chi2,pph,_,_=stats.chi2_contingency(_use) if len(_use)>=2 else (float('nan'),float('nan'),0,None)
axA.set_xticks(range(len(GROUPS4))); axA.set_xticklabels(labs,fontsize=8.5)
axA.set_ylabel("fraction of ablated chromosomes"); axA.set_ylim(0,1.12)
axA.legend(fontsize=8.5,loc="upper center",ncol=3,bbox_to_anchor=(.5,-.13),frameon=False)
_pol=[f"{100*t[0]/max(sum(t),1):.0f}%" for t in tab]
axA.set_title("Does creation phase change kinetochore fate?\nstayed polar: "+" · ".join(f"{l.replace(chr(10),' ')} {v}" for l,v in zip(labs,_pol))+f"\nchi² p={pph:.2g}",fontsize=9)

# ---- B: within prometaphase, creation→metaphase interval vs behavior ----
pm=[c for c in cr if c['ph']=='Prometaphase' and c['am'] is not None]
nonpol=[c['am']/60 for c in pm if c['bh'] in("congressed","at_plate")]
pol=[c['am']/60 for c in pm if c['bh']=="noncongression"]
u=stats.mannwhitneyu(pol,nonpol) if (len(pol)>=3 and len(nonpol)>=3) else None
for i,(v,lab,col) in enumerate([(nonpol,"congressed /\nat plate","#2166ac"),(pol,"stayed\npolar","#762a83")]):
    if not v: continue
    x=i+1
    axB.boxplot([v],positions=[x],widths=.55,patch_artist=True,boxprops=dict(facecolor=col,alpha=.22,edgecolor=col),
                medianprops=dict(color=col,lw=2),whiskerprops=dict(color=col),capprops=dict(color=col),showfliers=False)
    jit=(np.random.RandomState(i).rand(len(v))-.5)*.28; axB.scatter(np.full(len(v),x)+jit,v,s=28,color=col,alpha=.75,edgecolor="white",lw=.3)
    # 2026-08-04: these sat ON the box at x, so the median value and n printed over the median line and the
    # scattered points. Push them just outside the box instead.
    axB.text(x+0.34,np.median(v),f"{np.median(v):.1f}\nn={len(v)}",ha="left",va="center",fontsize=8,color=col)
axB.set_xticks([1,2]); axB.set_xticklabels(["congressed /\nat plate","stayed\npolar"],fontsize=9)
axB.set_ylabel("creation→metaphase interval (min)\n(time from ablation to metaphase onset)")
axB.set_title("Within prometaphase: creation timing\ndoes NOT separate behavior"+(f" · MWU p={u.pvalue:.2g}" if u else ""),fontsize=10)
figA.suptitle("#44a  Sisterless-KT creation phase vs behavior — CHROMOSOME_ANNOTATIONS_MASTER (on-target)",
              fontweight="bold",fontsize=10.5,x=.01,ha="left")
figA.tight_layout(rect=[0,0,1,0.93])
figA.savefig(f"{OUT}/G3_creation_phase_vs_behavior.png",bbox_inches="tight",dpi=135)
figA.savefig("/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/G3_creation_phase_vs_behavior.pdf",bbox_inches="tight")
lib.record_plot("G3_creation_phase_vs_behavior",["phase","n_sisterless","n_chromosomes","frac_stayed_polar"],
                [[GROUPS4[i][0],GROUPS4[i][1],sum(tab[i]),round(tab[i][0]/max(sum(tab[i]),1),4)] for i in range(len(GROUPS4))],
                {"source":"CHROMOSOME_MASTER.csv","bars":"phase x ablation number (USER 2026-08-05)",
                 "chi2_p":None if pph!=pph else round(pph,4)},SCRIPT,"Creation phase vs behavior (4 groups)",fig=figA)
plt.close(figA)

figB.suptitle("#44b  Within prometaphase: creation timing vs behavior",fontweight="bold",fontsize=10.5,x=.01,ha="left")
figB.tight_layout(rect=[0,0,1,0.93])
figB.savefig(f"{OUT}/G3_creation_timing_vs_behavior.png",bbox_inches="tight",dpi=135)
figB.savefig("/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/G3_creation_timing_vs_behavior.pdf",bbox_inches="tight")
lib.record_plot("G3_creation_timing_vs_behavior",["group","creation_to_meta_min"],
                [["stayed_polar",round(v,3)] for v in pol]+[["congressed_or_at_plate",round(v,3)] for v in nonpol],
                {"source":"CHROMOSOME_MASTER.csv","MWU_p":round(u.pvalue,4) if u else None},
                SCRIPT,"Within prometaphase: creation timing vs behavior",fig=figB)
plt.close(figB)

# ---- NEW (USER 2026-08-05): chance of forming a LAGGING connection, same 4 groups ----
LAG={r["Batch Name"]:(r.get("Lagging Chromosomes") or "").strip().lower() for r in lib.load_master()[0]}
figC,axC=plt.subplots(figsize=(7.0,5.0)); rowsC=[]; tabC=[]
for i,(ph,ns) in enumerate(GROUPS4):
    cells={c['b'] for c in cr if c['ph']==ph and c['ns']==ns}
    yes=sum(1 for b in cells if LAG.get(b)=="yes"); no=sum(1 for b in cells if LAG.get(b)=="no")
    tot=yes+no
    frac=yes/tot if tot else 0.0
    axC.bar(i,frac,color="#d1495b",alpha=.85,width=.62)
    axC.text(i,frac+.02,f"{100*frac:.0f}%\nN={tot}",ha="center",va="bottom",fontsize=8.5)
    tabC.append([yes,no]); rowsC.append([ph,ns,tot,yes,no,round(frac,4)])
_useC=[t for t in tabC if sum(t)>0]
chi2C,pC,_,_=stats.chi2_contingency(_useC) if len(_useC)>=2 else (float('nan'),float('nan'),0,None)
axC.set_xticks(range(len(GROUPS4))); axC.set_xticklabels([f"{p.lower()}\n{n}-sisterless" for p,n in GROUPS4],fontsize=8.5)
axC.set_ylabel("fraction of cells with a lagging chromosome"); axC.set_ylim(0,1.2)
axC.set_title(f"Chance of forming a lagging connection, by creation phase and ablation number\nchi² p={pC:.2g}",
              loc="left",fontweight="bold",fontsize=9.5)
figC.tight_layout(); figC.savefig(f"{OUT}/G3_lagging_by_creation_phase.png",bbox_inches="tight",dpi=135)
figC.savefig("/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/G3_lagging_by_creation_phase.pdf",bbox_inches="tight")
lib.record_plot("G3_lagging_by_creation_phase",["phase","n_sisterless","N_cells","lag_yes","lag_no","frac_lagging"],
                rowsC,{"unit":"cell","chi2_p":None if pC!=pC else round(pC,4)},
                SCRIPT,"Lagging likelihood by creation phase and ablation number",fig=figC)
plt.close(figC)
print("built #44a / #44b / lagging-by-creation-phase")
for r_ in rowsC: print("   ",r_)
print(f"  4-group behavior chi2 p={pph:.3g}" + (f" | timing MWU p={u.pvalue:.3g}" if u else ""))
