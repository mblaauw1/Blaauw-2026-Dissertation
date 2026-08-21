#target illustrator
// The one broken placement is G3_length_spread_vs_metaphase_duration -- a figure a previous session
// deliberately did NOT rebuild (its metric definition is unknown; guessing was refused). Its two
// honest replacements (SD / max-min) are already placed on the same artboard, so the broken frame
// and its caption are removed rather than filled with a guess.
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch(e){}
var COPY="/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
while (app.documents.length>0){ app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var d=app.open(new File(COPY));
var kill=[], cap=null, bb=null;
for (var i=0;i<d.placedItems.length;i++){
  var pi=d.placedItems[i]; var ok=false;
  try{ ok=(pi.file!=null)&&pi.file.exists; }catch(e){ ok=false; }
  if(!ok){ try{ bb=pi.visibleBounds; }catch(e){} kill.push(pi); }
}
for (var i=0;i<d.textFrames.length;i++){
  var tf=d.textFrames[i]; var b; try{b=tf.visibleBounds;}catch(e){continue;}
  if(bb && Math.abs(b[0]-bb[0])<10 && b[3]-bb[1]>=-2 && b[3]-bb[1]<40){ cap=tf; }
}
var n=kill.length; for (var i=0;i<kill.length;i++){ try{kill[i].remove();}catch(e){} }
var c=0; if(cap){ try{ cap.remove(); c=1; }catch(e){} }
var opt=new IllustratorSaveOptions(); opt.pdfCompatible=false;
d.saveAs(new File(COPY), opt);
"removed_broken="+n+" removed_caption="+c+" placed="+d.placedItems.length;
