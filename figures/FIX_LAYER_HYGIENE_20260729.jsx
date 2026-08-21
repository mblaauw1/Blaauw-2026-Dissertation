// 133 FIGURES (PlacedItems) were sitting on the REVIVED_OUTLINE layer, which only ever holds the 5
// brown stroke-only rects marking un-retired figures. REVIVED_OUTLINE is near the TOP of the stack
// (above RETIRED_MARKS and PLOT_LABELS), so those figures painted OVER their own red retirement boxes
// and captions - which is why marks looked missing or wrong. Move every PlacedItem to the `figures`
// layer so the mark layers sit above the artwork as intended.
// Every value is captured BEFORE d.close() (reading after raises Error 45).
#target illustrator
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var PATH="/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
var d=app.open(new File(PATH));
var figs; try{ figs=d.layers.getByName("figures"); }catch(e){ figs=d.layers.add(); figs.name="figures"; }
var moved=0, scanned=0, per={};
for (var li=0; li<d.layers.length; li++){
  var lay=d.layers[li];
  if (lay.name==="figures") continue;
  if (lay.name!=="REVIVED_OUTLINE" && lay.name!=="SIG_HIGHLIGHT" && lay.name!=="FAMILY_GROUP" &&
      lay.name!=="MODEL_HIGHLIGHT" && lay.name!=="RETIRED_MARKS" && lay.name!=="DECK_TITLE") continue;
  for (var i=lay.pageItems.length-1;i>=0;i--){
    var it=lay.pageItems[i];
    if (it.typename!=="PlacedItem") continue;
    scanned++;
    try { it.move(figs, ElementPlacement.PLACEATEND); moved++; per[lay.name]=(per[lay.name]||0)+1; } catch(e2){}
  }
}
// restore intended stacking: FAMILY_GROUP (bottom) -> SIG_HIGHLIGHT -> figures -> marks -> DECK_TITLE (top)
// NB: do not name this L - `var L` was used as a loop counter above and ExtendScript hoists it,
// shadowing the function (Error 24: L is not a function). Same trap class as naming a variable `open`.
function layerByName(n){ try{ return d.layers.getByName(n); }catch(e){ return null; } }
var order=["DECK_TITLE","RETIRED_MARKS","PLOT_LABELS","REVIVED_OUTLINE","MODEL_HIGHLIGHT","figures","SIG_HIGHLIGHT","FAMILY_GROUP"];
for (var o=order.length-1;o>=0;o--){ var l=layerByName(order[o]); if(l){ try{ l.zOrder(ZOrderMethod.BRINGTOFRONT); }catch(e3){} } }
var lst=[]; for(var k in per) lst.push(k+"="+per[k]);
var layerReport=[];
for (var z=0; z<d.layers.length; z++) layerReport.push("z"+z+":"+d.layers[z].name+"("+d.layers[z].pageItems.length+")");
var mode="";
try{ var so=new IllustratorSaveOptions(); so.pdfCompatible=false; d.saveAs(new File(PATH), so); mode="saved"; }
catch(e4){ mode="SAVE_FAILED "+e4; }
try{ d.close(SaveOptions.DONOTSAVECHANGES); }catch(e5){}
"PlacedItems moved off mark layers: "+moved+" of "+scanned+"  ["+lst.join(", ")+"]"+
"\nlayers top->bottom: "+layerReport.join("  ")+"\nsave="+mode;
