"""Item 22 — quantify the 'many negative values' problem as a function of measurement radius.
Replicates the complete-ablation KT measurement (targeted & sister, background-SUBTRACTED total
intensity sum) but evaluates disk_sum at radii r=3..9 in a SINGLE pass per movie frame, then tallies
the fraction of measurements that go negative at each radius. Negatives = same-size cytosol disk sum
exceeds the KT disk sum (background>signal), which is what we expect to collapse as the radius shrinks
onto the bright KT core. Output -> r_sweep dir (CSV + plot). Reads movies once; nothing local."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, glob, json, os, numpy as np, cv2, matplotlib.pyplot as plt
from collections import defaultdict
import lib
lib.apply_style()
OUTDIR="/Volumes/4 MB/ablation_plots/r_sweep_20260627"; os.makedirs(OUTDIR,exist_ok=True)
RADII=[3,4,5,6,7,8,9]; NFRAMES=10
FRAP_BATCHES={  # same exclusion the ablation-intensity plot uses (handled in the FRAP plot)
 "20250501 ptk_yfpcdc20_12","20250711 double ablation_18","20250711 double ablation_9",
 "20250806 single_ablation_17","20250925 triple_ablation_23","20250925 triple_ablation_5",
 "20251021 coverslip3_10","20251021 no_manipulation_5","20251030 metaphase_ablation_3"}

rows=list(csv.reader(open("/Volumes/4 MB/annotations/kt_points.csv"))); ix={c:i for i,c in enumerate(rows[0])}
mk=defaultdict(lambda: defaultdict(dict)); cyto=defaultdict(list)
for r in rows[1:]:
    b=r[ix['batch']].strip(); lab=r[ix['label']].strip()
    if lib.is_mad1(b): continue
    if lib.is_misplaced_id(r[ix['id']]): continue
    if b in FRAP_BATCHES: continue
    try: f=int(r[ix['frame']]); t=float(r[ix['t_sec']]); x=float(r[ix['x']]); y=float(r[ix['y']])
    except: continue
    if lab=='pre_abl': mk[b][f]['tgt']=(x,y,t)
    elif lab=='pre_abl_pair': mk[b][f]['sis']=(x,y,t)
    elif lab=='cytosol_bg': cyto[b].append((f,t,x,y))

# per radius: count of (tg<0) + (ss<0), and totals
neg={R:0 for R in RADII}; tot={R:0 for R in RADII}
# also keep per-KT-kind so we can see targeted (ablated, dim) vs sister (intact, bright)
negk={('tgt',R):0 for R in RADII}; negk.update({('sis',R):0 for R in RADII})
totk={('tgt',R):0 for R in RADII}; totk.update({('sis',R):0 for R in RADII})
ncell=0; nmeas=0
for b in sorted(mk):
    pairs=[(F,m) for F,m in mk[b].items() if 'tgt' in m and 'sis' in m]
    if not pairs or b not in cyto: continue
    ft=lib.FluorTif(b,'ablation')                                  # 16-bit cropped fluor TIF, not the 8-bit MP4
    if not ft.ok(): continue
    ablts=ft.ts; N=len(ft); used=False
    for F,m in pairs:
        tx,ty,tF=m['tgt']; sx,sy,_=m['sis']
        cf,ct,cx,cy=min(cyto[b],key=lambda c:abs(c[0]-F))          # marked cytosol background point
        fr0=ft.pos_of_frame(F)                                    # marking frame by ground-truth index, not t_sec
        if fr0 is None: continue
        g0=ft.plane_by_pos(fr0)
        if g0 is None: continue
        txs,tys=lib.snap_to_peak(g0,tx,ty); sxs,sys=lib.snap_to_peak(g0,sx,sy)  # snap intact KTs once (pre)
        meas=[fr0]+[fr0+k for k in range(2,2+NFRAMES) if fr0+k<N]   # skip flash (fr0+1)
        for fr in meas:
            g=ft.plane_by_pos(fr)                                  # 16-bit plane
            if g is None: continue
            for R in RADII:
                cval=lib.disk_sum(g,cx,cy,R)                       # marked cytosol bg (per-frame, no snap)
                if cval is None: continue
                tg=lib.disk_sum(g,txs,tys,R)-cval; ss=lib.disk_sum(g,sxs,sys,R)-cval
                tot[R]+=2; totk[('tgt',R)]+=1; totk[('sis',R)]+=1
                if tg<0: neg[R]+=1; negk[('tgt',R)]+=1
                if ss<0: neg[R]+=1; negk[('sis',R)]+=1
                if R==9: nmeas+=2
        used=True
    ft.close()
    if used: ncell+=1

# ---- CSV ----
csvp=f"{OUTDIR}/negative_fraction_by_radius_TIF.csv"
with open(csvp,"w",newline="") as f:
    w=csv.writer(f); w.writerow(["radius_px","radius_um","n_measurements","n_negative","negative_fraction",
                                 "tgt_neg_frac","sis_neg_frac"])
    for R in RADII:
        nf=neg[R]/tot[R] if tot[R] else 0
        tf=negk[('tgt',R)]/totk[('tgt',R)] if totk[('tgt',R)] else 0
        sf=negk[('sis',R)]/totk[('sis',R)] if totk[('sis',R)] else 0
        w.writerow([R,round(R*0.062,3),tot[R],neg[R],round(nf,4),round(tf,4),round(sf,4)])

# ---- plot ----
fig,ax=plt.subplots(figsize=(7.2,5))
fr=[neg[R]/tot[R]*100 if tot[R] else 0 for R in RADII]
tfr=[negk[('tgt',R)]/totk[('tgt',R)]*100 if totk[('tgt',R)] else 0 for R in RADII]
sfr=[negk[('sis',R)]/totk[('sis',R)]*100 if totk[('sis',R)] else 0 for R in RADII]
ax.plot(RADII,fr,"-o",color="#222",lw=2.4,ms=7,label="all measurements")
ax.plot(RADII,tfr,"-o",color="#d62728",lw=1.6,ms=5,label="targeted (ablated) KT")
ax.plot(RADII,sfr,"-s",color="#1f77b4",lw=1.6,ms=5,label="sister (intact) KT")
ax.axvline(5,color="#2a9d3a",ls="--",lw=1.4); ax.text(5.08,ax.get_ylim()[1]*.96,"r=5 (chosen)",color="#2a9d3a",fontsize=8,va="top")
ax.axvline(9,color="#999",ls=":",lw=1.2); ax.text(8.92,ax.get_ylim()[1]*.96,"r=9 (old)",color="#777",fontsize=8,va="top",ha="right")
for R,v in zip(RADII,fr): ax.annotate(f"{v:.0f}%",(R,v),textcoords="offset points",xytext=(0,7),ha="center",fontsize=7)
ax.set_xlabel("measurement disk radius (px)  [0.062 µm/px]"); ax.set_ylabel("% of KT measurements that go negative\n(cytosol Σ > KT Σ)")
ax.set_title(f"Item 22 · Negative-fraction vs radius — measured on 16-bit TIF\n{nmeas} measurements, {ncell} cells",loc="left",fontweight="bold",fontsize=10.5)
ax.legend(fontsize=8); ax.set_ylim(bottom=0)
plt.tight_layout(); plt.savefig(f"{OUTDIR}/negative_fraction_by_radius_TIF.png",bbox_inches="tight"); plt.close()
print(f"negatives-by-radius: {ncell} cells, {nmeas} measurements")
for R in RADII: print(f"  r={R}: {neg[R]/tot[R]*100:.1f}% negative ({neg[R]}/{tot[R]})")
print(f"CSV -> {csvp}")
