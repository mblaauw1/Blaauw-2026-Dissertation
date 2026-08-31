#target illustrator
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch(e){}
while (app.documents.length>0){ app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var d=app.open(new File("/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai"));
var o=new ExportOptionsPNG24(); o.antiAliasing=true; o.transparency=false; o.artBoardClipping=true; o.horizontalScale=40; o.verticalScale=40;
var out=[];
for (var a=0;a<d.artboards.length;a++){
  if(d.artboards[a].name.indexOf("Kinetochore shape")>=0){
    d.artboards.setActiveArtboardIndex(a);
    d.exportFile(new File("/Volumes/4 MB/_scratch/chk_ktshape.png"), ExportType.PNG24, o);
    out.push((a+1)+"="+d.artboards[a].name);
  }
}
d.close(SaveOptions.DONOTSAVECHANGES);
out.join(" | ");
