// Refresh every linked figure in BOTH decks to its current on-disk version after the 2026-07-29
// full rebuild (smoothed snap_to_peak + the kinetochore label/track edits). Nothing moves: each
// placed item keeps its exact position and size, only the linked file is re-read.
//
// Based on _scratch/kt_notes_20260727/REFRESH_BOTH_20260727.jsx (her established method).
// Reports per deck: how many links refreshed, how many point at a file that no longer exists, and
// the names of the missing ones - a missing link is the failure mode that matters, because the deck
// would silently keep showing a stale embedded preview.
#target illustrator
app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;

var DOCS = ["/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai",
            "/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_kinetochore_overflow.ai"];
var report = [];

for (var k = 0; k < DOCS.length; k++) {
  var PATH = DOCS[k];
  var isOpen = false;   // NB: never name this `open` - collides with an ExtendScript global
  for (var q = 0; q < app.documents.length; q++) {
    try { if (app.documents[q].fullName && app.documents[q].fullName.fsName == PATH) isOpen = true; } catch (e) {}
  }
  if (isOpen) { report.push(PATH.replace(/^.*\//, "") + " :: SKIPPED (open in Illustrator)"); continue; }

  var d = app.open(new File(PATH));
  var refreshed = 0, missing = 0, kept = 0, missingNames = [];
  for (var i = 0; i < d.placedItems.length; i++) {
    var pi = d.placedItems[i], f = null;
    try { f = pi.file; } catch (e) {}
    if (!f) { kept++; continue; }
    if (!f.exists) {
      missing++;
      try { if (missingNames.length < 12) missingNames.push(decodeURI(f.name)); } catch (e3) {}
      continue;
    }
    var pos = pi.position, w = pi.width, h = pi.height;
    try { pi.file = f; pi.position = pos; pi.width = w; pi.height = h; refreshed++; }
    catch (e2) { kept++; }
  }
  // read everything off the document BEFORE closing it - `d` is invalid afterwards (Error 45)
  var nAb = d.artboards.length, nPlaced = refreshed + missing + kept;
  var mode = "";
  try {
    var so = new IllustratorSaveOptions(); so.pdfCompatible = false;
    d.saveAs(new File(PATH), so); mode = "saved";
  } catch (e4) { mode = "SAVE_FAILED " + e4; }
  try { d.close(SaveOptions.DONOTSAVECHANGES); } catch (e5) {}

  report.push(PATH.replace(/^.*\//, "") + " :: placed=" + nPlaced +
              " refreshed=" + refreshed + " missing=" + missing + " untouched=" + kept +
              " artboards=" + nAb + " save=" + mode +
              (missing ? "  MISSING[" + missingNames.join("|") + "]" : ""));
}
report.join("\n");
