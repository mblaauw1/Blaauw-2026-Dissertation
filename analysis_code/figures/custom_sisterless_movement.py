"""Sisterless-KT MOVEMENT / OSCILLATION analysis (single-ablation cells) from MANUAL tracks (user 2026-07-20).
Manual sisterless marks (kt_points 'sisterless') give the KT trajectory; manual 2-point meta_plate lines give the
metaphase plate per frame. Distance-to-plate over time is the master metric (pole position is undefined, so we use
plate distance). Joins per-chromosome length + behavior (CHROMOSOME_ANNOTATIONS_MASTER) and cell-outline PCA (spindle
long axis). Produces the oscillation / location / movement plots. Blocked questions (no per-KT shape or per-KT fluor
in the manual point marks) are noted in the printout.
"""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, os, glob, json, numpy as np, matplotlib.pyplot as plt
import collections
from collections import defaultdict
from scipy import stats
import lib
OUT="/Volumes/4 MB/ablation_figures_20260625/group4"; os.makedirs(OUT,exist_ok=True); SCRIPT=__file__
PDF="/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf"
data,_=lib.load_master_plots(); mr={r["Batch Name"]:r for r in data}
def gv(b,c): return (mr.get(b,{}).get(c,"") or "").strip()
def px(b):
    try: return float(gv(b,'Pixel Size (um)') or 0.062)
    except: return 0.062
def nsis(b):
    v=gv(b,'# Sisterless KTs'); return int(v) if v.isdigit() else None
# frame(index)->elapsed t_sec (monitoring, by position)
RD={os.path.basename(os.path.dirname(fj)):os.path.dirname(fj) for fj in glob.glob("/Volumes/4 MB/**/*_frames.json",recursive=True)}
def montimes(b):
    d=RD.get(b)
    if not d: return []
    g=glob.glob(os.path.join(d,"*_frames.json"))
    return [ff.get("t_sec") for ff in json.load(open(g[0])).get("frames",[]) if ff.get("role")=="monitoring"] if g else []
def frame_idx(b,tsec):
    mt=montimes(b)
    if tsec is None or not mt: return None
    ts=[t for t in mt if t is not None]
    if not ts: return None
    return min(range(len(mt)), key=lambda i:abs((mt[i] or 0)-tsec))
# manual sisterless track + plate lines
sis=defaultdict(dict); plate=defaultdict(dict)   # batch -> frame -> (x,y) / [(ax,ay),(bx,by)]
for r in csv.DictReader(open("/Volumes/4 MB/annotations/kt_points.csv")):
    if r.get('label')=='sisterless':
        try: sis[r['batch'].strip()][int(float(r['frame']))]=(float(r['x']),float(r['y']))
        except: pass
for r in csv.DictReader(open("/Volumes/4 MB/annotations/meta_plates.csv")):
    if r.get('label')=='meta_plate':
        try:
            p=json.loads(r.get('points','') or '[]')
            if len(p)>=2: plate[r['batch'].strip()][int(float(r['frame']))]=(p[0],p[-1])
        except: pass
# per-chromosome behavior + length
beh={}; length={}
for r in csv.DictReader(open("/Volumes/4 MB/annotations/CHROMOSOME_MASTER.csv")):
    if r.get('behavior','').strip(): beh[r['batch'].strip()]=r['behavior'].strip()
    if r.get('length_um','').strip(): length[r['batch'].strip()]=float(r['length_um'])
def dist_to_plate(pt, line, ps):
    (ax,ay),(bx,by)=line; x,y=pt
    num=abs((bx-ax)*(ay-y)-(ax-x)*(by-ay)); den=np.hypot(bx-ax,by-ay) or 1.0
    return num/den*ps
def nearest_plate(b,f):
    pl=plate.get(b,{})
    if f in pl: return pl[f]
    if not pl: return None
    nf=min(pl,key=lambda k:abs(k-f)); return pl[nf] if abs(nf-f)<=3 else None

