"""Does LAGGING depend on WHEN a chromosome congresses in metaphase? (USER 2026-07-19)
Hypothesis: a sisterless chromosome that (re)joins the plate LATER in metaphase is less well bi-oriented and
more likely to LAG at anaphase. Per cell we take the congression fraction f = (t_join - meta)/(ana - meta) of
the LAST sisterless KT to join (the laggard-candidate), and compare cells flagged Lagging=Yes vs No.
Also: latest congression time (min from metaphase onset) vs n_lagging_kinetochores (from the annotation csv).
Cohort: cdc20 on-target, non-drug, non-mad1, non-double-chromosome, not-excluded, with congression data + meta+ana."""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import csv, re, os, numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
import lib
try: lib.apply_style()
except Exception: pass
def tmin(s):
    s=(s or "").strip()
    if not s: return None
    p=s.split(":")
    try: return (int(p[0])*3600+int(p[1])*60+int(float(p[2])))/60.0 if len(p)==3 else int(p[0])+int(p[1])/60.0
    except: return None

data,_=lib.load_master_plots(); mr={r["Batch Name"]:r for r in data}
_DBL=lib.double_chromosome_batches()
pj={r["batch"].strip():r for r in csv.DictReader(open("/Volumes/4 MB/annotations/SISTERLESS_PLATE_JOIN_TIMES.csv"))
    if (r.get("exclude_this_data") or "").lower()!="yes"}
def ok(r):
    b=r["Batch Name"]
    return ("on-target" in (r.get("On-Target / Off-Target","").lower()) and not lib.is_drug(b)
            and not lib.is_mad1(b) and b not in _DBL and r.get("Exclude") not in ("Yes","yes")
            and not lib.excluded(b) and r.get("# Sisterless KTs","") in ("1","2","3"))

rows=[]
for b,pr in pj.items():
    r=mr.get(b)
    if not r or not ok(r): continue
    meta=tmin(r.get("Metaphase Start (s)","")); ana=tmin(r.get("Anaphase Onset (s)",""))
    if meta is None or ana is None or ana<=meta: continue
    # congression fractions among chromosomes that join at a finite time (>0)
    fs=[]; ts=[]
    for k in ("chromosome_1_plate_join","chromosome_2_plate_join","chromosome_3_plate_join"):
        v=(pr.get(k) or "").strip().lower()
        if not v or v in ("n/a","anaphase","0","0:00:00"): continue
        t=tmin(v)
        if t is None: continue
        f=(t-meta)/(ana-meta); fs.append(min(1.0,max(0.0,f))); ts.append((t-meta))
    if not fs: continue   # need at least one timed congression
    lag=(r.get("Lagging Chromosomes","") or "").strip().lower()
    if lag not in ("yes","no"): continue
    try: nlag=int((pr.get("n_lagging_kinetochores") or "").strip())
    except Exception: nlag=None
    rows.append(dict(batch=b,group=r.get("# Sisterless KTs",""),lag=lag,
                     latest_f=max(fs),mean_f=float(np.mean(fs)),latest_min=max(ts),nlag=nlag))
print(f"cells with timed congression + lagging flag: {len(rows)} | Lagging Yes={sum(1 for x in rows if x['lag']=='yes')} No={sum(1 for x in rows if x['lag']=='no')}")

OUT="/Volumes/4 MB/ablation_figures_20260625/custom_collagen_vs_triple"; os.makedirs(os.path.join(OUT,"illustrator"),exist_ok=True)
GC={"1":"#2e9e3f","2":"#d68f00","3":"#8e44ad"}
def save(fig,nm,cap,cols,prov,extra):
    fig.savefig(os.path.join(OUT,nm+".png"),dpi=150,bbox_inches="tight"); fig.savefig(os.path.join(OUT,"illustrator",nm+".svg")); plt.close(fig)
    lib.record_plot(nm,cols,prov,extra,__file__,cap,
        source=["/Volumes/4 MB/ABLATION_MASTER.csv","/Volumes/4 MB/annotations/SISTERLESS_PLATE_JOIN_TIMES.csv"])
    print("wrote",nm)

