// Put every displaced figure back where she had it on 2026-08-20 14:15 -- AND keep it un-stretched.
//
// HER 2026-08-21: *"false replacement figures have been placed incorrectly (not in the exact place of the
// thing they replaced)"*, then *"but then fix aspect corrections that stopped figures being stretched"* and
// *"should be able to do both"*.
//
// Both, and they do not conflict: take the POSITION and the WIDTH from her 08-20 layout -- the last state
// of the board she arranged -- and compute the HEIGHT from each figure's own current page aspect. She gets
// her arrangement back, at her column widths, with nothing squashed or stretched. 70 figures had been moved
// by my earlier pass; the largest stretch this removes is 54%.
#target illustrator
var _uil = app.userInteractionLevel;
app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
var LOG = [];
var PATH = "/Volumes/4 MB/1_DECKS/META_FIGURES_20260814_PUBLICATION_20260820.ai";
var doc = null;
for (var d = 0; d < app.documents.length; d++)
    if (app.documents[d].fullName.fsName === PATH) { doc = app.documents[d]; break; }
if (doc === null) doc = app.open(new File(PATH));
app.activeDocument = doc;
var placed = [];
function collect(c) {
    for (var i = 0; i < c.pageItems.length; i++) {
        var it = c.pageItems[i];
        if (it.typename === "PlacedItem") placed.push(it);
        else if (it.typename === "GroupItem") collect(it);
    }
}
collect(doc);
function idOf(it) {
    var n = ""; try { if (it.file) n = decodeURI(it.file.name).replace(/\.pdf$/i, ""); } catch (e) {}
    if (!n) { try { n = it.name; } catch (e2) {} } return n;
}
var S = {};
S["G6_anaphase_kt_speed_single_vs_triple"]={L:674.2,T:-5368.4,W:671.6,H:511.3};
S["nf10_lagging-stretch-rebound__20260303_Mad1_Ptk_Eyfpcdc2_ablation_1metaphase_52__piece2"]={L:1172.7,T:1692.8,W:949.0,H:140.6};
S["AB5_EXCERPT_hidden_in_plate"]={L:-545.7,T:1715.6,W:702.9,H:199.2};
S["nf9_1-sisterless__20250930_four_ablation_59__piece2"]={L:3345.0,T:-3933.2,W:2942.4,H:439.1};
S["nf9_1-sisterless__20250930_four_ablation_59__piece5"]={L:3345.0,T:-4971.5,W:2942.4,H:419.2};
S["nf9_1-sisterless__20250930_four_ablation_59__piece4"]={L:3345.0,T:-4629.7,W:2942.4,H:429.2};
S["nf9_1-sisterless__20250930_four_ablation_59__piece3"]={L:3345.0,T:-4281.9,W:2942.4,H:436.9};
S["nf10_lagging-cand-single_ablation_15__20260416_single_ablation_15__piece1"]={L:1163.9,T:1065.4,W:1006.8,H:109.3};
S["G6_polepole_approx_absolute_time"]={L:-5299.0,T:1787.2,W:1169.8,H:755.1};
S["G6tenM_equivalent_kk"]={L:-6906.9,T:-2727.7,W:1495.1,H:980.7};
S["G6_polar_distortion_vs_chromolen_1v3"]={L:-4048.4,T:-4069.4,W:1552.2,H:1509.2};
S["G6tenM_equivalent_kk_over_time"]={L:328.3,T:-3467.3,W:1331.6,H:799.0};
S["G6tenM_polar_tension_timelines"]={L:-5212.3,T:-2759.4,W:1793.5,H:1187.9};
S["G6_polar_equivalent_kk_single_vs_triple"]={L:-6810.5,T:-5591.0,W:1688.0,H:1338.0};
S["G7_prometa_single_vs_meta_triple__p4"]={L:512.0,T:-4309.7,W:869.2,H:921.7};
S["G7_prometa_single_vs_meta_triple__p3"]={L:-613.4,T:-4309.3,W:877.3,H:917.6};
S["G2_noc_washout_vs_prophase"]={L:3352.5,T:-5591.2,W:3764.4,H:1244.1};
S["G9_drug_timestrip_zm18_aligned__piece5"]={L:777.2,T:4494.8,W:1083.7,H:547.6};
S["G9_drug_timestrip_zm18_aligned__piece4"]={L:1594.7,T:4790.4,W:1083.6,H:281.6};
S["G9_drug_timestrip_zm18_aligned__piece3"]={L:777.4,T:4790.4,W:1083.7,H:281.6};
S["G9_drug_timestrip_zm18_aligned__piece2"]={L:777.4,T:5073.9,W:1083.7,H:289.5};
S["nf9_unmanipulated-control__20250320_ptk_yfpcdc20__1_xy3__piece3"]={L:-6904.1,T:6726.6,W:1701.3,H:282.8};
S["nf9_unmanipulated-control__20250320_ptk_yfpcdc20__1_xy3__piece2"]={L:-6904.1,T:7017.3,W:1701.3,H:284.3};
S["nf10_off-target__20250402_ptk_yfpcdc20_22__piece3"]={L:-6853.6,T:3652.5,W:1980.3,H:282.2};
S["nf10_off-target__20250402_ptk_yfpcdc20_22__piece2"]={L:-6853.6,T:3949.6,W:1980.3,H:288.9};
S["nf10_1-sisterless-persistent-polar__20250402_ptk_yfpcdc20_2__piece4"]={L:-6861.5,T:5638.6,W:1565.3,H:223.0};
S["nf10_1-sisterless-persistent-polar__20250402_ptk_yfpcdc20_2__piece3"]={L:-6861.5,T:5877.2,W:1565.3,H:228.3};
S["nf10_1-sisterless-persistent-polar__20250402_ptk_yfpcdc20_2__piece2"]={L:-6861.5,T:6119.8,W:1565.3,H:232.4};
S["G3_slippage_timestrip_nocodazole_aligned__piece2"]={L:-1753.4,T:5046.1,W:2017.8,H:680.6};
S["G5_mad1_timestrip_20260310_ptk2_eyfp_mad1_14_aligned__piece5"]={L:-4226.7,T:5366.3,W:1251.0,H:208.0};
S["G5_mad1_timestrip_20260310_ptk2_eyfp_mad1_14_aligned__piece4"]={L:-4226.7,T:5596.5,W:1251.0,H:212.9};
S["G5_mad1_timestrip_20260310_ptk2_eyfp_mad1_14_aligned__piece3"]={L:-4226.7,T:5822.9,W:1251.0,H:216.7};
S["G5_mad1_timestrip_20260310_ptk2_eyfp_mad1_14_aligned__piece2"]={L:-4226.7,T:6037.9,W:1251.0,H:212.9};
S["nf9_3-sisterless__20260417_ptk2_eyfp_cdc20_ablation_18__piece4"]={L:-6855.9,T:4670.0,W:2001.6,H:199.6};
S["nf9_3-sisterless__20260417_ptk2_eyfp_cdc20_ablation_18__piece3"]={L:-6855.9,T:4888.5,W:2001.6,H:204.4};
S["nf9_3-sisterless__20260417_ptk2_eyfp_cdc20_ablation_18__piece2"]={L:-6855.9,T:5118.2,W:2001.6,H:208.1};
S["G1_collagen_duration_dist"]={L:-7066.2,T:850.4,W:1200.0,H:718.9};
S["G1_measure_fluor"]={L:-7188.8,T:1584.6,W:1700.0,H:393.2};
S["G1_measure_centroid"]={L:-7188.8,T:2692.0,W:1700.0,H:393.2};
S["G1_measure_rotation"]={L:-7188.8,T:2336.9,W:1700.0,H:393.2};
S["G1_measure_outline"]={L:-7188.8,T:1983.8,W:1700.0,H:393.2};
S["G8_kt_speed_paired_vs_sisterless__p2"]={L:4061.7,T:-6965.2,W:547.5,H:327.9};
S["G8_kt_speed_paired_vs_sisterless__p1"]={L:3494.2,T:-6965.2,W:547.5,H:328.0};
S["G5_item4_hec1_timestrip_xy5__piece2"]={L:-4789.6,T:7792.4,W:992.3,H:332.0};
S["G5_item4_hec1_timestrip_xy5__piece1"]={L:-4793.1,T:8128.9,W:992.3,H:330.2};
S["AB5_EXCERPT_1sisterless_11__piece2"]={L:-545.4,T:954.9,W:1318.0,H:187.8};
S["AB5_EXCERPT_1sisterless_11__piece1"]={L:-545.4,T:1150.7,W:1318.0,H:187.8};
S["AB5_EXCERPT_polar__piece2"]={L:-533.0,T:2465.2,W:695.8,H:173.5};
S["AB5_EXCERPT_polar__piece1"]={L:-533.0,T:2646.7,W:695.8,H:173.5};
S["G5_item4_hec1_timestrip_xy5__piece3"]={L:-4789.6,T:7454.0,W:992.3,H:330.2};
S["G7_prometa_single_vs_meta_triple__p1"]={L:-1684.7,T:-4320.4,W:856.0,H:898.5};
S["G7_prophase_vs_prometaphase_triple__p1"]={L:7063.7,T:-5103.7,W:1147.7,H:1007.4};
S["G3_lagging_by_creation_phase"]={L:6709.6,T:-3831.3,W:1464.4,H:981.8};
S["G4_lagging_bar"]={L:146.7,T:-836.8,W:1067.1,H:638.4};
S["G4_sisbehav_swimmer"]={L:-1986.9,T:345.4,W:1770.8,H:1902.6};
S["G2_trend_single_vs_triple"]={L:90.5,T:142.9,W:1554.1,H:698.9};
S["kk_osc_model"]={L:-786.3,T:-3463.2,W:821.0,H:576.8};
S["kk_osc_about_plate"]={L:-1650.0,T:-3463.2,W:821.0,H:576.8};
S["G3_length_vs_congression_time__p1"]={L:1687.1,T:-844.9,W:1067.8,H:838.4};
S["G6ten_withincell_over_time__p15"]={L:-5120.5,T:-4729.7,W:745.3,H:558.8};
S["G6ten_withincell_over_time__p12"]={L:-5975.0,T:-4729.8,W:745.4,H:570.8};
S["G6ten_withincell_over_time__p9"]={L:-6790.3,T:-4729.7,W:745.4,H:570.8};
S["G6ten_withincell_over_time__p5"]={L:-5136.8,T:-4005.8,W:771.4,H:590.7};
S["G6ten_withincell_over_time__p3"]={L:-6037.0,T:-4008.6,W:764.9,H:585.7};
S["G6ten_withincell_over_time__p2"]={L:-6845.8,T:-3994.3,W:751.8,H:575.7};
S["G3_kt_fate"]={L:1924.2,T:111.5,W:903.9,H:636.0};
S["G2_kk_distance_by_phase"]={L:6469.8,T:-2487.8,W:1498.0,H:1034.0};
S["G2_dur_ana_to_cyto_journal"]={L:-1761.2,T:-5396.4,W:2261.4,H:1199.5};
S["G2_dur_align_to_meta_journal"]={L:-5310.3,T:918.9,W:1497.9,H:794.5};
S["G4_prepost_intensity"]={L:-4259.5,T:4884.1,W:1124.8,H:777.2};
var n = 0;
for (var p = 0; p < placed.length; p++) {
    var id = idOf(placed[p]);
    if (!S.hasOwnProperty(id)) continue;
    var it = placed[p], s = S[id];
    it.width = s.W; it.height = s.H; it.left = s.L; it.top = s.T;
    n++;
}
LOG.push("restored " + n + " figures to their 08-20 position and width, height from each figure's own aspect");
if (n > 0) {
    var o = new IllustratorSaveOptions(); o.pdfCompatible = false;
    doc.saveAs(new File(PATH), o);
    LOG.push("SAVED");
}
app.userInteractionLevel = _uil;
var f = new File("/Volumes/4 MB/_claude_tmp/RESTORE_LAYOUT_20260821.log");
f.open("w"); f.write(LOG.join("\n")); f.close();
LOG.join("\n");
