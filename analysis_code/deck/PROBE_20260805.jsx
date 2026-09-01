app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
var L = new File("/Volumes/4 MB/ablation_plots/PROBE_LOG.txt"); L.open("w");
function s(x){ L.writeln(x); L.close(); L.open("e"); L.seek(0,2); }
var f = new File("/Volumes/4 MB/1_DECKS/NEW_FIGURES_20260804.ai");
var d = app.open(f);
s("artboards: " + d.artboards.length + "   placedItems: " + d.placedItems.length);
for (var i = 0; i < d.artboards.length; i++) {
    var r = d.artboards[i].artboardRect;
    s("  ab" + (i+1) + " [" + Math.round(r[0]) + "," + Math.round(r[1]) + "," +
      Math.round(r[2]) + "," + Math.round(r[3]) + "]  w=" + Math.round(r[2]-r[0]) +
      " h=" + Math.round(r[1]-r[3]) + "  " + d.artboards[i].name);
}
s("Illustrator canvas limit is about +/-16330 pt from the origin.");
d.close(SaveOptions.DONOTSAVECHANGES);
s("DONE");
L.close();
