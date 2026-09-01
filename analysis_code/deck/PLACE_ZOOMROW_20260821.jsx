// Place the NEW zoom row of the lagging-rebound strip on artboard 5.
//
// HER 2026-08-19, board 5 items 3 and 8: zoom close-ups of the lagging kinetochore once the cell is in
// anaphase, with a TRANSLUCENT box on the whole-cell frames showing where each zoom looks. The strip now
// renders that row, which makes it a 3-piece strip where the board carries 2 -- so the row exists but was
// not on the deck. Placed directly under piece2, same left edge and same scale, so the three pieces read as
// one strip. Nothing else moves.
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

var NAME = "nf10_lagging-stretch-rebound__20260303_Mad1_Ptk_Eyfpcdc2_ablation_1metaphase_52__piece3";
var SRC  = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf_pub/" + NAME + ".pdf";

// already there?
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
var exists = false;
for (var q = 0; q < placed.length; q++) if (idOf(placed[q]) === NAME) exists = true;

if (exists) LOG.push("already placed - nothing to do");
else if (!(new File(SRC)).exists) LOG.push("REFUSED: source PDF not found: " + SRC);
else {
    // put it on the SAME layer as its sibling pieces, fetched BY NAME (layers[0] is not her top layer)
    var lay = null;
    for (var li = 0; li < doc.layers.length; li++)
        if (doc.layers[li].name === "session_20260819") { lay = doc.layers[li]; break; }
    if (lay === null) lay = doc.layers[0];
    var it = lay.placedItems.add();
    it.file = new File(SRC);
    it.width = 834.8; it.height = 121.5;
    it.left = 786.1;  it.top = 1687.8;
    LOG.push("placed " + NAME + " on layer " + lay.name + " at L=786.1 T=1687.8  834.8x121.5");
    var o = new IllustratorSaveOptions(); o.pdfCompatible = false;
    doc.saveAs(new File(PATH), o);
    LOG.push("SAVED");
}
app.userInteractionLevel = _uil;
var f = new File("/Volumes/4 MB/_claude_tmp/PLACE_ZOOMROW_20260821.log");
f.open("w"); f.write(LOG.join("\n")); f.close();
LOG.join("\n");
