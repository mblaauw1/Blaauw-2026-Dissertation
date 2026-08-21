"""2026-07-11 (user): actually compute polar-KT SPEED + chromosome LENGTH for the cells that HAVE manual polar
markings (kt_points polar/sisterless), + paired_kt plate control. Split by polar resolution + lagging. Small N —
report PER CELL so the actual cells are visible, plus group medians / MW where N>=3."""
import csv, json, numpy as np
from collections import defaultdict
from scipy import stats
def Gc(d,c): return (d.get(c,"") or "").strip()
rows=list(csv.reader(open("/Volumes/4 MB/ABLATION_MASTER.csv"))); h=rows[1]
data=[dict(zip(h,r)) for r in rows[2:] if any(r)]
mr={d["Batch Name"]:d for d in data}
def pxs(b):
    try: return float(Gc(mr.get(b,{}),"Pixel Size (um)"))
    except: return 0.062

# manual KT tracks
trk=defaultdict(lambda: defaultdict(list))
for r in csv.DictReader(open("/Volumes/4 MB/annotations/kt_points.csv")):
    lab=r["label"].strip()
    if lab in ("polar","sisterless","paired_kt"):
        try: trk[r["batch"].strip()][lab].append((float(r["t_sec"]),float(r["x"]),float(r["y"])))
        except: pass
def track(b):
    a=trk[b].get("polar",[]); c=trk[b].get("sisterless",[])
    return sorted(a if len(a)>=len(c) else c)
def speed2d(seq,px):
    """mean 2D speed µm/min from consecutive marks (dt>0)."""
    seq=sorted(seq); v=[]
    for (t0,x0,y0),(t1,x1,y1) in zip(seq,seq[1:]):
        if t1>t0: v.append(np.hypot(x1-x0,y1-y0)*px/((t1-t0)/60.0))
    return (np.median(v), len(v)) if v else (None,0)
# metaphase plates -> distance-to-plate over time (for congression pattern)
plates=defaultdict(dict)
for r in csv.DictReader(open("/Volumes/4 MB/annotations/meta_plates.csv")):
    try: plates[r["batch"].strip()][round(float(r["t_sec"]),1)]=np.array(json.loads(r["points"]),float)
    except: pass
def pt_line(p,poly):
    if len(poly)<2: return None
    d=[]
    for i in range(len(poly)-1):
        a,b=poly[i],poly[i+1]; ab=b-a; t=np.clip(np.dot(p-a,ab)/max(1e-9,np.dot(ab,ab)),0,1)
        d.append(np.hypot(*(p-(a+t*ab))))
    return min(d)
def dist_series(b,px):
    pm=plates.get(b);
    if not pm: return []
    pk=sorted(pm); out=[]
    for t,x,y in track(b):
        k=min(pk,key=lambda z:abs(z-t)); d=pt_line(np.array([x,y]),pm[k])
        if d is not None: out.append((t/60.0,d*px))
    return sorted(out)
# chromosome length (lagging shape major axis)
clen=defaultdict(list)
try:
    for r in csv.DictReader(open("/Volumes/4 MB/ablation_plots/data/G4_lagging_shape.csv")):
        try: clen[r["batch"]].append(float(r["major_axis_um"]))
        except: pass
except FileNotFoundError: pass

def resolution(b):
    v=Gc(mr.get(b,{}),"Polar Chromosomes").lower()
    return "UNRES" if v=="yes" else "RES" if v=="no" else "?"
def lagging(b):
    v=Gc(mr.get(b,{}),"Lagging Chromosomes").lower()
    return "LAG" if v=="yes" else "noLAG" if v=="no" else "?"
def cohort(b):
    d=mr.get(b,{}); return Gc(d,"# Sisterless KTs") if Gc(d,"On-Target / Off-Target")=="On-target" else None

# per-cell table for cells WITH a polar track
cells=[b for b in trk if len(track(b))>=3 and cohort(b) in ("1","3")]
print(f"cells with polar/sisterless track >=3 marks in on-target 1/3-sis: {len(cells)}\n")
print(f"{'batch':40s} {'sis':3s} {'res':6s} {'lag':6s} {'polarSpd':8s} {'pairSpd':8s} {'chrLen':7s} {'distDrop':8s}")
recs=[]
for b in sorted(cells):
    px=pxs(b); ps_,n1=speed2d(track(b),px); pp_,n2=speed2d(trk[b].get("paired_kt",[]),px)
    cl=np.mean(clen[b]) if clen.get(b) else None
    ds=dist_series(b,px); drop=(ds[0][1]-min(d for _,d in ds)) if len(ds)>=2 else None  # how far it moved toward plate
    recs.append(dict(b=b,sis=cohort(b),res=resolution(b),lag=lagging(b),spd=ps_,pair=pp_,clen=cl,drop=drop))
    def f(x,fmt="%.2f"): return (fmt%x) if x is not None else "-"
    print(f"  {b[:38]:38s} {cohort(b):3s} {resolution(b):6s} {lagging(b):6s} {f(ps_):>8s} {f(pp_):>8s} {f(cl):>7s} {f(drop):>8s}")

def grpcmp(key,label):
    print(f"\n=== {label}: by polar resolution & lagging (median, MW where N>=3) ===")
    for split,pos,neg in [("resolution","UNRES","RES"),("lagging","LAG","noLAG")]:
        for sis in ("1","3"):
            a=[r[key] for r in recs if r["sis"]==sis and r[split[:3] if split=='lagging' else 'res']==pos and r[key] is not None]
            b_=[r[key] for r in recs if r["sis"]==sis and r[split[:3] if split=='lagging' else 'res']==neg and r[key] is not None]
            if not a and not b_: continue
            p=stats.mannwhitneyu(a,b_).pvalue if len(a)>=3 and len(b_)>=3 else None
            ma=np.median(a) if a else None; mb=np.median(b_) if b_ else None
            print(f"  {sis}-sis {pos}:{('%.2f'%ma) if ma is not None else '-':>7}(n{len(a)}) vs {neg}:{('%.2f'%mb) if mb is not None else '-':>7}(n{len(b_)})  p={('%.2g'%p) if p else 'n/a'}")
for key,lab in [("spd","POLAR-KT SPEED µm/min"),("clen","CHROMOSOME LENGTH µm"),("drop","DISTANCE MOVED TOWARD PLATE µm")]:
    grpcmp(key,lab)
