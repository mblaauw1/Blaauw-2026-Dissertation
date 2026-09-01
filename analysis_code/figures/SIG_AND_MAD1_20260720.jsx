#target illustrator
// Relink the fixed Hec1/Mad1 dot-quant (bg-subtracted, no negative Mad1) + refresh SIG_HIGHLIGHT with the
// expanded significant-plot set (29, excludes retired v1 phase-split). Backgrounded, non-PDF save.
app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
var COPY="/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
var PDF="/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/";
var d=null; for(var q=0;q<app.documents.length;q++){if(app.documents[q].name=="ablation_figures_grouped copy.ai"){d=app.documents[q];break;}}
var opened=false; if(!d){d=app.open(new File(COPY));opened=true;}
var rep=[];
function baseOf(pi){var f=null;try{f=pi.file;}catch(e){}if(!f)return null;return decodeURI(f.name).toLowerCase().replace(/\.(pdf|png|svg)$/,"");}
function findAll(base){base=base.toLowerCase();var o=[];for(var i=0;i<d.placedItems.length;i++){if(baseOf(d.placedItems[i])==base)o.push(d.placedItems[i]);}return o;}
// relink the mad1 dot-quant (it's a direct PNG placement in group4/)
var HEC="G5_hec1_mad1_dot_quant";
var pngf=new File("/Volumes/4 MB/ablation_figures_20260625/group4/G5_hec1_mad1_dot_quant.png");
var cs=findAll(HEC); for(var i=0;i<cs.length;i++){ if(pngf.exists){ try{cs[i].file=pngf;}catch(e){}} }
rep.push("relinked "+cs.length+" copies of "+HEC);
// expanded significance highlights
var SIG=["G1_start_rounded_metaphase","G1_start_rounded_vs_duration","G1_survival","G1_violin1_attempts_vs_duration",
"G2_dur_align_to_meta","G2_dur_align_to_meta_journal","G2_dur_ana_to_cyto","G2_dur_ana_to_cyto_journal",
"G2_dur_meta_to_ana","G2_dur_meta_to_ana_journal","G2_duration_combined","G2_metaphase_ablated_abltoana",
"G2_metaphase_dynamics_prometa","G2_phase_split_violin_v2","G2_phase_split_violin_v2_journal",
"G2_phase_split_violin_v2_tripledouble","G2_phase_split_violin_v2_tripledouble_journal","G2_prometa_combined_123",
"G2_prometa_combined_13","G3_kk_distance_vs_time_to_meta","G4_congression_score_sum_vs_duration",
"G4_congression_score_vs_duration","G4_polar_lagging_vs_duration","G4_sisbehav_fracjoined_vs_duration",
"G4_sisbehav_lastcongress_vs_duration","G4_sisbehav_npolar_vs_duration","G4_sisbehav_swimmer",
"pole_to_plate_behavior_vs_duration","pole_to_plate_jointime_vs_duration"];
var hl=null; try{hl=d.layers.getByName("SIG_HIGHLIGHT");}catch(e){hl=d.layers.add();hl.name="SIG_HIGHLIGHT";}
for(var i=hl.pathItems.length-1;i>=0;i--){try{hl.pathItems[i].remove();}catch(e){}}
hl.zOrder(ZOrderMethod.SENDTOBACK);
var yc=new RGBColor();yc.red=255;yc.green=238;yc.blue=120;var PAD=18,n=0;
for(var s=0;s<SIG.length;s++){ var cs2=findAll(SIG[s]);
  for(var j=0;j<cs2.length;j++){ var b=cs2[j].visibleBounds;
    var rr=hl.pathItems.roundedRectangle(b[1]+PAD,b[0]-PAD,(b[2]-b[0])+2*PAD,(b[1]-b[3])+2*PAD,14,14);
    rr.filled=true;rr.stroked=false;rr.fillColor=yc;rr.opacity=38;rr.name="SIGHILITE "+SIG[s];n++; } }
rep.push("highlighted "+n+" placements across "+SIG.length+" significant plots");
var so=new IllustratorSaveOptions();so.pdfCompatible=false;d.saveAs(new File(COPY),so);
if(opened){d.close(SaveOptions.DONOTSAVECHANGES);}
"DONE :: "+rep.join(" | ");
