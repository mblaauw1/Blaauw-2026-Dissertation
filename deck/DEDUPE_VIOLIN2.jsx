// Remove the DUPLICATE Violin 2. It was placed twice: once additively on `session_20260816` (before I knew
// the real one was an embedded raster) and once on `figures` when that embedded original was swapped out.
// The `figures` copy sits in her intended position and is the one to keep.
#target illustrator
var HB=new File("/Volumes/4 MB/_claude_tmp/dedupe.txt");
function beat(m){try{HB.open("a");HB.writeln(m);HB.close();}catch(e){}}
app.userInteractionLevel=UserInteractionLevel.DONTDISPLAYALERTS;
var doc=app.open(new File("/Volumes/4 MB/1_DECKS/META_FIGURES_20260814.ai"));
var removed=0;
for(var i=doc.placedItems.length-1;i>=0;i--){
  var pi=doc.placedItems[i], nm="", lay="";
  try{nm=pi.file.name;}catch(e){continue}
  try{lay=pi.layer.name;}catch(e){}
  if(nm.indexOf("G1_violin2_no_dc_offtarget_journal")<0) continue;
  if(lay!=="session_20260816") continue;          // keep the `figures` copy in her layout position
  var b=pi.visibleBounds;
  pi.remove(); removed++;
  beat("removed duplicate at "+b[0].toFixed(0)+","+b[1].toFixed(0));
}
doc.save(); doc.close(SaveOptions.SAVECHANGES);
app.userInteractionLevel=UserInteractionLevel.DISPLAYALERTS;
beat("DONE removed="+removed); "removed="+removed;
