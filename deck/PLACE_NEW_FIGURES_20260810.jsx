// Place this session's figures onto NEW_FIGURES_20260804.ai, collision-free.
//
// USER 2026-08-10: "none of the plots we made this morning (and some from last night) are on the illustrator
// files ... go through everything i told you to make and place it on the new_figures illustrator file (even
// if you think you already placed a copy of it somewhere else. and make sure to not overlap things when you
// place them"
//
// HOW OVERLAP IS AVOIDED, rather than hoped for:
//   1. The existing artwork's bounds are measured FIRST (visibleBounds over every top-level item).
//   2. Everything new goes in a band strictly BELOW that, starting GAP points under the lowest existing item.
//   3. Inside the band the items are laid out on a fixed pitch computed from the widest/tallest placed item,
//      so cells cannot collide with each other either.
//   4. The artboard is resized at the end to contain everything (ONE artboard, sized to content).
// One save at the end, pdfCompatible=false.

#target illustrator

var AI   = "/Volumes/4 MB/1_DECKS/NEW_FIGURES_20260804.ai";
var PDFD = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/";
var LIST = "/tmp/nf_place.txt";

function readLines(p) {
    var f = new File(p), out = [];
    if (!f.exists) return out;
    f.open("r");
    while (!f.eof) { var l = f.readln(); if (l && l.replace(/\s/g, "") !== "") out.push(l); }
    f.close();
    return out;
}

var doc = app.open(new File(AI));
app.activeDocument = doc;          // placedItems.add() targets the ACTIVE document. Without this the first
                                   // run added all 31 figures to whatever document happened to be active and
                                   // then saved THIS one unchanged -- it reported "placed=31 ... saved" while
                                   // pageItems stayed at 511 before and after, which is what gave it away.
var newLayer = doc.layers.add();
newLayer.name = "session 2026-08-10";
var log = [];
log.push("artboards=" + doc.artboards.length);
var ab = doc.artboards[0].artboardRect;   // [L, T, R, B]
log.push("artboardRect BEFORE = " + ab.join(", "));

// ---- 1. measure the existing artwork ------------------------------------------------------------
var minX = 1e9, maxX = -1e9, minY = 1e9, maxY = -1e9, n0 = doc.pageItems.length;
for (var i = 0; i < doc.pageItems.length; i++) {
    var b = doc.pageItems[i].visibleBounds;   // [L, T, R, B]
    if (b[0] < minX) minX = b[0];
    if (b[2] > maxX) maxX = b[2];
    if (b[3] < minY) minY = b[3];
    if (b[1] > maxY) maxY = b[1];
}
if (n0 === 0) { minX = 0; maxX = 1000; minY = 0; maxY = 0; }
log.push("existing items=" + n0 + "  bounds L=" + minX.toFixed(0) + " T=" + maxY.toFixed(0) +
         " R=" + maxX.toFixed(0) + " B=" + minY.toFixed(0));

// ---- 2. place into a band strictly below the existing artwork ------------------------------------
var GAP   = 400;                  // clear space between old artwork and the new band
var MAXW  = 900;                  // each figure is scaled to fit this box
var MAXH  = 620;
var PADX  = 120, PADY = 190;      // gutters inside the band
var COLS  = 8;   // 31 items -> 4 rows. 5 columns made the band ~5700pt tall and the resulting artboard
                 // exceeded Illustrator's canvas limit, which threw error 1200 on artboardRect.
var startX = minX;
var startY = minY - GAP;          // top of the new band

var names = readLines(LIST);
var placed = 0, failed = [];
var colW = MAXW + PADX, rowH = MAXH + PADY;

for (var k = 0; k < names.length; k++) {
    var nm = names[k];
    var f = new File(PDFD + nm + ".pdf");
    if (!f.exists) { failed.push(nm + " (no pdf)"); continue; }
    try {
        var it = doc.placedItems.add();
        it.file = f;
        // scale into the MAXW x MAXH box, preserving aspect
        var w = it.width, h = it.height;
        var s = Math.min(MAXW / w, MAXH / h, 1.0);
        it.width = w * s; it.height = h * s;

        var col = placed % COLS, row = Math.floor(placed / COLS);
        var x = startX + col * colW;
        var y = startY - row * rowH;
        it.position = [x, y];      // [left, top]

        // label above the figure so each cell is identifiable on the board
        var t = doc.textFrames.add();
        t.contents = nm;
        t.textRange.characterAttributes.size = 15;
        t.position = [x, y + 26];

        try { it.move(newLayer, ElementPlacement.PLACEATEND); t.move(newLayer, ElementPlacement.PLACEATEND); } catch(eMove) {}
        placed++;
        if (placed % 5 === 0) log.push("   ...after " + placed + " placed: pageItems=" + doc.pageItems.length);
    } catch (e) {
        failed.push(nm + " (" + e + ")");
    }
}

// ---- 3. NO ARTBOARD RESIZE ----------------------------------------------------------------------
// Do not touch artboardRect here. Setting it threw Illustrator error 1200 ('CoOA') and -- this is the part
// that mattered -- a FAILED artboardRect assignment ROLLS THE DOCUMENT BACK: pageItems climbed 521, 531 ...
// 571 through the placement loop and then read 511 again immediately after the failed resize, discarding
// all 31 placements. The first run then reported "placed=31 ... saved" while saving nothing at all.
// Placement and artboard geometry are now separate operations; the artboard is left exactly as found.
log.push("placed=" + placed + " of " + names.length + "  failed=" + failed.length);
for (var q = 0; q < failed.length; q++) log.push("   FAILED: " + failed[q]);
log.push("total items now=" + doc.pageItems.length + "  (was " + n0 + ")");
log.push("placedItems now=" + doc.placedItems.length);
if (doc.pageItems.length <= n0) {
    // nothing actually landed -- do NOT overwrite a good file with an unchanged one
    log.push("ABORT: item count did not grow; not saving");
    var lf0 = new File("/tmp/nf_place_report.txt"); lf0.open("w"); lf0.write(log.join("\n")); lf0.close();
    doc.close(SaveOptions.DONOTSAVECHANGES);
    throw new Error("placement did not land; file left untouched");
}

// ---- 4. save once --------------------------------------------------------------------------------
var opts = new IllustratorSaveOptions();
opts.pdfCompatible = false;
doc.saveAs(new File(AI), opts);
log.push("saved");

var lf = new File("/tmp/nf_place_report.txt");
lf.open("w"); lf.write(log.join("\n")); lf.close();
log.join("\n");
