#target illustrator
// Stage the 7 recent figures that are in the PDF deck but missing from copy.ai.
// Adds them as NEW linked placements below all artwork, labeled. Suppresses modal dialogs (which hung
// prior runs) and saves NON-PDF-compatible so the deck drops back to ~7MB and saves fast.
app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
var COPY="/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
var P="/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/";
var F=[
 "single_sisterless_length_congression.pdf",
 "metaphase_duration_delta_from_unmodified.pdf",
 "triple_prometa_ablation_to_mitosis.pdf",
 "ablation_count_by_cohort.pdf",
 "ablation_count_on_vs_offpooled.pdf",
 "G4_zm_by_target.pdf",
 "20250501_ptk_yfpcdc20_12_frap0.pdf"
];
var d=null;
for (var q=0;q<app.documents.length;q++){ if(app.documents[q].name=="ablation_figures_grouped copy.ai"){ d=app.documents[q]; break; } }
var opened=false; if(!d){ d=app.open(new File(COPY)); opened=true; }
var lyr=d.activeLayer;
// basenames already present (stem, extension-agnostic) -> skip
var have={};
for (var i=0;i<d.placedItems.length;i++){ var f=null; try{f=d.placedItems[i].file;}catch(e){}
  if(f) have[decodeURI(f.name).toLowerCase().replace(/\.(pdf|png|svg)$/,"")]=true; }
// bounding box -> stage BELOW all artwork
var gb=null, it=d.pageItems;
for (var i=0;i<it.length;i++){ var b; try{b=it[i].visibleBounds;}catch(e){continue;}
  if(!gb) gb=[b[0],b[1],b[2],b[3]];
  else { if(b[0]<gb[0])gb[0]=b[0]; if(b[1]>gb[1])gb[1]=b[1]; if(b[2]>gb[2])gb[2]=b[2]; if(b[3]<gb[3])gb[3]=b[3]; } }
var left=gb?gb[0]:0, bottom=gb?gb[3]:0;
var STAGE_TOP=bottom-700, CW=470.0, CH=430.0, M=16.0, CAPH=26.0, COLS=4;
var added=0, missing=[], skipped=[];
for (var i=0;i<F.length;i++){
  var stem=F[i].toLowerCase().replace(/\.pdf$/,"");
  if(have[stem]){ skipped.push(F[i]); continue; } have[stem]=true;
  var file=new File(P+F[i]);
  if(!file.exists){ missing.push(F[i]); continue; }
  var col=added%COLS, row=Math.floor(added/COLS);
  var x0=left+col*CW, top=STAGE_TOP-row*CH;
  var pi=lyr.placedItems.add(); pi.file=file;
  var sc=Math.min((CW-2*M)/pi.width, (CH-CAPH-2*M)/pi.height);
  pi.width=pi.width*sc; pi.height=pi.height*sc;
  pi.position=[x0+(CW-pi.width)/2, top-M]; pi.name="NEW "+F[i];
  var tf=lyr.textFrames.add(); tf.contents=F[i].replace(/\.pdf$/i,"");
  tf.textRange.characterAttributes.size=11; tf.position=[x0+M, top-(CH-CAPH+8)];
  added++;
}
if(added>0){ var hd=lyr.textFrames.add();
  hd.contents="↓↓  "+added+" figure(s) from the PDF deck, added to copy.ai — drag into their group  ↓↓";
  hd.textRange.characterAttributes.size=26; hd.position=[left, STAGE_TOP+90]; }
var so=new IllustratorSaveOptions(); so.pdfCompatible=false;
d.saveAs(new File(COPY), so);
if(opened){ d.close(SaveOptions.DONOTSAVECHANGES); }
"added="+added+"  skipped_present="+skipped.length+"  missing_file="+missing.length+(missing.length?(" :: "+missing.join(" | ")):"");
