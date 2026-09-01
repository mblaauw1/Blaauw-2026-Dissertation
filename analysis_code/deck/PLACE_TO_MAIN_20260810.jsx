// Move recent work onto the four main decks: place each figure where its family already lives.
//
// USER 2026-08-10: "if any of the figures in it are ones that i have been editing or created recently - like
// as in today, then thy shouldnt be in there. they should be in one of the four main files" ... "that goes
// for all of the figures youre putting in these new locaitons".
//
// The four main files are the four .ai modified today: NEW_FIGURES, META_FIGURES, supplemental,
// NEW_TIMESTRIPS. 138 figures on ablation_figures_edited.ai were rebuilt today or yesterday; 37 of those are
// already on a main deck, and the 101 here are not. Each is routed to the deck where its own G-group's
// siblings already sit (timestrips to NEW_TIMESTRIPS), so nothing lands somewhere arbitrary.
//
// HOW OVERLAP IS AVOIDED, rather than hoped for: existing bounds are measured first, everything new goes in
// a band strictly BELOW the lowest existing item, and inside that band items sit on a fixed pitch, so new
// work can collide neither with hers nor with itself. Each figure gets its name as a label above it, and all
// of it goes on its own dated layer so it is trivially distinguishable from her layout.
//
// SAFETY, every rule learned the hard way earlier today:
//   - app.activeDocument = doc, or placedItems.add() silently targets whatever document was already open.
//   - artboardRect is NEVER assigned: a failed assignment throws 1200 and ROLLS THE DOCUMENT BACK, which
//     once discarded 31 placements while the script still reported "saved".
//   - the item count must GROW or the file is closed without saving, so a no-op can never overwrite a good
//     file with an unchanged one.
//   - a backup copy is written before saving, and pdfCompatible=false.
// Her existing artwork is never moved, restyled or removed by this script.

#target illustrator

var PDFD = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/";
var JOBS = [
  { ai: "/Volumes/4 MB/ablation_plots/META_FIGURES_20260805.ai",
    list: "/Volumes/4 MB/_claude_tmp/place_META_FIGURES_20260805.txt" },
  { ai: "/Volumes/4 MB/1_DECKS/other.ai",
    list: "/Volumes/4 MB/_claude_tmp/place_supplemental.txt" },
  { ai: "/Volumes/4 MB/1_DECKS/NEW_TIMESTRIPS_20260804.ai",
    list: "/Volumes/4 MB/_claude_tmp/place_NEW_TIMESTRIPS_20260804.txt" }
];

var GAP = 400, MAXW = 900, MAXH = 620, PADX = 120, PADY = 190, COLS = 8;
var log = [];

function readLines(p) {
    var f = new File(p), out = [];
    if (!f.exists) return out;
    f.open("r");
    while (!f.eof) { var l = f.readln(); if (l && l.replace(/\s/g, "") !== "") out.push(l); }
    f.close();
    return out;
}

for (var j = 0; j < JOBS.length; j++) {
    var job = JOBS[j];
    var names = readLines(job.list);
    var aiFile = new File(job.ai);
    log.push("=== " + aiFile.name + "  (" + names.length + " to place) ===");
    if (!aiFile.exists) { log.push("   MISSING DECK -- skipped"); continue; }
    if (names.length === 0) { log.push("   nothing to place -- skipped"); continue; }

    var doc = app.open(aiFile);
    app.activeDocument = doc;
    var n0 = doc.pageItems.length;

    // backup before any modification, so the previous state is always recoverable
    try {
        var bak = new File(job.ai.replace(/\.ai$/, ".bak_pre_mainmove_20260810.ai"));
        if (!bak.exists) aiFile.copy(bak);
    } catch (eb) { log.push("   backup failed: " + eb); }

    var layer = doc.layers.add();
    layer.name = "moved from edited 2026-08-10";

    var minX = 1e9, maxX = -1e9, minY = 1e9, maxY = -1e9;
    for (var i = 0; i < doc.pageItems.length; i++) {
        var b = doc.pageItems[i].visibleBounds;
        if (b[0] < minX) minX = b[0];
        if (b[2] > maxX) maxX = b[2];
        if (b[3] < minY) minY = b[3];
        if (b[1] > maxY) maxY = b[1];
    }
    if (n0 === 0) { minX = 0; maxX = 1000; minY = 0; maxY = 0; }
    log.push("   existing items=" + n0 + "  bottom=" + minY.toFixed(0));

    var startX = minX, startY = minY - GAP;
    var colW = MAXW + PADX, rowH = MAXH + PADY;
    var placed = 0, failed = [];

    for (var k = 0; k < names.length; k++) {
        var nm = names[k];
        var f = new File(PDFD + nm + ".pdf");
        if (!f.exists) { failed.push(nm + " (no pdf)"); continue; }
        try {
            var it = doc.placedItems.add();
            it.file = f;
            var w = it.width, h = it.height;
            var s = Math.min(MAXW / w, MAXH / h, 1.0);
            it.width = w * s; it.height = h * s;
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
        continue;
    }
    var opts = new IllustratorSaveOptions();
    opts.pdfCompatible = false;
    doc.saveAs(aiFile, opts);
    log.push("   saved");
    doc.close(SaveOptions.DONOTSAVECHANGES);
}

var lf = new File("/Volumes/4 MB/_claude_tmp/place_main_report.txt");
lf.open("w"); lf.write(log.join("\n")); lf.close();
log.join("\n");
