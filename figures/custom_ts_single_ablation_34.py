"""One-off custom timestrip for 20251029 single_ablation_34 (user spec 2026-07-10).
UNIQUE vs the standard timestrips:
  * brightfield (phase) row INCLUDED on BOTH the ablation base strip AND the monitoring strip
    (normally these are fluor-only); ablation CLOSE-UPS stay fluor-only.
  * MOVING crop: a fixed-SIZE square box RE-CENTERED on the main (ablated) cell in EACH frame
    (normally the crop box is one fixed location) — because the fluor channel has heavy artifacts,
    the cell is located from the cleaner BRIGHTFIELD channel, seeded on the ablation site.
Frames (relative to ablation t=0):
  ablation base : -00:00:05, -00:00:02, 00:00:30
  monitoring    : 00:02:38, 00:03:51, 00:04:27, 00:08:07, 00:13:26
"""
import os, json, numpy as np, cv2, tifffile
from scipy.ndimage import uniform_filter
import ts_render as T, lib

B   = "20251029 single_ablation_34"
RD  = f"/Volumes/4 MB/pipeline_session_output/20251029/{B}"
OUT = f"/Volumes/4 MB/ablation_figures_20260625/group1/timestrips2/20251029_single_ablation_34"
GREEN=(0,255,0)
ABL_T = [-5, -2, 30]
MON_T = [158, 231, 267, 487, 806]

fj = json.load(open(f"{RD}/{B}_frames.json"))
PX = float(fj.get("pixel_size_um", 0.062))
roi = fj["roi"]; frames = fj["frames"]
ev = fj.get("ablation_events_local", [])
# ablation site in CROPPED-tif coords (events are full-frame px -> subtract ROI origin)
abl_pts = [(e["x_px"]-roi["x"], e["y_px"]-roi["y"]) for e in ev]
abl_cx = float(np.mean([p[0] for p in abl_pts])); abl_cy = float(np.mean([p[1] for p in abl_pts]))

def load(p):
    with tifffile.TiffFile(p) as tf: return np.stack([pg.asarray() for pg in tf.pages])
FL = load(f"{RD}/{B}_Fluor_Cropped.tif")
BF = load(f"{RD}/{B}_Phase_Cropped.tif")

def frame_at(t, roles):
    cand=[f for f in frames if f.get("role") in roles]
    return min(cand, key=lambda f: abs(f["t_sec"]-t))
def fl_plane(f): return FL[int(f["fluor_tif_idx"])].astype(np.float32)
def bf_plane(f): return BF[int(f["phase_tif_idx"])].astype(np.float32)

# ---- fixed box SIDE from the cell on the +30 ablation frame (brightfield texture bbox) ----
rep = frame_at(30, {"ablation","monitoring"})
bbpts = T.brightfield_cell_bbox_pts(bf_plane(rep))
cell_side = max(bbpts[:,0].max()-bbpts[:,0].min(), bbpts[:,1].max()-bbpts[:,1].min())
SIDE_UM = float(min(max(cell_side*PX*1.30, 34.0), 42.0))   # fixed physical window, 34–42 µm
SIDE = int(round(SIDE_UM/PX))
if SIDE % 2: SIDE += 1
print(f"ablation site (cropped) = ({abl_cx:.0f},{abl_cy:.0f})  fixed window = {SIDE_UM:.1f} µm ({SIDE}px)")

def cell_center(bf, prev):
    """Texture (local-std) centroid of the cell within a search window around `prev` (keeps the box locked on
    the ABLATED cell, seeded on the ablation site, so the fluor artifacts don't pull it off)."""
    H,W = bf.shape
    m = uniform_filter(bf,15); m2 = uniform_filter(bf*bf,15)
    tex = np.sqrt(np.clip(m2-m*m,0,None))
    r = int(SIDE*0.6)
    px,py = int(round(prev[0])), int(round(prev[1]))
    x0,y0 = max(0,px-r), max(0,py-r); x1,y1 = min(W,px+r), min(H,py+r)
    win = tex[y0:y1, x0:x1]
    w = np.clip(win-np.percentile(win,75),0,None)
    if w.sum()<=0: return prev
    ys,xs = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    cx = float((xs*w).sum()/w.sum()); cy = float((ys*w).sum()/w.sum())
    # guard against a big jump (artifact); cap step to half a box
    mj = SIDE*0.5
    cx = float(np.clip(cx, prev[0]-mj, prev[0]+mj)); cy = float(np.clip(cy, prev[1]-mj, prev[1]+mj))
    return (cx,cy)

