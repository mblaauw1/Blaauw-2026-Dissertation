#target illustrator
// Place fig 405 (cytosol-bg accuracy by relax level) into the free slot on the kinetochore-shape artboard.
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch(e){}
function readFile(p){ var f=new File(p); f.encoding="UTF-8"; f.open("r"); var s=f.read(); f.close(); return s; }
var P = eval("("+readFile("/Volumes/4 MB/_scratch/place_cytosol405.json")+")");
var COPY="/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
while (app.documents.length>0){ app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var d=app.open(new File(COPY));
var lay; try{ lay=d.layers.getByName("PLOT_LABELS"); }catch(e){ lay=d.layers.add(); lay.name="PLOT_LABELS"; }
var it=P.items[0]; var f=new File(it.file); var msg="";
try{ var pi=d.placedItems.add(); pi.file=f; var ratio=pi.height/pi.width;
  pi.width=it.w; pi.height=it.w*ratio; pi.position=[it.x,it.y]; pi.name=it.base; msg="placed"; }
catch(e){ msg="ERR "+e; }
try{ var t=lay.textFrames.add(); t.contents=P.caps[0].txt; t.textRange.characterAttributes.size=11;
  t.position=[P.caps[0].pos[0],P.caps[0].pos[1]]; }catch(e){}
var opt=new IllustratorSaveOptions(); opt.pdfCompatible=false;
d.saveAs(new File(COPY), opt);
msg+" placed_total="+d.placedItems.length;
