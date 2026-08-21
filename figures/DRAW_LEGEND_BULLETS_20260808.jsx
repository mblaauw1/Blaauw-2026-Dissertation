// Draw the recomputed legend bullet points under every placed figure, on all four decks. 2026-08-08.
//
// USER: "go through the plots on the main four illustrator files and update the legends bullet points ...
// recalculate statiscics and N values ... so the legend bullet points are complete and updated."
//
// The bullet TEXT is computed in Python (dataops/build_legend_bullets_20260808.py) from each figure's own
// data CSV, so the numbers can never disagree with the figure above them. This script only draws.
//
// IDEMPOTENT. Bullets live on their own layer `legend_bullets`, and that layer is cleared before drawing,
// so re-running replaces rather than accumulates. Nothing else on the board is touched -- in particular
// her own edits and deletions are never restored.
// Text is anchored to the figure's own bounding box, so a moved figure keeps its legend.
#target illustrator
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}

var HB = new File("/Volumes/4 MB/_claude_tmp/place_heartbeat.txt");
function beat(m) { try { HB.open("a"); HB.writeln((new Date()).getTime() + " " + m); HB.close(); } catch (e) {} }
function readFile(p) { var f = new File(p); f.encoding = "UTF-8"; f.open("r"); var s = f.read(); f.close(); return s; }

var PS = eval("(" + readFile("/Volumes/4 MB/ablation_plots/PLOT_SETTINGS.json") + ")");
// 2026-08-18: this list still named META_FIGURES_20260805.ai, which was RETIRED on 2026-08-17 and is no
// longer at that path, and it omitted the two live META decks entirely -- so a run would have failed on the
// first document and, if it had not, would have left 0814/0813supp without bullets. These are the FIVE LIVE
// decks (NOTES 2026-08-16 (5), handoff-13).
var DOCS = ["/Volumes/4 MB/1_DECKS/META_FIGURES_20260814.ai",
            "/Volumes/4 MB/1_DECKS/META_FIGURES_20260813_supplemental.ai",
            "/Volumes/4 MB/1_DECKS/NEW_FIGURES_20260804.ai",
            "/Volumes/4 MB/1_DECKS/NEW_TIMESTRIPS_20260804.ai",
            "/Volumes/4 MB/1_DECKS/other_20260820.ai"];
var FS = 9, LEAD = 11.5, MAXW = 900;

beat("BULLETS start");
var report = [];
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }

for (var k = 0; k < DOCS.length; k++) {
  // `path` IS RESERVED IN EXTENDSCRIPT and silently resolves to the Illustrator APPLICATION path,
  // so app.open() tried to open the app bundle and threw Error 1200/-54. Hence `docPath`.
  var docPath = DOCS[k];
  if (!(new File(docPath)).exists) { beat("missing " + docPath); continue; }
  var d = app.open(new File(docPath));

  // dedicated layer, cleared -> idempotent
  var L = null;
  for (var li = 0; li < d.layers.length; li++) if (d.layers[li].name === "legend_bullets") L = d.layers[li];
  if (L) {
    try { L.locked = false; L.visible = true; } catch (eL) {}
    // 🔴 CLEAR ONLY THE BULLET TEXT. 2026-08-19: this loop used to remove EVERY item on the layer, and
    // FIGURES had ended up on it in an earlier session (NOTES §1 rule 24 -- "never put a PlacedItem on a
    // mark layer"). The 2026-08-18 redraw therefore DELETED 15 placed figures from META_FIGURES_20260814
    // and 15 from the supplemental. They survived only because the two *_PUBLICATION copies were not in
    // this script's deck list, and had to be synced back off them on 2026-08-19.
    // A figure found here is RESCUED onto the `figures` layer instead of being destroyed, and reported.
    var rescued = 0;
    var figLayer = null;
    for (var fl = 0; fl < d.layers.length; fl++) if (d.layers[fl].name === "figures") figLayer = d.layers[fl];
    for (var q = L.pageItems.length - 1; q >= 0; q--) {
      var itc = L.pageItems[q];
      var tn = "";
      try { tn = itc.typename; } catch (eT) {}
      if (tn === "TextFrame") { try { itc.remove(); } catch (eR) {} continue; }
      // anything that is NOT bullet text is art: move it out of harm's way, never delete it
      try {
        if (figLayer !== null) { figLayer.locked = false; itc.move(figLayer, ElementPlacement.PLACEATEND); }
        rescued++;
      } catch (eM) {}
    }
    if (rescued > 0) beat("RESCUED " + rescued + " non-text item(s) off legend_bullets in " + d.name);
  } else { L = d.layers.add(); L.name = "legend_bullets"; }

  var drawn = 0, nobul = 0;
  for (var i = 0; i < d.placedItems.length; i++) {
    var it = d.placedItems[i], nm = null;
    try { nm = it.file.name; } catch (eF) { continue; }
    var pid = nm.replace(/\.(pdf|png)$/i, "");
    var ent = PS[pid];
    if (!ent || !ent.legend_bullets || !ent.legend_bullets.length) { nobul++; continue; }
    var b = ent.legend_bullets;
    var vb = it.visibleBounds;              // [left, top, right, bottom]
    var figW = vb[2] - vb[0];
    // WIDTH IS TIED TO THE FIGURE, NOT A FIXED NUMBER. supplemental.ai carries 107 figures on ONE
    // 4940pt board (~400pt each), so a fixed 900pt bullet would run straight across its neighbours.
    // Scale the type down with the figure too, with a floor so it stays legible.
    var wcap = Math.min(MAXW, figW);
    var fs = Math.max(5.5, Math.min(FS, figW / 78));
    var lead = fs * 1.28;
    var x = vb[0], y = vb[3] - fs * 0.7;     // just under the figure
    for (var j = 0; j < b.length; j++) {
      var t = L.textFrames.add();
      t.contents = "• " + b[j];
      try {
        t.textRange.characterAttributes.size = fs;
        t.textRange.characterAttributes.fillColor = (function () {
          var c = new RGBColor(); c.red = 40; c.green = 40; c.blue = 40; return c;
        })();
      } catch (eA) {}
      try { if (t.width > wcap) { var s = wcap / t.width; t.width = t.width * s; t.height = t.height * s; } } catch (eW) {}
      t.left = x; t.top = y;
      y -= lead;
      drawn++;
    }
  }
  var opts = new IllustratorSaveOptions(); opts.pdfCompatible = false;
  var mode = "saved";
  try { d.saveAs(new File(docPath), opts); } catch (eS) { mode = "SAVE_FAILED " + eS; }
  beat("bullets " + d.name + " drawn=" + drawn + " figuresWithoutBullets=" + nobul + " " + mode);
  report.push(d.name + " :: bulletLines=" + drawn + " figuresWithoutBullets=" + nobul + " save=" + mode);
  try { d.close(SaveOptions.DONOTSAVECHANGES); } catch (eC) {}
}
beat("BULLETS done");
var rf = new File("/Volumes/4 MB/_claude_tmp/bullets_report_20260808.txt");
rf.open("w"); rf.write(report.join("\n")); rf.close();
report.join("\n");
