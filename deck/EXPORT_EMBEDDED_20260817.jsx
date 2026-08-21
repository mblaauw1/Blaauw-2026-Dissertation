// Export the three VISIBLE embedded rasters so each can be identified against the figure library.
// An embedded raster has no link, so its identity is only recoverable from its PIXELS.
//
// The earlier attempt at this duplicated each item into a fixed-size document and exported blank white;
// the fix (kept here) is to fit a TEMPORARY artboard to the item's OWN visibleBounds before exporting.
// READ-ONLY on the real file: the temp docs are closed without saving and the deck is closed with
// DONOTSAVECHANGES.
#target illustrator

var AIP = "/Volumes/4 MB/1_DECKS/META_FIGURES_20260814.ai";
var HB  = new File("/Volumes/4 MB/_claude_tmp/emb_export.txt");
function beat(m){ try{ HB.open("a"); HB.writeln(m); HB.close(); }catch(e){} }

app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
var doc = app.open(new File(AIP));

// the three targets, by size+position from DUMP_0814_FULL (AB5 legend_bullets, AB9 figures x2)
var WANT = [
  { tag: "ab5_1388x402",  w: 1388, h: 402 },
  { tag: "ab9_1043x702",  w: 1043, h: 702 },
  { tag: "ab9_1043x758",  w: 1043, h: 758 }
];

// 2026-08-17: RECURSIVE. `doc.rasterItems` does NOT descend into GroupItems, so the AB5 raster (nested in
// a group on legend_bullets) was invisible to the first pass -- the same non-recursion trap that hid art
// from an earlier dump. Collect by walking every container.
var ALL = [];
function collect(c){
  for (var q = 0; q < c.pageItems.length; q++){
    var it = c.pageItems[q];
    if (it.typename === "GroupItem") { collect(it); continue; }
    if (it.typename === "RasterItem") ALL.push(it);
  }
}
for (var Li = 0; Li < doc.layers.length; Li++) collect(doc.layers[Li]);
beat("recursive raster count=" + ALL.length);

var n = 0;
for (var i = 0; i < ALL.length; i++) {
  var ri = ALL[i], lay = "";
  try { lay = ri.layer.name; } catch (e) { continue; }
  if (lay === "embedded_originals_20260817") continue;      // already-archived originals: not these
  var b = ri.visibleBounds;
  var w = b[2] - b[0], h = b[1] - b[3];
  // 2026-08-17: export EVERY non-archived raster rather than size-matching. The AB5 item missed its filter
  // because the artboard scale-to-95% pass had already shrunk it (1388x402 -> ~1319x382) — a size literal
  // taken from a dump goes stale the moment anything is rescaled. Name by measured size instead.
  var tag = "r" + Math.round(w) + "x" + Math.round(h);

  var nd = app.documents.add(DocumentColorSpace.RGB, w, h);
  var cp = ri.duplicate(nd.layers[0], ElementPlacement.PLACEATEND);
  var ar = nd.artboards[0].artboardRect;                     // new doc: artboard origin at top-left
  cp.left = ar[0]; cp.top = ar[1];
  var ef = new ExportOptionsPNG24();
  ef.artBoardClipping = true; ef.horizontalScale = 40; ef.verticalScale = 40;
  nd.exportFile(new File("/Volumes/4 MB/_claude_tmp/emb_" + tag + ".png"), ExportType.PNG24, ef);
  nd.close(SaveOptions.DONOTSAVECHANGES);
  beat("exported " + tag + "  layer=" + lay + "  at " + b[0].toFixed(0) + "," + b[1].toFixed(0));
  n++;
}

doc.close(SaveOptions.DONOTSAVECHANGES);
app.userInteractionLevel = UserInteractionLevel.DISPLAYALERTS;
beat("DONE exported=" + n);
"exported=" + n;
