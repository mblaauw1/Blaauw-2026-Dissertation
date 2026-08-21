// Place the new ZM timestrip on NEW_FIGURES, onto the same dated layer as the rest of today's work.
// Appended BELOW the existing band so it cannot overlap anything, and inside the measured canvas floor
// (-7475) so no artboard/placement error can be provoked. Item count must grow before saving.
#target illustrator
var TARGET="/Volumes/4 MB/1_DECKS/NEW_FIGURES_20260804.ai";
var PDF="/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/G6_period_by_definition_panels.pdf";
var LAYER="from edited 2026-08-10";
var log=[];
var doc=app.open(new File(TARGET)); app.activeDocument=doc;
var n0=doc.pageItems.length;
var lay=null;
for(var L=0;L<doc.layers.length;L++) if(doc.layers[L].name===LAYER){lay=doc.layers[L];break;}
if(!lay){ lay=doc.layers.add(); lay.name=LAYER; }
var minX=1e9,minY=1e9;
for(var i=0;i<doc.pageItems.length;i++){var b=doc.pageItems[i].visibleBounds; if(b[3]<minY)minY=b[3]; if(b[0]<minX)minX=b[0];}
log.push("items="+n0+" bottom="+minY.toFixed(0));
var f=new File(PDF);
if(!f.exists){ log.push("PDF MISSING"); doc.close(SaveOptions.DONOTSAVECHANGES); }
else {
  var it=doc.placedItems.add(); it.file=f;
  var w=it.width,h=it.height,s=Math.min(1400/w,700/h,1.0);
  it.width=w*s; it.height=h*s;
  var y=-5970;
  it.position=[3800, y];
  var t=doc.textFrames.add(); t.contents="G6_period_by_definition_panels";
  t.textRange.characterAttributes.size=13; t.position=[3800, y+22];
  try{ it.move(lay,ElementPlacement.PLACEATEND); t.move(lay,ElementPlacement.PLACEATEND);}catch(e){}
  log.push("placed at ["+minX.toFixed(0)+", "+y.toFixed(0)+"] size "+(w*s).toFixed(0)+"x"+(h*s).toFixed(0));
  log.push("items "+n0+" -> "+doc.pageItems.length);
  if(doc.pageItems.length<=n0){ log.push("ABORT: no growth; not saving"); doc.close(SaveOptions.DONOTSAVECHANGES); }
  else { var o=new IllustratorSaveOptions(); o.pdfCompatible=false; doc.saveAs(new File(TARGET),o); log.push("saved"); doc.close(SaveOptions.DONOTSAVECHANGES); }
}
var lf=new File("/Volumes/4 MB/_claude_tmp/place_grid0_report.txt"); lf.open("w"); lf.write(log.join("\n")); lf.close();
log.join("\n");
