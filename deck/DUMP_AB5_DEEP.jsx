// RECURSIVE dump of artboard 5. Root cause of every "it isn't there": doc.pageItems does not descend into
// GroupItems in this build, so anything she GROUPED (strip + its label) was invisible to the flat walk.
#target illustrator
var HB=new File("/Volumes/4 MB/_claude_tmp/ab5_deep.txt");
function beat(m){try{HB.open("a");HB.writeln(m);HB.close();}catch(e){}}
function walk(coll,depth){
  for(var i=0;i<coll.length;i++){
    var it=coll[i],k="",b=null,nm="";
    try{k=it.typename;}catch(e){continue}
    try{b=it.visibleBounds;}catch(e){}
    try{ if(k==="PlacedItem"&&it.file) nm=it.file.name; }catch(e){}
    if(b){
      var cx=(b[0]+b[2])/2, cy=(b[1]+b[3])/2;
      if(cx>-2050&&cx<3050&&cy<3050&&cy>-2050&&(k==="PlacedItem"||k==="RasterItem"))
        beat(k+" d"+depth+" "+(b[2]-b[0]).toFixed(0)+"x"+(b[1]-b[3]).toFixed(0)+
             " at "+b[0].toFixed(0)+","+b[1].toFixed(0)+" "+(nm||"(embedded)"));
    }
    if(k==="GroupItem"){ try{ walk(it.pageItems,depth+1); }catch(e){} }
  }
}
app.userInteractionLevel=UserInteractionLevel.DONTDISPLAYALERTS;
var doc=app.open(new File("/Volumes/4 MB/1_DECKS/META_FIGURES_20260814.ai"));
for(var L=0;L<doc.layers.length;L++){ try{ walk(doc.layers[L].pageItems,0); }catch(e){} }
doc.close(SaveOptions.DONOTSAVECHANGES);
app.userInteractionLevel=UserInteractionLevel.DISPLAYALERTS;
beat("DONE"); "ok";
