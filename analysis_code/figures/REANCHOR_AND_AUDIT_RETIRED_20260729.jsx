// Re-anchor the highlight rectangles to their figures, and audit retirement branding (2026-07-29).
//
// WHY: relinking + moving figures during the 2026-07-29 rebuild left the highlight rectangles behind
// at their old coordinates, so they no longer sit behind the plot they describe.
//
// THE THREE MARKS (conventions from feedback_copyai_significance_highlights + NOTES):
//   SIG_HIGHLIGHT   soft-yellow (255,238,120) rounded rect, ~38% opacity, BEHIND a plot whose data
//                   shows a statistically significant relationship (p<0.05).
//   REVIVED_OUTLINE brown (139,69,19) 3pt STROKE-ONLY rect around a figure brought back out of
//                   retirement - stroke-only so a yellow highlight still reads through it.
//   MODEL_HIGHLIGHT blue panel behind the model figures.
// Each rect is NAMED for its target figure, which is how they are re-paired here.
//
// PASS 1  re-anchor every named rect to its target's current visibleBounds (+ per-layer margin).
// PASS 2  audit: which placed figures sit on a NON-retired artboard while carrying retirement
//         branding - either an Illustrator "RETIRED" text object over them, or one of the four
//         figures whose PNG has the watermark BAKED IN by lib.mark_retired (those cannot be fixed
//         from Illustrator; they need a builder edit + re-render, so they are only reported).
#target illustrator
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }

var PATH = "/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
var MARGIN = { "SIG_HIGHLIGHT": 16, "REVIVED_OUTLINE": 6, "MODEL_HIGHLIGHT": 16 };
// PNGs with the watermark drawn INTO the image by lib.mark_retired()
var BAKED = {};
BAKED["collagen_vs_triple_area"] = 1; BAKED["collagen_vs_triple_roundness"] = 1;
BAKED["g2_phase_split_violin"] = 1;   BAKED["g2_phase_split_violin_journal"] = 1;

var d = app.open(new File(PATH));
function lname(p) { var f = null; try { f = p.file; } catch (e) {} return f ? decodeURI(f.name).toLowerCase().replace(/\.(pdf|png)$/, "") : ""; }
function abOf(it) {
  var b; try { b = it.visibleBounds; } catch (e) { return -1; }
  var cx = (b[0] + b[2]) / 2, cy = (b[1] + b[3]) / 2;
  for (var a = 0; a < d.artboards.length; a++) {
    var R = d.artboards[a].artboardRect;
    if (cx >= R[0] && cx <= R[2] && cy <= R[1] && cy >= R[3]) return a;
  }
  return -1;
}
var retAb = -1;
for (var a0 = 0; a0 < d.artboards.length; a0++)
  if (d.artboards[a0].name.toUpperCase().indexOf("RETIRED") >= 0) { retAb = a0; break; }

// index placed figures by linked-file basename
var byName = {};
for (var i = 0; i < d.placedItems.length; i++) {
  var n = lname(d.placedItems[i]);
  if (n) { if (!byName[n]) byName[n] = []; byName[n].push(d.placedItems[i]); }
}

// ---------- PASS 1: re-anchor ----------
var moved = 0, unmatched = [], checked = 0;
for (var L = 0; L < d.pathItems.length; L++) {
  var pi = d.pathItems[L], lay = "";
  try { lay = pi.layer.name; } catch (e) { continue; }
  if (!(lay in MARGIN)) continue;
  checked++;
  // rect names read "SIGHILITE <fig>", "REVIVED <fig>", "MODELBOX <fig>" - SPACE separated, and the
  // model one is MODELBOX not MODEL. An earlier version stripped only "sighilite|revived|model" with an
  // optional _/- and so matched nothing at all (0 of 107 re-anchored).
  var nm = (pi.name || "").toLowerCase().replace(/\.(pdf|png)$/, "");
  nm = nm.replace(/^(sighilite|revived|modelbox|model)[\s_\-]+/, "");
  var tgt = byName[nm];
  if (!tgt || !tgt.length) { if (unmatched.length < 14) unmatched.push(pi.name || "(unnamed)"); continue; }
  var b = tgt[0].visibleBounds, m = MARGIN[lay];
  var nb = [b[0] - m, b[1] + m, b[2] + m, b[3] - m];
  var cur = pi.visibleBounds;
  if (Math.abs(cur[0] - nb[0]) > 1 || Math.abs(cur[1] - nb[1]) > 1 ||
      Math.abs(cur[2] - nb[2]) > 1 || Math.abs(cur[3] - nb[3]) > 1) {
    try {
      pi.position = [nb[0], nb[1]];
      pi.width = nb[2] - nb[0]; pi.height = nb[1] - nb[3];
      moved++;
    } catch (e2) {}
  }
}

// ---------- PASS 2: retirement branding on non-retired artboards ----------
var textRetired = [], bakedOffboard = [];
for (var t = 0; t < d.textFrames.length; t++) {
  var tf = d.textFrames[t], txt = "";
  try { txt = String(tf.contents); } catch (e) {}
  if (txt.toUpperCase().indexOf("RETIRED") < 0) continue;
  var ab = abOf(tf);
  if (ab !== retAb && textRetired.length < 30) textRetired.push("AB" + (ab + 1) + " :: " + txt.substring(0, 46));
}
for (var nm2 in byName) {
  if (!BAKED[nm2]) continue;
  for (var q = 0; q < byName[nm2].length; q++) {
    var ab2 = abOf(byName[nm2][q]);
    if (ab2 !== retAb) bakedOffboard.push(nm2 + " @AB" + (ab2 + 1));
  }
}

var mode = "";
try { var so = new IllustratorSaveOptions(); so.pdfCompatible = false; d.saveAs(new File(PATH), so); mode = "saved"; }
catch (e3) { mode = "SAVE_FAILED " + e3; }
var nAb = d.artboards.length, retName = (retAb >= 0 ? d.artboards[retAb].name : "-");
try { d.close(SaveOptions.DONOTSAVECHANGES); } catch (e4) {}

"highlight rects checked=" + checked + " re-anchored=" + moved +
" unmatched=[" + unmatched.join(" | ") + "]" +
"\nretired artboard = AB" + (retAb + 1) + " '" + retName + "' of " + nAb +
"\nRETIRED text objects on NON-retired artboards (" + textRetired.length + "): " + textRetired.join(" ; ") +
"\nBAKED-watermark figures on NON-retired artboards (" + bakedOffboard.length + "): " + bakedOffboard.join(" ; ") +
"\nsave=" + mode;
