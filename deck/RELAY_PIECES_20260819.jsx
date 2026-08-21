// CORRECTIVE PASS — re-lay the pieces/panels placed by APPLY_TODO0819 so a split figure occupies about the
// same space its parent did, instead of a tall stack that overflows the artboard.
//
// WHAT WENT WRONG AND WHY THIS FIXES IT
//   APPLY_TODO0819 scaled EVERY piece to the parent's full width. That is right for the widest row of a
//   timestrip and wrong for every other piece: a narrow whole-cell row was blown up 3x, and a 6-panel plot
//   became six full-width panels stacked vertically -- six times the parent's height. On NEW_FIGURES, where
//   44 combination figures were split at once, that produced 167 overlapping pairs.
//
//   The fix is two rules, applied per GROUP of pieces that came from one parent:
//     * ONE COMMON SCALE for the whole group, taken from the WIDEST piece, so the pieces keep their true
//       relative sizes. Each piece's natural size is recovered by re-setting its `.file` (which re-places it
//       at 100%), never guessed.
//     * TIMESTRIP pieces (`__pieceN`) stay STACKED, because they are the rows of one strip and their reading
//       order is the figure. PLOT PANELS (`__pN`) are laid out in a GRID, because they were a grid in the
//       parent -- that is what keeps the footprint.
//   Both leave every piece an independent object she can move, which is the whole point of her item 2/16.
//
// Only the `session_20260819` layer is touched: nothing of hers, and nothing placed by an earlier session.
#target illustrator

var TMP = "/Volumes/4 MB/_claude_tmp";
var HB = new File(TMP + "/relay_pieces_heartbeat.txt");
function beat(m) { try { HB.open("a"); HB.writeln(m); HB.close(); } catch (e) {} }

var DECK = {
  "0814":     "/Volumes/4 MB/1_DECKS/META_FIGURES_20260814.ai",
  "0813supp": "/Volumes/4 MB/1_DECKS/META_FIGURES_20260813_supplemental.ai",
  "newfig":   "/Volumes/4 MB/1_DECKS/NEW_FIGURES_20260804.ai",
  "supp":     "/Volumes/4 MB/1_DECKS/other_20260820.ai",
  "newts":    "/Volumes/4 MB/1_DECKS/NEW_TIMESTRIPS_20260804.ai",
  "pub0814":  "/Volumes/4 MB/1_DECKS/META_FIGURES_20260814_PUBLICATION_20260820.ai",
  "pub0813":  "/Volumes/4 MB/1_DECKS/META_FIGURES_20260813_supplemental_PUBLICATION_20260820.ai"
};
var LAYNAME = "session_20260819";
var GAP = 8;

app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
beat("START " + new Date());
var report = [];

function parentOf(nm) {
  var i = nm.indexOf("__piece");
  if (i > 0) return { base: nm.substring(0, i), kind: "strip", idx: parseInt(nm.substring(i + 7), 10) };
  i = nm.lastIndexOf("__p");
  if (i > 0) {
    var tail = nm.substring(i + 3);
    if (tail.length && !isNaN(parseInt(tail, 10)) && tail.indexOf("iece") < 0)
      return { base: nm.substring(0, i), kind: "panel", idx: parseInt(tail, 10) };
  }
  return null;
}

for (var tag in DECK) {
  beat("=== " + tag);
  var doc = null;
  try { doc = app.open(new File(DECK[tag])); } catch (e) { report.push(tag + "\tOPEN FAIL\t" + e); continue; }

  var lay = null, i, j;
  for (i = 0; i < doc.layers.length; i++) if (doc.layers[i].name === LAYNAME) { lay = doc.layers[i]; break; }
  if (lay === null) { report.push(tag + "\tno " + LAYNAME + " layer"); doc.close(SaveOptions.DONOTSAVECHANGES); continue; }
  try { lay.locked = false; lay.visible = true; doc.activeLayer = lay; } catch (e) {}

  // ---- gather groups on our layer ----
  var groups = {};
  for (i = 0; i < lay.pageItems.length; i++) {
    var it = lay.pageItems[i];
    var nm = "";
    try { nm = it.name || ""; } catch (e) {}
    var pr = parentOf(nm);
    if (!pr) continue;
    if (!groups[pr.base]) groups[pr.base] = { kind: pr.kind, items: [] };
    groups[pr.base].items.push({ it: it, idx: pr.idx });
  }

  var nGroups = 0;
  for (var base in groups) {
    var g = groups[base];
    if (g.items.length < 2) continue;
    g.items.sort(function (a, b) { return a.idx - b.idx; });

    // the footprint to fill: the group's current union box (its left/top is where the parent was)
    var L = 1e9, T = -1e9;
    var Wtarget = 0;
    for (i = 0; i < g.items.length; i++) {
      var o = g.items[i].it;
      if (o.left < L) L = o.left;
      if (o.top > T) T = o.top;
      if (o.width > Wtarget) Wtarget = o.width;
    }

    // recover each piece's NATURAL size by re-placing its own file at 100%
    var nat = [];
    for (i = 0; i < g.items.length; i++) {
      var o2 = g.items[i].it;
      try { o2.file = o2.file; } catch (e) {}
      nat.push({ w: o2.width, h: o2.height });
    }
    var maxNatW = 0;
    for (i = 0; i < nat.length; i++) if (nat[i].w > maxNatW) maxNatW = nat[i].w;
    if (maxNatW <= 0) continue;

    if (g.kind === "strip") {
      // ONE common scale from the widest row -> the strip keeps its true proportions and its height
      var S = Wtarget / maxNatW;
      var y = T;
      for (i = 0; i < g.items.length; i++) {
        var o3 = g.items[i].it;
        if (S > 0 && S !== 1) o3.resize(S * 100, S * 100);
        o3.left = L; o3.top = y;
        y -= (o3.height + GAP);
      }
    } else {
      // GRID: as square as the panel count allows, inside the parent's width
      var n = g.items.length;
      var cols = Math.ceil(Math.sqrt(n));
      var cellW = (Wtarget - GAP * (cols - 1)) / cols;
      var S2 = cellW / maxNatW;
      var col = 0, rowTop = T, rowH = 0, x = L;
      for (i = 0; i < n; i++) {
        var o4 = g.items[i].it;
        if (S2 > 0 && S2 !== 1) o4.resize(S2 * 100, S2 * 100);
        o4.left = x; o4.top = rowTop;
        if (o4.height > rowH) rowH = o4.height;
        col++; x += cellW + GAP;
        if (col >= cols && i < n - 1) { col = 0; x = L; rowTop -= (rowH + GAP); rowH = 0; }
      }
    }
    nGroups++;
    if (nGroups % 10 === 0) beat(tag + " groups=" + nGroups);
  }

  try { doc.selection = null; } catch (e) {}
  var opts = new IllustratorSaveOptions();
  opts.compatibility = Compatibility.ILLUSTRATOR17;
  opts.pdfCompatible = false;
  doc.saveAs(new File(DECK[tag]), opts);
  doc.close(SaveOptions.SAVECHANGES);
  report.push(tag + "\tRELAID GROUPS\t" + nGroups);
  beat(tag + " saved, groups=" + nGroups);
}

var rf = new File(TMP + "/relay_pieces_report.txt"); rf.encoding = "UTF-8"; rf.open("w");
for (i = 0; i < report.length; i++) rf.writeln(report[i]);
rf.close();
app.userInteractionLevel = UserInteractionLevel.DISPLAYALERTS;
beat("ALLDONE " + new Date());
"ALLDONE";
