// Place the ten NF9 timestrips into NEW_TIMESTRIPS_20260804.ai.
// Six already exist and are relinked in place (same filenames, so her layout is untouched); the four new
// variants (_alt, _v1, _v2, _v3) go on new artboards stacked DIRECTLY BELOW the existing content, not
// strung out to the side — the mistake made on NEW_FIGURES earlier today.
// Saves after every figure so a stall costs one placement, not the run. pdfCompatible=false; alerts off.
app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
var L = new File("/Volumes/4 MB/ablation_plots/PLACE_TS_LOG.txt"); L.open("w");
function s(x){ L.writeln(x); L.close(); L.open("e"); L.seek(0,2); }
var P = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/";
var NEWONES = [
 "nf9_1-sisterless__20250411_ptk_yfpcdc20_11_alt",
 "nf9_3-sisterless__20260417_ptk2_eyfp_cdc20_ablation_18_v1",
 "nf9_3-sisterless__20260417_ptk2_eyfp_cdc20_ablation_18_v2",
 "nf9_3-sisterless__20260417_ptk2_eyfp_cdc20_ablation_18_v3"
];
if (app.documents.length > 0) { s("ABORT: a document is already open"); L.close(); }
else {
  var f = new File("/Volumes/4 MB/1_DECKS/NEW_TIMESTRIPS_20260804.ai");
  var doc = app.open(f);
  s("opened: " + doc.artboards.length + " artboards, " + doc.placedItems.length + " placed");
  // 1. refresh the six already there
  var refreshed = 0;
  for (var i = doc.placedItems.length - 1; i >= 0; i--) {
    try { var lf = doc.placedItems[i].file; if (lf && lf.exists) { doc.placedItems[i].file = lf; refreshed++; } } catch (e) {}
  }
  s("relinked " + refreshed + " existing strip(s)");
  var have = {};
  for (var j = 0; j < doc.placedItems.length; j++) {
    try { have[doc.placedItems[j].file.name.replace(/\.(pdf|png|svg)$/i,"")] = true; } catch (e) {}
  }
  // 2. stack the new ones below everything
  var minBottom = 1e9, left = 0;
  for (var a = 0; a < doc.artboards.length; a++) {
    var r = doc.artboards[a].artboardRect;
    if (r[3] < minBottom) minBottom = r[3];
    if (a === 0) left = r[0];
  }
  var W = 2400, H = 700, PAD = 60, y = minBottom - 250, placed = 0;
  var opts = new IllustratorSaveOptions(); opts.pdfCompatible = false;
  for (var k = 0; k < NEWONES.length; k++) {
    var nm = NEWONES[k];
    if (have[nm]) { s("  already present: " + nm); continue; }
    var pf = new File(P + nm + ".pdf");
    if (!pf.exists) { s("  MISSING PDF: " + nm); continue; }
    var ab = doc.artboards.add([left, y, left + W, y - H]);
    ab.name = nm.substring(4, 64);
    var pi = doc.placedItems.add();
    pi.file = pf;
    var sc = Math.min((W - 2*PAD) / pi.width, (H - 2*PAD) / pi.height);
    pi.width *= sc; pi.height *= sc;
    pi.left = left + (W - pi.width) / 2;
    pi.top  = y - (H - pi.height) / 2;
    doc.saveAs(f, opts);
    s("  placed " + nm + " (artboard " + doc.artboards.length + ", saved)");
    y -= (H + 120); placed++;
  }
  doc.close(SaveOptions.DONOTSAVECHANGES);
  s("relinked " + refreshed + ", placed " + placed);
  s("DONE"); L.close();
}
