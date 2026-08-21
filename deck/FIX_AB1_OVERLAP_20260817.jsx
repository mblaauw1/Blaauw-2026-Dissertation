// Artboard 1 of META_FIGURES_20260814.ai — two fixes, both mine to make and both reversible.
//
// (1) THE NEW HEC1 STRIP WAS COVERING FOUR OF THE SPLIT PIECES.
//     `G5_item4_hec1_timestrip_xy5.pdf` was swapped in at the OLD embedded raster's top-left, but the new
//     strip is 1205 pt tall against the old 872 (it gained the phase row she asked for), so it grew
//     DOWNWARD over `nf9_3-sisterless__...ablation_18__piece1..4` — covering one of them 100%. That is
//     exactly the failure she described: "an older version is hiding it" so the fix looks undone.
//     I move the PIECES, not the strip: the strip sits where her original artwork sat (her layout), while
//     the pieces are art I added for §9f item [12] and she has not arranged them yet. All SEVEN move by the
//     same delta so their relative arrangement is preserved.
//
// (2) THE DEAD EMBEDDED HEC1 RASTER IS STILL UNDERNEATH.
//     A 1306x872 embedded RasterItem sits at the identical top-left as the new linked strip. It is
//     invisible today only because the new one covers it; move the strip and it reappears. Archived to the
//     hidden `embedded_originals_20260817` layer — the same reversible pattern used for the swimmer swap —
//     NOT deleted.
#target illustrator

var AIP = "/Volumes/4 MB/1_DECKS/META_FIGURES_20260814.ai";
var HB  = new File("/Volumes/4 MB/_claude_tmp/fix_ab1.txt");
function beat(m){ try{ HB.open("a"); HB.writeln(m); HB.close(); }catch(e){} }

var DX = -2342.0, DY = -366.0;          // from the occupancy-grid free-block scan

app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
var doc = app.open(new File(AIP));
beat("opened");

// ---- (1) shift the seven pieces -------------------------------------------------------------------
var moved = 0;
for (var i = 0; i < doc.placedItems.length; i++) {
  var it = doc.placedItems[i], f = "";
  try { f = it.file ? it.file.name : ""; } catch (e) { continue; }
  if (f.indexOf("nf9_3-sisterless__20260417_ptk2_eyfp_cdc20_ablation_18__piece") !== 0) continue;
  var b = it.visibleBounds;
  it.left = b[0] + DX;
  it.top  = b[1] + DY;
  moved++;
  beat("moved " + f + " -> " + it.left.toFixed(0) + "," + it.top.toFixed(0));
}

// ---- (2) archive the dead embedded hec1 raster ------------------------------------------------------
var keep;
try { keep = doc.layers.getByName("embedded_originals_20260817"); }
catch (e) { keep = doc.layers.add(); keep.name = "embedded_originals_20260817"; }

var archived = 0;
for (var r = doc.rasterItems.length - 1; r >= 0; r--) {
  var ri = doc.rasterItems[r], lay = "";
  try { lay = ri.layer.name; } catch (e) { continue; }
  if (lay === "embedded_originals_20260817") continue;
  var bb = ri.visibleBounds;
  var w = bb[2] - bb[0], h = bb[1] - bb[3];
  // the AB1 hec1 original: 1306 x 872 at (-4724, 8101). Bound-matched so the AB5/AB9 embedded rasters,
  // which are a separate question, are left completely alone.
  if (Math.abs(w - 1306) > 6 || Math.abs(h - 872) > 6) continue;
  if (Math.abs(bb[0] - (-4724)) > 8 || Math.abs(bb[1] - 8101) > 8) continue;
  ri.move(keep, ElementPlacement.PLACEATEND);
  ri.hidden = true;
  archived++;
  beat("archived embedded hec1 " + w.toFixed(0) + "x" + h.toFixed(0));
}
keep.visible = false;

doc.save();
doc.close(SaveOptions.SAVECHANGES);
app.userInteractionLevel = UserInteractionLevel.DISPLAYALERTS;
beat("DONE moved=" + moved + " archived=" + archived);
"moved=" + moved + " archived=" + archived;
