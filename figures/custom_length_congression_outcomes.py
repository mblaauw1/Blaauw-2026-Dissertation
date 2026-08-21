"""Length + congression timing + behavior -> mitotic outcomes. ALL per-chromosome data now comes from the ONE
consolidated source CHROMOSOME_MASTER.csv (regenerate via build_chromosome_annotations_master.py).
Per-cell outcomes (metaphase duration / anaphase onset) join by batch from ABLATION_MASTER.csv. (user 2026-07-20)
"""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, os, numpy as np, matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
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
SRC="/Volumes/4 MB/annotations/CHROMOSOME_MASTER.csv"
data,_=lib.load_master(); mr={r["Batch Name"]:r for r in data}
def phase(b):
    p=mr.get(b,{}).get("Phase of Ablations","").strip().lower()
    ph="Prophase" if p.startswith("proph") else "Prometaphase" if p.startswith("promet") else "Metaphase" if p.startswith("metaph") else None
    return "Prometaphase" if (ph=="Prophase" and lib.is_v2_prometaphase(b)) else ph
def md(b):
    r=mr.get(b);
    if not r: return None
    d,ok=lib.mitotic_duration_min(r); return d if ok else None
def ana(b): return lib.parse_time(mr.get(b,{}).get("Anaphase Onset (s)",""))
PCOL={"Prophase":"#1b7837","Prometaphase":"#2166ac","Metaphase":"#762a83",None:"#999"}

# ---- per-chromosome from the consolidated master ----
chrom=[]  # {batch, chr, length, behavior, delay_s, phase}
for r in csv.DictReader(open(SRC)):
    L=r.get('length_um','').strip(); bh=r.get('behavior','').strip()
    d=r.get('congression_delay_from_meta_onset_s','').strip()
    chrom.append(dict(batch=r['batch'],chr=r['chr_num'],
                      length=(float(L) if L else None),behavior=(bh or None),
                      delay=(float(d) if d else None),phase=phase(r['batch'])))
# ---- per-cell aggregates ----
def score(behavior,delay):
    if behavior=="at_plate": return 1.0
    if behavior=="noncongression": return 0.0
    if behavior=="congressed": return 0.5 if delay is None else max(0.0,min(1.0,1.0-delay/1800.0))
    return None
by=defaultdict(list)
for c in chrom: by[c['batch']].append(c)
cell=[]
for b,cs in by.items():
    sc=[score(c['behavior'],c['delay']) for c in cs if c['behavior']]
    dl=[c['delay'] for c in cs if c['behavior']=="congressed" and c['delay'] is not None]
    L=[c['length'] for c in cs if c['length'] is not None]
    cell.append(dict(batch=b,phase=phase(b),dur=md(b),ana=ana(b),
                     score=(np.mean([s for s in sc if s is not None]) if any(s is not None for s in sc) else None),
                     meandelay=(np.mean(dl) if dl else None),
                     meanlen=(np.mean(L) if L else None),maxlen=(max(L) if L else None),
                     # RESTORED 2026-07-22: these two per-cell aggregates were only ever computed by a one-off
                     # script (plots existed since 07-20 with no permanent code). Re-homed here so they rebuild.
                     lenspread=(float(np.std(L,ddof=1)) if len(L)>=2 else None),   # length heterogeneity
                     maxdelay=(max(dl) if dl else None),                            # slowest chromosome
                     npolar=sum(1 for c in cs if c['behavior']=="noncongression")))

