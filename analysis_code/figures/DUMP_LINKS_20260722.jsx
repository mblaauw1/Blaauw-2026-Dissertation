#target illustrator
// Read-only: dump every placed link's filename + path so we can diff against the figures on disk.
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var d = app.open(new File("/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai"));
var lines = [];
for (var i = 0; i < d.placedItems.length; i++) {
  var p = d.placedItems[i], fp = "";
  try { fp = p.file ? p.file.fsName : ""; } catch (e) { lines.push("EMBEDDED\t\t"); continue; }
  var b = p.visibleBounds, cx = (b[0]+b[2])/2, cy = (b[1]+b[3])/2, ab = 0;
  for (var a = 0; a < d.artboards.length; a++) { var r = d.artboards[a].artboardRect;
    if (cx>=r[0]&&cx<=r[2]&&cy<=r[1]&&cy>=r[3]) { ab = a+1; break; } }
  lines.push(decodeURI(fp) + "\tAB" + ab);
}
var f = new File("/Volumes/4 MB/ablation_plots/COPYAI_LINKS_20260722.txt");
f.open("w"); f.write(lines.join("\n")); f.close();
d.close(SaveOptions.DONOTSAVECHANGES);
"wrote " + lines.length + " links";
