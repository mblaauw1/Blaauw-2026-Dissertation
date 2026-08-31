// Find where NEW_FIGURES' canvas actually ends, by probing artboard creation. READ-ONLY: never saves.
//
// Four artboard adds over the new band failed with 1095724867 ('CoOA'). Objects may sit outside the canvas
// -- this document's items reached y=-9934 before compaction -- but ARTBOARDS may not, which is the whole
// reason artboardRect kept failing today. Rather than assume the canvas is 16384pt centred on artboard 1
// (which would put the floor at about y=-7492), this measures it: probe a small artboard at descending Y
// until it fails, then the same going up, left and right.
//
// Every probe is removed immediately, and the document is closed WITHOUT saving, so this cannot alter her
// file no matter which probes succeed.

#target illustrator

var TARGET = "/Volumes/4 MB/1_DECKS/NEW_FIGURES_20260804.ai";
var log = [];
var doc = app.open(new File(TARGET));
app.activeDocument = doc;
log.push("artboards=" + doc.artboards.length + " pageItems=" + doc.pageItems.length);

function probe(L, T, R, B) {
    try {
        var ab = doc.artboards.add([L, T, R, B]);
        try { ab.remove(); } catch (e2) {}
        return true;
    } catch (e) { return false; }
}

// descending floor: how low can an artboard's BOTTOM go?
var lo = null;
for (var y = -6000; y >= -11000; y -= 250) {
    if (probe(0, y + 200, 400, y)) lo = y; else { log.push("floor: last OK bottom=" + lo + ", failed at " + y); break; }
}
// refine to 25pt
if (lo !== null) {
    for (var y2 = lo; y2 >= lo - 250; y2 -= 25) {
        if (probe(0, y2 + 200, 400, y2)) lo = y2; else break;
    }
}
log.push("CANVAS FLOOR (lowest artboard bottom): " + lo);

// ceiling
var hi = null;
for (var y3 = 6000; y3 <= 11000; y3 += 250) {
    if (probe(0, y3, 400, y3 - 200)) hi = y3; else { log.push("ceiling: last OK top=" + hi + ", failed at " + y3); break; }
}
log.push("CANVAS CEILING (highest artboard top): " + hi);

// left / right
var lft = null;
for (var x = -5000; x >= -11000; x -= 250) {
    if (probe(x, 0, x + 400, -200)) lft = x; else { log.push("left: last OK=" + lft + ", failed at " + x); break; }
}
var rgt = null;
for (var x2 = 6000; x2 <= 12000; x2 += 250) {
    if (probe(x2 - 400, 0, x2, -200)) rgt = x2; else { log.push("right: last OK=" + rgt + ", failed at " + x2); break; }
}
log.push("CANVAS LEFT=" + lft + "  RIGHT=" + rgt);
log.push("artboards still=" + doc.artboards.length + " (probes removed)");

doc.close(SaveOptions.DONOTSAVECHANGES);
var lf = new File("/Volumes/4 MB/_claude_tmp/canvas_probe.txt");
lf.open("w"); lf.write(log.join("\n")); lf.close();
log.join("\n");
