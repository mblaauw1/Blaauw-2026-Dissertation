#target illustrator
// ONE consolidated pass (handoff rule: never two JSX back-to-back — that jams Illustrator).
//   1. AUDIT every placed link and report the ones Illustrator cannot read  -> explains the
//      "error occurred trying to read the linked file frap_candidates.png" dialog.
//   2. PLACE G4_sisterless_cdc20_vs_bleaching (rebuilt to spec) — its old slot is an EMPTY FRAME on the
//      modelling artboard, left behind when the fabricated version was retired.
//   3. PLACE G3_model_structured_performance (new).
// Existing placements are never moved (they are hers), and duplicates are never removed.
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}

var COPY = "/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
var PDFDIR = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/";
var TARGETS = ["G4_sisterless_cdc20_vs_bleaching.pdf", "G3_model_structured_performance.pdf"];
// anchor = a figure already on the artboard where the new one belongs (both are modelling/G4 analysis)
var ANCHOR = {
  "G4_sisterless_cdc20_vs_bleaching.pdf": "g4_sisterless_fluor_postabl_vs_pole.pdf",
  "G3_model_structured_performance.pdf":  "g3_plate_pole_predictive_model.pdf"
};
var ANCHOR2 = {   // fallback anchors if the first is not present
  "G4_sisterless_cdc20_vs_bleaching.pdf": "g4_fluor_over_time.pdf",
  "G3_model_structured_performance.pdf":  "g3_congression_score_vs_metaphase_duration.pdf"
};

for (var q = 0; q < app.documents.length; q++) {
  if (app.documents[q].fullName && app.documents[q].fullName.fsName == COPY) throw new Error("ABORT: copy.ai open");
}
var d = app.open(new File(COPY));

function lname(p) { var f = null; try { f = p.file; } catch (e) {} return f ? decodeURI(f.name).toLowerCase() : ""; }
function lpath(p) { var f = null; try { f = p.file; } catch (e) {} return f ? f.fsName : ""; }

// ---------- 1. LINK AUDIT ----------
var broken = [], nolink = 0, total = 0;
for (var i = 0; i < d.placedItems.length; i++) {
  var p = d.placedItems[i]; total++;
  var fp = "";
  try { fp = p.file ? p.file.fsName : ""; } catch (e) { nolink++; continue; }
  if (!fp) { nolink++; continue; }
  var f = new File(fp);
  if (!f.exists) broken.push(decodeURI(f.name) + "  ->  " + fp);
}

// ---------- 2/3. PLACEMENT ----------
var occupied = [], mine = {}, anchorOf = {};
for (var i2 = 0; i2 < d.placedItems.length; i2++) {
  var p2 = d.placedItems[i2], n2 = lname(p2), b2;
  try { b2 = p2.visibleBounds; } catch (e) { continue; }
  var isTarget = false;
  for (var t2 = 0; t2 < TARGETS.length; t2++) if (n2 == TARGETS[t2].toLowerCase()) { mine[n2] = p2; isTarget = true; }
  if (!isTarget) occupied.push(b2);
  for (var k in ANCHOR) {
    if (n2 == ANCHOR[k] || n2 == ANCHOR2[k]) {
      // prefer an ON-ARTBOARD instance: several figures are placed twice, once off-canvas, and picking
      // the off-canvas copy put 4 figures off-artboard on a previous run.
      if (!anchorOf[k]) anchorOf[k] = p2;
      else {
        var ob = anchorOf[k].visibleBounds, nb = b2, onOld = false, onNew = false;
        for (var aa = 0; aa < d.artboards.length; aa++) {
          var rr = d.artboards[aa].artboardRect;
          var ocx=(ob[0]+ob[2])/2, ocy=(ob[1]+ob[3])/2, ncx=(nb[0]+nb[2])/2, ncy=(nb[1]+nb[3])/2;
          if (ocx>=rr[0]&&ocx<=rr[2]&&ocy<=rr[1]&&ocy>=rr[3]) onOld = true;
          if (ncx>=rr[0]&&ncx<=rr[2]&&ncy<=rr[1]&&ncy>=rr[3]) onNew = true;
        }
        if (!onOld && onNew) anchorOf[k] = p2;
      }
    }
  }
}

