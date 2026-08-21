#target illustrator
// Give each newly-added figure a caption directly beneath it: number, name, and DATA SOURCE.
// Also removes the orphaned captions left behind when the figures were re-seated onto artboards.
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}

var COPY = "/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
// name -> [display number, data source]
var NEW = {
 "g4_oscillation_vs_plate_distance.pdf":            ["N1",  "manual annotations"],
 "g4_oscillation_vs_time_to_event.pdf":             ["N2",  "manual annotations"],
 "g4_polar_position_vs_time_to_anaphase.pdf":       ["N3",  "manual annotations"],
 "g3_length_vs_precongression_plate_distance.pdf":  ["N4",  "manual annotations"],
 "g3_position_along_plate_normal_vs_behavior.pdf":  ["N5",  "manual annotations"],
 "g3_length_by_behavior_group.pdf":                 ["N6",  "manual annotations"],
 "g3_lagging_vs_congression_balance.pdf":           ["N7",  "manual annotations"],
 "g4_polar_angle_to_plate.pdf":                     ["N8",  "manual annotations"],
 "g1_cell_centroid_movement_by_group.pdf":          ["N9",  "manual annotations"],
 "g3_cell_movement_vs_polar_length_sum.pdf":        ["N10", "manual annotations"],
 "g3_plate_rotation_vs_polar_length.pdf":           ["N11", "manual annotations"],
 "g3_plate_rotation_by_group.pdf":                  ["N12", "manual annotations"],
 "g4_chromosome_flux_vs_metaphase.pdf":             ["N13", "manual annotations"]
};

for (var q = 0; q < app.documents.length; q++) {
  if (app.documents[q].fullName && app.documents[q].fullName.fsName == COPY) throw new Error("ABORT: copy.ai open");
}
var d = app.open(new File(COPY));
var lyr = d.activeLayer;

// 1) drop the stale captions written during the first placement pass
var killed = 0;
for (var i = d.textFrames.length - 1; i >= 0; i--) {
  var c = String(d.textFrames[i].contents);
  for (var k in NEW) {
    var stem = k.replace(/\.pdf$/, "");
    if (c.toLowerCase().indexOf(stem) === 0 && c.indexOf("[data:") >= 0) {
      try { d.textFrames[i].remove(); killed++; } catch (e) {}
      break;
    }
  }
}

// 2) caption each figure where it now sits
var done = [];
for (var i = 0; i < d.placedItems.length; i++) {
  var p = d.placedItems[i], f = null;
  try { f = p.file; } catch (e) {}
  if (!f) continue;
  var n = decodeURI(f.name).toLowerCase();
  if (!NEW[n]) continue;
  var b = p.visibleBounds;
  var tf = lyr.textFrames.add();
  tf.contents = NEW[n][0] + ". " + n.replace(/\.pdf$/, "") + "   [data: " + NEW[n][1] + "]";
  tf.textRange.characterAttributes.size = 10;
  tf.position = [b[0], b[3] - 4];
  done.push(NEW[n][0]);
  delete NEW[n];
}

var so = new IllustratorSaveOptions(); so.pdfCompatible = true;
d.saveAs(new File(COPY), so);
d.close(SaveOptions.DONOTSAVECHANGES);
"captioned=" + done.length + " (" + done.join(",") + ")  stale_removed=" + killed;
