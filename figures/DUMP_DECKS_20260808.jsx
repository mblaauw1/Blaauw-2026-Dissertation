// READ-ONLY geometry dump of the four decks, 2026-08-08.
//
// Her rule: dump artboardRect FIRST, before any placement pass. A previous session stacked artboards past
// the canvas and it looked like a hang (AB0 was 1400pt against 2400pt strips, so nothing was ever on it).
// This script opens, measures, closes WITHOUT SAVING. It changes nothing.
//
// Heartbeat: a line is appended to the progress file after every document, so a watchdog can tell
// "still working" from "hung" without waiting out a timeout.
#target illustrator
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}

var HB = new File("/Volumes/4 MB/_claude_tmp/place_heartbeat.txt");
function beat(msg) {
  try { HB.open("a"); HB.writeln((new Date()).getTime() + " " + msg); HB.close(); } catch (e) {}
}

var DOCS = ["/Volumes/4 MB/ablation_plots/META_FIGURES_20260805.ai",
            "/Volumes/4 MB/1_DECKS/NEW_FIGURES_20260804.ai",
            "/Volumes/4 MB/1_DECKS/NEW_TIMESTRIPS_20260804.ai",
            "/Volumes/4 MB/1_DECKS/other_20260820.ai"];

beat("DUMP start");
var out = [];
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
for (var k = 0; k < DOCS.length; k++) {
  var fp = new File(DOCS[k]);
  if (!fp.exists) { out.push(DOCS[k] + " :: MISSING"); beat("missing " + DOCS[k]); continue; }
  var d = app.open(fp);
  var lines = [];
  lines.push("DOC " + d.name + " artboards=" + d.artboards.length + " placed=" + d.placedItems.length);
  for (var a = 0; a < d.artboards.length; a++) {
    var r = d.artboards[a].artboardRect;   // [left, top, right, bottom]
    lines.push("  AB" + a + " name=" + d.artboards[a].name +
               " rect=" + Math.round(r[0]) + "," + Math.round(r[1]) + "," +
               Math.round(r[2]) + "," + Math.round(r[3]) +
               " w=" + Math.round(r[2] - r[0]) + " h=" + Math.round(r[1] - r[3]));
  }
  // which figures are already placed, by linked file basename
  var seen = {};
  for (var i = 0; i < d.placedItems.length; i++) {
    var nm = "(no file)";
    try { nm = d.placedItems[i].file.name; } catch (e2) {}
    seen[nm] = (seen[nm] || 0) + 1;
  }
  var names = [];
  for (var n in seen) { names.push(n + (seen[n] > 1 ? " x" + seen[n] : "")); }
  names.sort();
  lines.push("  PLACED(" + names.length + " distinct): " + names.join(" | "));
  out.push(lines.join("\n"));
  beat("dumped " + d.name + " ab=" + d.artboards.length + " placed=" + d.placedItems.length);
  d.close(SaveOptions.DONOTSAVECHANGES);
}
beat("DUMP done");
var f = new File("/Volumes/4 MB/_claude_tmp/deck_dump_20260808.txt");
f.open("w"); f.write(out.join("\n\n")); f.close();
out.join("\n\n");
