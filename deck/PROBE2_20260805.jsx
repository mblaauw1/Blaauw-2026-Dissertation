app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
var L = new File("/Volumes/4 MB/ablation_plots/PROBE_LOG.txt"); L.open("w");
function s(x){ L.writeln(x); L.close(); L.open("e"); L.seek(0,2); }
var d = app.open(new File("/Volumes/4 MB/1_DECKS/NEW_FIGURES_20260804.ai"));
s("artboards " + d.artboards.length + "  placed " + d.placedItems.length);
for (var i = 0; i < d.placedItems.length; i++) {
    var p = d.placedItems[i], nm = "?";
    try { nm = p.file.name; } catch(e) {}
    if (nm.indexOf("G6tenM_polar_vs_paired") === 0 || nm.indexOf("G6_polar_distortion") === 0 ||
        nm.indexOf("G6_area_vs_distortion") === 0 || nm.indexOf("G4_oscillation_1v3") === 0) {
        s("  " + nm + "  left=" + Math.round(p.left) + " top=" + Math.round(p.top) +
          " w=" + Math.round(p.width) + " h=" + Math.round(p.height));
    }
}
for (var a = 1; a < d.artboards.length; a++) {
    var r = d.artboards[a].artboardRect;
    s("  AB " + d.artboards[a].name + " [" + Math.round(r[0]) + "," + Math.round(r[1]) + "," + Math.round(r[2]) + "," + Math.round(r[3]) + "]");
}
d.close(SaveOptions.DONOTSAVECHANGES); s("DONE"); L.close();
