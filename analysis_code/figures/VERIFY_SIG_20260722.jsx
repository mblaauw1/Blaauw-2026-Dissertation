#target illustrator
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var d = app.open(new File("/Volumes/4 MB/ablation_plots/_tmp_sig_20260722.ai"));
function lname(p){var f=null;try{f=p.file;}catch(e){}return f?decodeURI(f.name).replace(/\.[^.]+$/,""):"";}
var fig={}; var missing=0;
for(var i=0;i<d.placedItems.length;i++){
  var p=d.placedItems[i],n=lname(p),b;
  try{b=p.visibleBounds;}catch(e){continue;}
  if(n && !fig[n]) fig[n]=b;
  var fp=""; try{fp=p.file?p.file.fsName:"";}catch(e){}
  if(fp && !(new File(fp)).exists) missing++;
}
var floating=0, tot=0;
for(var i2=0;i2<d.pathItems.length;i2++){
  var q=d.pathItems[i2];
  if(!q.name || q.name.indexOf("SIGHILITE")!==0) continue;
  tot++;
  var t=q.name.replace(/^SIGHILITE\s*/,""), fb=fig[t];
  if(!fb){ floating++; continue; }
  var b; try{b=q.visibleBounds;}catch(e){continue;}
  var l=Math.max(fb[0],b[0]),r=Math.min(fb[2],b[2]),tp=Math.min(fb[1],b[1]),bo=Math.max(fb[3],b[3]);
  var ia=(r>l&&tp>bo)?(r-l)*(tp-bo):0, ba=(b[2]-b[0])*(b[1]-b[3]);
  if(!(ba>0 && ia>0.5*ba)) floating++;
}
var res="placedItems="+d.placedItems.length+" artboards="+d.artboards.length+
        " textFrames="+d.textFrames.length+" missingLinks="+missing+
        " | SIGHILITE total="+tot+" still floating/detached="+floating;
d.close(SaveOptions.DONOTSAVECHANGES);
res;
