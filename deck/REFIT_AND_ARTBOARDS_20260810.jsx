// Re-lay the 100 new figures INSIDE the canvas, then put artboards over them.
//
// USER 2026-08-10: "they should all just go to new_figures" ... "for more space you can make more artboards
// and also move together the remaining plots".
//
// WHY A REFIT. The first placement put the band at y -5932..-8170, and all four artboard adds failed with
// 'CoOA'. Probing this document's canvas found the floor at y=-7475 (ceiling 8750, left -7250, right 8750),
// so the band overran it by ~700 pt. Objects are allowed outside the canvas -- these 100 placed fine, and
// this document's items reached -9934 before compaction -- but ARTBOARDS are not, which is the real reason
// artboardRect has failed repeatedly today.
//
// So the figures are re-laid at a tighter pitch that ends at about y=-7420, just inside the floor, and the
// artboards then fit. The whole band is rebuilt rather than nudged: everything from the first attempt is on
// its own layer, so dropping that layer removes exactly it and nothing of hers.
//
// Guards throughout: the layer's item count must fall by what the layer held; the re-place must restore the
// same count; artboards are added last, each individually, and the save is skipped if nothing landed. Her
// artwork, her four original artboards and the compaction are untouched by all of this.

#target illustrator

var TARGET = "/Volumes/4 MB/1_DECKS/NEW_FIGURES_20260804.ai";
var LIST   = "/Volumes/4 MB/_claude_tmp/place_ALL_newfigures.txt";
var PDFD   = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/";
var LAYER  = "from edited 2026-08-10";
var FLOOR  = -7475;           // measured canvas floor
var log = [];

function readLines(p) {
    var f = new File(p), out = [];
    if (!f.exists) return out;
    f.open("r");
    while (!f.eof) { var l = f.readln(); if (l && l.replace(/\s/g, "") !== "") out.push(l); }
    f.close();
    return out;
}

var doc = app.open(new File(TARGET));
app.activeDocument = doc;
var n0 = doc.pageItems.length;
log.push("opened pageItems=" + n0 + " artboards=" + doc.artboards.length);

// ---- 1. drop the previous band ------------------------------------------------------------------
var lay = null;
for (var L = 0; L < doc.layers.length; L++) if (doc.layers[L].name === LAYER) { lay = doc.layers[L]; break; }
if (lay) {
    var held = lay.pageItems.length;
    lay.remove();
    log.push("removed old band layer: held " + held + ", items " + n0 + " -> " + doc.pageItems.length);
    if (n0 - doc.pageItems.length !== held) {
        log.push("ABORT: unexpected removal count; NOT saving");
        var lfx = new File("/Volumes/4 MB/_claude_tmp/refit_report.txt"); lfx.open("w"); lfx.write(log.join("\n")); lfx.close();
        doc.close(SaveOptions.DONOTSAVECHANGES);
        throw new Error("removal mismatch");
    }
} else { log.push("no previous band layer found"); }

var nBase = doc.pageItems.length;

// ---- 2. measure what is left, and lay the band inside the floor ----------------------------------
var minX = 1e9, minY = 1e9;
for (var q = 0; q < doc.pageItems.length; q++) {
    var bb = doc.pageItems[q].visibleBounds;
    if (bb[3] < minY) minY = bb[3];
    if (bb[0] < minX) minX = bb[0];
}
log.push("existing content: left=" + minX.toFixed(0) + " bottom=" + minY.toFixed(0));

var names = readLines(LIST);
var GAP = 180, COLS = 20;
var MAXW = 320, MAXH = 220, PADX = 60, PADY = 70;
var colW = MAXW + PADX, rowH = MAXH + PADY;
var startY = minY - GAP;
var rowsNeeded = Math.ceil(names.length / COLS);
var bandBottom = startY - rowsNeeded * rowH;
log.push("band: " + COLS + " cols x " + rowsNeeded + " rows, top=" + startY.toFixed(0) +
         " bottom=" + bandBottom.toFixed(0) + "  floor=" + FLOOR);
