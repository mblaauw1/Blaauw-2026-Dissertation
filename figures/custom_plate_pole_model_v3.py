"""#48 v2 — plate-vs-pole predictive model WITH per-chromosome POSITION, now that triple chromosomes are numbered
(chromo_measure_lines chr_num + length-matched chromo_lines -> pairing lengths). Features: chromosome length,
ablation PHASE, n-sisterless, and per-chromosome POSITION in the cell frame (radial 0=centroid→1=boundary, and
pole-axis |a1| 0=equator→1=pole; from the numbered trace centroid + nearest cell outline). Compares to the
length+phase+n-sis baseline and tests whether position helps + a 1→3 transfer. Run with the sklearn venv.
"""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, json, os, numpy as np, matplotlib.pyplot as plt
from collections import defaultdict
import lib
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import roc_auc_score, roc_curve
OUT="/Volumes/4 MB/ablation_figures_20260625/group3"; SCRIPT=__file__
PDF="/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf"
data,_=lib.load_master(); mr={r["Batch Name"]:r for r in data}
def gv(b,c): return (mr.get(b,{}).get(c,"") or "").strip()
def px(b):
    try: return float(gv(b,'Pixel Size (um)') or 0.062)
    except: return 0.062
def nsis(b):
    v=gv(b,'# Sisterless KTs'); return int(v) if v.isdigit() else None
def phase(b):
    if lib.is_v2_prometaphase(b): return 1   # USER RULE: v2 binning is the standard (2026-07-22 sweep)
    p=gv(b,'Phase of Ablations').lower(); return 1 if p.startswith('promet') else 0 if p.startswith('proph') else None
def cell_frame(poly):
    c=poly.mean(0); _,_,vt=np.linalg.svd(poly-c); d1=vt[0]
    if d1[0]<0 or (d1[0]==0 and d1[1]<0): d1=-d1
    d2=np.array([-d1[1],d1[0]]); e1=np.abs((poly-c)@d1).max() or 1.0; e2=np.abs((poly-c)@d2).max() or 1.0
    return c,d1,d2,e1,e2
_co=list(csv.reader(open("/Volumes/4 MB/annotations/cell_outlines.csv"))); cx={c:i for i,c in enumerate(_co[0])}
outl=defaultdict(dict)
for r in _co[1:]:
    try:
        b=r[cx['batch']].strip(); p=np.array(json.loads(r[cx['points']]),float)
        if len(p)>=6: outl[b][int(r[cx['frame']])]=p
    except: pass
def carry(b,f):
    o=outl.get(b,{})
    if not o: return None
    prev=[k for k in o if k<=f]; return o[max(prev)] if prev else o[min(o)]
# v3: authoritative per-chromosome length + behavior from the CORRECTED consolidated file (fixes the mis-paired
# length<->behavior that the old pairing-notes parser produced, e.g. collagen_31 chr1/chr2 flip).
beh=defaultdict(dict); length=defaultdict(dict)
for r in csv.DictReader(open("/Volumes/4 MB/annotations/CHROMOSOME_MASTER.csv")):
    b=r['batch'].strip(); cn=str(r.get('chr_num','')).strip()
    if r.get('behavior','').strip(): beh[b][cn]=r['behavior'].strip()
    if r.get('length_um','').strip():
        try: length[b][cn]=float(r['length_um'])
        except: pass
# numbered positions: chromo_measure_lines + length-matched chromo_lines + single-sisterless single trace
pos=defaultdict(dict)
for r in csv.DictReader(open("/Volumes/4 MB/annotations/chromo_measure_lines.csv")):
    cn=str(r.get('chr_num','')).strip()
    if cn in('1','2','3'):
        try: P=np.array(json.loads(r.get('points','')),float); pos[r['batch'].strip()][cn]=(float(P.mean(0)[0]),float(P.mean(0)[1]),int(float(r.get('frame',0))))
        except: pass
