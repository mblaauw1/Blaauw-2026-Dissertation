// Place the ten NF10 timestrips ON an artboard - and PROVE they are on it.
//
// What went wrong before (her diagnosis, correct): I added one artboard per figure and trusted the
// arithmetic. Two things break that. (1) doc.artboards.add() does NOT necessarily keep the rect you hand
// it, so the artboard is not where the placement math assumes - the figure lands off-board. (2) saveAs()
// after every figure rewrites the whole .ai; on a file this size that is what stalls Illustrator at ~1.5%
// CPU. On the META boards I placed into an EXISTING artboard and saved once, which is why that worked.
//
// So: ONE artboard, read its rect back from Illustrator AFTER creating it, lay the grid out inside THAT
// rect, save once, then verify every item's geometricBounds against the rect and log the result.
app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
var L = new File("/Volumes/4 MB/ablation_plots/PLACE_NF10_V2_LOG.txt"); L.open("w");
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
var isMine = {};
for (var m = 0; m < FIGS.length; m++) isMine[FIGS[m]] = true;

var f = new File("/Volumes/4 MB/1_DECKS/NEW_TIMESTRIPS_20260804.ai");
var doc = null;
for (var q = app.documents.length - 1; q >= 0; q--) {
  var dq = app.documents[q]; var same = false;
  try { same = (dq.fullName && dq.fullName.fsName === f.fsName); } catch (e) {}
  if (same) doc = dq; else dq.close(SaveOptions.DONOTSAVECHANGES);
}
if (doc === null) doc = app.open(f);
s("opened: " + doc.artboards.length + " artboards, " + doc.placedItems.length + " placed");

// 1. undo the previous attempt: my placed items and my per-figure artboards
var removed = 0;
for (var i = doc.placedItems.length - 1; i >= 0; i--) {
  var nm = ""; try { nm = doc.placedItems[i].file.name.replace(/\.(pdf|png|svg)$/i, ""); } catch (e) { continue; }
  if (isMine[nm]) { doc.placedItems[i].remove(); removed++; }
}
var abGone = 0;
for (var a = doc.artboards.length - 1; a >= 1; a--) {
  if (doc.artboards[a].name.indexOf("nf10_") === 0 || doc.artboards[a].name.indexOf("NF10") === 0) {
    doc.artboards[a].remove(); abGone++;
  }
}
s("cleared " + removed + " item(s) and " + abGone + " artboard(s) from the previous attempt");

// 2. ONE artboard below everything - then READ BACK what Illustrator actually made
var minBottom = 1e9, left = 0;
for (var b2 = 0; b2 < doc.artboards.length; b2++) {
  var rr = doc.artboards[b2].artboardRect;
  if (rr[3] < minBottom) minBottom = rr[3];
  if (b2 === 0) left = rr[0];
}
var COLS = 2, CW = 2500, CH = 900, PAD = 90;
var ROWS = Math.ceil(FIGS.length / COLS);
var bw = COLS * CW + PAD * 2, bh = ROWS * CH + PAD * 2;
var nb = doc.artboards.add([left, minBottom - 300, left + bw, minBottom - 300 - bh]);
nb.name = "NF10 timestrips 2026-08-06";
var R = nb.artboardRect;                       // AUTHORITATIVE - not the rect I asked for
s("artboard requested [" + Math.round(left) + "," + Math.round(minBottom-300) + "," +
  Math.round(left+bw) + "," + Math.round(minBottom-300-bh) + "]");
s("artboard ACTUAL    [" + Math.round(R[0]) + "," + Math.round(R[1]) + "," +
  Math.round(R[2]) + "," + Math.round(R[3]) + "]");
var AL = R[0], AT = R[1], AR = R[2], AB = R[3];
var cw = (AR - AL - PAD * 2) / COLS, ch = (AT - AB - PAD * 2) / ROWS;

// 3. fill the grid inside the ACTUAL rect
var placed = 0;
for (var k = 0; k < FIGS.length; k++) {
  var figName = FIGS[k], pf = new File(P + figName + ".pdf");
  if (!pf.exists) { s("  MISSING PDF: " + figName); continue; }
  var col = k % COLS, row = Math.floor(k / COLS);
  var cellL = AL + PAD + col * cw, cellT = AT - PAD - row * ch;
  var pi = doc.placedItems.add();
  pi.file = pf;
  var sc = Math.min((cw - 50) / pi.width, (ch - 50) / pi.height);
  pi.width *= sc; pi.height *= sc;
  pi.left = cellL + (cw - pi.width) / 2;
  pi.top  = cellT - (ch - pi.height) / 2;
  s("  placed " + figName + "  r" + (row+1) + "c" + (col+1));
  placed++;
}
// 4. ONE save
var opts = new IllustratorSaveOptions(); opts.pdfCompatible = false;
doc.saveAs(f, opts);
s("saved once after " + placed + " placement(s)");

// 5. PROVE it: every item's bounds against the artboard rect
var onBoard = 0, offBoard = 0;
for (var z = 0; z < doc.placedItems.length; z++) {
  var it = doc.placedItems[z], nz = "";
  try { nz = it.file.name.replace(/\.(pdf|png|svg)$/i, ""); } catch (e) { continue; }
  if (!isMine[nz]) continue;
  var g = it.geometricBounds;                  // [left, top, right, bottom]
  var inside = (g[0] >= AL - 1 && g[2] <= AR + 1 && g[1] <= AT + 1 && g[3] >= AB - 1);
  if (inside) onBoard++; else {
    offBoard++;
    s("  OFF-BOARD " + nz + " bounds[" + Math.round(g[0]) + "," + Math.round(g[1]) + "," +
      Math.round(g[2]) + "," + Math.round(g[3]) + "]");
  }
}
s("VERIFY: " + onBoard + " of " + (onBoard + offBoard) + " NF10 figures are INSIDE the artboard");
doc.close(SaveOptions.DONOTSAVECHANGES);
s("DONE"); L.close();
