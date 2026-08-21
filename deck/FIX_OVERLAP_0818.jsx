// Move the two 2026-08-18 figures that overlapped a board-straddling neighbour.
// Cause: my occupancy grid keyed on the raw ab_overlap STRING, so an item spanning boards 5 and 6
// ("5,6") matched neither board and was invisible to both. Assign by EVERY overlapped board.
#target illustrator
app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var HB=new File("/Volumes/4 MB/_claude_tmp/fixoverlap_heartbeat.txt");
function beat(m){try{HB.open("a");HB.writeln(m);HB.close();}catch(e){}}
var AIP="/Volumes/4 MB/1_DECKS/META_FIGURES_20260814.ai";
var doc=app.open(new File(AIP)); beat("opened "+doc.name);

(function(){
  for (var i=0;i<doc.pageItems.length;i++){
    var it=doc.pageItems[i];
    if (it.name != "G8_polar_chromosome_angle") continue;
    if (1.0 != 1.0) it.resize(1.0*100,1.0*100,true,true,true,true,1.0*100,Transformation.TOPLEFT);
    var b=it.geometricBounds;
    it.translate(-1990.0-b[0], -1290.0-b[1]);
    beat("moved "+it.name);
    break;
  }
})();

(function(){
  for (var i=0;i<doc.pageItems.length;i++){
    var it=doc.pageItems[i];
    if (it.name != "G8_kt_speed_paired_vs_sisterless") continue;
    if (1.0 != 1.0) it.resize(1.0*100,1.0*100,true,true,true,true,1.0*100,Transformation.TOPLEFT);
    var b=it.geometricBounds;
    it.translate(3570.0-b[0], -1630.0-b[1]);
    beat("moved "+it.name);
    break;
  }
})();

var opt=new IllustratorSaveOptions(); opt.pdfCompatible=false;
doc.saveAs(new File(AIP),opt); beat("SAVED");
doc.close(SaveOptions.DONOTSAVECHANGES); beat("DONE");