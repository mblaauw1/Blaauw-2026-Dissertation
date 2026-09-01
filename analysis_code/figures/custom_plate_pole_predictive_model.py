"""#48 — Predictive model: does a sisterless KT localize to the PLATE or stay POLAR?
Label: plate(1) = behavior at_plate OR congressed (reaches the plate by anaphase); pole(0) = noncongression
(still polar at anaphase onset). Per-chromosome, on-target, from the consolidated CHROMOSOME_ANNOTATIONS_MASTER.
Features (transfer across groups): chromosome length (per-chromosome), ablation phase (prophase=0/prometaphase=1),
n-sisterless group (1 vs 2/3 — captures the very different base rates), and (secondary, sparser) the ablation→
metaphase interval. Models: (A) TRANSFER — train on 1-sisterless, predict 2/3 (the user's core ask); (B) COMBINED
— train on 1+2/3 with n-sisterless as a feature, stratified CV. 4-KT stretch is data-blocked (0 annotated).
Run with the sklearn venv:  /Volumes/4 MB/.mlvenv/bin/python custom_plate_pole_predictive_model.py
"""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, os, numpy as np, matplotlib.pyplot as plt
import lib
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import roc_auc_score, roc_curve
OUT="/Volumes/4 MB/ablation_figures_20260625/group3"; os.makedirs(OUT,exist_ok=True); SCRIPT=__file__
PDF="/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf"
data,_=lib.load_master(); mr={r["Batch Name"]:r for r in data}
def gv(b,c): return (mr.get(b,{}).get(c,"") or "").strip()
def nsis(b):
    v=gv(b,'# Sisterless KTs'); return int(v) if v.isdigit() else None
def phase(b):
    if lib.is_v2_prometaphase(b): return 'Prometaphase'   # USER RULE: v2 binning is the standard (2026-07-22 sweep)
    p=gv(b,'Phase of Ablations').lower()
    return 'Prophase' if p.startswith('proph') else 'Prometaphase' if p.startswith('promet') else None
def num(b,c):
    v=gv(b,c)
    try: return float(v)
    except: return lib.parse_time(v)

rows=[]
for r in csv.DictReader(open("/Volumes/4 MB/annotations/CHROMOSOME_MASTER.csv")):
    b=r['batch'].strip()
    if gv(b,'On-Target / Off-Target').lower()!='on-target' or lib.is_mad1(b) or lib.is_drug(b) or lib.excluded(b): continue
    bh=r.get('behavior','').strip(); L=r.get('length_um','').strip()
    if bh not in('at_plate','congressed','noncongression') or not L: continue
    N=nsis(b); ph=phase(b)
    if ph is None or N not in(1,2,3): continue
    am=num(b,'Ablation->Meta (s)')
    rows.append(dict(length=float(L),phase=1 if ph=='Prometaphase' else 0,n23=0 if N==1 else 1,
                     am=(am/60.0 if am is not None else None),label=1 if bh in('at_plate','congressed') else 0))
L=np.array([r['length'] for r in rows]); PH=np.array([r['phase'] for r in rows]); NG=np.array([r['n23'] for r in rows])
Y=np.array([r['label'] for r in rows]); is1=NG==0; is23=NG==1
print(f"N={len(rows)}  (1-sis={is1.sum()} plate%={100*Y[is1].mean():.0f} | 2/3={is23.sum()} plate%={100*Y[is23].mean():.0f})")

def cv_auc(X,y,cv=5):
    pipe=make_pipeline(StandardScaler(),LogisticRegression(max_iter=1000))
    p=cross_val_predict(pipe,X,y,cv=StratifiedKFold(cv,shuffle=True,random_state=0),method='predict_proba')[:,1]
    return roc_auc_score(y,p),p
