// Step 1 of consolidating onto NEW_FIGURES: undo the family-based split, and MEASURE the target first.
//
// USER 2026-08-10: "i mean really they should all just go to new_figures" ... "the figures currently on
// new_figures have lots of space between them so for more space you can make more artboards and also move
// together the remaining plots".
//
// This script does two things and changes NEW_FIGURES in NO way:
//   1. Removes the layer "moved from edited 2026-08-10" from META_FIGURES / supplemental / NEW_TIMESTRIPS,
//      undoing the earlier routing. Deleting that one named layer removes exactly what the earlier pass
//      added and nothing of hers -- safer than restoring the .bak backups, which would also discard anything
//      she changed on those decks since. The removal is checked: the document total must fall by exactly the
//      layer's item count or the file is closed unsaved.
//   2. Dumps NEW_FIGURES' artboards and the bounds of every top-level item, so the repack and the new
//      artboards are designed from measured geometry rather than guessed at. Measuring first is the whole
//      lesson of the earlier artboard incident: AB0 was 1400pt against 2400pt strips, so nothing was ever on
//      it, and stacking artboards past the canvas looked exactly like a hang.
//
// NEW_FIGURES is opened READ-ONLY here and closed with DONOTSAVECHANGES.

#target illustrator

var LAYER = "moved from edited 2026-08-10";
var STRIP = ["/Volumes/4 MB/ablation_plots/META_FIGURES_20260805.ai",
             "/Volumes/4 MB/1_DECKS/other.ai",
             "/Volumes/4 MB/1_DECKS/NEW_TIMESTRIPS_20260804.ai"];
var TARGET = "/Volumes/4 MB/1_DECKS/NEW_FIGURES_20260804.ai";
var log = [], geo = [];

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

// ---- measure NEW_FIGURES, read-only ---------------------------------------------------------------
var doc = app.open(new File(TARGET));
log.push("=== measure " + doc.name + " ===");
log.push("   layers=" + doc.layers.length + "  pageItems=" + doc.pageItems.length +
         "  placedItems=" + doc.placedItems.length + "  textFrames=" + doc.textFrames.length +
         "  artboards=" + doc.artboards.length);
for (var a = 0; a < doc.artboards.length; a++) {
    var r = doc.artboards[a].artboardRect;
    log.push("   AB" + a + " L=" + r[0].toFixed(0) + " T=" + r[1].toFixed(0) +
             " R=" + r[2].toFixed(0) + " B=" + r[3].toFixed(0) +
             "  (" + (r[2] - r[0]).toFixed(0) + " x " + (r[1] - r[3]).toFixed(0) + ")");
}
for (var L2 = 0; L2 < doc.layers.length; L2++) {
    log.push("   layer[" + L2 + "] '" + doc.layers[L2].name + "' items=" + doc.layers[L2].pageItems.length);
}
// every top-level item: kind, link name, bounds
for (var i = 0; i < doc.pageItems.length; i++) {
    var it = doc.pageItems[i], b = it.visibleBounds, nm = "", kind = it.typename;
    try { if (it.typename === "PlacedItem" && it.file) nm = it.file.name.replace(/\.(pdf|png|ai|eps)$/i, ""); } catch (e) {}
    if (!nm && it.typename === "TextFrame") { try { nm = String(it.contents).substr(0, 40); } catch (e2) {} }
    geo.push([kind, nm, b[0].toFixed(1), b[1].toFixed(1), b[2].toFixed(1), b[3].toFixed(1),
              (it.layer ? it.layer.name : "")].join("\t"));
}
doc.close(SaveOptions.DONOTSAVECHANGES);

var lf = new File("/Volumes/4 MB/_claude_tmp/strip_measure_report.txt");
lf.open("w"); lf.write(log.join("\n")); lf.close();
var gf = new File("/Volumes/4 MB/_claude_tmp/newfigures_geometry.tsv");
gf.open("w"); gf.write(geo.join("\n")); gf.close();
log.join("\n");