# ---- assemble per-KT trajectories (single-ablation, >=8 frames) ----
KT=[]
for b in sis:
    if nsis(b)!=1: continue
    frames=sorted(sis[b])
    if len(frames)<8: continue
    ps=px(b); ana=frame_idx(b,lib.parse_time(gv(b,'Anaphase Onset (s)'))); meta=frame_idx(b,lib.parse_time(gv(b,'Metaphase Start (s)')))
    traj=[]
    for f in frames:
        ln=nearest_plate(b,f)
        d=dist_to_plate(sis[b][f], ln, ps) if ln else None
        traj.append((f, sis[b][f][0], sis[b][f][1], d))
    KT.append(dict(b=b,traj=traj,frames=frames,ana=ana,meta=meta,beh=beh.get(b),length=length.get(b),ps=ps))
print(f"assembled {len(KT)} single-ablation sisterless trajectories")

# ── USER 2026-08-05: "do we have more data to put on the #move-3 oscillation: near-pole ... plot now?" ──
# Yes, and it was never an annotation gap. The loop above hard-filters `nsis(b) != 1`, so MOVE-3 was
# drawing 8 kinetochores while 17 more — 3-sisterless, congressed or at-plate, all meeting its own frame
# and plate-line requirements — sat excluded. Assemble those separately here rather than relaxing the
# filter above, because every OTHER figure in this script is single-ablation by design.
# Triple goes in as its OWN group, never pooled with single (standing rule).
# CRITICAL, and it is why `nsis != 1` was here in the first place. `sis` is keyed batch -> frame -> (x,y),
# so a cell with SEVERAL sisterless marks on one frame keeps only the last: 398 of 2189 (batch, frame)
# keys carry more than one mark, up to 4, across 25 batches of which 21 are 3-sisterless. Feeding that
# straight in makes a triple cell's "trajectory" jump between different kinetochores frame to frame, which
# inflates apparent oscillation — and produced a spurious "triple oscillate 2.2x more near the pole"
# (p=0.037) that vanished (p=0.71) once the marks were linked properly.
# Separate them geometrically first: nearest-neighbour linking, one track per kinetochore.
_raw3 = collections.defaultdict(list)
for _b, _fm in sis.items():
    if nsis(_b) != 3: continue
    for _f, _xy in _fm.items(): _raw3[_b].append((_f, 0.0, _xy[0], _xy[1]))
KT3 = []
for b, marks in _raw3.items():
    ps = px(b)
    ana = frame_idx(b, lib.parse_time(gv(b, 'Anaphase Onset (s)')))
    meta = frame_idx(b, lib.parse_time(gv(b, 'Metaphase Start (s)')))
    for tr in lib.link_kt_tracks(marks, ps):
        frames = sorted(int(m[0]) for m in tr)
        if len(frames) < 8: continue
        xy = {int(m[0]): (m[2], m[3]) for m in tr}
        traj = []
        for f in frames:
            ln = nearest_plate(b, f)
            traj.append((f, xy[f][0], xy[f][1], dist_to_plate(xy[f], ln, ps) if ln else None))
        KT3.append(dict(b=b, traj=traj, frames=frames, ana=ana, meta=meta, beh=beh.get(b),
                        length=length.get(b), ps=ps))
print(f"assembled {len(KT3)} TRIPLE-ablation sisterless KINETOCHORE tracks (for #MOVE-3)")
withd=[k for k in KT if sum(1 for _,_,_,d in k['traj'] if d is not None)>=6]
print(f"  with >=6 distance-to-plate points: {len(withd)}")
medlen=np.median([k['length'] for k in KT if k['length']]) if any(k['length'] for k in KT) else 5.0
def islong(k): return k['length'] is not None and k['length']>=medlen

# ===================== FIG 1: distance-to-plate trajectories, aligned to anaphase =====================
fig,(axC,axP)=plt.subplots(1,2,figsize=(13,5.3),sharey=True)
BCOL={"at_plate":"#1b7837","congressed":"#2166ac","noncongression":"#762a83"}
for k in withd:
    if k['ana'] is None: continue
    xs=[(f-k['ana'])*20/60 for f,_,_,d in k['traj'] if d is not None]   # min from anaphase (nominal 20s/frame)
    ys=[d for _,_,_,d in k['traj'] if d is not None]
    ax = axP if k['beh']=="noncongression" else axC
    ax.plot(xs,ys,'-',color=BCOL.get(k['beh'],"#999"),alpha=.55,lw=1.3)
