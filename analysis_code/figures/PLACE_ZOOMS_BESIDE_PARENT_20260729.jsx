// Place each outlier-trimmed _zoom companion IMMEDIATELY BESIDE the figure it is a zoom of
// (user 2026-07-29: "make sure theyre all placed in copy.ai and the overflow next to the figure they
// are zooms/trims/different time ranges of").
//
// Placement rule: same width and vertical position as the parent, offset one parent-width + gap to
// the RIGHT. If that would run past the parent's artboard edge, it drops DIRECTLY BELOW the parent
// instead, so a companion never lands on a different artboard from its parent.
// Anything already placed is skipped. Nothing existing is moved.
#target illustrator
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
function readFile(p){ var f=new File(p); f.encoding="UTF-8"; f.open("r"); var s=f.read(); f.close(); return s; }
var WANT = eval("(" + readFile("/Volumes/4 MB/_working/_deck_jsx_inputs/place_zooms.json") + ")");
var PDFDIR = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/";
var GAP = 14;
var DOCS = ["/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai",
            "/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_kinetochore_overflow.ai"];
var report = [];

for (var k = 0; k < DOCS.length; k++) {
  var d = app.open(new File(DOCS[k]));
  function lname(p){ var f=null; try{f=p.file;}catch(e){} return f?decodeURI(f.name).toLowerCase().replace(/\.(pdf|png)$/,""):""; }
  function abRectOf(it){
    var b; try{b=it.visibleBounds;}catch(e){return null;}
    var cx=(b[0]+b[2])/2, cy=(b[1]+b[3])/2;
    for(var a=0;a<d.artboards.length;a++){ var R=d.artboards[a].artboardRect;
      if(cx>=R[0]&&cx<=R[2]&&cy<=R[1]&&cy>=R[3]) return R; }
    return null;
  }
  var byName={};
  for (var i=0;i<d.placedItems.length;i++){ var n=lname(d.placedItems[i]); if(n&&!byName[n]) byName[n]=d.placedItems[i]; }

  // SLOT COUNTER (fix 2026-07-29c). byName is built ONCE, before this loop, so a companion placed inside
  // the loop is invisible to the next iteration. Every companion sharing a parent therefore computed the
  // SAME nx,ny and they stacked exactly on top of each other. Four of the 25 in the current list share
  // G4_exhaustion_violin_journal, and two more pairs share G4_fluor_over_time_zoom and
  // G4_oscillation_effective. Count how many have already been placed against each parent and step the
  // slot along, so companion n sits n widths further right (or n heights further down).
  var slotOf={};
  var placed=0, right=0, below=0, skipped=0, missing=[];
  for (var q=0;q<WANT.length;q++){
    // strip either a _zoom suffix or a _win_<mode> suffix to find the parent figure
    var z=String(WANT[q]), zl=z.toLowerCase(), par=zl.replace(/_zoom$/,"").replace(/_win_[a-z_]+$/,"");
    if (byName[zl]) { skipped++; continue; }          // already placed in this doc
    var pit=byName[par];
    if (!pit) continue;                                // parent not in THIS doc
    var f=new File(PDFDIR+z+".pdf");
    if (!f.exists) { if(missing.length<8) missing.push(z); continue; }
    var pb=pit.visibleBounds, pw=pit.width, ph=pit.height, R=abRectOf(pit);
    var slot=(slotOf[par]||0)+1; slotOf[par]=slot;     // 1 = first companion, 2 = second, ...
    var nx=pb[0]+slot*(pw+GAP), ny=pb[1];
    if (R && (nx+pw) > R[2]) { nx=pb[0]; ny=pb[3]-(slot-1)*(ph+GAP)-GAP; below++; } else { right++; }
    try{
      // LAYER (fix 2026-07-29c). placedItems.add() puts the new item on the ACTIVE layer, which after a
      // previous pass can be a MARK layer. On the first attempt the 25 companions landed on a mark layer
      // and DECK_TITLES_SIG_FAMILY's clearLayer() deleted every one of them on its next run (placed went
      // straight back to 501/80). Force them onto `figures`, which is also what FIX_LAYER_HYGIENE enforces.
      var FIGL; try{ FIGL=d.layers.getByName("figures"); }catch(eL){ FIGL=d.layers.add(); FIGL.name="figures"; }
      var pi=FIGL.placedItems.add(); pi.file=f;
      var ratio=pi.height/pi.width;
      pi.width=pw; pi.height=pw*ratio;
      pi.position=[nx,ny];
      pi.name=z;
      placed++;
    }catch(e2){}
  }
  var mode="";
  try{ var so=new IllustratorSaveOptions(); so.pdfCompatible=false; d.saveAs(new File(DOCS[k]), so); mode="saved"; }
  catch(e3){ mode="SAVE_FAILED "+e3; }
  var tot=d.placedItems.length;
  try{ d.close(SaveOptions.DONOTSAVECHANGES); }catch(e4){}
  report.push(DOCS[k].replace(/^.*\//,"")+" :: placed="+placed+" (right="+right+", below="+below+")"+
              " already_there="+skipped+" placed_total="+tot+" save="+mode+
              (missing.length?" MISSING_PDF["+missing.join("|")+"]":""));
}
report.join("\n");
