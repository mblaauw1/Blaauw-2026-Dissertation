// REVIVED_OUTLINE reported 138 pageItems but only 5 brown paths. What are the other 133?
#target illustrator
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var d=app.open(new File("/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai"));
function col(c){ try{ if(c.typename=="RGBColor") return Math.round(c.red)+","+Math.round(c.green)+","+Math.round(c.blue);}catch(e){} return "?"; }
var agg={}, samples=[];
var L=d.layers.getByName("REVIVED_OUTLINE");
for(var i=0;i<L.pageItems.length;i++){
  var it=L.pageItems[i], t=it.typename, extra="";
  if(t=="PathItem"){ extra=" stroke "+(it.stroked?col(it.strokeColor):"none")+" fill "+(it.filled?col(it.fillColor):"none"); }
  if(t=="TextFrame"){ try{ extra=" text='"+String(it.contents).substring(0,30)+"'"; }catch(e){} }
  var k=t+extra;
  agg[k]=(agg[k]||0)+1;
  if(samples.length<6) samples.push((it.name||"(unnamed)")+" :: "+k);
}
var out=[]; for(var k2 in agg) out.push("   "+agg[k2]+"x  "+k2);
d.close(SaveOptions.DONOTSAVECHANGES);
"REVIVED_OUTLINE composition ("+L.pageItems.length+" items):\n"+out.join("\n")+"\nsamples:\n   "+samples.join("\n   ");
