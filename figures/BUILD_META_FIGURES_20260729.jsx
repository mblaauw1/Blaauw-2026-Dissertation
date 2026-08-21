// Build the 9-artboard META-FIGURE document (user 2026-07-29f).
//
// Every live figure from copy.ai and the overflow board - 549 of them, i.e. all 590 placed minus the 41
// retired - is copied onto one of 9 boards: her 8 meta-figure topics plus ONE split (M5b), taken from the
// 1-3 splits she allowed because M5 was carrying 183 figures and two separate arguments.
//
// MUST BE BUILT IN ONE SESSION. Reopening a saved .ai to append throws Error 9080 (NOTES section 8), so
// this script creates the document, places all 549, and saves once.
//
// Sizing: each figure is scaled to FIT its cell preserving its own aspect ratio - a cell is a budget, not
// a frame - so nothing is stretched. Boards are ~10,000 x 7,000pt, tiled 3x3 inside the +/-16383 canvas
// limit, which makes the cells LARGER than the figures are in copy.ai rather than smaller.
// Uncertain placements get a red outline, as she asked.
// Layers: `figures`, `labels`, `board_titles`, `uncertain` - PlacedItems always go on `figures`, because
// placedItems.add() otherwise uses the active layer and a later clearLayer() can silently delete them.
#target illustrator
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }

function readFile(p) { var f = new File(p); f.encoding = "UTF-8"; f.open("r"); var s = f.read(); f.close(); return s; }
var IN = "/Volumes/4 MB/_working/_deck_jsx_inputs/";
var L = eval("(" + readFile(IN + "meta_layout.json") + ")");
var P = eval("(" + readFile(IN + "meta_paths.json") + ")");
var OUTFILE = "/Volumes/4 MB/ablation_plots/_superseded_decks/META_FIGURES_20260729.ai";
var ORDER = ["M1", "M2", "M3", "M4", "M5", "M5b", "M6", "M7", "M8"];

// A 1000x1000 initial artboard puts the canvas centre at (500,500); the nine boards are laid out
// centred on that point (see build_meta_layout_20260729.py for the probed window).
var d = app.documents.add(DocumentColorSpace.RGB, 1000, 1000);
var LFIG = d.layers.add(); LFIG.name = "figures";
var LLAB = d.layers.add(); LLAB.name = "labels";
var LRED = d.layers.add(); LRED.name = "uncertain";
var LTIT = d.layers.add(); LTIT.name = "board_titles";

// ---- artboards ----
// ORDER MATTERS. Re-using artboard 0 and SHRINKING it to the first board's 5100pt rect immediately
// re-anchors what Illustrator considers in-range, and the next artboards.add() throws 'CoOA'. So: leave
// the oversized initial artboard alone while all nine real boards are added around it - the union then
// already covers the whole area - and delete it at the very end.
var made = 0;
for (var i = 0; i < ORDER.length; i++) {
  var b = L.boards[ORDER[i]];
  var ab = d.artboards.add(b.rect);
  ab.name = ORDER[i];
  made++;
  var t = LTIT.textFrames.add();
  t.contents = b.title + "     (" + b.n + " figures)";
  t.textRange.characterAttributes.size = 96;
  t.position = [b.rect[0] + 120, b.rect[1] - 120];
}

// ---- figures ----
var placed = 0, failed = [], reds = 0;
for (var f in L.cells) {
  var c = L.cells[f], src = P[f];
  if (!src) { failed.push(f + "(no path)"); continue; }
  var file = new File(src);
  if (!file.exists) { failed.push(f + "(file gone)"); continue; }
  var pi;
  try { pi = LFIG.placedItems.add(); pi.file = file; }
  catch (e1) { failed.push(f + "(add " + e1 + ")"); continue; }
  // FIT, never stretch: one scale factor from whichever axis binds
  var natW = pi.width, natH = pi.height;
  var labelH = 34;                                   // room under the figure for its name
  var availW = c.w, availH = c.h - labelH;
  var s = Math.min(availW / natW, availH / natH);
  pi.width = natW * s; pi.height = natH * s;
  var x = c.x + (c.w - pi.width) / 2;                // centre in the cell
  var y = c.y - (availH - pi.height) / 2;
  pi.position = [x, y];
  pi.name = f;
  placed++;
  var lab = LLAB.textFrames.add();
  lab.contents = f;
  lab.textRange.characterAttributes.size = Math.max(9, Math.min(20, c.w / 60));
  lab.position = [c.x + 4, c.y - availH - 6];
  if (c.red) {                                       // her rule: best guess, then outline it in red
    var r = LRED.pathItems.rectangle(y + 8, x - 8, pi.width + 16, pi.height + 16);
    r.filled = false; r.stroked = true; r.strokeWidth = 6;
    var col = new RGBColor(); col.red = 220; col.green = 30; col.blue = 30;
    r.strokeColor = col;
    reds++;
  }
}

// drop the oversized scaffolding artboard now that the nine real boards define the extent
var dropped = "no";
try {
  for (var a = 0; a < d.artboards.length; a++) {
    if (d.artboards[a].name.indexOf("M") !== 0) { d.artboards.remove(a); dropped = "yes"; break; }
  }
} catch (eD) { dropped = "FAILED " + eD; }

var opts = new IllustratorSaveOptions();
opts.pdfCompatible = false;
var mode = "saved";
try { d.saveAs(new File(OUTFILE), opts); } catch (eS) { mode = "SAVE_FAILED " + eS; }
var nAb = d.artboards.length, nPl = d.placedItems.length;
try { d.close(SaveOptions.DONOTSAVECHANGES); } catch (eC) {}

"artboards=" + made + " placed=" + placed + " red=" + reds + " failed=" + failed.length +
  " docPlacedItems=" + nPl + " artboardsInDoc=" + nAb + " save=" + mode +
  (failed.length ? "\nFAILED: " + failed.slice(0, 12).join("; ") : "");
