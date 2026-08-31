// Any item THIS SESSION placed that ended up just off the bottom/edge of its artboard is slid back inside.
//
// The de-overlap solver keeps a figure inside the board it is ON; an item that had drifted OFF a board was
// therefore free to move further off. Six of mine finished a few hundred points below a board edge. Items
// that sit on the PASTEBOARD on purpose -- the pieces of strips whose parent was already off-board in her own
// arrangement -- are left exactly where they are: only items within NEAR pt of a board are pulled in, and
// only ones on the session_20260819 layer.
#target illustrator
var TMP = "/Volumes/4 MB/_claude_tmp";
var HB = new File(TMP + "/nudge_heartbeat.txt");
function beat(m) { try { HB.open("a"); HB.writeln(m); HB.close(); } catch (e) {} }
var DECKS = [
  "/Volumes/4 MB/1_DECKS/META_FIGURES_20260814.ai",
  "/Volumes/4 MB/1_DECKS/META_FIGURES_20260813_supplemental.ai",
  "/Volumes/4 MB/1_DECKS/NEW_FIGURES_20260804.ai",
  "/Volumes/4 MB/1_DECKS/META_FIGURES_20260814_PUBLICATION_20260820.ai",
  "/Volumes/4 MB/1_DECKS/META_FIGURES_20260813_supplemental_PUBLICATION_20260820.ai"
];
var LAYNAME = "session_20260819", NEAR = 1500, PAD = 20;
app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
beat("START");
var report = [], i, j;
for (var d = 0; d < DECKS.length; d++) {
  var doc = null;
  try { doc = app.open(new File(DECKS[d])); } catch (e) { report.push("OPEN FAIL " + e); continue; }
  var docName = doc.name;
  var lay = null;
  for (i = 0; i < doc.layers.length; i++) if (doc.layers[i].name === LAYNAME) { lay = doc.layers[i]; break; }
  if (lay === null) { doc.close(SaveOptions.DONOTSAVECHANGES); continue; }
  try { lay.locked = false; } catch (e) {}
  var AB = [];
  for (i = 0; i < doc.artboards.length; i++) AB.push(doc.artboards[i].artboardRect);
  var moved = 0;
  for (i = 0; i < lay.pageItems.length; i++) {
    var it = lay.pageItems[i], b = null;
    try { b = it.visibleBounds; } catch (e) { continue; }
    var w = b[2] - b[0], h = b[1] - b[3];
    var inside = false, best = -1, bestD = 1e12;
    for (j = 0; j < AB.length; j++) {
      var R = AB[j];
      if (b[0] >= R[0] - 1 && b[2] <= R[2] + 1 && b[1] <= R[1] + 1 && b[3] >= R[3] - 1) { inside = true; break; }
      // distance from the item's centre to this board's box
      var cx = (b[0] + b[2]) / 2, cy = (b[1] + b[3]) / 2;
      var dx = Math.max(R[0] - cx, 0, cx - R[2]), dy = Math.max(cy - R[1], 0, R[3] - cy);
      var dd = Math.sqrt(dx * dx + dy * dy);
      if (dd < bestD) { bestD = dd; best = j; }
    }
    if (inside || best < 0 || bestD > NEAR) continue;
    var Rb = AB[best];
    if (w > (Rb[2] - Rb[0]) || h > (Rb[1] - Rb[3])) continue;   // genuinely too big for the board
    var nl = Math.min(Math.max(b[0], Rb[0] + PAD), Rb[2] - PAD - w);
    var nt = Math.max(Math.min(b[1], Rb[1] - PAD), Rb[3] + PAD + h);
    try { it.left = nl; it.top = nt; moved++; } catch (e) {}
  }
  try { doc.selection = null; } catch (e) {}
  var o = new IllustratorSaveOptions();
  o.compatibility = Compatibility.ILLUSTRATOR17; o.pdfCompatible = false;
  doc.saveAs(new File(DECKS[d]), o);
  doc.close(SaveOptions.SAVECHANGES);
  report.push(docName + "\tnudged on-board\t" + moved);
  beat(docName + " nudged " + moved);
}
var rf = new File(TMP + "/nudge_report.txt"); rf.encoding = "UTF-8"; rf.open("w");
for (i = 0; i < report.length; i++) rf.writeln(report[i]);
rf.close();
app.userInteractionLevel = UserInteractionLevel.DISPLAYALERTS;
beat("ALLDONE");
"ALLDONE";
