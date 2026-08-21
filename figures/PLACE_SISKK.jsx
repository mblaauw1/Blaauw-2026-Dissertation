#target illustrator
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch(e){}
function readFile(p){ var f=new File(p); f.encoding="UTF-8"; f.open("r"); var s=f.read(); f.close(); return s; }
var P = eval("("+readFile("/Volumes/4 MB/_scratch/place_siskk.json")+")");
var COPY="/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
while (app.documents.length>0){ app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var d=app.open(new File(COPY));
var lay; try{ lay=d.layers.getByName("PLOT_LABELS"); }catch(e){ lay=d.layers.add(); lay.name="PLOT_LABELS"; }
var n=0;
for (var i=0;i<P.items.length;i++){ var it=P.items[i]; var f=new File(it.file);
  try{ var pi=d.placedItems.add(); pi.file=f; var ra=pi.height/pi.width; pi.width=it.w; pi.height=it.w*ra; pi.position=[it.x,it.y]; pi.name=it.base; n++; }catch(e){} }
for (var i=0;i<P.caps.length;i++){ try{ var t=lay.textFrames.add(); t.contents=P.caps[i].txt; t.textRange.characterAttributes.size=11; t.position=[P.caps[i].pos[0],P.caps[i].pos[1]]; }catch(e){} }
var opt=new IllustratorSaveOptions(); opt.pdfCompatible=false; d.saveAs(new File(COPY), opt);
"placed="+n+" total="+d.placedItems.length;
