// Place the two metaphase-anchored collagen-vs-pooled figures alongside their ablation-anchored siblings.
//
// USER 2026-08-17: "make sure ... the products are placed on the active files."
// Item 12 produced four figures -- area and roundness, each anchored to the ablation AND to metaphase onset,
// matching how the rest of that family is built. Two were placed; these are the other two.
//
// ROOM IS MADE BY SCALING WHAT IS ALREADY ON THE BOARD, never by adding an artboard:
//   "if you need more space on artboards, etc, scale existing things on the artboard down instead of
//    placing things on different artboards - this messes up sorting and can get confusing."
#target illustrator

var AIP = "/Volumes/4 MB/1_DECKS/META_FIGURES_20260814.ai";
var PDF = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf";
var TMP = "/Volumes/4 MB/_claude_tmp";
var HB  = new File(TMP + "/collagenmeta_heartbeat.txt");
function beat(m) { try { HB.open("a"); HB.writeln(m); HB.close(); } catch (e) {} }

var AB = 4;                     // 1-based
var SCALE = 0.88;               // shrink what is already there just enough to open two slots
var WANT = ["G1_area_collagen_vs_pooled_meta", "G1_roundness_collagen_vs_pooled_meta"];
var TARGET_W = 1500;

app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
beat("START");
var doc = app.open(new File(AIP));
beat("opened " + doc.name);
var report = [], i, k;

var lockState = [];
for (i = 0; i < doc.layers.length; i++) {
  var Ly = doc.layers[i]; var st = { lay: Ly, lk: false };
  try { st.lk = Ly.locked; Ly.locked = false; } catch (e) {}
  lockState.push(st);
}

var R = doc.artboards[AB - 1].artboardRect;
var ccx = (R[0] + R[2]) / 2, ccy = (R[1] + R[3]) / 2;

// already there?
var have = {};
for (i = 0; i < doc.pageItems.length; i++) {
  var q = doc.pageItems[i], qn = "";
  try { if (q.typename === "PlacedItem" && q.file) qn = q.file.name.replace(/\.(pdf|png|ai|eps)$/i, ""); } catch (e) {}
  if (qn) have[qn] = 1;
}
var todo = [];
for (k = 0; k < WANT.length; k++) if (!have[WANT[k]]) todo.push(WANT[k]);
report.push("to place: " + (todo.length ? todo.join(", ") : "(none -- already on the deck)"));

if (todo.length) {
  // scale everything already on this board, about the board centre
  var onboard = [];
  for (i = 0; i < doc.pageItems.length; i++) {
    var p = doc.pageItems[i], pb = null;
    try { pb = p.visibleBounds; } catch (e) { continue; }
    try { if (p.parent.typename !== "Layer") continue; } catch (e) { continue; }
    if (pb[0] < R[2] && pb[2] > R[0] && pb[3] < R[1] && pb[1] > R[3]) onboard.push(p);
  }
  for (i = 0; i < onboard.length; i++) {
    var p2 = onboard[i], b2 = null;
    try { b2 = p2.visibleBounds; } catch (e) { continue; }
    var cxi = (b2[0] + b2[2]) / 2, cyi = (b2[1] + b2[3]) / 2;
    try {
      p2.resize(SCALE * 100, SCALE * 100);
      var b3 = p2.visibleBounds;
      p2.translate(ccx + (cxi - ccx) * SCALE - (b3[0] + b3[2]) / 2,
                   ccy + (cyi - ccy) * SCALE - (b3[1] + b3[3]) / 2);
    } catch (e) {}
  }
  report.push("scaled " + onboard.length + " items already on artboard " + AB + " by " + SCALE);

  var LAYNAME = "session_20260817";
  var lay = null;
  for (i = 0; i < doc.layers.length; i++) if (doc.layers[i].name === LAYNAME) lay = doc.layers[i];
  if (lay === null) { lay = doc.layers.add(); lay.name = LAYNAME; }
  try { lay.locked = false; lay.visible = true; doc.activeLayer = lay; } catch (e) {}

  for (k = 0; k < todo.length; k++) {
    var pf = new File(PDF + "/" + todo[k] + ".pdf");
    if (!pf.exists) { report.push("MISSING PDF\t" + todo[k]); continue; }
    var it2 = lay.placedItems.add();
    it2.file = pf;
    var sc = TARGET_W / it2.width;
    if (sc > 0 && sc !== 1) it2.resize(sc * 100, sc * 100);
    var w = it2.width, h = it2.height;

    // occupancy AFTER the scale-down, excluding the ones we are seating
    var occ = [];
    for (i = 0; i < doc.pageItems.length; i++) {
      var o = doc.pageItems[i];
      if (o === it2) continue;
      var ob = null;
      try { ob = o.visibleBounds; } catch (e) { continue; }
      try { if (o.parent.typename !== "Layer") continue; } catch (e) { continue; }
      if (ob[0] < R[2] && ob[2] > R[0] && ob[3] < R[1] && ob[1] > R[3]) occ.push(ob);
    }
    var STEP = 50, found = false, bx = R[0] + 40, by = R[1] - 40;
    for (var yy = R[1] - 40; yy - h > R[3] + 40 && !found; yy -= STEP) {
      for (var xx = R[0] + 40; xx + w < R[2] - 40 && !found; xx += STEP) {
        var ok = true;
        for (i = 0; i < occ.length; i++) {
          var oo = occ[i];
          if (xx < oo[2] && xx + w > oo[0] && yy > oo[3] && yy - h < oo[1]) { ok = false; break; }
        }
        if (ok) { bx = xx; by = yy; found = true; }
      }
    }
    it2.left = bx; it2.top = by; it2.name = todo[k];
    report.push((found ? "PLACED\t" : "PLACED (no free slot -> top-left, re-flow needed)\t") + todo[k]);
    beat("placed " + todo[k] + " found=" + found);
  }

  for (i = 0; i < lockState.length; i++) { try { lockState[i].lay.locked = lockState[i].lk; } catch (e) {} }
  try { doc.selection = null; } catch (e) {}
  var opts = new IllustratorSaveOptions();
  opts.compatibility = Compatibility.ILLUSTRATOR17;
  opts.pdfCompatible = false;
  doc.saveAs(new File(AIP), opts);
  doc.close(SaveOptions.SAVECHANGES);
} else {
  doc.close(SaveOptions.DONOTSAVECHANGES);
}

var rf = new File(TMP + "/collagenmeta_report.txt"); rf.encoding = "UTF-8"; rf.open("w");
for (i = 0; i < report.length; i++) rf.writeln(report[i]);
rf.close();
app.userInteractionLevel = UserInteractionLevel.DISPLAYALERTS;
beat("ALLDONE");
report.join("\n");
