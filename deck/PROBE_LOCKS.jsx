#target illustrator
var HB=new File("/Volumes/4 MB/_claude_tmp/locks.txt");
function beat(m){try{HB.open("a");HB.writeln(m);HB.close();}catch(e){}}
app.userInteractionLevel=UserInteractionLevel.DONTDISPLAYALERTS;
var doc=app.open(new File("/Volumes/4 MB/1_DECKS/META_FIGURES_20260814.ai"));
function dump(l,ind){
  beat(ind+"LAYER '"+l.name+"' locked="+l.locked+" visible="+l.visible+" items="+l.pageItems.length+" sublayers="+l.layers.length);
  for(var i=0;i<l.layers.length;i++) dump(l.layers[i],ind+"   ");
}
for(var i=0;i<doc.layers.length;i++) dump(doc.layers[i],"");
beat("--- template/locked doc? templateLayer checks ---");
doc.close(SaveOptions.DONOTSAVECHANGES);
app.userInteractionLevel=UserInteractionLevel.DISPLAYALERTS;
"ok";
