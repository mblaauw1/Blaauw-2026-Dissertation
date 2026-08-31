"""Build the GROUPED .ai (user 2026-07-14): related plots TILED together on shared artboards — one artboard
per topical sub-group. EVERY figure exactly ONCE, no repeats. Data-source label appended to each figure's
caption; sub-group title on each artboard. pdf-mode placement (cached svg2pdf PDFs + placed PNGs)."""
import os, json, math
ROOT="/Volumes/4 MB/ablation_figures_20260625"
OUT=os.environ.get("KT_AI_OUT","/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped.ai")
PDFDIR=f"{ROOT}/_ai_relink/pdf"
figs_all=json.load(open(f"{ROOT}/_ai_relink/reordered_manifest_TOPICAL.json"))
try: SRCLAB=json.load(open(f"{ROOT}/_ai_relink/figure_source_labels.json"))
except Exception: SRCLAB={}
try: CAP=json.load(open(f"{ROOT}/_ai_relink/reordered_manifest.json")) and {}  # captions come from deck; fallback = name
except Exception: CAP={}
def srclabel(img):
    l=SRCLAB.get(img,"manual annotations"); return "example imaging" if l=="pipeline/auto" else l

# --- topical SUB-GROUP assignment (ordered) ---
SUBGROUPS=[
 ("G1 · metaphase-duration violins", lambda b,p: b.startswith("G1_violin")),
 ("G1 · time-to-anaphase survival",  lambda b,p: b.startswith("G1_survival")),
 ("G1 · cell shape (roundness/area)",lambda b,p: b.startswith("G1_roundness") or b.startswith("G1_area")),
 ("G1 · shape at onset vs duration", lambda b,p: b.startswith("G1_start_rounded")),
 ("G1 · example timestrips",         lambda b,p: ("timestrips2/" in p) or b in ("traced_cell","G1_traced_timestrip") or b.endswith("-sisterless") or b.endswith("-sisterless_aligned") or "off-target" in b or "double-chromosome" in b or "unmanipulated" in b),
 ("G2 · mitotic-phase durations",    lambda b,p: b.startswith("G2_") and "kk" not in b),
 ("G2 · kinetochore-kinetochore distance", lambda b,p: b.startswith("G2_kk")),
 ("G3 · chromosome length",          lambda b,p: b.startswith("G3_chromo")),
 ("G3 · KT fate / position / congression", lambda b,p: b.startswith("G3_")),
 ("G4 · FRAP recovery",              lambda b,p: b.startswith("G4_frap")),
 ("G4 · ablation intensity",         lambda b,p: b.startswith("G4_ablation_intensity")),
 ("G4 · pre/post-ablation intensity",lambda b,p: b.startswith("G4_prepost")),
 ("G4 · polar & lagging chromosomes",lambda b,p: b.startswith("G4_polar") or b.startswith("G4_lagging") or b.startswith("G4_neither") or b.startswith("G4_1sis")),
 ("G4 · kinetochore oscillation",    lambda b,p: b.startswith("G4_oscillation")),
 ("G4 · KT velocity & plate distance",lambda b,p: b.startswith("G4_velocity") or b.startswith("G4_plate_distance") or b.startswith("G4_distance_vs")),
 ("G4 · eYFP-Cdc20 intensity over time", lambda b,p: b.startswith("G4_kt_intensity") or b.startswith("G4_cdc20_intensity")),
 ("G4 · cell fluorescence",          lambda b,p: b.startswith("G4_fluor")),
 ("G4 · drug controls (Noc / ZM)",   lambda b,p: b.startswith("G4_noc") or b.startswith("G4_zm") or b.startswith("G9_drug")),
 ("G4 · FRAP timestrips",            lambda b,p: "frap_timestrips/" in p),
 ("G4 · slippage/exhaustion timestrips", lambda b,p: "slippage" in b),
 ("G5 · IF quantification (Mad1/Hec1)", lambda b,p: b.startswith("G5_item2") or b.startswith("G5_item3") or "dot_quant" in b),
 ("G5 · Mad1 / Hec1 IF imaging",     lambda b,p: b.startswith("G5_")),
 ("Custom analyses",                 lambda b,p: "custom_collagen_vs_triple" in p),
]
def assign(img):
    b=os.path.basename(img)[:-4]
    for i,(title,fn) in enumerate(SUBGROUPS):
        try:
            if fn(b,img): return i,title
        except Exception: pass
    return len(SUBGROUPS)-1, "Custom analyses"
groups={}
for img in figs_all:
    gi,title=assign(img); groups.setdefault((gi,title),[]).append(img)
ordered_groups=sorted(groups.items(), key=lambda kv: kv[0][0])

