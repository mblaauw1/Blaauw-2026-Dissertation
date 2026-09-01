# NOTES §1 rule 30 (user 2026-08-16): a RED marker on a GREEN fluorescence panel is the exact
# red/green pair that ~8%% of men cannot separate. Ablation-site markers are now MAGENTA
# (255,0,255) BGR, the standard accessible complement to green, unchanged in shape and width.
"""IF (Mad1/Hec1) figure for an ablated cdc20 cell that was fixed + immunostained.
Top: ablation-movie timestrip (phase top / fluor bottom), formatted like the group_timestrips
ablation strips (1-sisterless): pre-abl / ablation (red site marker) / post-abl, using the
pipeline-rendered movies (burned-in timestamp + channel label + scale bar). Flash frames are
detected by a brightness dip and NEVER used for the displayed pre-abl frame.
Then the IF z-stack panels (per channel + a TRUE additive fluor overlay):
  Row MIP       : brightfield = MIDDLE z-plane; each fluor channel = MIP over z; overlay = additive of fluor MIPs.
  Row SISTERLESS: every channel at the z-plane where the sisterless KT is marked; sisterless KT circled.
  Row PAIRED    : every channel at the z-plane where the paired KT pair is marked; paired KTs circled.
CHANNELS (confirmed from frames.json ch_names ['405 (DAPI)','488 (GFP)','561(mCherry)','640 (Cy5)','Brightfield']):
  405 = Hoechst / DNA (BLUE); 488 = Mad1 (GREEN); 561 = CREST (MAGENTA); 640 = tubulin (HOT PINK).
  NOTE: the pipeline's `mon_fluor` == the 405/DAPI channel (fluor_ch=0) — it is the DNA, NOT a fluor overlay.
Batch pos9_1 IF paired to ablation 20260416 …ptk2 cdc20_10."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import os, json, glob, csv, numpy as np, cv2
import lib
import ts_render   # scale-aware overlay stroke (user 2026-08-20, board 8 item 4)
OUT="/Volumes/4 MB/ablation_figures_20260625/group4"; os.makedirs(OUT,exist_ok=True)  # lands in deck Group-4/Additional

_IFBATCH = "20260417 ptk2 eyfp cdc20 IF stained slide 1 pos9_1"
# The original path pointed into analysis_mad1_task3_IF_20260626, which was ARCHIVED to /Volumes/2 MB
# on 2026-07-22. With that drive detached cv2.VideoCapture only prints "Couldn't read video stream" and
# returns empty frames, so this script kept "succeeding" and wrote a figure built from BLANK channels
# (observed and corrected 2026-07-29). What moved to 2 MB was a retired BACKUP - the same per-channel
# movies are still live on 4 MB in the served IF annotation package, so prefer that and fall back in
# order. lib.require_path turns a genuine miss into a stop that names the archive location.
_IFDIRS = [f"/Volumes/4 MB/_working/_annotation_packages/if_annot_pkgs_20260722/{_IFBATCH}",
           f"/Volumes/4 MB/analysis_mad1_task3_IF_20260626/{_IFBATCH}"]
IFDIR = next((d for d in _IFDIRS if os.path.isdir(d)), None)
if IFDIR is None:
    lib.require_path(_IFDIRS[-1], "IF source movies for G5_IF_mad1hec1_pos9")
print(f"IF source: {IFDIR}")
ABL_BATCH="20260416 IF dish 1 ro ptk2 cdc20_10"

# --- channel table: (mp4/mip stem, label, BGR colour). mon_fluor == the 405/DAPI channel. ---
HOTPINK=(180,105,255)  # BGR for RGB(255,105,180)
BLUE=(255,0,0); GREEN=(0,255,0); MAGENTA=(255,0,255)   # was MAGENTA; see rule 30
CHANS=[("phase","Brightfield",None),
       ("mon_fluor","405 / Hoechst (DNA)",BLUE),
       ("mon_488_GFP","488 / Mad1",GREEN),
       ("mon_561_mCherry","561 / CREST",MAGENTA),
       ("mon_640_Cy5","640 / tubulin",HOTPINK)]
MIDZ=17  # 34 z-planes -> middle
PIX_UM=0.062  # micron / px (from ablation frames.json pixel_size_um)
K_TUBSUB=0.75 # tubulin-subtraction scale: CREST'=clip(CREST-k*tub,0), Mad1'=clip(Mad1-k*tub,0)
# per-channel display stretch (high-percentile, gamma). Less aggressive than the old p99.5->white:
#   raise the high point so <~0.1% saturates, and gamma>1 darkens the diffuse background so
#   puncta/structure read WITHOUT blowing out to saturated white.
STRETCH={"phase":(99.5,1.0),
         "mon_fluor":(99.9,1.15),
         "mon_488_GFP":(99.95,1.30),
         "mon_561_mCherry":(99.9,1.20),
         "mon_640_Cy5":(99.9,1.25)}

# ---- KT annotations for pos9 (loaded from annotations/kt_points.csv; fall back to known coords) ----
def load_pos9_marks():
    p="/Volumes/4 MB/annotations/kt_points.csv"
    sis=[]; sisz=None; par=[]; parz=None
    if os.path.isfile(p):
        rr=csv.DictReader(open(p))
        for r in rr:
            if r["batch"].strip()!="20260417 ptk2 eyfp cdc20 IF stained slide 1 pos9_1": continue
            lab=r["label"].strip()
            try: x=float(r["x"]); y=float(r["y"]); z=int(float(r["frame"]))
            except: continue
            if lab in ("sisterless","mad1_sister") and "640" in r["channel"]:
                sis.append((x,y)); sisz=z
            elif lab=="paired_kt" and "640" in r["channel"]:
                par.append((x,y)); parz=z
    if not sis: sis=[(1113.67,747.73)]; sisz=13
    if not par: par=[(999.52,862.54),(1009.05,903.70)]; parz=12
    return {"z":sisz,"pts":sis},{"z":parz,"pts":par}
SISTER,PAIRED=load_pos9_marks()

def plane(mp4, k):
    cap=cv2.VideoCapture(mp4)
    if int(cap.get(7))<1: cap.release(); return None
    k=max(0,min(int(k),int(cap.get(7))-1)); cap.set(cv2.CAP_PROP_POS_FRAMES,k); ok,fr=cap.read(); cap.release()
    return fr if ok else None
_MIP_CACHE={}
def mip_png(name):
    """Maximum-intensity projection for a fluor channel.

    Prefers a precomputed <name>_mip.png. Those PNGs only ever existed inside
    analysis_mad1_task3_IF_20260626, which was archived to 2 MB on 2026-07-22, so with the live source
    (_annotation_packages/if_annot_pkgs_20260722) they are absent and this used to return None -> a BLANK MIP row while the
    z-plane rows rendered normally (observed 2026-07-29).
    <name>.mp4 IS the z-stack (its frames are z-planes; the z13/z12 rows below index straight into it),
    so the MIP is just the per-pixel max over every frame. Computed once per channel and cached."""
    p=f"{IFDIR}/{name}_mip.png"
    if os.path.isfile(p):
        return cv2.imread(p)
    if name in _MIP_CACHE:
        return _MIP_CACHE[name]
    mp4=f"{IFDIR}/{name}.mp4"
    if not os.path.isfile(mp4):
        _MIP_CACHE[name]=None; return None
    cap=cv2.VideoCapture(mp4); acc=None; n=0
    while True:
        ok,fr=cap.read()
        if not ok: break
        acc=fr.astype(np.uint8) if acc is None else np.maximum(acc,fr)
        n+=1
    cap.release()
    if acc is not None:
        print(f"  MIP computed from {os.path.basename(mp4)} over {n} z-planes")
    _MIP_CACHE[name]=acc
    return acc
def gray(fr): return cv2.cvtColor(fr,cv2.COLOR_BGR2GRAY) if fr is not None and fr.ndim==3 else fr
def norm8(a,hi_pct=99.9,gamma=1.0):
    """Contrast stretch p1..p(hi_pct) -> 0..1 with an optional gamma (>1 darkens midtones/
    diffuse background), then to 8-bit. Raising hi_pct keeps bright puncta from clipping to white."""
    if a is None: return np.zeros((2112,2496),np.uint8)
    a=a.astype(np.float32); lo=np.percentile(a,1); hi=np.percentile(a,hi_pct)
    x=np.clip((a-lo)/max(hi-lo,1),0,1)
    if gamma!=1.0: x=x**gamma
    return (x*255).astype(np.uint8)
def colorize(g8,color):
    if color is None: return cv2.cvtColor(g8,cv2.COLOR_GRAY2BGR)
    out=np.zeros((*g8.shape,3),np.uint8)
    for i,c in enumerate(color): out[...,i]=(g8.astype(np.float32)*c/255).astype(np.uint8)
    return out
def overlay_fluor(planes):
    """planes = list of (gray8, color BGR) -> additive BGR overlay (all fluor channels incl. 405)."""
    h,w=planes[0][0].shape; out=np.zeros((h,w,3),np.uint16)
    for g8,color in planes:
        for i,c in enumerate(color): out[...,i]+=(g8.astype(np.uint16)*c//255)
    return np.clip(out,0,255).astype(np.uint8)

def chan_gray_raw(name,zmode):
    """RAW float32 grayscale plane (no contrast stretch): MIP png (fluor) / middle-or-z movie plane."""
    if name=="phase":
        g=gray(plane(f"{IFDIR}/mon_phase.mp4", MIDZ if zmode=="mip" else zmode))
    elif zmode=="mip":
        g=gray(mip_png(name))
    else:
        g=gray(plane(f"{IFDIR}/{name}.mp4", zmode))
    if g is None: g=np.zeros((2112,2496),np.uint8)
    return g.astype(np.float32)

def chan_gray(name,zmode,tubsub=False,k=K_TUBSUB):
    """8-bit grayscale plane for a channel. If tubsub, subtract k*tubulin(640) from CREST(561)
    and Mad1(488) (clip at 0) BEFORE the per-channel stretch, to knock down diffuse spindle bg."""
    raw=chan_gray_raw(name,zmode)
    if tubsub and name in ("mon_488_GFP","mon_561_mCherry"):
        raw=np.clip(raw-k*chan_gray_raw("mon_640_Cy5",zmode),0,None)
    hi,gm=STRETCH.get(name,(99.9,1.0))
    return norm8(raw,hi,gm)

# ---- crop region around the cell (from KT marks) ----
allpts=SISTER["pts"]+PAIRED["pts"]; cx=np.mean([p[0] for p in allpts]); cy=np.mean([p[1] for p in allpts])
HALF=820
def crop_cell(img):
    h,w=img.shape[:2]; x0=int(max(0,cx-HALF)); y0=int(max(0,cy-HALF)); x1=int(min(w,cx+HALF)); y1=int(min(h,cy+HALF))
    return img[y0:y1,x0:x1], x0, y0
PANEL_H=440
def fit(img):
    s=PANEL_H/img.shape[0]; return cv2.resize(img,(int(img.shape[1]*s),PANEL_H)), s
def lab(img,txt,color=(255,255,255)):
    cv2.putText(img,txt,(8,26),cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,0,0),3,cv2.LINE_AA)
    cv2.putText(img,txt,(8,26),cv2.FONT_HERSHEY_SIMPLEX,0.6,color,1,cv2.LINE_AA)
def mark(img,pts,x0,y0,s,color=(0,255,255)):
    for (x,y) in pts:
        cx2=int((x-x0)*s); cy2=int((y-y0)*s); cv2.circle(img,(cx2,cy2),16,color,ts_render.stroke_px(img),cv2.LINE_AA)

def draw_scalebar(img,bar_px,txt="2 um"):
    h,w=img.shape[:2]; x1=w-14; x0=x1-bar_px; y=h-18
    cv2.rectangle(img,(x0,y),(x1,y+5),(255,255,255),-1)
    cv2.putText(img,txt,(x0,y-6),cv2.FONT_HERSHEY_SIMPLEX,0.45,(0,0,0),3,cv2.LINE_AA)
    cv2.putText(img,txt,(x0,y-6),cv2.FONT_HERSHEY_SIMPLEX,0.45,(255,255,255),1,cv2.LINE_AA)

def zoom_crop(panel,x,y,zhalf):
    """Crop a (2*zhalf) box centred on full-res (x,y), zero-padding if it runs off the frame."""
    h,w=panel.shape[:2]
    x0=int(round(x-zhalf)); y0=int(round(y-zhalf)); x1=x0+2*zhalf; y1=y0+2*zhalf
    out=np.zeros((2*zhalf,2*zhalf,3),panel.dtype)
    cx0=max(0,x0); cy0=max(0,y0); cx1=min(w,x1); cy1=min(h,y1)
    px0=cx0-x0; py0=cy0-y0
    out[py0:py0+(cy1-cy0), px0:px0+(cx1-cx0)]=panel[cy0:cy1,cx0:cx1]
    return out

def if_zoom_row(zmode, pt, marks=None, tubsub=False, k=K_TUBSUB, zhalf=110):
    """Zoomed close-up row centred on the marked KT `pt` (full-res coords), one panel per channel
    + fluor overlay, KT circled (yellow) with a 2 um scale bar. Analogous to the ablation-site zooms."""
    up=PANEL_H/(2*zhalf); bar_px=int((2.0/PIX_UM)*up); fluor_planes=[]; cells=[]
    for name,label,color in CHANS:
        g8=chan_gray(name,zmode,tubsub=tubsub,k=k)
        panel=cv2.cvtColor(g8,cv2.COLOR_GRAY2BGR) if color is None else colorize(g8,color)
        if color is not None: fluor_planes.append((g8,color))
        cr=cv2.resize(zoom_crop(panel,pt[0],pt[1],zhalf),(PANEL_H,PANEL_H),interpolation=cv2.INTER_CUBIC)
        cv2.circle(cr,(PANEL_H//2,PANEL_H//2),24,(0,255,255),2,cv2.LINE_AA)
        draw_scalebar(cr,bar_px); lab(cr,label.split(" /")[0]+" zoom")
        cells.append(cr)
    ov=overlay_fluor(fluor_planes)
    cr=cv2.resize(zoom_crop(ov,pt[0],pt[1],zhalf),(PANEL_H,PANEL_H),interpolation=cv2.INTER_CUBIC)
    cv2.circle(cr,(PANEL_H//2,PANEL_H//2),24,(0,255,255),2,cv2.LINE_AA)
    draw_scalebar(cr,bar_px); lab(cr,"overlay zoom")
    cells.append(cr)
    ims=[]
    for c in cells: ims+=[c,np.full((PANEL_H,6,3),20,np.uint8)]
    return np.hstack(ims[:-1])

def if_row(zmode, marks=None, tubsub=False, k=K_TUBSUB):
    """zmode: 'mip' or an int z-plane. marks: pts to circle. Returns the hstacked row image.
    Overlay column = TRUE additive overlay of ALL fluor channels (405+488+561+640)."""
    cells=[]; fluor_planes=[]
    for name,label,color in CHANS:
        g8=chan_gray(name,zmode,tubsub=tubsub,k=k)
        if name=="phase":
            panel=cv2.cvtColor(g8,cv2.COLOR_GRAY2BGR)
            tag=label+(" (mid z)" if zmode=="mip" else f" (z{zmode})")
        else:
            panel=colorize(g8,color); fluor_planes.append((g8,color))
            tag=label+(" MIP" if zmode=="mip" else f" (z{zmode})")
        c,x0,y0=crop_cell(panel); c,s=fit(c)
        if marks is not None: mark(c,marks,x0,y0,s)
        lab(c,tag)
        cells.append(c)
    # TRUE fluor overlay (fix for the old bug: top row used the 405/DNA plane grayscaled)
    ovimg=overlay_fluor(fluor_planes)
    c,x0,y0=crop_cell(ovimg); c,s=fit(c)
    if marks is not None: mark(c,marks,x0,y0,s)
    lab(c,"fluor overlay"+(" MIP" if zmode=="mip" else f" (z{zmode})"))
    cells.append(c)
    ims=[]
    for c in cells: ims+=[c,np.full((PANEL_H,6,3),20,np.uint8)]
    return np.hstack(ims[:-1])

# ---- ablation timestrip (phase top / fluor bottom) from the pipeline-rendered movies ----
def _abl_render_dir():
    for pat in (f"/Volumes/4 MB/**/{ABL_BATCH}/{ABL_BATCH}_frames.json",):
        g=glob.glob(pat,recursive=True)
        if g: return os.path.dirname(g[0])
    return None
def abl_site_render():
    d=_abl_render_dir()
    if not d: return []
    fj=json.load(open(f"{d}/{ABL_BATCH}_frames.json")); roi=fj.get("roi") or {"x":0,"y":0}
    return [(e["x_px"]-roi.get("x",0), e["y_px"]-roi.get("y",0)) for e in fj.get("ablation_events_local",[])]
def _frame_brightness(cap,n):
    out=[]
    for k in range(n):
        cap.set(cv2.CAP_PROP_POS_FRAMES,k); ok,fr=cap.read()
        out.append(float(cv2.cvtColor(fr,cv2.COLOR_BGR2GRAY).mean()) if ok else 0.0)
    return out
def abl_strip():
    """3 columns: pre-abl (clean, before pulses) / ablation (red site marker) / post-abl.
    Flash frames (laser-pulse brightness dips) are excluded from the displayed frames."""
    d=_abl_render_dir()
    if not d: return None
    site=abl_site_render()
    fj=json.load(open(f"{d}/{ABL_BATCH}_frames.json"))
    ts_abl=[f['t_sec'] for f in fj['frames'] if f['role']=='ablation']
    pcap=cv2.VideoCapture(f"{d}/{ABL_BATCH}_Phase_Ablation.mp4"); n=int(pcap.get(7))
    if n<1: pcap.release(); return None
    brP=_frame_brightness(pcap,n); pcap.release()
    med=float(np.median(brP)); clean=[i for i in range(n) if brP[i]>0.90*med]
    flash=[i for i in range(n) if i not in clean]
    if not clean: clean=list(range(n))
    # pre-abl: latest clean frame that is BEFORE the first flash (i.e. before any pulse); else first clean
    first_flash=min(flash) if flash else n//2
    pre_i=max([i for i in clean if i<first_flash], default=clean[0])
    # ablation: clean frame nearest the middle of the pulse window (an ablation-active but non-flash frame)
    mid_flash=int(np.median(flash)) if flash else n//2
    abl_i=min(clean,key=lambda i:abs(i-mid_flash))
    # post-abl: last clean frame
    post_i=clean[-1]
    cols=[("pre-abl",pre_i,False),("ablation",abl_i,True),("post-abl",post_i,False)]
    rows={}
    for ch in ("Phase","Fluor"):
        cap=cv2.VideoCapture(f"{d}/{ABL_BATCH}_{ch}_Ablation.mp4")
        if int(cap.get(7))<1: cap.release(); rows[ch]=None; continue
        cells=[]
        for name,k,marked in cols:
            cap.set(cv2.CAP_PROP_POS_FRAMES,k); ok,fr=cap.read()
            if not ok: continue
            fr=fr.copy()
            if marked and site:
                for (sx,sy) in site:
                    cv2.circle(fr,(int(sx),int(sy)),10,MAGENTA,ts_render.stroke_px(fr),cv2.LINE_AA)
                    cv2.drawMarker(fr,(int(sx),int(sy)),MAGENTA,cv2.MARKER_CROSS,10,1,cv2.LINE_AA)
            c,s=fit(fr)
            if ch=="Phase": lab(c,name)
            cells.append(c)
        ims=[]
        for c in cells: ims+=[c,np.full((PANEL_H,6,3),20,np.uint8)]
        rows[ch]=np.hstack(ims[:-1]) if cells else None
        cap.release()
    parts=[r for r in (rows["Phase"],rows["Fluor"]) if r is not None]
    if not parts: return None
    W=max(p.shape[1] for p in parts); parts=[np.pad(p,((0,0),(0,W-p.shape[1]),(0,0))) for p in parts]
    return np.vstack([np.vstack([p,np.full((5,W,3),20,np.uint8)]) for p in parts])

def captionbar(text,W,h=34,col=(38,38,38)):
    bar=np.full((h,W,3),col,np.uint8); cv2.putText(bar,text,(8,23),cv2.FONT_HERSHEY_SIMPLEX,0.6,(220,220,220),1,cv2.LINE_AA); return bar

# ---- assemble ----
def build_fig(ab, tubsub=False, k=K_TUBSUB):
    blocks=[]
    if ab is not None: blocks+=[captionbar("ABLATION MOVIE (phase top / fluor bottom; pre-abl / ablation site marked / post-abl; burned-in timestamp + scale bar)",ab.shape[1]),ab]
    mip=if_row("mip",tubsub=tubsub,k=k);           blocks+=[captionbar("IF - MIP (brightfield = middle z; each fluor channel MIP; overlay = additive of the 4 fluor MIPs)"+(" [tubulin-subtracted]" if tubsub else ""),mip.shape[1]),mip]
    sis=if_row(SISTER["z"],marks=SISTER["pts"],tubsub=tubsub,k=k); blocks+=[captionbar(f"IF - sisterless KT z-plane (z{SISTER['z']}); sisterless KT circled (yellow)",sis.shape[1]),sis]
    sz=if_zoom_row(SISTER["z"],SISTER["pts"][0],tubsub=tubsub,k=k); blocks+=[captionbar("IF - sisterless KT ZOOM close-up (KT circled yellow, 2 um scale bar)",sz.shape[1]),sz]
    par=if_row(PAIRED["z"],marks=PAIRED["pts"],tubsub=tubsub,k=k); blocks+=[captionbar(f"IF - paired KT z-plane (z{PAIRED['z']}); paired KT pair circled (yellow)",par.shape[1]),par]
    for i,pt in enumerate(PAIRED["pts"]):
        pz=if_zoom_row(PAIRED["z"],pt,tubsub=tubsub,k=k); blocks+=[captionbar(f"IF - paired KT #{i+1} ZOOM close-up (KT circled yellow, 2 um scale bar)",pz.shape[1]),pz]
    W=max(b.shape[1] for b in blocks)
    if tubsub:
        blocks.insert(0,captionbar(f"TUBULIN-SUBTRACTED IF: CREST'=clip(CREST - {k}*tubulin, 0),  Mad1'=clip(Mad1 - {k}*tubulin, 0)   (640/tubulin scaled by k={k} then removed to suppress the diffuse spindle background so KT puncta stand out; layout identical to the original)",W,h=40,col=(20,20,70)))
    blocks=[np.pad(b,((0,0),(0,W-b.shape[1]),(0,0))) for b in blocks]
    fig=np.vstack([np.vstack([b,np.full((8,W,3),18,np.uint8)]) for b in blocks])
    s=min(4500/fig.shape[1],4200/fig.shape[0],1.0)
    if s<1.0: fig=cv2.resize(fig,(int(fig.shape[1]*s),int(fig.shape[0]*s)),interpolation=cv2.INTER_AREA)
    return fig

ab=abl_strip()
for fname,tsub in (("G5_IF_mad1hec1_pos9.png",False),("G5_IF_mad1hec1_pos9_tubsub.png",True)):
    fig=build_fig(ab,tubsub=tsub,k=K_TUBSUB)
    cv2.imwrite(f"{OUT}/{fname}",fig)
    print(f"wrote {fname}  {fig.shape[1]}x{fig.shape[0]}  ({os.path.getsize(f'{OUT}/{fname}')//1024}KB)")
    # 2026-08-03: this builder wrote the image but never recorded a plot spreadsheet, so these two figures
    # had NO data/<id>.csv -- nothing to open behind the figure, and the "is this figure out of date?"
    # check (which compares that CSV's mtime against the source) could not see them at all. Record the
    # rows the figure is actually built from: the marked KTs (z-plane + x,y, straight out of kt_points.csv)
    # and the ablation strip's batch, with the IF package and channel table as the source lineage.
    _pid=os.path.splitext(fname)[0]
    _rows=[[_pid,"sisterless",SISTER["z"],round(x,2),round(y,2),PIX_UM,(K_TUBSUB if tsub else "")]
           for (x,y) in SISTER["pts"]]
    _rows+=[[_pid,"paired_kt",PAIRED["z"],round(x,2),round(y,2),PIX_UM,(K_TUBSUB if tsub else "")]
            for (x,y) in PAIRED["pts"]]
    lib.record_plot(_pid,["plot_id","kt_label","z_plane","x_px","y_px","pixel_um","tubsub_k"],_rows,
        {"type":"IF montage","if_package":IFDIR,"ablation_batch":ABL_BATCH,
         "channels":[c[1] for c in CHANS],"mid_z":MIDZ,"tubulin_subtracted":bool(tsub),
         "n_sisterless":len(SISTER["pts"]),"n_paired":len(PAIRED["pts"])},
        __file__,f"IF Mad1/CREST montage for {_IFBATCH}"+(" (tubulin-subtracted)" if tsub else ""),
        source=["/Volumes/4 MB/annotations/kt_points.csv",IFDIR],key_column=None)
