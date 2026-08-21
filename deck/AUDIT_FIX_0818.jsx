// 2026-08-18 AUDIT FIX.
// (1) mirror the 7 new G8_* figures onto META_FIGURES_20260814_PUBLICATION.ai -- they were placed on the
//     LIVE deck yesterday but never onto its title-free copy, so the publication mirror was 7 short.
// (2) correct G4_lagging_bar's placed frame on BOTH decks: dropping the 2-Sister cohort made the figure
//     narrower, but the frame kept its old width, leaving the art ~3% stretched.
// Targets solved in Python from the verified dump and written here as literals.
#target illustrator
app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var HB=new File("/Volumes/4 MB/_claude_tmp/auditfix_heartbeat.txt");
function beat(m){try{HB.open("a");HB.writeln(m);HB.close();}catch(e){}}
function openDoc(p){ var d=app.open(new File(p)); beat("opened "+d.name); return d; }
function saveClose(d,p){ var o=new IllustratorSaveOptions(); o.pdfCompatible=false;
  d.saveAs(new File(p),o); beat("SAVED"); d.close(SaveOptions.DONOTSAVECHANGES); }
function resizeTo(doc,nm,L,T,W,H){
  for (var i=0;i<doc.pageItems.length;i++){
    var it=doc.pageItems[i];
    if (it.name!=nm) continue;
    var b=it.geometricBounds, w=b[2]-b[0], h=b[1]-b[3];
    it.resize((W/w)*100,(H/h)*100,true,true,true,true,100,Transformation.TOPLEFT);
    b=it.geometricBounds; it.translate(L-b[0],T-b[1]);
    beat("resized "+nm); return true;
  }
  beat("NOT FOUND "+nm); return false;
}
var PUBP="/Volumes/4 MB/1_DECKS/META_FIGURES_20260814_PUBLICATION.ai", LIVEP="/Volumes/4 MB/1_DECKS/META_FIGURES_20260814.ai";

// ---- publication deck: add the 7 mirrors, then fix G4_lagging_bar
var d = openDoc(PUBP);
var LAY="session_20260818";
var lay=null;
for (var i=0;i<d.layers.length;i++) if (d.layers[i].name==LAY) lay=d.layers[i];
if (lay==null){ lay=d.layers.add(); lay.name=LAY; }
lay.visible=true; lay.locked=false; d.activeLayer=lay;

(function(){
  for (var i=0;i<d.pageItems.length;i++) if (d.pageItems[i].name=="G8_metaphase_duration_model"){ beat("already present G8_metaphase_duration_model"); return; }
  var f=new File("/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf_pub/G8_metaphase_duration_model.pdf");
  if(!f.exists){ beat("MISSING PDF G8_metaphase_duration_model"); return; }
  var pi=lay.placedItems.add(); pi.file=f; pi.name="G8_metaphase_duration_model";
  var b=pi.geometricBounds, w=b[2]-b[0], h=b[1]-b[3];
  var s=Math.min(1079.8/w,651.8/h);
  pi.resize(s*100,s*100,true,true,true,true,s*100,Transformation.TOPLEFT);
  b=pi.geometricBounds; pi.translate(-7289.9-b[0],-189.9-b[1]);
  beat("mirrored G8_metaphase_duration_model");
})();

(function(){
  for (var i=0;i<d.pageItems.length;i++) if (d.pageItems[i].name=="G8_pooling_2plus3_vs_3"){ beat("already present G8_pooling_2plus3_vs_3"); return; }
  var f=new File("/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf_pub/G8_pooling_2plus3_vs_3.pdf");
  if(!f.exists){ beat("MISSING PDF G8_pooling_2plus3_vs_3"); return; }
  var pi=lay.placedItems.add(); pi.file=f; pi.name="G8_pooling_2plus3_vs_3";
  var b=pi.geometricBounds, w=b[2]-b[0], h=b[1]-b[3];
  var s=Math.min(820.0/w,456.2/h);
  pi.resize(s*100,s*100,true,true,true,true,s*100,Transformation.TOPLEFT);
  b=pi.geometricBounds; pi.translate(-5770.0-b[0],-1530.0-b[1]);
  beat("mirrored G8_pooling_2plus3_vs_3");
})();

