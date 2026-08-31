// Make room on the crowded artboards by SCALING that board's contents about the board centre.
//
// HER RULE, not an invention: when four figures had to go onto META_FIGURES_20260814 AB4 on 2026-08-17,
// room was made by scaling that board's 15 existing figures to 0.88 about the board centre -- never by
// adding an artboard, because "each artboard corresponds to a figure in the thesis end product"
// (2026-08-19 figure item 11).
//
// The minimal-motion de-overlap solver converged with 22 pairs it could not clear: supplemental board 2 and
// main board 1 are simply full. Scaling the whole board keeps every relative position and every proportion
// -- the figure arrangement she made is preserved exactly, just smaller -- and then the solver can finish.
//
// Only the boards listed here are touched, and only items that lie INSIDE the board.
#target illustrator

var TMP = "/Volumes/4 MB/_claude_tmp";
var HB = new File(TMP + "/make_room_heartbeat.txt");
function beat(m) { try { HB.open("a"); HB.writeln(m); HB.close(); } catch (e) {} }

var JOBS = [
  // 2026-08-21, second pass: pub0814 AB9 still had one 52% overlap the minimal-motion solver could not
  // clear -- a re-split timestrip piece sitting on G2_noc_washout_vs_prophase. Scaling the board again
  // gives the solver somewhere to move it. Her rule: scale the board, never spill onto another artboard.
  { deck: "/Volumes/4 MB/1_DECKS/META_FIGURES_20260814_PUBLICATION_20260820.ai", ab: 9, k: 0.80 }
];

app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
beat("START " + new Date());
var report = [];

for (var j = 0; j < JOBS.length; j++) {
  var job = JOBS[j];
  var doc = null;
  try { doc = app.open(new File(job.deck)); } catch (e) { report.push(job.deck + "\tOPEN FAIL\t" + e); continue; }
  var docName = doc.name;
  beat("opened " + docName + " ab" + job.ab);

  var lockState = [], i;
  for (i = 0; i < doc.layers.length; i++) {
    var Ly = doc.layers[i], st = { lay: Ly, lk: false };
    try { st.lk = Ly.locked; Ly.locked = false; } catch (e) {}
    lockState.push(st);
  }

  var abi = job.ab - 1;
  if (abi < 0 || abi >= doc.artboards.length) {
    report.push(docName + "\tNO ARTBOARD " + job.ab);
    doc.close(SaveOptions.DONOTSAVECHANGES); continue;
  }
  var R = doc.artboards[abi].artboardRect;          // [L,T,R,B]
  var cx = (R[0] + R[2]) / 2.0, cy = (R[1] + R[3]) / 2.0;
  var k = job.k, n = 0;

  for (i = 0; i < doc.pageItems.length; i++) {
    var it = doc.pageItems[i];
    var b = null;
    try { b = it.visibleBounds; } catch (e) { continue; }
    try { if (it.parent.typename !== "Layer") continue; } catch (e) { continue; }   // top-level only
    // strictly INSIDE this board (not merely touching it), so nothing on a neighbouring board moves
    if (!(b[0] >= R[0] - 1 && b[2] <= R[2] + 1 && b[1] <= R[1] + 1 && b[3] >= R[3] - 1)) continue;
    var w = b[2] - b[0], h = b[1] - b[3];
    var ccx = (b[0] + b[2]) / 2.0, ccy = (b[1] + b[3]) / 2.0;
    try {
      it.resize(k * 100, k * 100);
      // resize is about the item's own anchor, so re-place its CENTRE on the scaled-about-board-centre point
      var nb = it.visibleBounds;
      var nw = nb[2] - nb[0], nh = nb[1] - nb[3];
      var tx = cx + (ccx - cx) * k, ty = cy + (ccy - cy) * k;
      it.left = tx - nw / 2.0;
      it.top = ty + nh / 2.0;
      n++;
    } catch (e) {}
  }

  for (i = 0; i < lockState.length; i++) { try { lockState[i].lay.locked = lockState[i].lk; } catch (e) {} }
  try { doc.selection = null; } catch (e) {}
  var opts = new IllustratorSaveOptions();
  opts.compatibility = Compatibility.ILLUSTRATOR17;
  opts.pdfCompatible = false;
  doc.saveAs(new File(job.deck), opts);
  doc.close(SaveOptions.SAVECHANGES);
  report.push(docName + "\tAB" + job.ab + "\tscaled " + n + " items by " + k);
  beat(docName + " ab" + job.ab + " scaled " + n + " by " + k);
}

var rf = new File(TMP + "/make_room_report.txt"); rf.encoding = "UTF-8"; rf.open("w");
for (i = 0; i < report.length; i++) rf.writeln(report[i]);
rf.close();
app.userInteractionLevel = UserInteractionLevel.DISPLAYALERTS;
beat("ALLDONE " + new Date());
"ALLDONE";
