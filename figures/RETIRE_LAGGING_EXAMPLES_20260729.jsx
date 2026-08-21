// Finish retiring the circle-derived lagging-example figures and make sure their replacements are
// placed wherever they used to be (user 2026-07-29).
//   OLD (retire): G4_lagging_examples.pdf, G4_lagging_examples_outlined.pdf
//   NEW (place) : G4_lagging_examples_outlines.pdf, G4_lagging_examples_outlines_traced.pdf
// The old pair derived anaphase lagging shape from circle marks by auto-segmentation; the new pair
// overlays her MANUAL kt_outlines. Every old placement is MOVED to the RETIRED artboard, never
// deleted, and a replacement is placed into the slot it vacated so no artboard loses a panel.
// Runs over BOTH decks. Reports artboard indices before and after.
#target illustrator
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }

var DOCS = ["/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai",
            "/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_kinetochore_overflow.ai"];
var PDFDIR = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/";
var MAP = {};
MAP["g4_lagging_examples.pdf"]          = "G4_lagging_examples_outlines.pdf";
MAP["g4_lagging_examples_outlined.pdf"] = "G4_lagging_examples_outlines_traced.pdf";
var report = [];

function lname(p) { var f = null; try { f = p.file; } catch (e) {} return f ? decodeURI(f.name).toLowerCase() : ""; }
function abOf(d, it) {                       // which artboard contains this item's centre
  var b; try { b = it.visibleBounds; } catch (e) { return -1; }
  var cx = (b[0] + b[2]) / 2, cy = (b[1] + b[3]) / 2;
  for (var a = 0; a < d.artboards.length; a++) {
    var R = d.artboards[a].artboardRect;
    if (cx >= R[0] && cx <= R[2] && cy <= R[1] && cy >= R[3]) return a;
  }
  return -1;
}

for (var k = 0; k < DOCS.length; k++) {
  var PATH = DOCS[k], nm = PATH.replace(/^.*\//, "");
  var d = app.open(new File(PATH));

  var ri = -1;
  for (var a = 0; a < d.artboards.length; a++)
    if (d.artboards[a].name.toUpperCase().indexOf("RETIRED") >= 0) { ri = a; break; }

  var olds = [], newsSeen = {};
  for (var i = 0; i < d.placedItems.length; i++) {
    var n = lname(d.placedItems[i]);
    if (MAP[n]) olds.push({ it: d.placedItems[i], src: n, ab: abOf(d, d.placedItems[i]) });
    if (n.indexOf("g4_lagging_examples_outlines") === 0) newsSeen[n] = (newsSeen[n] || 0) + 1;
  }

  var placed = 0, moved = 0, errs = [];
  if (olds.length && ri < 0) errs.push("no RETIRED artboard in this doc");

  for (var q = 0; q < olds.length; q++) {
    var o = olds[q].it, tgt = MAP[olds[q].src], pos, w;
    try { pos = o.position; w = o.width; } catch (e) { errs.push("bounds"); continue; }
    var f = new File(PDFDIR + tgt);
    if (f.exists) {
      try {
        var pi = d.placedItems.add(); pi.file = f;
        var ratio = pi.height / pi.width;
        pi.width = w; pi.height = w * ratio; pi.position = pos;
        pi.name = tgt.replace(/\.pdf$/i, ""); placed++;
      } catch (e2) { errs.push("place " + tgt + " " + e2); }
    } else { errs.push("missing " + tgt); }
  }

  if (ri >= 0 && olds.length) {                       // repack the RETIRED artboard with the olds added
    var R = d.artboards[ri].artboardRect, members = [];
    for (var i2 = 0; i2 < d.placedItems.length; i2++) {
      var p = d.placedItems[i2], isOld = false;
      for (var z = 0; z < olds.length; z++) if (olds[z].it === p) isOld = true;
      if (isOld || abOf(d, p) === ri) members.push(p);
    }
    var n2 = members.length, cols = Math.ceil(Math.sqrt(n2)), rows = Math.ceil(n2 / cols);
    var M = 18, GAP = 10;
    var cw = ((R[2] - R[0]) - 2 * M - (cols - 1) * GAP) / cols;
    var ch = ((R[1] - R[3]) - 2 * M - (rows - 1) * GAP) / rows;
    for (var m = 0; m < n2; m++) {
      var it = members[m], iw = it.width, ih = it.height, s = Math.min(cw / iw, ch / ih);
      it.width = iw * s; it.height = ih * s;
      var c = m % cols, r2 = Math.floor(m / cols);
      it.position = [R[0] + M + c * (cw + GAP) + (cw - it.width) / 2,
                     R[1] - M - r2 * (ch + GAP) - (ch - it.height) / 2];
    }
    moved = olds.length;
  }

  var oldAbs = [];
  for (var z2 = 0; z2 < olds.length; z2++) oldAbs.push("AB" + (olds[z2].ab + 1));
  var nAb = d.artboards.length, retName = (ri >= 0 ? d.artboards[ri].name : "-");
  var mode = "";
  try { var so = new IllustratorSaveOptions(); so.pdfCompatible = false; d.saveAs(new File(PATH), so); mode = "saved"; }
  catch (e3) { mode = "SAVE_FAILED " + e3; }
  try { d.close(SaveOptions.DONOTSAVECHANGES); } catch (e4) {}

  report.push(nm + " :: olds_found=" + olds.length + " on [" + oldAbs.join(",") + "]" +
              "  replacements_placed=" + placed + "  retired_to=AB" + (ri + 1) + " '" + retName + "'" +
              "  artboards=" + nAb + "  save=" + mode +
              (errs.length ? "  ERRORS[" + errs.join("; ") + "]" : ""));
}
report.join("\n");
