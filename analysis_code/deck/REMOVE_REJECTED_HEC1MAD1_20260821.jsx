// Remove the mad1/hec1 quantification she rejected outright from board 1.
//
// HER 2026-08-19, board 1 item 1: *"I told you to get the plot of mad1 and hec 1 flourescences and you come
// back with this piece of shit that we've discussed before is completely wrong."*
// Identified from the image she pasted (image6.png in her .docx): it is `G5_hec1_mad1_dot_quant` — MAGENTA
// AND GREEN together, which is NOTES §1 rule 30 (colourblindness), on TWO separate min-max-normalised axes,
// so neither channel's real level is readable and the apparent Mad1 decline is a stretching artefact.
// Its replacement `G5_hec1_mad1_dot_quant_linear` is already placed on the same board: magenta/cyan, ONE
// linear axis, fold over local background, 1.0 reference line. Removing the rejected one, not hers.
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
// guard: only remove the rejected one if its corrected replacement is actually on the document
var haveLinear = false;
for (var q = 0; q < placed.length; q++)
    if (idOf(placed[q]) === "G5_hec1_mad1_dot_quant_linear") haveLinear = true;
var n = 0;
if (!haveLinear) LOG.push("REFUSED: G5_hec1_mad1_dot_quant_linear is not on the document; not removing anything");
else {
    for (var p = placed.length - 1; p >= 0; p--) {
        if (idOf(placed[p]) !== "G5_hec1_mad1_dot_quant") continue;   // exact: not the _linear sibling
        placed[p].remove(); n++;
        LOG.push("removed rejected G5_hec1_mad1_dot_quant");
    }
    if (n > 0) {
        var o = new IllustratorSaveOptions(); o.pdfCompatible = false;
        doc.saveAs(new File(PATH), o);
        LOG.push("SAVED (" + n + " removed; the corrected _linear version stays)");
    } else LOG.push("nothing matched");
}
app.userInteractionLevel = _uil;
var f = new File("/Volumes/4 MB/_claude_tmp/REMOVE_REJECTED_HEC1MAD1_20260821.log");
f.open("w"); f.write(LOG.join("\n")); f.close();
LOG.join("\n");
