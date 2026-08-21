"""#13c — Annotated deck: each plot with the EXACT matching writeup section copied in the whitespace below it.
Text is extracted verbatim via pdftotext (no editing). Plot goes in the top region, writeup text in the
bottom region — never overlapping. Output: ablation_figures_ANNOTATED.pdf on 4 MB.
Section->plot matching is reasoned here (the writeups don't name plots/slides)."""
import subprocess, re, os, textwrap
from PIL import Image, ImageDraw, ImageFont

ROOT="/Volumes/4 MB/ablation_figures_20260625"
WU=f"{ROOT}/writeups"
DOCS=[f"{WU}/4_TABLES_AND_REPORTS/condensed results type-up.pdf", f"{WU}/4_TABLES_AND_REPORTS/original results type-up.pdf"]

# ---- 1. extract exact text from both writeups (verbatim) ----
def extract(p):
    try: return subprocess.check_output(["/opt/homebrew/bin/pdftotext","-layout",p,"-"],text=True)
    except Exception as e: print("extract fail",p,e); return ""
alltext="\n".join(extract(d) for d in DOCS if os.path.isfile(d))

# ---- 2. split into (header, body) sections on 'Figure ...:' lines ----
lines=alltext.splitlines()
secs=[]; cur=None
hdr_re=re.compile(r'^\s*Figure\b.*?:', re.I)
for ln in lines:
    if hdr_re.match(ln) and len(ln.strip())>12:
        cur={"hdr":ln.strip(),"body":[ln.strip()]}; secs.append(cur)
    elif cur is not None:
        cur["body"].append(ln.rstrip())
for s in secs: s["text"]=re.sub(r'\n{3,}','\n\n',"\n".join(s["body"]).strip())
print(f"extracted {len(secs)} writeup sections")

def find_sec(*keys):
    """return the first section whose OPENING text contains any keyword (first ~260 chars covers a
    header that pdftotext wrapped onto a second line)."""
    for k in keys:
        for s in secs:
            if k.lower() in s["text"][:260].lower(): return s["text"]
    return None

# ---- 3. reasoned mapping: plot basename substring -> writeup section (by header keyword) ----
# ordered rules; first match wins.
RULES=[
 (("unmanipulated","traced_cell"),                       ("In healthy mitosis","healthy mitosis")),
 (("timestrips2/1-sisterless","timestrips2/2-sisterless","timestrips2/3-sisterless","timestrips2/off-target","timestrips2/double","frap_timestrip"),
                                                          ("can be created by destroying","Sisterless kinetochores can be created")),
 (("ablation_intensity","frap","ablation_individual","prepost_intensity"),   ("lose and do not recover","targeted for ablation lose")),
 (("kt_fate","origin_position","polar_timestrip","edge_distance","pole_time","plate_join","congression"),
                                                          ("can never achieve bioriented","single kinetochore can never")),
 (("plate_distance","oscillation","velocity","kt_intensity_time","distance_vs_fluor"),
                                                          ("can never achieve bioriented","single kinetochore can never")),
 (("kk_distance",),                                       ("k-k distance","k-k distance between the targeted")),
 (("chromo_length",),                                     ("length of targeted chromosomes","chromosomes does not")),
 (("metaphase_ablated","phase_split","metaphase_dynamics","prophase_dynamics","abl_to_meta","duration_combined"),
                                                          ("delay anaphase when a single","prophase versus prometaphase")),
 (("violin2","violin1","survival","statgrid","mitotic_duration","start_rounded","roundness","area"),
                                                          ("Three early sisterless","Two early sisterless","delay anaphase when a single")),
 (("exhaustion","nocodazole","G4_zm"),                    ("not due to activation of mitotic slippage","mitotic slippage")),
 (("lagging","polar_bar","neither_bar","polar_lagging"),  ("directionless kinetochore-less midzone","kinetochore-less midzone chromatids")),
 (("cdc20","G5_IF","mad1hec1"),                           ("retains more fluorescent signal","polar sisterless kinetochore retains")),
 (("G5_",),                                               ("eYFP-Mad1","Mad1")),
]
def sec_for(img):
    b=img.lower()
    for subs,keys in RULES:
        if any(s.lower() in b for s in subs):
            t=find_sec(*keys)
            if t: return t
    return None

# ---- 4. slide order (mirror deck.py) ----
import importlib.util
src=open(f"{ROOT}/deck.py").read()
ns={}; m=re.search(r'GROUPS=(\[.*?\n\])\n',src,re.S); exec("GROUPS="+m.group(1),ns)
imgs=[]
for g in ns["GROUPS"]:
    for s in g.get("slides",[]):
        if s.get("img"): imgs.append(s["img"])

# ---- 5. render: plot on top, verbatim writeup text below (no overlap) ----
def font(sz):
    for p in ["/System/Library/Fonts/Supplemental/Arial.ttf","/System/Library/Fonts/Helvetica.ttc","/Library/Fonts/Arial.ttf"]:
        if os.path.isfile(p):
            try: return ImageFont.truetype(p,sz)
            except Exception: pass
    return ImageFont.load_default()
W,H=1700,2200; MARGIN=60; PLOT_H=1150
pages=[]; matched=0; unmatched=[]
for img in imgs:
    fp=os.path.join(ROOT,img)
    if not os.path.isfile(fp): continue
    canvas=Image.new("RGB",(W,H),"white"); d=ImageDraw.Draw(canvas)
    try:
        im=Image.open(fp).convert("RGB")
        r=min((W-2*MARGIN)/im.width,(PLOT_H-MARGIN)/im.height)
        im=im.resize((int(im.width*r),int(im.height*r)))
        canvas.paste(im,((W-im.width)//2,MARGIN))
    except Exception as e: print("img fail",img,e); continue
    ty=PLOT_H+30; d.line([(MARGIN,ty-14),(W-MARGIN,ty-14)],fill="#cccccc",width=2)
    txt=sec_for(img)
    if txt:
        matched+=1
        # fit font so the (wrapped) section fills the bottom region without overflow
        for fs in (26,23,20,18,16,14,12):
            fnt=font(fs); cw=max(4,int((W-2*MARGIN)/(fs*0.55)))
            wrapped=[]
            for para in txt.split("\n"):
                wrapped += (textwrap.wrap(para,cw) or [""]) if para.strip() else [""]
            if MARGIN+len(wrapped)*(fs+5) <= (H-ty-MARGIN) or fs==12: break
        yy=ty
        for wl in wrapped:
            if yy> H-MARGIN-fs: d.text((MARGIN,yy),"… [section continues]",font=font(12),fill="#888"); break
            d.text((MARGIN,yy),wl,font=fnt,fill="#111"); yy+=fs+5
    else:
        unmatched.append(img)   # no relevant writeup section for this plot -> leave the whitespace blank (that's fine)
    pages.append(canvas)
out=f"{ROOT}/ablation_figures_ANNOTATED.pdf"
pages[0].save(out,save_all=True,append_images=pages[1:],resolution=110.0)
print(f"ANNOTATED PDF: {len(pages)} pages -> {out}  (matched {matched}, unmatched {len(unmatched)})")
print("unmatched:", ", ".join(os.path.basename(u) for u in unmatched[:30]))
