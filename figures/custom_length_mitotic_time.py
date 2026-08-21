"""#51 — Chromosome LENGTH -> MITOTIC TIME, decomposed. Two pathways the user asked about:
  (a) via staying POLAR: longer chromosome -> more likely to stay polar -> longer mitosis;
  (b) 2nd-degree via CONGRESSION: longer chromosome -> congresses later / less likely -> longer metaphase.
All per-chromosome data from CHROMOSOME_ANNOTATIONS_MASTER; mitotic duration per cell from ABLATION_MASTER.
Mediation is shown with partial correlation: does length's effect on duration survive controlling for congression delay?
"""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, os, numpy as np, matplotlib.pyplot as plt
from scipy import stats
from collections import defaultdict
import lib
lib.apply_style()   # 2026-08-17: was MISSING. apply_style() installs the Figure.savefig hook that
                    # mirrors every PNG to illustrator/*.svg AND to _ai_relink/pdf/*.pdf -- the PDFs the
                    # .ai decks LINK. Without it this builder wrote a fresh PNG while its deck figure
                    # kept whatever PDF some other script last emitted (G3 PDFs were 7.8 DAYS stale and
                    # G3_length_vs_behavior_paired.pdf did not exist at all), so re-running after a data
                    # fix silently never reached the deck. Also applies the house style/font scaling.
OUT="/Volumes/4 MB/ablation_figures_20260625/group3"; os.makedirs(OUT,exist_ok=True); SCRIPT=__file__
PDF="/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf"
SRC="/Volumes/4 MB/annotations/CHROMOSOME_MASTER.csv"
data,_=lib.load_master(); mr={r["Batch Name"]:r for r in data}
def md(b):
    r=mr.get(b)
    if not r: return None
    d,ok=lib.mitotic_duration_min(r); return d if ok else None
def phase(b):
    if lib.is_v2_prometaphase(b): return "Prometaphase"   # USER RULE: v2 binning is the standard (2026-07-22 sweep)
    p=(mr.get(b,{}).get("Phase of Ablations","") or "").lower()
    return "Prophase" if p.startswith("proph") else "Prometaphase" if p.startswith("promet") else "Metaphase" if p.startswith("metaph") else None

chrom=defaultdict(list)
for r in csv.DictReader(open(SRC)):
    b=r['batch'].strip()
    if mr.get(b,{}).get("On-Target / Off-Target","").strip().lower()!="on-target": continue
    L=r.get('length_um','').strip(); bh=r.get('behavior','').strip()
    d=r.get('congression_delay_from_meta_onset_s','').strip()
    chrom[b].append(dict(L=float(L) if L else None, bh=bh or None, delay=float(d) if d else None))
cell=[]
for b,cs in chrom.items():
    Ls=[c['L'] for c in cs if c['L'] is not None]
    dl=[c['delay'] for c in cs if c['bh']=="congressed" and c['delay'] is not None]
    cell.append(dict(b=b,maxlen=(max(Ls) if Ls else None),meanlen=(np.mean(Ls) if Ls else None),
                     haspolar=1 if any(c['bh']=="noncongression" for c in cs) else 0,
                     meandelay=(np.mean(dl) if dl else None),dur=md(b),phase=phase(b)))

def sr(x,y):
    p=[(a,b) for a,b in zip(x,y) if a is not None and b is not None]
    if len(p)<5: return None,None,len(p)
    X=[a for a,_ in p]; Y=[b for _,b in p]; r,pv=stats.spearmanr(X,Y); return r,pv,len(p)
def partial(xn,yn,zn):
    P=[(c[xn],c[yn],c[zn]) for c in cell if c[xn] is not None and c[yn] is not None and c[zn] is not None]
    if len(P)<6: return None,len(P)
    import numpy as _np
    X=stats.rankdata([p[0] for p in P]); Y=stats.rankdata([p[1] for p in P]); Z=stats.rankdata([p[2] for p in P])
    rxy=_np.corrcoef(X,Y)[0,1]; rxz=_np.corrcoef(X,Z)[0,1]; ryz=_np.corrcoef(Y,Z)[0,1]
    pr=(rxy-rxz*ryz)/(((1-rxz**2)*(1-ryz**2))**0.5 + 1e-12); return pr,len(P)

fig,(axA,axB)=plt.subplots(1,2,figsize=(13.2,5.4))
# ---- A: longest chromosome length vs mitotic time, colored by whether the cell has a polar chromosome ----
for hp,col,lab in [(0,"#2166ac","no polar chromosome"),(1,"#b2182b","has a polar chromosome")]:
    xs=[c['maxlen'] for c in cell if c['haspolar']==hp and c['maxlen'] is not None and c['dur'] is not None]
    ys=[c['dur'] for c in cell if c['haspolar']==hp and c['maxlen'] is not None and c['dur'] is not None]
    if xs: axA.scatter(xs,ys,s=42,color=col,alpha=.8,edgecolor="white",lw=.4,label=f"{lab} (n={len(xs)})")
