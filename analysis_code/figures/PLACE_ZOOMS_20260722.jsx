#target illustrator
// Place the 10 custom-analysis _zoom companions that were rendered but never placed
// (found by ablation_plots/verify_deck_complete.py). They go in the free band under the existing
// "Custom analyses" artboard, which is grown downward -- a NEW artboard down there throws 'CoOA'
// (artboard coords outside the canvas), so grow an existing one instead.
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch(e){}
function readFile(p){ var f=new File(p); f.encoding="UTF-8"; f.open("r"); var s=f.read(); f.close(); return s; }
var P = eval("("+readFile("/Volumes/4 MB/_scratch/place_zooms.json")+")");
var COPY="/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
while (app.documents.length>0){ app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var d=app.open(new File(COPY));
var grew=0;
for (var a=0;a<d.artboards.length;a++){
  if(d.artboards[a].name.indexOf(P.resize.name)>=0){ d.artboards[a].artboardRect=P.resize.rect; grew++; break; }
}
var lay; try{ lay=d.layers.getByName("PLOT_LABELS"); }catch(e){ lay=d.layers.add(); lay.name="PLOT_LABELS"; }
var n=0, errs=[];
for (var i=0;i<P.items.length;i++){
  var it=P.items[i]; var f=new File(it.file);
  if(!f.exists){ errs.push(it.base); continue; }
  try{ var pi=d.placedItems.add(); pi.file=f;
    pi.width=it.b[2]-it.b[0]; pi.height=it.b[1]-it.b[3]; pi.position=[it.b[0],it.b[1]];
    pi.name=it.base; n++; }catch(e){ errs.push(it.base+"::"+e); }
}
var c=0;
for (var i=0;i<P.caps.length;i++){
  try{ var t=lay.textFrames.add(); t.contents=P.caps[i].txt;
    t.textRange.characterAttributes.size=9; t.position=[P.caps[i].pos[0],P.caps[i].pos[1]]; c++; }catch(e){}
}
var opt=new IllustratorSaveOptions(); opt.pdfCompatible=false;
d.saveAs(new File(COPY), opt);
"artboard_grown="+grew+" placed="+n+" captions="+c+" errs="+errs.join(",")+" placed_total="+d.placedItems.length;
