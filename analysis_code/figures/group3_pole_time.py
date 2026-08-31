"""Does time a kinetochore spends at the pole (before congressing to the plate) correlate with metaphase duration?
One point PER KINETOCHORE (3-sisterless contributes 3 points; NO averaging)."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, numpy as np, matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from matplotlib.lines import Line2D
from scipy import stats
import lib
lib.apply_style()
OUT="/Volumes/4 MB/ablation_figures_20260625/group3"; SCRIPT=__file__
data,_=lib.load_master(); mr={r["Batch Name"]:r for r in data}
_DBL=set(lib.double_chromosome_batches())   # double-chromosome cells: excluded everywhere (was leaking into pole_time + plate_join)
def mdur(b):
    r=mr.get(b);
    if not r: return None
    d,ok=lib.mitotic_duration_min(r); return d if ok else None
PAL={"1":lib.PALETTE["1-Sister"],"2":lib.PALETTE["2-Sister"],"3":lib.PALETTE["3-Sister"]}
r=list(csv.reader(open("/Volumes/4 MB/annotations/SISTERLESS_PLATE_JOIN_TIMES.csv"))); ix={c:i for i,c in enumerate(r[0])}
xs=[];ys=[];fs=[];cs=[];rec=[]
for row in r[1:]:
    if row[ix['exclude_this_data']].strip(): continue
    b=row[ix['batch']].strip(); n=row[ix['n_sisterless']].strip()
    if n not in ("1","2","3") or lib.is_mad1(b) or lib.plot_excluded(b) or b in _DBL: continue   # +REVIEW_EXCLUDE +double-chromosome guard
    meta=lib.parse_time(mr.get(b,{}).get("Metaphase Start (s)","")); dur=mdur(b)
    if meta is None or dur is None: continue
    for k in (1,2,3):   # EACH kinetochore is its own point (no averaging)
        v=row[ix[f'chromosome_{k}_plate_join']].strip(); s=row[ix[f'chromosome_{k}_plate_join_s']].strip()
        if not v or v.lower() in ("n/a","anaphase") or v in("0","0:00:00"): continue   # only KTs that move to plate
        try: jt=float(s)
        except: continue
        pole=(jt-meta)/60.0   # time at pole (after metaphase) before congression
        # D13 (2026-07-07): drop KTs that reach the plate BEFORE metaphase onset (below the metaphase-start line);
        # removes the 3-sisterless point the user flagged (consistent with the arrival-summary plot).
        if pole<0:
            lib.log_review("pole_time_before_metaphase",b,f"{pole:.2f}min (n={n},k={k})","plate-join before metaphase onset — removed (D13)"); continue
        # USER 2026-08-04 (item 27): put the time-at-pole on the Y axis as a 0-1 FRACTION OF METAPHASE ELAPSED
        # (0 = metaphase onset, 1 = anaphase), matching the existing convention in
        # G4_lagging_vs_congression_fraction / G4_plate_distance_time_normalized. In absolute minutes a
        # 1-sisterless and a 3-sisterless cell are not comparable because their mean metaphase durations
        # differ; as a fraction of each cell's own metaphase they are.
        if not dur or dur <= 0: continue
        frac = pole / dur
        if frac > 1.05:   # plate-join after anaphase onset -> not a within-metaphase congression
            lib.log_review("pole_time_after_anaphase",b,f"frac={frac:.2f} (n={n},k={k})",
                           "plate-join later than anaphase onset — removed (item 27 fraction conversion)"); continue
        frac = min(frac, 1.0)
        xs.append(pole); ys.append(dur); fs.append(frac); cs.append(n)
        rec.append([b,n,k,round(pole,2),round(dur,3),round(frac,4)])
xs=np.array(xs);ys=np.array(ys);fs=np.array(fs);cs=np.array(cs)
# ITEM 27 (user 2026-08-04): X = metaphase duration, Y = time at pole as a 0-1 FRACTION of metaphase elapsed.
fig,ax=plt.subplots(figsize=(8,5.6))
for n in "123":
    m=cs==n
    if m.any(): ax.scatter(ys[m],fs[m],s=34,color=PAL[n],alpha=.85,edgecolor="white",lw=.4,label=f"{n}-sisterless (n={m.sum()} KTs)")
rho=p=None
if len(fs)>=5:
    rho,p=stats.spearmanr(ys,fs)   # per-feedback S40: NO all-data (black dashed) trend line; keep per-group
for n in "123":
    mm=cs==n
    if mm.sum()>=4:
        m,b0=np.polyfit(ys[mm],fs[mm],1); xr=np.linspace(ys[mm].min(),ys[mm].max(),20)
        ax.plot(xr,m*xr+b0,color=PAL[n],lw=1.5)
ax.set_xlabel("Metaphase duration (MM:SS)"); ax.xaxis.set_major_formatter(FuncFormatter(lambda v,_: lib.mmss(v) if v>=0 else ""))
ax.set_ylabel("Time at pole before congression\n(fraction of metaphase elapsed: 0=onset, 1=anaphase)")
ax.set_ylim(-0.03,1.03)
ax.legend(fontsize=8); ax.set_title("How far into metaphase does a sisterless kinetochore congress? (per kinetochore)"+(f"  ·  Spearman rho={rho:.2f}, p={p:.2g}" if rho is not None else ""),loc="left",fontweight="bold",fontsize=9)
plt.tight_layout(); plt.savefig(f"{OUT}/G3_pole_time_vs_duration.png",bbox_inches="tight"); plt.close()
lib.record_plot("G3_pole_time_vs_duration",["batch","n_sisterless","chromosome","pole_time_min","mitotic_duration_min","frac_meta_to_ana"],rec,
  {"type":"scatter per-kinetochore","note":"NO averaging for multi-sisterless cells — each KT a point","stat":"Spearman",
   "x_label":"Metaphase duration (min)",
   "y_label":"Time at pole before congression (fraction of metaphase elapsed: 0=onset, 1=anaphase)",
   "item27":"y converted from absolute minutes to a 0-1 fraction of each cell's own metaphase so 1- and 3-sisterless cells (different mean durations) are comparable"},
  SCRIPT,"Fraction of metaphase spent at the pole before congression, vs metaphase duration, per kinetochore")
print(f"pole-time vs duration: {len(fs)} kinetochores; frac median={np.median(fs):.3f}")
