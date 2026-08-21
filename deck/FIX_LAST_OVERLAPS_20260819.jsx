// Clear the last overlapping pairs the minimal-motion solver could not.
//
// TWO DIFFERENT PROBLEMS, TWO DIFFERENT FIXES:
//
// (1) `G4_ablation_individual_contactsheet` should never have been split. It is a CONTACT SHEET -- a
//     browsing/chooser sheet -- not one of the "combination figures ... that can only be moved as one
//     piece" her item 16 is about, and `dataops/split_panels_20260809.py` has always exempted contact
//     sheets and timestrips for exactly that reason. My 2026-08-19 strip splitter matched it on the word
//     "contact" and cut it into 25 tiles, which is what crowded NEW_FIGURES board 5. Its 25 pieces are
//     removed and the single sheet is placed back.
//
// (2) The remaining pairs are new figures sitting on a full board. The de-overlap solver only makes the
//     SMALLEST translation that clears a pair, and on a packed board there is no small translation left --
//     but there is still free space elsewhere on the board. These are re-placed with the same first-free-slot
//     scan used when they were added, which searches the whole board rather than the neighbourhood.
#target illustrator

var TMP = "/Volumes/4 MB/_claude_tmp";
var PDF = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf";
var HB = new File(TMP + "/fix_last_heartbeat.txt");
function beat(m) { try { HB.open("a"); HB.writeln(m); HB.close(); } catch (e) {} }

var LAYNAME = "session_20260819";

// (1) un-split the contact sheet on NEW_FIGURES
var UNSPLIT = [{ deck: "/Volumes/4 MB/1_DECKS/NEW_FIGURES_20260804.ai",
                 base: "G4_ablation_individual_contactsheet", ab: 5, w: 2400 }];

// (2) re-place these into the first genuinely free slot on their own board
var REFLOW = [
  { deck: "/Volumes/4 MB/1_DECKS/META_FIGURES_20260814.ai", ab: 1,
    names: ["G5_hec1_mad1_dot_quant__p1", "G5_hec1_mad1_dot_quant__p2",
            "G5_item4_hec1_timestrip_xy5__piece1", "G5_item4_hec1_timestrip_xy5__piece2",
            "G5_item4_hec1_timestrip_xy5__piece3",
            "nf10_1-sisterless-persistent-polar__20250402_ptk_yfpcdc20_2__piece1",
            "nf10_1-sisterless-persistent-polar__20250402_ptk_yfpcdc20_2__piece2",
            "nf10_1-sisterless-persistent-polar__20250402_ptk_yfpcdc20_2__piece3",
            "nf10_1-sisterless-persistent-polar__20250402_ptk_yfpcdc20_2__piece4"] },
  { deck: "/Volumes/4 MB/1_DECKS/META_FIGURES_20260813_supplemental.ai", ab: 2,
    names: ["G2_ablmeta_vs_duration_triple", "G2_ablmeta_vs_duration_single",
            "G1_imaging_rate_vs_metaphase_unmodified__p2"] }
];

app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
beat("START " + new Date());
var report = [], i, j, k;

function unlockAll(doc) {
  var st = [];
  for (var q = 0; q < doc.layers.length; q++) {
    var L = doc.layers[q], s = { lay: L, lk: false };
    try { s.lk = L.locked; L.locked = false; } catch (e) {}
    st.push(s);
  }
  return st;
}
function relock(st) { for (var q = 0; q < st.length; q++) { try { st[q].lay.locked = st[q].lk; } catch (e) {} } }
function saveClose(doc, aiPath) {
  try { doc.selection = null; } catch (e) {}
  var o = new IllustratorSaveOptions();
  o.compatibility = Compatibility.ILLUSTRATOR17; o.pdfCompatible = false;
  doc.saveAs(new File(aiPath), o);
  doc.close(SaveOptions.SAVECHANGES);
}
function ourLayer(doc) {
  for (var q = 0; q < doc.layers.length; q++) if (doc.layers[q].name === LAYNAME) return doc.layers[q];
  var L = doc.layers.add(); L.name = LAYNAME; return L;
}
// first slot on artboard `abi` that overlaps nothing, ignoring the items in `skip`
function freeSlot(doc, abi, w, h, skip) {
  var R = doc.artboards[abi].artboardRect;
  var occ = [];
  for (var q = 0; q < doc.pageItems.length; q++) {
    var p = doc.pageItems[q];
    var isSkip = false;
    for (var z = 0; z < skip.length; z++) if (skip[z] === p) { isSkip = true; break; }
    if (isSkip) continue;
    var pb = null;
    try { pb = p.visibleBounds; } catch (e) { continue; }
    try { if (p.parent.typename !== "Layer") continue; } catch (e) { continue; }
    if (pb[0] < R[2] && pb[2] > R[0] && pb[3] < R[1] && pb[1] > R[3]) occ.push(pb);
  }
  var STEP = 40;
  for (var yy = R[1] - 30; yy - h > R[3] + 30; yy -= STEP) {
    for (var xx = R[0] + 30; xx + w < R[2] - 30; xx += STEP) {
      var ok = true;
      for (var m = 0; m < occ.length; m++) {
        var o = occ[m];
        if (xx < o[2] + 10 && xx + w + 10 > o[0] && yy + 10 > o[3] && yy - h - 10 < o[1]) { ok = false; break; }
      }
      if (ok) return [xx, yy];
    }
  }
  return null;
}