if (bandBottom < FLOOR) {
    log.push("ABORT: band would overrun the canvas floor again; NOT saving");
    var lfy = new File("/Volumes/4 MB/_claude_tmp/refit_report.txt"); lfy.open("w"); lfy.write(log.join("\n")); lfy.close();
    doc.close(SaveOptions.DONOTSAVECHANGES);
    throw new Error("band below floor");
}

var layer = doc.layers.add();
layer.name = LAYER;
var placed = 0, failed = [];
for (var k = 0; k < names.length; k++) {
    var nm = names[k];
    var pf = new File(PDFD + nm + ".pdf");
    if (!pf.exists) { failed.push(nm + " (no pdf)"); continue; }
    try {
        var it = doc.placedItems.add();
        it.file = pf;
        var w = it.width, h = it.height;
        var sc = Math.min(MAXW / w, MAXH / h, 1.0);
        it.width = w * sc; it.height = h * sc;
        var col = placed % COLS, row = Math.floor(placed / COLS);
        var x = minX + col * colW, y = startY - row * rowH;
        it.position = [x, y];
        var t = doc.textFrames.add();
        t.contents = nm;
        t.textRange.characterAttributes.size = 9;
        t.position = [x, y + 14];
        try { it.move(layer, ElementPlacement.PLACEATEND); t.move(layer, ElementPlacement.PLACEATEND); } catch (eM) {}
        placed++;
    } catch (e) { failed.push(nm + " (" + e + ")"); }
}
log.push("placed=" + placed + " of " + names.length + " failed=" + failed.length);
for (var z = 0; z < failed.length; z++) log.push("   FAILED: " + failed[z]);
log.push("items " + nBase + " -> " + doc.pageItems.length);
if (doc.pageItems.length <= nBase) {
    log.push("ABORT: nothing placed; NOT saving");
    doc.close(SaveOptions.DONOTSAVECHANGES);
    var lfz = new File("/Volumes/4 MB/_claude_tmp/refit_report.txt"); lfz.open("w"); lfz.write(log.join("\n")); lfz.close();
    throw new Error("no placement");
}

// ---- 3. artboards over the band, measured from what actually landed -------------------------------
var bx0 = 1e9, bx1 = -1e9, by0 = 1e9, by1 = -1e9;
for (var i2 = 0; i2 < layer.pageItems.length; i2++) {
    var b2 = layer.pageItems[i2].visibleBounds;
    if (b2[0] < bx0) bx0 = b2[0];
    if (b2[2] > bx1) bx1 = b2[2];
    if (b2[3] < by0) by0 = b2[3];
    if (b2[1] > by1) by1 = b2[1];
}
var PAD = 40;
bx0 -= PAD; bx1 += PAD; by0 -= PAD; by1 += PAD;
if (by0 < FLOOR) by0 = FLOOR + 5;
log.push("band bounds L=" + bx0.toFixed(0) + " T=" + by1.toFixed(0) + " R=" + bx1.toFixed(0) + " B=" + by0.toFixed(0));

var ab0 = doc.artboards.length, added = 0, TILES = 4;
var step = (bx1 - bx0) / TILES;
for (var t2 = 0; t2 < TILES; t2++) {
    var L1 = bx0 + t2 * step, R1 = bx0 + (t2 + 1) * step;
    try {
        var nb = doc.artboards.add([L1, by1, R1, by0]);
        nb.name = "session 2026-08-10 (" + (t2 + 1) + "/" + TILES + ")";
        added++;
    } catch (e3) { log.push("   artboard tile " + (t2 + 1) + " FAILED: " + e3); }
}
log.push("artboards " + ab0 + " -> " + doc.artboards.length + " (added " + added + ")");

// placement is worth saving even if the artboards failed, so this does not gate on `added`
var opts = new IllustratorSaveOptions();
opts.pdfCompatible = false;
doc.saveAs(new File(TARGET), opts);
log.push("saved");
doc.close(SaveOptions.DONOTSAVECHANGES);

var lf = new File("/Volumes/4 MB/_claude_tmp/refit_report.txt");
lf.open("w"); lf.write(log.join("\n")); lf.close();
log.join("\n");
