app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
var L = new File("/Volumes/4 MB/ablation_plots/DUMP_AB_LOG.txt"); L.open("w");
function s(x){ L.writeln(x); L.close(); L.open("e"); L.seek(0,2); }
while (app.documents.length > 0) app.documents[0].close(SaveOptions.DONOTSAVECHANGES);
var f = new File("/Volumes/4 MB/1_DECKS/NEW_TIMESTRIPS_20260804.ai");
var doc = app.open(f);
s("artboards: " + doc.artboards.length + "   placedItems: " + doc.placedItems.length);
for (var a = 0; a < doc.artboards.length; a++) {
  var r = doc.artboards[a].artboardRect;
  s("  AB" + a + "  [" + Math.round(r[0]) + ", " + Math.round(r[1]) + ", " + Math.round(r[2]) + ", " +
    Math.round(r[3]) + "]  w=" + Math.round(r[2]-r[0]) + " h=" + Math.round(r[1]-r[3]) +
    "  name=" + doc.artboards[a].name);
}
doc.close(SaveOptions.DONOTSAVECHANGES);
s("DONE"); L.close();
