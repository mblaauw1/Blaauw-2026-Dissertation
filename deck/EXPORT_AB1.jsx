// Render artboard 5 to PNG. An object walk keeps missing things she says are there (it only ever named
// linked PlacedItems, and now finds no strips on AB5 while she reports two). Rasterising the BOARD is an
// independent method: whatever is actually on it appears, regardless of item kind, nesting, layer state or
// link health. Read-only; her file is closed without saving.
#target illustrator
var HB=new File("/Volumes/4 MB/_claude_tmp/ab5exp.txt");
function beat(m){try{HB.open("a");HB.writeln(m);HB.close();}catch(e){}}
app.userInteractionLevel=UserInteractionLevel.DONTDISPLAYALERTS;
var doc=app.open(new File("/Volumes/4 MB/1_DECKS/META_FIGURES_20260814.ai"));
beat("layers="+doc.layers.length);
for(var i=0;i<doc.layers.length;i++){
  var L=doc.layers[i];
  beat("layer["+i+"] '"+L.name+"' visible="+L.visible+" locked="+L.locked+" items="+L.pageItems.length);
}
doc.artboards.setActiveArtboardIndex(0);          // 0-based -> artboard 5
var ef=new ExportOptionsPNG24();
ef.artBoardClipping=true; ef.horizontalScale=12; ef.verticalScale=12;
doc.exportFile(new File("/Volumes/4 MB/_claude_tmp/ab1_board.png"), ExportType.PNG24, ef);
beat("exported ab1_board.png");
doc.close(SaveOptions.DONOTSAVECHANGES);
app.userInteractionLevel=UserInteractionLevel.DISPLAYALERTS;
beat("DONE"); "ok";
