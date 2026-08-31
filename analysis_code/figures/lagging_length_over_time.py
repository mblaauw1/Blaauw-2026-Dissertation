"""Lagging vs control kinetochore LENGTH over time (USER 2026-07-17).
Manual cross marks live in annotations/lagging_lengths.csv (type lagging_length/lagging_width), phase=mon.
Rules (user): marks come in crosses (2 line-marks per kinetochore, a long + short axis). Per cross the
LENGTH = the longer of its two marks (max caliper extent). Per frame:
  1 cross  -> lagging (control not visible)
  2 crosses-> longest = lagging, shorter = control
  3 crosses-> two longest = lagging, shortest = control
Plot length (um) vs time (min from each cell's first lagging observation): lagging (red) vs control (blue)."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, json, os, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from collections import defaultdict
import lib
try: lib.apply_style()
except Exception: pass
PX=0.062
rows=[r for r in csv.DictReader(open("/Volumes/4 MB/annotations/lagging_lengths.csv")) if "lag" in (r.get("type") or "").lower()]
def extent_um(pts):
    p=np.array(pts,float)
    if len(p)<2: return 0.0
    # max pairwise (caliper) distance
    d=0.0
    # cheap: max dist from each point to farthest — O(n^2) ok for small n
    for i in range(len(p)):
        dd=np.hypot(p[:,0]-p[i,0],p[:,1]-p[i,1]).max()
        if dd>d: d=dd
    return d*PX
def centroid(pts):
    p=np.array(pts,float); return p.mean(axis=0)
def pair_marks(marks):
    """Greedy nearest-centroid pairing of marks into crosses. Returns list of crosses (each=list of marks)."""
    cs=[centroid(m['pts']) for m in marks]
    used=set(); crosses=[]
    order=[]
    for i in range(len(marks)):
        for j in range(i+1,len(marks)):
            order.append((np.hypot(*(cs[i]-cs[j])),i,j))
    order.sort()
    for d,i,j in order:
        if i in used or j in used: continue
        used.add(i); used.add(j); crosses.append([marks[i],marks[j]])
    for i in range(len(marks)):
        if i not in used: crosses.append([marks[i]])   # leftover singleton
    return crosses

# group by cell -> frame
by=defaultdict(lambda: defaultdict(list))
for r in rows:
    b=(r.get("batch") or "").strip()
    # USER 2026-08-10: standing cohort exclusion (prophase / drug / metaphase-abl / 4-sis / Mad1).
    if lib.plot_excluded(b) or lib.is_mad1(b): continue
    try: pts=json.loads(r["points"])
    except Exception: continue
    fr=r.get("frame"); ts=float(r.get("t_sec") or 0)
    by[b][fr].append({"pts":pts,"t":ts})

records=[]   # (cell, t_sec, role, length_um)
xcount=defaultdict(int)
for cell in by:
    for fr,marks in by[cell].items():
        crosses=pair_marks(marks)
        xcount[len(crosses)]+=1
        lens=[max(extent_um(m['pts']) for m in cr) for cr in crosses]
        t=marks[0]['t']
        idx=sorted(range(len(lens)),key=lambda k:-lens[k])   # longest first
        if len(lens)==1:
            records.append((cell,t,"lagging",lens[0]))
        elif len(lens)==2:
            records.append((cell,t,"lagging",lens[idx[0]])); records.append((cell,t,"control",lens[idx[1]]))
        else:  # 3+ : all but shortest = lagging, shortest = control
            for k in idx[:-1]: records.append((cell,t,"lagging",lens[k]))
            records.append((cell,t,"control",lens[idx[-1]]))
print("crosses-per-frame distribution:",dict(xcount))
print("total records:",len(records),"| cells:",len(by))

# plot: per cell, per role -> length vs (t - cell's first t) in min
fig,ax=plt.subplots(figsize=(8.4,5.6))
cells=sorted(by)
t0={c:min(r[1] for r in records if r[0]==c) for c in cells}
COL={"lagging":"#d62728","control":"#1f77b4"}
for cell in cells:
    for role in ("lagging","control"):
        pr=sorted([(r[1],r[3]) for r in records if r[0]==cell and r[2]==role])
        if not pr: continue
        # a frame may contribute 2 lagging (3-cross); group by time, keep each as separate handled below
        xs=[(t-t0[cell])/60.0 for t,_ in pr]; ys=[v for _,v in pr]
        ax.plot(xs,ys,color=COL[role],alpha=.5,lw=1.3,marker="o",ms=3,
                label=None)
# legend proxies + counts
nlag=len(set((r[0],r[2]) for r in records if r[2]=="lagging"))
nctl=len(set((r[0]) for r in records if r[2]=="control"))
ax.plot([],[],color=COL["lagging"],lw=2,marker="o",ms=4,label=f"Lagging KT (n={sum(1 for r in records if r[2]=='lagging')} obs)")
ax.plot([],[],color=COL["control"],lw=2,marker="o",ms=4,label=f"Control KT (n={sum(1 for r in records if r[2]=='control')} obs)")
ax.set_xlabel("Time from first lagging observation (min)")
ax.set_ylabel("Kinetochore length (µm, longer cross axis)")
ax.set_title(f"Lagging vs control kinetochore length over time\n({len(cells)} cells; per cross length = longer of its two marks)")
ax.legend(loc="best",fontsize=9); ax.set_ylim(bottom=0)
fig.tight_layout()
OUTD="/Volumes/4 MB/ablation_figures_20260625/custom_collagen_vs_triple"; os.makedirs(os.path.join(OUTD,"illustrator"),exist_ok=True)
nm="G4_lagging_vs_control_length_over_time"
fig.savefig(os.path.join(OUTD,nm+".png"),dpi=150); fig.savefig(os.path.join(OUTD,"illustrator",nm+".svg")); plt.close(fig)
lib.record_plot(nm,["cell","t_sec","role","length_um"],[[c,round(t,2),role,round(v,3)] for c,t,role,v in records],
    {"type":"lagging vs control KT length over time","cells":len(cells),
     "length_rule":"per cross = longer of the two cross marks (max caliper extent x 0.062)",
     "classify":"1cross=lagging;2=longest lagging/other control;3=two longest lagging/shortest control"},
    __file__,"Lagging vs control kinetochore length over time",
    source=["/Volumes/4 MB/annotations/lagging_lengths.csv"])
print("wrote",nm)
PY = None