// ---- (1) un-split the contact sheet ----
for (i = 0; i < UNSPLIT.length; i++) {
  var U = UNSPLIT[i];
  var doc = null;
  try { doc = app.open(new File(U.deck)); } catch (e) { report.push("UNSPLIT OPEN FAIL " + e); continue; }
  var st = unlockAll(doc);
  var n = 0;
  for (j = doc.pageItems.length - 1; j >= 0; j--) {
    var it = doc.pageItems[j], nm = "";
    try { nm = it.name || ""; } catch (e) {}
    if (nm.indexOf(U.base + "__piece") === 0) { try { it.remove(); n++; } catch (e) {} }
  }
  var lay = ourLayer(doc);
  try { doc.activeLayer = lay; } catch (e) {}
  var pf = new File(PDF + "/" + U.base + ".pdf");
  if (pf.exists) {
    var np = lay.placedItems.add();
    np.file = pf;
    if (U.w && np.width > 0) { var s = U.w / np.width; if (s > 0 && s !== 1) np.resize(s * 100, s * 100); }
    np.name = U.base;
    var slot = freeSlot(doc, U.ab - 1, np.width, np.height, [np]);
    if (slot) { np.left = slot[0]; np.top = slot[1]; }
    else { var R2 = doc.artboards[U.ab - 1].artboardRect; np.left = R2[0] + 30; np.top = R2[1] - 30; }
    report.push("UNSPLIT\t" + U.base + "\tremoved " + n + " pieces, sheet restored" + (slot ? "" : " (NO FREE SLOT)"));
  } else report.push("UNSPLIT\tPDF MISSING\t" + U.base);
  relock(st); saveClose(doc, U.deck);
  beat("unsplit done, removed " + n);
}

// ---- (2) reflow the crowded new figures ----
for (i = 0; i < REFLOW.length; i++) {
  var F = REFLOW[i];
  var d2 = null;
  try { d2 = app.open(new File(F.deck)); } catch (e) { report.push("REFLOW OPEN FAIL " + e); continue; }
  var st2 = unlockAll(d2);
  // collect the group first, so a slot search ignores every member of it
  var grp = [];
  for (j = 0; j < d2.pageItems.length; j++) {
    var p2 = d2.pageItems[j], nm2 = "";
    try { nm2 = p2.name || ""; } catch (e) {}
    for (k = 0; k < F.names.length; k++) if (nm2 === F.names[k]) { grp.push(p2); break; }
  }
  // park them far off-board so they cannot block one another during the search
  for (j = 0; j < grp.length; j++) { try { grp[j].left = 90000; grp[j].top = 90000; } catch (e) {} }
  var moved = 0, failed = 0;
  for (j = 0; j < grp.length; j++) {
    var g = grp[j];
    var slot2 = freeSlot(d2, F.ab - 1, g.width, g.height, grp);
    if (slot2) { g.left = slot2[0]; g.top = slot2[1]; moved++; }
    else { failed++; }
    // once placed it becomes an obstacle for the next one: drop it out of the skip list
    var rest = [];
    for (k = 0; k < grp.length; k++) if (k > j) rest.push(grp[k]);
    grp = grp.slice(0, j + 1).concat(rest);
  }
  report.push("REFLOW\t" + F.deck.split("/").pop() + " ab" + F.ab + "\tmoved " + moved + " / failed " + failed);
  relock(st2); saveClose(d2, F.deck);
  beat("reflow done " + moved + "/" + failed);
}

var rf = new File(TMP + "/fix_last_report.txt"); rf.encoding = "UTF-8"; rf.open("w");
for (i = 0; i < report.length; i++) rf.writeln(report[i]);
rf.close();
app.userInteractionLevel = UserInteractionLevel.DISPLAYALERTS;
beat("ALLDONE " + new Date());
"ALLDONE";
