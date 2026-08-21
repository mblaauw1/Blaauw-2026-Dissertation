// Remove the superseded two-group prometaphase figures from NEW_FIGURES.
//
// USER 2026-08-10: "the single plot carrying all three gourps of 1-meta, 3-meta, and 1-prometa: also put
// those on new_figures (in place of the plots only showing 1-prometa and 3-meta)".
//
// The three-group figures are already placed. This removes the four two-group ones they supersede, plus the
// name label placed above each. Only these four names are touched, matched exactly against the linked
// file's name -- nothing else on the board is inspected or moved, because everything else there is hers.
// Removal is reported per item and the count is checked before saving, so a silent no-op cannot masquerade
// as success (the same failure that let an earlier placement report "saved" while saving nothing).

#target illustrator

var AI = "/Volumes/4 MB/1_DECKS/NEW_FIGURES_20260804.ai";
var DROP = ["G6_prometa_vs_meta_amplitude", "G6_prometa_vs_meta_period",
            "G6_prometa_vs_meta_meankk", "G6_prometa_vs_meta_model"];

function wanted(n) {
    for (var i = 0; i < DROP.length; i++) if (DROP[i] === n) return true;
    return false;
}

var doc = app.open(new File(AI));
app.activeDocument = doc;
var log = [];
log.push("pageItems before = " + doc.pageItems.length + ", placedItems = " + doc.placedItems.length);

// 1. the placed figures
var killed = 0;
for (var i = doc.placedItems.length - 1; i >= 0; i--) {
    var it = doc.placedItems[i], f = null;
    try { f = it.file; } catch (e) { f = null; }
    if (!f) continue;
    var nm = f.name.replace(/\.pdf$/i, "");
    if (wanted(nm)) { log.push("  removed figure: " + nm); it.remove(); killed++; }
}
// 2. their labels
var killedText = 0;
for (var t = doc.textFrames.length - 1; t >= 0; t--) {
    var tf = doc.textFrames[t], c = "";
    try { c = String(tf.contents).replace(/^\s+|\s+$/g, ""); } catch (e) { continue; }
    if (wanted(c)) { log.push("  removed label: " + c); tf.remove(); killedText++; }
}

log.push("figures removed = " + killed + ", labels removed = " + killedText);
log.push("pageItems after = " + doc.pageItems.length + ", placedItems = " + doc.placedItems.length);

if (killed === 0 && killedText === 0) {
    log.push("NOTHING MATCHED — not saving");
    var lf0 = new File("/tmp/nf_remove_report.txt"); lf0.open("w"); lf0.write(log.join("\n")); lf0.close();
    doc.close(SaveOptions.DONOTSAVECHANGES);
} else {
    var opts = new IllustratorSaveOptions();
    opts.pdfCompatible = false;
    doc.saveAs(new File(AI), opts);
    log.push("saved");
    var lf = new File("/tmp/nf_remove_report.txt"); lf.open("w"); lf.write(log.join("\n")); lf.close();
}
log.join("\n");