pair=defaultdict(dict)
for r in csv.DictReader(open("/Volumes/4 MB/annotations/CHROMO_LENGTH_BEHAVIOR_PAIRING.csv")):
    b=r['batch'].strip()
    for i in(1,2,3):
        v=(r.get(f'chr{i}_length_um','') or '').strip()
        if v:
            try: pair[b][str(i)]=float(v)
            except: pass
cl=defaultdict(list)
for r in csv.DictReader(open("/Volumes/4 MB/annotations/chromo_lines.csv")):
    b=r['batch'].strip()
    try: P=np.array(json.loads(r.get('points','')),float)
    except: continue
    if len(P)>=2: cl[b].append((float(P.mean(0)[0]),float(P.mean(0)[1]),float(np.sum(np.hypot(np.diff(P[:,0]),np.diff(P[:,1])))*px(b)),int(float(r.get('frame',0)))))
for b in cl:
    if nsis(b)==1 and '1' not in pos.get(b,{}) and cl[b]:   # single: the one trace = chr1
        t=max(cl[b],key=lambda t:t[2]); pos[b]['1']=(t[0],t[1],t[3]); continue
    if pos.get(b) and len(pos[b])>=len(pair.get(b,{})): continue
    if not pair.get(b): continue
    traces=sorted(cl[b],key=lambda t:t[2]); nums=sorted(pair[b],key=lambda k:pair[b][k])
    if len(traces)<len(nums): continue
    okk=True; tmp={}
    for t,cn in zip(traces[:len(nums)],nums):
        if abs(t[2]-pair[b][cn])>0.25*pair[b][cn]+0.5: okk=False; break
        tmp[cn]=(t[0],t[1],t[3])
    if okk:
        for cn,v in tmp.items():
            if cn not in pos[b]: pos[b][cn]=v
import re as _re
_DBL=set(lib.double_chromosome_batches()); _BIG=_re.compile(r'four_abl|max_abl',_re.I)
def _is_meta(b):
    p=gv(b,'Phase of Ablations').lower(); return 'metaphase' in p and 'prometaphase' not in p
rows=[]
for b in mr:
    if gv(b,'On-Target / Off-Target').lower()!='on-target' or lib.is_mad1(b) or lib.is_drug(b) or lib.excluded(b): continue
    # v3 reclassifications: drop metaphase ablations, >3-ablation, and the 2-KT-on-one-chromosome group
    if _is_meta(b) or _BIG.search(b) or b in _DBL or 'single_chromosome' in b.lower(): continue
    N=nsis(b); ph=phase(b)
    if N not in(1,2,3) or ph is None: continue
    for cn in('1','2','3'):
        L=length[b].get(cn); bh=beh[b].get(cn)
        if L is None or bh not in('at_plate','congressed','noncongression'): continue
        rad=pa=np.nan
        pxy=pos[b].get(cn) if pos.get(b) else None
        if pxy and b in outl:
            o=carry(b,pxy[2])
            if o is not None:
                c,d1,d2,e1,e2=cell_frame(o); pt=np.array([pxy[0],pxy[1]]); a1=(pt-c)@d1/e1; a2=(pt-c)@d2/e2
                rad=float(np.hypot(a1,a2)); pa=abs(float(a1))
        rows.append(dict(b=b,N=N,length=L,phase=ph,n23=0 if N==1 else 1,rad=rad,pa=pa,label=1 if bh in('at_plate','congressed') else 0))
wp=sum(1 for r in rows if not np.isnan(r['rad']))
print(f"per-chromosome rows: {len(rows)} (with position: {wp}) | 1-sis={sum(1 for r in rows if r['N']==1)} 3-sis={sum(1 for r in rows if r['N']==3)}")
L=np.array([r['length'] for r in rows]); PH=np.array([r['phase'] for r in rows]); NG=np.array([r['n23'] for r in rows])
RA=np.array([r['rad'] for r in rows]); PA=np.array([r['pa'] for r in rows]); Y=np.array([r['label'] for r in rows])
def cvauc(X,y):
    pipe=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),LogisticRegression(max_iter=1000))
    p=cross_val_predict(pipe,X,y,cv=StratifiedKFold(5,shuffle=True,random_state=0),method='predict_proba')[:,1]
    return roc_auc_score(y,p),p
