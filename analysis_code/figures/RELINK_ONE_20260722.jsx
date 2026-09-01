#target illustrator
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch(e){}
var COPY="/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
while (app.documents.length>0){ app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var d=app.open(new File(COPY));
var PDF=new File("/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/G3_length_spread_vs_metaphase_duration.pdf");
var n=0, info=[];
for (var i=0;i<d.placedItems.length;i++){
  var pi=d.placedItems[i]; var ok=false;
  try{ ok = (pi.file!=null) && pi.file.exists; }catch(e){ ok=false; }
  if(ok) continue;
  var b; try{b=pi.visibleBounds;}catch(e){ b=[0,0,0,0]; }
  info.push("["+Math.round(b[0])+","+Math.round(b[1])+","+Math.round(b[2])+","+Math.round(b[3])+"]");
  if(PDF.exists){ try{ pi.file=PDF; pi.width=b[2]-b[0]; pi.height=b[1]-b[3]; pi.position=[b[0],b[1]];
    pi.name="G3_length_spread_vs_metaphase_duration"; n++; }catch(e){ info.push("ERR:"+e); } }
}
var opt=new IllustratorSaveOptions(); opt.pdfCompatible=false;
if(n>0) d.saveAs(new File(COPY), opt);
"broken="+info.join(" ")+" relinked="+n;
