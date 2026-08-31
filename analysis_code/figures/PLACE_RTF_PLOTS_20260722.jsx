#target illustrator
// Place the 5 "plots that should exist" figures into `ablation_figures_grouped copy.ai`, each one
// directly BELOW its thematic neighbour rather than in a generic staging grid, so they land in the
// right topic block. Linked (not embedded), so lib.savefig refreshes them automatically.
// USER PREF: never let an Illustrator dialog steal focus.
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}

var COPY = "/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
var PDF  = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/";

// new figure  ->  the already-placed figure it belongs next to
var JOBS = [
  {"base": "G4_oscillation_vs_plate_distance.pdf",           "anchor": "G4_velocity_vs_distance"},
  {"base": "G4_oscillation_vs_time_to_event.pdf",            "anchor": "G4_oscillation.pdf"},
  {"base": "G4_polar_position_vs_time_to_anaphase.pdf",      "anchor": "G4_plate_distance_time.pdf"},
  {"base": "G3_length_vs_precongression_plate_distance.pdf", "anchor": "G3_length_vs_mitotic_time"},
  {"base": "G3_position_along_plate_normal_vs_behavior.pdf", "anchor": "G3_ablation_location_vs_behavior"}
];

for (var q = 0; q < app.documents.length; q++) {
  if (app.documents[q].fullName && app.documents[q].fullName.fsName == COPY) {
    throw new Error("ABORT: 'grouped copy.ai' is open — save + close it first.");
  }
}

var d = app.open(new File(COPY));
var lyr = d.activeLayer;

// index every linked placement by its file basename (lowercased)
function linkName(pi) { var f = null; try { f = pi.file; } catch (e) {} return f ? decodeURI(f.name).toLowerCase() : ""; }
var have = {}, anchorItem = {};
for (var i = 0; i < d.placedItems.length; i++) {
  var n = linkName(d.placedItems[i]);
  if (!n) continue;
  have[n] = true;
  // keep the FIRST placement of each basename as the anchor (duplicates are her paper-figure copies)
  if (!anchorItem[n]) anchorItem[n] = d.placedItems[i];
}

function findAnchor(a) {
  var key = a.toLowerCase();
  if (anchorItem[key]) return anchorItem[key];
  if (anchorItem[key + ".pdf"]) return anchorItem[key + ".pdf"];
  for (var k in anchorItem) { if (k.indexOf(key) === 0) return anchorItem[k]; }
  return null;
}

var added = 0, skipped = [], noanchor = [], missing = [];
for (var j = 0; j < JOBS.length; j++) {
  var base = JOBS[j].base;
  if (have[base.toLowerCase()]) { skipped.push(base); continue; }   // never duplicate
  var file = new File(PDF + base);
  if (!file.exists) { missing.push(base); continue; }
  var an = findAnchor(JOBS[j].anchor);
  if (!an) { noanchor.push(base); continue; }
  var ab = an.visibleBounds;                     // [left, top, right, bottom]
  try {
    var pi = lyr.placedItems.add(); pi.file = file;
    var targetW = ab[2] - ab[0];                 // match the anchor's width so the block stays tidy
    var sc = targetW / pi.width;
    pi.width = pi.width * sc; pi.height = pi.height * sc;
    pi.position = [ab[0], ab[3] - 30];           // directly beneath the anchor
    pi.name = "NEW " + base;
    var tf = lyr.textFrames.add();
    tf.contents = base.replace(/\.pdf$/i, "") + "   [data: manual annotations]";
    tf.textRange.characterAttributes.size = 11;
    tf.position = [ab[0], ab[3] - 14];
    added++;
  } catch (e) { missing.push(base + " [ERR " + e + "]"); }
}

var so = new IllustratorSaveOptions(); so.pdfCompatible = true;   // match how SYNC_GROUPED_COPY.jsx saves this same file
d.saveAs(new File(COPY), so);
d.close(SaveOptions.DONOTSAVECHANGES);
"added=" + added + " skipped_already_present=" + skipped.length +
  " no_anchor=" + noanchor.length + " missing=" + missing.length +
  (noanchor.length ? (" :: NOANCHOR " + noanchor.join(" | ")) : "") +
  (missing.length ? (" :: MISSING " + missing.join(" | ")) : "");
