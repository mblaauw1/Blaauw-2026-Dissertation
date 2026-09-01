// Replace the EMBEDDED swimmer raster on artboard 5 with the LINKED figure, so it updates like everything
// else on the deck. Identified by exporting it and looking: it is G4_sisbehav_swimmer ("cells sorted by
// metaphase duration (N=66)"), NOT a timestrip — which is why nothing I re-rendered ever changed it.
//
// SAFE BY CONSTRUCTION: the new placement takes the embedded item's OWN bounds, so the figure does not move
// or resize; only the source changes from embedded pixels to a live link. The embedded original is not
// deleted — it is moved onto a layer named `embedded_originals_20260817` and hidden, so nothing of hers is
// destroyed and the swap is reversible.
#target illustrator

var AIP = "/Volumes/4 MB/1_DECKS/META_FIGURES_20260814.ai";
var PDF = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/G4_sisbehav_swimmer.pdf";
var HB  = new File("/Volumes/4 MB/_claude_tmp/relink_emb.txt");
function beat(m){ try{ HB.open("a"); HB.writeln(m); HB.close(); }catch(e){} }

app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
var doc = app.open(new File(AIP));
var src = new File(PDF);
if (!src.exists) { beat("MISSING " + PDF); }

var keep;
try { keep = doc.layers.getByName("embedded_originals_20260817"); }
catch (e) { keep = doc.layers.add(); keep.name = "embedded_originals_20260817"; }

var done = 0;
for (var i = doc.rasterItems.length - 1; i >= 0; i--) {
  var ri = doc.rasterItems[i], lay = "";
  try { lay = ri.layer.name; } catch (e) { continue; }
  if (lay === "legend_bullets" || lay === "embedded_originals_20260817") continue;
  var b = ri.visibleBounds;
  var w = b[2] - b[0], h = b[1] - b[3];
  // the artboard-5 swimmer: 2012 x 2003 pt at (-2015, -27)
  if (Math.abs(w - 2012) > 6 || Math.abs(h - 2003) > 6) continue;

  var it = doc.layers[0].placedItems.add();
  it.file = src;
  var s = Math.min(w / it.width, h / it.height);   // uniform, never distorts
  it.width = it.width * s; it.height = it.height * s;
  it.left = b[0] + (w - it.width) / 2.0;
  it.top  = b[1] - (h - it.height) / 2.0;

  ri.move(keep, ElementPlacement.PLACEATEND);      // keep the original, do not delete it
  ri.hidden = true;
  done++;
  beat("relinked swimmer at " + b[0].toFixed(0) + "," + b[1].toFixed(0));
}
keep.visible = false;

doc.save();
doc.close(SaveOptions.SAVECHANGES);
app.userInteractionLevel = UserInteractionLevel.DISPLAYALERTS;
beat("DONE relinked=" + done);
"relinked=" + done;
