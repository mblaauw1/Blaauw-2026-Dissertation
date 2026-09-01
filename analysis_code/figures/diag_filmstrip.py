"""Filmstrip for the two dramatic cases: show frames i-6..i+2 (i = my t_sec-mapped frame, boxed) with the
click (white +) fixed at (x,y). If the KT sits at the click in MY frame -> mapping OK (click maybe just dim).
If the KT is clearly at the click in an EARLIER frame and gone in mine -> a frame-offset bug."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, numpy as np, matplotlib.pyplot as plt
import lib
OUT="/Volumes/4 MB/ablation_figures_20260625"
TARGETS=[("20250409 ptk_yfpcdc20_6","200"),("20260416 single ablation_? ","48")]  # match by id within batch prefix
rows=list(csv.reader(open("/Volumes/4 MB/annotations/kt_points.csv"))); ix={c:i for i,c in enumerate(rows[0])}
want={}
for r in rows[1:]:
    b=r[ix['batch']].strip()
    for pref,aid in TARGETS:
        if b.startswith(pref.strip().split("_?")[0]) and r[ix['id']]==aid:
            want[(b,aid)]=(float(r[ix['t_sec']]),float(r[ix['x']]),float(r[ix['y']]),r[ix['label']],r[ix['frame']])
print("matched:",list(want))
if not want:
    # TARGETS are hand-picked (batch prefix, annotation id) probes from the 2026-06-27 frame-offset
    # investigation; one entry is still a placeholder ("20260416 single ablation_? "). When nothing
    # matches, plt.subplots(0,9) raises "Number of rows must be a positive integer" - so exit cleanly
    # instead. This is a diagnostic with no deck figure; _FRAME_FILMSTRIP.png is placed in neither .ai.
    print("no TARGETS matched in kt_points.csv - nothing to draw. "
          "Edit TARGETS (batch prefix, annotation id) to probe a different mark.")
    sys.exit(0)
fig,axes=plt.subplots(len(want),9,figsize=(18,2.4*max(len(want),1)),squeeze=False)
for ri,((b,aid),(t,x,y,lab,frame)) in enumerate(want.items()):
    ft=None
    for role in ("monitoring","ablation"):
        f=lib.FluorTif(b,role)
        if f.ok(): ft=f; break
        f.close()
    if ft is None: continue
    i=int(np.argmin(np.abs(ft.ts-t)))
    for c,k in enumerate(range(-6,3)):
        a=axes[ri][c]; g=ft.plane_by_pos(i+k)
        if g is None: a.axis("off"); continue
        W=20;h,w=g.shape;x0,y0=max(0,int(x)-W),max(0,int(y)-W);cr=g[y0:min(h,int(y)+W),x0:min(w,int(x)+W)].astype(float)
        lo,hi=np.percentile(cr,[12,99.8]); a.imshow(np.clip((cr-lo)/(hi-lo+1e-6),0,1),cmap="gray",interpolation="nearest")
        a.plot(x-x0,y-y0,"+",color="#ff3b3b",ms=12,mew=1.8)
        a.set_xticks([]);a.set_yticks([])
        a.set_title(f"Δf={k:+d}"+(" (MINE)" if k==0 else ""),fontsize=8,color=("#d00" if k==0 else "#000"))
        if c==0: a.set_ylabel(f"{b[:16]}\nid{aid} {lab} f{frame}",fontsize=7)
    ft.close()
fig.suptitle("Filmstrip · RED + = the click (fixed) · does the KT sit at the click in MY frame (Δf=0) or an earlier one?",fontsize=10)
plt.tight_layout(); plt.savefig(f"{OUT}/_FRAME_FILMSTRIP.png",bbox_inches="tight",dpi=140); plt.close()
print(f"-> {OUT}/_FRAME_FILMSTRIP.png")
