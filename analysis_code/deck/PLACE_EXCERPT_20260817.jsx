// Put AB5_EXCERPT_1sisterless_11 exactly where the embedded raster it replaces used to sit.
// The surviving copy came from a run that errored BEFORE positioning it, so it was left at the PDF's
// native size (547x156) at a default spot. Target geometry is the archived original's own bounds:
// 1318 x 382 at (-19, 1284) on artboard 5 — height set from the true aspect so nothing is distorted.
#target illustrator
var HB=new File("/Volumes/4 MB/_claude_tmp/place_exc.txt");
function beat(m){try{HB.open("a");HB.writeln(m);HB.close();}catch(e){}}
app.userInteractionLevel=UserInteractionLevel.DONTDISPLAYALERTS;
while(app.documents.length>0){ app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var doc=app.open(new File("/Volumes/4 MB/1_DECKS/META_FIGURES_20260814.ai"));
var figs=doc.layers.getByName("figures"); figs.locked=false; figs.visible=true; doc.activeLayer=figs;
var n=0;
for(var i=0;i<doc.placedItems.length;i++){
  var it=doc.placedItems[i], f="";
  try{ f=it.file? it.file.name : ""; }catch(e){ continue; }
  if(f.indexOf("AB5_EXCERPT_1sisterless_11")!==0) continue;
  var W=1318.0;
  var s=W/it.width;                       // uniform scale from native width -> never distorts
  it.width=it.width*s; it.height=it.height*s;
  it.left=-19.0; it.top=1284.0;
  n++; beat("placed at "+it.left.toFixed(0)+","+it.top.toFixed(0)+" "+it.width.toFixed(0)+"x"+it.height.toFixed(0)+" layer="+it.layer.name);
}
beat("DONE placed="+n);
doc.save(); doc.close(SaveOptions.SAVECHANGES);
app.userInteractionLevel=UserInteractionLevel.DISPLAYALERTS;
"placed="+n;
