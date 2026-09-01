"""Build FRAME_CALIBRATION.csv: ground-truth (batch,role,frame)->corrected TIF position.
The annotation `frame`->TIF-position offset is batch-dependent (frame right for most monitoring, off by
1-2 or 31-55 for some ablation). For each UNIQUE (batch, video_file, frame) used by an annotation/outline,
read the real annotation-movie frame and correlate it against TIF positions near {frame, t_sec-pos}±3; the
best-correlating position is the truth. lib.plane_by_frame then consults this table. Run once; re-run if
annotations change."""
import sys; sys.path.insert(0,".")
import lib, glob, os, cv2, numpy as np, csv
from collections import defaultdict
lib._fcrop_index()
ANN="/Volumes/4 MB/annotations"
def role_of(vf):
    n=os.path.basename(vf).lower()
    return "ablation" if ("abl" in n and "mon" not in n) else "monitoring"
# collect unique (batch, video_file, frame, a representative t_sec)
need=defaultdict(dict)   # (batch,video_file) -> {frame: t_sec}
for fn in (f"{ANN}/kt_points.csv",f"{ANN}/cell_outlines.csv"):
    if not os.path.isfile(fn): continue
    for r in csv.DictReader(open(fn)):
        b=r["batch"].strip(); vf=r.get("video_file","").strip()
        if not vf or lib.is_mad1(b): continue
        try: fr=int(r["frame"]); t=float(r["t_sec"])
        except (KeyError,ValueError): continue
        need[(b,vf)].setdefault(fr,t)
def find_mov(b,vf):
    g=glob.glob(f"/Volumes/4 MB/**/*{b}*/{os.path.basename(vf)}",recursive=True)
    return g[0] if g else None
# CONVENTION MARKER (2026-07-28). corrected_pos in THIS file is a true 0-based TIF page, because the
# movie is now read at cv2 index fr-1 (annotation frames are 1-based). The pre-2026-07-28 table was built
# without that correction, so its positions were one too high; lib.pos_of_frame reads this column to know
# which semantics apply instead of assuming.
CONVENTION="onebased_corrected_20260728"

rows=[]; nfix=0; nmiss=0; ntot=0
for bi,((b,vf),frmap) in enumerate(sorted(need.items())):
    role=role_of(vf); ft=lib.FluorTif(b,role)
    if not ft.ok(): ft.close(); nmiss+=len(frmap); ntot+=len(frmap); continue
    mov=find_mov(b,vf); cap=cv2.VideoCapture(mov) if mov else None
    for fr,t in sorted(frmap.items()):
        ntot+=1
        i_t=int(np.argmin(np.abs(ft.ts-t)))
        # fallback when no correlation match is found: 1-based annotation frame -> 0-based TIF page
        pos=max(0,min(fr-1 if fr>0 else fr,len(ft.ts)-1)); corr=-1.0; method="frame(raw-1)"
        if cap is not None and 0<=fr:
            # OFF-BY-ONE FIX (2026-07-28): `fr` is a ONE-based annotation frame, OpenCV is ZERO-based.
            # Reading index fr grabbed the NEXT frame, and because plane_by_pos was compared against it
            # the correlation matched a page that was also one late - which is why 95% of the resulting
            # rows said 'corrected_pos == frame' and the table silently endorsed the bug.
            cap.set(cv2.CAP_PROP_POS_FRAMES,max(0,fr-1)); ok,im=cap.read()
            if ok:
                am=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY).astype(float)
                cands=set()
                for c in (fr,i_t):
                    for d in range(-3,4): cands.add(c+d)
                cands={c for c in cands if 0<=c<len(ft.ts)}
                best=None
                for c in sorted(cands):
                    g=ft.plane_by_pos(c).astype(float)
                    if g.shape!=am.shape: g=cv2.resize(g,(am.shape[1],am.shape[0]))
                    cc=float(np.corrcoef(am.ravel(),g.ravel())[0,1])
                    if best is None or cc>best[1]: best=(c,cc)
                if best and best[1]>0.25:           # trust only a real match
                    pos,corr,method=best[0],best[1],"corr"
                    if pos!=max(0,min(fr-1 if fr>0 else fr,len(ft.ts)-1)): nfix+=1
        rows.append([b,role,fr,pos,round(corr,3),method,CONVENTION])
    if cap is not None: cap.release()
    ft.close()
    if bi%30==0: print(f"...{bi}/{len(need)} (batch,movie) groups",flush=True)
with open(f"{ANN}/FRAME_CALIBRATION.csv","w",newline="") as f:
    w=csv.writer(f); w.writerow(["batch","role","frame","corrected_pos","corr","method","convention"])
    w.writerows(rows)
print(f"\ncalibration: {len(rows)} (batch,role,frame) entries; corrected-away-from-raw-frame {nfix}; "
      f"movie/TIF missing (raw fallback) {nmiss}/{ntot}")
print(f"-> {ANN}/FRAME_CALIBRATION.csv")
print("CALIB_DONE")
