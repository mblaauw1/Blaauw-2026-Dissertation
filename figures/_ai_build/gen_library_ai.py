"""Build ablation_figures.ai — a complete LIBRARY .ai: EVERY current plot on its own labeled artboard, as
NATIVE, EDITABLE Illustrator art (real vector paths + selectable <text>) for every figure that has an
editable SVG, and a placed raster PNG only for the pure-raster figures that have no SVG. Scans the filesystem
directly (via the reordered manifest) so newly-made plots are ALWAYS included. Emits a JSX run via osascript.

WHY / HOW (native-open approach) --------------------------------------------------------------------------
The OLD build converted each SVG to a PDF (svg2pdf) and did placedItems.add(); pi.file=pdf — a PLACED PDF.
Placed PDFs trigger Illustrator's "…contains PDF elements…" warning and can't be cleanly edited in place.

The NEW build makes the content NATIVE:
  * For each figure that has an editable SVG (charts + slippage/polar timestrips emit these with real <text>):
    Illustrator OPENS the SVG as its OWN document (app.open) — SVGs open as native art: vector paths become
    editable paths, <text> becomes selectable text, and any embedded rasters stay embedded. We select-all,
    GROUP into one item, app.copy() to the app clipboard, then close that source doc. The clipboard is
    APP-LEVEL and survives the doc close, so we then activate the target library doc and app.paste(); the
    pasted group is transformed (uniform-scaled + centered) into the figure's grid cell. Result: fully
    editable native art on the artboard, NO placed PDF, NO warning.
  * For a figure with no SVG (pure-raster montages, e.g. the sisterless timestrips in timestrips2/), we fall
    back to placing the PNG as a raster — unavoidable, but that is the minority (~22 of ~149).
  * We keep so.pdfCompatible=true on the final saveAs: that is only PDF-COMPAT METADATA on the .ai container
    (needed for other apps to preview it); the drawn CONTENT is native, not a placed PDF.

Copy/paste across docs in ExtendScript is finicky, so we are deliberate: copy while the SOURCE doc is active,
close it, then set app.activeDocument = target and paste. We reference the pasted art via doc.selection
(paste leaves the new items selected), group it, and transform that group. See per-figure try/catch below —
errors are collected and non-fatal, and a hard failure reports the figure index it died on.

BUILD MODES (KT_AI_MODE) ---------------------------------------------------------------------------------
  KT_AI_MODE=native  DEFAULT. The open-SVG -> copy -> paste behavior described above: fully editable NATIVE
                     art, but the resulting .ai is HEAVY (~500MB) and slow to open.
  KT_AI_MODE=pdf     LIGHTER FALLBACK. The OLD placed-PDF path: each SVG is converted to a cached PDF
                     (svg2pdf) and dropped in with placedItems.add(); pi.file=pdf (PNGs placed directly).
                     The .ai is a set of PLACED PDFs/PNGs — smaller (~200MB) and opens easily, but less
                     editable (placed art, triggers Illustrator's "contains PDF elements" note). Use this
                     when the native ~500MB file is too big for the machine to open comfortably.
  KT_AI_MODE=symbol  native editable art where every figure is an Illustrator SYMBOL, so user-made copies
                     stay in sync with the master; heavier but fully editable + synced. Builds each figure
                     EXACTLY like native (open SVG -> copy -> paste -> group -> fit into the cell), then calls
                     doc.symbols.add(grp) so the placed group is replaced by an INSTANCE of a registered
                     master symbol. Duplicate any instance in the doc and edits to the master propagate to all
                     copies. The ~23 raster (no-SVG) figures fall back to a plain placed PNG (not a symbol).
  Everything else (manifest-driven fig list, retired-excluded, grid math, CROP_OFFSETS, KT_AI_* knobs,
  per-figure caption + try/catch + FAILED-report) is IDENTICAL between the modes.

HOW TO RUN (reusable / parameterized) -------------------------------------------------------------------
  python3 _ai_build/gen_library_ai.py        # writes the JSX; then the MAIN THREAD runs it via osascript.
Env-var knobs (all optional):
  KT_AI_MODE    native (default, editable but ~500MB) | pdf (placed-PDF, lighter ~200MB, less editable but
                opens easier) | symbol (native editable art, every figure an Illustrator SYMBOL so user-made
                copies stay in sync with the master; heavier but fully editable + synced)
  KT_AI_OUT     output .ai path                      (default /Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures.ai)
  KT_AI_JSX     output JSX path                       (default <ROOT>/BUILD_AI_LIBRARY.jsx)
  KT_AI_SINCE   epoch secs; keep only figs whose PNG mtime >= it  (the "updated-only changelist" .ai)
  KT_AI_KEYS    comma-list of name substrings; keep only figs whose path matches one (precise changelist)
  KT_AI_TS_RASTER  if set (1/true), force the raster-heavy timestrips back to a placed PNG even when they
                   have an SVG — an escape hatch if a timestrip SVG opens too slowly. Default: native.

Main-thread invocations:
  (1) FULL native library:            python3 _ai_build/gen_library_ai.py   (then osascript the JSX)
  (2) Updated-only native changelist: KT_AI_KEYS="G3_slippage,G4_polar" KT_AI_OUT="/Volumes/4 MB/ablation_plots/ablation_figures_CHANGED.ai" python3 _ai_build/gen_library_ai.py
      (or KT_AI_SINCE=<epoch> for an mtime-based changelist)
  (3) LIGHTER full fallback (placed-PDF): KT_AI_MODE=pdf KT_AI_OUT="/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_pdf.ai" python3 _ai_build/gen_library_ai.py
  (4) LIGHTER changelist (placed-PDF):    KT_AI_MODE=pdf KT_AI_KEYS="G3_slippage,G4_polar" KT_AI_OUT="/Volumes/4 MB/ablation_plots/ablation_figures_pdf_CHANGED.ai" python3 _ai_build/gen_library_ai.py
  (5) SYNCED-COPIES symbol library:       KT_AI_MODE=symbol KT_AI_OUT="/Volumes/4 MB/ablation_plots/ablation_figures_symbol.ai" python3 _ai_build/gen_library_ai.py
"""
import os, glob, json
ROOT="/Volumes/4 MB/ablation_figures_20260625"
# KT_AI_OUT = output .ai path; KT_AI_SINCE = optional epoch -> keep only figures whose PNG was modified at/after
# it (the "updated-only" changelist .ai); KT_AI_JSX = output JSX path. Defaults build the full library.
OUT_AI=os.environ.get("KT_AI_OUT","/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures.ai")
_SINCE=float(os.environ.get("KT_AI_SINCE","0") or 0)
# KT_AI_MODE: "native" (default; open-SVG -> copy -> paste editable art, ~500MB) or "pdf" (old placed-PDF
# path; svg2pdf-cached PDFs placed via placedItems.add, lighter ~200MB, easier to open, less editable) or
# "symbol" (native art, but each figure registered as an Illustrator SYMBOL so user-made copies stay synced
# to the master; heavier but fully editable + synced).
MODE=os.environ.get("KT_AI_MODE","native").strip().lower()
if MODE not in ("native","pdf","symbol"): MODE="native"
# PDF cache dir (pdf mode ONLY): svg2pdf writes each converted SVG's PDF here so repeat builds reuse them.
PDFDIR=f"{ROOT}/_ai_relink/pdf"
if MODE=="pdf": os.makedirs(PDFDIR, exist_ok=True)
ns={}; exec(open(f"{ROOT}/deck.py").read().split("# ---------------- PPTX")[0],ns)
cap={}
for g in ns["GROUPS"]:
    for sl in g["slides"]:
        if "img" in sl: cap[sl["img"]]=sl["cap"]
