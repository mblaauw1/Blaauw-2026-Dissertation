#target illustrator
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch(e){}
while (app.documents.length>0){ app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var d=app.open(new File("/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai"));
var o=new ExportOptionsPNG24(); o.antiAliasing=true; o.transparency=false; o.artBoardClipping=true; o.horizontalScale=35; o.verticalScale=35;
// find the model artboard + the bottom-left-most artboard
var out=[], bestI=0, bestScore=1e12;
for (var a=0;a<d.artboards.length;a++){
  var r=d.artboards[a].artboardRect;      // [l,t,r,b]
  var score=r[0]-r[3];                    // small left + low bottom => bottom-left
  if(score<bestScore){ bestScore=score; bestI=a; }
}
var want=[bestI];
for (var a=0;a<d.artboards.length;a++){ if(d.artboards[a].name.indexOf("G23")===0) want.push(a); }
for (var k=0;k<want.length;k++){
  try{ d.artboards.setActiveArtboardIndex(want[k]);
    d.exportFile(new File("/Volumes/4 MB/_scratch/chk_ab"+(want[k]+1)+".png"), ExportType.PNG24, o);
    out.push((want[k]+1)+"="+d.artboards[want[k]].name.substring(0,26)); }catch(e){ out.push("ERR"+e); }
}
d.close(SaveOptions.DONOTSAVECHANGES);
out.join(" | ");
