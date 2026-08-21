"""G2_prometaphase_dynamics_lastablation (USER 2026-07-17): same as G2_prometaphase_dynamics but the x-axis is
time from the LAST ablation to metaphase start (instead of first ablation). last->meta = first->meta - ablation
span, where span = (Last Ablation - First Ablation). Same 1-/3-sisterless filtering, same measured-only trend."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from scipy import stats
import lib
try: lib.apply_style()
except Exception: pass
data,_=lib.load_master(); _dbl=lib.double_chromosome_batches()
CMAP={"1":lib.PALETTE["1-Sister"],"3":lib.PALETTE["3-Sister"]}
def md(r):
    d,ok=lib.mitotic_duration_min(r); return d if ok else None
def span_min(r):
    v=lib.parse_time(r.get("Ablation Span (s)","") or "")
    return v/60.0 if v is not None else 0.0   # single ablation -> span 0 -> last==first
PROMETA_REVIEW_EXCLUDE={"20260113 snigle_ablation_visualize chromosome with sisterless kinetochore_1"}
prometa=[r for r in data if (r.get("Phase of Ablations","").strip().lower().startswith("promet") or lib.is_v2_prometaphase(r["Batch Name"]))
         and r.get("Exclude") not in ("Yes","yes") and not lib.excluded(r["Batch Name"]) and not lib.is_mad1(r["Batch Name"])
         and r.get("# Sisterless KTs","") in ("1","3") and not lib.is_drug(r["Batch Name"]) and r["Batch Name"] not in _dbl
         and r["Batch Name"] not in PROMETA_REVIEW_EXCLUDE]
Bp=[]; rows=[]
for r in prometa:
    dur=md(r); am,src=lib.abl_to_meta_min(r,fallback_metastart=True)
    if dur is None or am is None: continue
    x=am-span_min(r)                       # LAST ablation -> metaphase
    if not (-50<=x<200): continue
    Bp.append((x,dur,r.get("# Sisterless KTs",""),src)); rows.append([r["Batch Name"],round(x,2),round(dur,3),src,round(span_min(r),2)])
fig,ax=plt.subplots(figsize=(6.2,5)); _ntxt=[]
for g in ("1","3"):
    gp=[p for p in Bp if p[2]==g]
    if not gp: continue
    gm=[p for p in gp if p[3]!="metastart"]; ge=[p for p in gp if p[3]=="metastart"]
    if gm: ax.scatter([p[0] for p in gm],[p[1] for p in gm],s=34,color=CMAP[g],alpha=.85,edgecolor="white",lw=.4,zorder=3)
    if ge: ax.scatter([p[0] for p in ge],[p[1] for p in ge],s=34,facecolors="none",edgecolors=CMAP[g],lw=1.0,alpha=.9,zorder=3)
    gx=[p[0] for p in gm]; gy=[p[1] for p in gm]; _rt=""
    if len(gx)>=4:
        m,b=np.polyfit(gx,gy,1); xr=np.linspace(min(gx),max(gx),40); ax.plot(xr,m*np.array(xr)+b,"--",color=CMAP[g],lw=1.5,zorder=2)
        rho,p=stats.spearmanr(gx,gy); _rt=f", rho={rho:.2f}, p={p:.2g}"
    _ntxt.append(f"{g}-sis N={len(gx)}{_rt}")
ax.text(.03,.97,"\n".join(_ntxt) if _ntxt else "N=0",transform=ax.transAxes,va="top",fontsize=8)
ax.set_xlabel("Time from LAST ablation to metaphase (min)"); ax.set_ylabel("Metaphase duration (min)")   # lib.mitotic_duration_min is Meta->Ana, not NEB->Ana (2026-07-29)
_nest=sum(1 for p in Bp if p[3]=="metastart")
fig.suptitle(f"Prometaphase-ABLATED cells (1- & 3-sisterless) — LAST-ablation-to-metaphase vs metaphase duration\n"
             f"N={len(Bp)} ({_nest} est.); x = first-ablation->meta minus ablation span. color = sisterless group; trend on measured pts.",
             x=.01,ha="left",fontweight="bold",fontsize=8.3)
plt.tight_layout(); plt.savefig("/Volumes/4 MB/ablation_figures_20260625/custom_collagen_vs_triple/G2_prometaphase_dynamics_lastablation.png",bbox_inches="tight"); plt.close()
lib.record_plot("G2_prometaphase_dynamics_lastablation",["batch","x_min","mitotic_duration_min","abl_meta_source","ablation_span_min"],rows,
  {"type":"scatter","x":"LAST ablation -> metaphase (min) = first-abl->meta - ablation span","y":"mitotic duration (min)",
   "subset":"prometaphase-ablated 1-/3-sisterless (v2 rebin incl.)","trend":"per sisterless group (measured only)",
   "variant_of":"G2_prometaphase_dynamics (x was FIRST ablation->meta)"},
  __file__,"Prometaphase dynamics — LAST ablation to metaphase",source=["/Volumes/4 MB/ABLATION_MASTER.csv"])
print(f"wrote G2_prometaphase_dynamics_lastablation N={len(Bp)}")