# Use the REORDERED-PDF figure list (in reordered order) so the library .ai contains EXACTLY the figures in
# ablation_figures_REORDERED.pdf, in that order — comprehensive (incl. the build_pdfs-inserted aligned/drug
# timestrips) and reordered. The manifest already EXCLUDES retired figures. Falls back to the filesystem glob
# only if the manifest is missing.
_manifest=f"{ROOT}/_ai_relink/reordered_manifest.json"
if os.path.isfile(_manifest):
    imgs=[m for m in json.load(open(_manifest)) if "_notext" not in m and "/illustrator/" not in m]
    seen=set(); imgs=[x for x in imgs if not (x in seen or seen.add(x))]   # dedupe, PRESERVE reordered order
    if _SINCE>0:   # updated-only changelist .ai: keep figures whose PNG changed at/after the cutoff
        imgs=[x for x in imgs if os.path.isfile(f"{ROOT}/{x}") and os.path.getmtime(f"{ROOT}/{x}")>=_SINCE]
    _KEYS=[k for k in os.environ.get("KT_AI_KEYS","").split(",") if k]
    if _KEYS:   # updated-only changelist by EXPLICIT name substrings (precise "what I changed this round")
        imgs=[x for x in imgs if any(k in x for k in _KEYS)]
else:
    pats=["group1/*.png","group2/*.png","group3/*.png","group4/*.png","group1/timestrips2/*.png"]
    imgs=[]
    for p in pats:
        for f in sorted(glob.glob(f"{ROOT}/{p}")):
            rel=os.path.relpath(f,ROOT)
            if "/illustrator/" in rel or "_individual" in rel: continue
            imgs.append(rel)
    imgs=sorted(set(imgs))
