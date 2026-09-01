// NEW_FIGURES: close the vertical gaps, then place this session's 100 figures in the reclaimed space.
//
// USER 2026-08-10: "i mean really they should all just go to new_figures" ... "the figures currently on
// new_figures have lots of space between them so for more space you can make more artboards and also move
// together the remaining plots".
//
// WHY COMPACT AT ALL, beyond her asking. Measured: the 111 figures occupy 10.7% of their bounding box, and
// the content is 17954 pt tall against Illustrator's ~16344 pt canvas. That is almost certainly what threw
// error 1200 on artboardRect earlier today -- the board was already past the canvas, so no artboard could
// ever contain it. Closing the gaps to a uniform 150 pt brings it to 13811 pt and leaves room for the new
// work at a total of 16231 pt.
//
// HOW THE COMPACTION IS SAFE. Items move in whole horizontal BANDS: every item whose vertical centre falls
// in a band -- figure, label, legend bullet alike -- shifts by the SAME amount. Relative geometry inside a
// band is therefore preserved exactly, so nothing comes unstuck from the figure it belongs to. Only the
// empty space between bands changes. Nothing is resized, restyled, reordered or removed.
//
// AND WHY IT CANNOT SCRAMBLE THE FILE. The plan is keyed by item index, which is only valid if this document
// enumerates in the same order as the measuring pass. So every row carries the position that item was
// measured at, and each one is checked before it moves: if more than 5 items disagree by over 1 pt, the
// whole run aborts without saving. An index-keyed edit that silently drifts is precisely the failure mode
// worth refusing to risk on her file.
//
// NO ARTBOARD OPERATIONS HERE. A failed artboardRect assignment ROLLS THE DOCUMENT BACK -- that is how 31
// placements were discarded earlier while the script still reported "saved". Artboards are a separate pass
// with its own save, so a failure there cannot undo this work.

#target illustrator

var TARGET = "/Volumes/4 MB/1_DECKS/NEW_FIGURES_20260804.ai";
var PLAN   = "/Volumes/4 MB/_claude_tmp/compact_plan.tsv";
var LIST   = "/Volumes/4 MB/_claude_tmp/place_ALL_newfigures.txt";
var PDFD   = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/";
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
log.push("opened: pageItems=" + n0 + " artboards=" + doc.artboards.length);

try {
    var bak = new File(TARGET.replace(/\.ai$/, ".bak_pre_compact_20260810.ai"));
    if (!bak.exists) (new File(TARGET)).copy(bak);
    log.push("backup: " + bak.name + " exists=" + bak.exists);
} catch (eb) { log.push("backup FAILED: " + eb); }

// ---- 1. verify the plan lines up with this document ----------------------------------------------
var plan = readLines(PLAN), rowsP = [], bad = 0, checked = 0;
for (var i = 0; i < plan.length; i++) {
    var p = plan[i].split("\t");
    if (p.length < 4) continue;
    rowsP.push({ idx: parseInt(p[0], 10), dy: parseFloat(p[1]), L: parseFloat(p[2]), T: parseFloat(p[3]) });
}
log.push("plan rows=" + rowsP.length + "  document items=" + n0);
if (rowsP.length !== n0) {
    log.push("ABORT: plan/document size mismatch");
    var lfx = new File("/Volumes/4 MB/_claude_tmp/compact_report.txt"); lfx.open("w"); lfx.write(log.join("\n")); lfx.close();
    doc.close(SaveOptions.DONOTSAVECHANGES);
    throw new Error("plan does not match document");
}
for (var v = 0; v < rowsP.length; v++) {
    var b = null;
    try { b = doc.pageItems[rowsP[v].idx].visibleBounds; } catch (e) { b = null; }
    if (b === null) { bad++; continue; }
    checked++;
    if (Math.abs(b[0] - rowsP[v].L) > 1 || Math.abs(b[1] - rowsP[v].T) > 1) bad++;
}
log.push("position check: " + checked + " checked, " + bad + " mismatched");
if (bad > 5) {
    log.push("ABORT: item order differs from the measuring pass; NOT saving");
    var lfy = new File("/Volumes/4 MB/_claude_tmp/compact_report.txt"); lfy.open("w"); lfy.write(log.join("\n")); lfy.close();
    doc.close(SaveOptions.DONOTSAVECHANGES);
    throw new Error("index drift");
}

// ---- 2. compact: shift each band rigidly ---------------------------------------------------------
var moved = 0;
for (var m = 0; m < rowsP.length; m++) {
    if (Math.abs(rowsP[m].dy) <= 0.5) continue;
    try { doc.pageItems[rowsP[m].idx].translate(0, rowsP[m].dy); moved++; } catch (eT) {}
}
log.push("moved " + moved + " items");

var minY2 = 1e9, minX2 = 1e9;
for (var q = 0; q < doc.pageItems.length; q++) {
    var bb = doc.pageItems[q].visibleBounds;
    if (bb[3] < minY2) minY2 = bb[3];
    if (bb[0] < minX2) minX2 = bb[0];
}
log.push("after compaction: bottom=" + minY2.toFixed(0) + " left=" + minX2.toFixed(0));

// ---- 3. place the 100 figures in the reclaimed band ----------------------------------------------
var names = readLines(LIST);
var layer = doc.layers.add();
layer.name = "from edited 2026-08-10";
var MAXW = 480, MAXH = 340, PADX = 80, PADY = 100, COLS = 20, GAP2 = 220;
var colW = MAXW + PADX, rowH = MAXH + PADY;
var startX = minX2, startY = minY2 - GAP2;
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
        it.position = [startX + col * colW, startY - row * rowH];
        var t = doc.textFrames.add();
        t.contents = nm;
        t.textRange.characterAttributes.size = 11;
        t.position = [startX + col * colW, startY - row * rowH + 18];
        try { it.move(layer, ElementPlacement.PLACEATEND); t.move(layer, ElementPlacement.PLACEATEND); } catch (eM) {}
        placed++;
    } catch (e) { failed.push(nm + " (" + e + ")"); }
}
log.push("placed=" + placed + " of " + names.length + "  failed=" + failed.length);
for (var z = 0; z < failed.length; z++) log.push("   FAILED: " + failed[z]);
log.push("items " + n0 + " -> " + doc.pageItems.length);

if (doc.pageItems.length <= n0) {
    log.push("ABORT: item count did not grow; NOT saving");
    doc.close(SaveOptions.DONOTSAVECHANGES);
} else {
    var opts = new IllustratorSaveOptions();
    opts.pdfCompatible = false;
    doc.saveAs(new File(TARGET), opts);
    log.push("saved");
    doc.close(SaveOptions.DONOTSAVECHANGES);
}

var lf = new File("/Volumes/4 MB/_claude_tmp/compact_report.txt");
lf.open("w"); lf.write(log.join("\n")); lf.close();
log.join("\n");
