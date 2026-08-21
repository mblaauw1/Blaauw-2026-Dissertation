// DECK PASS 1b (2026-07-29c) - actually refresh the linked artwork.
//
// Pass 1 called placedItem.update(), which is NOT a PlacedItem method in Illustrator's DOM - it threw for
// all 581 placements (linksUpdated=0, linkFailed=581) and the pass saved the decks unchanged. The correct
// call is relink(file): re-pointing a placement at the SAME file forces Illustrator to re-read it from
// disk. 296 of the linked PDFs were re-rendered after the decks were last saved, so without this the deck
// shows yesterday's artwork.
//
// Safe by construction: each placement is relinked to its OWN current file path, so nothing moves, nothing
// is re-parented, and a placement whose file is missing is left exactly as it was and reported.
// Values are read BEFORE close (Error 45); no variable named `open` (Error 24).
#target illustrator
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }

var DOCS = ["/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai",
            "/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_kinetochore_overflow.ai"];
var report = [];

for (var k = 0; k < DOCS.length; k++) {
  var d = app.open(new File(DOCS[k]));
  var nOk = 0, nMissing = 0, nErr = 0, examples = [];

  for (var i = d.placedItems.length - 1; i >= 0; i--) {
    var it = d.placedItems[i];
    var f = null;
    try { f = it.file; } catch (eF) { f = null; }
    if (!f) { nErr++; continue; }
    var p = f.fsName;
    if (!(new File(p)).exists) {
      nMissing++;
      if (examples.length < 5) examples.push(decodeURI(f.name));
      continue;
    }
    try { it.relink(new File(p)); nOk++; }
    catch (eR) { nErr++; if (examples.length < 5) examples.push(decodeURI(f.name) + " ERR " + eR); }
  }

  var docName = d.name, nPl = d.placedItems.length;
  var opts = new IllustratorSaveOptions();
  opts.pdfCompatible = false;
  var saved = "yes";
  try { d.saveAs(new File(DOCS[k]), opts); } catch (eS) { saved = "FAILED: " + eS; }
  try { d.close(SaveOptions.DONOTSAVECHANGES); } catch (eC) {}
  report.push(docName + " :: placements=" + nPl + " relinked=" + nOk +
              " missingFile=" + nMissing + " errors=" + nErr + " saved=" + saved +
              (examples.length ? " | e.g. " + examples.join("; ") : ""));
}
report.join("\n");