for ax,ttl in [(axC,"Congressing / at-plate KTs"),(axP,"Permanent-polar KTs")]:
    ax.axvline(0,color="#b2182b",ls="--",lw=1); ax.text(0.2,ax.get_ylim()[1]*0.9 if ax.get_ylim()[1]>0 else 5,"anaphase",color="#b2182b",fontsize=8)
    ax.set_xlabel("time from anaphase onset (min)"); ax.set_title(ttl,fontsize=10)
axC.set_ylabel("sisterless KT distance to metaphase plate (µm)")
fig.suptitle("#MOVE-1  Sisterless-KT distance-to-plate over time (manual tracks, single-ablation)",fontweight="bold",fontsize=11,x=.01,ha="left")
plt.tight_layout(rect=[0,0,1,0.95]); plt.savefig(f"{OUT}/G4_sisterless_dist_to_plate_traj.png",bbox_inches="tight",dpi=130); plt.savefig(f"{PDF}/G4_sisterless_dist_to_plate_traj.pdf",bbox_inches="tight"); plt.close()
lib.record_plot("G4_sisterless_dist_to_plate_traj",["batch","frame","dist_to_plate","behavior"],
  [[k["b"],f,round(d,4),k.get("beh") or ""] for k in withd for f,_,_,d in k["traj"] if d is not None],{"source":"manual sisterless+plate","N":len(withd)},SCRIPT,"Sisterless distance-to-plate trajectories", fig=fig)

# ===================== FIG 2: oscillation amplitude vs length (polar phase) =====================
# oscillation = std of the DETRENDED distance-to-plate (removes the slow congression drift) over the KT's track.
def oscillation(traj):
    d=np.array([x for _,_,_,x in traj if x is not None])
    if len(d)<6: return None
    t=np.arange(len(d)); m,b=np.polyfit(t,d,1); detr=d-(m*t+b)
    return float(np.std(detr))
osc=[(k['length'],oscillation(k['traj']),k['beh']) for k in withd if k['length'] and oscillation(k['traj']) is not None]
fig,ax=plt.subplots(figsize=(7,5.2))
for bh,col,lab in [("noncongression","#762a83","stayed polar"),("congressed","#2166ac","congressed"),("at_plate","#1b7837","at plate")]:
    xs=[L for L,o,b in osc if b==bh]; ys=[o for L,o,b in osc if b==bh]
    if xs: ax.scatter(xs,ys,s=42,color=col,alpha=.8,edgecolor="white",lw=.4,label=f"{lab} (n={len(xs)})")
X=[L for L,o,b in osc]; Y=[o for L,o,b in osc]
if len(X)>=4:
    m,bb=np.polyfit(X,Y,1); xr=np.linspace(min(X),max(X),20); ax.plot(xr,m*xr+bb,"-",color="#222",lw=1.6)
    rho,p=stats.spearmanr(X,Y)
    ax.set_title(f"#MOVE-2  Oscillation amplitude vs chromosome length\nSpearman ρ={rho:.2f}, p={p:.2g}, N={len(X)}",fontsize=10)
ax.set_xlabel("chromosome length (µm)"); ax.set_ylabel("oscillation amplitude (µm, SD of detrended dist-to-plate)"); ax.legend(fontsize=8)
plt.tight_layout(); plt.savefig(f"{OUT}/G4_sisterless_oscillation_vs_length.png",bbox_inches="tight",dpi=130); plt.savefig(f"{PDF}/G4_sisterless_oscillation_vs_length.pdf",bbox_inches="tight"); plt.close()
lib.record_plot("G4_sisterless_oscillation_vs_length",["length","oscillation","behavior"],[],{"source":"manual tracks","N":len(X)},SCRIPT,"Oscillation vs length", fig=fig)

