"""G2 prometaphase dynamics — ALTERNATIVE quantifications (USER 2026-07-18): does combining groups or using a
ratio reveal a significant relationship between ablation->metaphase timing and metaphase duration?
x = abl->meta (min); y = meta->ana duration (min). Variants: combined 1+3 trend; combined 1+2+3 trend;
within-group z-scored (removes the per-group intercept confound = the correct 'combined' test); and a ratio
(fraction of post-ablation mitosis spent reaching metaphase vs total post-ablation mitosis)."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, os, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from scipy import stats
import lib
try: lib.apply_style()
except Exception: pass
data,_=lib.load_master(); _dbl=lib.double_chromosome_batches()
CMAP={"1":lib.PALETTE["1-Sister"],"2":"#d68f00","3":lib.PALETTE["3-Sister"]}
prometa=[r for r in data if (r.get("Phase of Ablations","").strip().lower().startswith("promet") or lib.is_v2_prometaphase(r["Batch Name"]))
         and r.get("Exclude") not in ("Yes","yes") and not lib.excluded(r["Batch Name"]) and not lib.is_mad1(r["Batch Name"])
         and r.get("# Sisterless KTs","") in ("1","2","3") and not lib.is_drug(r["Batch Name"]) and r["Batch Name"] not in _dbl]
P=[]  # (group, abl_meta, meta_ana, src)
for r in prometa:
    dur,ok=lib.mitotic_duration_min(r);
    if not ok: continue
    am,src=lib.abl_to_meta_min(r,fallback_metastart=True)
    if am is None or not (0<=am<200) or src=="metastart": continue   # measured only
    P.append((r["# Sisterless KTs"],am,dur,src))
print("measured prometaphase points:",len(P),"| by group:",{g:sum(1 for p in P if p[0]==g) for g in ("1","2","3")})
OUT="/Volumes/4 MB/ablation_figures_20260625/custom_collagen_vs_triple"; os.makedirs(os.path.join(OUT,"illustrator"),exist_ok=True)
def stat_txt(x,y):
    rho,pr=stats.spearmanr(x,y); lr=stats.linregress(x,y)
    return f"Spearman rho={rho:.2f}, p={pr:.2g}\nlin slope={lr.slope:.3f}/min, p={lr.pvalue:.2g}", lr
def save(fig,nm,cap,cols,prov):
    fig.savefig(os.path.join(OUT,nm+".png"),dpi=150); fig.savefig(os.path.join(OUT,"illustrator",nm+".svg")); plt.close(fig)
    lib.record_plot(nm,cols,prov,{"cohort":"prometaphase-ablated 1/2/3-sisterless (measured pts)","x":"abl->meta (min)","y":"meta->ana (min)"},
        __file__,cap,source=["/Volumes/4 MB/ABLATION_MASTER.csv"]); print("wrote",nm)

def combined(groups,tag,title):
    pts=[p for p in P if p[0] in groups]
    fig,ax=plt.subplots(figsize=(7,5.2))
    for g in groups:
        gp=[p for p in pts if p[0]==g]
        ax.scatter([p[1] for p in gp],[p[2] for p in gp],color=CMAP[g],s=34,alpha=.8,edgecolor="w",lw=.4,label=f"{g}-sis (N={len(gp)})",zorder=3)
    x=np.array([p[1] for p in pts]); y=np.array([p[2] for p in pts])
    txt,lr=stat_txt(x,y); xr=np.array([x.min(),x.max()]); ax.plot(xr,lr.slope*xr+lr.intercept,"k--",lw=1.8,zorder=4,label="combined trend")
    # group-covariate-adjusted common slope (removes per-group intercept confound)
    gi=np.array([list(groups).index(p[0]) for p in pts]); cols=[np.ones_like(x),x]+[ (gi==k).astype(float) for k in range(1,len(groups))]
    X=np.column_stack(cols); beta,_,_,_=np.linalg.lstsq(X,y,rcond=None); resid=y-X@beta; n=len(y); k=X.shape[1]
    s2=resid@resid/(n-k); cov=s2*np.linalg.inv(X.T@X); t=beta[1]/np.sqrt(cov[1,1]); pp=2*stats.t.sf(abs(t),df=n-k)
    ax.text(.03,.97,f"COMBINED (N={n}):\n{txt}\ncovariate-adj slope={beta[1]:.3f}, p={pp:.2g}",transform=ax.transAxes,va="top",fontsize=8.5,bbox=dict(boxstyle="round",fc="white",ec=".6"))
    ax.set_xlabel("Time from ablation to metaphase (min)"); ax.set_ylabel("Metaphase duration (min)"); ax.set_title(title); ax.legend(fontsize=8,loc="upper right")
    fig.tight_layout(); save(fig,tag,title,["group","abl_meta_min","meta_ana_min"],[[p[0],round(p[1],2),round(p[2],2)] for p in pts])

combined(("1","3"),"G2_prometa_combined_13","Combined trend — 1+3 sisterless (single+triple)")
combined(("1","2","3"),"G2_prometa_combined_123","Combined trend — 1+2+3 sisterless")

# within-group z-scored duration (removes per-group intercept) vs abl->meta, pooled
fig,ax=plt.subplots(figsize=(7,5.2)); zx=[]; zy=[]
for g in ("1","2","3"):
    gp=[p for p in P if p[0]==g]
    if len(gp)<3: continue
    ys=np.array([p[2] for p in gp]); mu,sd=ys.mean(),ys.std()
    for p in gp:
        z=(p[2]-mu)/sd if sd>0 else 0; ax.scatter(p[1],z,color=CMAP[g],s=34,alpha=.8,edgecolor="w",lw=.4,zorder=3); zx.append(p[1]); zy.append(z)
for g in ("1","2","3"): ax.scatter([],[],color=CMAP[g],label=f"{g}-sis")
zx=np.array(zx); zy=np.array(zy); txt,lr=stat_txt(zx,zy); xr=np.array([zx.min(),zx.max()]); ax.plot(xr,lr.slope*xr+lr.intercept,"k--",lw=1.8)
ax.text(.03,.97,f"within-group z-scored (N={len(zx)}):\n{txt}",transform=ax.transAxes,va="top",fontsize=8.5,bbox=dict(boxstyle="round",fc="white",ec=".6"))
ax.axhline(0,color=".8",lw=1); ax.set_xlabel("Time from ablation to metaphase (min)"); ax.set_ylabel("Metaphase duration (z-score WITHIN sisterless group)")
ax.set_title("Combined after removing per-group intercept (within-group z-scored)"); ax.legend(fontsize=8)
fig.tight_layout(); save(fig,"G2_prometa_zscore","Within-group z-scored metaphase duration vs abl->meta (pooled)",["group","abl_meta_min","dur_zscore"],[[p[0],round(p[1],2)] for p in P])

# ratio: fraction of post-ablation mitosis spent reaching metaphase vs total post-ablation mitosis
fig,ax=plt.subplots(figsize=(7,5.2)); fx=[]; fy=[]
for p in P:
    tot=p[1]+p[2]; frac=p[1]/tot if tot>0 else 0
    ax.scatter(frac,tot,color=CMAP[p[0]],s=34,alpha=.8,edgecolor="w",lw=.4,zorder=3); fx.append(frac); fy.append(tot)
for g in ("1","2","3"): ax.scatter([],[],color=CMAP[g],label=f"{g}-sis")
fx=np.array(fx); fy=np.array(fy); txt,lr=stat_txt(fx,fy); xr=np.array([fx.min(),fx.max()]); ax.plot(xr,lr.slope*xr+lr.intercept,"k--",lw=1.8)
ax.text(.03,.97,f"ratio view (N={len(fx)}):\n{txt}",transform=ax.transAxes,va="top",fontsize=8.5,bbox=dict(boxstyle="round",fc="white",ec=".6"))
ax.set_xlabel("Fraction of post-ablation mitosis spent reaching metaphase\n= (abl->meta) / (abl->meta + meta->ana)")
ax.set_ylabel("Total post-ablation mitosis (abl->anaphase, min)"); ax.set_title("Ratio quantification: fraction-to-metaphase vs total post-ablation time")
ax.legend(fontsize=8); fig.tight_layout()
save(fig,"G2_prometa_ratio","Fraction-to-metaphase vs total post-ablation mitosis",["group","frac_to_meta","total_min"],[[p[0],round(p[1]/(p[1]+p[2]),3),round(p[1]+p[2],2)] for p in P])
print("DONE")
