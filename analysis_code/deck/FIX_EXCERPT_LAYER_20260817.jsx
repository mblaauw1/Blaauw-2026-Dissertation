// Two pieces of debris from the failed relink attempts:
//  (1) the surviving AB5_EXCERPT_1sisterless_11 placement ended up on the HIDDEN
//      `embedded_originals_20260817` layer, so it is invisible — the same "relinked art lands on the keep
//      layer" bug as the swimmer swap. Move it to `figures`.
//  (2) a 0x0 PlacedItem with an unreadable link sits at (-7691, 8691) on `figures` — an aborted add from a
//      run that errored. Remove it.
// Always close any already-open document FIRST: a JSX that errors leaves the file open and dirty, and the
// next app.open() silently returns that stale in-memory copy instead of re-reading disk.
#target illustrator
var HB=new File("/Volumes/4 MB/_claude_tmp/fix_layer.txt");
function beat(m){try{HB.open("a");HB.writeln(m);HB.close();}catch(e){}}
app.userInteractionLevel=UserInteractionLevel.DONTDISPLAYALERTS;
while(app.documents.length>0){ app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var doc=app.open(new File("/Volumes/4 MB/1_DECKS/META_FIGURES_20260814.ai"));
var figs=doc.layers.getByName("figures"); figs.locked=false; figs.visible=true; doc.activeLayer=figs;
var keep=doc.layers.getByName("embedded_originals_20260817");
keep.visible=true; keep.locked=false;                       // must be visible to move art OUT of it

var moved=0, junk=0;
for(var i=doc.placedItems.length-1;i>=0;i--){
  var it=doc.placedItems[i], f="", lay="";
  try{ lay=it.layer.name; }catch(e){}
  try{ f=it.file? it.file.name : ""; }catch(e){ f="(unreadable)"; }
  var b=it.visibleBounds, w=b[2]-b[0], h=b[1]-b[3];
  if(w<1 && h<1){ it.remove(); junk++; beat("removed 0x0 debris"); continue; }
  if(f.indexOf("AB5_EXCERPT_1sisterless_11")===0 && lay==="embedded_originals_20260817"){
    it.move(figs, ElementPlacement.PLACEATBEGINNING);
    moved++; beat("moved excerpt to figures at "+b[0].toFixed(0)+","+b[1].toFixed(0)+" "+w.toFixed(0)+"x"+h.toFixed(0));
  }
}
keep.visible=false;
beat("DONE moved="+moved+" junk="+junk);
doc.save(); doc.close(SaveOptions.SAVECHANGES);
app.userInteractionLevel=UserInteractionLevel.DISPLAYALERTS;
"moved="+moved+" junk="+junk;
