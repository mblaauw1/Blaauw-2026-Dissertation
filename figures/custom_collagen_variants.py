"""Collagen shape (roundness/area, metaphase->anaphase) — EXTRA GROUP VARIANTS (USER 2026-07-17).
Adds two more WITH-vs-WITHOUT-collagen comparisons alongside the on-target-triple one:
  (1) 2-or-3 sisterless ON-target ablations (each group = 2 OR 3 on-target sisterless KTs)
  (2) triple OFF-target ablations
Same computation/style as custom_collagen_vs_triple_shape.py (trend fit to group-mean anaphase,
ANCOVA group x time + per-cell-slope Mann-Whitney)."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import json, csv, os, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from collections import defaultdict
import scipy.stats as _ss
import lib
try: lib.apply_style()
except Exception: pass
data,_=lib.load_master_plots(); mr={r["Batch Name"]:r for r in data}
rows=list(csv.reader(open("/Volumes/4 MB/annotations/cell_outlines.csv"))); ix={c.strip():i for i,c in enumerate(rows[0])}
psize={}
for r in rows[1:]:
    b=r[ix['batch']].strip()
    try: psize[b]=float(r[ix['pixel_size_um']])
    except Exception: psize.setdefault(b,0.062)
OUTD="/Volumes/4 MB/ablation_figures_20260625/custom_collagen_vs_triple"; os.makedirs(os.path.join(OUTD,"illustrator"),exist_ok=True)

def poly_round(pts):
    p=np.array(pts,float)
    if len(p)<3: return None
    x,y=p[:,0],p[:,1]; Ar=0.5*abs(np.dot(x,np.roll(y,-1))-np.dot(y,np.roll(x,-1)))
    per=np.sum(np.hypot(np.diff(np.append(x,x[0])),np.diff(np.append(y,y[0]))))
    if per==0: return None
    r=4*np.pi*Ar/per**2; return r if 0<r<=1.2 else None
def poly_area(pts,pxs):
    p=np.array(pts,float)
    if len(p)<3: return None
    x,y=p[:,0],p[:,1]; Ar=0.5*abs(np.dot(x,np.roll(y,-1))-np.dot(y,np.roll(x,-1)))
    a=Ar*pxs*pxs; return a if 0<a<=5000 else None
def win(b):
    r=mr.get(b,{}); ms=lib.parse_time(r.get("Metaphase Start (s)","") or ""); an=lib.parse_time(r.get("Anaphase Onset (s)","") or "")
    return ms,an
def build_ma(metric,members):
    tr=defaultdict(list)
    for r in rows[1:]:
        b=r[ix['batch']].strip()
        if b not in members: continue
        ms,an=win(b)
        if ms is None or an is None: continue
        try:
            ts=float(r[ix['t_sec']]); pts=json.loads(r[ix['points']])
            if ts<ms-1e-6 or ts>an+1e-6: continue
            v=poly_round(pts) if metric=="round" else poly_area(pts,psize.get(b,0.062))
        except Exception: continue
        if v is None: continue
        tr[b].append(((ts-ms)/60.0,v))
    return tr
def cell_slopes(members,tr):
    out=[]
    for b in members:
        if b not in tr or len(tr[b])<3: continue
        arr=np.array(sorted(tr[b]))
        if np.ptp(arr[:,0])<=0: continue
        out.append(float(np.polyfit(arr[:,0],arr[:,1],1)[0]))
    return out
def ancova(ptsA,ptsB):
    if len(ptsA)<2 or len(ptsB)<2: return None
    X=[];Y=[]
    for (t,v) in ptsA: X.append([1.0,t,1.0,t]); Y.append(v)
    for (t,v) in ptsB: X.append([1.0,t,0.0,0.0]); Y.append(v)
    X=np.array(X);Y=np.array(Y);n=len(Y)
    if n-4<1: return None
    beta,_,_,_=np.linalg.lstsq(X,Y,rcond=None)
    resid=Y-X@beta; rss=float(resid@resid); sigma2=rss/(n-4)
    try: cov=sigma2*np.linalg.inv(X.T@X)
    except np.linalg.LinAlgError: return None
    se3=float(np.sqrt(cov[3,3]))
    if se3==0: return None
    t=float(beta[3])/se3; p=float(2*_ss.t.sf(abs(t),df=n-4))
    return {"diff":float(beta[3]),"p":p}
def _sig(p): return "***" if p<1e-3 else "**" if p<1e-2 else "*" if p<0.05 else "n.s."

def make_plot(A,B,tag,titlelead):
    members=A|B
    for metric in ("round","area"):
        tr=build_ma(metric,members); fig,ax=plt.subplots(figsize=(8.2,5.8)); grp_pts={}
        for grpname,mem,col in (("A",A,"#1f77b4"),("B",B,"#d62728")):
            allpts=[]; durs=[]
            for b in mem:
                if b not in tr: continue
                arr=sorted(tr[b]); allpts+=arr
                ms,an=win(b)
                if ms is not None and an is not None: durs.append((an-ms)/60.0)
                ax.plot([p[0] for p in arr],[p[1] for p in arr],color=col,alpha=.16,lw=1,zorder=1)
                ax.scatter([p[0] for p in arr],[p[1] for p in arr],s=15,color=col,alpha=.30,zorder=2)
            grp_pts[grpname]=allpts
            mean_ana=float(np.mean(durs)) if durs else None
            if len(allpts)>=2:
                arr=np.array(allpts)
                fit=arr[arr[:,0]<=mean_ana] if mean_ana is not None else arr
                if len(fit)<2: fit=arr
                m,c=np.polyfit(fit[:,0],fit[:,1],1)
                xx=np.array([0.0, mean_ana if mean_ana is not None else arr[:,0].max()])
                lab={"A":f"WITH collagen (N={len(A)})","B":f"WITHOUT collagen (N={len(B)})"}[grpname]
                ax.plot(xx,m*xx+c,color=col,lw=3,zorder=5,label=lab+f"  [slope={m:.3g}/min]")
            if durs: ax.axvline(mean_ana,color=col,ls=":",lw=1.1,alpha=.6,zorder=3)
        anc=ancova(grp_pts.get("A",[]),grp_pts.get("B",[])); sA=cell_slopes(A,tr); sB=cell_slopes(B,tr); mw=None
        if len(sA)>=1 and len(sB)>=2:
            try: mw=float(_ss.mannwhitneyu(sA,sB,alternative="two-sided").pvalue)
            except Exception: mw=None
        lines=["Slope difference (with vs without collagen):"]
        if anc: lines.append(f"ANCOVA group×time: p={anc['p']:.3g} {_sig(anc['p'])}")
        if mw is not None: lines.append(f"per-cell slope MWU: p={mw:.3g} {_sig(mw)}  (n={len(sA)} vs {len(sB)})")
        ax.text(0.98,0.98,"\n".join(lines),transform=ax.transAxes,ha="right",va="top",fontsize=8,
                bbox=dict(boxstyle="round",fc="white",ec="0.6"))
        yl="Cell roundness (4πA/P²)" if metric=="round" else "Cross-sectional area (µm²)"
        ax.set_xlabel("Time from metaphase start (min)"); ax.set_ylabel(yl); ax.set_xlim(left=0)
        ax.set_title(f"{titlelead} — WITH vs WITHOUT collagen — {'roundness' if metric=='round' else 'cross-sectional area'}\n"
                     f"(cells: metaphase to anaphase; dotted = group mean anaphase; trend fit ≤ mean anaphase)")
        ax.legend(loc="upper left",fontsize=9); fig.tight_layout()
        nm=f"collagen_vs_triple_{tag}_{'roundness' if metric=='round' else 'area'}_meta_to_ana"
        fig.savefig(os.path.join(OUTD,nm+".png"),dpi=150); fig.savefig(os.path.join(OUTD,"illustrator",nm+".svg")); plt.close(fig)
        prov=[[b,("A" if b in A else "B"),round(t,3),round(v,3)] for b in tr for (t,v) in tr[b]]
        lib.record_plot(nm,["batch","group","time_from_meta_min","value"],prov,
            {"type":"collagen shape meta->ana variant","variant":tag,
             "groupA_WITHcollagen_N":len(A),"groupB_WITHOUTcollagen_N":len(B),"metric":metric},
            __file__,f"{titlelead} — {'roundness' if metric=='round' else 'area'} (with vs without collagen)",
            source=["/Volumes/4 MB/ABLATION_MASTER.csv","/Volumes/4 MB/annotations/cell_outlines.csv"])
        print(f"wrote {nm}  (A={len(A)} B={len(B)})")

def sis(b): return (mr.get(b,{}).get("# Sisterless KTs") or "").strip()
def ont(b): return (mr.get(b,{}).get("On-Target / Off-Target") or "").lower()
def is_meta(b): return (mr.get(b,{}).get("Phase of Ablations") or "").strip().lower()=="metaphase"  # USER 2026-07-17: exclude metaphase ablations
COMMENT_COLLAGEN={"20250918 triple_ablation_15","20250918 triple_ablation_29",
                  "20250925 triple_ablation_7","20250925 triple_ablation_13"}
CC=set(b for b in COMMENT_COLLAGEN if not is_meta(b))

# (1) 2-or-3 sisterless ON-target (metaphase-ablation + double-KT-on-one-chromosome batches excluded)
_DBL=lib.double_chromosome_batches()   # both KTs on one chromosome -> not sisterless
on23=[b for b in mr if sis(b) in ("2","3") and "on-target" in ont(b) and not lib.plot_excluded(b) and not is_meta(b) and b not in _DBL]
A1=set(b for b in on23 if "collagen" in b.lower())|CC
B1=set(b for b in on23 if "collagen" not in b.lower())-CC
make_plot(A1,B1,"2or3_ontarget","On-target 2–3 sisterless ablations")

# (2) triple OFF-target (off-target has no #Sisterless; triple = triple_ablation acquisition; no metaphase)
offtri=[b for b in mr if "off" in ont(b) and "triple_ablation" in b.lower() and not lib.plot_excluded(b) and not is_meta(b)]
A2=set(b for b in offtri if "collagen" in b.lower())
B2=set(b for b in offtri if "collagen" not in b.lower())
make_plot(A2,B2,"offtarget_triple","Triple off-target ablations")
