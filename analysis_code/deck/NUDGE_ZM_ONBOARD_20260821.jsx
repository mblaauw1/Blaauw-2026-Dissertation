// Bring the two ZM drug strips fully onto their artboards.
//
// `G9_drug_timestrip_zm18_aligned` pieces ran off the TOP of artboard 2 (piece4) and the top of artboard 5
// (piece5) -- 87-91% visible, so the top of those frames was being cut by the artboard edge on export. The
// whole FAMILY is shifted by one offset per artboard, never a single piece: moving one piece of a split
// strip would break its alignment with its siblings, which is the defect this pass exists to remove.
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
var NUDGE = {};
NUDGE["G9_drug_timestrip_zm18_aligned__piece4"] = { dx: 0.0, dy: 53.1 };
NUDGE["G9_drug_timestrip_zm18_aligned__piece3"] = { dx: 0.0, dy: 53.1 };
NUDGE["G9_drug_timestrip_zm18_aligned__piece2"] = { dx: 0.0, dy: 53.1 };
NUDGE["G9_drug_timestrip_zm18_aligned__piece1"] = { dx: 0.0, dy: 53.1 };
NUDGE["G9_drug_timestrip_zm18_aligned__piece5"] = { dx: 0.0, dy: -146.9 };
var n = 0;
for (var p = 0; p < placed.length; p++) {
    var id = idOf(placed[p]);
    if (!NUDGE.hasOwnProperty(id)) continue;
    var it = placed[p];
    it.left = it.left + NUDGE[id].dx;
    it.top  = it.top  + NUDGE[id].dy;
    LOG.push(id + "  dx=" + NUDGE[id].dx + " dy=" + NUDGE[id].dy);
    n++;
}
if (n > 0) {
    var o = new IllustratorSaveOptions(); o.pdfCompatible = false;
    doc.saveAs(new File(PATH), o);
    LOG.push("SAVED (" + n + " nudged)");
} else LOG.push("none matched");
app.userInteractionLevel = _uil;
var f = new File("/Volumes/4 MB/_claude_tmp/NUDGE_ZM_20260821.log");
f.open("w"); f.write(LOG.join("\n")); f.close();
LOG.join("\n");
