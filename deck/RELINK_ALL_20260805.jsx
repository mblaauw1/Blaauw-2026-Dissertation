// Refresh every placed link in the four decks so they show the current figures.
//
// USER 2026-08-05: "the adobe illustrator docs are alll closed, so you should be able to update the
// figures in the four illustrator docs just fine".
//
// This ONLY re-reads links from disk. It does not move, add, delete, resize or reorder anything, because
// her layout edits are hers and must survive untouched (standing rule: never revert her deck edits).
// Each file was copied to *.bak_pre_relink_20260805 before this ran.
//
// Aborts immediately if any document is already open, so it can never fight an unsaved edit.
// Saves with pdfCompatible = false (standing rule: keeps the files small and the save fast).

// Suppress modal dialogs. The first run hung inside app.open() with an empty log — Illustrator was
// waiting on a dialog nobody could answer (missing fonts / colour profile / "update modified links?").
// With alerts off it answers itself and proceeds.
app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;

var LOG = new File("/Volumes/4 MB/ablation_plots/RELINK_LOG_20260805.txt");
LOG.open("w");
function say(s) { LOG.writeln(s); LOG.close(); LOG.open('e'); LOG.seek(0, 2); }

if (app.documents.length > 0) {
    say("ABORT: " + app.documents.length + " document(s) already open — refusing to touch anything.");
    for (var q = 0; q < app.documents.length; q++) say("   open: " + app.documents[q].name);
    LOG.close();
} else {
    var base = "/Volumes/4 MB/ablation_plots/";
    var docs = ["META_FIGURES_20260803.ai", "supplemental.ai",
                "NEW_TIMESTRIPS_20260804.ai", "NEW_FIGURES_20260804.ai"];
    var grand = 0, grandFail = 0;

    for (var d = 0; d < docs.length; d++) {
        var f = new File(base + docs[d]);
        if (!f.exists) { say(docs[d] + ": NOT FOUND"); continue; }
        say("opening " + docs[d] + " ...");
        var doc = app.open(f);
        var refreshed = 0, missing = 0, failed = 0, total = 0;

        // placedItems = linked .ai/.pdf; rasterItems = linked images. Both can carry a file link.
        var pools = [doc.placedItems, doc.rasterItems];
        for (var p = 0; p < pools.length; p++) {
            var items = pools[p];
            for (var i = items.length - 1; i >= 0; i--) {
                var it = items[i];
                total++;
                var lf = null;
                try { lf = it.file; } catch (e) { lf = null; }
                if (lf === null) { missing++; continue; }        // embedded, not linked — nothing to do
                try {
                    if (!lf.exists) { missing++; say("   MISSING FILE: " + lf.fsName); continue; }
                    // relinking to the SAME path forces Illustrator to re-read the current bytes
                    it.file = lf;
                    refreshed++;
                } catch (e2) {
                    failed++;
                    say("   FAILED: " + (lf ? lf.name : "?") + " -> " + e2);
                }
            }
        }
        var opts = new IllustratorSaveOptions();
        opts.pdfCompatible = false;
        doc.saveAs(f, opts);
        doc.close(SaveOptions.DONOTSAVECHANGES);
        say(docs[d] + ": " + total + " placed item(s); refreshed " + refreshed +
            ", not linked/missing " + missing + ", failed " + failed);
        grand += refreshed; grandFail += failed;
    }
    say("TOTAL refreshed " + grand + ", failed " + grandFail);
    say("DONE");
    LOG.close();
}
