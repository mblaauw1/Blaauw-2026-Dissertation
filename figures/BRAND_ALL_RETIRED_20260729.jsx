// Brand EVERY figure sitting on the RETIRED artboard (user 2026-07-29: "make sure all plots on the
// retire artboard are also branded with the retirement brand? just to reinforce clarity of their state").
//
// The brand is the existing convention on layer RETIRED_MARKS: a red (220,30,30) stroke-only rectangle
// around the figure plus a small red "RETIRED" caption. Red is used ONLY here - it is not one of the
// four content conventions (yellow = statistically significant, brown = revived, blue = model,
// grey = family group) - so a red box anywhere else would be mislabelling a live figure.
//
// Idempotent: a figure that already carries a brand is skipped, so re-running adds nothing.
// Also reports the composition of REVIVED_OUTLINE, which held 138 items but only 5 brown paths.
// NOTE: every document value is read BEFORE d.close() - reading after it raises Error 45.
#target illustrator
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }

var PATH = "/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
var d = app.open(new File(PATH));

var ri = -1;
for (var a = 0; a < d.artboards.length; a++)
  if (d.artboards[a].name.toUpperCase().indexOf("RETIRED") >= 0) { ri = a; break; }
if (ri < 0) throw new Error("no RETIRED artboard");

function abOf(it) {
  var b; try { b = it.visibleBounds; } catch (e) { return -1; }
  var cx = (b[0] + b[2]) / 2, cy = (b[1] + b[3]) / 2;
  for (var q = 0; q < d.artboards.length; q++) {
    var R = d.artboards[q].artboardRect;
    if (cx >= R[0] && cx <= R[2] && cy <= R[1] && cy >= R[3]) return q;
  }
  return -1;
}
function lname(p) { var f = null; try { f = p.file; } catch (e) {} return f ? decodeURI(f.name).replace(/\.(pdf|png)$/i, "") : ""; }

var RL;
try { RL = d.layers.getByName("RETIRED_MARKS"); } catch (e) { RL = d.layers.add(); RL.name = "RETIRED_MARKS"; }

// which figures on the retired board already carry a brand? match by the rect's name
var branded = {};
for (var i = 0; i < RL.pageItems.length; i++) {
  var nm = String(RL.pageItems[i].name || "");
  if (nm.indexOf("RETIREDBOX ") === 0) branded[nm.substring(11).toLowerCase()] = 1;
}

var red = new RGBColor(); red.red = 220; red.green = 30; red.blue = 30;
var onBoard = [], added = 0, already = 0;
for (var p = 0; p < d.placedItems.length; p++) {
  var it = d.placedItems[p];
  if (abOf(it) !== ri) continue;
  var n = lname(it);
  if (!n) continue;
  onBoard.push(n);
  if (branded[n.toLowerCase()]) { already++; continue; }
  var b; try { b = it.visibleBounds; } catch (e) { continue; }
  var M = 5;
  try {
    var r = RL.pathItems.rectangle(b[1] + M, b[0] - M, (b[2] - b[0]) + 2 * M, (b[1] - b[3]) + 2 * M);
    r.filled = false; r.stroked = true; r.strokeColor = red; r.strokeWidth = 1.6;
    r.name = "RETIREDBOX " + n;
    var t = RL.textFrames.add();
    t.contents = "RETIRED";
    t.textRange.characterAttributes.size = 7;
    t.textRange.characterAttributes.fillColor = red;
    t.top = b[1] + M + 8; t.left = b[0] - M;
    t.name = "RETIREDTAG " + n;
    added++;
  } catch (e2) {}
}

// REVIVED_OUTLINE composition, captured BEFORE the close
var revComp = [];
try {
  var VL = d.layers.getByName("REVIVED_OUTLINE");
  var agg = {};
  for (var v = 0; v < VL.pageItems.length; v++) {
    var tt = VL.pageItems[v].typename;
    agg[tt] = (agg[tt] || 0) + 1;
  }
  for (var kk in agg) revComp.push(agg[kk] + "x " + kk);
} catch (e3) { revComp.push("layer absent"); }

var nOn = onBoard.length, nMarks = RL.pageItems.length, abName = d.artboards[ri].name;
var mode = "";
try { var so = new IllustratorSaveOptions(); so.pdfCompatible = false; d.saveAs(new File(PATH), so); mode = "saved"; }
catch (e4) { mode = "SAVE_FAILED " + e4; }
try { d.close(SaveOptions.DONOTSAVECHANGES); } catch (e5) {}

"retired board = AB" + (ri + 1) + " '" + abName + "'  figures_on_it=" + nOn +
"  newly_branded=" + added + "  already_branded=" + already +
"  RETIRED_MARKS_items_now=" + nMarks +
"\nREVIVED_OUTLINE composition: " + revComp.join(", ") +
"\nsave=" + mode;
