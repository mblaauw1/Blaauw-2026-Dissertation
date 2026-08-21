// Add G6tenM_strain_by_state into the existing "NEW 2026-08-05" grid, next free slot (r4c3).
// Uses the same grid geometry as REPLACE_NEW_20260805.jsx so it lands in line with the other 14.
app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
var L = new File("/Volumes/4 MB/ablation_plots/ADD_ONE_LOG.txt"); L.open("w");
function s(x){ L.writeln(x); L.close(); L.open("e"); L.seek(0,2); }
var figName = "G6tenM_strain_by_state";
var pf = new File("/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/" + figName + ".pdf");
if (!pf.exists) { s("MISSING PDF"); s("DONE"); L.close(); }
else {
  var file = new File("/Volumes/4 MB/1_DECKS/NEW_FIGURES_20260804.ai");
  var doc = app.open(file);
  var already = false;
  for (var i = 0; i < doc.placedItems.length; i++) {
    try { if (doc.placedItems[i].file.name.replace(/\.(pdf|png|svg)$/i,"") === figName) already = true; } catch(e){}
  }
  if (already) { s("already present"); }
  else {
    var ab = null;
    for (var a = 0; a < doc.artboards.length; a++)
      if (doc.artboards[a].name === "NEW 2026-08-05") ab = doc.artboards[a];
    if (!ab) { s("grid artboard not found"); }
    else {
      var r = ab.artboardRect;                 // [left, top, right, bottom]
      var COLS = 4, CW = 900, CH = 640, PAD = 70;
      var k = 14, col = k % COLS, row = Math.floor(k / COLS);    // 15th figure -> r4c3
      var cx = r[0] + PAD + col * CW, cyTop = r[1] - PAD - row * CH;
      var pi = doc.placedItems.add();
      pi.file = pf;
      var sc = Math.min((CW - 60) / pi.width, (CH - 60) / pi.height);
      pi.width *= sc; pi.height *= sc;
      pi.left = cx + (CW - pi.width) / 2;
      pi.top  = cyTop - (CH - pi.height) / 2;
      var o = new IllustratorSaveOptions(); o.pdfCompatible = false;
      doc.saveAs(file, o);
      s("placed " + figName + " at r" + (row+1) + "c" + (col+1) +
        "  left=" + Math.round(pi.left) + " top=" + Math.round(pi.top));
    }
  }
  doc.close(SaveOptions.DONOTSAVECHANGES);
  s("DONE"); L.close();
}
