// Re-place the 25 companion figures WITHOUT overlapping anything (2026-07-29c).
//
// WHY: PLACE_ZOOMS_BESIDE_PARENT puts a companion one parent-width to the RIGHT, or directly below when
// the artboard edge is in the way. That rule assumes there is free space beside the parent. On these
// artboards there usually is not: after placing all 25, a geometry dump showed 22 of them overlapping an
// existing figure, several at 91-97% (G4_exhaustion_violin_journal_win_measured_exit sat almost entirely
// on top of G4_exhaustion_statgrid). Adjacency is worth nothing if it hides another figure.
//
// WHAT THIS DOES, per companion:
//   1. delete the existing placement of that companion, if any (identified by linked filename)
//   2. build the occupied-rectangle list for the parent's artboard from EVERY placed item on it
//   3. try candidate positions in order of preference - right of parent, below parent, then a grid scan
//      over the whole artboard stepping by half a companion width - and take the FIRST that collides with
//      nothing, preferring the candidate nearest the parent
//   4. if no free slot exists anywhere on the artboard, LEAVE IT UNPLACED and report it. A reported gap is
//      recoverable; a figure buried under another figure is not.
// New items go on the `figures` layer: placedItems.add() uses the ACTIVE layer, and when that was a mark
// layer DECK_TITLES_SIG_FAMILY's clearLayer() silently deleted all 25 on its next run.
#target illustrator
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
function readFile(p){ var f=new File(p); f.encoding="UTF-8"; f.open("r"); var s=f.read(); f.close(); return s; }
var WANT   = eval("(" + readFile("/Volumes/4 MB/_working/_deck_jsx_inputs/place_zooms.json") + ")");
// Optional explicit {figure: parent} map. The suffix rule (_zoom / _win_*) only works for companions whose
// name is derived from their parent's; a NEW figure like G1_shape_rate_vs_polar_fraction has no such
// relationship, so its parent has to be stated. Falls back to the suffix rule when a figure is absent here.
var PARENTS = {};
try { PARENTS = eval("(" + readFile("/Volumes/4 MB/_working/_deck_jsx_inputs/place_parents.json") + ")"); } catch (ePM) {}
var PDFDIR = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/";
var GAP = 14;
var DOCS = ["/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai",
            "/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_kinetochore_overflow.ai"];
var report = [];