# --- layout: each group = mini-grid; shelf-pack group blocks across the canvas ---
CW,CH,CAPH,M=430.0,380.0,30.0,12.0   # cell w/h (incl caption band), margins — sized so the whole grouped
TITLEH=48.0; GPAD=28.0               # layout fits inside Illustrator's ~±6500pt safe canvas half-extent
CANVAS_W=12200.0                     # (the Error-8700 fix: keep max|coord| well under 8000 after centering)
LETTER=os.environ.get("KT_AI_LETTER","") not in ("","0","false","False")  # US-Letter pages: 1 sub-group = 1 letter sheet
def gcols(n): return min(7, max(1, n))
def _src_kind(img):
    b=os.path.basename(img)[:-4]
    svg=f"{ROOT}/{img.rsplit('/',1)[0]}/illustrator/{b}.svg"
    return (svg,"svg") if os.path.isfile(svg) else (f"{ROOT}/{img}","png")
placed=[]     # (src,kind,x,y,w,h,cap)
abrects=[]    # (x0,y0,x1,y1,title)
if LETTER:
    # each sub-group -> ONE US-Letter LANDSCAPE page (792x612); the group's mini-grid is scaled into the page's
    # content area. Pages tiled PCOLS-wide so all fit inside Illustrator's ~±8000pt half-extent.
    PGW,PGH,PM=792.0,612.0,24.0; PCOLS=6; PXPAD,PYPAD=64.0,88.0
    for idx,((gi,title),imgs) in enumerate(ordered_groups):
        pc,pr=idx%PCOLS, idx//PCOLS
        px,py=pc*(PGW+PXPAD), -pr*(PGH+PYPAD)
        abrects.append((px,py,px+PGW,py-PGH,title))
        n=len(imgs); C=gcols(n); R=math.ceil(n/C)
        ax0,ay0=px+PM, py-TITLEH; cw,ch=(PGW-2*PM)/C,(PGH-TITLEH-PM)/R
        for k,img in enumerate(imgs):
            b=os.path.basename(img)[:-4]; src,kind=_src_kind(img)
            x=ax0+(k%C)*cw; y=ay0-(k//C)*ch
            cap=f"{b.replace('_',' ')[:52]}  [data: {srclabel(img)}]"
            placed.append((src,kind,x,y,cw,ch,cap))
else:
    cx=0.0; cy=0.0; shelf_h=0.0
    for (gi,title),imgs in ordered_groups:
        n=len(imgs); C=gcols(n); R=math.ceil(n/C)
        bw=C*CW; bh=TITLEH+R*CH
        if cx>0 and cx+bw>CANVAS_W:            # wrap to next shelf
            cx=0.0; cy-=shelf_h+GPAD; shelf_h=0.0
        bx,by=cx,cy
        abrects.append((bx,by,bx+bw,by-bh,title))
        for k,img in enumerate(imgs):
            col=k%C; row=k//C
            x=bx+col*CW; y=by-TITLEH-row*CH
            b=os.path.basename(img)[:-4]; src,kind=_src_kind(img)
            cap=f"{b.replace('_',' ')[:60]}  [data: {srclabel(img)}]"
            placed.append((src,kind,x,y,CW,CH,cap))
        cx+=bw+GPAD; shelf_h=max(shelf_h,bh)
# fit check: after centering, |coord| must stay well under ~8000 (Illustrator canvas half-extent)
_xs=[a[0] for a in abrects]+[a[2] for a in abrects]; _ys=[a[1] for a in abrects]+[a[3] for a in abrects]
_w=max(_xs)-min(_xs); _h=max(_ys)-min(_ys)
print(f"layout bounds: {_w:.0f} x {_h:.0f}  (half-extent {_w/2:.0f} x {_h/2:.0f}; must be < ~6500 each)")

J=json.dumps([{"src":p[0],"kind":p[1],"x":p[2],"y":p[3],"w":p[4],"h":p[5],"cap":p[6]} for p in placed],ensure_ascii=False)
AB=json.dumps([{"x0":a[0],"y0":a[1],"x1":a[2],"y1":a[3],"t":a[4].replace(" · ",": ").replace("·",":")} for a in abrects],ensure_ascii=False)
jsx=r'''#target illustrator
var F=__J__, AB=__AB__, OUT="__OUT__", PDFDIR="__PDFDIR__", CAPH=__CAPH__, M=__M__, TITLEH=__TITLEH__;
var prevIL; try{prevIL=app.userInteractionLevel; app.userInteractionLevel=UserInteractionLevel.DONTDISPLAYALERTS;}catch(e){}
for(var k=app.documents.length-1;k>=0;k--){ try{ if(/^Untitled/i.test(app.documents[k].name)) app.documents[k].close(SaveOptions.DONOTSAVECHANGES); }catch(_){} }
function svg2pdf(svgPath){ var svg=new File(svgPath); if(!svg.exists) return svg;
  var base=svg.name.replace(/\.svg$/i,""); var pdf=new File(PDFDIR+"/"+base+".pdf");
  if(!pdf.exists){ var d=app.open(svg); var o=new PDFSaveOptions(); o.preserveEditability=true; o.compatibility=PDFCompatibility.ACROBAT5; d.saveAs(pdf,o); d.close(SaveOptions.DONOTSAVECHANGES); } return pdf; }
// bounds of the whole layout -> initial doc big enough
var minX=1e9,maxX=-1e9,minY=1e9,maxY=-1e9;
for(var a=0;a<AB.length;a++){ if(AB[a].x0<minX)minX=AB[a].x0; if(AB[a].x1>maxX)maxX=AB[a].x1; if(AB[a].y1<minY)minY=AB[a].y1; if(AB[a].y0>maxY)maxY=AB[a].y0; }
var DW=Math.min(16000,maxX-minX+200), DH=Math.min(16000,maxY-minY+200);
var doc=app.documents.add(DocumentColorSpace.RGB, DW, DH);
var lyr=doc.layers[0]; lyr.name="figures";
var ab0=doc.artboards[0].artboardRect; var ccx=(ab0[0]+ab0[2])/2, ccy=(ab0[1]+ab0[3])/2;
var lcx=(minX+maxX)/2, lcy=(minY+maxY)/2; var OX=ccx-lcx, OY=ccy-lcy;   // shift layout to canvas center
var placed=0, miss=0, errs=[];
try{
// artboards per group + titles
for(var a=0;a<AB.length;a++){ var r=AB[a];
  var rect=[r.x0+OX, r.y0+OY, r.x1+OX, r.y1+OY];
  var ab; if(a==0){ ab=doc.artboards[0]; ab.artboardRect=rect; } else { ab=doc.artboards.add(rect); }
  ab.name=("G"+(a+1)+" "+r.t).substring(0,60);
  try{ var tt=lyr.textFrames.add(); tt.contents=r.t; tt.textRange.characterAttributes.size=26; tt.position=[r.x0+OX+M, r.y0+OY-M]; }catch(_t){}
}
for(var i=0;i<F.length;i++){ var f=F[i];
  var x0=f.x+OX, top=f.y+OY;
  try{
    var fileRef = /\.svg$/i.test(f.src) ? svg2pdf(f.src) : new File(f.src);
    if(fileRef && fileRef.exists){
      var pi=lyr.placedItems.add(); pi.file=fileRef;
      var pw=pi.width, ph=pi.height; var sc=Math.min((f.w-2*M)/pw, (f.h-CAPH-2*M)/ph);
      pi.width=pw*sc; pi.height=ph*sc; pi.position=[x0+(f.w-pi.width)/2, top-M]; pi.name="fig "+(i+1); placed++;
    } else miss++;
  }catch(e){ errs.push((i+1)+":"+e); }
  try{ var tf=lyr.textFrames.add(); tf.contents=f.cap; tf.textRange.characterAttributes.size=11; tf.position=[x0+M, top-(f.h-CAPH+14)]; }catch(e2){}
}
}catch(ee){ try{doc.close(SaveOptions.DONOTSAVECHANGES);}catch(_){}; try{app.userInteractionLevel=prevIL;}catch(_2){}; throw new Error("FAILED @fig "+i+": "+ee); }
var so=new IllustratorSaveOptions(); so.pdfCompatible=true; doc.saveAs(new File(OUT), so); doc.close(SaveOptions.DONOTSAVECHANGES);
try{app.userInteractionLevel=prevIL;}catch(e){}
"placed="+placed+" miss="+miss+" errs="+errs.length+(errs.length?(" :: "+errs.slice(0,3).join(" | ")):"");
'''
for k,v in {"__J__":J,"__AB__":AB,"__OUT__":OUT,"__PDFDIR__":PDFDIR,"__CAPH__":CAPH,"__M__":M,"__TITLEH__":TITLEH}.items():
    jsx=jsx.replace(k,str(v))
jsxpath=os.environ.get("KT_AI_JSX",f"{ROOT}/BUILD_AI_GROUPED.jsx")
open(jsxpath,"w").write(jsx)
print(f"grouped JSX -> {jsxpath}")
print(f"groups: {len(ordered_groups)}, figures: {len(placed)} -> {OUT}")
for (gi,t),imgs in ordered_groups: print(f"   {len(imgs):3d}  {t}")
