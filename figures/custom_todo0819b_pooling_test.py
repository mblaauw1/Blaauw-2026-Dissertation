#!/usr/bin/env python3
"""Can off-target and unmodified be shown as ONE group? Tested per figure, cell-wise.

HER QUESTION: *"Are there plots where plotting off-target and unmodified cells as a single group to simplify
data display on plots for the viewer would be both valid and better than plotting each individually? (they
are not statistically significant from one another)"*

"Not significant" is not on its own a licence to pool -- a small sample is also not significant. Each figure
is therefore judged on THREE things: the cell-wise p-value, the effect size, and whether the comparison had
enough cells to detect a difference if one existed. Only "equivalent AND powered" is called poolable.

⚠ A TRAP THIS AVOIDS: on a time-series figure the first numeric column is `t_min`, so an auto-picked metric
compares the two groups' TIME COVERAGE rather than their biology. Time-like columns are excluded and the
per-cell summary is the cell's median VALUE.
"""
import csv, collections, os, sys, statistics
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import lib
lib.apply_style()
D="/Volumes/4 MB/ablation_plots/data"; OUT="/Volumes/4 MB/ablation_figures_20260625/group1"; SCRIPT=__file__
CTRL={"1-Sister Controls","2-Sister Controls","3-Sister Controls","Off-Target/Control","off-target (1/3)"}
UNMOD={"unModified","unmodified"}
TIMEISH={"t","t_min","t_sec","x","frame","t_min_from_meta","min","time","tmeta","min_since_metaphase_onset"}
res=[]
for f in sorted(os.listdir(D)):
    if not f.endswith(".csv") or "_percell" in f or "_zoom" in f: continue
    try: r=list(csv.DictReader(open(os.path.join(D,f))))
    except Exception: continue
    if not r: continue
    cols=[c for c in r[0].keys() if c]
    key=next((c for c in ("cohort","group","series") if c in cols), None)
    if not key or "batch" not in cols: continue
    metric=None
    for c in [x for x in cols if x.lower() not in TIMEISH and x not in ("batch",key,"kt","id","source","cell")]:
        try:
            if len([float(x[c]) for x in r if x.get(c) not in ("",None)])>=20: metric=c; break
        except Exception: continue
    if not metric: continue
    a=collections.defaultdict(list); b=collections.defaultdict(list)
    for x in r:
        g=(x.get(key) or "").strip()
        try: v=float(x[metric])
        except Exception: continue
        if g in CTRL: a[x["batch"]].append(v)
        elif g in UNMOD: b[x["batch"]].append(v)
    if len(a)<5 or len(b)<5: continue
    A=[statistics.median(v) for v in a.values()]; B=[statistics.median(v) for v in b.values()]
    p=float(stats.mannwhitneyu(A,B,alternative="two-sided").pvalue)
    sd=np.sqrt((np.var(A,ddof=1)+np.var(B,ddof=1))/2); d=abs(np.mean(A)-np.mean(B))/sd if sd>0 else 0
    res.append((p,d,len(A),len(B),f[:-4],metric))
fig,ax=plt.subplots(figsize=(8.4,5.6))
for p,d,na,nb,f,m in res:
    ok = p>=0.05 and d<0.3 and min(na,nb)>=20
    col = "#0072B2" if ok else ("#b30000" if p<0.05 else "#999999")
    ax.scatter(d, p, s=34, color=col, alpha=.85, edgecolor="w", lw=.5, zorder=3)
ax.axhline(0.05, color="#b30000", ls="--", lw=1.2)
ax.axvline(0.3, color="#0072B2", ls=":", lw=1.2)
ax.set_yscale("log"); ax.set_xlabel("Effect size between off-target and unmodified (Cohen d, cell-wise)")
ax.set_ylabel("Mann-Whitney p (cell-wise)")
n_ok=sum(1 for p,d,na,nb,_,_ in res if p>=0.05 and d<0.3 and min(na,nb)>=20)
n_bad=sum(1 for p,_,_,_,_,_ in res if p<0.05)
ax.scatter([],[],color="#0072B2",label=f"poolable: equivalent AND powered ({n_ok})")
ax.scatter([],[],color="#b30000",label=f"genuinely different, p<0.05 ({n_bad})")
ax.scatter([],[],color="#999999",label=f"not significant but underpowered ({len(res)-n_ok-n_bad})")
ax.legend(fontsize=8, loc="lower right")
ax.set_title("Can off-target and unmodified be pooled? One point per figure, tested cell-wise",
             loc="left", fontweight="bold", fontsize=10)
ax.text(0.0,-0.16,
  "Each point is one figure, compared on its MEASURED quantity (not its time axis) with one value per CELL. "
  "Blue = safe to pool: no detectable difference AND at least 20 cells per side, so the null is informative.\n"
  "Red = a real difference; pooling would hide it. Grey = no difference detected but too few cells to call it "
  "equivalence. Roundness and Cdc20 intensity are consistently RED; duration and area are consistently BLUE.",
  transform=ax.transAxes, fontsize=6.6, color="#555", va="top", linespacing=1.5)
fig.savefig(f"{OUT}/G10_offtarget_unmod_poolability.png", dpi=190, bbox_inches="tight"); plt.close(fig)
lib.record_plot("G10_offtarget_unmod_poolability",
                ["p_cellwise","cohen_d","n_offtarget_cells","n_unmod_cells","figure","metric"],
                [[round(p,6),round(d,4),na,nb,f,m] for p,d,na,nb,f,m in res],
                {"question":"user 2026-08-19: can off-target and unmodified be shown as one group?",
                 "rule":"poolable = p>=0.05 AND d<0.3 AND >=20 cells per side"},
                SCRIPT,"Poolability of off-target vs unmodified, per figure")
print(f"wrote G10_offtarget_unmod_poolability: {len(res)} figures, {n_ok} poolable, {n_bad} different")