# KT_AI_TS_RASTER escape hatch: force raster-heavy timestrips back to a placed PNG even if they have an SVG.
_TS_RASTER = os.environ.get("KT_AI_TS_RASTER","") not in ("","0","false","False")
# DATA-SOURCE LABELS (user 2026-07-14): append the provenance (manual annotations vs TrackMate) to each
# artboard caption so it sits ON THE SLIDE next to the figure. Map built from FIGURE_PLOTS_PROVENANCE.
import json as _json_src
try: _SRCLAB=_json_src.load(open(f"{ROOT}/_ai_relink/figure_source_labels.json"))
except Exception: _SRCLAB={}
def _srclabel(img):
    l=_SRCLAB.get(img,"manual annotations")
    return "example imaging" if l=="pipeline/auto" else l
figs=[]
for img in imgs:
    base=os.path.basename(img)[:-4]; grp=img.split("/")[0]
    # Timestrips are raster-heavy montages, BUT their illustrator/*.svg carries editable <text> (frame
    # times/labels) over embedded rasters, so opening them NATIVELY still yields editable art. We prefer
    # native by default; set KT_AI_TS_RASTER=1 to force these back to a placed PNG if their SVGs open slowly.
    is_ts = ("timestrip" in img.lower() or "timestrips2/" in img or "frap_timestrips/" in img
             or any(k in base for k in ("slippage","_aligned","frap0","1-sisterless","2-sisterless",
                     "3-sisterless","off-target","double-chromosome","unmanipulated","traced_cell")))
    svg=f"{ROOT}/{grp}/illustrator/{base}.svg"
    # Prefer the editable SVG (native open) whenever it exists; fall back to the raster PNG otherwise, or when
    # KT_AI_TS_RASTER forces timestrips to raster.
    use_png = (is_ts and _TS_RASTER) or (not os.path.isfile(svg))
    src=f"{ROOT}/{img}" if use_png else svg
    _cap=(cap.get(img) or base.replace('_',' '))[:78]
    figs.append({"src":src,"img":img,"cap":f"{_cap}  [data: {_srclabel(img)}]","kind":"png" if src.endswith(".png") else "svg"})
# The Illustrator canvas is only ~16000pt total. With 150+ figs the grid must fit in BOTH dims with margin, so
# use SMALLER cells (900x750) + 13 cols -> grid ~13000x10560 (half-extent 6500x5280), well inside the canvas
# even allowing for its offset from the initial artboard. Bigger cells (1200 @ 12 cols = 15720 wide) fell off
# the canvas edge past col ~6 -> Error 54 at the artboard step.
COLS=15; W=760.0; H=630.0; GX=70.0; GY=110.0; M=22.0; CAPH=42.0   # 15 cols + smaller cells so 237 figs
# fit inside Illustrator's ~±8191pt canvas: half-width 15*830/2=6225, half-height ceil(237/15)*740/2=5920 (<6500)
# LETTER mode (KT_AI_LETTER=1): each artboard becomes a US-Letter PAGE with PER-FIGURE orientation (landscape for
# wide plots, portrait for tall) so File>Print gives one letter sheet per figure. Uniform SQUARE grid cell (letter
# long edge) keeps spacing/canvas math simple; the page rect is centered in the cell and the figure fit to it.
# Env-gated -> only the build that sets KT_AI_LETTER=1 changes; pdf/grouped/native stay exactly as before.
LETTER = os.environ.get("KT_AI_LETTER","") not in ("","0","false","False")
if LETTER:
    from PIL import Image as _PILImg
    _LONG,_SHORT=792.0,612.0                        # US Letter in points (11in x 8.5in)
    W=H=_LONG; GX=GY=90.0; M=30.0; CAPH=46.0        # square cell fits either orientation; roomier print margins
    def _abdims(img):
        try:
            w,h=_PILImg.open(f"{ROOT}/{img}").size
            return (_LONG,_SHORT) if w>=h else (_SHORT,_LONG)   # landscape page for wide figs, portrait for tall
        except Exception:
            return (_LONG,_SHORT)
    _AB={f["img"]:_abdims(f["img"]) for f in figs}
