// Scale down the CONTENTS of the three full artboards so the overlapping figure fits with clear space.
// USER 2026-08-17: "if a figure is supposed to go on a certain artboard but that artboard is full, just
// scale down everything on the full artboard so theres room to place the other items without overlapping
// anything."
//
// AB4 -> 80%, AB5 -> 95%, AB8 -> 92%. Every item is scaled UNIFORMLY about its artboard centre (the board's
// composition is preserved, just tighter), then the figure that was overlapping is moved into the freed
// space. Targets were solved in Python against a 20 pt occupancy grid and are written out literally here,
// so this script does no geometry maths of its own and cannot drift from what was verified.
//
// TWO ITEMS ARE DELIBERATELY UNTOUCHED: G2_trend_single_vs_triple and G3_length_vs_congression_time__p1
// straddle artboards 5 and 6, so scaling them about AB5 centre would drag them off AB6. They were pinned as
// fixed obstacles in the solve.
//
// Matching is by link basename AND current bounds, so an item placed more than once cannot be confused.
#target illustrator
var AIP="/Volumes/4 MB/1_DECKS/META_FIGURES_20260814.ai";
var HB=new File("/Volumes/4 MB/_claude_tmp/scale_boards.txt");
function beat(m){try{HB.open("a");HB.writeln(m);HB.close();}catch(e){}}
var T=[
{b:"4",n:"G1_plate_rotation_combined_meta_trendscaled_delta.pdf",ol:-3064.00,ot:-1300.00,nl:-3411.20,nt:-940.00,nw:651.20,nh:389.76},
{b:"4",n:"G1_centroid_movement_combined_meta_trendscaled_delta.pdf",ol:-3892.00,ot:-1300.00,nl:-4073.60,nt:-940.00,nw:651.20,nh:389.92},
{b:"4",n:"G1_roundness_combined_trendscaled_delta.pdf",ol:-4721.00,ot:-1300.00,nl:-4736.80,nt:-940.00,nw:651.20,nh:389.92},
{b:"4",n:"G1_area_combined_trendscaled_delta.pdf",ol:-5550.00,ot:-1300.00,nl:-5400.00,nt:-940.00,nw:651.20,nh:389.84},
{b:"4",n:"G1_meta_ana_pair_candidates.pdf",ol:-4648.10,ot:1400.00,nl:-4678.48,nt:1220.00,nw:1076.88,nh:860.00},
{b:"4",n:"traced_cell.pdf",ol:-7245.80,ot:-1240.00,nl:-6756.64,nt:-892.00,nw:1352.88,nh:576.00},
{b:"4",n:"G1_plate_rotation_combined_meta_trendscaled.pdf",ol:-4015.60,ot:2566.90,nl:-4172.48,nt:2153.52,nw:1400.08,nh:920.40},
{b:"4",n:"G1_centroid_movement_combined_meta_trendscaled.pdf",ol:-5667.90,ot:2567.00,nl:-5494.32,nt:2153.60,nw:1400.16,nh:920.40},
{b:"4",n:"G6_polepole_approx_absolute_time.pdf",ol:-7302.80,ot:146.20,nl:-6802.24,nt:216.96,nw:1706.40,nh:1016.24},
{b:"4",n:"G1_roundness_combined_trendscaled.pdf",ol:-7221.50,ot:2477.00,nl:-6737.20,nt:2081.60,nw:1142.72,nh:728.80},
{b:"4",n:"G1_area_combined_trendscaled.pdf",ol:-7138.80,ot:1328.20,nl:-6671.04,nt:1162.56,nw:1142.72,nh:728.80},
{b:"4",n:"collagen_vs_triple_2or3_ontarget_area_meta_to_ana.pdf",ol:-8274.00,ot:1444.50,nl:-7579.20,nt:1255.60,nw:1158.16,nh:819.20},
{b:"4",n:"G2_dur_align_to_meta_journal.pdf",ol:-5096.20,ot:305.40,nl:-5036.96,nt:344.32,nw:2184.96,nh:1270.96},
{b:"4",n:"collagen_vs_triple_2or3_ontarget_roundness_meta_to_ana.pdf",ol:-8296.80,ot:2533.50,nl:-7330.00,nt:3030.00,nw:1158.16,nh:819.20},
{b:"5",n:"nf10_lagging-cand-single_ablation_15__20260416_single_ablation_15.pdf",ol:-2050.00,ot:124.00,nl:-1922.50,nt:142.80,nw:610.18,nh:141.55},
{b:"5",n:"nf10_lagging-cand-four_ablation_59__20250930_four_ablation_59.pdf",ol:-2050.00,ot:293.00,nl:-1922.50,nt:303.35,nw:610.18,nh:141.55},
{b:"5",n:"nf10_lagging-cand-two_sisterless_14__20260108_two_sisterless_kinetochores_14.pdf",ol:-2050.00,ot:462.00,nl:-1922.50,nt:463.90,nw:610.18,nh:141.55},
{b:"5",n:"nf10_lagging-cand-four_ablation_23__20250929_four_ablation_23.pdf",ol:-2050.00,ot:631.00,nl:-1922.50,nt:624.45,nw:610.18,nh:141.55},
{b:"5",n:"nf10_lagging-cand-triple_ablation_26__20251029_triple_ablation_26.pdf",ol:-2050.00,ot:800.00,nl:-1922.50,nt:785.00,nw:610.18,nh:141.55},
{b:"5",n:"AB5_EXCERPT_polar.pdf",ol:-42.60,ot:2503.10,nl:-15.47,nt:2402.94,nw:695.40,nh:347.70},
{b:"5",n:"AB5_EXCERPT_hidden_in_plate.pdf",ol:-46.50,ot:1920.00,nl:-19.17,nt:1849.00,nw:702.72,nh:351.31},
{b:"5",n:"nf10_lagging-stretch-rebound__20260303_Mad1_Ptk_Eyfpcdc2_ablation_1metaphase_52.pdf",ol:-281.30,ot:-841.30,nl:-242.23,nt:-774.23,nw:1898.01,nh:608.48},
{b:"5",n:"(EMBEDDED)",ol:-46.50,ot:1324.80,nl:-19.17,nt:1283.56,nw:1318.32,nh:381.90},
{b:"5",n:"G4_lagging_bar.pdf",ol:-389.20,ot:-70.00,nl:-344.74,nt:-41.50,nw:1064.95,nh:704.23},
{b:"5",n:"G3_kt_fate.pdf",ol:1825.00,ot:592.10,nl:1758.75,nt:587.50,nw:903.83,nh:720.76},
{b:"5",n:"G4_sisbehav_swimmer.pdf",ol:-1941.40,ot:-27.10,nl:-2030.00,nt:3030.00,nw:1770.89,nh:1902.66},
{b:"8",n:"G6kk_zoom_candidates.pdf",ol:-988.10,ot:-6650.00,nl:-869.05,nt:-6502.00,nw:1128.10,nh:644.00},
{b:"8",n:"G7_prometa_single_vs_meta_triple__p4.pdf",ol:277.40,ot:-2905.70,nl:295.21,nt:-3057.24,nw:869.12,nh:1008.32},
{b:"8",n:"G7_prometa_single_vs_meta_triple__p3.pdf",ol:-703.00,ot:-2905.70,nl:-606.76,nt:-3057.24,nw:877.31,nh:1008.41},
{b:"8",n:"G7_prometa_single_vs_meta_triple__p1.pdf",ol:-1814.10,ot:-4001.70,nl:-1628.97,nt:-4065.56,nw:855.97,nh:994.52},
{b:"8",n:"G6_polar_equivalent_kk_single_vs_triple.pdf",ol:930.70,ot:-4195.30,nl:896.24,nt:-4243.68,nw:1687.92,nh:774.36},
{b:"8",n:"G6_anaphase_kt_speed_single_vs_triple.pdf",ol:261.60,ot:-5816.20,nl:280.67,nt:-5734.90,nw:1119.36,nh:555.68},
{b:"8",n:"kk_osc_model.pdf",ol:1303.40,ot:-3246.90,nl:1239.13,nt:-3371.15,nw:821.01,nh:599.75},
{b:"8",n:"kk_osc_about_plate.pdf",ol:-1741.10,ot:-3270.10,nl:-1561.81,nt:-3392.49,nw:821.01,nh:599.75},
{b:"8",n:"G6tenM_equivalent_kk_over_time.pdf",ol:-632.20,ot:-4195.30,nl:-541.62,nt:-4243.68,nw:1331.61,nh:796.90},
{b:"8",n:"G2_dur_ana_to_cyto_journal.pdf",ol:-1821.10,ot:-5206.30,nl:-2030.00,nt:-5090.00,nw:2261.36,nh:1315.60}
];
app.userInteractionLevel=UserInteractionLevel.DONTDISPLAYALERTS;
var doc=app.open(new File(AIP));
var done=0, miss=0;
function baseName(s){ var i=s.lastIndexOf("/"); return i<0?s:s.substring(i+1); }
for (var k=0;k<T.length;k++){
  var t=T[k], hit=null;
  for (var i=0;i<doc.placedItems.length;i++){
    var it=doc.placedItems[i], f="";
    try{ f=it.file? baseName(it.file.fsName):""; }catch(e){ continue; }
    if (f!==t.n) continue;
    var b=it.visibleBounds;
    if (Math.abs(b[0]-t.ol)>2 || Math.abs(b[1]-t.ot)>2) continue;
    hit=it; break;
  }
  if (!hit){
    for (var r=0;r<doc.rasterItems.length;r++){
      var ri=doc.rasterItems[r], bb=ri.visibleBounds;
      if (Math.abs(bb[0]-t.ol)>2 || Math.abs(bb[1]-t.ot)>2) continue;
      hit=ri; break;
    }
  }
  if (!hit){ miss++; beat("MISS "+t.n+" @"+t.ol.toFixed(0)+","+t.ot.toFixed(0)); continue; }
  hit.width=t.nw; hit.height=t.nh; hit.left=t.nl; hit.top=t.nt;
  done++;
}
beat("repositioned="+done+" missed="+miss);
doc.save();
doc.close(SaveOptions.SAVECHANGES);
app.userInteractionLevel=UserInteractionLevel.DISPLAYALERTS;
"done="+done+" miss="+miss;
