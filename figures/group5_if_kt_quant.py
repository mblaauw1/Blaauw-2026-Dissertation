# 2026-08-16 (NOTES §1 rule 30): the off-target colour #d6604d is a RED and sat against the
# 1-Sister GREEN in every cohort figure. lib.PALETTE moved it to teal #00a0b0, but these builders
# HARD-CODED the hex and so bypassed the palette entirely — found by a pixel audit of the rendered
# figures, not by reading the code. Hard-coded copies replaced; use lib.PALETTE, never a literal.
"""Group 5 / ITEM 2 — IF kinetochore quantification: sisterless vs paired KT fluorescence in 561 & 640.
Uses the manual KT marks in annotations/kt_points.csv on the IF z-stack batches
(20260417 ...IF stained slide 1 posN_1), labels: paired_kt / sisterless / mad1_sister.
For every marked KT we find the punctum (snap_to_peak) and measure BOTH the 561 (CREST) and 640 (tubulin)
channels at the mark's shared z-slice (the 5-channel z-stack shares one slice index across channels), using
lib.disk_local_bg (integrated intensity above the local annulus background). We NORMALIZE per cell, per
channel, to that cell's mean paired-KT intensity, then plot sisterless vs paired. Separate figures for 561
and 640. Each cell (=a paired set) gets its own colour + a connecting line.
MEASUREMENT SOURCE (corrected 2026-08-18): every value is read from the RAW 16-BIT per-channel stack
`<batch>_561_mCherry_Cropped.tif` / `<batch>_640_Cy5_Cropped.tif` in `pipeline_session_output`, NOT from the
8-bit MP4 render.  The earlier note here said no 16-bit TIF existed for these channels; that was true only of
the retired `analysis_mad1_task3_IF_20260626` folder (now gone), and it made this the ONE builder on the
project that quantified from a contrast-stretched movie.  Why it matters: the render applies a per-movie
AFFINE map (gain and offset).  Background subtraction removes the offset but NOT the gain, so intensities
from two differently-stretched movies are not comparable even after background correction, and the 8-bit
render also clips bright kinetochores.  Saturated (clipped) marks are still flagged and dropped."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import os, csv, numpy as np, cv2
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import lib
lib.apply_style()
OUT="/Volumes/4 MB/ablation_figures_20260625/group4"; os.makedirs(OUT,exist_ok=True)
import glob, tifffile
PIPE="/Volumes/4 MB/pipeline_session_output"
CHAN_TIF={"561":"561_mCherry","640":"640_Cy5"}
SAT16=65000        # the 16-bit camera clips at 65535; anything at/above this is unquantifiable

_dircache={}
def batch_dir(b):
    """Resolve a batch to its pipeline output folder (the 16-bit stacks live there)."""
    if b not in _dircache:
        hits=glob.glob(f"{PIPE}/*/{b}") or glob.glob(f"{PIPE}/*/*{b}*")
        _dircache[b]=hits[0] if hits else None
    return _dircache[b]
SIS_LABELS={"sisterless","mad1_sister"}; PAIR_LABEL="paired_kt"

# ---- load marks per IF cell: (label_norm, z, x, y) ----
cells={}
for r in csv.DictReader(open("/Volumes/4 MB/annotations/kt_points.csv")):
    b=r["batch"].strip()
    if "IF stained" not in b: continue
    lab=r["label"].strip()
    cat="sisterless" if lab in SIS_LABELS else ("paired" if lab==PAIR_LABEL else None)
    if cat is None: continue
    try: z=int(float(r["frame"])); x=float(r["x"]); y=float(r["y"])
    except: continue
    cells.setdefault(b,[]).append((cat,z,x,y))

def plane16(b,ch,z):
    """One z-plane of the RAW 16-bit channel stack (no scaling, no contrast stretch)."""
    d=batch_dir(b)
    if not d: return None
    hits=glob.glob(f"{d}/*_{CHAN_TIF[ch]}_Cropped.tif")
    if not hits: return None
    with tifffile.TiffFile(hits[0]) as tf:
        n=len(tf.pages)
        if n<1: return None
        k=max(0,min(int(z),n-1))
        return tf.pages[k].asarray()

_planecache={}
def measure(b,ch,z,x,y):
    """Intensity of the KT at (x,y) in channel ch at shared z-slice; snap xy, disk_local_bg. None if saturated."""
    key=(b,ch,z)
    if key not in _planecache:
        _planecache[key]=plane16(b,ch,z)
    g=_planecache[key]
    if g is None: return None
    sx,sy=lib.snap_to_peak(g,x,y)
    if lib.is_saturated(g,sx,sy,9,level=SAT16): return "SAT"   # 16-bit camera clips at 65535
    v=lib.disk_local_bg(g,sx,sy)   # disk sum above local-annulus bg; snap already centres on the local PEAK
    # A peak-centred disk still below its surrounding annulus = a genuine at-background KT (no signal above bg).
    # Fluorescence cannot be physically negative, so floor at 0 (matches the Mad1 plot's convention).
    return None if v is None else max(0.0,v)

# ---- measure every KT in both channels ----
data={"561":{}, "640":{}}   # channel -> batch -> {"paired":[..],"sisterless":[..]}
report=[]
for b,marks in cells.items():
    has_pair=any(c=="paired" for c,_,_,_ in marks); has_sis=any(c=="sisterless" for c,_,_,_ in marks)
    if not(has_pair and has_sis):
        report.append(f"SKIP {b.replace('20260417 ptk2 eyfp cdc20 ','')}: only {'paired' if has_pair else 'sisterless'} marked")
        continue
    for ch in ("561","640"):
        d=data[ch].setdefault(b,{"paired":[],"sisterless":[]})
        for cat,z,x,y in marks:
            v=measure(b,ch,z,x,y)
            if v=="SAT" or v is None: continue
            d[cat].append(v)
    report.append(f"USE  {b.replace('20260417 ptk2 eyfp cdc20 ','')}: "
                  f"561 P/S={len(data['561'][b]['paired'])}/{len(data['561'][b]['sisterless'])}  "
                  f"640 P/S={len(data['640'][b]['paired'])}/{len(data['640'][b]['sisterless'])}")

SHORT=lambda b:b.replace("20260417 ptk2 eyfp cdc20 IF stained slide 1 ","").replace("_1","").replace(" maybe","")
COLORS=["#1b7837","#2166ac","#762a83","#00a0b0","#e08214","#000000"]

def make_plot(ch,title):
    d=data[ch]
    usable=[b for b in d if d[b]["paired"] and d[b]["sisterless"]]
    fig,ax=plt.subplots(figsize=(6.6,5.0))
    xs={"sisterless":0,"paired":1}
    rng=np.random.RandomState(5)
    all_sis=[]; all_par=[]   # accumulate normalized values across all cells for ONE general trendline
    for i,b in enumerate(sorted(usable)):
        col=COLORS[i%len(COLORS)]
        pmean=np.mean(d[b]["paired"])
        if pmean==0: continue
        sis=[v/pmean for v in d[b]["sisterless"]]; par=[v/pmean for v in d[b]["paired"]]
        all_sis+=sis; all_par+=par
        sx=xs["sisterless"]+rng.uniform(-0.06,0.06,len(sis)); px=xs["paired"]+rng.uniform(-0.06,0.06,len(par))
        ax.scatter(sx,sis,s=55,color=col,edgecolor="k",linewidth=0.5,zorder=3,label=SHORT(b))
        ax.scatter(px,par,s=55,color=col,edgecolor="k",linewidth=0.5,zorder=3)
        # (per-pair connecting trendlines removed per 07-07 feedback IF1)
    # ONE general trendline: grand mean of all sisterless -> grand mean of all paired (across cells)
    if all_sis and all_par:
        ax.plot([xs["sisterless"],xs["paired"]],[np.mean(all_sis),np.mean(all_par)],
                color="k",lw=2.2,alpha=0.9,zorder=4,label="general trend (all-cell mean)")
    ax.axhline(1.0,color="#999",lw=0.8,ls="--",zorder=1)
    ax.set_xticks([0,1]); ax.set_xticklabels(["sisterless KT","paired KT"]); ax.set_xlim(-0.55,1.55)
    ax.set_yscale("log")   # one cell sits ~40x its own paired mean; a linear axis hides every other point
    ax.set_ylabel(f"{title} intensity, normalized to\nper-cell mean paired-KT intensity")
    ax.set_title(f"{title} at sisterless vs paired KTs (IF)")
    # legend OUTSIDE the axes (right) so it never overlaps the data (the 640 legend previously sat on top of
    # the point cloud); bbox_inches="tight" keeps it in the saved PNG.
    ax.legend(title="cell (paired set)",fontsize=8,loc="center left",bbox_to_anchor=(1.01,0.5),borderaxespad=0.0)
    ax.text(0.5,-0.20,f"Normalization: per cell, {ch} intensity / that cell's mean paired-KT intensity "
            f"(dashed=1.0). disk_local_bg on the raw 16-bit stack, floored at 0 (no negative fluorescence). n cells={len(usable)}.",
            transform=ax.transAxes,ha="center",va="top",fontsize=7.5,color="#444")
    plt.tight_layout()
    p=f"{OUT}/G5_item2_IF_KT_{ch}.png"; plt.savefig(p,dpi=200,bbox_inches="tight"); plt.close()
    print("wrote",p,"  cells:",[SHORT(b) for b in sorted(usable)])
    return usable

u561=make_plot("561","561 / CREST")
u640=make_plot("640","640 / tubulin")
print("\n".join(report))