function overlaps(b) {
  for (var i = 0; i < occupied.length; i++) {
    var a = occupied[i];
    var l = Math.max(a[0], b[0]), r = Math.min(a[2], b[2]);
    var tp = Math.min(a[1], b[1]), bo = Math.max(a[3], b[3]);
    if (r > l && tp > bo) {
      var ia = (r - l) * (tp - bo), ba = (b[2] - b[0]) * (b[1] - b[3]);
      if (ia > 0.03 * ba) return true;
    }
  }
  return false;
}

var log = [];
for (var t = 0; t < TARGETS.length; t++) {
  var nm = TARGETS[t], key = nm.toLowerCase();
  var pi = mine[key], an = anchorOf[nm];
  var relinked = false;
  if (pi) {                                    // already placed -> just refresh the link to the new PDF
    try { pi.file = new File(PDFDIR + nm); relinked = true; } catch (e) {}
    log.push(nm.replace(/\.pdf$/, "") + ":ALREADY_PLACED" + (relinked ? "_RELINKED" : ""));
    continue;
  }
  var nf = new File(PDFDIR + nm);
  if (!nf.exists) { log.push(nm + ":NO_PDF"); continue; }
  if (!an) { log.push(nm + ":NO_ANCHOR"); continue; }
  pi = d.activeLayer.placedItems.add(); pi.file = nf; pi.name = "NEW " + nm;
  var abw = an.visibleBounds[2] - an.visibleBounds[0];
  var sc0 = abw / pi.width; pi.width = pi.width * sc0; pi.height = pi.height * sc0;

  var ab = an.visibleBounds, acx = (ab[0] + ab[2]) / 2, acy = (ab[1] + ab[3]) / 2, ai = -1;
  for (var a = 0; a < d.artboards.length; a++) {
    var r = d.artboards[a].artboardRect;
    if (acx >= r[0] && acx <= r[2] && acy <= r[1] && acy >= r[3]) { ai = a; break; }
  }
  if (ai < 0) { log.push(nm + ":ANCHOR_OFF_ARTBOARD"); continue; }
  var R = d.artboards[ai].artboardRect, w = pi.width, h = pi.height, M = 12;
  var bestPos = null, bestD = 1e18;
  var stepX = Math.max(20, w / 3), stepY = Math.max(20, h / 3);
  for (var x = R[0] + M; x + w <= R[2] - M; x += stepX) {
    for (var y = R[1] - M; y - h >= R[3] + M; y -= stepY) {
      var cand = [x, y, x + w, y - h];
      if (overlaps(cand)) continue;
      var dx = (x + w / 2) - acx, dy = (y - h / 2) - acy, dd = dx * dx + dy * dy;
      if (dd < bestD) { bestD = dd; bestPos = [x, y]; }
    }
  }
  if (!bestPos) {
    var sc = 0.45; pi.width = w * sc; pi.height = h * sc; w = pi.width; h = pi.height;
    for (var x2 = R[0] + M; x2 + w <= R[2] - M && !bestPos; x2 += stepX)
      for (var y2 = R[1] - M; y2 - h >= R[3] + M && !bestPos; y2 -= stepY)
        if (!overlaps([x2, y2, x2 + w, y2 - h])) bestPos = [x2, y2];
  }
  if (!bestPos) { log.push(nm + ":NO_FREE_SLOT_ON_AB" + (ai + 1)); continue; }
  pi.position = bestPos;
  occupied.push([bestPos[0], bestPos[1], bestPos[0] + w, bestPos[1] - h]);
  log.push(nm.replace(/\.pdf$/, "") + ":AB" + (ai + 1));
}

var so = new IllustratorSaveOptions(); so.pdfCompatible = true;
d.saveAs(new File(COPY), so);
d.close(SaveOptions.DONOTSAVECHANGES);

var out = "PLACED: " + log.join(" | ");
out += "\nLINKS: " + total + " placed items, " + nolink + " embedded/no-file, " + broken.length + " BROKEN";
for (var bb = 0; bb < broken.length && bb < 25; bb++) out += "\n  BROKEN: " + broken[bb];
out;
