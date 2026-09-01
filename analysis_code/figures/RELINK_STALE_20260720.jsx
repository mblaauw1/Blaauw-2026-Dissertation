#target illustrator
app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
var COPY="/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
var PDF="/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/";
var d=null; for(var q=0;q<app.documents.length;q++){if(app.documents[q].name=="ablation_figures_grouped copy.ai"){d=app.documents[q];break;}}
var opened=false; if(!d){d=app.open(new File(COPY));opened=true;}
function baseOf(pi){var f=null;try{f=pi.file;}catch(e){}if(!f)return null;return decodeURI(f.name).toLowerCase().replace(/\.(pdf|png|svg)$/,"");}
var TARGETS=["G4_1sis_polar_lagging_duration", "G4_1sis_size_vs_outcome_metatime", "G4_cdc20_intensity_sanitycheck", "G4_distance_vs_fluor", "G4_distance_vs_fluor_paired", "G4_kt_intensity_diff", "G4_kt_intensity_polar_vs_plate", "G4_kt_intensity_time", "G4_kt_intensity_time_scaled01", "G4_kt_intensity_time_trendscaled", "G4_lagging_bar", "G4_lagging_count_vs_congression_time", "G4_lagging_vs_congression_fraction", "G4_neither_bar", "G4_oscillation_chronological", "G4_oscillation_tracking", "G4_oscillation_tracking_effective", "G4_plate_distance_chronological", "G4_plate_distance_time_normalized", "G4_plate_distance_time_normalized_trendscaled", "G4_plate_distance_tracking", "G4_plate_distance_tracking_trendscaled", "G4_polar_bar", "G4_polar_lagging_vs_duration", "G4_polar_lagging_vs_duration_byphase", "G5_hec1_mad1_dot_quant", "G5_item4_hec1_timestrip_xy2", "G5_item4_hec1_timestrip_xy4", "G5_item4_hec1_timestrip_xy5", "G5_item4_hec1_timestrip_xy6", "metaplate_rotation_by_sisterless"];
var tset={}; for(var i=0;i<TARGETS.length;i++) tset[TARGETS[i].toLowerCase()]=true;
var n=0; for(var i=0;i<d.placedItems.length;i++){var b=baseOf(d.placedItems[i]); if(b&&tset[b]){var f=new File(PDF+d.placedItems[i].file.name); if(f.exists){try{d.placedItems[i].file=f;n++;}catch(e){}}}}
var so=new IllustratorSaveOptions(); so.pdfCompatible=false; d.saveAs(new File(COPY),so);
if(opened){d.close(SaveOptions.DONOTSAVECHANGES);}
"RELINKED "+n+" of "+TARGETS.length;
