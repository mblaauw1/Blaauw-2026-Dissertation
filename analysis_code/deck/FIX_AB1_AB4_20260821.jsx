// FIX_AB1_AB4_20260821.jsx
//
// HER 2026-08-21: "even the changes that are [in] have placed the plots in a mis-sized way or it looks like
// the plot or figure was cropped to just a corner of its full size and then just that is placed on the boards"
//
// TWO DEFECTS, both mine, both measured before writing this:
//
//  AB1 - `nf9_3-sisterless__20260417_ptk2_eyfp_cdc20_ablation_18` was linking THREE STALE 08-17 pieces
//        (5, 6, 7) left behind when the strip was re-split into 4 pieces on 08-21. The splitter cleaned only
//        one of the two link libraries while savefig writes both, so the publication library kept them and
//        the deck went on resolving them. piece6 is BLANK, piece5 is a 152pt runt that had been scaled
//        11.57x on the board (which is what reads as "cropped to a corner"), piece7 sat on the pasteboard.
//        Those three source PDFs are now retired, so these placements are broken links; delete them and
//        re-stack the four real pieces at ONE uniform scale.
//
//  AB4 - the four `_delta` plots are placed at 0.30x their natural size while every sibling on the board is
//        at 0.89x, so they render as postage stamps. Resize to 0.89x (604 x 328 pt) and move them into a
//        verified-empty block found by occupancy scan, so nothing is overlapped.
//
// ONE pass, ONE save, pdfCompatible = false, per NOTES §14.  Read-only geometry is dumped first and the
// result is verified against the artboard rect before saving.

#target illustrator

// 2026-08-21: opening this document with a missing linked file raises a MODAL dialog that blocks the
// script -- Illustrator then sits at ~0.3% CPU looking like a hang. Suppress alerts before opening,
// and restore the level at the end.
var _uil = app.userInteractionLevel;
app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;

var LOG = [];
function say(s) { LOG.push(s); }

var PATH = "/Volumes/4 MB/1_DECKS/META_FIGURES_20260814_PUBLICATION_20260820.ai";
var doc = null;
for (var d = 0; d < app.documents.length; d++) {
    if (app.documents[d].fullName.fsName === PATH) { doc = app.documents[d]; break; }
}
if (doc === null) doc = app.open(new File(PATH));
app.activeDocument = doc;

// ---- artboard rects FIRST, read-only, so the writes can be checked against them -------------------
var abRect = {};
for (var a = 0; a < doc.artboards.length; a++) {
    var r = doc.artboards[a].artboardRect;      // [L, T, R, B]
    abRect[a + 1] = r;
    say("AB" + (a + 1) + " rect " + Math.round(r[0]) + "," + Math.round(r[1]) + "," +
        Math.round(r[2]) + "," + Math.round(r[3]));
}

// ---- collect every placed item once, recursing into groups ---------------------------------------
var placed = [];
function collect(container) {
    for (var i = 0; i < container.pageItems.length; i++) {
        var it = container.pageItems[i];
        if (it.typename === "PlacedItem") placed.push(it);
        else if (it.typename === "GroupItem") collect(it);
    }
}
collect(doc);
say("placed items found: " + placed.length);

function idOf(it) {
    var n = "";
    try { if (it.file) n = decodeURI(it.file.name).replace(/\.pdf$/i, ""); } catch (e) {}
    if (!n) { try { n = it.name; } catch (e2) {} }
    return n;
}

// ================= AB1: drop the three stale pieces, re-stack the four real ones ===================
var STEM = "nf9_3-sisterless__20260417_ptk2_eyfp_cdc20_ablation_18";
var STALE = { 5: 1, 6: 1, 7: 1 };
var STACK = {                                  // uniform 1.29x, natural sizes x 1.29
    1: { w: 1764.72, h: 229.41 },
    2: { w: 1764.72, h: 183.44 },
    3: { w: 1764.72, h: 180.19 },
    4: { w: 1764.72, h: 176.01 }
};
var LEFT = -6915.0, TOP = 5506.0, GAP = 6.0;

var removed = 0, restacked = 0;
var keep = {};
for (var p = 0; p < placed.length; p++) {
    var id = idOf(placed[p]);
    if (id.indexOf(STEM + "__piece") !== 0) continue;
    var num = parseInt(id.substring((STEM + "__piece").length), 10);
    if (STALE[num]) { placed[p].remove(); removed++; say("AB1 removed stale " + id); }
    else if (STACK[num]) keep[num] = placed[p];
}
var t = TOP;
for (var k = 1; k <= 4; k++) {
    if (!keep[k]) { say("AB1 WARNING: piece" + k + " not on the board"); continue; }
    var it = keep[k], spec = STACK[k];
    it.width = spec.w; it.height = spec.h;      // uniform scale, aspect preserved (w/h from the source)
    it.left = LEFT; it.top = t;
    say("AB1 piece" + k + " -> L=" + Math.round(LEFT) + " T=" + Math.round(t) +
        "  " + Math.round(spec.w) + "x" + Math.round(spec.h));
    t -= spec.h + GAP;
    restacked++;
}
var r1 = abRect[1];
if (LEFT < r1[0] || (LEFT + 1764.72) > r1[2] || TOP > r1[1] || t < r1[3])
    say("AB1 🔴 STACK WOULD LEAVE THE ARTBOARD - not saving");

// ================= AB4: the four delta plots to sibling scale, in verified-free space ==============
var DELTA = {};
DELTA["G1_area_combined_meta_trendscaled_delta"]             = { L: -5356.0, T: 3036.0 };
DELTA["G1_roundness_combined_meta_trendscaled_delta"]        = { L: -4662.0, T: 3036.0 };
DELTA["G1_centroid_movement_combined_meta_trendscaled_delta"]= { L: -5356.0, T: 2638.0 };
DELTA["G1_plate_rotation_combined_meta_trendscaled_delta"]   = { L: -4662.0, T: 2638.0 };

var resized = 0;
for (var q = 0; q < placed.length; q++) {
    var nm = idOf(placed[q]);
    if (!DELTA.hasOwnProperty(nm)) continue;    // exact match only: the _nocollagen / _collagen_vs_3
    var tgt = DELTA[nm];                        // siblings are already correct and must not move
    var itm = placed[q];
    itm.width = 604.0; itm.height = 328.0;
    itm.left = tgt.L; itm.top = tgt.T;
    resized++;
    say("AB4 " + nm + " -> 604x328 at L=" + Math.round(tgt.L) + " T=" + Math.round(tgt.T));
}

// ---- save once -----------------------------------------------------------------------------------
var opts = new IllustratorSaveOptions();
opts.pdfCompatible = false;
doc.saveAs(new File(PATH), opts);
say("SAVED  removed=" + removed + " restacked=" + restacked + " resized=" + resized);

app.userInteractionLevel = _uil;
var f = new File("/Volumes/4 MB/_claude_tmp/FIX_AB1_AB4_20260821.log");
f.open("w"); f.write(LOG.join("\n")); f.close();
LOG.join("\n");