# ===================== FIG 3 (#MOVE-3): oscillation at-pole vs approaching-plate =====================
# For congressing KTs: split the track at its midpoint; compare oscillation in the early (at/near pole)
# half against the late (approaching plate) half. Paired within a kinetochore, so each KT is its own
# control and cell-to-cell differences cancel.
# USER 2026-08-05: now split 1- vs 3-sisterless. Previously 1-sisterless only (n=8).
def _phase_osc(klist):
    early, late = [], []
    for k in klist:
        if k['beh'] not in ("congressed", "at_plate"): continue
        d = [(f, x) for f, _, _, x in k['traj'] if x is not None]
        if len(d) < 10: continue
        half = len(d) // 2
        def seg(sq):
            v = np.array([x for _, x in sq]); t = np.arange(len(v))
            m, b_ = np.polyfit(t, v, 1); return float(np.std(v - (m * t + b_)))
        early.append(seg(d[:half])); late.append(seg(d[half:]))
    return early, late

_G3 = [("1-sisterless", KT, "#2166ac"), ("3-sisterless", KT3, "#762a83")]
fig, ax = plt.subplots(figsize=(8.4, 5.4))
_pos = 0.0; _seed = 0; _xt = []; _xl = []; _m3rows = []; _m3stats = {}
for _lab, _kl, _col in _G3:
    early, late = _phase_osc(_kl)
    if len(early) < 3:
        print(f"  #MOVE-3 {_lab}: only {len(early)} kinetochores, not drawn"); continue
    for vals, sub, shade in ((early, "early (near pole)", 0.45), (late, "late (approaching)", 0.20)):
        ax.boxplot([vals], positions=[_pos], widths=.55, patch_artist=True, showfliers=False,
                   boxprops=dict(facecolor=_col, alpha=shade, edgecolor=_col),
                   medianprops=dict(color=_col, lw=2.2))
        jit = (np.random.RandomState(_seed).rand(len(vals)) - .5) * .25   # int seed: _pos is a float
        _seed += 1
        ax.scatter(np.full(len(vals), _pos) + jit, vals, s=lib.VIOLIN_DOT_S, color=_col, alpha=.8,
                   edgecolor="white", lw=.4, zorder=3)
        _xt.append(_pos); _xl.append(f"{_lab}\n{sub}"); _pos += 1
    # paired lines: each kinetochore is its own control
    for e, l in zip(early, late):
        ax.plot([_pos - 2, _pos - 1], [e, l], "-", color=_col, lw=0.7, alpha=0.35, zorder=1)
    u = stats.wilcoxon(early, late) if len(early) >= 6 else None
    _p = u.pvalue if u else float("nan")
    ax.text(_pos - 1.5, max(max(early), max(late)) * 1.03,
            f"n={len(early)} KTs\nWilcoxon p={_p:.3g}" if u else f"n={len(early)} KTs",
            ha="center", va="bottom", fontsize=8, color=_col)
    _m3stats[_lab] = {"n_kt": len(early), "median_early": round(float(np.median(early)), 4),
                      "median_late": round(float(np.median(late)), 4), "wilcoxon_p": float(_p)}
    _m3rows += [[_lab, "early_near_pole", round(float(v), 5)] for v in early]
    _m3rows += [[_lab, "late_approaching", round(float(v), 5)] for v in late]
    _pos += 0.6
# the per-cohort "n / Wilcoxon" captions sit above each group's tallest point and ran into the title
_yl = ax.get_ylim(); ax.set_ylim(_yl[0], _yl[1] + (_yl[1] - _yl[0]) * 0.16)
ax.set_xticks(_xt); ax.set_xticklabels(_xl, fontsize=8)
ax.set_ylabel("oscillation amplitude (µm, SD of detrended distance-to-plate)")
ax.set_title("#MOVE-3  Oscillation: near-pole vs approaching-plate (congressing KTs)\n"
             "split 1- vs 3-sisterless; thin lines pair each kinetochore with itself",
             loc="left", fontweight="bold", fontsize=10)
ax.text(0.0, -0.15, "Previously 1-sisterless only: the builder filtered `nsis != 1` because a triple cell's "
        "marks share one frame key and collapse into a single mixed\ntrack. They are now separated by "
        "nearest-neighbour linking, one track per kinetochore. Each track is split at its own midpoint, "
        "so the comparison is paired.",
        transform=ax.transAxes, fontsize=7, color="#555", va="top")