def scatter(xs,ys,phs,xl,yl,title,fn,yfmt=None,highlight=False,keys=None):
    """keys: optional per-point identifier (batch) so each recorded row ties back to a source row.

    2026-08-03: this helper recorded an EMPTY row list for every plot it drew, while still writing rho/p/N
    into the settings block - so seven placed figures advertised a statistic that could not be checked
    against their own data, and any _zoom companion built from those CSVs was built from nothing. The
    figures themselves were always fine; only the provenance was missing."""
    if keys is None: keys=[None]*len(xs)
    pts=[(x,y,p,k) for x,y,p,k in zip(xs,ys,phs,keys) if x is not None and y is not None]
    X=[a for a,_,_,_ in pts]; Y=[b for _,b,_,_ in pts]; P=[p for _,_,p,_ in pts]; K=[k for _,_,_,k in pts]
    fig,ax=plt.subplots(figsize=(6.9,5.0))
    for ph in ["Prophase","Prometaphase","Metaphase",None]:
        xx=[x for x,p in zip(X,P) if p==ph]; yy=[y for y,p in zip(Y,P) if p==ph]
        if xx: ax.scatter(xx,yy,s=34,color=PCOL[ph],alpha=.82,edgecolor="white",lw=.4,label=(ph or "unspecified"))
    if len(X)>=3:
        m,bb=np.polyfit(X,Y,1); xr=np.linspace(min(X),max(X),20); ax.plot(xr,m*xr+bb,"-",color="#222",lw=1.7)
    rho,p=stats.spearmanr(X,Y) if len(X)>=4 else (None,None)
    ax.set_xlabel(xl); ax.set_ylabel(yl)
    if yfmt: ax.yaxis.set_major_formatter(FuncFormatter(yfmt))
    ax.set_title(title+(f"\nSpearman ρ={rho:.2f}, p={p:.3g}, N={len(X)}" if rho is not None else f"\nN={len(X)}"),fontsize=10)
    ax.legend(fontsize=8)
    plt.tight_layout(); plt.savefig(f"{OUT}/{fn}.png",bbox_inches="tight",dpi=130); plt.close()
    lib.record_plot(fn,["batch","x","y","phase"],
                    [[k if k is not None else "",round(float(x),5),round(float(y),5),ph or ""]
                     for x,y,ph,k in pts],{"source":"CHROMOSOME_MASTER.csv",
                    "rho":round(rho,3) if rho is not None else None,"p":round(p,4) if p is not None else None,"N":len(X)},SCRIPT,title)
    return rho,p,len(X)

hhmm=lambda v,_:(f"{int(v//60)}:{int(v%60):02d}" if v>=0 else "")
res={}
# per-chromosome: length vs congression delay
cc=[c for c in chrom if c['behavior']=="congressed" and c['length'] is not None and c['delay'] is not None]
res['G3_length_vs_congression_delay']=scatter([c['length'] for c in cc],[c['delay']/60 for c in cc],[c['phase'] for c in cc],
    "chromosome length (µm)","congression delay from metaphase onset (min)","Longer chromosomes congress later","G3_length_vs_congression_delay",keys=[c["batch"] for c in cc])
# per-cell
res['G3_congression_delay_vs_metaphase_duration']=scatter([c['meandelay'] and c['meandelay']/60 for c in cell],[c['dur'] for c in cell],[c['phase'] for c in cell],
    "mean congression delay from metaphase onset (min)","metaphase duration, Meta→Ana (min)","Later congression → longer metaphase","G3_congression_delay_vs_metaphase_duration",keys=[c["batch"] for c in cell])
res['G3_congression_delay_vs_anaphase_onset']=scatter([c['meandelay'] and c['meandelay']/60 for c in cell],[c['ana'] and c['ana']/60 for c in cell],[c['phase'] for c in cell],
    "mean congression delay from metaphase onset (min)","anaphase onset (min from frame 0)","Later congression → later anaphase","G3_congression_delay_vs_anaphase_onset",keys=[c["batch"] for c in cell])
res['G3_congression_score_vs_metaphase_duration']=scatter([c['score'] for c in cell],[c['dur'] for c in cell],[c['phase'] for c in cell],
    "congression score (1=all at plate/early · 0=all polar)","metaphase duration, Meta→Ana (min)","Congression score vs metaphase duration","G3_congression_score_vs_metaphase_duration",keys=[c["batch"] for c in cell])
res['G3_congression_score_vs_anaphase_onset']=scatter([c['score'] for c in cell],[c['ana'] and c['ana']/60 for c in cell],[c['phase'] for c in cell],
    "congression score","anaphase onset (min from frame 0)","Congression score vs anaphase onset","G3_congression_score_vs_anaphase_onset",keys=[c["batch"] for c in cell])
