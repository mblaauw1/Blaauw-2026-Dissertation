"""Ground-truth cdc20 polar-vs-plate: pick each annotation's TIF plane by correlating the ACTUAL annotation-movie
frame against TIF positions near both candidates (frame field & t_sec position). This sidesteps the
batch-dependent frame/t_sec inconsistency. Efficient: one movie handle per batch."""
import sys; sys.path.insert(0,".")
import lib, glob, os, cv2, numpy as np, csv
from collections import defaultdict
from scipy import stats
lib._fcrop_index()
kt=list(csv.reader(open("/Volumes/4 MB/annotations/kt_points.csv"))); kx={c:i for i,c in enumerate(kt[0])}
pts=defaultdict(lambda: defaultdict(list))
for r in kt[1:]:
    b=r[kx['batch']].strip()
    if lib.is_mad1(b) or lib.is_misplaced_id(r[kx['id']]): continue
    try: pts[b][r[kx['label']].strip()].append((int(r[kx['frame']]),float(r[kx['t_sec']]),float(r[kx['x']]),float(r[kx['y']]),r[kx['video_file']]))
    except: pass
def find_mov(b,vf):
    g=glob.glob(f"/Volumes/4 MB/**/*{b}*/{os.path.basename(vf)}",recursive=True)
    return g[0] if g else None
def measure(b,label,role):
    P=pts[b].get(label,[]); bg=pts[b].get("cytosol_bg",[])
    if not P or not bg: return [],0,0
    ft=lib.FluorTif(b,role)
    if not ft.ok(): return [],0,0
    caps={}
    def cap_for(vf):
        k=os.path.basename(vf)
        if k not in caps:
            m=find_mov(b,vf); caps[k]=cv2.VideoCapture(m) if m else None
        return caps[k]
    out=[]; nfix=0
    for (f,t,x,y,vf) in P:
        i_t=int(np.argmin(np.abs(ft.ts-t)))
        cands=set()
        for c in (f,i_t): cands|={c-2,c-1,c,c+1,c+2}
        cands={c for c in cands if 0<=c<len(ft.ts)}
        cap=cap_for(vf); p=f if 0<=f<len(ft.ts) else i_t
        if cap is not None:
            # OFF-BY-ONE FIX (2026-07-28): annotation frames are ONE-based (make_annotation_html.py
            # writes `... + 1`), OpenCV frame indices are ZERO-based, so reading index f grabbed the
            # frame AFTER the annotated one. Correlating that against the TIF shifted BOTH sides
            # equally and so 'confirmed' the wrong alignment.
            cap.set(cv2.CAP_PROP_POS_FRAMES,max(0,f-1)); ok,fr=cap.read()
            if ok:
                am=cv2.cvtColor(fr,cv2.COLOR_BGR2GRAY).astype(float); best=None
                for c in sorted(cands):
                    g=ft.plane_by_pos(c).astype(float)
                    if g.shape!=am.shape: g=cv2.resize(g,(am.shape[1],am.shape[0]))
                    cc=float(np.corrcoef(am.ravel(),g.ravel())[0,1])
                    if best is None or cc>best[1]: best=(c,cc)
                p=best[0]
                if p!=f: nfix+=1
        g=ft.plane_by_pos(p)
        if g is None: continue
        bf,bt,bx,by,_=min(bg,key=lambda c:abs(c[0]-f)); cv0=lib.disk_sum(g,bx,by,8)
        sx,sy=lib.snap_to_peak(g,x,y); v=lib.disk_sum(g,sx,sy,8)-cv0
        if v<1e6: out.append(v)
    for c in caps.values():
        if c is not None: c.release()
    ft.close(); return out,nfix,len(P)
polar=[];plate=[]; pol_fix=plt_fix=pol_tot=plt_tot=0
for bi,b in enumerate(pts):
    o,nf,nt=measure(b,"polar","monitoring"); polar+=[v for v in o if v>0]; pol_fix+=nf; pol_tot+=nt
    o,nf,nt=measure(b,"pre_abl","ablation"); plate+=[v for v in o if v>0]; plt_fix+=nf; plt_tot+=nt
    if bi%20==0: print(f"...{bi}/{len(pts)} batches",flush=True)
polar=np.array(polar);plate=np.array(plate)
p=stats.mannwhitneyu(polar,plate,alternative="greater").pvalue
print("\n=== GROUND-TRUTH (annotation-movie correlation) cdc20 ===")
print(f"polar  N={len(polar)} med={np.median(polar):.0f}")
print(f"plate  N={len(plate)} med={np.median(plate):.0f}")
print(f"Mann-Whitney polar>plate p={p:.3g}")
print(f"plane corrected away from frame-field: polar {pol_fix}/{pol_tot}, plate {plt_fix}/{plt_tot}")
print("GT_DONE")