(function(){
  for (var i=0;i<d.pageItems.length;i++) if (d.pageItems[i].name=="G8_kt_deformation_materialfits"){ beat("already present G8_kt_deformation_materialfits"); return; }
  var f=new File("/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf_pub/G8_kt_deformation_materialfits.pdf");
  if(!f.exists){ beat("MISSING PDF G8_kt_deformation_materialfits"); return; }
  var pi=lay.placedItems.add(); pi.file=f; pi.name="G8_kt_deformation_materialfits";
  var b=pi.geometricBounds, w=b[2]-b[0], h=b[1]-b[3];
  var s=Math.min(1108.5/w,320.0/h);
  pi.resize(s*100,s*100,true,true,true,true,s*100,Transformation.TOPLEFT);
  b=pi.geometricBounds; pi.translate(-1990.0-b[0],-1670.0-b[1]);
  beat("mirrored G8_kt_deformation_materialfits");
})();

(function(){
  for (var i=0;i<d.pageItems.length;i++) if (d.pageItems[i].name=="G8_polar_chromosome_angle"){ beat("already present G8_polar_chromosome_angle"); return; }
  var f=new File("/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf_pub/G8_polar_chromosome_angle.pdf");
  if(!f.exists){ beat("MISSING PDF G8_polar_chromosome_angle"); return; }
  var pi=lay.placedItems.add(); pi.file=f; pi.name="G8_polar_chromosome_angle";
  var b=pi.geometricBounds, w=b[2]-b[0], h=b[1]-b[3];
  var s=Math.min(1120.5/w,322.9/h);
  pi.resize(s*100,s*100,true,true,true,true,s*100,Transformation.TOPLEFT);
  b=pi.geometricBounds; pi.translate(-1990.0-b[0],-1290.0-b[1]);
  beat("mirrored G8_polar_chromosome_angle");
})();

(function(){
  for (var i=0;i<d.pageItems.length;i++) if (d.pageItems[i].name=="G8_kt_speed_paired_vs_sisterless"){ beat("already present G8_kt_speed_paired_vs_sisterless"); return; }
  var f=new File("/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf_pub/G8_kt_speed_paired_vs_sisterless.pdf");
  if(!f.exists){ beat("MISSING PDF G8_kt_speed_paired_vs_sisterless"); return; }
  var pi=lay.placedItems.add(); pi.file=f; pi.name="G8_kt_speed_paired_vs_sisterless";
  var b=pi.geometricBounds, w=b[2]-b[0], h=b[1]-b[3];
  var s=Math.min(900.0/w,347.9/h);
  pi.resize(s*100,s*100,true,true,true,true,s*100,Transformation.TOPLEFT);
  b=pi.geometricBounds; pi.translate(3570.0-b[0],-1630.0-b[1]);
  beat("mirrored G8_kt_speed_paired_vs_sisterless");
})();

(function(){
  for (var i=0;i<d.pageItems.length;i++) if (d.pageItems[i].name=="G8_lagging_fracture_timing"){ beat("already present G8_lagging_fracture_timing"); return; }
  var f=new File("/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf_pub/G8_lagging_fracture_timing.pdf");
  if(!f.exists){ beat("MISSING PDF G8_lagging_fracture_timing"); return; }
  var pi=lay.placedItems.add(); pi.file=f; pi.name="G8_lagging_fracture_timing";
  var b=pi.geometricBounds, w=b[2]-b[0], h=b[1]-b[3];
  var s=Math.min(1120.0/w,331.7/h);
  pi.resize(s*100,s*100,true,true,true,true,s*100,Transformation.TOPLEFT);
  b=pi.geometricBounds; pi.translate(-7290.0-b[0],-6950.0-b[1]);
  beat("mirrored G8_lagging_fracture_timing");
})();

(function(){
  for (var i=0;i<d.pageItems.length;i++) if (d.pageItems[i].name=="G8_lagging_fracture_materials"){ beat("already present G8_lagging_fracture_materials"); return; }
  var f=new File("/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf_pub/G8_lagging_fracture_materials.pdf");
  if(!f.exists){ beat("MISSING PDF G8_lagging_fracture_materials"); return; }
  var pi=lay.placedItems.add(); pi.file=f; pi.name="G8_lagging_fracture_materials";
  var b=pi.geometricBounds, w=b[2]-b[0], h=b[1]-b[3];
  var s=Math.min(820.0/w,319.0/h);
  pi.resize(s*100,s*100,true,true,true,true,s*100,Transformation.TOPLEFT);
  b=pi.geometricBounds; pi.translate(-6130.0-b[0],-6970.0-b[1]);
  beat("mirrored G8_lagging_fracture_materials");
})();
resizeTo(d,"G4_lagging_bar",-345.8,-43.3,1067.1,638.4);
saveClose(d,PUBP);

// ---- live deck: G4_lagging_bar aspect only
var d2 = openDoc(LIVEP);
resizeTo(d2,"G4_lagging_bar",-345.6,-42.9,1066.7,682.4);
saveClose(d2,LIVEP);
beat("DONE");