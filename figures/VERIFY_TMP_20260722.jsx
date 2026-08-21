#target illustrator
// Verify the TEMP file before it replaces the deck: counts must match the original plus the one addition,
// and no link may be broken. Read-only on the temp.
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var d = app.open(new File("/Volumes/4 MB/ablation_plots/_tmp_copy_place_20260722.ai"));
var missing = 0, embedded = 0, tgt = [];
for (var i = 0; i < d.placedItems.length; i++) {
  var p = d.placedItems[i], fp = "";
  try { fp = p.file ? p.file.fsName : ""; } catch (e) { embedded++; continue; }
  if (!fp) { embedded++; continue; }
  var f = new File(fp);
  if (!f.exists) missing++;
  var n = decodeURI(f.name).toLowerCase();
  if (n == "g3_model_structured_performance.pdf" || n == "g4_sisterless_cdc20_vs_bleaching.pdf") {
    var b = p.visibleBounds, cx = (b[0]+b[2])/2, cy = (b[1]+b[3])/2, ab = -1;
    for (var a = 0; a < d.artboards.length; a++) { var r = d.artboards[a].artboardRect;
      if (cx>=r[0]&&cx<=r[2]&&cy<=r[1]&&cy>=r[3]) { ab = a+1; break; } }
    tgt.push(decodeURI(f.name) + " on AB" + ab + " size " + Math.round(p.width) + "x" + Math.round(p.height));
  }
}
var res = "placedItems=" + d.placedItems.length + "  artboards=" + d.artboards.length +
          "  textFrames=" + d.textFrames.length + "  layers=" + d.layers.length +
          "  missingLinks=" + missing + "  embedded=" + embedded + "\n" + tgt.join("\n");
d.close(SaveOptions.DONOTSAVECHANGES);
res;
