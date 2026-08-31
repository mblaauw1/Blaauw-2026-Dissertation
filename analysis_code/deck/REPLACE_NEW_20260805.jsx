// Put today's new figures on ONE artboard directly BELOW the existing NEW_FIGURES board.
//
// USER 2026-08-05: "when i see the new figure artboard, all of the actual plots are to the side of the
// artbord, not on it."
//
// She is right about the effect, though not the cause: each figure WAS inside its own artboard
// (measured: G6tenM_polar_vs_paired_percell at left=1650,w=759 inside artboard [1580..2480]). The mistake
// was mine at the design level — I appended SIX SEPARATE artboards strung out to the right, x 1580 to
// 7880, so from the main board they read as floating off to the side. "Append without disturbing her
// layout" is not the same as "put it where she will find it".
//
// This undoes that and does it properly:
//   1. removes the artboards I created (matched by name against MINE) and the items on them
//   2. adds ONE artboard directly below artboard 1, sized for a 4-column grid
//   3. places all 14 figures into that grid, in reading order
// Artboard 1 and its 25 original figures are never touched.

app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
var L = new File("/Volumes/4 MB/ablation_plots/REPLACE_LOG_20260805.txt"); L.open("w");
function s(x) { L.writeln(x); L.close(); L.open("e"); L.seek(0, 2); }

var F = "/Volumes/4 MB/ablation_figures_20260625/";
var P = F + "_ai_relink/pdf/";
// heavy scatter figures go in as PNG; the rest as vector PDF
var MINE = [
  ["G6tenM_polar_vs_paired_percell",        P + "G6tenM_polar_vs_paired_percell.pdf"],
  ["G6_polar_distortion_single_vs_triple",  P + "G6_polar_distortion_single_vs_triple.pdf"],
  ["G6_polar_distortion_vs_chromolen_single", P + "G6_polar_distortion_vs_chromolen_single.pdf"],
  ["G6_polar_distortion_vs_chromolen_1v3",  P + "G6_polar_distortion_vs_chromolen_1v3.pdf"],
  ["G6_area_vs_distortion_over_metaphase",  P + "G6_area_vs_distortion_over_metaphase.pdf"],
  ["G4_oscillation_1v3_cohort",             P + "G4_oscillation_1v3_cohort.pdf"],
  ["G6trk_circ_vs_ttana_4group",            F + "group6_tracks/G6trk_circ_vs_ttana_4group.png"],
  ["G6trk_speed_vs_ttana_4group",           F + "group6_tracks/G6trk_speed_vs_ttana_4group.png"],
  ["G6trk_distance_per_min_4group",         F + "group6_tracks/G6trk_distance_per_min_4group.png"],
  ["G6trk_distance_cumulative_4group",      F + "group6_tracks/G6trk_distance_cumulative_4group.png"],
  ["G2_ablmeta_vs_duration_single",         P + "G2_ablmeta_vs_duration_single.pdf"],
  ["G2_ablmeta_vs_duration_triple",         P + "G2_ablmeta_vs_duration_triple.pdf"],
  ["G3_lagging_by_creation_phase",          P + "G3_lagging_by_creation_phase.pdf"],
  ["G4_congressed_bar",                     P + "G4_congressed_bar.pdf"]
];

if (app.documents.length > 0) { s("ABORT: document already open"); L.close(); }
else {
  var isMine = {};
  for (var m = 0; m < MINE.length; m++) isMine[MINE[m][0]] = true;

  var file = new File("/Volumes/4 MB/1_DECKS/NEW_FIGURES_20260804.ai");
  var doc = app.open(file);
  s("opened: " + doc.artboards.length + " artboards, " + doc.placedItems.length + " placed");

  // 1. remove the placed items I added, then the artboards I added
  var removed = 0;
  for (var i = doc.placedItems.length - 1; i >= 0; i--) {
    var nm = "";
    try { nm = doc.placedItems[i].file.name.replace(/\.(pdf|png|svg)$/i, ""); } catch (e) { continue; }
    if (isMine[nm]) { doc.placedItems[i].remove(); removed++; }
  }
  var abRemoved = 0;
  for (var a = doc.artboards.length - 1; a >= 1; a--) {      // never index 0
    if (isMine[doc.artboards[a].name]) { doc.artboards[a].remove(); abRemoved++; }
  }
  s("cleared " + removed + " item(s) and " + abRemoved + " artboard(s) from the earlier attempt");

  // 2. one artboard directly BELOW artboard 1
  var r0 = doc.artboards[0].artboardRect;                    // [left, top, right, bottom]
  var COLS = 4, CW = 900, CH = 640, PAD = 70;
  var ROWS = Math.ceil(MINE.length / COLS);
  var boardW = COLS * CW + PAD * 2, boardH = ROWS * CH + PAD * 2;
  var bx = r0[0], byTop = r0[3] - 200;                       // 200 pt gap under artboard 1
  var nb = doc.artboards.add([bx, byTop, bx + boardW, byTop - boardH]);
  nb.name = "NEW 2026-08-05";
  s("new artboard [" + Math.round(bx) + "," + Math.round(byTop) + "," +
    Math.round(bx + boardW) + "," + Math.round(byTop - boardH) + "]  " + COLS + "x" + ROWS + " grid");

  // 3. fill the grid
  var placed = 0, missing = 0;
  var opts = new IllustratorSaveOptions(); opts.pdfCompatible = false;
  for (var k = 0; k < MINE.length; k++) {
    var figName = MINE[k][0], pf = new File(MINE[k][1]);
    if (!pf.exists) { missing++; s("  MISSING: " + figName); continue; }
    var col = k % COLS, row = Math.floor(k / COLS);
    var cx = bx + PAD + col * CW, cyTop = byTop - PAD - row * CH;
    var pi = doc.placedItems.add();
    pi.file = pf;
    var sc = Math.min((CW - 60) / pi.width, (CH - 60) / pi.height);
    pi.width *= sc; pi.height *= sc;
    pi.left = cx + (CW - pi.width) / 2;
    pi.top  = cyTop - (CH - pi.height) / 2;
    doc.saveAs(file, opts);                                  // save per figure: the run is resumable
    s("  placed " + figName + "  (r" + (row + 1) + "c" + (col + 1) + ", saved)");
    placed++;
  }
  doc.close(SaveOptions.DONOTSAVECHANGES);
  s("placed " + placed + ", missing " + missing);
  s("DONE");
  L.close();
}
