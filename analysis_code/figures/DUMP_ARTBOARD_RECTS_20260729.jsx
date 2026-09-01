// Dump each artboard's rect + name for both decks, so artboard occupancy can be measured off-line.
// Read-only: opens and closes WITHOUT saving.
#target illustrator
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var DOCS = ["/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai",
            "/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_kinetochore_overflow.ai"];
var TAG = ["AB", "OV-AB"];
var out = [];
for (var k = 0; k < DOCS.length; k++) {
  var d = app.open(new File(DOCS[k]));
  for (var a = 0; a < d.artboards.length; a++) {
    var R = d.artboards[a].artboardRect, nm = "";
    try { nm = String(d.artboards[a].name).replace(/"/g, "'"); } catch (e1) {}
    out.push('"' + TAG[k] + (a + 1) + '":[' + Math.round(R[0]) + ',' + Math.round(R[1]) + ',' +
             Math.round(R[2]) + ',' + Math.round(R[3]) + ',"' + nm + '"]');
  }
  try { d.close(SaveOptions.DONOTSAVECHANGES); } catch (e2) {}
}
var f = new File("/Volumes/4 MB/_working/_deck_jsx_inputs/artboard_rects.json");
f.encoding = "UTF-8"; f.open("w"); f.write("{" + out.join(",\n") + "}"); f.close();
"wrote " + out.length + " artboard rects";
