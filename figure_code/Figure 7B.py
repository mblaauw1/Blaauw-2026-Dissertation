"""Kinetochore–Kinetochore (KK) distance in µm, by ablation phase."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, numpy as np, matplotlib.pyplot as plt
from collections import defaultdict
from scipy import stats as _st
import lib
lib.apply_style()
OUT="/Volumes/4 MB/ablation_figures_20260625/group2"; SCRIPT=__file__
data,_=lib.load_master(); mr={r["Batch Name"]:r for r in data}
_dbl=lib.double_chromosome_batches()   # l429: destruction of 2 KTs on one chromosome excluded from ALL plots (globally)
def pxsize(b):
    v=mr.get(b,{}).get("Pixel Size (um)","")
    try: return float(v)
    except: return 0.062
import re as _re_kk
_V2PAT_kk=_re_kk.compile(r'v2\s*=\s*prometaphase',_re_kk.I)
V2_PROMETA={b for b in mr if _V2PAT_kk.search((mr[b].get("Notes","") or ""))}   # user v2=prometaphase reclassification
def phase_of(b):
    if b in V2_PROMETA: return "Prometaphase"                                   # USER 2026-07-16: use v2 binning (prophase-flagged -> prometaphase), like the phase-split
    p=mr.get(b,{}).get("Phase of Ablations","").strip().lower()
    return "Prophase" if p.startswith("proph") else "Prometaphase" if p.startswith("promet") else "Metaphase" if p.startswith("metaph") else None
def sis(b): return mr.get(b,{}).get("# Sisterless KTs","")

# (KK-LOWKK) 2026-07-10 (user): 4 PROMETAPHASE batches with extremely-low KK measurements — the low tail of the
# prometaphase violin (~0.52-0.76 µm, well below the ~1.0-2.6 main cluster). Removed from ALL KK plots (per-pair,
# per-cell, summary) so they stay consistent, and flagged for review-later (likely mis-clicked / too-close sister
# annotations). NOT the same as the existing <0.4 near-zero point filter — these survive that.
KK_LOWKK_EXCLUDE={
    "20250901 triple_ablation_6",              # low pair 0.524 µm
    "20260108 two_sisterless_kinetochores_18", # low pair 0.547 µm
    "20251029 triple_ablation_4",              # low pair 0.742 µm
    "20250925 triple_ablation_26",             # low pair 0.762 µm
}
for _b in sorted(KK_LOWKK_EXCLUDE):
    lib.log_review("KK_lowkk_prometa_excluded",_b,"prometaphase, extremely-low KK (violin low tail)","batch removed from all KK plots per user (2026-07-10) — verify sister annotations / KK measurement; likely mis-clicked or too-close pair")

rows=list(csv.reader(open("/Volumes/4 MB/annotations/kt_points.csv"))); ix={c:i for i,c in enumerate(rows[0])}
# group: batch -> frame -> {label:[(x,y)]}
byb=defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
for r in rows[1:]:
    b=r[ix['batch']].strip()
    # USER 2026-07-16: metaphase IS allowed on the KK-by-phase plot, so drop drug/Exclude/REVIEW/4-sis but KEEP metaphase.
    if lib.is_mad1(b) or b in _dbl or b in KK_LOWKK_EXCLUDE: continue
    if lib.is_drug(b) or lib.is_four_sisterless(b) or lib.excluded(b) or (mr.get(b,{}).get("Exclude","") or "").strip().lower() in ("yes","true","1"): continue
    try: x=float(r[ix['x']]); y=float(r[ix['y']])
    except: continue
    byb[b][r[ix['frame']]][r[ix['label']].strip()].append((x,y))

def pair_nn(A,B):
    """nearest-neighbour pairing; return list of (a,b) pairs."""
    A=list(A); B=list(B); pairs=[]; used=set()
    for a in A:
        best=None;bd=1e18
        for j,b in enumerate(B):
            if j in used: continue
            d=(a[0]-b[0])**2+(a[1]-b[1])**2
            if d<bd: bd=d;best=j
        if best is not None: used.add(best); pairs.append((a,B[best]))
    return pairs

# per-batch KK: use the pre_abl frame (native sister distance before ablation)
batch_kk=defaultdict(list)   # batch -> [kk_um per pair]
for b,frames in byb.items():
    ps=pxsize(b)
    for fr,labs in frames.items():
        A=labs.get("pre_abl",[]); B=labs.get("pre_abl_pair",[])
        if not A or not B: continue
        for a,bb in pair_nn(A,B):
            d=np.hypot(a[0]-bb[0],a[1]-bb[1])*ps
            if d>20: lib.log_review("KK_dist",b,f"{d:.1f}um","implausible KK distance (>20um) — excluded"); continue
            batch_kk[b].append(d)

# ---------- Plot 1: KK distance (per pair) vs phase ----------
PHASES=["Prophase","Prometaphase","Metaphase"]
PCOL={"Prophase":"#1b7837","Prometaphase":"#2166ac","Metaphase":"#762a83"}
# 🔴 HER 2026-08-25 item 12: *"For prophase group only use measurements from cells plotted on
# G2_noc_washout_vs_prophase (so 6 for single and 2+3+3=8 for triple)"*. That figure now writes the exact
# cells it plots (custom_noc_washout_v2_20260722.py -> the CSV below); the prophase group here is restricted
# to them, so the two figures cannot disagree about which cells are "the prophase cells".
_PROPH_ONLY=set()
try:
    import csv as _csv_p
    for _r in _csv_p.DictReader(open("/Volumes/4 MB/annotations/NOC_WASHOUT_PROPHASE_CELLS_20260825.csv")):
        _b=(_r.get("batch") or "").strip()
        if _b: _PROPH_ONLY.add(_b)
    print(f"prophase restricted to the {len(_PROPH_ONLY)} cells plotted on G2_noc_washout_vs_prophase")
except Exception as _e:
    print("prophase restriction list unavailable, prophase left unrestricted:", _e)

perpair=defaultdict(list); rows_out=[]; _nz_excluded=0; _nz_prophase=[]; _proph_dropped=0
for b,ds in batch_kk.items():
    ph=phase_of(b)
    if ph is None: continue
    if ph=="Prophase" and _PROPH_ONLY and b not in _PROPH_ONLY:
        _proph_dropped+=1; continue
    for d in ds:
        # audio S31: exclude the near-zero prometaphase/prophase points the user flagged for review
        if ph in ("Prophase","Prometaphase") and d<0.4:
            if ph=="Prophase":
                # F5: flag the near-zero PROPHASE points for manual verification (likely mis-clicked sisters)
                lib.log_review("kk_near_zero",b,f"{d:.3f}","near-zero prophase KK — verify"); _nz_prophase.append((b,d))
            lib.log_review("KK_nearzero_excluded",b,f"{d:.2f}um in {ph}","near-zero KK point EXCLUDED per audio S31"); _nz_excluded+=1; continue
        perpair[ph].append((d,sis(b))); rows_out.append([b,ph,sis(b),round(d,3)])
if _proph_dropped: print(f"prophase: {_proph_dropped} cell(s) dropped -- not on G2_noc_washout_vs_prophase")
print("F5 near-zero PROPHASE KK points (flagged kk_near_zero):")
for _b,_d in _nz_prophase: print(f"    {_b}  ->  {_d:.3f} um")
SM3={"1":"o","2":"s","3":"^"}   # marker shape by sisterless count (slide-32 request)
fig,ax=plt.subplots(figsize=(7,5))
for i,ph in enumerate(PHASES):
    pts=perpair.get(ph,[])
    if not pts: continue
    d=[v for v,_ in pts]
    lib.journal_violin(ax,d,i,PCOL[ph],width=0.6,alpha=.3)   # scale=width (uniform max half-width), cut=0, N<6 points-only
    rs=np.random.RandomState(i)
    for (v,sc) in pts:
        ax.scatter(i+(rs.rand()-.5)*.2,v,s=18,color=PCOL[ph],alpha=.8,edgecolor="white",lw=.3,zorder=3,marker=SM3.get(sc,"o"))
    ax.hlines(np.median(d),i-.33,i+.33,color=PCOL[ph],lw=2.2)
    ax.hlines(np.mean(d),i-.28,i+.28,color=PCOL[ph],lw=1.4,ls=(0,(2,1.5)))
    # D8 (2026-07-07): within each phase-violin, test whether the 1/2/3-sisterless subsamples differ
    # (Kruskal-Wallis across the sisterless groups present with >=2 points; MW when exactly two groups).
    from collections import Counter as _Ck
    _bys={s:[v for v,sc in pts if sc==s] for s in "123"}; _gk=[vv for vv in _bys.values() if len(vv)>=2]
    _wtxt="1/2/3-sis n<2\n(not tested)"
    if len(_gk)>=2:
        try:
            _hw,_pw=_st.kruskal(*_gk); _cnt="/".join(str(len(_bys[s])) for s in "123")
            # 🔴 HER 2026-08-20, board-9 item 1: *"Some of the text on this plot is overlapping with other
            # things, fix"*. On the RIGHTMOST (metaphase) violin this one-line form ran off the axes and
            # through the legend, which already sits outside the plot. Split onto two shorter lines so a
            # centred label cannot reach past the axes edge.
            _wtxt=f"1/2/3-sis n {_cnt}\np={_pw:.2g}"
        except Exception: pass
    ax.text(i,max(d)+.3,f"x̄ {np.mean(d):.2f}\nmed {np.median(d):.2f} µm\nN={len(d)}\n{_wtxt}",ha="center",va="bottom",fontsize=6.6)
ax.set_ylim(top=ax.get_ylim()[1]*1.30)   # headroom so the mean/median + within-violin labels don't collide with the title
from matplotlib.lines import Line2D as _L2a
_hkk1=[_L2a([0],[0],marker=SM3[s],color='w',markerfacecolor='#888',markeredgecolor='#888',label=f"{s}-sisterless",ms=7) for s in "123"]
_hkk1+=[_L2a([0],[0],color="#444",lw=2.2,label="median"),_L2a([0],[0],color="#444",lw=1.4,ls=(0,(2,1.5)),label="mean")]
# ITEM 7 (feedback 2026-07-06): the legend overlapped the (rightmost, tall) metaphase violin. Move it OUTSIDE
# the axes to the right so it never covers any violin/points.
ax.legend(handles=_hkk1,fontsize=7.5,loc="upper left",bbox_to_anchor=(1.01,1.0),borderaxespad=0)
# audio s32: stats — Kruskal-Wallis across the three ablation phases (non-parametric, unequal N)
_grp=[[v for v,_ in perpair[ph]] for ph in PHASES if len(perpair.get(ph,[]))>=2]
if len(_grp)>=2:
    _H,_p=_st.kruskal(*_grp)
    # D8 (2026-07-07): the across-phase KW label previously sat at (.02,.02), overlapping the (low-KK) prophase
    # points. Move it BELOW the axes so it never covers a violin/point.
    ax.text(.5,-0.16,f"Kruskal-Wallis across phases: H={_H:.2f}, p={_p:.2g}  ·  within-violin 1/2/3-sisterless test shown above each violin",
            transform=ax.transAxes,fontsize=7.5,va="top",ha="center")
ax.set_xticks(range(len(PHASES))); ax.set_xticklabels(PHASES)
ax.set_ylabel("k\u2013k distance (µm)"); ax.set_title("k\u2013k distance (pre-ablation sister pairs) by phase",loc="left",fontweight="bold",fontsize=11,pad=10)
plt.subplots_adjust(bottom=0.2)   # room for the KW label placed below the axes
plt.tight_layout(); plt.savefig(f"{OUT}/G2_kk_distance_by_phase.png",bbox_inches="tight"); plt.close()
lib.record_plot("G2_kk_distance_by_phase",["batch","phase","n_sisterless","kk_um"],rows_out,
  {"type":"violin+points","source":"kt_points pre_abl/pre_abl_pair, nearest-neighbour pairing",
   "unit":"um (px*PixelSize)","outlier_rule":">20um excluded","color":"by phase"},SCRIPT,
  "KK distance per pre-ablation sister pair, by ablation phase")

# ---------- Plot 2: average KK per cell (1/2/3 sisterless) vs phase ----------
# ITEM 8 (feedback 2026-07-06): "only two points plotted for metaphase but there are at least 8 metaphase
# batches." ROOT CAUSE: this per-cell plot restricted to 2/3-sisterless, but of the 10 metaphase batches that
# have a pre-ablation sister pair, 8 are 1-sisterless and only 2 are 2-sisterless — so the 1-sisterless
# metaphase cells (the majority) were dropped. Include 1-sisterless so every cell with a KK pair is shown.
fig,ax=plt.subplots(figsize=(6.5,5)); rows2=[]
percell=defaultdict(list)
for b,ds in batch_kk.items():
    if sis(b) not in ("1","2","3") or not ds: continue
    ph=phase_of(b)
    if ph is None: continue
    avg=float(np.mean(ds)); percell[ph].append((avg,sis(b))); rows2.append([b,ph,sis(b),round(avg,3),len(ds)])
SM={"1":"o","2":"s","3":"^"}   # marker shape by sisterless count (matches per-pair plot)
for i,ph in enumerate(PHASES):
    dd=percell.get(ph,[]); d=[v for v,_ in dd]
    if not dd: continue
    lib.journal_violin(ax,d,i,PCOL[ph],width=0.45,alpha=.3)   # scale=width (uniform max half-width), cut=0, N<6 points-only; skinnier (slide-33 request)
    for (v,sc) in dd:
        ax.scatter(i+(np.random.RandomState(int(v*97)%9999).rand()-.5)*.16,v,s=lib.VIOLIN_DOT_S,color=PCOL[ph],alpha=.85,edgecolor="white",lw=.4,zorder=3,marker=SM.get(sc,"o"))
    ax.hlines(np.median(d),i-.22,i+.22,color=PCOL[ph],lw=2.2)                                 # median (solid)
    ax.hlines(np.mean(d),i-.18,i+.18,color=PCOL[ph],lw=1.4,ls=(0,(2,1.5)))                    # mean (dashed)
    ax.text(i,max(d)+.2,f"x̄ {np.mean(d):.2f}\nmed {np.median(d):.2f}\nN={len(d)}",ha="center",va="bottom",fontsize=7.5)
ax.set_ylim(top=ax.get_ylim()[1]*1.18)   # headroom so the per-phase mean/median/N labels clear the title (ITEM I)
from matplotlib.lines import Line2D as _L2
_hkk2=[_L2([0],[0],marker=SM[s],color='w',markerfacecolor='#888',markeredgecolor='#888',label=f"{s}-sisterless") for s in "123"]
_hkk2+=[_L2([0],[0],color="#444",lw=2.2,label="median"),_L2([0],[0],color="#444",lw=1.4,ls=(0,(2,1.5)),label="mean")]
ax.legend(handles=_hkk2,fontsize=8,loc="upper left")
# audio s32: stats — Kruskal-Wallis across phases (per-cell averages)
_grp2=[[v for v,_ in percell[ph]] for ph in PHASES if len(percell.get(ph,[]))>=2]
if len(_grp2)>=2:
    _H2,_p2=_st.kruskal(*_grp2)
    ax.text(.02,.02,f"Kruskal-Wallis across phases: H={_H2:.2f}, p={_p2:.2g}",transform=ax.transAxes,fontsize=7.5,va="bottom",ha="left")
ax.set_xticks(range(len(PHASES))); ax.set_xticklabels(PHASES)
ax.set_ylabel("Average KK distance per cell (µm)")
ax.set_title("Average KK distance per cell (1/2/3-sisterless) by phase",loc="left",fontweight="bold",fontsize=11)
plt.tight_layout(); plt.savefig(f"{OUT}/G2_kk_distance_percell.png",bbox_inches="tight"); plt.close()
lib.record_plot("G2_kk_distance_percell",["batch","phase","n_sisterless","avg_kk_um","n_pairs"],rows2,
  {"type":"violin+points","subset":"1/2/3-sisterless","value":"mean KK per cell"},SCRIPT,
  "Average KK distance per cell (1/2/3-sisterless) by ablation phase")
# ---------- Plot 3: CLEAN summary — mean (± 1 SD) KK per phase (slide-26/27 request) ----------
# The user said the per-pair + per-cell plots are "a lot to look at". This is the single, glanceable view:
# one point per phase = mean KK distance, with an SD error bar, N labeled, so the Pro<Prometa<Meta trend
# (KK distance increasing with mitotic progression) reads at a glance. Mean+median text kept per phase.
fig,ax=plt.subplots(figsize=(5.6,4.6)); rows3=[]
for i,ph in enumerate(PHASES):
    d=np.array([v for v,_ in perpair.get(ph,[])],float)
    if d.size==0: continue
    m=float(d.mean()); md_=float(np.median(d)); n=d.size
    # USER 2026-08-17: "for error bars on violin and dot plots, SD is being used." This dot plot showed a
    # 95% CI built from the SEM, which is a statement about how well the MEAN is pinned down, not about how
    # spread the k-k distances are. Now +/- 1 SD (ddof=1), the same quantity every violin in the deck shows.
    sd=float(d.std(ddof=1)) if n>1 else 0.0
    ci=sd
    ax.errorbar(i,m,yerr=sd,fmt="o",ms=11,color=PCOL[ph],ecolor=PCOL[ph],elinewidth=2,capsize=6,capthick=2,zorder=3)
    ax.hlines(md_,i-.14,i+.14,color=PCOL[ph],lw=1.4,ls=(0,(2,1.5)),zorder=4)   # median (dashed) for reference
    ax.text(i,m+ci+0.06,f"x̄ {m:.2f} µm\nmed {md_:.2f}\nN={n}",ha="center",va="bottom",fontsize=8)
    rows3.append([ph,round(m,3),round(md_,3),round(sd,3),n])
# connect the means so the Pro<Prometa<Meta trend is obvious at a glance
_xi=[i for i,ph in enumerate(PHASES) if perpair.get(ph)]; _yi=[float(np.mean([v for v,_ in perpair[PHASES[i]]])) for i in _xi]
if len(_xi)>=2: ax.plot(_xi,_yi,"-",color="#888",lw=1.2,zorder=1)
if len(_grp)>=2:
    ax.text(.02,.98,f"Kruskal-Wallis: H={_H:.2f}, p={_p:.2g}",transform=ax.transAxes,fontsize=8,va="top",ha="left")
ax.set_xticks(range(len(PHASES))); ax.set_xticklabels(PHASES); ax.set_xlim(-.5,len(PHASES)-.5)
ax.set_ylim(bottom=0); ax.set_ylim(top=ax.get_ylim()[1]*1.18)
ax.set_ylabel("Mean KK distance (µm)")
from matplotlib.lines import Line2D as _L2s
ax.legend(handles=[_L2s([0],[0],marker="o",color="#444",lw=2,label="mean ± SD"),
                   _L2s([0],[0],color="#444",lw=1.4,ls=(0,(2,1.5)),label="median")],fontsize=8,loc="lower right")
ax.set_title("k–k distance per phase — summary (mean ± SD)",loc="left",fontweight="bold",fontsize=10)
plt.tight_layout(); plt.savefig(f"{OUT}/G2_kk_distance_summary.png",bbox_inches="tight"); plt.close()
lib.record_plot("G2_kk_distance_summary",["phase","mean_kk_um","median_kk_um","ci95_um","n_pairs"],rows3,
  {"type":"point + SD","source":"per-pair KK by phase","note":"glanceable summary of the per-pair/per-cell plots"},SCRIPT,
  "k–k distance per phase — compact mean±SD summary")

lib.flush_review("/Volumes/4 MB/ablation_figures_20260625/_review/outlier_review_kk.csv")
print("KK distance: batches with KK pairs:",len(batch_kk),"| per-pair by phase:",{k:len(v) for k,v in perpair.items()},"| S31 near-zero excluded:",_nz_excluded)
print("KK summary (mean±SD) rows:",rows3)
