"""Is a suspicious annotation a PLACEMENT BUG (my frame/coord mapping) or a genuinely BAD CLICK?
For the worst-offset intact-KT clicks (+ a few well-placed controls), show the MP4 RENDER frame the user
annotated on, beside the 16-bit TIF plane I measure on — SAME frame position, SAME ROI coords. Mark the raw
click (white +) and the snapped point (cyan +). If a KT is visible in the MP4 but not the TIF -> mapping bug.
If neither shows a KT -> the click is genuinely misplaced (and the screen should have caught it)."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, numpy as np, cv2, matplotlib.pyplot as plt
from collections import defaultdict
import lib
OUT="/Volumes/4 MB/ablation_figures_20260625"
SCREEN={"pre_abl","pre_abl_pair","post_abl_pair","polar","sisterless","paired_kt"}
mispl=lib.misplaced_ids()
rows=list(csv.reader(open("/Volumes/4 MB/annotations/kt_points.csv"))); ix={c:i for i,c in enumerate(rows[0])}
byb=defaultdict(list)
for r in rows[1:]:
    b=r[ix['batch']].strip(); lab=r[ix['label']].strip()
    if lab not in SCREEN or lib.is_mad1(b): continue
    try: byb[b].append((r[ix['id']],lab,r[ix['frame']],float(r[ix['t_sec']]),float(r[ix['x']]),float(r[ix['y']])))
    except: pass

def mp4_path(b,role):
    fp=lib._FCROP_IDX.get(b);  return fp.replace("_Fluor_Cropped.tif",f"_Fluor_{role.capitalize()}.mp4") if fp else None

recs=[]   # (off, mp4frame, tifplane, click, snap, mp4img, tifimg, meta)
for b in byb:
    for role in ("ablation","monitoring"):
        ft=lib.FluorTif(b,role)
        if not ft.ok(): ft.close(); continue
        import os
        mp=mp4_path(b,role); cap=cv2.VideoCapture(mp) if mp and os.path.isfile(mp) else None
        for (aid,lab,frame,t,x,y) in byb[b]:
            i=ft.pos_of_frame(frame)            # ground-truth frame index (not t_sec)
            if i is None: continue
            g=ft.plane_by_pos(i)
            if g is None: continue
            sx,sy=lib.snap_to_peak(g,x,y); off=float(np.hypot(sx-x,sy-y))
            mimg=None
            if cap is not None:
                cap.set(cv2.CAP_PROP_POS_FRAMES,i); okr,fr=cap.read()
                if okr: mimg=cv2.cvtColor(fr,cv2.COLOR_BGR2GRAY)
            recs.append((off,i,ft._idx[i],(x,y),(sx,sy),mimg,g.copy(),
                         (b[:20],aid,lab,frame,aid in mispl)))
        if cap is not None: cap.release()
        ft.close(); break   # first role that validates

# pick the 9 worst-offset (suspicious) + 6 smallest-offset (controls) that have an MP4 to compare
recs=[r for r in recs if r[5] is not None]
recs.sort(key=lambda r:-r[0])
pick=recs[:9]+recs[-6:]
def crop(img,x,y,W=18):
    h,w=img.shape; x0,y0=max(0,int(x)-W),max(0,int(y)-W); c=img[y0:min(h,int(y)+W),x0:min(w,int(x)+W)].astype(float)
    lo,hi=np.percentile(c,[12,99.7]); return np.clip((c-lo)/(hi-lo+1e-6),0,1),x-x0,y-y0
fig,axes=plt.subplots(len(pick),2,figsize=(6,2.5*len(pick)))
for k,(off,mf,tp,(x,y),(sx,sy),mimg,timg,(bb,aid,lab,frame,flagged)) in enumerate(pick):
    for j,(img,name) in enumerate([(mimg,"MP4 render (you clicked here)"),(timg,"TIF plane (measured here)")]):
        a=axes[k][j]; cimg,cx,cy=crop(img,x,y); a.imshow(cimg,cmap="gray",interpolation="nearest")
        a.plot(cx,cy,"+",color="white",ms=11,mew=1.6)
        a.plot(cx+(sx-x),cy+(sy-y),"+",color="#37c8ff",ms=11,mew=1.6)
        a.add_patch(plt.Circle((cx+(sx-x),cy+(sy-y)),8,fill=False,color="#37ff5a",lw=1))
        a.set_xticks([]); a.set_yticks([])
        if j==0: a.set_ylabel(f"{bb}\nid{aid} {lab} f{frame}\noff {off:.0f}px"+("  FLAGGED" if flagged else ""),fontsize=6,color=("#c00" if flagged else "#000"))
        if k==0: a.set_title(name,fontsize=8)
fig.suptitle("Placement audit · WHITE + = your click · CYAN + = snapped · top 9 = worst offsets, bottom 6 = controls",fontsize=9,y=1.001)
plt.tight_layout(); plt.savefig(f"{OUT}/_PLACEMENT_AUDIT.png",bbox_inches="tight",dpi=140); plt.close()
print("worst-offset clicks (suspicious):")
for off,mf,tp,_,_,_,_,(bb,aid,lab,frame,flg) in recs[:12]:
    print(f"  off {off:4.1f}px  {bb:22s} id{aid:>4} {lab:14s} f{frame}  mp4_frame={mf} tif_page={tp}  {'FLAGGED-excluded' if flg else 'kept'}")
print(f"-> {OUT}/_PLACEMENT_AUDIT.png")
