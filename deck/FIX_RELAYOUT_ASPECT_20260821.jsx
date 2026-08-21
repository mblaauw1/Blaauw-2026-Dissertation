// Re-place the three figures whose PUBLICATION render changed shape when pub_strip started re-running
// tight_layout() after stripping text (the fix for her board-8 item 7: a clipped y-axis label).
// Width is kept; height comes from each figure's own page aspect. Top-left anchor preserved.
#target illustrator
var _uil = app.userInteractionLevel;
app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
var LOG = [];
var PATH = "/Volumes/4 MB/1_DECKS/META_FIGURES_20260814_PUBLICATION_20260820.ai";
var doc = null;
for (var d = 0; d < app.documents.length; d++)
    if (app.documents[d].fullName.fsName === PATH) { doc = app.documents[d]; break; }
if (doc === null) doc = app.open(new File(PATH));
app.activeDocument = doc;
var placed = [];
function collect(c) {
    for (var i = 0; i < c.pageItems.length; i++) {
        var it = c.pageItems[i];
        if (it.typename === "PlacedItem") placed.push(it);
        else if (it.typename === "GroupItem") collect(it);
    }
}
collect(doc);
function idOf(it) {
    var n = ""; try { if (it.file) n = decodeURI(it.file.name).replace(/\.pdf$/i, ""); } catch (e) {}
    if (!n) { try { n = it.name; } catch (e2) {} } return n;
}
var SPEC = {};
SPEC["G6_polepole_approx_absolute_time"] = 346.8;
SPEC["G6_polar_equivalent_kk_single_vs_triple"] = 1007.4;
SPEC["G6_anaphase_kt_speed_single_vs_triple"] = 669.8;
var n = 0;
for (var p = 0; p < placed.length; p++) {
    var id = idOf(placed[p]);
    if (!SPEC.hasOwnProperty(id)) continue;
    var it = placed[p], L = it.left, T = it.top, W = it.width;
    it.width = W; it.height = SPEC[id]; it.left = L; it.top = T;
    LOG.push(id + " -> H=" + SPEC[id] + " (W kept " + Math.round(W) + ")");
    n++;
}
if (n > 0) {
    var o = new IllustratorSaveOptions(); o.pdfCompatible = false;
    doc.saveAs(new File(PATH), o);
    LOG.push("SAVED (" + n + " re-placed)");
} else LOG.push("none matched");
app.userInteractionLevel = _uil;
var f = new File("/Volumes/4 MB/_claude_tmp/FIX_RELAYOUT_ASPECT_20260821.log");
f.open("w"); f.write(LOG.join("\n")); f.close();
LOG.join("\n");
