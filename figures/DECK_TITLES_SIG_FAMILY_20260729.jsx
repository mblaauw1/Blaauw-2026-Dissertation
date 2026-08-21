// Three deck passes in one run (user 2026-07-29):
//
// 1. TITLES        replace each figure's caption with the derived one-line descriptive title
//                  (relationship | data source | KT classes | time window | filters | n | AB | updated).
//                  Layer DECK_TITLE. Old DECK_TITLE text is cleared first so re-running is idempotent.
// 2. SIG_HIGHLIGHT rebuilt from the fresh 2026-07-29 significance scan (203 live placed figures with
//                  p<0.05 on at least one grouping x metric or Spearman pair). The previous rects
//                  covered only the pre-2026-07-20 deck and the curated list had been lost.
// 3. FAMILY_GROUP  NEW faint grey block behind each FAMILY - a parent plus its _zoom / _journal /
//                  _meta / _trendscaled / _scaled01 / _aligned variants - drawn around the bounding box
//                  of the whole family so the group reads as one unit at a glance.
//
// LAYER ORDER, bottom to top: FAMILY_GROUP (grey) -> SIG_HIGHLIGHT (yellow) -> MODEL_HIGHLIGHT /
// REVIVED_OUTLINE -> artwork -> DECK_TITLE. The grey is the faintest and lowest so a yellow
// significance panel and the brown/blue boxes all stay legible on top of it.
#target illustrator
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
function readFile(p){ var f=new File(p); f.encoding="UTF-8"; f.open("r"); var s=f.read(); f.close(); return s; }
var SP = "/Volumes/4 MB/_working/_deck_jsx_inputs/";
var TITLES = eval("(" + readFile(SP + "deck_titles.json") + ")");
var SIG    = eval("(" + readFile(SP + "sig_place.json") + ")");
var FAM    = eval("(" + readFile(SP + "families.json") + ")");
var sigSet = {}; for (var i=0;i<SIG.length;i++) sigSet[String(SIG[i]).toLowerCase()] = 1;

var DOCS = ["/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai",
            "/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_kinetochore_overflow.ai"];
var report = [];

function layer(d, nm, sendBack) {
  var L;
  try { L = d.layers.getByName(nm); } catch (e) { L = d.layers.add(); L.name = nm; }
  if (sendBack) { try { L.zOrder(ZOrderMethod.SENDTOBACK); } catch (e2) {} }
  return L;
}
function clearLayer(L) {
  for (var i = L.pageItems.length - 1; i >= 0; i--) { try { L.pageItems[i].remove(); } catch (e) {} }
}
function grey(d) { var c=new RGBColor(); c.red=150;c.green=150;c.blue=150; return c; }
function yellow(d){ var c=new RGBColor(); c.red=255;c.green=238;c.blue=120; return c; }

for (var k = 0; k < DOCS.length; k++) {
  var d = app.open(new File(DOCS[k]));
  function lname(p){ var f=null; try{f=p.file;}catch(e){} return f?decodeURI(f.name).toLowerCase().replace(/\.(pdf|png)$/,""):""; }

  var byName = {};
  for (var i2=0;i2<d.placedItems.length;i2++){
    var n=lname(d.placedItems[i2]); if(!n) continue;
    if(!byName[n]) byName[n]=[]; byName[n].push(d.placedItems[i2]);
  }

  // ---------- 3. FAMILY_GROUP (bottom) ----------
  var famL = layer(d, "FAMILY_GROUP", true); clearLayer(famL);
  var famDrawn = 0, MF = 28;
  for (var par in FAM) {
    var mem = FAM[par], bx = null;
    for (var m2=0;m2<mem.length;m2++){
      var arr = byName[String(mem[m2]).toLowerCase()];
      if (!arr) continue;
      for (var z=0; z<arr.length; z++){
        var b; try { b = arr[z].visibleBounds; } catch(e){ continue; }
        bx = bx ? [Math.min(bx[0],b[0]), Math.max(bx[1],b[1]), Math.max(bx[2],b[2]), Math.min(bx[3],b[3])] : b.slice();
      }
    }
    if (!bx) continue;
    // a family split across artboards would give a huge box - skip those rather than draw a monster
    if ((bx[2]-bx[0]) > 4000 || (bx[1]-bx[3]) > 4000) continue;
    try {
      var r = famL.pathItems.rectangle(bx[1]+MF, bx[0]-MF, (bx[2]-bx[0])+2*MF, (bx[1]-bx[3])+2*MF);
      r.filled = true; r.fillColor = grey(d); r.stroked = false; r.opacity = 13;
      r.name = "FAMILY " + par; famDrawn++;
    } catch (e3) {}
  }

  // ---------- 2. SIG_HIGHLIGHT ----------
  var sigL = layer(d, "SIG_HIGHLIGHT", false); clearLayer(sigL);
  try { sigL.zOrder(ZOrderMethod.SENDTOBACK); } catch(e){}
  try { famL.zOrder(ZOrderMethod.SENDTOBACK); } catch(e){}   // grey must end up BELOW yellow
  var sigDrawn = 0, MS = 16;
  for (var nm in byName) {
    if (!sigSet[nm]) continue;
    for (var q=0;q<byName[nm].length;q++){
      var bb; try { bb = byName[nm][q].visibleBounds; } catch(e){ continue; }
      try {
        var ry = sigL.pathItems.rectangle(bb[1]+MS, bb[0]-MS, (bb[2]-bb[0])+2*MS, (bb[1]-bb[3])+2*MS);
        ry.filled = true; ry.fillColor = yellow(d); ry.stroked = false; ry.opacity = 38;
        ry.name = "SIGHILITE " + nm; sigDrawn++;
      } catch (e4) {}
    }
  }

  // ---------- 1. DECK_TITLE (top) ----------
  var txtL = layer(d, "DECK_TITLE", false); clearLayer(txtL);
  try { txtL.zOrder(ZOrderMethod.BRINGTOFRONT); } catch(e){}
  var titled = 0;
  for (var nm2 in byName) {
    var t = null;
    for (var key in TITLES) { if (String(key).toLowerCase() === nm2) { t = TITLES[key]; break; } }
    if (!t) continue;
    for (var w=0;w<byName[nm2].length;w++){
      var pb; try { pb = byName[nm2][w].visibleBounds; } catch(e){ continue; }
      try {
        var tf = txtL.textFrames.add();
        tf.contents = String(t);
        tf.textRange.characterAttributes.size = 6.5;
        tf.textRange.characterAttributes.fillColor = (function(){var c=new RGBColor();c.red=40;c.green=40;c.blue=40;return c;})();
        tf.top = pb[3] - 4; tf.left = pb[0];
        try { tf.textRange.paragraphAttributes.justification = Justification.LEFT; } catch(e5){}
        titled++;
      } catch (e6) {}
    }
  }

  var mode = "";
  try { var so=new IllustratorSaveOptions(); so.pdfCompatible=false; d.saveAs(new File(DOCS[k]), so); mode="saved"; }
  catch (e7) { mode = "SAVE_FAILED " + e7; }
  var tot = d.placedItems.length, nab = d.artboards.length;
  try { d.close(SaveOptions.DONOTSAVECHANGES); } catch (e8) {}
  report.push(DOCS[k].replace(/^.*\//,"") + " :: titles=" + titled + " sig_rects=" + sigDrawn +
              " family_blocks=" + famDrawn + " placed=" + tot + " artboards=" + nab + " save=" + mode);
}
report.join("\n");
