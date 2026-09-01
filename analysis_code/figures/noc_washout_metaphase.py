"""Noc-washout metaphase duration by # sisterless kinetochores created (20251102 + 20251104).
Sources: annotations/NOC_WASHOUT_20251102_TIMES.tsv (time-to-anaphase, from the 11/17/25 lab-meeting sheet — the
short-time / spindle-competent cells give metaphase duration directly) + annotations/NOC_WASHOUT_METAPHASE_LINKED.csv
(20251104 metaphase->anaphase, already a clean metaphase duration). Journal-violin style, matches the deck.
USER-DIRECTED curation (2026-07-21): 4-ablation reclassified as 3; drop lowest-3 control; drop highest-4 of group3;
2-ablation group excluded; only short-time (0<t<45min) valid 20251102 cells (no spindle-reformation subtraction)."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, re, lib, numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
OUT="/Volumes/4 MB/ablation_figures_20260625/group2"; PDF="/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf"; SCRIPT=__file__
def sec(h):
    h=str(h).replace("\\","").strip(); neg=h.startswith("-"); h=h.lstrip("-").strip()
    p=[int(x) for x in h.split(":")];
    while len(p)<3: p=[0]+p
    s=p[0]*3600+p[1]*60+p[2]; return -s if neg else s
def nsis_from(l):
    l=l.lower()
    for w,n in [("four",4),("three",3),("one",1),("two",2)]:
        if w in l: return n
    m=re.search(r"(\d+)\s*abl",l); return int(m.group(1)) if m else 0
def bucket(typ,n): return 0 if typ=="control" else (3 if n>=4 else n)   # control=0; 4-abl -> 3
data=[[],[],[],[]]
for r in csv.DictReader(open("/Volumes/4 MB/annotations/NOC_WASHOUT_20251102_TIMES.tsv"),delimiter="\t"):
    tta=(r.get("time_to_anaphase","") or "").strip()
    if not tta: continue
    mm=sec(tta)/60.0; note=(r.get("notes","") or "").lower()
    if not(0<mm<45) or "dead" in note or "anaphase before" in note or "before noc" in note: continue  # spindle-competent short-time cells
    typ="on-target" if "on-target" in r["batch"] else "control"
    m=re.search(r"(\d+)abl",r["batch"]); b=bucket(typ,int(m.group(1)) if m else 0)
    if 0<=b<=3: data[b].append(mm)
for r in csv.DictReader(open("/Volumes/4 MB/annotations/NOC_WASHOUT_METAPHASE_LINKED.csv")):
    try: mm=float(r.get("meta_dur_min") or 0)
    except: mm=0
    if mm<=0: continue
    lab=r.get("label",""); typ="control" if "control" in lab.lower() else "on-target"
    b=bucket(typ,nsis_from(lab))
    if 0<=b<=3: data[b].append(mm)
data[0]=sorted(data[0])[3:]      # drop lowest-3 control (user 2026-07-21)
data[3]=sorted(data[3])[:-4]     # drop highest-4 of group3 (user 2026-07-21)
show=[(0,"control","#888"),(1,"1","#4a90e2"),(3,"3","#b2182b")]   # 2-ablation group excluded (user)
fig,ax=plt.subplots(figsize=(6.2,5.4))
recrows=[]
for xi,(gi,lab,c) in enumerate(show,start=1):
    v=data[gi]
    if not v: continue
    lib.journal_violin(ax,v,xi,c,width=0.8,min_n=6,alpha=.28)
    jit=(np.random.RandomState(gi).rand(len(v))-.5)*.30
    ax.scatter(np.full(len(v),xi)+jit,v,s=32,color=c,alpha=.8,edgecolor="white",lw=.4,zorder=3)
    med=float(np.median(v)); ax.plot([xi-.22,xi+.22],[med,med],color="#111",lw=2.2,zorder=4)
    ax.text(xi,med,f"  {med:.0f}m\n  n={len(v)}",va="center",ha="left",fontsize=9,color=c)
    for val in v: recrows.append([lab,round(val,2)])
ax.set_xticks(range(1,len(show)+1)); ax.set_xticklabels([s[1] for s in show],fontsize=10)
ax.set_xlabel("# sisterless kinetochores created"); ax.set_ylabel("metaphase duration (min)"); ax.set_ylim(bottom=0)
ax.set_title("Noc-washout metaphase duration by # sisterless KTs\n(20251102 + 20251104; curated)",fontsize=11)
plt.tight_layout()
plt.savefig(f"{OUT}/G2_noc_washout_metaphase_by_sisterless.png",bbox_inches="tight",dpi=140)
plt.savefig(f"{PDF}/G2_noc_washout_metaphase_by_sisterless.pdf",bbox_inches="tight"); plt.close()
lib.record_plot("G2_noc_washout_metaphase_by_sisterless",["group","metaphase_min"],recrows,
    {"source":"NOC_WASHOUT_20251102_TIMES.tsv + NOC_WASHOUT_METAPHASE_LINKED.csv",
     "medians":{lab:round(float(np.median(data[gi])),1) for gi,lab,_ in show if data[gi]},
     "n":{lab:len(data[gi]) for gi,lab,_ in show}},SCRIPT,"Noc-washout metaphase duration by # sisterless KTs (curated)",
    source=["/Volumes/4 MB/annotations/NOC_WASHOUT_20251102_TIMES.tsv","/Volumes/4 MB/annotations/NOC_WASHOUT_METAPHASE_LINKED.csv"],key_column=None)
print("built G2_noc_washout_metaphase_by_sisterless | "+" ".join(f"{lab}:n{len(data[gi])} med{np.median(data[gi]):.0f}m" for gi,lab,_ in show if data[gi]))