# ---- Model B: combined, stratified CV ----
Xc=np.column_stack([L,PH,NG]); aucC,pC=cv_auc(Xc,Y)
aucGrp,_=cv_auc(NG.reshape(-1,1),Y)                       # group (base rate) alone
aucLen,_=cv_auc(L.reshape(-1,1),Y)                        # length alone
aucLP,_=cv_auc(np.column_stack([L,PH]),Y)                # length+phase (no group)
# ---- Model A: TRANSFER train 1-sis -> predict 2/3 ----
sc=StandardScaler().fit(np.column_stack([L,PH])[is1])
clf=LogisticRegression(max_iter=1000).fit(sc.transform(np.column_stack([L,PH])[is1]),Y[is1])
p23=clf.predict_proba(sc.transform(np.column_stack([L,PH])[is23]))[:,1]
aucT=roc_auc_score(Y[is23],p23)
cal_pred=p23.mean(); cal_act=Y[is23].mean()              # calibration: predicted vs actual plate rate in 2/3
# ---- odds ratios (combined, standardized) ----
scAll=StandardScaler().fit(Xc); clfAll=LogisticRegression(max_iter=1000).fit(scAll.transform(Xc),Y)
ORs=np.exp(clfAll.coef_[0]); feat=["length","phase(promet)","n-sis(2/3)"]
# ---- secondary: does ablation->meta add? (subset with am) ----
sub=[r for r in rows if r['am'] is not None]
aucAM=None
if len(sub)>=30:
    Ls=np.array([r['length'] for r in sub]);Ps=np.array([r['phase'] for r in sub]);Ns=np.array([r['n23'] for r in sub])
    As=np.array([r['am'] for r in sub]);Ys=np.array([r['label'] for r in sub])
    aucAM,_=cv_auc(np.column_stack([Ls,Ps,Ns,As]),Ys); aucBase,_=cv_auc(np.column_stack([Ls,Ps,Ns]),Ys)

# ================= FIGURE =================
fig,axs=plt.subplots(2,2,figsize=(13.2,10.2)); (axA,axB),(axC,axD)=axs
# A: base rates (the group prior)
grps=[("1-sisterless",is1),("2/3-sisterless",is23)]
for i,(lab,msk) in enumerate(grps):
    plate=Y[msk].mean()
    axA.bar(i,plate,color="#1b7837",width=.6,label="plate" if i==0 else None)
    axA.bar(i,1-plate,bottom=plate,color="#762a83",width=.6,label="pole" if i==0 else None)
    axA.text(i,plate/2,f"{100*plate:.0f}%\nplate",ha="center",va="center",color="white",fontweight="bold")
    axA.text(i,plate+(1-plate)/2,f"{100*(1-plate):.0f}%\npole",ha="center",va="center",color="white",fontweight="bold")
    axA.text(i,1.02,f"n={msk.sum()}",ha="center",fontsize=8,color="#555")
axA.set_xticks([0,1]); axA.set_xticklabels([g[0] for g in grps]); axA.set_ylim(0,1.1); axA.set_ylabel("fraction")
axA.legend(fontsize=8,loc="lower right"); axA.set_title("The group prior — base rate differs sharply by # sisterless\n(this is the model's strongest single signal)",fontsize=10)
# B: logistic P(plate) vs length (fit on 1-sis), 2/3 overlaid by actual
xs=np.linspace(L.min(),L.max(),100)
pcurve=clf.predict_proba(sc.transform(np.column_stack([xs,np.full_like(xs,PH.mean())])))[:,1]
axB.plot(xs,pcurve,"-",color="#222",lw=2,label="P(plate) fit on 1-sis (length)")
for msk,mk,nm in [(is1,"o","1-sis"),(is23,"x","2/3")]:
    for lab,col in [(1,"#1b7837"),(0,"#762a83")]:
        sel=msk&(Y==lab); jit=(np.random.RandomState(lab).rand(sel.sum())-.5)*.06
        axB.scatter(L[sel],np.full(sel.sum(),lab)+jit,marker=mk,s=30,color=col,alpha=.7,edgecolor="white",lw=.3)
