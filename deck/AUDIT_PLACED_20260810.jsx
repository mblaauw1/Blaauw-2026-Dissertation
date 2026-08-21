// List every linked figure on the four decks, so placement can be audited from outside.
// `strings` cannot be used for this any more: these files are saved with pdfCompatible=false, which omits
// the XMP block that carries stRef:filePath, so a grep returns zero links on a perfectly healthy file.
// Each document is opened read-only and closed without saving.

#target illustrator

var FILES = ["/Volumes/4 MB/1_DECKS/NEW_FIGURES_20260804.ai",
             "/Volumes/4 MB/ablation_plots/META_FIGURES_20260805.ai",
             "/Volumes/4 MB/ablation_figures_edited.ai",
             "/Volumes/4 MB/ablation_figures_edited_1.ai"];
var out = [];

for (var i = 0; i < FILES.length; i++) {
    var f = new File(FILES[i]);
    if (!f.exists) { out.push("MISSING\t" + FILES[i]); continue; }
    var doc = app.open(f);
    var names = {};
    var missing = 0;
    for (var p = 0; p < doc.placedItems.length; p++) {
        var lf = null;
        try { lf = doc.placedItems[p].file; } catch (e) { lf = null; }
        if (!lf) { missing++; continue; }
        if (!lf.exists) missing++;
        var nm = lf.name.replace(/\.(pdf|png|ai|eps)$/i, "");
        names[nm] = (names[nm] || 0) + 1;
    }
    var list = [];
    for (var k in names) list.push(k + "" + names[k]);
    out.push("FILE\t" + f.name + "\t" + doc.placedItems.length + "\t" + missing);
    out.push("LINKS\t" + list.join(""));
    doc.close(SaveOptions.DONOTSAVECHANGES);
}

var lf2 = new File("/tmp/deck_links_audit.txt");
lf2.open("w"); lf2.write(out.join("\n")); lf2.close();
"done";
