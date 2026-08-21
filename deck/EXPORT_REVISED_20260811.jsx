// Read-only: export the revised-timestrips file to PNG so its CONTENT can be inspected, not inferred.
#target illustrator
var AI="/Volumes/4 MB/ablation_plots/_superseded_decks/REVISED_TIMESTRIPS_20260811.ai";
var doc=app.open(new File(AI));
var out=["placedItems="+doc.placedItems.length];
for(var i=0;i<doc.placedItems.length;i++){
  var f=null; try{f=doc.placedItems[i].file;}catch(e){}
  if(f) out.push("  "+f.name+"   modified="+f.modified);
}
var opt=new ExportOptionsPNG24();
opt.artBoardClipping=true; opt.horizontalScale=22; opt.verticalScale=22;
doc.exportFile(new File("/Volumes/4 MB/_claude_tmp/revised_check.png"), ExportType.PNG24, opt);
doc.close(SaveOptions.DONOTSAVECHANGES);
var lf=new File("/Volumes/4 MB/_claude_tmp/revised_check.txt"); lf.encoding="UTF-8"; lf.open("w");
for(var k=0;k<out.length;k++) lf.writeln(out[k]);
lf.close(); "ok";