def stretch(a, lo, hi, gamma=1.0):
    n = np.clip((a-lo)/max(hi-lo,1e-6),0,1)
    if gamma!=1.0: n = np.power(n,gamma)
    return (n*255).astype(np.uint8)
def colorize(g8,bgr):
    out=np.zeros((*g8.shape,3),np.float32)
    for i,c in enumerate(bgr): out[...,i]=g8.astype(np.float32)*(c/255.0)
    return out.astype(np.uint8)

def build_base_strip(times, roles, name):
    """Two-row (brightfield + fluor) strip with a per-frame moving crop (fixed SIDE)."""
    sel=[frame_at(t,roles) for t in times]
    # moving crop centers (seed on ablation site, track through the frames in time order)
    centers=[]; prev=(abl_cx,abl_cy)
    for f in sel:
        c=cell_center(bf_plane(f), prev); centers.append(c); prev=c
    H,W = BF.shape[1], BF.shape[2]
    # fixed-SIZE window, CLAMPED in-frame (shifts, never edge-pads -> no stripe smear); one per frame
    def box(c): return T.std_square_crop(c[0], c[1], W, H, PX, um=SIDE_UM)
    fl_c=[T.crop_pad(fl_plane(f),box(c)) for f,c in zip(sel,centers)]
    bf_c=[T.crop_pad(bf_plane(f),box(c)) for f,c in zip(sel,centers)]
    # ONE uniform exposure per channel across this strip (robust percentiles pooled over all frames).
    # Fluor is dim/noisy for this cell -> HIGH low-percentile to suppress the noise floor, lift puncta.
    flo,fhi=np.percentile(np.concatenate([p.ravel() for p in fl_c]),(80,99.8))
    blo,bhi=np.percentile(np.concatenate([p.ravel() for p in bf_c]),(1,99.5))
    panels=[]
    for f,fc,bc in zip(sel,fl_c,bf_c):
        panels.append({"phase":colorize(stretch(bc,blo,bhi),(255,255,255)),
                       "fluor":colorize(stretch(fc,flo,fhi,gamma=0.8),GREEN),
                       "t":f["t_sec"]})
    return T.assemble(panels, PX, 10.0, chan_labels=("Brightfield","eYFP-Cdc20"), fluor_only=False)

def build_ablation_zooms():
    """Fluor-only close-ups on the ablation site for the SAME 3 ablation frames (-5,-2,+30), red circle,
    2 µm scalebar (NO brightfield). Exposure from the LOCAL zoom window so bright KTs don't saturate."""
    half=T.zoom_half_px(PX)
    sel=[frame_at(t,{"ablation","monitoring"}) for t in ABL_T]
    x,y=abl_cx,abl_cy
    locs=[]
    for f in sel:
        p=fl_plane(f)
        y0,y1=max(0,int(y-half)),int(y+half); x0,x1=max(0,int(x-half)),int(x+half)
        locs.append(p[y0:y1,x0:x1].ravel())
    flo,fhi=np.percentile(np.concatenate(locs),(70,99.6))
    panels=[]
    for f in sel:
        gz=colorize(stretch(fl_plane(f),flo,fhi,gamma=0.85),GREEN)
        z=T.zoom_to_square(gz, x, y, half, mark=True, N=T.ALIGN_N)
        panels.append({"fluor":z,"t":None})
    return T.assemble(panels, PX, 2.0, chan_labels=("Brightfield","eYFP-Cdc20"), fluor_only=True, show_fmt=False)

abl = build_base_strip(ABL_T, {"ablation","monitoring"}, "ablation")
zoom = build_ablation_zooms()
mon = build_base_strip(MON_T, {"monitoring"}, "monitoring")

portions=[]
if abl:  portions.append(("ablation", *abl))
if zoom: portions.append(("ablation zoom", *zoom))
if mon:  portions.append(("monitoring", *mon))
ok=T.emit(portions, OUT, title=None)
print("emit ok:", ok, "->", OUT+".png")
