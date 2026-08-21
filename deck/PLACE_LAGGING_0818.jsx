// NEW_FIGURES_20260804.ai — place the two LAGGING-LENGTH figures that were never on a deck (2026-08-18).
// WHY: `annotations/lagging_lengths.csv` (her 2026-07-17 cross marks, 749 marks) built
// G4_lagging_vs_control_length_over_time and G4_lagging_auto_shape_v2, and neither had ever been placed —
// so the store looked unused. Both were also STALE (built 08-10 04:51, marks edited 08-10 16:23) and were
// re-rendered before this pass.
// Placement slots were computed from the read-only geometry dump with a 20 pt occupancy grid and a 40 pt
// margin, so both land INSIDE artboard "NEW 2026-08-05" with no overlap; no existing item is moved.
// Traps honoured (NOTES §8): no var named `path`/`open`/`L`; doc name captured BEFORE close; alerts
// suppressed before open; heartbeat per step; ONE save at the end.
#target illustrator

var AIP = "/Volumes/4 MB/1_DECKS/NEW_FIGURES_20260804.ai";
var PDF = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/";
var HB  = new File("/Volumes/4 MB/_claude_tmp/place_lagging_heartbeat.txt");
function beat(m){ try{ HB.open("a"); HB.writeln(m); HB.close(); }catch(e){} }

// [basename, x_left, y_top, max_width, max_height]  -- artboard "NEW 2026-08-05" is x[0,3740] y[-2900,-200]
var ADD = [
  ["G4_lagging_vs_control_length_over_time", 120,  -2456.8, 604.8, 403.2],
  ["G4_lagging_auto_shape_v2",               2160, -2316.8, 972.0, 403.2]
];

app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
beat("open");
var doc = app.open(new File(AIP));
var docName = doc.name;
beat("opened " + docName + " placed=" + doc.placedItems.length);

// refresh every existing link first, so today's re-renders show on the board
var n = doc.placedItems.length, refreshed = 0, failed = 0;
for (var i = n - 1; i >= 0; i--) {
  var pi = doc.placedItems[i];
  var base = "";
  try { base = pi.file.name.replace(/\.(pdf|png|ai|eps)$/i, ""); } catch (e) { continue; }
  var f = new File(PDF + base + ".pdf");
  if (!f.exists) { continue; }
  try { pi.relink(f); refreshed++; } catch (e) { failed++; }
  if (i % 25 === 0) beat("relink " + i + "/" + n);
}
beat("refreshed=" + refreshed + " failed=" + failed);

var lay;
try { lay = doc.layers.getByName("session_20260818b"); }
catch (e) { lay = doc.layers.add(); lay.name = "session_20260818b"; }

var added = 0;
for (var j = 0; j < ADD.length; j++) {
  var spec = ADD[j];
  var pf = new File(PDF + spec[0] + ".pdf");
  if (!pf.exists) { beat("MISSING " + spec[0]); continue; }
  try {
    var it = lay.placedItems.add();
    it.file = pf;
    var w = it.width, h = it.height;
    var s = Math.min(spec[3] / w, spec[4] / h);      // uniform scale, never distorts
    it.width = w * s; it.height = h * s;
    it.left = spec[1]; it.top = spec[2];
    added++;
    beat("placed " + spec[0] + " at " + spec[1] + "," + spec[2]);
  } catch (e) { beat("FAILED " + spec[0] + " :: " + e); }
}

beat("saving");
doc.save();
doc.close(SaveOptions.SAVECHANGES);
app.userInteractionLevel = UserInteractionLevel.DISPLAYALERTS;
beat("DONE refreshed=" + refreshed + " added=" + added + " failed=" + failed);
"refreshed=" + refreshed + " added=" + added + " failed=" + failed;
