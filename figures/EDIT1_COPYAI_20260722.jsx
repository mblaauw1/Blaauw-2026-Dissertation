#target illustrator
// copy.ai edit pass 1:
//  - delete the 64 manual paper-figure copies (now living in arranged_into_paper_figures_2.ai) + their 12 labels
//  - delete one exact-duplicate frap_candidates (identical bounds, stacked)
//  - place a base copy of the 10 figures that existed ONLY as manual copies
//  - move G4_zm_by_target(+_zoom) onto AB31 RETIRED
//  - move the orphan G4_1sis_size_vs_outcome_metatime tag next to its figure
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch(e){}
function readFile(p){ var f=new File(p); f.encoding="UTF-8"; f.open("r"); var s=f.read(); f.close(); return s; }
var plan = eval("("+readFile("/Volumes/4 MB/_scratch/copyai_edit1.json")+")");
var COPY="/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
while (app.documents.length>0){ app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var d=app.open(new File(COPY));

function near(a,b,tol){ return Math.abs(a[0]-b[0])<tol&&Math.abs(a[1]-b[1])<tol&&Math.abs(a[2]-b[2])<tol&&Math.abs(a[3]-b[3])<tol; }
var log=[];

// ---- delete placed items ----
var toKill=[];
for (var i=0;i<d.placedItems.length;i++){
  var pi=d.placedItems[i]; var fp=""; try{fp=decodeURI(pi.file.fsName);}catch(e){}
  var b; try{b=pi.visibleBounds;}catch(e){continue;}
  for (var k=0;k<plan.delete_items.length;k++){
    var t=plan.delete_items[k];
    if(t.done) continue;
    if(fp==t.file && near(b,t.b,1.0)){ toKill.push(pi); t.done=true; break; }
  }
}
var ndel=toKill.length;
for (var i=0;i<toKill.length;i++){ try{ toKill[i].remove(); }catch(e){} }
var unmatched=0; for (var k=0;k<plan.delete_items.length;k++){ if(!plan.delete_items[k].done) unmatched++; }
log.push("deleted_items="+ndel+" unmatched="+unmatched);

// ---- delete their text labels ----
var killT=[];
for (var i=0;i<d.textFrames.length;i++){
  var tf=d.textFrames[i]; var b; try{b=tf.visibleBounds;}catch(e){continue;}
  var c=""; try{c=tf.contents;}catch(e){}
  for (var k=0;k<plan.delete_texts.length;k++){
    var t=plan.delete_texts[k]; if(t.done) continue;
    if(near(b,t.b,1.0)){ killT.push(tf); t.done=true; break; }
  }
}
var ndt=killT.length;
for (var i=0;i<killT.length;i++){ try{ killT[i].remove(); }catch(e){} }
log.push("deleted_texts="+ndt);

// ---- place the 10 orphan bases ----
var nplaced=0, perr=[];
for (var k=0;k<plan.place.length;k++){
  var p=plan.place[k];
  var f=new File(p.file);
  if(!f.exists){ perr.push(p.base+"(nofile)"); continue; }
  var r=plan.artboards[p.ab];
  try{
    var pi=d.placedItems.add(); pi.file=f;
    pi.width=p.w; pi.height=p.h;
    pi.position=[r[0]+20+ (k%4)*(p.w+20), r[1]-30];
    pi.name=p.base; nplaced++;
  }catch(e){ perr.push(p.base+"::"+e); }
}
log.push("placed="+nplaced+(perr.length?(" perr="+perr.join(",")):""));

// ---- retire zm_by_target to AB31 ----
var ab31=plan.ab31, nret=0, slot=0;
for (var i=0;i<d.placedItems.length;i++){
  var pi=d.placedItems[i]; var fp=""; try{fp=decodeURI(pi.file.fsName);}catch(e){}
  var b; try{b=pi.visibleBounds;}catch(e){continue;}
  for (var k=0;k<plan.retire.length;k++){
    var t=plan.retire[k]; if(t.done) continue;
    if(fp==t.file && near(b,t.b,1.0)){
      var w=b[2]-b[0], h=b[1]-b[3];
      var sc = Math.min(210/w, 150/h, 1);
      pi.width=w*sc; pi.height=h*sc;
      pi.position=[ab31[0]+20+slot*230, ab31[3]+200];
      slot++; nret++; t.done=true; break;
    }
  }
}
log.push("retired_to_AB31="+nret);

// ---- move the stray tag ----
var moved=0;
for (var i=0;i<d.textFrames.length;i++){
  var tf=d.textFrames[i]; var b; try{b=tf.visibleBounds;}catch(e){continue;}
  if(near(b,plan.tag.old,2.0)){ tf.position=[plan.tag["new"][0], plan.tag["new"][1]]; moved++; break; }
}
log.push("tag_moved="+moved);

var opt=new IllustratorSaveOptions(); opt.pdfCompatible=false;
d.saveAs(new File(COPY), opt);
log.push("saved placed_now="+d.placedItems.length+" text_now="+d.textFrames.length);
log.join(" | ");
