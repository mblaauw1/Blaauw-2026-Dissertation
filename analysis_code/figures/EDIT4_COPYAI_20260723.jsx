#target illustrator
// copy.ai edit pass 4 (user 2026-07-22/23):
//  - a BLUE panel behind every model-creation figure, the same idea as the yellow significance panels
//  - the yellow SIGHILITE panels only showed a 6pt margin around their figure, so they read as "gone";
//    widened to 16pt each side so they are visible again
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch(e){}
function readFile(p){ var f=new File(p); f.encoding="UTF-8"; f.open("r"); var s=f.read(); f.close(); return s; }
var P = eval("("+readFile("/Volumes/4 MB/_scratch/copyai_edit4.json")+")");
var COPY="/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
while (app.documents.length>0){ app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var d=app.open(new File(COPY));
var log=[];

// ---- 1. widen the yellow panels ----
var sig=null; try{ sig=d.layers.getByName("SIG_HIGHLIGHT"); }catch(e){}
var widened=0;
if(sig){
  var M=P.yellow_margin;
  for (var i=0;i<sig.pathItems.length;i++){
    var p=sig.pathItems[i], nm=p.name||"";
    if(nm.indexOf("SIGHILITE ")!==0) continue;
    var base=nm.substring(10);
    // find that figure and re-fit the panel around it
    for (var k=0;k<d.placedItems.length;k++){
      var pi=d.placedItems[k], b;
      try{ if(decodeURI(pi.file.name).replace(/\.(pdf|png|svg)$/i,"")!==base) continue; }catch(e){ continue; }
      try{ b=pi.visibleBounds; }catch(e){ continue; }
      try{
        p.width=(b[2]-b[0])+2*M; p.height=(b[1]-b[3])+2*M;
        p.position=[b[0]-M, b[1]+M];
        widened++;
      }catch(e){}
      break;
    }
  }
}
log.push("yellow_panels_widened="+widened);

// ---- 2. blue panels behind the model figures ----
var blue=null;
try{ blue=d.layers.getByName("MODEL_HIGHLIGHT"); }catch(e){ blue=d.layers.add(); blue.name="MODEL_HIGHLIGHT"; }
for (var i=blue.pageItems.length-1;i>=0;i--){ try{ blue.pageItems[i].remove(); }catch(e){} }
var col=new RGBColor(); col.red=150; col.green=200; col.blue=255;
var nb=0;
for (var k=0;k<P.blue.length;k++){
  var t=P.blue[k], b=t.b;
  try{
    var r=blue.pathItems.rectangle(b[1], b[0], b[2]-b[0], b[1]-b[3]);
    r.filled=true; r.fillColor=col; r.stroked=false; r.name=t.name;
    nb++;
  }catch(e){}
}
// the highlight layers must sit BEHIND the figures
try{ blue.zOrder(ZOrderMethod.SENDTOBACK); }catch(e){}
try{ if(sig) sig.zOrder(ZOrderMethod.SENDTOBACK); }catch(e){}
log.push("blue_model_panels="+nb);

var opt=new IllustratorSaveOptions(); opt.pdfCompatible=false;
d.saveAs(new File(COPY), opt);
log.push("saved placed="+d.placedItems.length+" abs="+d.artboards.length);
log.join(" | ");
