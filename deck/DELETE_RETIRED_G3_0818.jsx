// Remove the RETIRED figure `G3_ablation_location_vs_behavior` from her four hand-arranged paper files.
// 2026-08-18, on her instruction: "Relink them to the two successors, and if these successors are already
// included on a current ai file, then delete these old no longer relevant versions."
// The condition is met and was checked before running: BOTH successors — G3_ablation_location_vs_platefate
// and G3_ablation_location_vs_recongression — are already placed on `supplemental.ai` (4 placements each),
// so the old link is deleted rather than relinked. The builder was split on 2026-08-03 and the old PDF no
// longer exists, so these placements were broken links showing a stale preview.
// Every file was copied to *.bak_pre_g3delete_20260818 BEFORE this ran.
// Traps honoured: no var named `path`/`open`/`L`; doc name captured BEFORE close; alerts suppressed; heartbeat.
#target illustrator

var FILES = [
  "/Volumes/4 MB/1_DECKS/arranged_into_paper_figures.ai",
  "/Volumes/4 MB/1_DECKS/arranged_into_paper_figures_2.ai",
  "/Volumes/4 MB/1_DECKS/arranged_into_paper_figures_2 computer.ai",
  "/Volumes/4 MB/1_DECKS/figure 6.ai"
];
var TARGET = "G3_ablation_location_vs_behavior";
var HB = new File("/Volumes/4 MB/_claude_tmp/g3delete_heartbeat.txt");
function beat(m){ try{ HB.open("a"); HB.writeln(m); HB.close(); }catch(e){} }

app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
var report = [];
for (var k = 0; k < FILES.length; k++) {
  var fileRef = new File(FILES[k]);
  if (!fileRef.exists) { beat("MISSING " + FILES[k]); continue; }
  beat("open " + FILES[k]);
  var doc = app.open(fileRef);
  var docName = doc.name;
  var removed = 0, kept = 0;
  for (var i = doc.placedItems.length - 1; i >= 0; i--) {
    var pi = doc.placedItems[i];
    var base = "";
    try { base = pi.file.name.replace(/\.(pdf|png|ai|eps)$/i, ""); } catch (e) { kept++; continue; }
    if (base === TARGET) {
      try { pi.remove(); removed++; beat("  removed a " + TARGET + " placement"); }
      catch (e) { beat("  FAILED remove :: " + e); }
    } else { kept++; }
  }
  if (removed > 0) { beat("saving " + docName); doc.save(); doc.close(SaveOptions.SAVECHANGES); }
  else { beat("nothing to remove in " + docName); doc.close(SaveOptions.DONOTSAVECHANGES); }
  report.push(docName + ": removed " + removed + ", kept " + kept);
}
app.userInteractionLevel = UserInteractionLevel.DISPLAYALERTS;
beat("ALLDONE " + report.join(" | "));
report.join(" | ");
