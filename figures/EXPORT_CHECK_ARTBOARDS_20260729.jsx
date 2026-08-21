// Visual check for the 2026-07-29c deck pass: export the two artboards that gained new companions,
// so the result can be LOOKED AT rather than trusted from a count (standing rule: verify plots visually).
//   copy.ai AB22       - the 4 G4_exhaustion_violin_journal_win_* companions
//   overflow OV-AB3    - the 8 G6ph_*_zoom companions
// Read-only: opens, exports PNG, closes WITHOUT saving.
#target illustrator
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var OUT = "/private/tmp/claude-501/-Users-mblaauw/ee38f673-2da8-4cae-858d-785e29a66194/scratchpad/";
var JOBS = [["/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai", 22, "check_AB22.png"],
            ["/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_kinetochore_overflow.ai", 3, "check_OVAB3.png"]];
var report = [];
for (var k = 0; k < JOBS.length; k++) {
  var d = app.open(new File(JOBS[k][0]));
  var idx = JOBS[k][1] - 1;
  var note;
  if (idx < 0 || idx >= d.artboards.length) {
    note = "artboard " + JOBS[k][1] + " out of range (" + d.artboards.length + ")";
  } else {
    d.artboards.setActiveArtboardIndex(idx);
    var o = new ExportOptionsPNG24();
    o.artBoardClipping = true;
    o.horizontalScale = 40; o.verticalScale = 40;   // artboards are large; 40% keeps the file readable
    try { d.exportFile(new File(OUT + JOBS[k][2]), ExportType.PNG24, o); note = "exported " + JOBS[k][2]; }
    catch (e2) { note = "EXPORT FAILED " + e2; }
  }
  var nm = d.name;
  try { d.close(SaveOptions.DONOTSAVECHANGES); } catch (e3) {}
  report.push(nm + " :: " + note);
}
report.join("\n");
