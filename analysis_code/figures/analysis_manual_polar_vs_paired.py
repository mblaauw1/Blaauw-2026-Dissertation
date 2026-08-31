"""2026-07-11 (user rule): ALL-MANUAL polar-vs-plate eYFP-Cdc20 intensity — manual polar KT vs manual paired_kt
(NO TrackMate). Replaces the mixed G4_kt_intensity_polar_vs_plate (manual polar + TrackMate plate) for the cells
that have a manual plate control. Same r=9 disk Σ, cytosol_bg-subtracted, measured identically on both.

SUPERSEDED 2026-08-03 (ITEM D investigation) -- DO NOT let this write to the shared name
G4_kt_intensity_polar_vs_plate_MANUAL.png anymore. That name is now owned by
rebuild_182_187_outline_intensity.py, which sources the SAME comparison from her traced kt_outlines
(annotations/KT_FLUOR_CYTOSOLNORM_20260728.csv, label paired) instead of kt_points.csv's paired_kt label.
Per the 2026-08-03 standing rule (MEMORY.md reference_kk_and_point_measurements_source /
feedback_manual_markings_over_trackmate): "the paired_kt label in kt_points.csv covers only 13 batches,
nearly all Mad1/IF slides, so it is NOT a usable source for cdc20 plots." Verified here: only 3 cdc20
batches have BOTH a manual polar point and a manual paired_kt point, and only 1 of those actually measures
(N=1 cell) -- vs 19 cells / 704 time-matched frames from the kt_outlines source. This script's OWN output
was silently clobbering the correct (N=19/704) file whenever it ran after rebuild_182_187 (both wrote the
identical filename; last-run-wins). Kept only for provenance/audit of the pre-kt_outlines approach -- writes
to its own distinctly-named file below, never the shared deck name. Do not add this script back to any
"rebuild everything" pass that also runs rebuild_182_187_outline_intensity.py without checking run order."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from collections import defaultdict
from scipy import stats
import lib
lib.apply_style()
OUT="/Volumes/4 MB/ablation_figures_20260625/group4"; R=9
trk=defaultdict(lambda: defaultdict(list))
for r in csv.DictReader(open("/Volumes/4 MB/annotations/kt_points.csv")):
    lab=r["label"].strip()
    if lab in ("polar","sisterless","paired_kt","cytosol_bg"):
        try: trk[r["batch"].strip()][lab].append((int(r["frame"]),float(r["t_sec"]),float(r["x"]),float(r["y"])))
        except: pass
def polar(b):
    a=trk[b].get("polar",[]); c=trk[b].get("sisterless",[]); return a if len(a)>=len(c) else c
def meas(ft,cy,fr,x,y):
    g=ft.plane_by_frame(fr)
    if g is None: return None
    if not cy: return None
    c=min(cy,key=lambda c:abs(c[0]-fr)); cb=lib.disk_sum(g,c[2],c[3],R)
    if cb is None: return None
    sx,sy=lib.snap_to_peak(g,x,y)
    if lib.is_saturated(g,sx,sy,R) or lib.is_saturated(g,c[2],c[3],R): return None
    return max(0.0, lib.disk_sum(g,sx,sy,R)-cb)
cells=[b for b in trk if polar(b) and trk[b].get("paired_kt") and not lib.is_mad1(b) and not lib.plot_excluded(b)]  # drop mad1/drug/Exclude=Yes
print(f"cells with BOTH manual polar AND manual paired_kt: {len(cells)}")
pairs=[]   # (batch, polar_med, plate_med)
for b in sorted(cells):
    ft=lib.FluorTif(b,'monitoring')
    if not ft.ok():
        ft=lib.FluorTif(b,'ablation')
    if not ft.ok(): print(f"  {b}: no fluor movie"); continue
    cy=trk[b].get("cytosol_bg",[])
    pv=[meas(ft,cy,fr,x,y) for (fr,t,x,y) in polar(b)]
    qv=[meas(ft,cy,fr,x,y) for (fr,t,x,y) in trk[b]["paired_kt"]]
    ft.close()
    pv=[v for v in pv if v is not None]; qv=[v for v in qv if v is not None]
    if pv and qv:
        pairs.append((b,float(np.median(pv)),float(np.median(qv))))
        print(f"  {b[:40]:40s} polar={np.median(pv):8.0f}  plate(paired)={np.median(qv):8.0f}  (n_pol={len(pv)},n_plate={len(qv)})")
fig,ax=plt.subplots(figsize=(5.6,5.4)); rec=[]
if pairs:
    pol_=np.array([p[1] for p in pairs]); pla_=np.array([p[2] for p in pairs])
    for _,pv,qv in pairs: ax.plot([0,1],[qv,pv],color=("#7b3294" if pv>qv else "#c2c2c2"),lw=1.0,marker="o",ms=5,alpha=.8)
    ax.hlines(np.median(pla_),-.18,.18,color="#1b7837",lw=2.6); ax.hlines(np.median(pol_),.82,1.18,color="#7b3294",lw=2.6)
    try: W,p=stats.wilcoxon(pol_,pla_,alternative="greater"); pw=f"Wilcoxon (polar>plate, paired) p={p:.2g}"
    except Exception: pw="Wilcoxon n/a"
    frac=float(np.mean(pol_>pla_))
    ax.set_title(f"[LEGACY/AUDIT ONLY -- superseded by rebuild_182_187_outline_intensity.py]\neYFP-Cdc20 polar vs plate KT — kt_points paired_kt source (banned for cdc20 per 2026-08-03 standing rule)\n{pw}; polar brighter in {frac*100:.0f}% of {len(pairs)} cells (med polar {np.median(pol_):,.0f} vs plate {np.median(pla_):,.0f})",loc="left",fontweight="bold",fontsize=8.2)
    rec=[[b,round(pv,1),round(qv,1)] for b,pv,qv in pairs]
else:
    ax.set_title("[LEGACY/AUDIT ONLY] polar vs plate, kt_points paired_kt source — no cells with both manual polar + paired_kt measurable",loc="left",fontsize=9)
ax.set_xticks([0,1]); ax.set_xticklabels(["plate KT\n(manual paired_kt)","polar KT\n(manual)"])
ax.set_ylabel(f"eYFP-Cdc20 intensity (Σ r={R} disk, cytosol-bg-subtracted)")
plt.tight_layout()
# RENAMED (2026-08-03, ITEM D): was G4_kt_intensity_polar_vs_plate_MANUAL.png, which collided with and was
# being silently overwritten BY / silently overwriting rebuild_182_187_outline_intensity.py's correct,
# much-larger-N kt_outlines-sourced version of the same-named deck plot. This script's kt_points-paired_kt
# source is banned for cdc20 plots (standing rule) and is kept only as an audit trail, off the shared name.
OUT_ID="G4_kt_intensity_polar_vs_plate_MANUAL_LEGACY_kt_points_paired_kt"
plt.savefig(f"{OUT}/{OUT_ID}.png",bbox_inches="tight"); plt.close()
lib.record_plot(OUT_ID,["batch","polar_au","plate_manual_au"],rec,
  {"type":"paired dumbbell + Wilcoxon","plate":"kt_points paired_kt label (NOT kt_outlines) — BANNED source for cdc20 per 2026-08-03 standing rule, kept for audit only",
   "measure":f"r={R} disk Σ cytosol-bg-subtracted, identical both",
   "note":"LEGACY: superseded by G4_kt_intensity_polar_vs_plate_MANUAL (rebuild_182_187_outline_intensity.py, kt_outlines-sourced, N=19 cells/704 frames). NOT placed in the deck under the old name anymore."},
  __file__,"LEGACY/audit: polar vs plate (kt_points paired_kt) eYFP-Cdc20 intensity — superseded, not the deck figure")
print(f"wrote {OUT_ID}.png (N={len(pairs)} cells) -- LEGACY/audit only, no longer the deck's G4_kt_intensity_polar_vs_plate_MANUAL")
