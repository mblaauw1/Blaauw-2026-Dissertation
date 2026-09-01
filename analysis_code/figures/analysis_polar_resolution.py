"""2026-07-11 (user): within-cohort comparison — do cells that go into ANAPHASE WITH A POLAR KT differ from
cells that RESOLVE it (congress back to plate)? Same analysis split by LAGGING-chromosome presence. Cohorts:
1-sisterless on-target and 3-sisterless on-target (non-metaphase). Reports N, medians, Mann-Whitney per metric."""
import csv, json, numpy as np
from collections import defaultdict
from scipy import stats
def G(d,c): return (d.get(c,"") or "").strip()
def psec(s):
    s=(s or "").strip().replace(",","")   # strip thousands-commas ("1,223.00")
    if not s: return None
    try: return float(s)
    except: pass
    p=s.split(":")
    try:
        p=[float(x) for x in p]
        return p[0]*3600+p[1]*60+p[2] if len(p)==3 else p[0]*60+p[1] if len(p)==2 else p[0]
    except: return None

rows=list(csv.reader(open("/Volumes/4 MB/ABLATION_MASTER.csv"))); h=rows[1]
data=[dict(zip(h,r)) for r in rows[2:] if any(r)]
mr={d["Batch Name"]:d for d in data}

# ---- per-batch metrics ----
# roundness + area over time from cell_outlines
outl=defaultdict(list)
for r in csv.DictReader(open("/Volumes/4 MB/annotations/cell_outlines.csv")):
    try:
        p=np.array(json.loads(r["points"]),float)
        if len(p)<3: continue
        x,y=p[:,0],p[:,1]; A=0.5*abs(np.dot(x,np.roll(y,-1))-np.dot(y,np.roll(x,-1)))
        per=float(np.sum(np.hypot(np.diff(np.append(x,x[0])),np.diff(np.append(y,y[0])))))
        if per<=0: continue
        circ=min(1.0,4*np.pi*A/per**2)
        outl[r["batch"].strip()].append((psec(r["t_sec"])/60.0, circ, A))
    except: pass
def slope(seq,i):
    s=sorted((t,v[i-1]) for t,*v in [(t,c,a) for t,c,a in seq])  # placeholder
def slopes(b):
    s=sorted(outl.get(b,[]))
    if len(s)<3: return None,None
    t=np.array([x[0] for x in s]); c=np.array([x[1] for x in s]); a=np.array([x[2] for x in s])
    rs=np.polyfit(t,c,1)[0] if np.ptp(t)>0 else None            # roundness change /min
    as_=np.polyfit(t,a/a[0],1)[0] if (np.ptp(t)>0 and a[0]>0) else None  # area (norm to start) change /min
    return rs,as_
# polar speed per batch (from the batch-tagged velocity CSV)
pv=defaultdict(list)
try:
    for r in csv.DictReader(open("/Volumes/4 MB/ablation_plots/data/G4_velocity_paired_comparison.csv")):
        if r.get("kind")=="polar":
            try: pv[r["batch"]].append(float(r["velocity_um_per_min"]))
            except: pass
except FileNotFoundError: pass
# chromosome length per batch (lagging shape)
clen=defaultdict(list)
try:
    for r in csv.DictReader(open("/Volumes/4 MB/ablation_plots/data/G4_lagging_shape.csv")):
        try: clen[r["batch"]].append(float(r["major_axis_um"]))
        except: pass
except FileNotFoundError: pass

def abl_frac(b):
    # ablation-to-metaphase interval (min): time from ablation to metaphase. LARGER = ablation EARLIER (more time
    # before metaphase). (NEB->Meta prometaphase-duration is only 27/156-filled, too sparse to normalize into a
    # true fraction, so use the raw interval, filled 101/156.) First Ablation (s) is a Unix timestamp; Ablation->
    # Meta is the same-clock precomputed interval.
    am=psec(G(mr[b],"Ablation->Meta (s)"))
    return am/60.0 if am is not None else None

def metrics(b):
    rs,as_=slopes(b)
    return dict(abl_frac=abl_frac(b),
               round_slope=rs, area_slope=as_,
               polar_speed=(np.mean(np.abs(pv[b])) if pv.get(b) else None),
               polar_speed_signed=(np.median(pv[b]) if pv.get(b) else None),
               chrom_len=(np.mean(clen[b]) if clen.get(b) else None))

def mw(a,b):
    a=[x for x in a if x is not None]; b=[x for x in b if x is not None]
    if len(a)<3 or len(b)<3: return None
    try: return stats.mannwhitneyu(a,b).pvalue
    except: return None
def med(xs):
    xs=[x for x in xs if x is not None]; return np.median(xs) if xs else None

METRICS=[("abl_frac","abl->metaphase interval min (HIGHER = ablation EARLIER)"),
         ("round_slope","roundness change /min (+ = rounding up)"),
         ("area_slope","area change /min (norm to start)"),
         ("polar_speed","polar KT |speed| µm/min"),
         ("polar_speed_signed","polar KT signed median (+ away from plate)"),
         ("chrom_len","targeted-chromosome major axis µm")]

def run_split(cohort_sis, split_col, posval, negval, poslab, neglab):
    grp=[b for b,d in mr.items() if G(d,"On-Target / Off-Target")=="On-target"
         and G(d,"# Sisterless KTs")==cohort_sis and not lib.is_metaphase_ablation(b) and not lib.is_four_sisterless(b)]
    def val(b):
        v=G(mr[b],split_col).lower()
        if v in posval: return "pos"
        if v in negval: return "neg"
        return None
    pos=[b for b in grp if val(b)=="pos"]; neg=[b for b in grp if val(b)=="neg"]
    print(f"\n{'='*78}\n{cohort_sis}-SISTERLESS on-target — split by {split_col}: {poslab} (N={len(pos)}) vs {neglab} (N={len(neg)})")
    M={b:metrics(b) for b in grp}
    for key,desc in METRICS:
        pv_=[M[b][key] for b in pos]; nv_=[M[b][key] for b in neg]
        p=mw(pv_,nv_); n1=sum(x is not None for x in pv_); n2=sum(x is not None for x in nv_)
        mp=med(pv_); mn=med(nv_)
        star=" *" if (p is not None and p<0.05) else ""
        print(f"  {desc:52s} {poslab}:{('%.3g'%mp) if mp is not None else '-':>8}(n{n1:2d})  {neglab}:{('%.3g'%mn) if mn is not None else '-':>8}(n{n2:2d})  MW p={('%.2g'%p) if p else 'n/a'}{star}")

for sis in ("1","3"):
    # Split A: polar resolution — Polar Chromosomes Yes (unresolved) vs No (resolved)
    run_split(sis,"Polar Chromosomes",{"yes"},{"no"},"UNRESOLVED(polar)","RESOLVED")
    # Split B: lagging present vs absent
    run_split(sis,"Lagging Chromosomes",{"yes"},{"no"},"LAGGING","noLAG")
print("\n(* = Mann-Whitney p<0.05; small N — treat as exploratory)")
