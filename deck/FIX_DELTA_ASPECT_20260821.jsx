// Correct the four AB4 delta placements to each figure's OWN aspect.
//
// Resizing all four to a single 604 x 328 was my error: their natural aspects differ slightly, so a shared
// height left every one of them ~3% stretched. Width is kept (they are meant to sit on a common column
// width); height comes from each figure's own page size. Top-left anchor preserved, so the grid holds.
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
SPEC["G1_plate_rotation_combined_meta_trendscaled_delta"] = { W: 604.0, H: 337.3 };
SPEC["G1_centroid_movement_combined_meta_trendscaled_delta"] = { W: 604.0, H: 337.7 };
SPEC["G1_roundness_combined_meta_trendscaled_delta"] = { W: 604.0, H: 337.8 };
SPEC["G1_area_combined_meta_trendscaled_delta"] = { W: 604.0, H: 337.7 };
var n = 0;
for (var p = 0; p < placed.length; p++) {
    var id = idOf(placed[p]);
    if (!SPEC.hasOwnProperty(id)) continue;
    var it = placed[p], L = it.left, T = it.top;
    it.width = SPEC[id].W; it.height = SPEC[id].H; it.left = L; it.top = T;
    LOG.push(id + " -> " + SPEC[id].W + " x " + SPEC[id].H);
    n++;
}
if (n > 0) {
    var o = new IllustratorSaveOptions(); o.pdfCompatible = false;
    doc.saveAs(new File(PATH), o);
    LOG.push("SAVED (" + n + " corrected)");
} else LOG.push("none matched");
app.userInteractionLevel = _uil;
var f = new File("/Volumes/4 MB/_claude_tmp/FIX_DELTA_ASPECT_20260821.log");
f.open("w"); f.write(LOG.join("\n")); f.close();
LOG.join("\n");
