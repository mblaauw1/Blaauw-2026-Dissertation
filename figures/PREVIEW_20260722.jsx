#target illustrator
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch(e){}
var COPY="/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
while (app.documents.length>0){ app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var d=app.open(new File(COPY));
var opts=new ExportOptionsPNG24();
opts.antiAliasing=true; opts.transparency=false; opts.artBoardClipping=true; opts.horizontalScale=30; opts.verticalScale=30;
var want=[0,5,12,22,27];
var out=[];
for (var k=0;k<want.length;k++){
  try{
    d.artboards.setActiveArtboardIndex(want[k]);
    var f=new File("/Volumes/4 MB/_scratch/preview_ab"+(want[k]+1)+".png");
    d.exportFile(f, ExportType.PNG24, opts);
    out.push("ab"+(want[k]+1));
  }catch(e){ out.push("ERR"+want[k]+":"+e); }
}
d.close(SaveOptions.DONOTSAVECHANGES);
out.join(",");
