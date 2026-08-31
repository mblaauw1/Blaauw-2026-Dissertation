#target illustrator
// Close the empty band on the "Custom analyses" artboard: the 10 zoom companions were placed in a
// detached block below the real content, which reads as "figures floating at the bottom left, not on
// an artboard" (user 2026-07-23). They ARE on the artboard; the gap is what made them look orphaned.
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch(e){}
function readFile(p){ var f=new File(p); f.encoding="UTF-8"; f.open("r"); var s=f.read(); f.close(); return s; }
var P = eval("("+readFile("/Volumes/4 MB/_scratch/copyai_edit5.json")+")");
var COPY="/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
while (app.documents.length>0){ app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var d=app.open(new File(COPY));
function near(a,b,t){ return Math.abs(a[0]-b[0])<t&&Math.abs(a[1]-b[1])<t&&Math.abs(a[2]-b[2])<t&&Math.abs(a[3]-b[3])<t; }
var log=[], mv=[], mt=[], mbox=[];

for (var i=0;i<d.placedItems.length;i++){
  var pi=d.placedItems[i], b; try{b=pi.visibleBounds;}catch(e){continue;}
  for (var k=0;k<P.items.length;k++){ var t=P.items[k]; if(t.done) continue;
    if(near(b,t.ob,1.0)){ mv.push({o:pi,nb:t.nb,base:t.base}); t.done=true; break; } }
}
for (var i=0;i<d.textFrames.length;i++){
  var tf=d.textFrames[i], b; try{b=tf.visibleBounds;}catch(e){continue;}
  for (var k=0;k<P.caps.length;k++){ var t=P.caps[k]; if(t.done) continue;
    if(near(b,t.ob,1.0)){ mt.push({o:tf,p:t.pos}); t.done=true; break; } }
}
// any highlight panel anchored to a moved figure travels with it
for (var i=0;i<d.pathItems.length;i++){
  var p=d.pathItems[i], nm=""; try{ nm=p.name||""; }catch(e){}
  for (var k=0;k<P.items.length;k++){
    if(nm.indexOf(P.items[k].base)>=0){ mbox.push({o:p,dy:P.shift}); break; }
  }
}
for (var i=0;i<mv.length;i++){ var o=mv[i].o, nb=mv[i].nb;
  try{ o.position=[nb[0], nb[1]]; }catch(e){} }
for (var i=0;i<mt.length;i++){ try{ mt[i].o.position=[mt[i].p[0], mt[i].p[1]]; }catch(e){} }
for (var i=0;i<mbox.length;i++){ try{ mbox[i].o.translate(0, mbox[i].dy); }catch(e){} }
log.push("figures_moved="+mv.length+" captions_moved="+mt.length+" panels_moved="+mbox.length);

for (var a=0;a<d.artboards.length;a++){
  if(d.artboards[a].name.indexOf("Custom analyses")>=0){
    try{ d.artboards[a].artboardRect=P.artboard.rect; log.push("artboard_resized"); }catch(e){ log.push("resize_failed:"+e); }
    break;
  }
}
var opt=new IllustratorSaveOptions(); opt.pdfCompatible=false;
d.saveAs(new File(COPY), opt);
log.push("saved placed="+d.placedItems.length);
log.join(" | ");
