// Set each figure's height from ITS OWN width AS ILLUSTRATOR MEASURES IT, times the figure's aspect.
// Passing a precomputed height did not clear the drift: the geometry dump reports geometric bounds while
// `PlacedItem.width` reports visible bounds (stroke included), so a height computed from the dump's width
// lands a few percent off. Letting Illustrator divide its own width by the aspect removes that whole class
// of error.
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
var ASP = {};
ASP["G6_polepole_approx_absolute_time"] = 1.5491;
ASP["G6_polar_equivalent_kk_single_vs_triple"] = 1.238779;
ASP["G6_anaphase_kt_speed_single_vs_triple"] = 1.313405;
var n = 0;
for (var p = 0; p < placed.length; p++) {
    var id = idOf(placed[p]);
    if (!ASP.hasOwnProperty(id)) continue;
    var it = placed[p], L = it.left, T = it.top, W = it.width;
    it.height = W / ASP[id]; it.width = W; it.left = L; it.top = T;
    LOG.push(id + ": W=" + Math.round(W) + " aspect=" + ASP[id] + " -> H=" + Math.round(W / ASP[id]));
    n++;
}
if (n > 0) {
    var o = new IllustratorSaveOptions(); o.pdfCompatible = false;
    doc.saveAs(new File(PATH), o);
    LOG.push("SAVED (" + n + ")");
} else LOG.push("none matched");
app.userInteractionLevel = _uil;
var f = new File("/Volumes/4 MB/_claude_tmp/FIX_ASPECT_BY_RATIO_20260821.log");
f.open("w"); f.write(LOG.join("\n")); f.close();
LOG.join("\n");