axB.set_xlabel("chromosome length (µm)"); axB.set_ylabel("pole (0)  →  plate (1)")
axB.set_title(f"Length weakly separates fate (o=1-sis, x=2/3; green=plate, purple=pole)\nlength-alone CV AUC={aucLen:.2f}",fontsize=10)
axB.legend(fontsize=8,loc="center right")
# C: ROC curves
def roc(y,p,ax,lab,col):
    fpr,tpr,_=roc_curve(y,p); ax.plot(fpr,tpr,color=col,lw=2,label=lab)
roc(Y,pC,axC,f"COMBINED CV (len+phase+group)  AUC={aucC:.2f}","#2166ac")
roc(Y[is23],p23,axC,f"TRANSFER train-1→test-2/3  AUC={aucT:.2f}","#d95f0e")
axC.plot([0,1],[0,1],"--",color="#888",lw=1); axC.set_xlabel("false positive rate"); axC.set_ylabel("true positive rate")
axC.set_title(f"Discrimination (ROC)\ngroup-only AUC={aucGrp:.2f} · length+phase AUC={aucLP:.2f}",fontsize=10); axC.legend(fontsize=8,loc="lower right")
# D: odds ratios
order=np.argsort(ORs); yy=np.arange(len(feat))
axD.barh(yy,[ORs[i] for i in order],color=["#b2182b" if ORs[i]>1 else "#2166ac" for i in order])
axD.axvline(1,color="#222",lw=1); axD.set_yticks(yy); axD.set_yticklabels([feat[i] for i in order])
for i,o in enumerate(order): axD.text(ORs[o],i,f" {ORs[o]:.2f}×",va="center",fontsize=9)
axD.set_xlabel("odds ratio for reaching the PLATE (per +1 SD; >1 favors plate)")
axD.set_title("What drives the prediction (combined model)\n2/3-group ↑plate-odds; longer ↓; prometaphase ↑",fontsize=10)
fig.suptitle("#48  Predicting plate-vs-pole fate of a sisterless kinetochore — CHROMOSOME_ANNOTATIONS_MASTER (on-target)\n"
             f"COMBINED CV AUC={aucC:.2f} · transfer 1→2/3 AUC={aucT:.2f} · but calibration shifts (1-sis-trained predicts {100*cal_pred:.0f}% plate for 2/3 vs actual {100*cal_act:.0f}%)",
             fontweight="bold",fontsize=11,x=.01,ha="left")
plt.tight_layout(rect=[0,0,1,0.955])
plt.savefig(f"{OUT}/G3_plate_pole_predictive_model.png",bbox_inches="tight",dpi=130)
plt.savefig(f"{PDF}/G3_plate_pole_predictive_model.pdf",bbox_inches="tight"); plt.close()
lib.record_plot("G3_plate_pole_predictive_model",["length","phase","n_sisterless","label"],[],
                {"source":"CHROMOSOME_MASTER.csv","N":len(rows),"AUC_combined_cv":round(aucC,3),
                 "AUC_transfer_1to23":round(aucT,3),"AUC_group_only":round(aucGrp,3),"AUC_length_only":round(aucLen,3),
                 "AUC_with_ablation_meta":round(aucAM,3) if aucAM else None},SCRIPT,"Plate/pole predictive model", fig=fig)
print(f"COMBINED CV AUC={aucC:.3f} | transfer 1→2/3 AUC={aucT:.3f} | group-only={aucGrp:.3f} | length-only={aucLen:.3f} | len+phase={aucLP:.3f}")
print(f"odds ratios (per +1SD toward plate): "+", ".join(f"{f}={o:.2f}" for f,o in zip(feat,ORs)))
if aucAM: print(f"adding ablation→meta: AUC {aucBase:.3f} -> {aucAM:.3f} (N={len(sub)})")
print(f"transfer calibration: 1-sis-trained model predicts {100*cal_pred:.0f}% plate for 2/3, actual {100*cal_act:.0f}%")