X=[c['maxlen'] for c in cell]; Y=[c['dur'] for c in cell]
r,pv,n=sr(X,Y)
xy=[(a,b) for a,b in zip(X,Y) if a is not None and b is not None]
if len(xy)>=3:
    m,bb=np.polyfit([a for a,_ in xy],[b for _,b in xy],1); xr=np.linspace(min(a for a,_ in xy),max(a for a,_ in xy),20); axA.plot(xr,m*xr+bb,"-",color="#222",lw=1.7)
axA.set_xlabel("longest ablated chromosome in cell (µm)"); axA.set_ylabel("Metaphase duration (min)")
axA.set_title(f"(a) Longer chromosome present → longer mitosis\nSpearman ρ={r:.2f}, p={pv:.2g}, N={n}",fontsize=10); axA.legend(fontsize=8)
# ---- B: mediation path: length -> congression delay -> duration ----
r_ld,p_ld,n_ld=sr([c['maxlen'] for c in cell],[c['dur'] for c in cell])
r_lc,p_lc,_=sr([c['maxlen'] for c in cell],[c['meandelay'] for c in cell])
r_cd,p_cd,_=sr([c['meandelay'] for c in cell],[c['dur'] for c in cell])
pr,npart=partial('maxlen','dur','meandelay')
axB.axis('off')
axB.set_title("(b) Is the length→time effect mediated by congression?",fontsize=10)
def node(x,y,txt,col):
    axB.add_patch(plt.Rectangle((x-.14,y-.06),.28,.12,fc=col,ec="#333",alpha=.9,transform=axB.transAxes))
    axB.text(x,y,txt,ha="center",va="center",fontsize=9,fontweight="bold",color="white",transform=axB.transAxes)
node(.18,.75,"chromosome\nlength","#1b7837"); node(.82,.75,"congression\ndelay","#2166ac"); node(.5,.28,"mitotic\nduration","#762a83")
def arrow(x1,y1,x2,y2,txt):
    axB.annotate("",xy=(x2,y2),xytext=(x1,y1),xycoords=axB.transAxes,textcoords=axB.transAxes,arrowprops=dict(arrowstyle="-|>",lw=2,color="#444"))
    axB.text((x1+x2)/2,(y1+y2)/2+.03,txt,ha="center",fontsize=8.5,color="#333",transform=axB.transAxes)
arrow(.30,.75,.68,.75,f"ρ={r_lc:.2f}" if r_lc is not None else "n/a")
arrow(.80,.68,.56,.36,f"ρ={r_cd:.2f}" if r_cd is not None else "n/a")
arrow(.22,.68,.44,.36,f"total ρ={r_ld:.2f}")
axB.text(.5,.06,((f"direct length→duration controlling for congression delay:  partial ρ={pr:.2f}  (N={npart})\n"
                  if pr is not None else
                  f"direct length→duration controlling for congression delay:  not computable (N={npart})\n")
               +("→ largely MEDIATED by congression timing" if (pr is not None and r_ld is not None and abs(pr)<abs(r_ld)*0.6) else "→ a direct effect remains")),
         ha="center",fontsize=9,transform=axB.transAxes,color="#333")
fig.suptitle("#51  Chromosome length → mitotic time (via staying polar / via congression) — on-target",fontweight="bold",fontsize=11.5,x=.01,ha="left")
plt.tight_layout(rect=[0,0,1,0.95])
plt.savefig(f"{OUT}/G3_length_vs_mitotic_time.png",bbox_inches="tight",dpi=135)
plt.savefig(f"{PDF}/G3_length_vs_mitotic_time.pdf",bbox_inches="tight"); plt.close()
lib.record_plot("G3_length_vs_mitotic_time",["batch","maxlen","dur","meandelay","haspolar"],[],
                {"source":"CHROMOSOME_MASTER.csv","rho_len_dur":round(r_ld,3) if r_ld else None,
                 "rho_len_delay":round(r_lc,3) if r_lc else None,"rho_delay_dur":round(r_cd,3) if r_cd else None,
                 "partial_len_dur_given_delay":round(pr,3) if pr else None},SCRIPT,"Length vs mitotic time (mediation)", fig=fig)
# also: mitotic time by polar-presence (the (a) pathway, as a box)
print(f"built #51 | len→dur ρ={r_ld} p={p_ld} | len→delay ρ={r_lc} | delay→dur ρ={r_cd} | partial(len→dur|delay)={pr}")
dp=[c['dur'] for c in cell if c['haspolar']==1 and c['dur'] is not None]; dn=[c['dur'] for c in cell if c['haspolar']==0 and c['dur'] is not None]
if len(dp)>=3 and len(dn)>=3: print(f"  mitotic time: has-polar {np.median(dp):.1f} vs no-polar {np.median(dn):.1f} min, MWU p={stats.mannwhitneyu(dp,dn).pvalue:.3g}")
