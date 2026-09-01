// RECURSIVE cleanup. `doc.placedItems` does not descend into GroupItems in this build — the same blind spot
// that hid the artboard-5 strips — so a flat pass removed nothing. Walk layers and groups explicitly.
#target illustrator
var HB=new File("/Volumes/4 MB/_claude_tmp/cleanup.txt");
function beat(m){try{HB.open("a");HB.writeln(m);HB.close();}catch(e){}}
var seen={}, removed=0, found=0;
function walk(coll){
  var kill=[];
  for(var i=0;i<coll.length;i++){
    var it=coll[i], k="";
    try{k=it.typename;}catch(e){continue}
    if(k==="GroupItem"){ try{ walk(it.pageItems); }catch(e){} continue; }
    if(k!=="PlacedItem") continue;
    var nm=""; try{nm=it.file.name;}catch(e){continue}
    if(nm!=="G6tenM_equivalent_kk.pdf") continue;
    found++;
    var b=it.visibleBounds, lay=""; try{lay=it.layer.name;}catch(e){}
    var stray=(lay==="embedded_originals_20260817")||(Math.abs(b[0])<1&&Math.abs(b[3])<1);
    var key=b[0].toFixed(0)+"_"+b[1].toFixed(0);
    if(stray){ beat("stray on "+lay+" @"+key); kill.push(it); }
    else if(seen[key]){ beat("stacked dup @"+key); kill.push(it); }
    else seen[key]=1;
  }
  for(var j=0;j<kill.length;j++){ try{ kill[j].remove(); removed++; }catch(e){ beat("remove failed: "+e); } }
}
app.userInteractionLevel=UserInteractionLevel.DONTDISPLAYALERTS;
var doc=app.open(new File("/Volumes/4 MB/1_DECKS/META_FIGURES_20260814.ai"));
for(var L=0;L<doc.layers.length;L++){
  var lay=doc.layers[L], wasVis=lay.visible, wasLock=lay.locked;
  lay.visible=true; lay.locked=false;
  try{ walk(lay.pageItems); }catch(e){ beat("layer "+lay.name+": "+e); }
  lay.visible=wasVis; lay.locked=wasLock;
}
beat("found="+found+" removed="+removed);
doc.save(); doc.close(SaveOptions.SAVECHANGES);
app.userInteractionLevel=UserInteractionLevel.DISPLAYALERTS;
"found="+found+" removed="+removed;
