// Remove the duplicate AB5_EXCERPT_1sisterless_11 placement.
//
// CAUSE, worth recording: a JSX that ERRORS leaves the document OPEN and DIRTY in Illustrator. The next
// run's app.open() then returns that already-open in-memory document rather than re-reading the file, so
// the previous attempt's partial edits are still present and the new run adds its work ON TOP. Run 4 had
// already added the placement before failing at ri.move(); run 5 added a second one and saved both.
// LESSON: a script that can fail must close the document in its error path, and a repair script should
// check for pre-existing copies before adding.
#target illustrator
var HB=new File("/Volumes/4 MB/_claude_tmp/dedupe_exc.txt");
function beat(m){try{HB.open("a");HB.writeln(m);HB.close();}catch(e){}}
app.userInteractionLevel=UserInteractionLevel.DONTDISPLAYALERTS;
// close anything already open so we work from the SAVED file, not a stale in-memory copy
while(app.documents.length>0){ app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var doc=app.open(new File("/Volumes/4 MB/1_DECKS/META_FIGURES_20260814.ai"));
var figs=doc.layers.getByName("figures"); figs.locked=false; figs.visible=true; doc.activeLayer=figs;
var found=[];
for(var i=0;i<doc.placedItems.length;i++){
  var it=doc.placedItems[i],f="";
  try{ f=it.file? it.file.name : ""; }catch(e){ continue; }
  if(f.indexOf("AB5_EXCERPT_1sisterless_11")===0) found.push(it);
}
beat("copies found="+found.length);
var removed=0;
for(var k=1;k<found.length;k++){ found[k].remove(); removed++; }   // keep exactly one
beat("removed="+removed);
doc.save(); doc.close(SaveOptions.SAVECHANGES);
app.userInteractionLevel=UserInteractionLevel.DISPLAYALERTS;
"found="+found.length+" removed="+removed;
