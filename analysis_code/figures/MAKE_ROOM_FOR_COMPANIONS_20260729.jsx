// Make room on the four artboards whose companions could not be placed (user 2026-07-29d).
//
// Measured situation, which splits the four into two different problems:
//   AB25 (510x455, ONE figure 450x300) and AB26 (783x455, ONE figure 723x300) are single-figure boards on
//     the BOTTOM ROW with open canvas beneath them (no artboard below within 18,000pt). They are not full,
//     they are simply too SMALL. -> GROW the artboard downward. Nothing moves, nothing is scaled.
//   AB17 (3046x750, 12 figs, 54% full) and AB22 (3025x2151, 42 figs, 71% full) are boxed in on all four
//     sides by a 260pt gutter, so they cannot grow. -> SCALE THEIR CONTENTS DOWN IN PLACE.
//
// HOW THE SCALING IS DONE (her requirement: scale uniformly, and do not let anything end up floating off
// the artboard). Every page item whose CENTRE lies on the artboard is scaled by the SAME factor S in x and
// y - never a non-uniform stretch - and repositioned about the artboard's TOP-LEFT corner:
//     new_pos = anchor + (old_pos - anchor) * S
// Anchoring at the corner the contents are already inside guarantees that scaling can only move an item
// TOWARDS the anchor, so an item that was on the artboard stays on it. The artboard RECT is left unchanged,
// so the freed space appears as an L-shaped band along the right and bottom edges, which is where the
// companions then go. All layers are scaled together (figures, captions, and the mark layers) so nothing
// drifts out of register; the mark layers are regenerated afterwards anyway.
//
// S = 0.85 gives AB22 a 454pt x 323pt band and AB17 a 457pt x 113pt band, against a biggest-figure size of
// 440x327 on AB22 and 407x310 on AB17 - and the companions are placed at their PARENT's new width, so they
// shrink by the same factor and stay visually matched to the figure they belong to.
#target illustrator
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }

var PATH = "/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
var GROW  = { "25": 328, "26": 328 };     // extra height in pt (figure height 300 + 28pt gap)
var SCALE = { "17": 0.85, "22": 0.85 };
var CANVAS_FLOOR = -16000;                // stay inside Illustrator's +/-16383 coordinate limit

var d = app.open(new File(PATH));
var report = [];

// ---------- 1. grow the two single-figure boards downward ----------
for (var key in GROW) {
  var gi = parseInt(key, 10) - 1;
  if (gi < 0 || gi >= d.artboards.length) { report.push("AB" + key + ": out of range"); continue; }
  var ab = d.artboards[gi], R = ab.artboardRect;
  var want = R[3] - GROW[key];
  if (want < CANVAS_FLOOR) { report.push("AB" + key + ": would pass the canvas floor - SKIPPED"); continue; }
  ab.artboardRect = [R[0], R[1], R[2], want];
  report.push("AB" + key + ": height " + Math.round(R[1] - R[3]) + " -> " + Math.round(R[1] - want) + "pt (grown down)");
}

// ---------- 2. scale the two boxed-in boards' contents in place ----------
function centreOn(it, R) {
  var b; try { b = it.visibleBounds; } catch (e) { return false; }
  var cx = (b[0] + b[2]) / 2, cy = (b[1] + b[3]) / 2;
  return cx >= R[0] && cx <= R[2] && cy <= R[1] && cy >= R[3];
}
for (var skey in SCALE) {
  var si = parseInt(skey, 10) - 1;
  if (si < 0 || si >= d.artboards.length) { report.push("AB" + skey + ": out of range"); continue; }
  var SR = d.artboards[si].artboardRect;
  var S = SCALE[skey], ax = SR[0], ay = SR[1];      // anchor = artboard TOP-LEFT
  var n = 0, failed = 0;
  // collect first - resizing while walking d.pageItems is unsafe
  var todo = [];
  for (var i = 0; i < d.pageItems.length; i++) { if (centreOn(d.pageItems[i], SR)) todo.push(d.pageItems[i]); }
  for (var j = 0; j < todo.length; j++) {
    var it = todo[j];
    try {
      var px = it.position[0], py = it.position[1];
      it.resize(S * 100, S * 100, true, true, true, true, S * 100, Transformation.TOPLEFT);
      it.position = [ax + (px - ax) * S, ay + (py - ay) * S];
      n++;
    } catch (eS) { failed++; }
  }
  report.push("AB" + skey + ": scaled " + n + " items by " + S + " about the artboard top-left (" +
              failed + " failed); freed band " + Math.round((SR[2] - SR[0]) * (1 - S)) + "pt wide x " +
              Math.round((SR[1] - SR[3]) * (1 - S)) + "pt tall");
}

var opts = new IllustratorSaveOptions();
opts.pdfCompatible = false;
var mode = "saved";
try { d.saveAs(new File(PATH), opts); } catch (eSv) { mode = "SAVE_FAILED " + eSv; }
try { d.close(SaveOptions.DONOTSAVECHANGES); } catch (eC) {}
report.push("save=" + mode);
report.join("\n");
