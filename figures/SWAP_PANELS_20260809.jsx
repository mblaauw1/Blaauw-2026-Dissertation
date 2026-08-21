// Replace every multi-panel figure on the four decks with its individual panels. 2026-08-09.
//
// USER: "i do not want any multi-panel figures anywhere on any of the documents" ... "each panel become a
// separate". Timestrips and contact sheets are EXEMPT (her words) and are matched out by name.
//
// LAYOUT IS PRESERVED. Each parent's panels are tiled into EXACTLY the bounding box the parent occupied,
// so the board keeps its topical arrangement and nothing collides with a neighbour — the same screen real
// estate now holds N separate, individually movable objects instead of one grid. That is visually close to
// what was there before, which matters because she arranged these boards by hand.
//
// TRAPS THIS SCRIPT AVOIDS (both cost real time on 2026-08-08):
//   * `path` is RESERVED in ExtendScript and silently resolves to the Illustrator application path ->
//     Error 1200/-54 that looks like a permissions failure. Hence `docPath`.
//   * reading a document property AFTER d.close() throws Error 45 and kills the whole pass. Names are
//     captured BEFORE save/close.
//   * AppleScript's default Apple Event timeout is 120 s -> the caller must wrap in `with timeout of`.
#target illustrator
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}

var HB = new File("/Volumes/4 MB/_claude_tmp/place_heartbeat.txt");
function beat(m) { try { HB.open("a"); HB.writeln((new Date()).getTime() + " " + m); HB.close(); } catch (e) {} }
function readFile(p) { var f = new File(p); f.encoding = "UTF-8"; f.open("r"); var s = f.read(); f.close(); return s; }

var MAP = eval("(" + readFile("/Volumes/4 MB/_claude_tmp/panel_map.json") + ")");
var PDF = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/";
var DOCS = ["/Volumes/4 MB/ablation_plots/META_FIGURES_20260805.ai",
            "/Volumes/4 MB/1_DECKS/NEW_FIGURES_20260804.ai",
            "/Volumes/4 MB/1_DECKS/NEW_TIMESTRIPS_20260804.ai",
            "/Volumes/4 MB/1_DECKS/other_20260820.ai"];
var TS = /timestrip|_aligned$|^nf\d+_|contact|sheet|_strip/i;

beat("SWAP start");
var report = [];
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }

for (var k = 0; k < DOCS.length; k++) {
  var docPath = DOCS[k];
  if (!(new File(docPath)).exists) { beat("missing " + docPath); continue; }
  var d = app.open(new File(docPath));
  var dname = d.name;
  var LFIG = null;
  for (var li = 0; li < d.layers.length; li++) if (d.layers[li].name === "figures") LFIG = d.layers[li];
  if (!LFIG) { LFIG = d.layers.add(); LFIG.name = "figures"; }

  var replaced = 0, added = 0, missing = 0;
  // COLLECT FIRST, THEN MUTATE. The first version walked d.placedItems backwards while REMOVING parents
  // and ADDING panels to the same collection -- the indices shift underneath the loop and parents get
  // skipped (it left 7 on META and 21 on NEW_FIGURES). Snapshot the targets into a plain array, then act.
  var targets = [];
  for (var i = 0; i < d.placedItems.length; i++) {
    var itx = d.placedItems[i], nmx = null;
    try { nmx = itx.file.name; } catch (eF0) { continue; }
    var pidx = nmx.replace(/\.(pdf|png)$/i, "");
    if (TS.test(pidx)) continue;                // timestrips / contact sheets stay whole
    if (MAP[pidx] && MAP[pidx].length) targets.push({ item: itx, pid: pidx });
  }
  for (var ti = 0; ti < targets.length; ti++) {
    var it = targets[ti].item, pid = targets[ti].pid;
    var panels = MAP[pid];

    // the footprint the parent occupied -- the panels will tile into exactly this
    var vb = it.visibleBounds;                  // [left, top, right, bottom]
    var L0 = vb[0], T0 = vb[1], W = vb[2] - vb[0], H = vb[1] - vb[3];
    var n = panels.length;
    var cols = Math.ceil(Math.sqrt(n));
    var rows = Math.ceil(n / cols);
    var cw = W / cols, ch = H / rows, pad = Math.min(cw, ch) * 0.03;

    var placedAny = 0;
    for (var j = 0; j < n; j++) {
      var pf = new File(PDF + panels[j] + ".pdf");
      if (!pf.exists) { missing++; continue; }
      var pi = null;
      try { pi = LFIG.placedItems.add(); pi.file = pf; } catch (eA) { missing++; continue; }
      var availW = cw - 2 * pad, availH = ch - 2 * pad;
      var s = Math.min(availW / pi.width, availH / pi.height);
      pi.width = pi.width * s; pi.height = pi.height * s;
      var c = j % cols, r = Math.floor(j / cols);
      pi.left = L0 + c * cw + pad + (availW - pi.width) / 2;
      pi.top  = T0 - r * ch - pad - (availH - pi.height) / 2;
      placedAny++; added++;
    }
    if (placedAny) {
      try { it.remove(); replaced++; } catch (eR) {}   // the multi-panel parent goes
    }
  }
  beat("swapped " + dname + " parents=" + replaced + " panels=" + added + " missingPDF=" + missing);
  var opts = new IllustratorSaveOptions(); opts.pdfCompatible = false;
  var mode = "saved";
  try { d.saveAs(new File(docPath), opts); } catch (eS) { mode = "SAVE_FAILED " + eS; }
  report.push(dname + " :: parentsReplaced=" + replaced + " panelsPlaced=" + added +
              " missingPDF=" + missing + " save=" + mode);
  try { d.close(SaveOptions.DONOTSAVECHANGES); } catch (eC) {}
}
beat("SWAP done");
var rf = new File("/Volumes/4 MB/_claude_tmp/swap_panels_report.txt");
rf.open("w"); rf.write(report.join("\n")); rf.close();
report.join("\n");
