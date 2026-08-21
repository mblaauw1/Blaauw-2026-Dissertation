// Place ONE figure into NEW_FIGURES_20260804.ai, named by PLACE_ONE_TARGET.txt.
// One figure per invocation: three batch runs hung part-way with no diagnosable cause, and a per-figure
// run means a hang costs one figure and identifies exactly which. Appends a new artboard to the right of
// the rightmost existing one; nothing already on the board is touched. Skips if already present.
app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
var L = new File("/Volumes/4 MB/ablation_plots/PLACE_ONE_LOG.txt"); L.open("w");
function s(x){ L.writeln(x); L.close(); L.open("e"); L.seek(0,2); }
var T = new File("/Volumes/4 MB/ablation_plots/PLACE_ONE_TARGET.txt");
T.open("r"); var spec = T.read().replace(/[\r\n]+$/, ""); T.close();
var bits = spec.split("|"), figName = bits[0], path = bits[1];
var pf = new File(path);
if (!pf.exists) { s("NO FILE: " + path); s("DONE"); L.close(); }
else {
    var f = new File("/Volumes/4 MB/1_DECKS/NEW_FIGURES_20260804.ai");
    var doc = app.open(f);
    var have = false;
    for (var i = 0; i < doc.placedItems.length; i++) {
        try { if (doc.placedItems[i].file.name.replace(/\.(pdf|png|svg)$/i,"") === figName) have = true; } catch(e){}
    }
    if (have) { s("already present: " + figName); }
    else {
        var maxRight = -1e9, topY = 0;
        for (var a = 0; a < doc.artboards.length; a++) {
            var r = doc.artboards[a].artboardRect;
            if (r[2] > maxRight) maxRight = r[2];
            if (a === 0) topY = r[1];
        }
        var W = 900, H = 620, GAP = 60, x = maxRight + 180;
        var ab = doc.artboards.add([x, topY, x + W, topY - H]);
        ab.name = figName.substring(0, 60);
        var pi = doc.placedItems.add();
        pi.file = pf;
        var sc = Math.min((W - 2*GAP) / pi.width, (H - 2*GAP) / pi.height);
        pi.width *= sc; pi.height *= sc;
        pi.left = x + (W - pi.width) / 2;
        pi.top  = topY - (H - pi.height) / 2;
        var o = new IllustratorSaveOptions(); o.pdfCompatible = false;
        doc.saveAs(f, o);
        s("placed " + figName + " on artboard " + doc.artboards.length);
    }
    doc.close(SaveOptions.DONOTSAVECHANGES);
    s("DONE");
    L.close();
}
