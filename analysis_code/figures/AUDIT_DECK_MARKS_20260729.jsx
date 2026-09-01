// Inventory every non-figure mark in copy.ai: layer, colour, opacity, z-order, count.
// Answering two questions: (a) what is drawing RED outlines, which is not one of the defined
// conventions, and (b) why the grey FAMILY_GROUP blocks are invisible.
#target illustrator
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var d = app.open(new File("/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai"));
function col(c){ try{ if(c.typename=="RGBColor") return Math.round(c.red)+","+Math.round(c.green)+","+Math.round(c.blue); }catch(e){} return "?"; }
var out=[];
out.push("LAYERS bottom->top:");
for(var i=d.layers.length-1;i>=0;i--){
  var L=d.layers[i];
  out.push("   z"+i+"  "+L.name+"  items="+L.pageItems.length+"  visible="+L.visible+"  opacity="+L.opacity);
}
// path items grouped by (layer, stroke colour, fill colour)
var agg={};
for(var p=0;p<d.pathItems.length;p++){
  var it=d.pathItems[p], ln="?";
  try{ ln=it.layer.name; }catch(e){}
  var sc = it.stroked ? col(it.strokeColor) : "none";
  var fc = it.filled  ? col(it.fillColor)   : "none";
  var key=ln+" | stroke "+sc+" | fill "+fc+" | op "+Math.round(it.opacity);
  agg[key]=(agg[key]||0)+1;
}
out.push("");
out.push("PATH ITEMS by layer/colour/opacity:");
for(var k in agg) out.push("   "+agg[k]+"x   "+k);
// anything big and opaque that could hide the grey
out.push("");
out.push("LARGE OPAQUE FILLS (could cover FAMILY_GROUP):");
for(var q=0;q<d.pathItems.length;q++){
  var t=d.pathItems[q];
  if(!t.filled || t.opacity<90) continue;
  var b; try{b=t.visibleBounds;}catch(e){continue;}
  var w=b[2]-b[0], h=b[1]-b[3];
  if(w>600 && h>600){ var ln2="?"; try{ln2=t.layer.name;}catch(e){}
    out.push("   "+Math.round(w)+"x"+Math.round(h)+"  layer="+ln2+"  fill="+col(t.fillColor)+"  op="+Math.round(t.opacity)); }
}
d.close(SaveOptions.DONOTSAVECHANGES);
out.join("\n");
