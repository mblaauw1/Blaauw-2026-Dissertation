// de-overlap the two mirrored G8 figures on the PUBLICATION deck. Placing at the LIVE deck's
// coordinates was wrong: the publication copy hides its title text, so its artboard-7 layout differs
// and those coordinates landed on the peakzoom sheets. Solved against pub0814's OWN geometry.
#target illustrator
app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var HB=new File("/Volumes/4 MB/_claude_tmp/pubdeoverlap_heartbeat.txt");
function beat(m){try{HB.open("a");HB.writeln(m);HB.close();}catch(e){}}
var P="/Volumes/4 MB/1_DECKS/META_FIGURES_20260814_PUBLICATION.ai";
var d=app.open(new File(P)); beat("opened "+d.name);

(function(){
  for (var i=0;i<d.pageItems.length;i++){
    var it=d.pageItems[i];
    if (it.name!="G8_lagging_fracture_timing") continue;
    var b=it.geometricBounds, w=b[2]-b[0], h=b[1]-b[3];
    var s=Math.min(1140.0/w,260.0/h);
    it.resize(s*100,s*100,true,true,true,true,s*100,Transformation.TOPLEFT);
    b=it.geometricBounds; it.translate(-7290.0-b[0],-7030.0-b[1]);
    beat("moved "+it.name); return;
  }
  beat("NOT FOUND G8_lagging_fracture_timing");
})();

(function(){
  for (var i=0;i<d.pageItems.length;i++){
    var it=d.pageItems[i];
    if (it.name!="G8_lagging_fracture_materials") continue;
    var b=it.geometricBounds, w=b[2]-b[0], h=b[1]-b[3];
    var s=Math.min(840.0/w,200.0/h);
    it.resize(s*100,s*100,true,true,true,true,s*100,Transformation.TOPLEFT);
    b=it.geometricBounds; it.translate(-6110.0-b[0],-7090.0-b[1]);
    beat("moved "+it.name); return;
  }
  beat("NOT FOUND G8_lagging_fracture_materials");
})();

var o=new IllustratorSaveOptions(); o.pdfCompatible=false;
d.saveAs(new File(P),o); beat("SAVED"); d.close(SaveOptions.DONOTSAVECHANGES); beat("DONE");