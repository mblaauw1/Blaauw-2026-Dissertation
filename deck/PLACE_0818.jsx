// ONE consolidated placement pass for the 2026-08-18 to-do list.
// Targets were solved in Python against the verified dump and are written here as LITERALS --
// this script does no geometry of its own.
//
// TRAPS AVOIDED (NOTES §8/§14):
//   - a JSX that errored earlier leaves a stale DIRTY document open, and the next app.open() silently
//     returns THAT copy -> close everything first.
//   - modal on open (links/fonts/profile) presents as a hang at ~1.2% CPU -> DONTDISPLAYALERTS first.
//   - `path` is RESERVED in ExtendScript -> aiPath.
//   - doc.layers[0] is not necessarily a usable layer, and layers.add() inserts at index 0 -> get the
//     target layer BY NAME, and never add art while activeLayer is hidden (Error 8705).
//   - never doc.save(); saveAs with pdfCompatible=false.
//   - capture doc.name BEFORE close (Error 45).
#target illustrator
app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }

var HB = new File("/Volumes/4 MB/_claude_tmp/place_heartbeat_20260818.txt");
function beat(m){ try{ HB.open("a"); HB.writeln(m); HB.close(); }catch(e){} }

var AIP = "/Volumes/4 MB/1_DECKS/META_FIGURES_20260814.ai";
var doc = app.open(new File(AIP));
beat("opened " + doc.name);

// a visible, unlocked layer to place onto -- created only if absent, fetched BY NAME
var LAYNAME = "session_20260818";
var lay = null;
for (var i = 0; i < doc.layers.length; i++) if (doc.layers[i].name == LAYNAME) lay = doc.layers[i];
if (lay == null) { lay = doc.layers.add(); lay.name = LAYNAME; }
lay.visible = true; lay.locked = false;
doc.activeLayer = lay;
beat("layer ready");


(function(){
  var f = new File("/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/G8_metaphase_duration_model.pdf");
  if (!f.exists) { beat("MISSING G8_metaphase_duration_model"); return; }
  var pi = lay.placedItems.add();
  pi.file = f;
  pi.name = "G8_metaphase_duration_model";
  var b = pi.geometricBounds;
  var w = b[2]-b[0], h = b[1]-b[3];
  var s = Math.min(1080.0/w, 660.0/h);
  pi.resize(s*100, s*100, true,true,true,true, s*100, Transformation.TOPLEFT);
  b = pi.geometricBounds;
  pi.translate(-7290.0-b[0], -190.0-b[1]);
  beat("placed G8_metaphase_duration_model AB4");
})();

(function(){
  var f = new File("/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/G8_pooling_2plus3_vs_3.pdf");
  if (!f.exists) { beat("MISSING G8_pooling_2plus3_vs_3"); return; }
  var pi = lay.placedItems.add();
  pi.file = f;
  pi.name = "G8_pooling_2plus3_vs_3";
  var b = pi.geometricBounds;
  var w = b[2]-b[0], h = b[1]-b[3];
  var s = Math.min(820.0/w, 460.0/h);
  pi.resize(s*100, s*100, true,true,true,true, s*100, Transformation.TOPLEFT);
  b = pi.geometricBounds;
  pi.translate(-5770.0-b[0], -1530.0-b[1]);
  beat("placed G8_pooling_2plus3_vs_3 AB4");
})();

(function(){
  var f = new File("/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/G8_kt_deformation_materialfits.pdf");
  if (!f.exists) { beat("MISSING G8_kt_deformation_materialfits"); return; }
  var pi = lay.placedItems.add();
  pi.file = f;
  pi.name = "G8_kt_deformation_materialfits";
  var b = pi.geometricBounds;
  var w = b[2]-b[0], h = b[1]-b[3];
  var s = Math.min(1120.0/w, 320.0/h);
  pi.resize(s*100, s*100, true,true,true,true, s*100, Transformation.TOPLEFT);
  b = pi.geometricBounds;
  pi.translate(-1990.0-b[0], -1670.0-b[1]);
  beat("placed G8_kt_deformation_materialfits AB5");
})();

(function(){
  var f = new File("/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/G8_polar_chromosome_angle.pdf");
  if (!f.exists) { beat("MISSING G8_polar_chromosome_angle"); return; }
  var pi = lay.placedItems.add();
  pi.file = f;
  pi.name = "G8_polar_chromosome_angle";
  var b = pi.geometricBounds;
  var w = b[2]-b[0], h = b[1]-b[3];
  var s = Math.min(1120.0/w, 340.0/h);
  pi.resize(s*100, s*100, true,true,true,true, s*100, Transformation.TOPLEFT);
  b = pi.geometricBounds;
  pi.translate(1470.0-b[0], -1650.0-b[1]);
  beat("placed G8_polar_chromosome_angle AB5");
})();

(function(){
  var f = new File("/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/G8_kt_speed_paired_vs_sisterless.pdf");
  if (!f.exists) { beat("MISSING G8_kt_speed_paired_vs_sisterless"); return; }
  var pi = lay.placedItems.add();
  pi.file = f;
  pi.name = "G8_kt_speed_paired_vs_sisterless";
  var b = pi.geometricBounds;
  var w = b[2]-b[0], h = b[1]-b[3];
  var s = Math.min(900.0/w, 360.0/h);
  pi.resize(s*100, s*100, true,true,true,true, s*100, Transformation.TOPLEFT);
  b = pi.geometricBounds;
  pi.translate(3310.0-b[0], -1630.0-b[1]);
  beat("placed G8_kt_speed_paired_vs_sisterless AB6");
})();

(function(){
  var f = new File("/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/G8_lagging_fracture_timing.pdf");
  if (!f.exists) { beat("MISSING G8_lagging_fracture_timing"); return; }
  var pi = lay.placedItems.add();
  pi.file = f;
  pi.name = "G8_lagging_fracture_timing";
  var b = pi.geometricBounds;
  var w = b[2]-b[0], h = b[1]-b[3];
  var s = Math.min(1120.0/w, 340.0/h);
  pi.resize(s*100, s*100, true,true,true,true, s*100, Transformation.TOPLEFT);
  b = pi.geometricBounds;
  pi.translate(-7290.0-b[0], -6950.0-b[1]);
  beat("placed G8_lagging_fracture_timing AB7");
})();

(function(){
  var f = new File("/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/G8_lagging_fracture_materials.pdf");
  if (!f.exists) { beat("MISSING G8_lagging_fracture_materials"); return; }
  var pi = lay.placedItems.add();
  pi.file = f;
  pi.name = "G8_lagging_fracture_materials";
  var b = pi.geometricBounds;
  var w = b[2]-b[0], h = b[1]-b[3];
  var s = Math.min(820.0/w, 320.0/h);
  pi.resize(s*100, s*100, true,true,true,true, s*100, Transformation.TOPLEFT);
  b = pi.geometricBounds;
  pi.translate(-6130.0-b[0], -6970.0-b[1]);
  beat("placed G8_lagging_fracture_materials AB7");
})();

var nm = doc.name;
var opt = new IllustratorSaveOptions();
opt.pdfCompatible = false;
doc.saveAs(new File(AIP), opt);
beat("SAVED " + nm);
doc.close(SaveOptions.DONOTSAVECHANGES);
beat("DONE");
