"""Definitive match: every pasted object against EVERY placed item on the pre-session publication decks.

No aspect gate (a filter can exclude the right answer) and no single cropping assumption -- each object is
scored both as-extracted and border-trimmed, and the better of the two is reported, because whether a raster
carries page padding is a property of how Docs exported it, not of the figure. Aspect ratio is then reported
as CORROBORATION: a direct paste preserves it, so the winner should also match on aspect.
"""
import glob, io, os, subprocess
import numpy as np, cv2

S="/private/tmp/claude-501/-Users-mblaauw/eda8b94f-c455-471c-8117-e03fc087d822/scratchpad"
TMP="/Volumes/4 MB/_claude_tmp"; CACHE=f"{S}/ras2"
PUB="/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf_pub"
PDF="/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf"
SRC="/Users/mblaauw/Downloads/to-do list 0819 1pm.pdf"

roles=[]
for ln in subprocess.run(["pdfimages","-list",SRC],capture_output=True,text=True).stdout.splitlines()[2:]:
    f=ln.split()
    if len(f)>=4 and f[0].isdigit(): roles.append((int(f[0]),f[2]))
imgs=sorted(glob.glob(f"{S}/pdfimg/img-*.png"))
art=[(p,pg) for (p,(pg,t)) in zip(imgs,roles) if t=="image"]
msk={imgs[i-1]:imgs[i] for i,(pg,t) in enumerate(roles) if t=="smask" and i>0 and roles[i-1][1]=="image"}

items=[]
for tag in ("prepub0814","prepub0813"):
    p=f"{TMP}/geom_{tag}.tsv"
    if not os.path.exists(p): continue
    for ln in io.open(p,encoding="utf-8",errors="replace").read().replace("\r","\n").split("\n"):
        f=ln.split("\t")
        if len(f)<9 or f[0] in ("kind","ARTBOARD") or not f[2]: continue
        try: L,T,R,B=float(f[3]),float(f[4]),float(f[5]),float(f[6])
        except ValueError: continue
        if R-L<=1 or T-B<=1: continue
        items.append({"deck":tag,"ab":f[1],"name":f[2],"aspect":(R-L)/(T-B)})
seen=set(); uitems=[]
for it in items:
    if it["name"] in seen: continue
    seen.add(it["name"]); uitems.append(it)

def ras(n):
    png=f"{CACHE}/{n}.png"
    if not os.path.exists(png):
        s=f"{PUB}/{n}.pdf"
        if not os.path.exists(s): s=f"{PDF}/{n}.pdf"
        if not os.path.exists(s): return None
        subprocess.run(["pdftoppm","-r","40","-png","-singlefile",s,png[:-4]],check=False,capture_output=True)
    return cv2.imread(png) if os.path.exists(png) else None

REF={}
for it in uitems:
    r=ras(it["name"])
    if r is None: continue
    g=cv2.cvtColor(r,cv2.COLOR_BGR2GRAY)
    g=cv2.resize(g,(160,160),interpolation=cv2.INTER_AREA).astype(np.float32); g-=g.mean()
    if g.std()>1e-6: REF[it["name"]]=(g/g.std(), it)
print(f"{len(REF)} placed figures on the pre-session publication decks rasterised as references\n")

def sig(im):
    g=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY) if im.ndim==3 else im
    g=cv2.resize(g,(160,160),interpolation=cv2.INTER_AREA).astype(np.float32); g-=g.mean()
    return g/g.std() if g.std()>1e-6 else None
def trim(im):
    g=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY) if im.ndim==3 else im
    bg=int(np.median(np.concatenate([g[0,:],g[-1,:],g[:,0],g[:,-1]])))
    nz=np.abs(g.astype(np.int16)-bg)>12
    ys,xs=np.where(nz)
    return im if len(xs)<50 else im[ys.min():ys.max()+1, xs.min():xs.max()+1]

objs=[]
for p,pg in art:
    im=cv2.imread(p)
    if im is None: continue
    m=msk.get(p)
    if m:
        mk=cv2.imread(m,cv2.IMREAD_GRAYSCALE)
        if mk is not None and mk.shape[:2]==im.shape[:2] and (mk>20).mean()<0.98:
            n,_,st,_=cv2.connectedComponentsWithStats((mk>20).astype(np.uint8),8); k=0
            for li in range(1,n):
                x,y,w,h,a=st[li]
                if w<120 or h<60 or a<8000: continue
                objs.append((pg,os.path.basename(p),k,im[y:y+h,x:x+w])); k+=1
            continue
    objs.append((pg,os.path.basename(p),0,im))

print(f"{'pg':>3s} {'object':18s} {'corr':>6s} {'aspΔ':>6s}  verdict  figure  [artboard she copied from]")
for pg,nm,k,crop in objs:
    best=(0.0,None,None)
    for variant in (crop, trim(crop)):
        s=sig(variant)
        if s is None: continue
        a=variant.shape[1]/variant.shape[0]
        for name,(g,it) in REF.items():
            v=float((s*g).mean())
            if v>best[0]: best=(v,it,a)
    v,it,a=best
    if it is None: print(f"{pg:3d} {nm+'#'+str(k):18s}      -  no match"); continue
    da=abs(a-it["aspect"])/it["aspect"]
    verdict="CERTAIN" if (v>=0.90 and da<=0.05) else ("CERTAIN" if v>=0.95 else "strong" if v>=0.78 else "weak")
    print(f"{pg:3d} {nm+'#'+str(k):18s} {v:6.3f} {da*100:5.1f}%  {verdict:7s} {it['name'][:50]:52s} [{it['deck'].replace('pre','')} AB{it['ab']}]")
