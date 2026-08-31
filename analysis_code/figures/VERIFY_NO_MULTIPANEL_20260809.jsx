// READ-ONLY final check: are there any multi-panel figures left on the four decks? 2026-08-09.
//
// USER: "i do not want any multi-panel figures anywhere on any of the documents" (timestrips and contact
// sheets exempt). This opens each deck, compares every placement against the list of known multi-panel
// parents, and reports anything still there. It changes nothing and saves nothing.
//
// Traps avoided (both cost real time on 2026-08-08): `path` is reserved in ExtendScript, and reading a
// document property after close() throws Error 45. The caller must wrap in `with timeout of`.
#target illustrator
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}
function readFile(p) { var f = new File(p); f.encoding = "UTF-8"; f.open("r"); var s = f.read(); f.close(); return s; }

var MAP = eval("(" + readFile("/Volumes/4 MB/_claude_tmp/panel_map.json") + ")");
var DOCS = ["/Volumes/4 MB/ablation_plots/META_FIGURES_20260805.ai",
            "/Volumes/4 MB/1_DECKS/NEW_FIGURES_20260804.ai",
            "/Volumes/4 MB/1_DECKS/NEW_TIMESTRIPS_20260804.ai",
            "/Volumes/4 MB/1_DECKS/other_20260820.ai"];
var TS = /timestrip|_aligned$|^nf\d+_|contact|sheet|_strip/i;

var out = [];
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
for (var k = 0; k < DOCS.length; k++) {
  var docPath = DOCS[k];
  if (!(new File(docPath)).exists) { out.push(docPath + " :: MISSING"); continue; }
  var d = app.open(new File(docPath));
  var dname = d.name;
  var leftovers = [], panelsPlaced = 0, bullets = 0;
  for (var li = 0; li < d.layers.length; li++)
    if (d.layers[li].name === "legend_bullets") bullets = d.layers[li].pageItems.length;
  for (var i = 0; i < d.placedItems.length; i++) {
    var nm = null;
    try { nm = d.placedItems[i].file.name; } catch (e) { continue; }
    var pid = nm.replace(/\.(pdf|png)$/i, "");
    if (/__p\d+$/.test(pid)) { panelsPlaced++; continue; }
    if (TS.test(pid)) continue;                       // exempt by her instruction
    if (MAP[pid]) leftovers.push(pid);                // a known multi-panel parent still placed
  }
  out.push(dname + " :: placed=" + d.placedItems.length + " panelsPlaced=" + panelsPlaced +
           " bulletItems=" + bullets + " MULTIPANEL_LEFT=" + leftovers.length +
           (leftovers.length ? " -> " + leftovers.slice(0, 8).join(", ") : ""));
  d.close(SaveOptions.DONOTSAVECHANGES);
}
var rf = new File("/Volumes/4 MB/_claude_tmp/verify_nomultipanel_report.txt");
rf.open("w"); rf.write(out.join("\n")); rf.close();
out.join("\n");
