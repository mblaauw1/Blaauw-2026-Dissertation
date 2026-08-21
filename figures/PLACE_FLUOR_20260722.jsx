#target illustrator
// Re-seat the 5 new figures so each sits ON its anchor's artboard, inside the bounds, and overlaps nothing.
// The first pass put them directly under the anchor, which pushed 3 of them off the artboard edge.
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}

var COPY = "/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
var TARGETS = ["G4_sisterless_fluor_postabl_vs_pole.pdf"];
var ANCHOR = { "G4_sisterless_fluor_postabl_vs_pole.pdf": "g4_kt_intensity_time.pdf" };

for (var q = 0; q < app.documents.length; q++) {
  if (app.documents[q].fullName && app.documents[q].fullName.fsName == COPY) throw new Error("ABORT: copy.ai open");
}
var d = app.open(new File(COPY));

function lname(p) { var f = null; try { f = p.file; } catch (e) {} return f ? decodeURI(f.name).toLowerCase() : ""; }

// everything that occupies space (so we can avoid it)
var occupied = [], mine = {}, anchorOf = {};
for (var i = 0; i < d.placedItems.length; i++) {
  var p = d.placedItems[i], n = lname(p), b;
  try { b = p.visibleBounds; } catch (e) { continue; }
  var isTarget = false;
  for (var t = 0; t < TARGETS.length; t++) if (n == TARGETS[t].toLowerCase()) { mine[n] = p; isTarget = true; }
  if (!isTarget) occupied.push(b);
  for (var k in ANCHOR) if (n == ANCHOR[k]) {
    // several figures are placed twice — once off-canvas, once on an artboard. Prefer the ON-artboard
    // copy, otherwise the new figure inherits the off-artboard position (4 failures in the first pass).
    if (!anchorOf[k]) anchorOf[k] = p;
    else {
      var ob = anchorOf[k].visibleBounds, nb = b;
      var onOld = false, onNew = false;
      for (var aa = 0; aa < d.artboards.length; aa++) {
        var rr = d.artboards[aa].artboardRect;
        var ocx=(ob[0]+ob[2])/2, ocy=(ob[1]+ob[3])/2, ncx=(nb[0]+nb[2])/2, ncy=(nb[1]+nb[3])/2;
        if (ocx>=rr[0]&&ocx<=rr[2]&&ocy<=rr[1]&&ocy>=rr[3]) onOld = true;
        if (ncx>=rr[0]&&ncx<=rr[2]&&ncy<=rr[1]&&ncy>=rr[3]) onNew = true;
      }
      if (!onOld && onNew) anchorOf[k] = p;
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
  if (!pi) {                                   // not in the doc yet -> add it linked, then seat it
    var nf = new File("/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/" + nm);
    if (!nf.exists) { log.push(nm + ":NO_PDF"); continue; }
    pi = d.activeLayer.placedItems.add(); pi.file = nf; pi.name = "NEW " + nm;
    if (an) { var abw = an.visibleBounds[2] - an.visibleBounds[0];
              var sc0 = abw / pi.width; pi.width = pi.width * sc0; pi.height = pi.height * sc0; }
  }
  if (!an) { log.push(nm + ":NO_ANCHOR"); continue; }
  // artboard containing the anchor's centre
  var ab = an.visibleBounds, acx = (ab[0] + ab[2]) / 2, acy = (ab[1] + ab[3]) / 2, ai = -1;
  for (var a = 0; a < d.artboards.length; a++) {
    var r = d.artboards[a].artboardRect;
    if (acx >= r[0] && acx <= r[2] && acy <= r[1] && acy >= r[3]) { ai = a; break; }
  }
  if (ai < 0) { log.push(nm + ":ANCHOR_OFF_ARTBOARD"); continue; }
  var R = d.artboards[ai].artboardRect;      // [l,t,r,b]
  var w = pi.width, h = pi.height, M = 12;
  // scan the artboard for a free slot, preferring positions near the anchor
  var bestPos = null, bestD = 1e18;
  var stepX = Math.max(20, w / 3), stepY = Math.max(20, h / 3);
  for (var x = R[0] + M; x + w <= R[2] - M; x += stepX) {
    for (var y = R[1] - M; y - h >= R[3] + M; y -= stepY) {
      var cand = [x, y, x + w, y - h];
      if (overlaps(cand)) continue;
      var dx = (x + w / 2) - acx, dy = (y - h / 2) - acy;
      var dd = dx * dx + dy * dy;
      if (dd < bestD) { bestD = dd; bestPos = [x, y]; }
    }
  }
  if (!bestPos) {
    // nothing free at full size — shrink to fit a free slot
    var sc = 0.45; pi.width = w * sc; pi.height = h * sc; w = pi.width; h = pi.height;
    for (var x2 = R[0] + M; x2 + w <= R[2] - M && !bestPos; x2 += stepX) {
      for (var y2 = R[1] - M; y2 - h >= R[3] + M && !bestPos; y2 -= stepY) {
        var c2 = [x2, y2, x2 + w, y2 - h];
        if (!overlaps(c2)) bestPos = [x2, y2];
      }
    }
  }
  if (!bestPos) { log.push(nm + ":NO_FREE_SLOT_ON_AB" + (ai + 1)); continue; }
  pi.position = bestPos;
  occupied.push([bestPos[0], bestPos[1], bestPos[0] + w, bestPos[1] - h]);
  log.push(nm.replace(/\.pdf$/, "") + ":AB" + (ai + 1));
}

var so = new IllustratorSaveOptions(); so.pdfCompatible = true;
d.saveAs(new File(COPY), so);
d.close(SaveOptions.DONOTSAVECHANGES);
log.join("  |  ");
