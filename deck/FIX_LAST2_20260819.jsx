// Recover the items FIX_LAST_OVERLAPS parked off-board, and give them a real home.
//
// WHAT HAPPENED: that script parked each item at (90000, 90000) so the free-slot search could not be
// blocked by the group's own members, then searched for a slot. On these two boards there was no slot large
// enough, so it moved 0 of 12 and they were left parked. That is a worse state than an overlap -- an item
// nobody can see is an item she will think is missing -- so it is fixed first and by construction:
//
//   1. scale the board's EXISTING contents down about the board centre (her rule for making room), and
//   2. lay the parked items out in a tidy grid in the strip of board freed at the bottom, so every one of
//      them is on the board, visible, and separately movable.
//
// The grid is computed from the items' own sizes, so nothing is distorted and nothing is left overlapping.
#target illustrator

var TMP = "/Volumes/4 MB/_claude_tmp";
var HB = new File(TMP + "/fix_last2_heartbeat.txt");
function beat(m) { try { HB.open("a"); HB.writeln(m); HB.close(); } catch (e) {} }

var JOBS = [
  // her board-4 item 6: the collagen-free four and the collagen-vs-3-on-target four go on
  // board 4 beside their parents, making room by SCALING THE BOARD'S CONTENTS (her rule), never by
  // spilling onto another artboard.
  { deck: "/Volumes/4 MB/1_DECKS/META_FIGURES_20260814_PUBLICATION_20260820.ai", ab: 4, k: 0.82,
    names: ["G1_roundness_combined_meta_trendscaled_delta_nocollagen", "G1_roundness_combined_meta_trendscaled_delta_collagen_vs_3", "G1_area_combined_meta_trendscaled_delta_nocollagen", "G1_area_combined_meta_trendscaled_delta_collagen_vs_3", "G1_centroid_movement_combined_meta_trendscaled_delta_nocollagen", "G1_centroid_movement_combined_meta_trendscaled_delta_collagen_vs_3", "G1_plate_rotation_combined_meta_trendscaled_delta_nocollagen", "G1_plate_rotation_combined_meta_trendscaled_delta_collagen_vs_3"] }
];

app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
beat("START " + new Date());
var report = [], i, j;

for (var q = 0; q < JOBS.length; q++) {
  var J = JOBS[q];
  var doc = null;
  try { doc = app.open(new File(J.deck)); } catch (e) { report.push("OPEN FAIL " + e); continue; }
  var docName = doc.name;

  var lockState = [];
  for (i = 0; i < doc.layers.length; i++) {
    var Ly = doc.layers[i], st = { lay: Ly, lk: false };
    try { st.lk = Ly.locked; Ly.locked = false; } catch (e) {}
    lockState.push(st);
  }

  var abi = J.ab - 1;
  var R = doc.artboards[abi].artboardRect;    // [L,T,R,B]
  var cx = (R[0] + R[2]) / 2.0, cy = (R[1] + R[3]) / 2.0;

  // collect the parked/homeless items by name
  var mine = [];
  for (i = 0; i < doc.pageItems.length; i++) {
    var p = doc.pageItems[i], nm = "";
    try { nm = p.name || ""; } catch (e) {}
    for (j = 0; j < J.names.length; j++) if (nm === J.names[j]) { mine.push(p); break; }
  }

  // 1. shrink what is ON the board (excluding our homeless items) about the board centre
  var n = 0;
  for (i = 0; i < doc.pageItems.length; i++) {
    var it = doc.pageItems[i];
    var skip = false;
    for (j = 0; j < mine.length; j++) if (mine[j] === it) { skip = true; break; }
    if (skip) continue;
    var b = null;
    try { b = it.visibleBounds; } catch (e) { continue; }
    try { if (it.parent.typename !== "Layer") continue; } catch (e) { continue; }
    if (!(b[0] >= R[0] - 1 && b[2] <= R[2] + 1 && b[1] <= R[1] + 1 && b[3] >= R[3] - 1)) continue;
    var ccx = (b[0] + b[2]) / 2.0, ccy = (b[1] + b[3]) / 2.0;
    try {
      it.resize(J.k * 100, J.k * 100);
      var nb = it.visibleBounds, nw = nb[2] - nb[0], nh = nb[1] - nb[3];
      it.left = cx + (ccx - cx) * J.k - nw / 2.0;
      it.top = cy + (ccy - cy) * J.k + nh / 2.0;
      n++;
    } catch (e) {}
  }

  // 2. find the lowest occupied y on the board -> the free strip below it is where ours go
  var lowest = R[1];
  for (i = 0; i < doc.pageItems.length; i++) {
    var it2 = doc.pageItems[i];
    var sk = false;
    for (j = 0; j < mine.length; j++) if (mine[j] === it2) { sk = true; break; }
    if (sk) continue;
    var b2 = null;
    try { b2 = it2.visibleBounds; } catch (e) { continue; }
    try { if (it2.parent.typename !== "Layer") continue; } catch (e) { continue; }
    if (b2[0] < R[2] && b2[2] > R[0] && b2[3] < R[1] && b2[1] > R[3]) { if (b2[3] < lowest) lowest = b2[3]; }
  }
  var stripTop = lowest - 40, stripH = stripTop - (R[3] + 30), boardW = (R[2] - R[0]) - 60;
  if (stripH < 60) { stripTop = R[3] + 30 + 400; stripH = 400; }   // degenerate board: still put them ON it

  // 3. lay ours out in a grid inside that strip, uniformly scaled to fit
  var cols = Math.ceil(Math.sqrt(mine.length));
  var rowsN = Math.ceil(mine.length / cols);
  var cellW = (boardW - 12 * (cols - 1)) / cols;
  var cellH = (stripH - 12 * (rowsN - 1)) / rowsN;
  var placed = 0;
  for (i = 0; i < mine.length; i++) {
    var g = mine[i];
    var s = Math.min(cellW / g.width, cellH / g.height);
    if (s > 0 && s !== 1) { try { g.resize(s * 100, s * 100); } catch (e) {} }
    var c = i % cols, r = Math.floor(i / cols);
    g.left = R[0] + 30 + c * (cellW + 12);
    g.top = stripTop - r * (cellH + 12);
    placed++;
  }

  for (i = 0; i < lockState.length; i++) { try { lockState[i].lay.locked = lockState[i].lk; } catch (e) {} }
  try { doc.selection = null; } catch (e) {}
  var o = new IllustratorSaveOptions();
  o.compatibility = Compatibility.ILLUSTRATOR17; o.pdfCompatible = false;
  doc.saveAs(new File(J.deck), o);
  doc.close(SaveOptions.SAVECHANGES);
  report.push(docName + "\tAB" + J.ab + "\tshrank " + n + " by " + J.k + "\tplaced " + placed + " in the freed strip");
  beat(docName + " ab" + J.ab + " shrank=" + n + " placed=" + placed);
}

var rf = new File(TMP + "/fix_last2_report.txt"); rf.encoding = "UTF-8"; rf.open("w");
for (i = 0; i < report.length; i++) rf.writeln(report[i]);
rf.close();
app.userInteractionLevel = UserInteractionLevel.DISPLAYALERTS;
beat("ALLDONE " + new Date());
"ALLDONE";
