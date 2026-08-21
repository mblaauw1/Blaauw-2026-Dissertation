#target illustrator
// Swap the circle-based lagging-example figures for the manual-outline rebuild (user 2026-07-29).
//   G4_lagging_examples.pdf          (AB13, AB27) -> G4_lagging_examples_outlines.pdf
//   G4_lagging_examples_outlined.pdf (AB13)       -> G4_lagging_examples_outlines_traced.pdf
// The originals are MOVED to the RETIRED artboard, never deleted, so this is reversible.
// New figures take the exact slot (position + width) of the ones they replace; height follows the
// new file's own aspect ratio so nothing is distorted.
// Also reports any SIGHILITE shape naming an old figure, so a highlight is not silently orphaned.
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }

var COPY = "/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
var PDFDIR = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/";
var MAP = {};
MAP["g4_lagging_examples.pdf"]          = "G4_lagging_examples_outlines.pdf";
MAP["g4_lagging_examples_outlined.pdf"] = "G4_lagging_examples_outlines_traced.pdf";

var d = app.open(new File(COPY));
function lname(p) { var f = null; try { f = p.file; } catch (e) {} return f ? decodeURI(f.name).toLowerCase() : ""; }

// ---- 1. find the originals ----
var olds = [];
for (var i = 0; i < d.placedItems.length; i++) {
  var nm = lname(d.placedItems[i]);
  if (MAP[nm]) olds.push({ it: d.placedItems[i], src: nm });
}

// ---- 2. place each replacement into the slot its original occupies ----
var placed = 0, errs = [];
for (var k = 0; k < olds.length; k++) {
  var o = olds[k].it, tgt = MAP[olds[k].src];
  var pos, w;
  try { pos = o.position; w = o.width; } catch (e) { errs.push("bounds " + olds[k].src); continue; }
  var f = new File(PDFDIR + tgt);
  if (!f.exists) { errs.push("missing " + tgt); continue; }
  try {
    var pi = d.placedItems.add();
    pi.file = f;
    var ratio = pi.height / pi.width;
    pi.width = w; pi.height = w * ratio;
    pi.position = pos;
    pi.name = tgt.replace(/\.pdf$/i, "");
    placed++;
  } catch (e2) { errs.push("place " + tgt + " " + e2); }
}

// ---- 3. move the originals onto the RETIRED artboard and repack it ----
var ri = -1;
for (var a = 0; a < d.artboards.length; a++)
  if (d.artboards[a].name.toUpperCase().indexOf("RETIRED") >= 0) { ri = a; break; }
var packed = 0, abname = "";
if (ri >= 0) {
  abname = d.artboards[ri].name;
  var R = d.artboards[ri].artboardRect;   // [l,t,r,b]
  var members = [];
  for (var i2 = 0; i2 < d.placedItems.length; i2++) {
    var p = d.placedItems[i2], b;
    try { b = p.visibleBounds; } catch (e) { continue; }
    var cx = (b[0] + b[2]) / 2, cy = (b[1] + b[3]) / 2;
    var onRet = (cx >= R[0] && cx <= R[2] && cy <= R[1] && cy >= R[3]);
    var isOld = false;
    for (var q = 0; q < olds.length; q++) if (olds[q].it === p) isOld = true;
    if (onRet || isOld) members.push(p);
  }
  var n = members.length;
  var cols = Math.ceil(Math.sqrt(n)), rows = Math.ceil(n / cols);
  var M = 18, GAP = 10;
  var cw = ((R[2] - R[0]) - 2 * M - (cols - 1) * GAP) / cols;
  var ch = ((R[1] - R[3]) - 2 * M - (rows - 1) * GAP) / rows;
  for (var m = 0; m < n; m++) {
    var it = members[m], iw = it.width, ih = it.height;
    var s = Math.min(cw / iw, ch / ih);      // uniform -- never distorts
    it.width = iw * s; it.height = ih * s;
    var c = m % cols, r2 = Math.floor(m / cols);
    it.position = [R[0] + M + c * (cw + GAP) + (cw - it.width) / 2,
                   R[1] - M - r2 * (ch + GAP) - (ch - it.height) / 2];
  }
  packed = n;
}

// ---- 4. report SIGHILITE shapes naming an old figure (do not touch them) ----
var sig = [];
for (var L = 0; L < d.pathItems.length; L++) {
  var pn = "";
  try { pn = d.pathItems[L].name || ""; } catch (e) {}
  var low = pn.toLowerCase();
  if (low.indexOf("lagging_examples") >= 0) sig.push(pn);
}

var mode = "";
try { var opt = new IllustratorSaveOptions(); opt.pdfCompatible = false; d.saveAs(new File(COPY), opt); mode = "saved"; }
catch (e3) { mode = "SAVE_FAILED " + e3; }

"olds_found=" + olds.length + "  replacements_placed=" + placed +
"  retired_artboard=AB" + (ri + 1) + " '" + abname + "' total_now=" + packed +
"  sighilite_naming_old=[" + sig.join("|") + "]" +
"  errors=[" + errs.join("; ") + "]  save=" + mode +
"  placed_total=" + d.placedItems.length;