aucBase,_=cvauc(np.column_stack([L,PH,NG]),Y)
aucPos,pPos=cvauc(np.column_stack([L,PH,NG,RA,PA]),Y)
# within-triple: does position separate plate vs pole?
tri=[i for i,r in enumerate(rows) if r['N']==3 and not np.isnan(r['rad'])]
from scipy import stats
def wtest(idx,feat):
    a=[feat[i] for i in idx if Y[i]==1]; p=[feat[i] for i in idx if Y[i]==0]
    return stats.mannwhitneyu(a,p).pvalue if len(a)>=3 and len(p)>=3 else None
p_rad=wtest(tri,RA); p_pa=wtest(tri,PA); p_len=wtest(tri,L)
# odds ratios
from numpy import exp
Xall=np.column_stack([L,PH,NG,RA,PA]); imp=SimpleImputer(strategy='median').fit_transform(Xall)
sc=StandardScaler().fit(imp); clf=LogisticRegression(max_iter=1000).fit(sc.transform(imp),Y); ORs=np.exp(clf.coef_[0]); feat=["length","phase","n-sis","radial","pole-axis"]

fig,(axA,axB)=plt.subplots(1,2,figsize=(13,5.3))
def roc(y,p,ax,lab,col): fpr,tpr,_=roc_curve(y,p); ax.plot(fpr,tpr,color=col,lw=2,label=lab)
_,pBase=cvauc(np.column_stack([L,PH,NG]),Y)
roc(Y,pBase,axA,f"length+phase+n-sis  AUC={aucBase:.2f}","#888")
roc(Y,pPos,axA,f"+ per-chromosome POSITION  AUC={aucPos:.2f}","#2166ac")
axA.plot([0,1],[0,1],'--',color='#bbb'); axA.set_xlabel("FPR"); axA.set_ylabel("TPR")
axA.set_title(f"Does position help? (N={len(rows)} chromosomes, {wp} with position)",fontsize=10); axA.legend(fontsize=8,loc="lower right")
order=np.argsort(ORs); axB.barh(range(len(feat)),[ORs[i] for i in order],color=["#b2182b" if ORs[i]>1 else "#2166ac" for i in order])
axB.axvline(1,color="#222"); axB.set_yticks(range(len(feat))); axB.set_yticklabels([feat[i] for i in order])
for i,o in enumerate(order): axB.text(ORs[o],i,f" {ORs[o]:.2f}×",va="center",fontsize=9)
axB.set_xlabel("odds ratio for reaching PLATE (per +1 SD)")
_rp = f"{p_rad:.2g}" if p_rad is not None else "n/a"; _pp = f"{p_pa:.2g}" if p_pa is not None else "n/a"
axB.set_title(f"Within triples: radial p={_rp}, pole-axis p={_pp}",fontsize=10)
fig.suptitle(f"#48v3  Plate-vs-pole model + per-chromosome position — triples now numbered (length-matched)",fontweight="bold",fontsize=11,x=.01,ha="left")
plt.tight_layout(rect=[0,0,1,0.95]); plt.savefig(f"{OUT}/G3_plate_pole_model_v3.png",bbox_inches="tight",dpi=130); plt.savefig(f"{PDF}/G3_plate_pole_model_v3.pdf",bbox_inches="tight"); plt.close()
lib.record_plot("G3_plate_pole_model_v3",["length","phase","n_sis","radial","pole_axis","label"],[],{"AUC_base":round(aucBase,3),"AUC_pos":round(aucPos,3),"N":len(rows),"N_pos":wp},SCRIPT,"Plate/pole model v2 with position", fig=fig)
print(f"baseline AUC={aucBase:.3f} | +position AUC={aucPos:.3f}")
print(f"within-triple: radial p={p_rad} | pole-axis p={p_pa} | length p={p_len}")
print("odds ratios:", {f:round(o,2) for f,o in zip(feat,ORs)})
