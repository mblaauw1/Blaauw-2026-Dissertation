// ONE artboard, sized to the content, holding every timestrip. Save once. Then prove it.
//
// Measured first (DUMP_AB): AB0 is 1400x1400 while every strip is >=2400 wide - so nothing was ever ON it,
// which is exactly what she saw. My per-figure artboards stacked to y=-7170 and the next request ended at
// -12150, past the canvas, which is where Illustrator stalled. Both problems go away with one board.
app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
var L = new File("/Volumes/4 MB/ablation_plots/FIX_LAYOUT_LOG.txt"); L.open("w");
function s(x){ L.writeln(x); L.close(); L.open("e"); L.seek(0,2); }
var P = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/";
var NF10 = [
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
while (app.documents.length > 0) app.documents[0].close(SaveOptions.DONOTSAVECHANGES);
var f = new File("/Volumes/4 MB/1_DECKS/NEW_TIMESTRIPS_20260804.ai");
var doc = app.open(f);
s("opened: " + doc.artboards.length + " artboards, " + doc.placedItems.length + " placed");

// 1. drop every artboard I added; keep only AB0
for (var a = doc.artboards.length - 1; a >= 1; a--) doc.artboards[a].remove();
s("artboards now: " + doc.artboards.length);

// 2. add any NF10 not already linked
var have = {};
for (var j = 0; j < doc.placedItems.length; j++) {
  try { have[doc.placedItems[j].file.name.replace(/\.(pdf|png|svg)$/i,"")] = true; } catch (e) {}
}
var added = 0;
for (var k = 0; k < NF10.length; k++) {
  if (have[NF10[k]]) continue;
  var pf = new File(P + NF10[k] + ".pdf");
  if (!pf.exists) { s("  MISSING PDF: " + NF10[k]); continue; }
  var np = doc.placedItems.add(); np.file = pf; added++;
}
s("added " + added + " new link(s); total placed now " + doc.placedItems.length);

// 3. ONE artboard below AB0, sized to a 4-col grid of everything
var r0 = doc.artboards[0].artboardRect;
var items = [];
for (var z = 0; z < doc.placedItems.length; z++) items.push(doc.placedItems[z]);
var COLS = 4, CELL_W = 1150, CELL_H = 900, PAD = 80;
var ROWS = Math.ceil(items.length / COLS);
var bw = COLS * CELL_W + PAD * 2, bh = ROWS * CELL_H + PAD * 2;
var top = r0[3] - 200;
var nb = doc.artboards.add([r0[0], top, r0[0] + bw, top - bh]);
nb.name = "ALL TIMESTRIPS 2026-08-06";
var R = nb.artboardRect;                        // read back, never trust the requested rect
s("artboard ACTUAL [" + Math.round(R[0]) + "," + Math.round(R[1]) + "," + Math.round(R[2]) + "," +
  Math.round(R[3]) + "]  grid " + COLS + "x" + ROWS + " for " + items.length + " figures");
var AL = R[0], AT = R[1], AR = R[2], AB = R[3];
var cw = (AR - AL - PAD * 2) / COLS, ch = (AT - AB - PAD * 2) / ROWS;

// 4. lay every figure into a cell
for (var i = 0; i < items.length; i++) {
  var pi = items[i];
  var col = i % COLS, row = Math.floor(i / COLS);
  var cellL = AL + PAD + col * cw, cellT = AT - PAD - row * ch;
  var sc = Math.min((cw - 40) / pi.width, (ch - 40) / pi.height);
  pi.width *= sc; pi.height *= sc;
  pi.left = cellL + (cw - pi.width) / 2;
  pi.top  = cellT - (ch - pi.height) / 2;
}
s("laid out " + items.length + " figures");

// 5. ONE save
var opts = new IllustratorSaveOptions(); opts.pdfCompatible = false;
doc.saveAs(f, opts);
s("saved once");

// 6. prove every figure is inside the artboard
var on = 0, off = 0;
for (var y2 = 0; y2 < doc.placedItems.length; y2++) {
  var g = doc.placedItems[y2].geometricBounds;
  if (g[0] >= AL - 1 && g[2] <= AR + 1 && g[1] <= AT + 1 && g[3] >= AB - 1) on++;
  else { off++; s("  OFF-BOARD idx " + y2 + " [" + Math.round(g[0]) + "," + Math.round(g[1]) + "," +
                  Math.round(g[2]) + "," + Math.round(g[3]) + "]"); }
}
s("VERIFY: " + on + " of " + (on + off) + " figures are INSIDE the artboard");
doc.close(SaveOptions.DONOTSAVECHANGES);
s("DONE"); L.close();
