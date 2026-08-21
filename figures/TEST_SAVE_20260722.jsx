#target illustrator
// Can Illustrator save ANYTHING to /Volumes/4 MB right now? Isolates volume/space from document size.
var out = [];
var t = app.documents.add();
t.pathItems.rectangle(100, 100, 200, 200);
var so = new IllustratorSaveOptions(); so.pdfCompatible = true;
try { t.saveAs(new File("/Volumes/4 MB/ablation_plots/_tmp_savetest.ai", so)); out.push("small doc + pdfCompatible: OK"); }
catch (e) { out.push("small doc + pdfCompatible: FAILED " + e); }
try { var so2 = new IllustratorSaveOptions(); so2.pdfCompatible = false;
      t.saveAs(new File("/Volumes/4 MB/ablation_plots/_tmp_savetest2.ai"), so2); out.push("small doc, no pdfCompat: OK"); }
catch (e) { out.push("small doc, no pdfCompat: FAILED " + e); }
t.close(SaveOptions.DONOTSAVECHANGES);
out.join("\n");
