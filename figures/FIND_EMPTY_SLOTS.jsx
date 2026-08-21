#target illustrator
// Find every spot on copy.ai where artwork is SUPPOSED to be but is not:
//   A. placedItems whose linked file cannot be resolved (an empty picture frame)
//   B. captions / titles with no placed art beneath or beside them (an orphaned label)
// Read-only: opens, measures, closes WITHOUT saving. Also re-runs the placement audit so the
// counts are current rather than from an earlier run.
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}

var COPY = "/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
var OUT  = "/Volumes/4 MB/ablation_plots/COPYAI_EMPTY_SLOTS.txt";

for (var q = 0; q < app.documents.length; q++) {
  if (app.documents[q].fullName && app.documents[q].fullName.fsName == COPY) throw new Error("ABORT: copy.ai open");
}
var d = app.open(new File(COPY));
var L = [];

function abOf(b) {
  var cx = (b[0] + b[2]) / 2, cy = (b[1] + b[3]) / 2;
  for (var a = 0; a < d.artboards.length; a++) {
    var r = d.artboards[a].artboardRect;
    if (cx >= r[0] && cx <= r[2] && cy <= r[1] && cy >= r[3]) return a + 1;
  }
  return 0;
}

// ---- A. unresolvable placements ------------------------------------------------------------
var placed = [];
L.push("A. PICTURE FRAMES WITH NO RESOLVABLE LINK");
var nA = 0;
for (var i = 0; i < d.placedItems.length; i++) {
  var p = d.placedItems[i], f = null, err = "";
  try { f = p.file; } catch (e) { err = String(e); }
  var b; try { b = p.visibleBounds; } catch (e) { continue; }
  if (f) { placed.push({ b: b, nm: decodeURI(f.name) }); continue; }
  nA++;
  L.push("   #" + nA + "  artboard " + abOf(b) +
         "  size " + Math.round(b[2] - b[0]) + "x" + Math.round(b[1] - b[3]) + "pt" +
         "  at [" + Math.round(b[0]) + "," + Math.round(b[1]) + "]" +
         "  name='" + (p.name || "") + "'" + (err ? "  err=" + err : ""));
}
if (!nA) L.push("   none");

// ---- B. captions with no art near them -----------------------------------------------------
L.push("");
L.push("B. CAPTIONS / TITLES WITH NO ARTWORK NEAR THEM");
var nB = 0;
for (var i = 0; i < d.textFrames.length; i++) {
  var t = d.textFrames[i], tb;
  try { tb = t.visibleBounds; } catch (e) { continue; }
  var s = String(t.contents).replace(/[\r\n]+/g, " ");
  if (s.length < 6) continue;
  // only consider strings that look like a figure label
  if (!/^(G\d|N\d|DEMO|collagen|frap|polar|ablation|metaDur|firsthalf|ALLcohorts|\d+[\).])/i.test(s)) continue;
  var near = false;
  for (var j = 0; j < placed.length; j++) {
    var b = placed[j].b;
    var dx = Math.max(0, Math.max(b[0] - tb[2], tb[0] - b[2]));
    var dy = Math.max(0, Math.max(tb[3] - b[1], b[3] - tb[1]));
    if (dx < 120 && dy < 200) { near = true; break; }
  }
  if (!near) {
    nB++;
    if (nB <= 40) L.push("   artboard " + abOf(tb) + "  \"" + s.substr(0, 90) + "\"");
  }
}
if (!nB) L.push("   none");
L.push("   (total orphaned labels: " + nB + ")");

var f2 = new File(OUT); f2.open("w"); f2.write(L.join("\r\n")); f2.close();
d.close(SaveOptions.DONOTSAVECHANGES);
"empty_frames=" + nA + "  orphaned_labels=" + nB + "  -> " + OUT;