# ---- Plot 1: latest congression FRACTION, Lagging Yes vs No (strip + box + Mann-Whitney) ----
yes=[x["latest_f"] for x in rows if x["lag"]=="yes"]; no=[x["latest_f"] for x in rows if x["lag"]=="no"]
fig,ax=plt.subplots(figsize=(6.4,5.2))
for i,(grp,vals,lab) in enumerate([("no",no,f"No lagging\n(N={len(no)})"),("yes",yes,f"Lagging\n(N={len(yes)})")]):
    xs=np.full(len(vals),i)+ (np.random.RandomState(i+7).rand(len(vals))-0.5)*0.16
    cols=[GC.get(x["group"],"#888") for x in rows if x["lag"]==grp]
    ax.scatter(xs,vals,c=cols,s=48,alpha=.85,edgecolor="w",lw=.5,zorder=3)
    if vals:
        ax.boxplot([vals],positions=[i],widths=.5,showfliers=False,
                   boxprops=dict(color="#444"),medianprops=dict(color="#111",lw=2),whiskerprops=dict(color="#888"),capprops=dict(color="#888"))
ax.set_xticks([0,1]); ax.set_xticklabels([f"No lagging (N={len(no)})",f"Lagging (N={len(yes)})"])
ax.set_ylabel("Latest sisterless-KT congression\n(fraction of metaphase elapsed: 0=onset, 1=anaphase)")
ttl="Does the last sisterless KT congress LATER in cells that lag?"
if yes and no:
    u,p=stats.mannwhitneyu(yes,no,alternative="two-sided")
    ax.text(.03,.97,f"Mann-Whitney p={p:.3g}\nmedian late-f: lag={np.median(yes):.2f} vs no-lag={np.median(no):.2f}",
            transform=ax.transAxes,va="top",fontsize=9,bbox=dict(boxstyle="round",fc="white",ec=".6"))
for g in ("1","2","3"): ax.scatter([],[],color=GC[g],label=f"{g}-sisterless")
ax.legend(fontsize=8,title="cell group"); ax.set_title(ttl,fontsize=11)
save(fig,"G4_lagging_vs_congression_fraction",ttl,["batch","group","lagging","latest_congress_fraction"],
     [[x["batch"],x["group"],x["lag"],round(x["latest_f"],3)] for x in rows],
     {"cohort":"cdc20 on-target non-drug 1/2/3-sisterless w/ timed congression","test":"Mann-Whitney latest-f lag vs no-lag"})

# ---- Plot 2: latest congression TIME (min from meta) vs n_lagging_kinetochores ----
pts=[x for x in rows if x["nlag"] is not None]
if len(pts)>=4:
    fig,ax=plt.subplots(figsize=(6.8,5.2))
    xs=np.array([x["latest_min"] for x in pts]); ys=np.array([x["nlag"] for x in pts])
    for x in pts:
        jit=(np.random.RandomState(abs(hash(x["batch"]))%2**31).rand()-0.5)*0.18
        ax.scatter(x["latest_min"],x["nlag"]+jit,color=GC.get(x["group"],"#888"),s=48,alpha=.85,edgecolor="w",lw=.5,zorder=3)
    m,b0=np.polyfit(xs,ys,1); xr=np.array([xs.min(),xs.max()]); ax.plot(xr,m*xr+b0,"k--",lw=1.4,alpha=.7)
    rho,p=stats.spearmanr(xs,ys)
    ax.text(.03,.97,f"N={len(pts)}\nSpearman rho={rho:.2f}, p={p:.2g}",transform=ax.transAxes,va="top",fontsize=9,bbox=dict(boxstyle="round",fc="white",ec=".6"))
    for g in ("1","2","3"): ax.scatter([],[],color=GC[g],label=f"{g}-sisterless")
    ax.set_xlabel("Latest sisterless-KT congression (min from metaphase onset)")
    ax.set_ylabel("# lagging kinetochores (annotation)"); ax.set_yticks([0,1,2,3])
    ax.set_title("Later congression vs number of lagging KTs"); ax.legend(fontsize=8)
    save(fig,"G4_lagging_count_vs_congression_time","Later congression vs # lagging KTs",
         ["batch","group","latest_congress_min","n_lagging"],
         [[x["batch"],x["group"],round(x["latest_min"],2),x["nlag"]] for x in pts],
         {"cohort":"same, with n_lagging_kinetochores present","test":"Spearman"})
else:
    print(f"skip plot2: only {len(pts)} cells have n_lagging_kinetochores")
print("DONE")
