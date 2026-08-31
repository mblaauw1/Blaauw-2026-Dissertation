// Append the ten NF10 timestrips to NEW_TIMESTRIPS_20260804.ai.
// Stacked DIRECTLY BELOW the existing content in one column - not strung off to the right (her correction
// on NEW_FIGURES: "all of the actual plots are to the side of the artbord, not on it").
// Existing placements are never touched; her layout edits survive. Saves after each figure so a stall
// costs one placement, not the run. pdfCompatible=false; alerts off; `name` is reserved so use figName.
app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
var L = new File("/Volumes/4 MB/ablation_plots/PLACE_NF10_LOG.txt"); L.open("w");
function s(x){ L.writeln(x); L.close(); L.open("e"); L.seek(0,2); }
var P = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/";
var FIGS = [
 "nf10_1-sisterless__20260420_ptk2_eyfp_cdc20_1_ablation_11",
 "nf10_1-sisterless-congressing__20260420_ptk2_eyfp_cdc20_1_ablation_13",
 "nf10_metaphase-ablation__20260303_Mad1_Ptk_Eyfpcdc2_ablation_1metaphase_82",
 "nf10_2-sisterless__20260108_two_sisterless_kinetochores_14",
 "nf10_lagging-fractured__20260108_two_sisterless_kinetochores_14",
 "nf10_lagging-stretch-rebound__20260303_Mad1_Ptk_Eyfpcdc2_ablation_1metaphase_52",
 "nf10_1-sisterless-persistent-polar__20250402_ptk_yfpcdc20_2",
 "nf10_1-sisterless-persistent-polar__20250402_ptk_yfpcdc20_7",
 "nf10_1-sisterless-pole-switch__20250417_ptk_yfpcdc20_3",
 "nf10_off-target__20250402_ptk_yfpcdc20_22"
];
var f = new File("/Volumes/4 MB/1_DECKS/NEW_TIMESTRIPS_20260804.ai");
{
  var doc = null;
  for (var q = app.documents.length - 1; q >= 0; q--) {
    var dq = app.documents[q];
    var samePath = false;
    try { samePath = (dq.fullName && dq.fullName.fsName === f.fsName); } catch (e) {}
    if (samePath) { doc = dq; s("adopted the already-open target document"); }
    else { s("closing unrelated open document: " + dq.name); dq.close(SaveOptions.DONOTSAVECHANGES); }
  }
  if (doc === null) doc = app.open(f);
  s("opened: " + doc.artboards.length + " artboards, " + doc.placedItems.length + " placed");
  var have = {};
  for (var j = 0; j < doc.placedItems.length; j++) {
    try { have[doc.placedItems[j].file.name.replace(/\.(pdf|png|svg)$/i,"")] = true; } catch (e) {}
  }
  var minBottom = 1e9, left = 0;
  for (var a = 0; a < doc.artboards.length; a++) {
    var r = doc.artboards[a].artboardRect;
    if (r[3] < minBottom) minBottom = r[3];
    if (a === 0) left = r[0];
  }
  var W = 2400, H = 760, PAD = 60, y = minBottom - 300, placed = 0, missing = 0;
  var opts = new IllustratorSaveOptions(); opts.pdfCompatible = false;
  for (var k = 0; k < FIGS.length; k++) {
    var figName = FIGS[k];
    if (have[figName]) { s("  already present, skipped: " + figName); continue; }
    var pf = new File(P + figName + ".pdf");
    if (!pf.exists) { s("  MISSING PDF: " + figName); missing++; continue; }
    var ab = doc.artboards.add([left, y, left + W, y - H]);
    ab.name = figName.substring(5, 68);
    var pi = doc.placedItems.add();
    pi.file = pf;
    var sc = Math.min((W - 2*PAD) / pi.width, (H - 2*PAD) / pi.height);
    pi.width *= sc; pi.height *= sc;
    pi.left = left + (W - pi.width) / 2;
    pi.top  = y - (H - pi.height) / 2;
    doc.saveAs(f, opts);
    s("  placed " + figName + "  (artboard " + doc.artboards.length + ", saved)");
    y -= (H + 140); placed++;
  }
  doc.close(SaveOptions.DONOTSAVECHANGES);
  s("placed " + placed + ", missing " + missing);
  s("DONE"); L.close();
}
