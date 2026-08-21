"""k-k distance vs time-from-metaphase (metaphase window), per-pair traces + per-group mean+/-SD trendline.
Same curated sister pairs (via pair tags) and window as the refined oscillation analysis."""
import sys, csv, re, json, collections; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import lib
ANN="/Volumes/4 MB/annotations"; PX=0.062
data,_=lib.load_master(); mrow={r["Batch Name"]:r for r in data}
def tag(n,k): m=re.search(rf"{k}:([^;]*)",n or ""); return m.group(1) if m else ""
def absnum(b): return (mrow.get(b,{}).get("# Sisterless KTs","") or "").strip()
def hms2s(s):
    s=(s or "").strip(); neg=s.startswith("-"); s=s.lstrip("-")
    if not s: return None
    p=[float(x) for x in s.split(":")]; v=p[0]*3600+p[1]*60+p[2] if len(p)==3 else (p[0]*60+p[1] if len(p)==2 else p[0])
    return -v if neg else v
def cen(p): a=np.array(p,float); return np.array([a[:,0].mean(),a[:,1].mean()])
# SISTERS from KT_SISTERS_20260723.csv (manual > proximity); GEOMETRY from the tracked objects.
SIS={}
for r in csv.DictReader(open(f"{ANN}/KT_SISTERS_20260723.csv")):
    if r["sister_pair_id"]: SIS[r["track_id"]]=r["sister_pair_id"]
outs=collections.defaultdict(list)
for r in csv.DictReader(open(f"{ANN}/KT_OUTLINE_TRACKS_20260723.csv")):
    if r["label"]!="paired" or not r["t_sec"] or not r["frame"].isdigit(): continue
    if r["track_id"] not in SIS: continue
    outs[r["batch"]].append(dict(frame=int(r["frame"]),t=float(r["t_sec"]),grp=r["track_id"],
        pair=SIS[r["track_id"]],c=np.array([float(r["cx_px"]),float(r["cy_px"])])))

# build per-pair (t_from_meta, kk) series in metaphase window
series=[]  # (cohort, cell, pair, [(tmin,kk),...])
for b,rs in outs.items():
    a=absnum(b); cohort="2/3" if a in ("2","3") else ("single" if a=="1" else None)
    if cohort is None: continue
    ms=hms2s(mrow.get(b,{}).get("Metaphase Start (s)")); ana=hms2s(mrow.get(b,{}).get("Anaphase Onset (s)"))
    if ms is None or ana is None: continue
    byp=collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(list)))
    for r in rs: byp[r["pair"]][r["frame"]][r["grp"]].append(r["c"])
    for pid,frs in byp.items():
        ft={r["frame"]:r["t"] for r in rs}
        pts=[]
        for f,gd in frs.items():
            t=ft.get(f)
            if t is None or not (ms<=t<=ana): continue
            cents=[np.mean(v,axis=0) for v in gd.values()]
            if len(cents)>=2:
                kk=np.hypot(*(cents[0]-cents[1]))*PX; pts.append(((t-ms)/60.0,kk))
        if len(pts)>=4: series.append((cohort,b,pid,sorted(pts)))

COL={"single":"#2a7fff","2/3":"#ff5a3c"}
fig,ax=plt.subplots(figsize=(11,7))
ncount={"single":0,"2/3":0}
allpts={"single":[],"2/3":[]}
for cohort,cell,pid,pts in series:
    ncount[cohort]+=1; x,y=zip(*pts); ax.plot(x,y,c=COL[cohort],alpha=.3,lw=1); allpts[cohort]+=pts
for co in ["single","2/3"]:
    if not allpts[co]: continue
    x=np.array([p[0] for p in allpts[co]]); y=np.array([p[1] for p in allpts[co]])
    bins=np.arange(0,np.ceil(x.max())+2,2); idx=np.digitize(x,bins); mx=[];md=[];sd=[]
    for bi in range(1,len(bins)):
        yy=y[idx==bi]
        if len(yy)>=3: mx.append(bins[bi-1]+1); md.append(yy.mean()); sd.append(yy.std())
    if mx:
        mx,md,sd=map(np.array,(mx,md,sd)); ax.plot(mx,md,c=COL[co],lw=3,zorder=6)
        ax.fill_between(mx,md-sd,md+sd,color=COL[co],alpha=.15,zorder=1)
from matplotlib.lines import Line2D
ax.legend([Line2D([],[],c=COL['single'],lw=3),Line2D([],[],c=COL['2/3'],lw=3)],
          [f"single (n={ncount['single']})",f"2/3 (n={ncount['2/3']})"])
ax.set_xlabel("time from metaphase start (min)"); ax.set_ylabel("k-k distance (um)")
ax.set_title("Sister k-k distance vs time from metaphase (metaphase window)\neach line = one pair; bold = per-group mean +/- SD")
ax.grid(alpha=.3)
# Register the plotted data - see the note in kk_osc_refined.py (2026-07-29).
try:
    _hdr=["cell","pair","cohort","t_min_from_meta","kk_um"]
    _rows=[]
    for _co,_cell,_pid,_pts in series:
        for _t,_kk in _pts:
            _rows.append([_cell,_pid,_co,round(_t,3),round(_kk,4)])
    lib.record_plot("kk_vs_time", _hdr, _rows,
                    {"type":"sister k-k distance vs time from metaphase onset",
                     "window":"metaphase","x":"t_min_from_meta","y":"kk_um"},
                    __file__,
                    "Sister k-k distance over the metaphase window, per sister pair, single vs 2/3 "
                    "ablation. Pairs from KT_SISTERS, geometry from KT_OUTLINE_TRACKS - her MANUAL outlines.",
                    source=["/Volumes/4 MB/annotations/KT_SISTERS_20260723.csv",
                            "/Volumes/4 MB/annotations/KT_OUTLINE_TRACKS_20260723.csv"],
                    key_column="cell")
except Exception as _e:
    print("record_plot(kk_vs_time) skipped: %s" % _e)
plt.tight_layout(); plt.savefig("/Volumes/4 MB/_scratch/kk_vs_time.png",dpi=130)
plt.savefig("/Volumes/4 MB/_scratch/kk_vs_time.png".replace(".png",".pdf"))
print(f"wrote /Volumes/4 MB/_scratch/kk_vs_time.png  (single {ncount['single']}, 2/3 {ncount['2/3']} pairs)")
