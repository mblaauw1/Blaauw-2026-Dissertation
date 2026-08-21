#target illustrator
// Isolated, non-destructive: place each frap_candidates PNG into a THROWAWAY document and report which
// ones Illustrator can actually read. Does not touch copy.ai.
var files = ["/Volumes/4 MB/ablation_figures_20260625/group1/frap_timestrips/frap_candidates.png",
             "/Volumes/4 MB/ablation_figures_20260625/group1/frap_timestrips/frap_candidates_2.png",
             "/Volumes/4 MB/ablation_figures_20260625/group1/frap_timestrips/frap_candidates_3.png",
             "/Volumes/4 MB/ablation_figures_20260625/group4/G4_frap.png"];
var out = [];
var t = app.documents.add();
for (var i = 0; i < files.length; i++) {
  var f = new File(files[i]);
  var nm = decodeURI(f.name);
  if (!f.exists) { out.push(nm + ": NOT_FOUND"); continue; }
  try {
    var p = t.placedItems.add();
    p.file = f;
    out.push(nm + ": OK  " + Math.round(p.width) + "x" + Math.round(p.height));
  } catch (e) {
    out.push(nm + ": FAILED  " + e);
  }
}
t.close(SaveOptions.DONOTSAVECHANGES);
out.join("\n");
