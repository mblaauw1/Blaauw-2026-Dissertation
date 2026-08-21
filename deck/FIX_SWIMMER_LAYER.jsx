// FIX a regression from RELINK_EMBEDDED_0817.jsx: `doc.layers.add()` inserts the new layer at INDEX 0, so
// the `doc.layers[0].placedItems.add()` that was meant to put the relinked swimmer on her top layer put it
// on `embedded_originals_20260817` instead — which the same script then hid. Net effect: the swimmer was
// invisible on her deck. Move the LINKED item back to the `figures` layer and make it visible; the embedded
// original stays hidden on the keep layer.
#target illustrator
var HB=new File("/Volumes/4 MB/_claude_tmp/fixswim.txt");
function beat(m){try{HB.open("a");HB.writeln(m);HB.close();}catch(e){}}
app.userInteractionLevel=UserInteractionLevel.DONTDISPLAYALERTS;
var doc=app.open(new File("/Volumes/4 MB/1_DECKS/META_FIGURES_20260814.ai"));
var figs; try{figs=doc.layers.getByName("figures");}catch(e){figs=doc.layers[doc.layers.length-1];}
var keep; try{keep=doc.layers.getByName("embedded_originals_20260817");}catch(e){keep=null;}
if(keep) keep.visible=true;              // must be visible to move items out of it
var moved=0;
for(var i=doc.placedItems.length-1;i>=0;i--){
  var pi=doc.placedItems[i], nm="";
  try{nm=pi.file.name;}catch(e){continue;}
  if(nm.indexOf("G4_sisbehav_swimmer")<0) continue;
  var lay=""; try{lay=pi.layer.name;}catch(e){}
  if(lay!=="embedded_originals_20260817") continue;
  pi.move(figs,ElementPlacement.PLACEATBEGINNING);
  pi.hidden=false; moved++;
  beat("moved swimmer to figures layer");
}
if(keep) keep.visible=false;
doc.save(); doc.close(SaveOptions.SAVECHANGES);
app.userInteractionLevel=UserInteractionLevel.DISPLAYALERTS;
beat("DONE moved="+moved); "moved="+moved;