for (var k = 0; k < DOCS.length; k++) {
  var d = app.open(new File(DOCS[k]));
  var FIGL; try { FIGL = d.layers.getByName("figures"); } catch (eL) { FIGL = d.layers.add(); FIGL.name = "figures"; }

  function lname(p){ var f=null; try{f=p.file;}catch(e){} return f?decodeURI(f.name).toLowerCase().replace(/\.(pdf|png)$/,""):""; }
  function abIndexOfBounds(b){
    var cx=(b[0]+b[2])/2, cy=(b[1]+b[3])/2;
    for(var a=0;a<d.artboards.length;a++){ var R=d.artboards[a].artboardRect;
      if(cx>=R[0]&&cx<=R[2]&&cy<=R[1]&&cy>=R[3]) return a; }
    return -1;
  }
  // 1. delete any existing placement of a wanted companion
  var wantSet={}; for (var w=0; w<WANT.length; w++) wantSet[String(WANT[w]).toLowerCase()]=1;
  var removed=0;
  for (var r=d.placedItems.length-1; r>=0; r--){
    if (wantSet[lname(d.placedItems[r])]) { try{ d.placedItems[r].remove(); removed++; }catch(eR){} }
  }
  // 2. index what remains
  var byName={}, occupied=[];
  for (var i=0;i<d.placedItems.length;i++){
    var it=d.placedItems[i], n=lname(it), bb;
    try{ bb=it.visibleBounds; }catch(eB){ continue; }
    if(n && !byName[n]) byName[n]=it;
    occupied.push([bb[0],bb[1],bb[2],bb[3], abIndexOfBounds(bb)]);
  }
  function collides(l,t,rr,bt,ai){
    for (var c=0;c<occupied.length;c++){
      var o=occupied[c];
      if (o[4]!==ai) continue;
      if (rr<=o[0]||l>=o[2]||bt>=o[1]||t<=o[3]) continue;   // disjoint
      return true;
    }
    return false;
  }
  var placedN=0, unplaced=[], modeCount={right:0, below:0, scan:0}; var shrunk=[];
  for (var q=0;q<WANT.length;q++){
    var z=String(WANT[q]), zl=z.toLowerCase();
    var par = PARENTS[z] ? String(PARENTS[z]).toLowerCase()
                         : zl.replace(/_zoom$/,"").replace(/_win_[a-z_]+$/,"");
    var pit=byName[par];
    if (!pit) continue;                       // parent not in THIS doc
    var f=new File(PDFDIR+z+".pdf");
    if (!f.exists) { unplaced.push(z+"(no pdf)"); continue; }
    var pb=pit.visibleBounds, pw=pit.width, ph=pit.height;
    var ai=abIndexOfBounds(pb);
    if (ai<0) { unplaced.push(z+"(parent off-artboard)"); continue; }
    var R=d.artboards[ai].artboardRect;
    // candidates: right, below, then a grid scan ordered by distance from the parent
    var cands=[[pb[0]+pw+GAP, pb[1], "right"], [pb[0], pb[3]-GAP, "below"]];
    var stepX=pw/2, stepY=ph/2;
    for (var gx=R[0]+GAP; gx+pw<=R[2]-GAP; gx+=stepX)
      for (var gy=R[1]-GAP; gy-ph>=R[3]+GAP; gy-=stepY)
        cands.push([gx, gy, "scan"]);
    var scanStart=2;
    cands = cands.slice(0,scanStart).concat(
      cands.slice(scanStart).sort(function(A,B){
        var da=(A[0]-pb[0])*(A[0]-pb[0])+(A[1]-pb[1])*(A[1]-pb[1]);
        var db=(B[0]-pb[0])*(B[0]-pb[0])+(B[1]-pb[1])*(B[1]-pb[1]);
        return da-db;
      }));
    // Create the item FIRST and measure its real height at the parent's width. Sizing slots with the
    // PARENT's height was wrong: a companion with a taller aspect ratio overhangs the artboard, which is
    // how G4_lagging_auto_shape_v2_win_to_ana ended up past AB26's floor. `ph` is only used for the
    // "below" candidate's step, never for the fit test.
    var pi;
    try{
      pi=FIGL.placedItems.add(); pi.file=f;
      var ratio0=pi.height/pi.width;                  // the file's own aspect - never altered
      pi.width=pw; pi.height=pw*ratio0;
      pi.name=z;
    }catch(eA){ unplaced.push(z+"(add failed "+eA+")"); continue; }
    // Try at the parent's width first, then progressively narrower. A wide 2-panel companion can miss an
    // otherwise-fine gap by a few points - G4_oscillation_vs_time_to_event_traces needed 224pt of height at
    // the parent's 528pt width and AB14's largest free band was 208pt. Shrinking that one figure is far less
    // invasive than rescaling a whole artboard again, so size is the last thing to give, not the first.
    var SHRINK=[1.0, 0.85, 0.72, 0.60], chosen=null, aw=0, ah=0;
    for (var sIdx=0; sIdx<SHRINK.length && !chosen; sIdx++){
      pi.width = pw*SHRINK[sIdx]; pi.height = pw*SHRINK[sIdx]*ratio0;
      aw=pi.width; ah=pi.height;
      for (var cc=0; cc<cands.length; cc++){
        var nx=cands[cc][0], ny=cands[cc][1];
        if (nx<R[0] || nx+aw>R[2] || ny>R[1] || ny-ah<R[3]) continue;   // must stay on the parent's artboard
        if (collides(nx, ny, nx+aw, ny-ah, ai)) continue;
        chosen=[nx,ny,cands[cc][2]+(SHRINK[sIdx]<1?" @"+Math.round(SHRINK[sIdx]*100)+"%":"")]; break;
      }
    }
    if (!chosen) {
      try{ pi.remove(); }catch(eX){}                  // never leave a homeless item floating on the canvas
      unplaced.push(z+"(no free slot on "+(ai+1)+")"); continue;
    }
    pi.position=[chosen[0], chosen[1]];
    var nb=pi.visibleBounds;
    occupied.push([nb[0],nb[1],nb[2],nb[3],ai]);      // so the NEXT companion sees it
    byName[zl]=pi; placedN++;
    var mkey=chosen[2].split(" ")[0]; modeCount[mkey]=(modeCount[mkey]||0)+1;
    if (chosen[2].indexOf("@")>=0) shrunk.push(z+" "+chosen[2].split("@")[1]);
  }
  var nm=d.name, tot=d.placedItems.length;
  var mode="";
  try{ var so=new IllustratorSaveOptions(); so.pdfCompatible=false; d.saveAs(new File(DOCS[k]), so); mode="saved"; }
  catch(e3){ mode="SAVE_FAILED "+e3; }
  try{ d.close(SaveOptions.DONOTSAVECHANGES); }catch(e4){}
  report.push(nm+" :: removed="+removed+" placed="+placedN+
              " (right="+modeCount.right+", below="+modeCount.below+", scan="+modeCount.scan+")"+
              " unplaced="+unplaced.length+" total="+tot+" save="+mode+
              (shrunk.length? "\n     SHRUNK TO FIT: "+shrunk.join("; ") : "")+
              (unplaced.length? "\n     UNPLACED: "+unplaced.join("; ") : ""));
}
report.join("\n");
