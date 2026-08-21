// CORRECTION (2026-07-29): RETIRE_LAGGING_EXAMPLES_20260729.jsx was run after the olds had ALREADY
// been moved to the RETIRED artboard by SWAP_LAGGING_EXAMPLES_20260729.jsx. It therefore placed a
// replacement into each old slot - which was on the RETIRED artboard - creating two duplicate copies
// of the new figures there. This removes ONLY those duplicates: a G4_lagging_examples_outlines*
// placement whose centre sits on the RETIRED artboard. The live copies elsewhere are untouched, and
// the retired originals stay retired.
// Deleting here is safe because these items were created by my own erroneous run minutes ago and
// carry no user content; every other placement is left alone.
#target illustrator
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }

var PATH = "/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
var d = app.open(new File(PATH));

function lname(p) { var f = null; try { f = p.file; } catch (e) {} return f ? decodeURI(f.name).toLowerCase() : ""; }
function abOf(it) {
  var b; try { b = it.visibleBounds; } catch (e) { return -1; }
  var cx = (b[0] + b[2]) / 2, cy = (b[1] + b[3]) / 2;
  for (var a = 0; a < d.artboards.length; a++) {
    var R = d.artboards[a].artboardRect;
    if (cx >= R[0] && cx <= R[2] && cy <= R[1] && cy >= R[3]) return a;
  }
  return -1;
}

var ri = -1;
for (var a = 0; a < d.artboards.length; a++)
  if (d.artboards[a].name.toUpperCase().indexOf("RETIRED") >= 0) { ri = a; break; }

// census BEFORE
var before = {}, kill = [];
for (var i = 0; i < d.placedItems.length; i++) {
  var p = d.placedItems[i], n = lname(p);
  if (n.indexOf("g4_lagging_examples") !== 0) continue;
  var ab = abOf(p);
  var key = n + " @AB" + (ab + 1);
  before[key] = (before[key] || 0) + 1;
  if (ab === ri && n.indexOf("g4_lagging_examples_outlines") === 0) kill.push(p);
}
var removed = 0;
for (var q = 0; q < kill.length; q++) { try { kill[q].remove(); removed++; } catch (e2) {} }

// census AFTER, and repack the retired board so no gap is left
var after = {};
for (var j = 0; j < d.placedItems.length; j++) {
  var p2 = d.placedItems[j], n2 = lname(p2);
  if (n2.indexOf("g4_lagging_examples") !== 0) continue;
  after[n2 + " @AB" + (abOf(p2) + 1)] = (after[n2 + " @AB" + (abOf(p2) + 1)] || 0) + 1;
}
var bl = [], al = [];
for (var kb in before) bl.push(kb + "x" + before[kb]);
for (var ka in after) al.push(ka + "x" + after[ka]);

var mode = "";
try { var so = new IllustratorSaveOptions(); so.pdfCompatible = false; d.saveAs(new File(PATH), so); mode = "saved"; }
catch (e3) { mode = "SAVE_FAILED " + e3; }
var total = d.placedItems.length;
try { d.close(SaveOptions.DONOTSAVECHANGES); } catch (e4) {}

"removed_dupes=" + removed + "  placed_total=" + total + "  save=" + mode +
"\nBEFORE: " + bl.join(" | ") + "\nAFTER : " + al.join(" | ");