plt.tight_layout()
plt.savefig(f"{OUT}/G4_sisterless_oscillation_phases.png", bbox_inches="tight", dpi=130)
plt.savefig(f"{PDF}/G4_sisterless_oscillation_phases.pdf", bbox_inches="tight")
plt.close()
lib.record_plot("G4_sisterless_oscillation_phases", ["cohort", "phase", "oscillation_um"], _m3rows,
                _m3stats, SCRIPT, "#MOVE-3 oscillation near-pole vs approaching-plate, 1 vs 3 sisterless")
print(f"  #MOVE-3: {_m3stats}")

# ===================== FIG 4: total path & net displacement vs behavior/length =====================
def path_net(k):
    pts=[(x,y) for _,x,y,_ in k['traj']]; P=np.array(pts,float)*k['ps']
    path=float(np.sum(np.hypot(np.diff(P[:,0]),np.diff(P[:,1])))); net=float(np.hypot(*(P[-1]-P[0])))
    return path,net
fig,(axA,axB)=plt.subplots(1,2,figsize=(12.4,5.2))
CATS=[("at_plate","at plate","#1b7837"),("congressed","congressed","#2166ac"),("noncongression","stayed polar","#762a83")]
g=defaultdict(list)
for k in withd:
    if k['beh']: g[k['beh']].append(path_net(k)[0])
for i,(bh,lab,col) in enumerate(CATS):
    v=g[bh]
    if not v: continue
    x=i+1; axA.boxplot([v],positions=[x],widths=.55,patch_artist=True,boxprops=dict(facecolor=col,alpha=.25,edgecolor=col),medianprops=dict(color=col,lw=2),showfliers=False)
    jit=(np.random.RandomState(i).rand(len(v))-.5)*.28; axA.scatter(np.full(len(v),x)+jit,v,s=26,color=col,alpha=.7,edgecolor="white",lw=.3)
axA.set_xticks([1,2,3]); axA.set_xticklabels([c[1] for c in CATS],fontsize=9); axA.set_ylabel("total path length (µm)"); axA.set_title("Total movement by behavior",fontsize=10)
# path vs length
pl=[(k['length'],path_net(k)[0]) for k in withd if k['length']]
X=[a for a,_ in pl]; Y=[b for _,b in pl]
axB.scatter(X,Y,s=40,color="#2166ac",alpha=.8,edgecolor="white",lw=.4)
if len(X)>=4:
    m,bb=np.polyfit(X,Y,1); xr=np.linspace(min(X),max(X),20); axB.plot(xr,m*xr+bb,"-",color="#222",lw=1.6); rho,p=stats.spearmanr(X,Y)
    axB.set_title(f"Total movement vs length\nρ={rho:.2f}, p={p:.2g}, N={len(X)}",fontsize=10)
axB.set_xlabel("chromosome length (µm)"); axB.set_ylabel("total path length (µm)")
fig.suptitle("#MOVE-4  Sisterless-KT movement magnitude (single-ablation, manual tracks)",fontweight="bold",fontsize=11,x=.01,ha="left")
plt.tight_layout(rect=[0,0,1,0.95]); plt.savefig(f"{OUT}/G4_sisterless_movement_metrics.png",bbox_inches="tight",dpi=130); plt.savefig(f"{PDF}/G4_sisterless_movement_metrics.pdf",bbox_inches="tight"); plt.close()
# 2026-08-03: was recording ZERO rows while advertising N - provenance unverifiable. Write real rows.
lib.record_plot("G4_sisterless_movement_metrics",["batch","behavior","length_um","n_points"],
  [[k["b"],k.get("beh") or "",k.get("length") or "",sum(1 for _,_,_,d in k["traj"] if d is not None)] for k in withd],{"source":"manual tracks","N":len(withd)},SCRIPT,"Movement magnitude", fig=fig)

print(f"\nBUILT 4 movement figures (N={len(withd)} trajectories, median length {medlen:.1f}um)")
print("BLOCKED (noted for user): per-KT SHAPE change (marks are points, no area/aspect); per-KT FLUOR over time "
      "(manual marks carry no intensity — see existing G4_kt_intensity/G4_fluor); paired-KT Cdc20 (needs paired-KT fluor tracks).")
