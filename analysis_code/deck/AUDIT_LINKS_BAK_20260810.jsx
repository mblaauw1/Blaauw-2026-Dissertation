// Dump every linked figure on the four decks, ONE line per link, TAB-separated.
//
// Replaces AUDIT_PLACED_20260810.jsx, whose output ran the name and its count together with no separator
// ("...anisotropy1G6perkt_paired_stretch_radial1"), which cannot be split back apart reliably -- a name may
// legitimately end in a digit. Here each link gets its own line, so nothing has to be re-parsed by guesswork.
//
// `strings` cannot substitute for this: these files are saved with pdfCompatible=false, which omits the XMP
// block carrying stRef:filePath, so a grep returns zero links on a perfectly healthy file.
//
// READ-ONLY. Every document is opened and closed with DONOTSAVECHANGES -- her edits are never touched.

#target illustrator

var FILES = ["/Volumes/4 MB/ablation_plots/_superseded_decks/META_FIGURES_20260805.bak_pre_mainmove_20260810.ai"];
var out = [];

for (var i = 0; i < FILES.length; i++) {
    var f = new File(FILES[i]);
    if (!f.exists) { out.push("MISSING\t" + FILES[i]); continue; }
    var doc = app.open(f);
    var names = {}, missing = 0, nolink = 0;
    for (var p = 0; p < doc.placedItems.length; p++) {
        var lf = null;
        try { lf = doc.placedItems[p].file; } catch (e) { lf = null; }
        if (!lf) { nolink++; continue; }
        if (!lf.exists) missing++;
        var nm = lf.name.replace(/\.(pdf|png|ai|eps|tif|tiff|jpg)$/i, "");
        names[nm] = (names[nm] || 0) + 1;
    }
    out.push("FILE\t" + f.name + "\tplaced=" + doc.placedItems.length +
             "\tartboards=" + doc.artboards.length +
             "\tbrokenlink=" + missing + "\tunlinked=" + nolink);
    for (var k in names) out.push("LINK\t" + f.name + "\t" + k + "\t" + names[k]);
    doc.close(SaveOptions.DONOTSAVECHANGES);
}

var lf2 = new File("/Volumes/4 MB/_claude_tmp/deck_links_bak_20260810.txt");
lf2.open("w"); lf2.write(out.join("\n")); lf2.close();
"done: " + out.length + " lines";
