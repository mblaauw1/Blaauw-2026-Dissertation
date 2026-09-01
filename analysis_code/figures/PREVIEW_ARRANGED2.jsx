#target illustrator
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch(e){}
while (app.documents.length>0){ app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var d=app.open(new File("/Volumes/4 MB/1_DECKS/arranged_into_paper_figures_2.ai"));
var o=new ExportOptionsPNG24(); o.antiAliasing=true; o.transparency=false; o.artBoardClipping=true; o.horizontalScale=60; o.verticalScale=60;
var out=[];
for (var k=0;k<3;k++){ try{ d.artboards.setActiveArtboardIndex(k);
  d.exportFile(new File("/Volumes/4 MB/_scratch/arr2_ab"+(k+1)+".png"), ExportType.PNG24, o); out.push(k+1);}catch(e){out.push("E"+e);} }
d.close(SaveOptions.DONOTSAVECHANGES);
out.join(",");
