#target illustrator
// Read-only: artboard names + how many placed items sit on each, so we can find the retired artboard
// rather than assume which one it is.
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var d = app.open(new File("/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai"));
var cnt = [];
for (var a = 0; a < d.artboards.length; a++) cnt.push(0);
var off = 0;
for (var i = 0; i < d.placedItems.length; i++) {
  var b; try { b = d.placedItems[i].visibleBounds; } catch (e) { continue; }
  var cx = (b[0]+b[2])/2, cy = (b[1]+b[3])/2, hit = -1;
  for (var a2 = 0; a2 < d.artboards.length; a2++) {
    var r = d.artboards[a2].artboardRect;
    if (cx>=r[0]&&cx<=r[2]&&cy<=r[1]&&cy>=r[3]) { hit = a2; break; }
  }
  if (hit < 0) off++; else cnt[hit]++;
}
var out = [];
for (var a3 = 0; a3 < d.artboards.length; a3++)
  out.push("AB" + (a3+1) + "\t" + d.artboards[a3].name + "\t" + cnt[a3] + " items");
out.push("OFF-ARTBOARD\t\t" + off + " items");
d.close(SaveOptions.DONOTSAVECHANGES);
out.join("\n");
