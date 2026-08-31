"""Sisterless-KT CONGRESSION SCORE vs metaphase duration (USER 2026-07-19).
Idea: score each cell by how well its sisterless KT(s) resolve. Per-KT points:
  - at-plate the entire time      -> P_ATPLATE (default 1.0)  [never left]
  - congresses to plate at frac f -> P_POLAR + (P_CONGRESS_MAX-P_POLAR)*(1-f)   [spectrum]
        f = fraction of METAPHASE elapsed at congression = (t_join - meta)/(ana - meta), clamped [0,1]
        (join at metaphase onset f=0 -> full points; join right before anaphase f=1 -> ~pole points)
  - pole the entire time          -> P_POLAR (default 0.0)    [never joined]
Cell score = MEAN over its sisterless KTs (0..1 competence) and SUM (total points). Correlate with
metaphase duration; hypothesis = lower score (polar / late congression) -> LONGER metaphase.
Reuses the exact cohort + prose/structured parsing from sisterless_behavior_vs_duration.py."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, re, os, numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
import lib
try: lib.apply_style()
except Exception: pass

# ---- tunable point values (user can adjust) ----
P_ATPLATE     = 1.0    # at the plate the entire time
P_POLAR       = 0.0    # polar the entire time (never joined)
P_CONGRESS_MAX= 1.0    # points for congressing exactly at metaphase onset (f=0); decays to P_POLAR at f=1
F_UNKNOWN     = 0.5    # assumed fraction when a congression has no recorded time (prose)

def tmin(s):
    s=(s or "").strip()
    if not s: return None
    p=s.split(":")
    try: return (int(p[0])*3600+int(p[1])*60+int(float(p[2])))/60.0 if len(p)==3 else int(p[0])+int(p[1])/60.0
    except: return None

data,_=lib.load_master_plots()
def ok(r):
    b=r["Batch Name"]
    return (r.get("# Sisterless KTs","") in ("1","2","3") and "on-target" in (r.get("On-Target / Off-Target","").lower())
            and not lib.is_drug(b) and "collagen" not in b.lower() and not lib.is_mad1(b)
            and r.get("Exclude") not in ("Yes","yes") and not lib.excluded(b))
_DBL=lib.double_chromosome_batches()   # both KTs on one chromosome -> no sisterless; never in this analysis
sel=[r for r in data if ok(r) and r["Batch Name"] not in _DBL]
pj={r["batch"].strip():r for r in csv.DictReader(open("/Volumes/4 MB/annotations/SISTERLESS_PLATE_JOIN_TIMES.csv"))
    if (r.get("exclude_this_data") or "").lower()!="yes"}

def parse_structured(r):
    beh=[]
    for k in ("chromosome_1_plate_join","chromosome_2_plate_join","chromosome_3_plate_join"):
        v=(r.get(k) or "").strip().lower()
        if not v or v=="n/a": continue
        if v=="anaphase": beh.append(("polar",None))
        elif v=="0" or v=="0:00:00": beh.append(("atplate",0.0))
        elif re.match(r"\d+:\d+",v): beh.append(("congress",tmin(v)))
    return beh
def parse_prose(text,n):
    t=" "+text.lower()+" "
    times=[]
    for m in re.finditer(r'(?:move[sd]?|moving|congress\w*|converg\w*|join\w*|disappear\w*|align\w*|reach\w*)[^.|]{0,45}?plate[^.|]{0,25}?(\d{1,2}:\d{2}(?::\d{2})?)',t): times.append(tmin(m.group(1)))
    for m in re.finditer(r'converg\w*[^.|]{0,15}?(?:at\s*)?(\d{1,2}:\d{2}(?::\d{2})?)',t): times.append(tmin(m.group(1)))
    for m in re.finditer(r'plate[^.|]{0,8}?at\s*(\d{1,2}:\d{2}(?::\d{2})?)',t): times.append(tmin(m.group(1)))
    if re.search(r'plate|congress|converg',t):
        for m in re.finditer(r'(?:another|second|third|next|then|first)[^.|]{0,22}?(?:at\s*)?(\d{1,2}:\d{2}(?::\d{2})?)',t):
            pre=t[max(0,m.start()-22):m.start()].lower()
            if re.search(r'anaphase|metaphase|nebd|stuck|change|onset|congress\w*\s*$',pre): continue
            times.append(tmin(m.group(1)))
    times=sorted(set(round(x,2) for x in times if x is not None))
    no_time=len(re.findall(r'(?:congress\w*\s+to|movement\s+from\s+pole\s+to|move[sd]?\s+(?:in)?to)\s+(?:the\s*)?(?:metaphase\s*)?plate',t))
    n_cong=len(times)+(1 if (no_time>0 and len(times)==0) else 0)
    n_atpl=len(re.findall(r'never seen|at (?:the )?(?:metaphase )?plate (?:the )?whole time|at (?:the )?(?:metaphase )?plate until anaphase|at (?:the )?(?:metaphase )?plate from (?:the )?(?:start|beginning)',t))
    has_polar=bool(re.search(r'polar|at (?:the )?pole',t))
    n_cong=min(n_cong,n); n_atpl=min(n_atpl,n-n_cong)
    n_polar=max(0,n-n_cong-n_atpl) if has_polar else 0
    beh=[("congress",x) for x in times[:n_cong]]+[("congress",None)]*(n_cong-len(times[:n_cong]))
    beh+=[("atplate",0.0)]*n_atpl+[("polar",None)]*n_polar
    return beh

def kt_score(typ,tm,meta,ana):
    """point value for one sisterless KT."""
    if typ=="atplate": return P_ATPLATE
    if typ=="polar":   return P_POLAR
    # congress: spectrum by fraction of metaphase at join
    if tm is None or meta is None or ana is None or ana<=meta:
        f=F_UNKNOWN
    else:
        f=(tm-meta)/(ana-meta); f=min(1.0,max(0.0,f))
    return P_POLAR+(P_CONGRESS_MAX-P_POLAR)*(1.0-f)

rows=[]
for r in sel:
    b=r["Batch Name"]; n=int(r["# Sisterless KTs"])
    if lib.is_prophase_ablation(b): continue   # prophase excluded (this plot has no prophase group)
    txt=(r.get("Notes","")+" || "+r.get("annotation_notes","")+" || "+r.get("Polar Comments",""))
    if "both kinetochores on one chromosome" in txt.lower() or "[plate-join n/a" in txt.lower(): continue
    meta=tmin(r.get("Metaphase Start (s)","")); ana=tmin(r.get("Anaphase Onset (s)",""))
    mdur,ok2=lib.mitotic_duration_min(r); mdur=mdur if ok2 else None
    metadur=(ana-meta) if (meta is not None and ana is not None) else None
    if b in pj: beh=parse_structured(pj[b]); src="structured"
    else: beh=parse_prose(txt,n); src="prose"
    beh=beh[:n]; full=(len(beh)==n)
    if not full: continue                                   # only fully-described cells get a score
    scores=[kt_score(typ,tm,meta,ana) for typ,tm in beh]
    y=metadur if metadur is not None else mdur
    if y is None: continue
    rows.append(dict(batch=b,group=n,src=src,mean=float(np.mean(scores)),summ=float(np.sum(scores)),
                     y=y,beh=beh,scores=scores))
print(f"scored cells: {len(rows)} | structured {sum(1 for r in rows if r['src']=='structured')} | prose {sum(1 for r in rows if r['src']=='prose')}")

OUT="/Volumes/4 MB/ablation_figures_20260625/custom_collagen_vs_triple"; os.makedirs(os.path.join(OUT,"illustrator"),exist_ok=True)
GC={1:"#2e9e3f",2:"#d68f00",3:"#8e44ad"}
MSRC={"structured":dict(marker="o"),"prose":dict(marker="^")}
YL="Metaphase duration (min)"
def save(fig,nm,caption,cols,prov):
    fig.savefig(os.path.join(OUT,nm+".png"),dpi=150,bbox_inches="tight"); fig.savefig(os.path.join(OUT,"illustrator",nm+".svg")); plt.close(fig)
    lib.record_plot(nm,cols,prov,{"cohort":"cdc20 on-target non-drug non-collagen 1/2/3-sisterless (fully-described)",
        "scoring":f"atplate={P_ATPLATE}, polar={P_POLAR}, congress=P_POLAR+({P_CONGRESS_MAX}-P_POLAR)*(1-frac_metaphase)",
        "behavior_source":"SISTERLESS_PLATE_JOIN_TIMES.csv (o) + master Notes prose (^)"},
        __file__,caption,source=["/Volumes/4 MB/ABLATION_MASTER.csv","/Volumes/4 MB/annotations/SISTERLESS_PLATE_JOIN_TIMES.csv"])
    print("wrote",nm)

def scatter_vs_dur(key,nm,xlabel,title,cap):
    fig,ax=plt.subplots(figsize=(7.6,5.4))
    xs=[]; ys=[]
    for r in rows:
        jit=np.random.default_rng(abs(hash(r["batch"]+key))%2**32).uniform(-0.012,0.012)
        ax.scatter(r[key]+jit,r["y"],color=GC[r["group"]],alpha=.82,s=44,edgecolor="w",lw=.5,**MSRC[r["src"]],zorder=3)
        xs.append(r[key]); ys.append(r["y"])
    xs=np.array(xs); ys=np.array(ys)
    if len(xs)>=3:
        m,b=np.polyfit(xs,ys,1); xr=np.array([xs.min(),xs.max()]); ax.plot(xr,m*xr+b,"k--",lw=1.5,alpha=.75)
        rho,p=stats.spearmanr(xs,ys); r_,pp=stats.pearsonr(xs,ys)
        ax.text(.03,.97,f"N={len(xs)}\nSpearman rho={rho:.2f}, p={p:.2g}\nPearson r={r_:.2f}, p={pp:.2g}",
                transform=ax.transAxes,va="top",fontsize=9,bbox=dict(boxstyle="round",fc="white",ec=".6"))
    for g in (1,2,3): ax.scatter([],[],color=GC[g],label=f"{g}-sisterless")
    ax.scatter([],[],color="gray",marker="o",label="structured"); ax.scatter([],[],color="gray",marker="^",label="prose (approx)")
    ax.set_xlabel(xlabel); ax.set_ylabel(YL); ax.set_title(title); ax.legend(fontsize=8)
    save(fig,nm,cap,["batch","group","score","metaphase_duration_min","source"],
         [[r["batch"],r["group"],round(r[key],3),round(r["y"],2),r["src"]] for r in rows])

scatter_vs_dur("mean","G4_congression_score_vs_duration",
    "Congression score (mean per sisterless KT, 0=all polar … 1=all at-plate)",
    f"Cell congression score vs metaphase duration\n(per-KT: at-plate={P_ATPLATE}, polar={P_POLAR}, congress=(1-frac metaphase))",
    "Mean-per-KT congression score vs metaphase duration")
scatter_vs_dur("summ","G4_congression_score_sum_vs_duration",
    "Congression score (SUM over sisterless KTs = total competence points)",
    f"Cell congression score (sum) vs metaphase duration",
    "Summed congression score vs metaphase duration")

# ranked bar: per-cell score, colored by group, to eyeball the spectrum
rows_s=sorted(rows,key=lambda r:r["mean"])
fig,ax=plt.subplots(figsize=(8.8,max(4,len(rows_s)*0.13)))
ax.barh(range(len(rows_s)),[r["mean"] for r in rows_s],color=[GC[r["group"]] for r in rows_s],alpha=.85)
ax.set_yticks([]); ax.set_xlim(0,1); ax.set_ylim(-0.5,len(rows_s)-0.5); ax.set_xlabel("Congression score (mean per sisterless KT)")
ax.set_ylabel(f"cells sorted by score (N={len(rows_s)})")
from matplotlib.patches import Patch
_leg=[Patch(facecolor=GC[g],label=f"{g}-sisterless") for g in (1,2,3)]
ax.legend(handles=_leg,fontsize=8,loc="lower right")
ax.set_title("Per-cell congression score (1=all KTs at plate early, 0=all polar)"); ax.legend(fontsize=8,loc="lower right")
save(fig,"G4_congression_score_ranked","Per-cell congression score ranked",
     ["batch","group","mean_score","sum_score"],[[r["batch"],r["group"],round(r["mean"],3),round(r["summ"],3)] for r in rows_s])
print("DONE")