else:
    _AB={f["img"]:(W,H) for f in figs}
NR=(len(figs)+COLS-1)//COLS
J=json.dumps([{"col":i%COLS,"row":i//COLS,"src":f["src"],"kind":f["kind"],"cap":f["cap"],
               "abw":_AB[f["img"]][0],"abh":_AB[f["img"]][1]} for i,f in enumerate(figs)],ensure_ascii=False)
jsx=r'''#target illustrator
var F=__J__, OUT="__OUT__", MODE="__MODE__", PDFDIR="__PDFDIR__";
var W=__W__,H=__H__,GX=__GX__,GY=__GY__,M=__M__,CAPH=__CAPH__,COLS=__COLS__;
var prevIL; try{prevIL=app.userInteractionLevel; app.userInteractionLevel=UserInteractionLevel.DONTDISPLAYALERTS;}catch(e){}
for(var k=app.documents.length-1;k>=0;k--){ try{ if(/^Untitled/i.test(app.documents[k].name)) app.documents[k].close(SaveOptions.DONOTSAVECHANGES); }catch(_){} }  // clear strays
// NATIVE-OPEN helper: open an SVG as its OWN Illustrator document (vector paths + editable <text> become
// native art; embedded rasters stay embedded), select-all, GROUP into a single item, COPY to the app-level
// clipboard, then close the source doc. The clipboard survives the close, so the caller can PASTE the group
// into the target library doc afterward. Returns true if something was copied to the clipboard.
function copySvgToClipboard(p){
  var s=new File(p); if(!s.exists) return false;
  var d=app.open(s);                            // d becomes app.activeDocument
  app.executeMenuCommand('selectall');          // select every unlocked item in the opened SVG
  if(d.selection.length==0){ d.close(SaveOptions.DONOTSAVECHANGES); return false; }
  if(d.selection.length>1) app.executeMenuCommand('group');   // collapse to ONE group -> single pasted item
  app.copy();                                   // app-level clipboard (persists past the close below)
  d.close(SaveOptions.DONOTSAVECHANGES);
  return true;
}
__SVG2PDF_HELPER____SYMBOL_HELPER__var doc=app.documents.add(DocumentColorSpace.RGB, W, H);   // small initial doc -> full canvas room for the grid
var lyr=doc.layers[0]; lyr.name="figures";
var ab0=doc.artboards[0].artboardRect; var cx=(ab0[0]+ab0[2])/2, cy=(ab0[1]+ab0[3])/2;  // center of the doc's initial artboard = canvas center
var CW=W+GX, CH=H+GY, OX=cx-(COLS*CW)/2, OY=cy+(__NR__*CH)/2;   // center the grid on the CANVAS CENTER so all artboards stay inside the ~16000pt canvas (small cells keep half-extent ~6500x5280, well within bounds)
var placed=0, miss=0, errs=[];
try{
for(var i=0;i<F.length;i++){ var f=F[i];
  var AW=f.abw||W, AH=f.abh||H;                                  // per-figure artboard (letter page) size
  var ccx=OX+f.col*CW+W/2, ccy=OY-f.row*CH-H/2;                  // center of this grid cell
  var x0=ccx-AW/2, top=ccy+AH/2; var rect=[x0, top, x0+AW, top-AH];   // page rect centered in the cell
  var ab; if(i==0){ ab=doc.artboards[0]; ab.artboardRect=rect; } else { ab=doc.artboards.add(rect); }
  ab.name="F"+(i+1);
  try{
__PDF_BRANCH_OPEN__    var isSvg = /\.svg$/i.test(f.src);
    if(isSvg && copySvgToClipboard(f.src)){
      // NATIVE branch: paste the copied group into the target library doc and fit it to the cell.
      app.activeDocument=doc;                       // paste target = library doc (source doc is closed)
      try{ doc.artboards.setActiveArtboardIndex(i); }catch(_a){}  // paste near this artboard; position fixed below regardless
      app.paste();
      var sel=doc.selection; var g;
      if(sel.length==0){ throw new Error("paste produced no items"); }
      if(sel.length>1){ app.executeMenuCommand('group'); g=doc.selection[0]; } else { g=sel[0]; }
      try{ g.move(lyr, ElementPlacement.PLACEATEND); }catch(_m){}  // keep pasted art on the 'figures' layer
      var gw=g.width, gh=g.height; var sc=Math.min((AW-2*M)/gw, (AH-CAPH-2*M)/gh);   // fit to this figure's page
      g.width=gw*sc; g.height=gh*sc;                // uniform scale (same sc both dims -> aspect preserved)
      g.position=[x0+(AW-g.width)/2, top-M];        // center horizontally in the page, top-aligned under caption
      g.name="fig "+(i+1); placed++;
__SYMBOL_HOOK__    } else {
      // RASTER fallback: no SVG (or KT_AI_TS_RASTER) -> place the PNG as an embedded raster.
      var fileRef=new File(f.src);
      if(fileRef.exists){
        var pi=lyr.placedItems.add(); pi.file=fileRef;
        var pw=pi.width, ph=pi.height; var sc2=Math.min((AW-2*M)/pw, (AH-CAPH-2*M)/ph);
        pi.width=pw*sc2; pi.height=ph*sc2; pi.position=[x0+(AW-pi.width)/2, top-M]; pi.name="fig "+(i+1); placed++;
      } else miss++;
    }
__PDF_BRANCH_CLOSE__  }catch(e){ errs.push((i+1)+":"+e); }
  try{ var tf=lyr.textFrames.add(); tf.contents=f.cap; tf.textRange.characterAttributes.size=13; tf.position=[x0+M, top-(AH-CAPH+18)]; }catch(e2){}
}
}catch(ee){ try{doc.close(SaveOptions.DONOTSAVECHANGES);}catch(_){}; try{app.userInteractionLevel=prevIL;}catch(_2){}; throw new Error("FAILED at figure "+(i+1)+" of "+F.length+" (src="+(F[i]?F[i].src:"?")+") @line"+ee.line+": "+ee+"  || per-figure errs: "+errs.join(" | ")); }
var so=new IllustratorSaveOptions(); so.pdfCompatible=true;   // PDF-COMPAT METADATA only; drawn content is native
doc.saveAs(new File(OUT), so); doc.close(SaveOptions.DONOTSAVECHANGES);
try{app.userInteractionLevel=prevIL;}catch(e){}
"placed="+placed+" miss="+miss+" errs="+errs.length+(errs.length?(" :: "+errs.slice(0,3).join(" | ")):"");
'''
# MODE-conditional JSX snippets. In native mode these are EMPTY so the emitted JSX is textually identical to the
# original native build (no svg2pdf, no MODE=="pdf" branch). In pdf mode we inject the svg2pdf helper + wrap the
# per-figure body with the OLD placed-PDF branch (the native body stays as the `else`, unreachable when MODE=="pdf").
_SVG2PDF_HELPER = r'''// PDF-MODE helper (KT_AI_MODE=pdf only): the OLD placed-PDF path. Convert an SVG to a cached PDF and return
// a File to it. If the SVG's PDF isn't already cached under <ROOT>/_ai_relink/pdf/, open the SVG, saveAs a
// PDF (preserveEditability + Acrobat5 compat), then close. Repeat builds reuse the cached PDF.
function svg2pdf(svgPath){
  var svg=new File(svgPath); if(!svg.exists) return svg;   // return non-existent File -> caller counts as miss
  var base=svg.name.replace(/\.svg$/i,"");
  var pdf=new File(PDFDIR+"/"+base+".pdf");
  if(!pdf.exists){
    var d=app.open(svg);
    var opts=new PDFSaveOptions();
    opts.preserveEditability=true;
    opts.compatibility=PDFCompatibility.ACROBAT5;
    d.saveAs(pdf, opts);
    d.close(SaveOptions.DONOTSAVECHANGES);
  }
  return pdf;
}
''' if MODE=="pdf" else ""
_PDF_BRANCH_OPEN = r'''    if(MODE=="pdf"){
      // PDF branch: OLD placed-PDF path. SVG -> cached PDF via svg2pdf; PNG placed directly. Same fit math.
      var src=f.src;
      var fileRef = /\.svg$/i.test(src) ? svg2pdf(src) : new File(src);
      if(fileRef && fileRef.exists){
        var pi=lyr.placedItems.add(); pi.file=fileRef;
        var pw=pi.width, ph=pi.height; var sc=Math.min((AW-2*M)/pw, (AH-CAPH-2*M)/ph);
        pi.width=pw*sc; pi.height=ph*sc; pi.position=[x0+(AW-pi.width)/2, top-M]; pi.name="fig "+(i+1); placed++;
      } else miss++;
    } else {
''' if MODE=="pdf" else ""
_PDF_BRANCH_CLOSE = "    }\n" if MODE=="pdf" else ""
# SYMBOL-MODE snippets. In native/pdf mode BOTH are EMPTY, so the emitted JSX is textually identical to those
# builds (no symbols.add, no MODE=="symbol" branch). In symbol mode we inject (a) a pre-loop de-dup helper and
# (b) a per-figure hook that runs AFTER the native group is built+fit: doc.symbols.add(g) registers the group
# as a master symbol and replaces it with an instance, so any COPY the user makes of that instance stays in
# sync with the master. The raster (no-SVG) figures never reach this hook (it lives only in the SVG branch),
# so they stay plain placed PNGs — intentional, per spec.
_SYMBOL_HELPER = r'''// SYMBOL-MODE helper (KT_AI_MODE=symbol only): return a symbol name that is not yet taken in this doc, so
// two figures with the same base filename can't collide. Appends _2, _3, ... until free.
function freeSymName(nm){
  var base=nm, cur=nm, ix=1, hit;
  do{ hit=false;
    for(var q=0;q<doc.symbols.length;q++){ if(doc.symbols[q].name==cur){ hit=true; break; } }
    if(hit){ ix++; cur=base+"_"+ix; }
  }while(hit);
  return cur;
}
''' if MODE=="symbol" else ""
_SYMBOL_HOOK = r'''      if(MODE=="symbol"){
        // SYMBOL branch: register the freshly built + fit native group as an Illustrator master SYMBOL. In
        // Illustrator, doc.symbols.add(g) creates the symbol AND replaces the selected group in-place with a
        // symbol INSTANCE of it (position/scale already set on g above -> instance lands in the same cell).
        // User-made copies of this instance stay in sync when the master symbol is edited.
        try{
          var _sf=new File(f.src); var _bn=_sf.name.replace(/\.[^.]+$/,"");   // figure base name (no dir/ext)
          var sym=doc.symbols.add(g);            // registers a master symbol; g becomes an instance of it
          sym.name=freeSymName(_bn);             // readable, de-duplicated symbol name
        }catch(_sy){ errs.push((i+1)+":sym:"+_sy); }
      }
''' if MODE=="symbol" else ""
for k,v in {"__J__":J,"__OUT__":OUT_AI,"__MODE__":MODE,"__PDFDIR__":PDFDIR,"__SVG2PDF_HELPER__":_SVG2PDF_HELPER,"__SYMBOL_HELPER__":_SYMBOL_HELPER,"__SYMBOL_HOOK__":_SYMBOL_HOOK,"__PDF_BRANCH_OPEN__":_PDF_BRANCH_OPEN,"__PDF_BRANCH_CLOSE__":_PDF_BRANCH_CLOSE,"__W__":W,"__H__":H,"__GX__":GX,"__GY__":GY,"__M__":M,"__CAPH__":CAPH,"__COLS__":COLS,"__NR__":NR}.items():
    jsx=jsx.replace(k, v if isinstance(v,str) else repr(v))
# Write the JSX to the DRIVE (obvious, top-level of the figures dir) — never /tmp (that's local Mac storage).
_JSX_OUT=os.environ.get("KT_AI_JSX",f"{ROOT}/BUILD_AI_LIBRARY.jsx")
open(_JSX_OUT,"w").write(jsx)
open(f"{ROOT}/_ai_build/ai_library.jsx","w").write(jsx)
print(f"JSX -> {_JSX_OUT}")
print(f"mode: {MODE} ({'placed-PDF, lighter ~200MB' if MODE=='pdf' else 'native symbols, synced copies, heavy' if MODE=='symbol' else 'native, editable ~500MB'})")
print(f"library: {len(figs)} figures ({sum(1 for f in figs if f['kind']=='svg')} SVG + {sum(1 for f in figs if f['kind']=='png')} raster) -> {OUT_AI}")
