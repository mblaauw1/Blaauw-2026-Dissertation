// ARTBOARDS-ONLY PASS, 2026-08-18. Her instruction: "extend/add artboards over where the figures already are."
// Every rect below is the bounding box of a CLUSTER of figures that currently sits outside every artboard,
// plus a 60 pt margin, computed from the read-only geometry dump. NOTHING IS MOVED, SCALED OR RELINKED here:
// artboard operations get their own save pass (NOTES 2026-08-10 — mixing them lost a whole placement run).
// Rects are clamped to the artboard-legal canvas x/y in [-7475, 8750]; figures beyond that cannot be covered
// by any artboard and are reported separately rather than moved.
// Traps honoured: no var named `path`/`open`/`L`; doc name captured BEFORE close; alerts suppressed; heartbeat.
#target illustrator

var HB = new File("/Volumes/4 MB/_claude_tmp/artboards_heartbeat.txt");
function beat(m){ try{ HB.open("a"); HB.writeln(m); HB.close(); }catch(e){} }

// [file, left, top, right, bottom, n_figures_covered]
var RECTS = [
  ["META_FIGURES_20260814.ai", 1327.7, -113.7, 3583.3, -2049.0, 2],
  ["META_FIGURES_20260814.ai", 1742.2, 3936.1, 2404.0, 3083.9, 1],
  ["META_FIGURES_20260814.ai", -7119.7, 4439.7, -5217.0, 3134.8, 1],
  ["META_FIGURES_20260814.ai", 7372.3, -5461.7, 8535.6, -6339.6, 1],
  ["NEW_FIGURES_20260804.ai", -5350.6, 8080.1, 6889.2, -308.9, 61],
  ["NEW_FIGURES_20260804.ai", -6028.4, -1805.5, 416.6, -5850.4, 14],
  ["NEW_FIGURES_20260804.ai", 2340.0, -5910.0, 5260.0, -7475, 3],
  ["supplemental.ai", -7435.7, -1045.4, -1462.3, -7474.1, 53],
  ["supplemental.ai", 5118.6, -675.2, 7559.4, -2447.2, 12],
  ["supplemental.ai", -59.7, -5349.3, 3361.7, -7122.0, 9],
  ["supplemental.ai", -1528.3, -2352.4, -333.3, -3671.5, 4],
  ["supplemental.ai", 5002.5, -5863.2, 6159.1, -6125.5, 2],
  ["supplemental.ai", 5220.5, -3578.5, 6403.7, -4334.2, 1],
  ["NEW_TIMESTRIPS_20260804.ai", -1603.2, -1771.1, -373.2, -2428.9, 1],
  ["NEW_TIMESTRIPS_20260804.ai", -1541.0, -3713.0, -311.0, -4524.6, 1],
  ["META_FIGURES_20260814_PUBLICATION.ai", 1327.7, -113.7, 3583.3, -2775.7, 2],
  ["META_FIGURES_20260814_PUBLICATION.ai", 1742.2, 3936.1, 2404.0, 3083.9, 1],
  ["META_FIGURES_20260814_PUBLICATION.ai", -7119.7, 4439.7, -5217.0, 3134.8, 1],
  ["META_FIGURES_20260814_PUBLICATION.ai", 7372.3, -5461.7, 8535.6, -6339.6, 1],
  ["META_FIGURES_20260813_supplemental_PUBLICATION.ai", 57.0, 4156.9, 1799.9, 2769.0, 1],
  ["META_FIGURES_20260813_supplemental_PUBLICATION.ai", -1309.8, -1615.0, -732.1, -2713.8, 1],
];

app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
var byDoc = {};
for (var i = 0; i < RECTS.length; i++) {
  var fnm = RECTS[i][0];
  if (!byDoc[fnm]) byDoc[fnm] = [];
  byDoc[fnm].push(RECTS[i]);
}
var report = [];
for (var fnm in byDoc) {
  var aiPath = "/Volumes/4 MB/1_DECKS/" + fnm;
  var fileRef = new File(aiPath);
  if (!fileRef.exists) { beat("MISSING " + fnm); continue; }
  beat("open " + fnm);
  var doc = app.open(fileRef);
  var docName = doc.name;
  var before = doc.artboards.length, added = 0;
  var specs = byDoc[fnm];
  for (var j = 0; j < specs.length; j++) {
    try {
      var ab = doc.artboards.add([specs[j][1], specs[j][2], specs[j][3], specs[j][4]]);
      ab.name = "auto 2026-08-18 (" + (j + 1) + ")";
      added++;
      beat("  added " + ab.name + " covering " + specs[j][5] + " figures");
    } catch (e) { beat("  FAILED rect " + j + " :: " + e); }
  }
  beat("saving " + docName);
  doc.save();
  doc.close(SaveOptions.SAVECHANGES);
  report.push(docName + ": " + before + " -> " + (before + added) + " artboards");
  beat("done " + docName);
}
app.userInteractionLevel = UserInteractionLevel.DISPLAYALERTS;
beat("ALLDONE " + report.join(" | "));
report.join(" | ");
