// Dump {figure basename: "AB##"} for every placed item in both decks, so the title generator can
// state which artboard a figure is on without guessing.
#target illustrator
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var DOCS=["/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai",
          "/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_kinetochore_overflow.ai"];
var TAG=["AB","OV-AB"];
var pairs=[];
for(var k=0;k<DOCS.length;k++){
  var d=app.open(new File(DOCS[k]));
  function abOf(it){ var b; try{b=it.visibleBounds;}catch(e){return -1;}
    var cx=(b[0]+b[2])/2, cy=(b[1]+b[3])/2;
    for(var a=0;a<d.artboards.length;a++){ var R=d.artboards[a].artboardRect;
      if(cx>=R[0]&&cx<=R[2]&&cy<=R[1]&&cy>=R[3]) return a; } return -1; }
  for(var i=0;i<d.placedItems.length;i++){
    var f=null; try{f=d.placedItems[i].file;}catch(e){}
    if(!f) continue;
    var n=decodeURI(f.name).replace(/\.(pdf|png)$/i,"");
    pairs.push('"'+n+'":"'+TAG[k]+(abOf(d.placedItems[i])+1)+'"');
  }
  d.close(SaveOptions.DONOTSAVECHANGES);
}
var f=new File("/Volumes/4 MB/_working/_deck_jsx_inputs/artboards.json");
f.encoding="UTF-8"; f.open("w"); f.write("{"+pairs.join(",")+"}"); f.close();
"wrote "+pairs.length+" figure->artboard pairs";
