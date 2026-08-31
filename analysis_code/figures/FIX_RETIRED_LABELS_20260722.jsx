#target illustrator
// Cosmetic: the rebuilt RETIRED stamps put their label on top of the figure's numbered caption.
// Move each label INSIDE its own red box, top-left, so both stay readable.
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch(e){}
var COPY="/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
while (app.documents.length>0){ app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var d=app.open(new File(COPY));
var lay=null; try{ lay=d.layers.getByName("RETIRED_MARKS"); }catch(e){}
if(!lay) { "no RETIRED_MARKS layer"; } else {
  var boxes=[], labels=[];
  for (var i=0;i<lay.pathItems.length;i++) boxes.push(lay.pathItems[i]);
  for (var i=0;i<lay.textFrames.length;i++) labels.push(lay.textFrames[i]);
  var n=0;
  for (var i=0;i<labels.length;i++){
    var t=labels[i], tb; try{tb=t.visibleBounds;}catch(e){continue;}
    var best=null, bd=1e9;
    for (var k=0;k<boxes.length;k++){
      var b=boxes[k].visibleBounds;
      var dx=Math.abs(((b[0]+b[2])/2)-((tb[0]+tb[2])/2)), dy=Math.abs(b[1]-tb[1]);
      if(dx+dy<bd){ bd=dx+dy; best=b; }
    }
    if(best){ t.position=[best[0]+5, best[1]-5]; n++; }
  }
  var opt=new IllustratorSaveOptions(); opt.pdfCompatible=false;
  d.saveAs(new File(COPY), opt);
  "retired labels repositioned="+n;
}
