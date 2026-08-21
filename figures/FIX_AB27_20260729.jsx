// Repair AB27 in copy.ai (user 2026-07-29g).
//
// AB27 "Sisterless-KT behavior vs metaphase duration" is 1539x455 and measures 161% full, because FOUR
// placements sit at the canvas ORIGIN, hanging off its left and top edges instead of on the board:
//   G5shape_major (538x365 at 0,365), G5shape_cytosol_relax_accuracy (553x365 at 0,365),
//   G4_oscillation_effective (493x362 at 0,362) - all three stacked on each other - and
//   G5shape_major_zoom (538x304 at 552,365).
// Position (0, ~365) with no offset is the signature of a placement whose position was never set. Verified
// against copy_pre_deckpass_20260729.ai: identical coordinates, so this predates all of today's work.
//
// They are MOVED, never deleted: each of these four figures is also referenced elsewhere in copy.ai, and
// duplicates in this deck are intentional (her paper-figure copies), so deleting one is not a safe call.
// AB27 grows downward into free canvas (nothing sits below it for ~3,100pt) and the four go in a second
// row beneath the four G4_sisbehav_* figures that were already correctly placed.
//
// Only placements that are BOTH one of the four names AND currently off the board are touched - a correctly
// placed copy of the same figure elsewhere in the document is left alone.
#target illustrator
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }

var PATH = "/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
var WANT = {"g5shape_major": 1, "g5shape_cytosol_relax_accuracy": 1,
            "g5shape_major_zoom": 1, "g4_oscillation_effective": 1};
var GROW = 330;          // new row height + gaps
var CELL_W = 366;        // 4 across: 4*366 + 3*12 = 1500 inside a 1539pt board
var GAP = 12;

var d = app.open(new File(PATH));
var ab = d.artboards[26];                       // AB27
var R = ab.artboardRect;
var newBottom = R[3] - GROW;
ab.artboardRect = [R[0], R[1], R[2], newBottom];

function lname(p) {
  var f = null; try { f = p.file; } catch (e) {}
  return f ? decodeURI(f.name).toLowerCase().replace(/\.(pdf|png)$/, "") : "";
}
// collect the strays: right name, and centred outside the ORIGINAL board rect
var strays = [];
for (var i = 0; i < d.placedItems.length; i++) {
  var it = d.placedItems[i], n = lname(it), b;
  if (!WANT[n]) continue;
  try { b = it.visibleBounds; } catch (e2) { continue; }
  var offBoard = (b[0] < R[0] - 1 || b[1] > R[1] + 1);
  var nearOrigin = (b[0] > -50 && b[0] < 700 && b[1] > 200 && b[1] < 500);
  if (offBoard && nearOrigin) strays.push([n, it]);
}
strays.sort(function (a, b2) { return a[0] < b2[0] ? -1 : 1; });

var moved = [];
for (var k = 0; k < strays.length; k++) {
  var nm = strays[k][0], pi = strays[k][1];
  var s = CELL_W / pi.width;                    // uniform - fit to the cell width, keep the aspect
  pi.width = pi.width * s; pi.height = pi.height * s;
  var x = R[0] + 14 + k * (CELL_W + GAP);
  var y = R[3] - 24;                            // just under the ORIGINAL board floor, inside the new one
  pi.position = [x, y];
  moved.push(nm + " -> [" + Math.round(x) + "," + Math.round(y) + "] " +
             Math.round(pi.width) + "x" + Math.round(pi.height));
}

var opts = new IllustratorSaveOptions();
opts.pdfCompatible = false;
var mode = "saved";
try { d.saveAs(new File(PATH), opts); } catch (eS) { mode = "SAVE_FAILED " + eS; }
try { d.close(SaveOptions.DONOTSAVECHANGES); } catch (eC) {}

"AB27 height " + Math.round(R[1] - R[3]) + " -> " + Math.round(R[1] - newBottom) +
  "pt; moved " + moved.length + " stray placements onto the board; save=" + mode +
  (moved.length ? "\n   " + moved.join("\n   ") : "");
