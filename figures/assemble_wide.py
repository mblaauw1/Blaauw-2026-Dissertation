"""Assemble the wide timestrip PNGs into ONE multi-page PDF slide file (+ manifest for the .ai grid build).
One page per timestrip (the WITH-text .png, not _notext), sorted by batch. Pages downscaled to keep the PDF
manageable across ~1000 strips. Separate deliverable on 4 MB; does not touch the main figure set."""
import os, glob, json, sys
from PIL import Image
Image.MAX_IMAGE_PIXELS=None
OUT="/Volumes/4 MB/ablation_timestrips_wide_20260710"
PNGDIR=f"{OUT}/png"
PAGE_W=1600   # downscale page width (keeps 1000-page PDF from ballooning; strips stay legible)
pngs=sorted(p for p in glob.glob(f"{PNGDIR}/*.png") if not p.endswith("_notext.png"))
print(f"timestrip pages: {len(pngs)}")
if not pngs: sys.exit("no PNGs to assemble")
def load(p):
    im=Image.open(p).convert("RGB")
    if im.width>PAGE_W:
        im=im.resize((PAGE_W,max(1,round(im.height*PAGE_W/im.width))))
    return im
pages=[]
first=None
for i,p in enumerate(pngs):
    try:
        im=load(p)
        if first is None: first=im
        else: pages.append(im)
    except Exception as e:
        print(f"  skip {os.path.basename(p)}: {e}")
    if (i+1)%100==0: print(f"  loaded {i+1}/{len(pngs)}")
pdf=f"{OUT}/ablation_timestrips_wide_20260710.pdf"
first.save(pdf,save_all=True,append_images=pages,resolution=150)
print(f"wrote {pdf}  ({len(pages)+1} pages, {os.path.getsize(pdf)/1e6:.1f} MB)")
# manifest for the .ai grid (list of PNG paths, batch order)
json.dump(pngs,open(f"{OUT}/wide_png_manifest.json","w"),indent=0)
print(f"manifest: {OUT}/wide_png_manifest.json ({len(pngs)} entries)")
