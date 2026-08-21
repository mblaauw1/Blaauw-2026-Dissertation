// Minimal probe: can a single PDF be placed into NEW_FIGURES at all?
// The full script reports "placed=31, failed=0" while doc.pageItems.length never grows, which is
// self-contradictory -- so this isolates ONE placement and reports the count at each step.
// Read-only: closes without saving no matter what.

#target illustrator

var AI  = "/Volumes/4 MB/1_DECKS/NEW_FIGURES_20260804.ai";
var PDF = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/kk_osc_amplitude.pdf";
var out = [];

var doc = app.open(new File(AI));
app.activeDocument = doc;
out.push("opened: " + doc.name);
out.push("docs open now = " + app.documents.length);
out.push("pageItems BEFORE   = " + doc.pageItems.length);
out.push("placedItems BEFORE = " + doc.placedItems.length);
out.push("active layer = " + doc.activeLayer.name + "  locked=" + doc.activeLayer.locked + "  visible=" + doc.activeLayer.visible);

var f = new File(PDF);
out.push("pdf exists = " + f.exists + "  (" + PDF + ")");

try {
    var it = doc.placedItems.add();
    out.push("after add(): pageItems = " + doc.pageItems.length + "  placedItems = " + doc.placedItems.length);
    out.push("  it.typename = " + it.typename);
    it.file = f;
    out.push("  after it.file: w=" + it.width.toFixed(1) + " h=" + it.height.toFixed(1));
    out.push("  it.layer = " + it.layer.name);
    it.position = [0, -7000];
    out.push("after position: pageItems = " + doc.pageItems.length + "  placedItems = " + doc.placedItems.length);
    out.push("  it.visibleBounds = " + it.visibleBounds.join(", "));
} catch (e) {
    out.push("EXCEPTION: " + e);
}

out.push("FINAL pageItems = " + doc.pageItems.length + "  placedItems = " + doc.placedItems.length);
doc.close(SaveOptions.DONOTSAVECHANGES);

var lf = new File("/tmp/nf_probe.txt");
lf.open("w"); lf.write(out.join("\n")); lf.close();
out.join("\n");
