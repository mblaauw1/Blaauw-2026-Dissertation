#target illustrator
// The SIG_HIGHLIGHT layer holds one yellow box per figure, named "SIGHILITE <figure>". Moving 20 figures
// to the RETIRED artboard left their boxes behind, floating over nothing. This RE-ANCHORS each box onto
// its own figure (matching position and size), and moves boxes whose figure no longer exists in the
// document onto the RETIRED artboard rather than deleting them -- nothing is destroyed.
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var COPY="/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
var TMP ="/Volumes/4 MB/ablation_plots/_tmp_sig_20260722.ai";
var d = app.open(new File(COPY));
function lname(p){var f=null;try{f=p.file;}catch(e){}return f?decodeURI(f.name).replace(/\.[^.]+$/,""):"";}
var fig={};
for(var i=0;i<d.placedItems.length;i++){
  var p=d.placedItems[i],n=lname(p); if(!n) continue; var b;
  try{b=p.visibleBounds;}catch(e){continue;}
  if(!fig[n]) fig[n]=b;                      // first instance wins
}
var ri=-1;
for(var a=0;a<d.artboards.length;a++) if(d.artboards[a].name.toUpperCase().indexOf("RETIRED")>=0){ri=a;break;}
var R=d.artboards[ri].artboardRect;
var reanch=0, orph=0, ok=0, names=[];
var ox=R[0]+20, oy=R[3]+20;                  // parking strip for orphans, bottom-left of RETIRED
for(var i2=0;i2<d.pathItems.length;i2++){
  var q=d.pathItems[i2];
  if(!q.name || q.name.indexOf("SIGHILITE")!==0) continue;
  var target=q.name.replace(/^SIGHILITE\s*/,"");
  var fb=fig[target];
  var b; try{b=q.visibleBounds;}catch(e){continue;}
  if(!fb){ q.position=[ox,oy]; ox+=14; orph++; names.push("ORPHAN:"+target); continue; }
  // already sitting on its figure?
  var l=Math.max(fb[0],b[0]),r=Math.min(fb[2],b[2]),t=Math.min(fb[1],b[1]),bo=Math.max(fb[3],b[3]);
  var ia=(r>l&&t>bo)?(r-l)*(t-bo):0, ba=(b[2]-b[0])*(b[1]-b[3]);
  if(ba>0 && ia>0.5*ba){ ok++; continue; }
  // re-anchor: match the figure's box exactly
  q.width  = fb[2]-fb[0];
  q.height = fb[1]-fb[3];
  q.position=[fb[0],fb[1]];
  reanch++; names.push("REANCHORED:"+target);
}
var mode="";
try{var so=new IllustratorSaveOptions(); so.pdfCompatible=true; d.saveAs(new File(TMP), so); mode="ok";}
catch(e){ mode="SAVE_FAILED "+e; }
"already_on_figure="+ok+"  reanchored="+reanch+"  orphans_parked_on_RETIRED="+orph+"  save="+mode+
"\n"+names.join(" | ");
