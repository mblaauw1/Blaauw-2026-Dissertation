// Put the figures back WHERE THEY WERE.
//
// HER 2026-08-21: *"false replacement figures have been placed incorrectly (not in the exact place of the
// thing they replaced)"*. She is right on both counts:
//
//  * `G5_hec1_mad1_dot_quant_linear` REPLACES the magenta/green plot she rejected, but I removed the old one
//    and left the replacement where it already sat -- so the board had a hole where the rejected figure had
//    been and the replacement somewhere else entirely. It now goes into that exact slot
//    (L=-3786.8 T=8222.7 W=1200), the position the removed figure occupied in the 08-20 snapshot.
//
//  * the four `_delta` plots were a 2x2 block at 450x250 with its top-left at (-5259.1, 2549.4), centroid
//    and plate-rotation on TOP, area and roundness BELOW. Resizing them, I moved the block up-left by about
//    (94, 491) AND flipped the row order. Restored to the exact 08-20 anchors.
//
// Widths are the ORIGINAL widths; only the height is recomputed, from each figure's own page aspect, so
// nothing is stretched and nothing lands anywhere she did not put it.
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
SPEC["G1_centroid_movement_combined_meta_trendscaled_delta"] = { L: -5259.1, T: 2549.4, W: 450.0, H: 260.3 };
SPEC["G1_plate_rotation_combined_meta_trendscaled_delta"] = { L: -4805.7, T: 2548.2, W: 451.4, H: 261.1 };
SPEC["G1_area_combined_meta_trendscaled_delta"] = { L: -5256.2, T: 2297.8, W: 446.4, H: 258.2 };
SPEC["G1_roundness_combined_meta_trendscaled_delta"] = { L: -4801.6, T: 2297.8, W: 446.5, H: 258.4 };
SPEC["G5_hec1_mad1_dot_quant_linear"] = { L: -3786.8, T: 8222.7, W: 1200.0, H: 704.3 };
var n = 0;
for (var p = 0; p < placed.length; p++) {
    var id = idOf(placed[p]);
    if (!SPEC.hasOwnProperty(id)) continue;
    var it = placed[p], s = SPEC[id];
    it.width = s.W; it.height = s.H; it.left = s.L; it.top = s.T;
    LOG.push(id + " -> L=" + s.L + " T=" + s.T + "  " + s.W + "x" + s.H);
    n++;
}
if (n > 0) {
    var o = new IllustratorSaveOptions(); o.pdfCompatible = false;
    doc.saveAs(new File(PATH), o);
    LOG.push("SAVED (" + n + " restored to their original positions)");
} else LOG.push("none matched");
app.userInteractionLevel = _uil;
var f = new File("/Volumes/4 MB/_claude_tmp/RESTORE_POSITIONS_20260821.log");
f.open("w"); f.write(LOG.join("\n")); f.close();
LOG.join("\n");
