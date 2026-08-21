#target illustrator
// copy.ai re-layout: one numbered caption per figure, directly above it; artboards shelf-packed;
// significance / revived boxes re-anchored; empty artboards removed.
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch(e){}
function readFile(p){ var f=new File(p); f.encoding="UTF-8"; f.open("r"); var s=f.read(); f.close(); return s; }
var P = eval("("+readFile("/Volumes/4 MB/_scratch/copyai_relayout.json")+")");
var COPY="/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
while (app.documents.length>0){ app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var d=app.open(new File(COPY));
function near(a,b,t){ return Math.abs(a[0]-b[0])<t&&Math.abs(a[1]-b[1])<t&&Math.abs(a[2]-b[2])<t&&Math.abs(a[3]-b[3])<t; }
var log=[];

// ---------- 1. resolve every reference BEFORE moving anything ----------
var mv=[];                      // {obj,nb}
for (var i=0;i<d.placedItems.length;i++){
  var pi=d.placedItems[i]; var fp=""; try{fp=decodeURI(pi.file.fsName);}catch(e){}
  var b; try{b=pi.visibleBounds;}catch(e){continue;}
  for (var k=0;k<P.items.length;k++){ var t=P.items[k];
    if(t.done) continue;
    if(fp==t.file && near(b,t.ob,1.0)){ mv.push({o:pi,nb:t.nb}); t.done=true; break; } }
}
var unm=0; for (var k=0;k<P.items.length;k++){ if(!P.items[k].done) unm++; }
log.push("items_matched="+mv.length+" unmatched="+unm);

var killT=[], moveT=[];
for (var i=0;i<d.textFrames.length;i++){
  var tf=d.textFrames[i]; var b; try{b=tf.visibleBounds;}catch(e){continue;}
  var hit=false;
  for (var k=0;k<P.drop_texts.length;k++){ var t=P.drop_texts[k]; if(t.done) continue;
    if(near(b,t.ob,1.0)){ killT.push(tf); t.done=true; hit=true; break; } }
  if(hit) continue;
  for (var k=0;k<P.head.length;k++){ var t=P.head[k]; if(t.done) continue;
    if(near(b,t.ob,1.0)){ moveT.push({o:tf,p:t.pos}); t.done=true; hit=true; break; } }
  if(hit) continue;
  for (var k=0;k<P.keep.length;k++){ var t=P.keep[k]; if(t.done) continue;
    if(near(b,t.ob,1.0)){ moveT.push({o:tf,p:t.pos}); t.done=true; break; } }
}
log.push("texts_drop="+killT.length+" texts_move="+moveT.length);

var mvBox=[];
for (var i=0;i<d.pathItems.length;i++){
  var p=d.pathItems[i]; var nm=""; try{nm=p.name;}catch(e){}
  if(!nm) continue;
  for (var k=0;k<P.boxes.length;k++){ var t=P.boxes[k]; if(t.done) continue;
    if(nm==t.name && t.nb){ mvBox.push({o:p,nb:t.nb}); t.done=true; break; } }
}
log.push("boxes_matched="+mvBox.length);

// ---------- 2. apply ----------
for (var i=0;i<killT.length;i++){ try{ killT[i].remove(); }catch(e){} }
for (var i=0;i<mv.length;i++){
  var o=mv[i].o, nb=mv[i].nb;
  try{ o.width=nb[2]-nb[0]; o.height=nb[1]-nb[3]; o.position=[nb[0],nb[1]]; }catch(e){}
}
for (var i=0;i<moveT.length;i++){ try{ moveT[i].o.position=moveT[i].p; }catch(e){} }
for (var i=0;i<mvBox.length;i++){
  var o=mvBox[i].o, nb=mvBox[i].nb;
  try{ o.width=nb[2]-nb[0]; o.height=nb[1]-nb[3]; o.position=[nb[0],nb[1]]; }catch(e){}
}

// ---------- 3. fresh captions ----------
var capLayer;
try{ capLayer=d.layers.getByName("PLOT_LABELS"); }catch(e){ capLayer=d.layers.add(); capLayer.name="PLOT_LABELS"; }
var ncap=0;
for (var i=0;i<P.caps.length;i++){
  try{
    var tf=capLayer.textFrames.add();
    tf.contents=P.caps[i].txt;
    tf.textRange.characterAttributes.size=9;
    tf.position=[P.caps[i].pos[0], P.caps[i].pos[1]];
    ncap++;
  }catch(e){}
}
log.push("captions_added="+ncap);

// ---------- 4. artboards ----------
var want=P.artboards.length;
// set the rects of the artboards we keep (P.artboards[].i is the ORIGINAL index)
for (var k=0;k<P.artboards.length;k++){
  var pa=P.artboards[k];
  try{ d.artboards[pa.i].artboardRect=pa.rect; }catch(e){}
}
// delete artboards that hold no figures (their content moved to arranged_into_paper_figures_2.ai)
var keepIdx={}; for (var k=0;k<P.artboards.length;k++){ keepIdx[P.artboards[k].i]=1; }
var ndel=0;
for (var a=d.artboards.length-1;a>=0;a--){
  if(!keepIdx[a]){ try{ d.artboards.remove(a); ndel++; }catch(e){} }
}
log.push("artboards_kept="+want+" removed="+ndel);

var opt=new IllustratorSaveOptions(); opt.pdfCompatible=false;
d.saveAs(new File(COPY), opt);
log.push("saved placed="+d.placedItems.length+" text="+d.textFrames.length+" abs="+d.artboards.length);
log.join(" | ");
