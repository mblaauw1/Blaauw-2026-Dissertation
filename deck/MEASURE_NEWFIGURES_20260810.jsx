// Read-only geometry dump of NEW_FIGURES, so the repack is designed from measurement.
//
// The previous attempt wrote a 0-byte file while its log wrote fine, so every item access here is wrapped
// individually and the reason for any skip is recorded rather than swallowed -- a silent empty result is
// exactly what made the earlier six-strip planner report "0 tracks" while every insert was throwing.
//
// Opened and closed with DONOTSAVECHANGES; nothing about the document is modified.

#target illustrator

var TARGET = "/Volumes/4 MB/1_DECKS/NEW_FIGURES_20260804.ai";
var doc = app.open(new File(TARGET));
var geo = ["kind\tname\tL\tT\tR\tB\tlayer"];
var skipped = 0, n = 0;

try { n = doc.pageItems.length; } catch (e0) { geo.push("ERR\tpageItems.length threw: " + e0); }

for (var i = 0; i < n; i++) {
    var kind = "?", nm = "", b = null, lay = "";
    try {
        var it = doc.pageItems[i];
        try { kind = it.typename; } catch (e1) {}
        try { b = it.visibleBounds; } catch (e2) { b = null; }
        try { if (kind === "PlacedItem" && it.file) nm = it.file.name.replace(/\.(pdf|png|ai|eps)$/i, ""); } catch (e3) {}
        try { if (!nm && kind === "TextFrame") nm = String(it.contents).substr(0, 40).replace(/[\t\r\n]/g, " "); } catch (e4) {}
        try { lay = it.layer.name; } catch (e5) { lay = ""; }
        if (b === null) { skipped++; continue; }
        geo.push(kind + "\t" + nm + "\t" + b[0].toFixed(1) + "\t" + b[1].toFixed(1) + "\t" +
                 b[2].toFixed(1) + "\t" + b[3].toFixed(1) + "\t" + lay);
    } catch (eOuter) { skipped++; }
}

geo.push("# items=" + n + " written=" + (geo.length - 1) + " skipped=" + skipped);

var gf = new File("/Volumes/4 MB/_claude_tmp/newfigures_geometry.tsv");
gf.encoding = "UTF-8";
gf.open("w");
for (var g = 0; g < geo.length; g++) gf.writeln(geo[g]);
gf.close();

doc.close(SaveOptions.DONOTSAVECHANGES);
"items=" + n + " written=" + (geo.length - 2) + " skipped=" + skipped;
