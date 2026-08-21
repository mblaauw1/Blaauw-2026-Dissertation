// Refresh linked artwork in copy.ai, the overflow board AND META_FIGURES (2026-07-30).
//
// All three documents LINK the same _ai_relink PDFs, so re-rendering a figure updates all three - but only
// once each placement is relinked. relink(file) re-points a placement at its OWN current path, forcing a
// re-read from disk; placedItem.update() is not a method and silently throws.
//
// META IS RELINKED, NEVER REBUILT. She has begun deleting figures from META_FIGURES and those deletions are
// deliberate; a full rebuild regenerates every figure from the inventory and would silently undo them.
// This pass adds nothing and removes nothing - it only refreshes what is already placed.
#target illustrator
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var DOCS = ["/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai",
            "/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_kinetochore_overflow.ai",
            "/Volumes/4 MB/ablation_plots/_superseded_decks/META_FIGURES_20260729.ai"];
var report = [];
for (var k = 0; k < DOCS.length; k++) {
  var d = app.open(new File(DOCS[k]));
  var ok = 0, gone = 0, err = 0, before = d.placedItems.length;
  for (var i = d.placedItems.length - 1; i >= 0; i--) {
    var it = d.placedItems[i], f = null;
    try { f = it.file; } catch (eF) {}
    if (!f) { err++; continue; }
    var p = f.fsName;
    if (!(new File(p)).exists) { gone++; continue; }
    try { it.relink(new File(p)); ok++; } catch (eR) { err++; }
  }
  var nm = d.name, after = d.placedItems.length;
  var opts = new IllustratorSaveOptions(); opts.pdfCompatible = false;
  var mode = "saved";
  try { d.saveAs(new File(DOCS[k]), opts); } catch (eS) { mode = "SAVE_FAILED " + eS; }
  try { d.close(SaveOptions.DONOTSAVECHANGES); } catch (eC) {}
  report.push(nm + " :: placements " + before + " -> " + after + " (must be equal) relinked=" + ok +
              " missingFile=" + gone + " errors=" + err + " save=" + mode);
}
report.join("\n");
