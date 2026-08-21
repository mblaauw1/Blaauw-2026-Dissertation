// READ-ONLY inspection of NEW_FIGURES_20260804.ai. Opens, measures, reports, closes WITHOUT saving.
// Written because two post-save signals looked wrong and neither can be judged from outside the file:
//   * `strings | grep stRef:filePath` returned 0 links, but that string lives in XMP metadata which a
//     pdfCompatible=false save does not embed -- so it is not evidence of lost links either way.
//   * the placement log reported the same pageItems count before and after placing 31 figures.
// The document itself is the only authority, so this asks it directly and changes nothing.

#target illustrator

var AI = "/Volumes/4 MB/1_DECKS/NEW_FIGURES_20260804.ai";
var doc = app.open(new File(AI));
var out = [];

out.push("pageItems      = " + doc.pageItems.length);
out.push("placedItems    = " + doc.placedItems.length);
out.push("textFrames     = " + doc.textFrames.length);
out.push("rasterItems    = " + doc.rasterItems.length);
out.push("layers         = " + doc.layers.length);
out.push("artboards      = " + doc.artboards.length);
for (var a = 0; a < doc.artboards.length; a++) {
    out.push("   AB" + a + " rect = " + doc.artboards[a].artboardRect.join(", "));
}

// overall artwork bounds
var nX = 1e9, xX = -1e9, nY = 1e9, xY = -1e9;
for (var i = 0; i < doc.pageItems.length; i++) {
    var b = doc.pageItems[i].visibleBounds;
    if (b[0] < nX) nX = b[0];
    if (b[2] > xX) xX = b[2];
    if (b[3] < nY) nY = b[3];
    if (b[1] > xY) xY = b[1];
}
out.push("artwork bounds L=" + nX.toFixed(0) + " T=" + xY.toFixed(0) + " R=" + xX.toFixed(0) + " B=" + nY.toFixed(0));
out.push("artwork size   = " + (xX - nX).toFixed(0) + " x " + (xY - nY).toFixed(0));

// how many placed items are missing their linked file, and how many are this session's
var missing = 0, sess = 0, names = {};
for (var p = 0; p < doc.placedItems.length; p++) {
    var f = null;
    try { f = doc.placedItems[p].file; } catch (e) { f = null; }
    if (!f || !f.exists) { missing++; continue; }
    var nm = f.name.replace(/\.pdf$/i, "");
    names[nm] = (names[nm] || 0) + 1;
}
out.push("placed with a MISSING linked file = " + missing);

// which of this session's figures are present, and how many copies
var want = ["kk_osc_meankk","kk_osc_amplitude","kk_osc_period","kk_osc_about_plate","kk_osc_model",
            "kk_osc_metaphase_duration","G8_pole_distance_over_time","G6_prometa_vs_meta_amplitude",
            "G6_prometa_vs_meta_period","G6_prometa_vs_meta_meankk","G6_prometa_vs_meta_model",
            "G6_amplitude_summary_statistic_sensitivity","G5_lagging_piece_count_after_anaphase",
            "G6_polar_distortion_vs_chromolen_1v3","G6tenM_flatness_polar_vs_paired",
            "G1_plate_rotation_combined","G1_plate_rotation_split","G1_plate_rotation_combined_meta",
            "G1_plate_rotation_split_meta","G1_centroid_movement_combined","G1_centroid_movement_split",
            "G1_centroid_movement_combined_meta","G1_centroid_movement_split_meta","G4_sisbehav_swimmer",
            "ablation_count_by_cohort","ablation_count_on_vs_offpooled",
            "G4_frap_vs_ablation_selected_combined_20s","G6_polepole_approx_absolute_time",
            "G1_violin2_mitotic_duration_journal","G6_sister_oscillation_single_vs_triple",
            "G6_anaphase_kt_speed_single_vs_triple"];
var found = 0, absent = [];
for (var w = 0; w < want.length; w++) {
    if (names[want[w]]) found++; else absent.push(want[w]);
}
out.push("this session's figures present = " + found + " of " + want.length);
for (var z = 0; z < absent.length; z++) out.push("   ABSENT: " + absent[z]);

doc.close(SaveOptions.DONOTSAVECHANGES);

var lf = new File("/tmp/nf_check_report.txt");
lf.open("w"); lf.write(out.join("\n")); lf.close();
out.join("\n");
