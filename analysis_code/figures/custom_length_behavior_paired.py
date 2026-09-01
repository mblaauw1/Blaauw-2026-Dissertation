"""Length vs congression behavior — reads the ONE consolidated source: CHROMOSOME_MASTER.csv
(per-chromosome length↔behavior, properly paired). Regenerate that file with build_chromosome_annotations_master.py.
"""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, os, numpy as np, matplotlib.pyplot as plt
from scipy import stats
from collections import defaultdict
import lib
lib.apply_style()   # 2026-08-17: was MISSING. apply_style() installs the Figure.savefig hook that
                    # mirrors every PNG to illustrator/*.svg AND to _ai_relink/pdf/*.pdf -- the PDFs the
                    # .ai decks LINK. Without it this builder wrote a fresh PNG while its deck figure
                    # kept whatever PDF some other script last emitted (G3 PDFs were 7.8 DAYS stale and
                    # G3_length_vs_behavior_paired.pdf did not exist at all), so re-running after a data
                    # fix silently never reached the deck. Also applies the house style/font scaling.
OUT="/Volumes/4 MB/ablation_figures_20260625/group3"; os.makedirs(OUT,exist_ok=True); SCRIPT=__file__
SRC="/Volumes/4 MB/annotations/CHROMOSOME_MASTER.csv"
rows=[]
for r in csv.DictReader(open(SRC)):
    L=r.get('length_um','').strip(); bh=r.get('behavior','').strip()
    if not L or not bh: continue
    try: L=float(L)
    except: continue
    d=r.get('congression_delay_from_meta_onset_s','').strip()
    d=float(d) if d else None
    rows.append((r['batch'],r['chr_num'],L,bh,d))

fig,(axA,axB)=plt.subplots(1,2,figsize=(12.6,5.2))
# A: length vs congression delay
cd=[(L,d/60.0) for _,_,L,bh,d in rows if bh=="congressed" and d is not None]
X=[x for x,_ in cd]; Y=[y for _,y in cd]
axA.scatter(X,Y,s=42,color="#2166ac",alpha=.82,edgecolor="white",lw=.4)
if len(X)>=3:
    m,b=np.polyfit(X,Y,1); xr=np.linspace(min(X),max(X),20); axA.plot(xr,m*xr+b,"-",color="#222",lw=1.8)
rho,p=stats.spearmanr(X,Y)
axA.set_title(f"Longer chromosomes congress LATER\nSpearman ρ={rho:.2f}, p={p:.3g}, N={len(X)}",fontsize=11)
axA.set_xlabel("chromosome length (µm)"); axA.set_ylabel("congression delay from metaphase onset (min)")
# B: length by behavior
CATS=[("at_plate","at plate\nwhole time","#1b7837"),("congressed","congressed","#2166ac"),("noncongression","never congressed\n(polar→anaphase)","#762a83")]
g=defaultdict(list)
for _,_,L,bh,_ in rows: g[bh].append(L)
for i,(k,lab,col) in enumerate(CATS):
    v=g[k]
    if not v: continue
    x=i+1
    axB.boxplot([v],positions=[x],widths=.55,patch_artist=True,boxprops=dict(facecolor=col,alpha=.25,edgecolor=col),
                medianprops=dict(color=col,lw=2),whiskerprops=dict(color=col),capprops=dict(color=col),showfliers=False)
    jit=(np.random.RandomState(i).rand(len(v))-.5)*.3
    axB.scatter(np.full(len(v),x)+jit,v,s=26,color=col,alpha=.7,edgecolor="white",lw=.3)
    axB.text(x+0.36,np.median(v),f"{np.mean(v):.1f}µm\nn={len(v)}",ha="left",va="center",fontsize=8,color=col)
axB.set_xticks([1,2,3]); axB.set_xticklabels([c[1] for c in CATS],fontsize=9); axB.set_ylabel("chromosome length (µm)")
present=[g[k] for k,_,_ in CATS if len(g[k])>=2]
kw=stats.kruskal(*present) if len(present)>=2 else None
axB.set_title(f"Length by post-ablation behavior\nKruskal p={kw.pvalue:.3g}" if kw else "Length by behavior",fontsize=11)
fig.suptitle("Chromosome length vs congression behavior — CHROMOSOME_ANNOTATIONS_MASTER (properly paired, N="+str(len(rows))+" chromosomes / "+str(len(set(r[0] for r in rows)))+" cells)",
             fontweight="bold",fontsize=11.5,x=.01,ha="left")
plt.tight_layout(rect=[0,0,1,0.955])
plt.savefig(f"{OUT}/G3_length_vs_behavior_paired.png",bbox_inches="tight",dpi=135); plt.close()
lib.record_plot("G3_length_vs_behavior_paired",["batch","chr_num","length_um","behavior","delay_s"],[],
                {"source":"CHROMOSOME_MASTER.csv","rho_delay":round(rho,3),"p_delay":round(p,4),
                 "kruskal_p":round(kw.pvalue,4) if kw else None,"N_chromosomes":len(rows)},SCRIPT,"Length vs congression behavior (consolidated source)", fig=fig)
print(f"built | N={len(rows)} chromosomes | congressed-delay N={len(X)} ρ={rho:.2f} p={p:.3g} | Kruskal p={kw.pvalue:.3g}")
print(f"  means: "+" ".join(f"{k}={np.mean(g[k]):.2f}µm(n{len(g[k])})" for k,_,_ in CATS if g[k]))
