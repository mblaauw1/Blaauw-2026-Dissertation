// Refresh every link in place and save ONCE. No artboards created, no repositioning.
app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
var L = new File("/Volumes/4 MB/ablation_plots/RELINK_13_LOG.txt"); L.open("w");
function s(x){ L.writeln(x); L.close(); L.open("e"); L.seek(0,2); }
while (app.documents.length > 0) app.documents[0].close(SaveOptions.DONOTSAVECHANGES);
var f = new File("/Volumes/4 MB/1_DECKS/NEW_TIMESTRIPS_20260804.ai");
var doc = app.open(f);
var n = 0;
for (var i = doc.placedItems.length - 1; i >= 0; i--) {
  try { var lf = doc.placedItems[i].file; if (lf && lf.exists) { doc.placedItems[i].file = lf; n++; } } catch (e) {}
}
var opts = new IllustratorSaveOptions(); opts.pdfCompatible = false;
doc.saveAs(f, opts);
var R = doc.artboards[doc.artboards.length-1].artboardRect;
var on = 0, off = 0;
for (var z = 0; z < doc.placedItems.length; z++) {
  var g = doc.placedItems[z].geometricBounds;
  if (g[0] >= R[0]-1 && g[2] <= R[2]+1 && g[1] <= R[1]+1 && g[3] >= R[3]-1) on++; else off++;
}
s("relinked " + n + ", saved once, VERIFY: " + on + " of " + (on+off) + " inside the artboard");
doc.close(SaveOptions.DONOTSAVECHANGES);
s("DONE"); L.close();
