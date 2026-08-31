// Append today's new figures to NEW_FIGURES_20260804.ai.
//
// USER 2026-08-05: "yes to adding the ones above to the new_figures.ai".
//
// APPENDS ONLY. Every figure goes on a NEW artboard placed to the RIGHT of the rightmost existing one,
// so nothing already on the board moves, resizes or reorders — her layout is hers (standing rule).
// A figure already present (same linked filename) is skipped, so re-running cannot duplicate anything.
// Backed up to NEW_FIGURES_20260804.ai.bak_pre_place_20260805 before this runs.
// pdfCompatible = false on save; alerts suppressed so a modal dialog cannot hang it.

app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;

var LOG = new File("/Volumes/4 MB/ablation_plots/PLACE_LOG_20260805.txt");
LOG.open("w");
function say(s) { LOG.writeln(s); LOG.close(); LOG.open("e"); LOG.seek(0, 2); }

var PDF    = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/";
var FIGROOT = "/Volumes/4 MB/ablation_figures_20260625/";
// PNGs live in their group folders, not in _ai_relink (which holds only pdf/)
var PNGOF = {
    "G6trk_circ_vs_ttana_4group":       FIGROOT + "group6_tracks/G6trk_circ_vs_ttana_4group.png",
    "G6trk_speed_vs_ttana_4group":      FIGROOT + "group6_tracks/G6trk_speed_vs_ttana_4group.png",
    "G6trk_distance_per_min_4group":    FIGROOT + "group6_tracks/G6trk_distance_per_min_4group.png",
    "G6trk_distance_cumulative_4group": FIGROOT + "group6_tracks/G6trk_distance_cumulative_4group.png",
    "G2_ablmeta_vs_duration_single":    FIGROOT + "group2/G2_ablmeta_vs_duration_single.png",
    "G2_ablmeta_vs_duration_triple":    FIGROOT + "group2/G2_ablmeta_vs_duration_triple.png",
    "G3_lagging_by_creation_phase":     FIGROOT + "group3/G3_lagging_by_creation_phase.png",
    "G4_congressed_bar":                FIGROOT + "group4/G4_congressed_bar.png"
};
var FIGS = [
    "G6tenM_polar_vs_paired_percell",
    "G6_polar_distortion_single_vs_triple",
    "G6_polar_distortion_vs_chromolen_single",
    "G6_polar_distortion_vs_chromolen_1v3",
    "G6_area_vs_distortion_over_metaphase",
    "G4_oscillation_1v3_cohort",
    "G6trk_circ_vs_ttana_4group",
    "G6trk_speed_vs_ttana_4group",
    "G6trk_distance_per_min_4group",
    "G6trk_distance_cumulative_4group",
    "G2_ablmeta_vs_duration_single",
    "G2_ablmeta_vs_duration_triple",
    "G3_lagging_by_creation_phase",
    "G4_congressed_bar"
];

if (app.documents.length > 0) {
    say("ABORT: " + app.documents.length + " document(s) already open.");
    LOG.close();
} else {
    var f = new File("/Volumes/4 MB/1_DECKS/NEW_FIGURES_20260804.ai");
    var doc = app.open(f);
    say("opened NEW_FIGURES_20260804.ai — " + doc.artboards.length + " artboards, " +
        doc.placedItems.length + " placed items");

    // what is already here? skip those.
    var have = {};
    for (var i = 0; i < doc.placedItems.length; i++) {
        try {
            var nm = doc.placedItems[i].file.name.replace(/\.(pdf|png|svg)$/i, "");
            have[nm] = true;
        } catch (e) {}
    }

    // rightmost edge of the existing artboards, so new ones sit clear of everything
    var maxRight = -1e9, topY = 0;
    for (var a = 0; a < doc.artboards.length; a++) {
        var r = doc.artboards[a].artboardRect;   // [left, top, right, bottom]
        if (r[2] > maxRight) maxRight = r[2];
        if (a === 0) topY = r[1];
    }
    var GAP = 60, W = 900, H = 620;
    var x = maxRight + GAP * 3;

    var placed = 0, skipped = 0, missing = 0;
    for (var k = 0; k < FIGS.length; k++) {
        // NOTE: do NOT call this `name` — that is a reserved global in ExtendScript and resolves
        // to the application name, so every lookup silently became "Adobe Illustrator".
        var figName = FIGS[k];
        if (have[figName]) { skipped++; say("  already present, skipped: " + figName); continue; }
        // HEAVY SCATTER FIGURES GO IN AS PNG. G6trk_circ_vs_ttana_4group carries ~4800 scatter points;
        // Illustrator hung twice generating a vector preview for it, at 5% CPU with no progress. The PNG
        // is a single image and places instantly. The decks already link a mix of png and pdf, so this is
        // not a new convention. Everything else stays vector.
        var HEAVY = {"G6trk_circ_vs_ttana_4group":1, "G6trk_speed_vs_ttana_4group":1,
                     "G6trk_distance_per_min_4group":1, "G6trk_distance_cumulative_4group":1};
        var pf = HEAVY[figName] && PNGOF[figName] ? new File(PNGOF[figName])
                                                  : new File(PDF + figName + ".pdf");
        if (!pf.exists && PNGOF[figName]) pf = new File(PNGOF[figName]);   // fall back to PNG
        if (!pf.exists) { missing++; say("  NO PDF OR PNG: " + figName); continue; }

        var ab = doc.artboards.add([x, topY, x + W, topY - H]);
        ab.name = figName.substring(0, 60);

        var pi = doc.placedItems.add();
        pi.file = pf;
        // fit inside the artboard, preserving aspect
        var sc = Math.min((W - 2 * GAP) / pi.width, (H - 2 * GAP) / pi.height);
        pi.width *= sc; pi.height *= sc;
        pi.left = x + (W - pi.width) / 2;
        pi.top = topY - (H - pi.height) / 2;

        // SAVE AFTER EVERY FIGURE. The first attempt placed 6 and then stalled with the save still to
        // come, so killing it lost all six. Saving as we go makes the run resumable: the skip-if-present
        // check at the top of the loop means a re-run picks up exactly where it stopped.
        var o1 = new IllustratorSaveOptions(); o1.pdfCompatible = false;
        doc.saveAs(f, o1);
        say("  placed: " + figName + "  (artboard " + doc.artboards.length + ", saved)");
        x += W + GAP * 3;
        placed++;
    }

    var opts = new IllustratorSaveOptions();
    opts.pdfCompatible = false;
    doc.saveAs(f, opts);
    doc.close(SaveOptions.DONOTSAVECHANGES);
    say("placed " + placed + ", skipped " + skipped + ", missing " + missing);
    say("DONE");
    LOG.close();
}
