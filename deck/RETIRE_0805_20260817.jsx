// Move the last figures off META_FIGURES_20260805.ai so it can be retired.
//
// USER 2026-08-17: "can you just place the figures remaining on meta_figures on another of our working
// docs so that meta_figures can be retired and its one less doc we have to worry about"
//
// DESTINATION: artboard 4 of NEW_FIGURES_20260804.ai — measured EMPTY (0 figures, 0% fill, 3720 x 2820 pt).
// That honours her standing rule for the other direction too: nothing already on the deck has to be scaled
// down to make room, and no NEW artboard is created ("this messes up sorting and can get confusing").
//
// HOW: cross-document `duplicate()`, NOT a relink. Two of the eleven are EMBEDDED rasters with no link —
// re-placing a file could not carry them, and an embedded raster cannot be refreshed by re-rendering, so it
// has to travel as an object. The originals stay on 0805, which is being retired wholesale, so nothing is
// destroyed at any point.
#target illustrator

var SRC = "/Volumes/4 MB/ablation_plots/META_FIGURES_20260805.ai";
var DST = "/Volumes/4 MB/1_DECKS/NEW_FIGURES_20260804.ai";
var TMP = "/Volumes/4 MB/_claude_tmp";
var HB  = new File(TMP + "/retire0805_heartbeat.txt");
function beat(m) { try { HB.open("a"); HB.writeln(m); HB.close(); } catch (e) {} }

var AB = 4;            // 1-based artboard on the destination
var NCOL = 4, NROW = 3, PAD = 30;

app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
beat("START");
var report = [];
var i;

var dst = app.open(new File(DST));
beat("opened dst " + dst.name);
var lockState = [];
for (i = 0; i < dst.layers.length; i++) {
  var Ly = dst.layers[i]; var st = { lay: Ly, lk: false };
  try { st.lk = Ly.locked; Ly.locked = false; } catch (e) {}
  lockState.push(st);
}
var LAYNAME = "from_META_FIGURES_20260805";
var lay = null;
for (i = 0; i < dst.layers.length; i++) if (dst.layers[i].name === LAYNAME) lay = dst.layers[i];
if (lay === null) { lay = dst.layers.add(); lay.name = LAYNAME; }
try { lay.locked = false; lay.visible = true; dst.activeLayer = lay; } catch (e) {}

var R = dst.artboards[AB - 1].artboardRect;      // [L,T,R,B]
var CW = (R[2] - R[0]) / NCOL, CH = (R[1] - R[3]) / NROW;
beat("dst artboard " + AB + " " + (R[2] - R[0]) + "x" + (R[1] - R[3]) + " cell " + CW + "x" + CH);

var src = app.open(new File(SRC));
beat("opened src " + src.name);

// collect the figures FIRST: duplicating while iterating the source collection is not safe
var take = [];
for (i = 0; i < src.pageItems.length; i++) {
  var it = src.pageItems[i];
  if (it.typename !== "PlacedItem" && it.typename !== "RasterItem") continue;
  try { if (it.parent.typename !== "Layer") continue; } catch (e) { continue; }
  try { if (it.hidden) continue; } catch (e) {}
  var nm = "";
  try { if (it.typename === "PlacedItem" && it.file) nm = it.file.name.replace(/\.(pdf|png|ai|eps)$/i, ""); } catch (e) {}
  if (!nm) nm = "(embedded " + it.typename + ")";
  take.push({ it: it, name: nm });
}
beat("found " + take.length + " figures on the source");

var placed = 0;
for (i = 0; i < take.length; i++) {
  var cc = i % NCOL, rr = Math.floor(i / NCOL);
  if (rr >= NROW) { report.push("NO ROOM\t" + take[i].name); continue; }
  var cx = R[0] + cc * CW + CW / 2;
  var cy = R[1] - rr * CH - CH / 2;
  try {
    var dup = take[i].it.duplicate(lay, ElementPlacement.PLACEATEND);
    var avail_w = CW - 2 * PAD, avail_h = CH - 2 * PAD;
    var sc = Math.min(avail_w / dup.width, avail_h / dup.height);
    if (sc > 0 && sc !== 1) dup.resize(sc * 100, sc * 100);   // UNIFORM: never distort her figures
    dup.left = cx - dup.width / 2;
    dup.top  = cy + dup.height / 2;
    try { dup.name = take[i].name; } catch (e) {}
    placed++;
    report.push("MOVED\t" + take[i].name);
  } catch (e) {
    report.push("FAILED\t" + take[i].name + "\t" + e);
  }
  beat("placed " + placed + "/" + take.length);
}

src.close(SaveOptions.DONOTSAVECHANGES);          // source untouched; the whole file is being retired
for (i = 0; i < lockState.length; i++) { try { lockState[i].lay.locked = lockState[i].lk; } catch (e) {} }
try { dst.selection = null; } catch (e) {}
var opts = new IllustratorSaveOptions();
opts.compatibility = Compatibility.ILLUSTRATOR17;
opts.pdfCompatible = false;
dst.saveAs(new File(DST), opts);
dst.close(SaveOptions.SAVECHANGES);
beat("saved dst");

var rf = new File(TMP + "/retire0805_report.txt"); rf.encoding = "UTF-8"; rf.open("w");
rf.writeln("placed\t" + placed + " of " + take.length);
for (i = 0; i < report.length; i++) rf.writeln(report[i]);
rf.close();
app.userInteractionLevel = UserInteractionLevel.DISPLAYALERTS;
beat("ALLDONE placed=" + placed);
"placed=" + placed + " of " + take.length;
