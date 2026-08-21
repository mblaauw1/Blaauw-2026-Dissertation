#target illustrator
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var d = app.open(new File("/Volumes/4 MB/ablation_plots/_tmp_retire_20260722.ai"));
var missing=0, off=0;
var ri=-1;
for (var a=0;a<d.artboards.length;a++) if(d.artboards[a].name.toUpperCase().indexOf("RETIRED")>=0){ri=a;break;}
var R=d.artboards[ri].artboardRect, onret=0, outside=0;
for (var i=0;i<d.placedItems.length;i++){
  var p=d.placedItems[i], fp="";
  try{ fp = p.file ? p.file.fsName : ""; }catch(e){ continue; }
  if (fp && !(new File(fp)).exists) missing++;
  var b; try{b=p.visibleBounds;}catch(e){continue;}
  var cx=(b[0]+b[2])/2, cy=(b[1]+b[3])/2;
  if(cx>=R[0]&&cx<=R[2]&&cy<=R[1]&&cy>=R[3]){
    onret++;
    if(b[0]<R[0]-1||b[2]>R[2]+1||b[1]>R[1]+1||b[3]<R[3]-1) outside++;
  }
}
var res="placedItems="+d.placedItems.length+" artboards="+d.artboards.length+
        " textFrames="+d.textFrames.length+" layers="+d.layers.length+
        " missingLinks="+missing+" | RETIRED AB"+(ri+1)+": "+onret+" items, "+outside+" spilling past its edges";
d.close(SaveOptions.DONOTSAVECHANGES);
res;
