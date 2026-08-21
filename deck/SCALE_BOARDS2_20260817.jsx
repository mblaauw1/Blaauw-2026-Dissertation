// PASS 2 — clear the last two residual overlaps (AB4 21.8%, AB1 18.7%), same method as SCALE_BOARDS:
// scale that board's single-board items to 95% about the board centre, then move the item that was ON TOP
// into the freed space. Cross-board items stay pinned. Targets solved in Python, written literally.
#target illustrator
var AIP="/Volumes/4 MB/1_DECKS/META_FIGURES_20260814.ai";
var HB=new File("/Volumes/4 MB/_claude_tmp/scale_boards2.txt");
function beat(m){try{HB.open("a");HB.writeln(m);HB.close();}catch(e){}}
var T=[
{n:"G1_plate_rotation_combined_meta_trendscaled_delta.pdf",ol:-3411.20,ot:-940.00,nl:-3480.64,nt:-868.00,nw:618.64,nh:370.31},
{n:"G1_centroid_movement_combined_meta_trendscaled_delta.pdf",ol:-4073.60,ot:-940.00,nl:-4109.92,nt:-868.00,nw:618.64,nh:370.40},
{n:"G1_roundness_combined_trendscaled_delta.pdf",ol:-4736.80,ot:-940.00,nl:-4739.96,nt:-868.00,nw:618.64,nh:370.40},
{n:"G1_area_combined_trendscaled_delta.pdf",ol:-5400.00,ot:-940.00,nl:-5370.00,nt:-868.00,nw:618.64,nh:370.31},
{n:"G1_meta_ana_pair_candidates.pdf",ol:-4678.50,ot:1220.00,nl:-4684.57,nt:1184.00,nw:1023.06,nh:817.00},
{n:"traced_cell.pdf",ol:-6756.60,ot:-892.00,nl:-6658.77,nt:-822.40,nw:1285.26,nh:547.20},
{n:"G1_plate_rotation_combined_meta_trendscaled.pdf",ol:-4172.50,ot:2153.50,nl:-4203.88,nt:2070.82,nw:1330.09,nh:874.38},
{n:"G1_centroid_movement_combined_meta_trendscaled.pdf",ol:-5494.30,ot:2153.60,nl:-5459.59,nt:2070.92,nw:1330.19,nh:874.38},
{n:"G6_polepole_approx_absolute_time.pdf",ol:-6802.20,ot:217.00,nl:-6702.09,nt:231.15,nw:1621.08,nh:965.39},
{n:"G1_roundness_combined_trendscaled.pdf",ol:-6737.20,ot:2081.60,nl:-6640.34,nt:2002.52,nw:1085.57,nh:692.36},
{n:"G1_area_combined_trendscaled.pdf",ol:-6671.00,ot:1162.60,nl:-6577.45,nt:1129.47,nw:1085.57,nh:692.36},
{n:"collagen_vs_triple_2or3_ontarget_roundness_meta_to_ana.pdf",ol:-7330.00,ot:3030.00,nl:-7203.50,nt:2903.50,nw:1100.29,nh:778.24},
{n:"G2_dur_align_to_meta_journal.pdf",ol:-5037.00,ot:344.30,nl:-5025.15,nt:352.09,nw:2075.75,nh:1207.45},
{n:"collagen_vs_triple_2or3_ontarget_area_meta_to_ana.pdf",ol:-7579.20,ot:1255.60,nl:-6075.00,nt:3035.00,nw:1100.29,nh:778.24},
{n:"nf9_3-sisterless__20260417_ptk2_eyfp_cdc20_ablation_18__piece7.pdf",ol:-4957.90,ot:6859.80,nl:-4950.00,nt:6806.81,nw:347.51,nh:36.10},
{n:"nf9_3-sisterless__20260417_ptk2_eyfp_cdc20_ablation_18__piece6.pdf",ol:-5353.20,ot:6805.90,nl:-5325.54,nt:6755.60,nw:382.19,nh:74.48},
{n:"nf9_3-sisterless__20260417_ptk2_eyfp_cdc20_ablation_18__piece5.pdf",ol:-5814.00,ot:6750.00,nl:-5763.30,nt:6702.50,nw:543.40,nh:317.30},
{n:"nf9_3-sisterless__20260417_ptk2_eyfp_cdc20_ablation_18__piece4.pdf",ol:-6106.20,ot:6805.90,nl:-6040.89,nt:6755.60,nw:382.28,nh:74.58},
{n:"nf9_3-sisterless__20260417_ptk2_eyfp_cdc20_ablation_18__piece3.pdf",ol:-6567.30,ot:6749.90,nl:-6478.94,nt:6702.40,nw:543.97,nh:318.35},
{n:"nf9_3-sisterless__20260417_ptk2_eyfp_cdc20_ablation_18__piece2.pdf",ol:-6859.20,ot:6805.90,nl:-6756.24,nt:6755.60,nw:382.19,nh:74.48},
{n:"nf9_3-sisterless__20260417_ptk2_eyfp_cdc20_ablation_18__piece1.pdf",ol:-7320.30,ot:6749.90,nl:-7194.28,nt:6702.40,nw:543.97,nh:318.35},
{n:"nf9_unmanipulated-control__20250320_ptk_yfpcdc20__1_xy3.pdf",ol:-7265.70,ot:8204.20,nl:-7142.41,nt:8083.99,nw:2126.57,nh:809.21},
{n:"nf10_off-target__20250402_ptk_yfpcdc20_22.pdf",ol:-7178.60,ot:4305.00,nl:-7059.67,nt:4379.75,nw:1782.67,nh:1184.93},
{n:"nf10_1-sisterless-persistent-polar__20250402_ptk_yfpcdc20_2.pdf",ol:-7428.60,ot:6084.50,nl:-7297.17,nt:6070.27,nw:1222.93,nh:761.90},
{n:"G5_item4_hec1_timestrip_xy5.pdf",ol:-4724.00,ot:8101.10,nl:-4727.80,nt:7986.05,nw:1240.32,nh:1144.46},
{n:"G5_mad1_timestrip_20260310_ptk2_eyfp_mad1_14_aligned.pdf",ol:-6184.70,ot:6054.30,nl:-6115.47,nt:6041.59,nw:1200.33,nh:872.57},
{n:"G4_prepost_intensity.pdf",ol:-4659.20,ot:4888.80,nl:-4666.24,nt:4934.36,nw:1409.23,nh:1054.21},
{n:"nf9_3-sisterless__20260417_ptk2_eyfp_cdc20_ablation_18.pdf",ol:-7290.30,ot:5044.80,nl:-4575.00,nt:6815.00,nw:2056.28,nh:896.42}
];
app.userInteractionLevel=UserInteractionLevel.DONTDISPLAYALERTS;
var doc=app.open(new File(AIP));
var done=0,miss=0;
function baseName(s){var i=s.lastIndexOf("/");return i<0?s:s.substring(i+1);}
for (var k=0;k<T.length;k++){
  var t=T[k],hit=null;
  for (var i=0;i<doc.placedItems.length;i++){
    var it=doc.placedItems[i],f="";
    try{f=it.file?baseName(it.file.fsName):"";}catch(e){continue;}
    if(f!==t.n) continue;
    var b=it.visibleBounds;
    if(Math.abs(b[0]-t.ol)>2||Math.abs(b[1]-t.ot)>2) continue;
    hit=it;break;
  }
  if(!hit){miss++;beat("MISS "+t.n);continue;}
  hit.width=t.nw;hit.height=t.nh;hit.left=t.nl;hit.top=t.nt;done++;
}
beat("repositioned="+done+" missed="+miss);
doc.save();doc.close(SaveOptions.SAVECHANGES);
app.userInteractionLevel=UserInteractionLevel.DISPLAYALERTS;
"done="+done+" miss="+miss;
