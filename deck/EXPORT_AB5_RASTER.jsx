// Export EVERY embedded raster on the `figures` layer so each can be identified.
// The first attempt duplicated into a fixed-size document and exported blank white; this version fits a
// temporary artboard to the item's OWN visibleBounds, which is the part that was wrong.
#target illustrator
var AIP = "/Volumes/4 MB/1_DECKS/META_FIGURES_20260814.ai";
var HB  = new File("/Volumes/4 MB/_claude_tmp/raster_probe.txt");
function beat(m){ try{ HB.open("a"); HB.writeln(m); HB.close(); }catch(e){} }
app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
var doc = app.open(new File(AIP));
var out = [];
for (var i = 0; i < doc.rasterItems.length; i++) {
  var ri = doc.rasterItems[i], lay = "";
  try { lay = ri.layer.name; } catch (e) {}
  if (lay !== "legend_bullets") continue;   // 2026-08-17: the AB5 STRIPS live on this layer, not bullet art
  out.push(ri);
}
beat("figures-layer rasters=" + out.length);
for (var k = 0; k < out.length; k++) {
  var ri = out[k], b = ri.visibleBounds;
  var w = b[2] - b[0], h = b[1] - b[3];
  var nd = app.documents.add(DocumentColorSpace.RGB, w, h);
  var cp = ri.duplicate(nd.layers[0], ElementPlacement.PLACEATEND);
  // artboard 0 of a new doc has its origin at top-left; place the copy exactly on it
  var ar = nd.artboards[0].artboardRect;   // [L,T,R,B]
  cp.left = ar[0]; cp.top = ar[1];
  var ef = new ExportOptionsPNG24();
  ef.artBoardClipping = true; ef.horizontalScale = 25; ef.verticalScale = 25;
  nd.exportFile(new File("/Volumes/4 MB/_claude_tmp/lb_" + k + ".png"), ExportType.PNG24, ef);
  nd.close(SaveOptions.DONOTSAVECHANGES);
  beat("lb_" + k + " w=" + w.toFixed(0) + " h=" + h.toFixed(0) +
       " at " + b[0].toFixed(0) + "," + b[1].toFixed(0));
}
doc.close(SaveOptions.DONOTSAVECHANGES);
app.userInteractionLevel = UserInteractionLevel.DISPLAYALERTS;
beat("DONE");
"ok";