res['G3_mean_length_vs_metaphase_duration']=scatter([c['meanlen'] for c in cell],[c['dur'] for c in cell],[c['phase'] for c in cell],
    "per-cell mean chromosome length (µm)","metaphase duration, Meta→Ana (min)","Mean chromosome length vs metaphase duration","G3_mean_length_vs_metaphase_duration",keys=[c["batch"] for c in cell])
res['G3_longest_chromosome_vs_metaphase_duration']=scatter([c['maxlen'] for c in cell],[c['dur'] for c in cell],[c['phase'] for c in cell],
    "longest chromosome in cell (µm)","metaphase duration, Meta→Ana (min)","A longer chromosome present → longer metaphase","G3_longest_chromosome_vs_metaphase_duration",keys=[c["batch"] for c in cell])
# NOT RESTORED (2026-07-22): G3_length_spread_vs_metaphase_duration and
# G3_max_congression_delay_vs_metaphase_duration were built by a one-off script whose code was never saved.
# Their ORIGINAL metric definitions are UNKNOWN (the archived code cache holds this file, not theirs).
# Reconstructing them required GUESSING the metric (SD vs range vs CV; max over congressed vs all), which
# produced different statistics than the originals (rho 0.307 vs 0.379; 0.647 vs 0.653). Per user rule
# "assume nothing", they are left unbuilt rather than fabricated. Retired outputs: /Volumes/4 MB/_retired/.

# length by behavior (box)
CATS=[("at_plate","at plate\nwhole time","#1b7837"),("congressed","congressed","#2166ac"),("noncongression","never congressed\n(polar→anaphase)","#762a83")]
g=defaultdict(list)
for c in chrom:
    if c['length'] is not None and c['behavior']: g[c['behavior']].append(c['length'])
fig,ax=plt.subplots(figsize=(7.4,5.0))
for i,(k,lab,col) in enumerate(CATS):
    v=g[k]
    if not v: continue
    x=i+1
    ax.boxplot([v],positions=[x],widths=.55,patch_artist=True,boxprops=dict(facecolor=col,alpha=.25,edgecolor=col),
               medianprops=dict(color=col,lw=2),whiskerprops=dict(color=col),capprops=dict(color=col),showfliers=False)
    jit=(np.random.RandomState(i).rand(len(v))-.5)*.3; ax.scatter(np.full(len(v),x)+jit,v,s=24,color=col,alpha=.7,edgecolor="white",lw=.3)
    ax.text(x+0.36,np.median(v),f"{np.mean(v):.1f}µm\nn={len(v)}",ha="left",va="center",fontsize=8,color=col)
ax.set_xticks([1,2,3]); ax.set_xticklabels([c[1] for c in CATS],fontsize=9); ax.set_ylabel("chromosome length (µm)")
present=[g[k] for k,_,_ in CATS if len(g[k])>=2]; kw=stats.kruskal(*present) if len(present)>=2 else None
ax.set_title(f"Chromosome length by post-ablation behavior\nKruskal p={kw.pvalue:.3g}" if kw else "Length by behavior",fontsize=11)
plt.tight_layout(); plt.savefig(f"{OUT}/G3_length_by_behavior.png",bbox_inches="tight",dpi=130); plt.close()
# 2026-08-03: was recording ZERO rows while advertising kruskal_p and N - the figure drew fine but its
# provenance could not be checked against its own data. Write the real per-chromosome rows.
lib.record_plot("G3_length_by_behavior",["length_um","behavior"],
  [[round(float(v),4),k] for k,_,_ in CATS for v in g[k]],{"source":"CHROMOSOME_MASTER.csv","kruskal_p":round(kw.pvalue,4) if kw else None,"N":sum(len(g[k]) for k,_,_ in CATS)},SCRIPT,"Length by behavior")
res['G3_length_by_behavior']=(None,kw.pvalue if kw else None,sum(len(g[k]) for k,_,_ in CATS))

print(f"regenerated from CHROMOSOME_ANNOTATIONS_MASTER ({len(chrom)} chromosomes / {len(cell)} cells):")
for k,(rho,p,n) in res.items(): print(f"  {k}: ρ={rho} p={p} N={n}")
