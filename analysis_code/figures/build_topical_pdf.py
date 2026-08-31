"""Render the TOPICAL manifest (all 223 figures, logical/topical order) to a PDF — one figure per page with a
small caption + group-section dividers. Matches the organized .ai order (by data type/relatedness, NOT recency)."""
import os, json
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

ROOT="/Volumes/4 MB/ablation_figures_20260625"
MAN=os.path.join(ROOT,"_ai_relink/reordered_manifest_TOPICAL.json")
OUT="/Volumes/4 MB/ablation_plots/ablation_figures_organized.pdf"
figs=json.load(open(MAN))
PW,PH=1400.0,1050.0; M=30.0; CAPH=34.0
IMGCACHE=os.path.join(ROOT,"_compact_img"); os.makedirs(IMGCACHE,exist_ok=True)
MAXW=2000; JPEGQ=82
def compact(img):
    src=os.path.join(ROOT,img)
    if not os.path.isfile(src): return None
    out=os.path.join(IMGCACHE,img.replace("/","__").rsplit(".",1)[0]+".jpg")
    if os.path.isfile(out) and os.path.getmtime(out)>=os.path.getmtime(src): return out
    im=Image.open(src)
    if im.mode in ("RGBA","P","LA"):
        bg=Image.new("RGB",im.size,(255,255,255)); bg.paste(im.convert("RGBA"),mask=im.convert("RGBA").split()[-1]); im=bg
    else: im=im.convert("RGB")
    if im.width>MAXW: im=im.resize((MAXW,max(1,round(im.height*MAXW/im.width))),Image.LANCZOS)
    im.save(out,"JPEG",quality=JPEGQ,optimize=True); return out
def grp(p):
    b=os.path.basename(p); low=p.lower()
    if "custom_collagen_vs_triple" in p: return "CUSTOM ANALYSES"
    if b.startswith("G5") or "g5_" in low or "mad1" in low or "_if_" in low or "hec1" in low: return "GROUP 5 — IF / Mad1 / Hec1"
    if "frap" in low and ("timestrip" in low or "frap_timestrips" in p): return "GROUP 4 — FRAP timestrips"
    if b.startswith("G4") or b.startswith("G9") or "group4/" in p or "g4_" in low: return "GROUP 4 — mechanism (FRAP / intensity / polar-lagging / oscillation / fluor / drug)"
    if b.startswith("G3") or "group3/" in p: return "GROUP 3 — chromosome length / KT fate / position"
    if b.startswith("G2") or "group2/" in p: return "GROUP 2 — durations / K-K distance"
    return "GROUP 1 — cohort / shape / example timestrips"
c=canvas.Canvas(OUT,pagesize=(PW,PH))
cur=None; n=0
for img in figs:
    g=grp(img)
    if g!=cur:
        cur=g
        c.setFont("Helvetica-Bold",34); c.drawCentredString(PW/2,PH/2+10,g); c.showPage()
    jp=compact(img)
    if not jp: continue
    im=Image.open(jp); iw,ih=im.size
    aw,ah=PW-2*M,PH-2*M-CAPH
    s=min(aw/iw,ah/ih); w,h=iw*s,ih*s
    c.drawImage(ImageReader(jp),(PW-w)/2,M+CAPH+(ah-h)/2,w,h,preserveAspectRatio=True,mask='auto')
    c.setFont("Helvetica",11); c.drawCentredString(PW/2,M+10,os.path.basename(img))
    c.showPage(); n+=1
c.save()
print(f"topical PDF: {n} figures -> {OUT}")
