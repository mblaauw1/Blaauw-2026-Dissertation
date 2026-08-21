// PASS D — apply the minimal-motion de-overlap solved from the CURRENT geometry of the six live decks.
// Each move is the smallest translation that clears the pair while keeping the figure inside its artboard;
// nothing is scaled and nothing that was not in an overlapping pair is touched.
#target illustrator

var TMP = "/Volumes/4 MB/_claude_tmp";
var HB  = new File(TMP + "/deoverlap_heartbeat.txt");
function beat(m) { try { HB.open("a"); HB.writeln(m); HB.close(); } catch (e) {} }
function readAll(fp) { var f = new File(fp); f.encoding = "UTF-8"; f.open("r"); var s = f.read(); f.close(); return s; }

var DECK = {
  "0814":     "/Volumes/4 MB/1_DECKS/META_FIGURES_20260814.ai",
  "0813supp": "/Volumes/4 MB/1_DECKS/META_FIGURES_20260813_supplemental.ai",
  "newfig":   "/Volumes/4 MB/1_DECKS/NEW_FIGURES_20260804.ai",
  "0805":     "/Volumes/4 MB/ablation_plots/META_FIGURES_20260805.ai",
  "supp":     "/Volumes/4 MB/1_DECKS/other.ai",
  "newts":    "/Volumes/4 MB/1_DECKS/NEW_TIMESTRIPS_20260804.ai"
};

app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
beat("START");
var plan = eval("(" + readAll(TMP + "/deoverlap_moves_20260817.json") + ")");
var report = [];
var i;

for (var tag in DECK) {
  var mv = plan[tag] ? plan[tag].moves : [];
  if (!mv || mv.length === 0) continue;
  var byKey = {};
  for (i = 0; i < mv.length; i++) byKey[mv[i].key] = mv[i];

  beat("open " + tag);
  var doc = app.open(new File(DECK[tag]));
  var lockState = [];
  for (i = 0; i < doc.layers.length; i++) {
    var Ly = doc.layers[i]; var st = { lay: Ly, lk: false };
    try { st.lk = Ly.locked; Ly.locked = false; } catch (e) {}
    lockState.push(st);
  }

  var done = 0, miss = 0, seen = {};
  for (i = 0; i < doc.pageItems.length; i++) {
    var it = doc.pageItems[i], b = null;
    try { b = it.visibleBounds; } catch (e) { continue; }
    try { if (it.parent.typename !== "Layer") continue; } catch (e) { continue; }
    var key = it.typename + "|" + b[0].toFixed(1) + "|" + b[1].toFixed(1);
    var m = byKey[key];
    if (!m || seen[key]) continue;
    try { it.translate(m.dx, m.dy); done++; seen[key] = 1; } catch (e) {}
  }
  for (var kx in byKey) if (!seen[kx]) miss++;
  beat(tag + " moved=" + done + " unmatched=" + miss);
  report.push(tag + "\tMOVED\t" + done + "\tUNMATCHED\t" + miss);

  for (i = 0; i < lockState.length; i++) { try { lockState[i].lay.locked = lockState[i].lk; } catch (e) {} }
  try { doc.selection = null; } catch (e) {}
  var opts = new IllustratorSaveOptions();
  opts.compatibility = Compatibility.ILLUSTRATOR17;
  opts.pdfCompatible = false;
  doc.saveAs(new File(DECK[tag]), opts);
  doc.close(SaveOptions.SAVECHANGES);
  beat(tag + " saved");
}

var rf = new File(TMP + "/deoverlap_report.txt"); rf.encoding = "UTF-8"; rf.open("w");
for (i = 0; i < report.length; i++) rf.writeln(report[i]);
rf.close();
app.userInteractionLevel = UserInteractionLevel.DISPLAYALERTS;
beat("ALLDONE");
report.join("\n");
