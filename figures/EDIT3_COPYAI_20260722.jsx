#target illustrator
// copy.ai edit pass 3: relink the one broken link, re-stamp the RETIRED marks onto the retired
// figures' new positions, pull the last 3 stray labels back onto an artboard.
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch(e){}
function readFile(p){ var f=new File(p); f.encoding="UTF-8"; f.open("r"); var s=f.read(); f.close(); return s; }
var P = eval("("+readFile("/Volumes/4 MB/_scratch/copyai_edit3.json")+")");
var COPY="/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
while (app.documents.length>0){ app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var d=app.open(new File(COPY));
function near(a,b,t){ return Math.abs(a[0]-b[0])<t&&Math.abs(a[1]-b[1])<t&&Math.abs(a[2]-b[2])<t&&Math.abs(a[3]-b[3])<t; }
var log=[];

// ---- 1. relink the broken placement ----
var done=0;
for (var i=0;i<d.placedItems.length;i++){
  var pi=d.placedItems[i]; var b; try{b=pi.visibleBounds;}catch(e){continue;}
  var ok=true; try{ ok = pi.file && pi.file.exists; }catch(e){ ok=false; }
  if(ok) continue;
  if(near(b,P.relink.b,2.0)){
    var f=new File(P.relink.file);
    if(f.exists){ pi.file=f; pi.width=P.relink.b[2]-P.relink.b[0]; pi.height=P.relink.b[1]-P.relink.b[3];
      pi.position=[P.relink.b[0],P.relink.b[1]]; pi.name=P.relink.base; done++; }
  }
}
log.push("relinked="+done);

// ---- 2. rebuild the RETIRED stamps ----
var lay=null;
try{ lay=d.layers.getByName("RETIRED_MARKS"); }catch(e){}
var nrm=0;
if(lay){
  for (var i=lay.pageItems.length-1;i>=0;i--){ try{ lay.pageItems[i].remove(); nrm++; }catch(e){} }
} else { lay=d.layers.add(); lay.name="RETIRED_MARKS"; }
var red=new RGBColor(); red.red=220; red.green=30; red.blue=30;
var nst=0;
for (var k=0;k<P.stamps.length;k++){
  var b=P.stamps[k].b;
  try{
    var r=lay.pathItems.rectangle(b[1]+4, b[0]-4, (b[2]-b[0])+8, (b[1]-b[3])+8);
    r.filled=false; r.stroked=true; r.strokeColor=red; r.strokeWidth=2;
    var tf=lay.textFrames.add(); tf.contents="RETIRED";
    tf.textRange.characterAttributes.size=11;
    tf.textRange.characterAttributes.fillColor=red;
    tf.position=[b[0], b[1]+22];
    nst++;
  }catch(e){}
}
log.push("stamps_removed="+nrm+" stamps_added="+nst);

// ---- 3. stray labels back onto an artboard ----
var nmv=0;
for (var i=0;i<d.textFrames.length;i++){
  var tf=d.textFrames[i]; var b; try{b=tf.visibleBounds;}catch(e){continue;}
  for (var k=0;k<P.offtexts.length;k++){ var t=P.offtexts[k]; if(t.done) continue;
    if(near(b,t.ob,1.5)){ tf.position=[t.pos[0],t.pos[1]]; t.done=true; nmv++; break; } }
}
log.push("stray_labels_moved="+nmv);

var opt=new IllustratorSaveOptions(); opt.pdfCompatible=false;
d.saveAs(new File(COPY), opt);
log.push("saved placed="+d.placedItems.length+" text="+d.textFrames.length+" abs="+d.artboards.length);
log.join(" | ");
