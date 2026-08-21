// Re-place G6_polar_distortion_vs_chromolen_1v3 at its true aspect after the rebuild.
//
// HER STANDING RULE: after re-rendering a placed figure, CHECK ITS ASPECT, not just the link -- a stretched
// figure passes every link check. Rebuilding this one for board-7 item 1 (n 11->14 single, 6->8 triple) and
// item 4 (canonical "Kinetochore distortion" axis) changed the figure's proportions, leaving the existing
// placement 11.4% stretched vertically. Keep the top-left anchor, set the height from the figure's own
// aspect. Width is untouched, so nothing else on the board moves.
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
var TARGET = "G6_polar_distortion_vs_chromolen_1v3", n = 0;
for (var p = 0; p < placed.length; p++) {
    if (idOf(placed[p]) !== TARGET) continue;
    var it = placed[p], L = it.left, T = it.top;
    it.width = 1210.7; it.height = 1177.2; it.left = L; it.top = T;
    LOG.push("re-placed " + TARGET + " -> 1210.7 x 1177.2 at L=" + Math.round(L) + " T=" + Math.round(T));
    n++;
}
if (n === 0) LOG.push("TARGET NOT FOUND - nothing changed");
else {
    var o = new IllustratorSaveOptions(); o.pdfCompatible = false;
    doc.saveAs(new File(PATH), o);
    LOG.push("SAVED (" + n + " placement corrected)");
}
app.userInteractionLevel = _uil;
var f = new File("/Volumes/4 MB/_claude_tmp/FIX_ASPECT_AB7_20260821.log");
f.open("w"); f.write(LOG.join("\n")); f.close();
LOG.join("\n");
