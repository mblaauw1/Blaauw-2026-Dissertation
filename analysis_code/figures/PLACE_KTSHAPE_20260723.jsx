#target illustrator
// Place the 17 NEW kinetochore-shape figures into a NEW artboard in the free region right of AB28
// (rect is WITHIN the existing canvas bounds -> no CoOA/Error 1200). Aspect preserved per PDF.
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch(e){}
function readFile(p){ var f=new File(p); f.encoding="UTF-8"; f.open("r"); var s=f.read(); f.close(); return s; }
var P = eval("("+readFile("/Volumes/4 MB/_scratch/place_ktshape.json")+")");
var COPY="/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
while (app.documents.length>0){ app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var d=app.open(new File(COPY));
var ab = d.artboards.add(P.new_artboard.rect);
ab.name = P.new_artboard.name;
var lay; try{ lay=d.layers.getByName("PLOT_LABELS"); }catch(e){ lay=d.layers.add(); lay.name="PLOT_LABELS"; }
var tt=lay.textFrames.add(); tt.contents=P.title.txt;
try{ tt.textRange.characterAttributes.size=18; }catch(e){}
tt.position=[P.title.pos[0],P.title.pos[1]];
var n=0, errs=[];
for (var i=0;i<P.items.length;i++){
  var it=P.items[i]; var f=new File(it.file);
  if(!f.exists){ errs.push(it.base+"::missing"); continue; }
  try{ var pi=d.placedItems.add(); pi.file=f;
    var ratio = pi.height/pi.width;          // native aspect BEFORE resizing
    pi.width = it.w; pi.height = it.w*ratio;
    pi.position=[it.x, it.y];                // top-left
    pi.name=it.base; n++; }catch(e){ errs.push(it.base+"::"+e); }
}
var c=0;
for (var i=0;i<P.caps.length;i++){
  try{ var t=lay.textFrames.add(); t.contents=P.caps[i].txt;
    try{ t.textRange.characterAttributes.size=11; }catch(e){}
    t.position=[P.caps[i].pos[0],P.caps[i].pos[1]]; c++; }catch(e){}
}
var opt=new IllustratorSaveOptions(); opt.pdfCompatible=false;
d.saveAs(new File(COPY), opt);
"artboard_added="+ab.name+" placed="+n+" captions="+c+" errs="+errs.join(" | ")+" placed_total="+d.placedItems.length+" artboards="+d.artboards.length;
