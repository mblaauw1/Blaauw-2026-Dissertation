"""Z-scan timestrips (2026-07-11, user): for Z-stack batches (frames.json = all-same-t_sec z-slices), render
(a) a MIP panel + (b) a strip of the z-SLICES (slices, not timepoints), labeled 'z-stack'. Fluor-only, square
crop + real-pixel scalebar reused from the timestrip method. Also uses the CORRECT fluor label by Cell Type."""
import os, sys, json, time, numpy as np, cv2
sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
SRC="/Volumes/4 MB/ablation_figures_20260625/group_timestrips.py"
src=open(SRC).read(); cut=src.index("chosen={}; ALIGNED_STATUS={}")
G={"__name__":"gts_z","__file__":SRC}; exec(compile(src[:cut],SRC,"exec"),G)
movie=G["movie"]; render_dir=G["render_dir"]; ps=G["ps"]; square_crop=G["square_crop"]; ts_render=G["ts_render"]; mr=G["mr"]

def fluor_label(b):
    ct=(mr.get(b,{}).get("Cell Type","") or "").lower()
    return "eYFP-Cdc20" if "cdc20" in ct else "eYFP-Mad1"

def read_all_fluor(b):
    """All fluor monitoring frames (the z-slices) as a list of BGR arrays, in z order."""
    m=movie(b,"Fluor","Monitoring")
    if not m: return None
    cap,ts=m; n=int(cap.get(7)); frames=[]
    for i in range(n):
        cap.set(cv2.CAP_PROP_POS_FRAMES,i); ok,fr=cap.read()
        if ok and fr is not None: frames.append(fr)
    cap.release()
    return frames if frames else None

def render_zscan(b, out_prefix, n_slices=6):
    frames=read_all_fluor(b)
    if not frames: return False
    pxs=ps(b); crop=square_crop(b)
    def cp(fr): return ts_render.crop_pad(fr,crop) if crop else fr
    frames=[cp(f) for f in frames]
    mip=np.max(np.stack(frames,0),0).astype(np.uint8)        # max-intensity projection over z
    # UNIFORM contrast stretch (same mapping across MIP + every slice, per the uniform-brightness rule): map the
    # MIP's [p2,p99.7] to [0,255] so the dim z-stack signal is legible without per-panel auto-normalization.
    g=mip.max(2) if mip.ndim==3 else mip
    lo,hi=np.percentile(g[g>0],2) if (g>0).any() else 0, np.percentile(g,99.7)
    lo=float(lo); hi=float(hi) if hi>lo else lo+1.0
    def stretch(im):
        f=(im.astype(np.float32)-lo)*(255.0/(hi-lo)); return np.clip(f,0,255).astype(np.uint8)
    mip=stretch(mip); frames=[stretch(f) for f in frames]
    idxs=sorted(set(np.linspace(0,len(frames)-1,min(n_slices,len(frames))).astype(int)))
    slices=[frames[i] for i in idxs]
    labs=[f"z{i+1}/{len(frames)}" for i in idxs]
    panels=[("MIP",mip)]+list(zip(labs,slices))
    H=min(p[1].shape[0] for p in panels)
    lab_fl=fluor_label(b); tiles=[]
    for j,(lab,img) in enumerate(panels):
        w=int(img.shape[1]*H/img.shape[0]); im=cv2.resize(img,(w,H)).copy()
        cv2.putText(im,lab,(6,26),cv2.FONT_HERSHEY_SIMPLEX,0.6,(255,255,255),1,cv2.LINE_AA)   # slice/MIP label (top-left)
        if j==0: cv2.putText(im,"z-stack",(6,50),cv2.FONT_HERSHEY_SIMPLEX,0.55,(120,220,255),1,cv2.LINE_AA)  # z-stack tag
        tiles.append(im); tiles.append(np.full((H,4,3),20,np.uint8))
    row=np.hstack(tiles[:-1])
    # scalebar (real pixel size) on the last tile
    bar_um=10.0; barpx=max(3,int(round(bar_um/pxs)))
    x1=row.shape[1]-10; x0=max(0,x1-barpx); y=row.shape[0]-12
    cv2.rectangle(row,(x0,y),(x1,y+5),(255,255,255),-1)
    cv2.putText(row,f"{bar_um:.0f} um",(x0,y-6),cv2.FONT_HERSHEY_SIMPLEX,0.5,(255,255,255),1,cv2.LINE_AA)
    cv2.putText(row,lab_fl,(6,row.shape[0]-10),cv2.FONT_HERSHEY_SIMPLEX,0.5,(255,255,255),1,cv2.LINE_AA)  # channel label
    cv2.imwrite(out_prefix+".png",row)
    print(f"wrote {out_prefix}.png  ({len(frames)} z-slices, MIP + {len(idxs)} slices, {lab_fl})")
    return True

if __name__=="__main__":
    # REPLACE the degenerate z-stack strips in the wide set: write straight into png/<safe>.png (same naming as
    # wide_timestrips.py). The .ai links these PNGs -> updates on Update Links; the PDF is re-assembled after.
    OUT="/Volumes/4 MB/ablation_timestrips_wide_20260710/png"
    LOG="/Volumes/4 MB/ablation_timestrips_wide_20260710/zscan_build.log"
    zs=json.load(open("/tmp/wide_zstack.json"))
    TEST=os.environ.get("ZTEST")
    todo=[TEST] if TEST else zs
    done=skip=fail=0
    def log(s):
        open(LOG,"a").write(s+"\n"); print(s,flush=True)
    log(f"=== ZSCAN REPLACE START {time.strftime('%H:%M:%S')} n={len(todo)} ===")
    for i,b in enumerate(todo):
        if not render_dir(b): skip+=1; continue
        try:
            if render_zscan(b,f"{OUT}/{b.replace('/','_').replace(' ','_')}"): done+=1
            else: skip+=1
        except Exception as e:
            log(f"  FAIL {b}: {e}"); fail+=1
        if (i+1)%25==0: log(f"{time.strftime('%H:%M:%S')} {i+1}/{len(todo)} done={done} skip={skip} fail={fail}")
    log(f"=== ZSCAN DONE {time.strftime('%H:%M:%S')} done={done} skip={skip} fail={fail} ===")
