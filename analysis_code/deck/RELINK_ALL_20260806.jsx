// Refresh every link in the FOUR current decks after the v2-phase rebuild, and prove each deck is clean.
//
// Deck set is exactly these four (user 2026-08-06: "the 20260805 meta file is the go-to meta file. do not
// refer to any other meta file besides this one") - META_FIGURES_20260803.ai is NOT touched.
//
// Method that works (learned the hard way today): no artboards are created, nothing is repositioned,
// each deck is saved ONCE, and the result is verified in-script rather than assumed.
//
// One link is SWAPPED rather than refreshed: META still points at G3_creation_time_vs_behavior, which no
// builder writes any more - it was superseded when the creation-time figure was split into 4 bars. Left
// alone it could never show the new phase binning. G3_creation_phase_vs_behavior is its direct successor
// (same panel, freshly built), so the swap is 1:1 and keeps the item's position and size.
app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
var L = new File("/Volumes/4 MB/ablation_plots/RELINK_ALL_LOG.txt"); L.open("w");
function s(x){ L.writeln(x); L.close(); L.open("e"); L.seek(0,2); }

var PDF = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/";
var DECKS = ["META_FIGURES_20260805.ai", "NEW_FIGURES_20260804.ai",
             "NEW_TIMESTRIPS_20260804.ai", "supplemental.ai"];
var SWAP = {};                       // old link name -> replacement name
SWAP["G3_creation_time_vs_behavior"] = "G3_creation_phase_vs_behavior";

while (app.documents.length > 0) app.documents[0].close(SaveOptions.DONOTSAVECHANGES);

for (var d = 0; d < DECKS.length; d++) {
  var f = new File("/Volumes/4 MB/ablation_plots/" + DECKS[d]);
  if (!f.exists) { s("MISSING DECK: " + DECKS[d]); continue; }
  var doc = app.open(f);
  var relinked = 0, swapped = 0, broken = 0;

  for (var i = doc.placedItems.length - 1; i >= 0; i--) {
    var it = doc.placedItems[i], nm = "";
    try { nm = it.file.name.replace(/\.(pdf|png|svg)$/i, ""); } catch (e) { broken++; continue; }
    if (SWAP[nm]) {
      var rep = new File(PDF + SWAP[nm] + ".pdf");
      if (rep.exists) {
        var w = it.width, h = it.height, l = it.left, t = it.top;
        it.file = rep;                       // keep the slot: restore geometry after the swap
        var sc = Math.min(w / it.width, h / it.height);
        it.width *= sc; it.height *= sc; it.left = l; it.top = t;
        swapped++;
        s("  SWAPPED " + nm + " -> " + SWAP[nm]);
        continue;
      }
    }
    try {
      var lf = it.file;
      if (lf && lf.exists) { it.file = lf; relinked++; } else { broken++; s("  BROKEN LINK: " + nm); }
    } catch (e) { broken++; }
  }

  var opts = new IllustratorSaveOptions(); opts.pdfCompatible = false;
  doc.saveAs(f, opts);                       // ONE save per deck
  s(DECKS[d] + ": " + doc.placedItems.length + " placed · " + relinked + " relinked · " +
    swapped + " swapped · " + broken + " broken");
  doc.close(SaveOptions.DONOTSAVECHANGES);
}
s("DONE"); L.close();
