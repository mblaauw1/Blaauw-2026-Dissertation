#target illustrator
// Re-seat the 5 new figures so each sits ON its anchor's artboard, inside the bounds, and overlaps nothing.
// The first pass put them directly under the anchor, which pushed 3 of them off the artboard edge.
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}

var COPY = "/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
var TARGETS = ["G4_oscillation_vs_plate_distance.pdf",
               "G4_oscillation_vs_time_to_event.pdf",
               "G4_polar_position_vs_time_to_anaphase.pdf",
               "G3_length_vs_precongression_plate_distance.pdf",
               "G3_position_along_plate_normal_vs_behavior.pdf"];
var ANCHOR = { "G4_oscillation_vs_plate_distance.pdf": "g4_velocity_vs_distance.pdf",
               "G4_oscillation_vs_time_to_event.pdf": "g4_oscillation.pdf",
               "G4_polar_position_vs_time_to_anaphase.pdf": "g4_plate_distance_time.pdf",
               "G3_length_vs_precongression_plate_distance.pdf": "g3_length_vs_mitotic_time.pdf",
               "G3_position_along_plate_normal_vs_behavior.pdf": "g3_ablation_location_vs_behavior.pdf" };

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
  for (var k in ANCHOR) if (n == ANCHOR[k] && !anchorOf[k]) anchorOf[k] = p;
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
  if (!pi) { log.push(nm + ":NOT_FOUND"); continue; }
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
    var sc = 0.6; pi.width = w * sc; pi.height = h * sc; w = pi.width; h = pi.height;
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
