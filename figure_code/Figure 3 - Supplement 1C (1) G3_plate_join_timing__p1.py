"""Succinct summary — when sisterless kinetochores reach the metaphase plate, within the metaphase->anaphase window."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, numpy as np, matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import lib
lib.apply_style()
OUT="/Volumes/4 MB/ablation_figures_20260625/group3"; SCRIPT=__file__
data,_=lib.load_master(); mr={r["Batch Name"]:r for r in data}
_DBL=set(lib.double_chromosome_batches())   # double-chromosome cells excluded everywhere (was leaking into plate_join)
r=list(csv.reader(open("/Volumes/4 MB/annotations/SISTERLESS_PLATE_JOIN_TIMES.csv"))); ix={c:i for i,c in enumerate(r[0])}
rows_frac=[]; rows_abs=[]
for row in r[1:]:
    if row[ix['exclude_this_data']].strip(): continue
    b=row[ix['batch']].strip(); n=row[ix['n_sisterless']].strip()
    if lib.is_mad1(b) or lib.plot_excluded(b) or b in _DBL: continue   # +REVIEW_EXCLUDE +double-chromosome guard
    if n not in ("1","2","3"): continue
    meta=lib.parse_time(mr.get(b,{}).get("Metaphase Start (s)","")); ana=lib.parse_time(mr.get(b,{}).get("Anaphase Onset (s)",""))
    for k in (1,2,3):
        v=row[ix[f'chromosome_{k}_plate_join']].strip(); s=row[ix[f'chromosome_{k}_plate_join_s']].strip()
        if not v or v.lower() in ("n/a","anaphase") or v in("0","0:00:00"): continue
        try: jt=float(s)
        except: continue
        if meta is None: continue
        t_after=(jt-meta)/60.0   # minutes after metaphase
        # D13 (2026-07-07): drop plate-joins that occur BEFORE metaphase onset (below the metaphase-start line) —
        # not relevant to arrival-within-metaphase to anaphase. (Removes the one 3-sisterless point in BOTH panels.)
        if t_after<0:
            lib.log_review("plate_join_before_metaphase",b,f"{t_after:.2f}min (n={n},k={k})","joins plate before metaphase onset — removed from arrival plots (D13)"); continue
        rows_abs.append([b,n,round(t_after,2)])
        if ana and ana>meta:
            frac=(jt-meta)/(ana-meta)
            if 0<=frac<=1.5: rows_frac.append([b,n,round(frac,3)])

PAL={"1":lib.PALETTE["1-Sister"],"2":lib.PALETTE["2-Sister"],"3":lib.PALETTE["3-Sister"]}
fig,(a1,a2)=plt.subplots(1,2,figsize=(11,4.8))
# left: minutes after metaphase, by sister group
_ymax_abs=max([x[2] for x in rows_abs], default=1)
a1.set_ylim(top=_ymax_abs*1.34)   # headroom so median/N labels sit below the panel title (no overlap)
for i,n in enumerate("13"):
    d=[x[2] for x in rows_abs if x[1]==n]
    if not d: continue
    a1.scatter(np.full(len(d),i)+(np.random.RandomState(i).rand(len(d))-.5)*.22,d,s=26,color=PAL[n],alpha=.8,edgecolor="white",lw=.3)
    a1.hlines(np.median(d),i-.3,i+.3,color=PAL[n],lw=2.4); a1.text(i,_ymax_abs*1.14,f"med {np.median(d):.1f}min\nN={len(d)}",ha="center",va="center",fontsize=8)   # aligned annotation row, clear of title
a1.set_xticks([0,1]); a1.set_xticklabels([lib.lbl("1-Sister"),lib.lbl("3-Sister")]); a1.set_ylabel("minutes after metaphase onset"); a1.axhline(0,color="#999",lw=.6)
a1.set_title("Absolute timing (min after metaphase onset)",fontsize=10)
# right: fraction of metaphase->anaphase window
for i,n in enumerate("13"):
    d=[x[2] for x in rows_frac if x[1]==n]
    if not d: continue
    a2.scatter(np.full(len(d),i)+(np.random.RandomState(i+9).rand(len(d))-.5)*.22,d,s=26,color=PAL[n],alpha=.8,edgecolor="white",lw=.3)
    a2.hlines(np.median(d),i-.3,i+.3,color=PAL[n],lw=2.4); a2.text(i,1.05,f"N={len(d)}",ha="center",fontsize=8)
a2.axhline(0,color="#1b7837",lw=1,ls="--"); a2.text(2.4,0.0,"metaphase",fontsize=7,color="#1b7837",va="center")
a2.axhline(1,color="#b2182b",lw=1,ls="--"); a2.text(2.4,1.0,"anaphase",fontsize=7,color="#b2182b",va="center")
a2.set_xticks([0,1]); a2.set_xticklabels([lib.lbl("1-Sister"),lib.lbl("3-Sister")]); a2.set_ylabel("Fraction of metaphase elapsed at plate-join"); a2.set_ylim(-0.25,1.3)
a2.set_title("Normalized to metaphase to anaphase window",fontsize=10)
fig.suptitle("Sisterless-kinetochore arrival at the metaphase plate (timing within metaphase to anaphase)",x=.01,ha="left",fontweight="bold")
plt.tight_layout(); plt.savefig(f"{OUT}/G3_plate_join_timing.png",bbox_inches="tight"); plt.close()
lib.record_plot("G3_plate_join_timing",["batch","n_sisterless","value"],rows_abs,
  {"type":"2-panel strip","left":"min after metaphase","right":"fraction of meta->ana window","source":"SISTERLESS_PLATE_JOIN_TIMES + master event times"},
  SCRIPT,"Sisterless KT arrival at metaphase plate, timed within metaphase->anaphase")
print(f"plate timing: abs N={len(rows_abs)}, frac N={len(rows_frac)}")
