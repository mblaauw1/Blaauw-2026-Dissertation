// Add artboards over the newly placed figures on NEW_FIGURES.
//
// USER 2026-08-10: "for more space you can make more artboards".
//
// SEPARATE PASS ON PURPOSE. A failed artboardRect operation throws 1200 and ROLLS THE DOCUMENT BACK, which
// is how 31 placements were discarded earlier today while the script still reported "saved". The compaction
// and placement are already saved; if anything here fails, that work cannot be undone by it.
//
// The band is MEASURED from the items on the "from edited 2026-08-10" layer rather than assumed from the
// numbers the placement script used, then tiled into artboards. Each add is individually guarded, and the
// file is saved only if the artboard count actually grew. Her four existing artboards are left untouched.

#target illustrator

var TARGET = "/Volumes/4 MB/1_DECKS/NEW_FIGURES_20260804.ai";
var LAYER  = "from edited 2026-08-10";
var TILES  = 4;
var log = [];

var doc = app.open(new File(TARGET));
app.activeDocument = doc;
var ab0 = doc.artboards.length;
log.push("artboards before=" + ab0 + "  pageItems=" + doc.pageItems.length);
for (var a = 0; a < doc.artboards.length; a++) {
    var r0 = doc.artboards[a].artboardRect;
    log.push("   existing AB" + a + " [" + r0[0].toFixed(0) + ", " + r0[1].toFixed(0) + ", " +
             r0[2].toFixed(0) + ", " + r0[3].toFixed(0) + "]");
}

var lay = null;
for (var L = 0; L < doc.layers.length; L++) if (doc.layers[L].name === LAYER) { lay = doc.layers[L]; break; }
if (!lay) {
    log.push("ABORT: layer '" + LAYER + "' not found");
    var lf0 = new File("/Volumes/4 MB/_claude_tmp/artboard_report.txt"); lf0.open("w"); lf0.write(log.join("\n")); lf0.close();
    doc.close(SaveOptions.DONOTSAVECHANGES);
    throw new Error("layer missing");
}

var minX = 1e9, maxX = -1e9, minY = 1e9, maxY = -1e9;
for (var i = 0; i < lay.pageItems.length; i++) {
    var b = lay.pageItems[i].visibleBounds;
    if (b[0] < minX) minX = b[0];
    if (b[2] > maxX) maxX = b[2];
    if (b[3] < minY) minY = b[3];
    if (b[1] > maxY) maxY = b[1];
}
var PAD = 60;
minX -= PAD; maxX += PAD; minY -= PAD; maxY += PAD;
log.push("new band measured: L=" + minX.toFixed(0) + " T=" + maxY.toFixed(0) +
         " R=" + maxX.toFixed(0) + " B=" + minY.toFixed(0) +
         "  (" + (maxX - minX).toFixed(0) + " x " + (maxY - minY).toFixed(0) + ")");

var added = 0;
var step = (maxX - minX) / TILES;
for (var t = 0; t < TILES; t++) {
    var L1 = minX + t * step, R1 = minX + (t + 1) * step;
    try {
        var nb = doc.artboards.add([L1, maxY, R1, minY]);
        nb.name = "session 2026-08-10 (" + (t + 1) + " of " + TILES + ")";
        added++;
        log.push("   added [" + L1.toFixed(0) + ", " + maxY.toFixed(0) + ", " + R1.toFixed(0) + ", " + minY.toFixed(0) + "]");
    } catch (e) {
        log.push("   FAILED tile " + (t + 1) + ": " + e);
    }
}

log.push("artboards " + ab0 + " -> " + doc.artboards.length + " (added " + added + ")");
if (doc.artboards.length <= ab0) {
    log.push("ABORT: no artboard added; NOT saving");
    doc.close(SaveOptions.DONOTSAVECHANGES);
} else {
    var opts = new IllustratorSaveOptions();
    opts.pdfCompatible = false;
    doc.saveAs(new File(TARGET), opts);
    log.push("saved");
    doc.close(SaveOptions.DONOTSAVECHANGES);
}

var lf = new File("/Volumes/4 MB/_claude_tmp/artboard_report.txt");
lf.open("w"); lf.write(log.join("\n")); lf.close();
log.join("\n");
