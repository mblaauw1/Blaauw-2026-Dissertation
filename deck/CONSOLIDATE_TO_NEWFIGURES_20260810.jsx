// Consolidate this session's relocated figures onto NEW_FIGURES, undoing the family-based split.
//
// USER 2026-08-10: "i mean really they should all just go to new_figures".
//
// An earlier pass routed 100 figures to META_FIGURES / supplemental / NEW_TIMESTRIPS by which deck each
// family already lived on. She wants them all on NEW_FIGURES instead, so this:
//   1. deletes the layer "moved from edited 2026-08-10" from each of those three decks, and
//   2. places all 100 onto NEW_FIGURES in one band.
//
// WHY DELETE THE LAYER RATHER THAN RESTORE THE BACKUP. The .bak_pre_mainmove backups are intact, but
// restoring them would also throw away anything she changed on those decks in the meantime. Everything the
// earlier pass added went onto that one named layer and nothing else was touched, so removing the layer
// removes exactly my additions and none of her work -- the surgical option, and the one that respects the
// standing rule that her deck edits are never reverted.
//
// The removal is CHECKED, not assumed: the layer's item count is recorded, and the document's total must
// drop by exactly that many or the file is closed without saving.
//
// Same safety rules as before: app.activeDocument is set before placedItems.add(); artboardRect is never
// assigned (a failed assignment throws 1200 and silently rolls the document back); the item count must move
// in the expected direction before any save; pdfCompatible=false.

#target illustrator

var PDFD  = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/";
var LAYER = "moved from edited 2026-08-10";
var STRIP = ["/Volumes/4 MB/ablation_plots/META_FIGURES_20260805.ai",
             "/Volumes/4 MB/1_DECKS/other.ai",
             "/Volumes/4 MB/1_DECKS/NEW_TIMESTRIPS_20260804.ai"];
var TARGET = "/Volumes/4 MB/1_DECKS/NEW_FIGURES_20260804.ai";
var LIST   = "/Volumes/4 MB/_claude_tmp/place_ALL_newfigures.txt";

var log = [];

function readLines(p) {
    var f = new File(p), out = [];
    if (!f.exists) return out;
    f.open("r");
    while (!f.eof) { var l = f.readln(); if (l && l.replace(/\s/g, "") !== "") out.push(l); }
    f.close();
    return out;
}

// ---- 1. strip the layer off the three decks ------------------------------------------------------
for (var s = 0; s < STRIP.length; s++) {
    var fAI = new File(STRIP[s]);
    log.push("=== strip " + fAI.name + " ===");
    if (!fAI.exists) { log.push("   missing -- skipped"); continue; }
    var d = app.open(fAI);
    app.activeDocument = d;
    var before = d.pageItems.length, lay = null;
    for (var L = 0; L < d.layers.length; L++) if (d.layers[L].name === LAYER) { lay = d.layers[L]; break; }
    if (!lay) { log.push("   layer not found -- nothing removed, not saving"); d.close(SaveOptions.DONOTSAVECHANGES); continue; }
    var owned = lay.pageItems.length;
    lay.remove();
    var after = d.pageItems.length;
    log.push("   layer held " + owned + " items; document " + before + " -> " + after);
    if (before - after !== owned || owned === 0) {
        log.push("   ABORT: unexpected change; NOT saving");
        d.close(SaveOptions.DONOTSAVECHANGES);
        continue;
    }
    var o1 = new IllustratorSaveOptions(); o1.pdfCompatible = false;
    d.saveAs(fAI, o1);
    log.push("   saved");
    d.close(SaveOptions.DONOTSAVECHANGES);
}

// ---- 2. place all 100 onto NEW_FIGURES ------------------------------------------------------------
var names = readLines(LIST);
var tf = new File(TARGET);
log.push("=== place onto " + tf.name + "  (" + names.length + ") ===");
var doc = app.open(tf);
app.activeDocument = doc;
var n0 = doc.pageItems.length;

try {
    var bak = new File(TARGET.replace(/\.ai$/, ".bak_pre_consolidate_20260810.ai"));
    if (!bak.exists) tf.copy(bak);
} catch (eb) { log.push("   backup failed: " + eb); }

var layer = doc.layers.add();
layer.name = LAYER;

var minX = 1e9, minY = 1e9, maxY = -1e9;
for (var i = 0; i < doc.pageItems.length; i++) {
    var b = doc.pageItems[i].visibleBounds;
    if (b[0] < minX) minX = b[0];
    if (b[3] < minY) minY = b[3];
    if (b[1] > maxY) maxY = b[1];
}
if (n0 === 0) { minX = 0; minY = 0; }
log.push("   existing items=" + n0 + "  bottom=" + minY.toFixed(0));

var GAP = 400, MAXW = 900, MAXH = 620, PADX = 120, PADY = 190, COLS = 10;
var startX = minX, startY = minY - GAP, colW = MAXW + PADX, rowH = MAXH + PADY;
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
        var x = startX + col * colW, y = startY - row * rowH;
        it.position = [x, y];
        var t = doc.textFrames.add();
        t.contents = nm;
        t.textRange.characterAttributes.size = 15;
        t.position = [x, y + 26];
        try { it.move(layer, ElementPlacement.PLACEATEND); t.move(layer, ElementPlacement.PLACEATEND); } catch (eM) {}
        placed++;
    } catch (e) { failed.push(nm + " (" + e + ")"); }
}

log.push("   placed=" + placed + " of " + names.length + "  failed=" + failed.length);
for (var q = 0; q < failed.length; q++) log.push("      FAILED: " + failed[q]);
log.push("   items " + n0 + " -> " + doc.pageItems.length);

if (doc.pageItems.length <= n0) {
    log.push("   ABORT: item count did not grow; NOT saving");
    doc.close(SaveOptions.DONOTSAVECHANGES);
} else {
    var o2 = new IllustratorSaveOptions(); o2.pdfCompatible = false;
    doc.saveAs(tf, o2);
    log.push("   saved");
    doc.close(SaveOptions.DONOTSAVECHANGES);
}

var lf = new File("/Volumes/4 MB/_claude_tmp/consolidate_report.txt");
lf.open("w"); lf.write(log.join("\n")); lf.close();
log.join("\n");
