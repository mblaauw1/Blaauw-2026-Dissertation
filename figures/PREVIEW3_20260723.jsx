#target illustrator
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch(e){}
while (app.documents.length>0){ app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var d=app.open(new File("/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai"));
var o=new ExportOptionsPNG24(); o.antiAliasing=true; o.transparency=false; o.artBoardClipping=true; o.horizontalScale=40; o.verticalScale=40;
var want=[21,26];   // Custom analyses (0-based 21) and Sisterless-KT behavior (0-based 26)
var out=[];
for (var k=0;k<want.length;k++){
  try{ d.artboards.setActiveArtboardIndex(want[k]);
    d.exportFile(new File("/Volumes/4 MB/_scratch/chk2_ab"+(want[k]+1)+".png"), ExportType.PNG24, o);
    out.push((want[k]+1)+"="+d.artboards[want[k]].name.substring(0,24)); }catch(e){ out.push("ERR"+e); }
}
d.close(SaveOptions.DONOTSAVECHANGES);
out.join(" | ");
