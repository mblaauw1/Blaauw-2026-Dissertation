#target illustrator
var AI="/Volumes/4 MB/ablation_plots/_superseded_decks/REVISED_TIMESTRIPS_20260811.ai";
var doc=app.open(new File(AI)); var out=[];
out.push("pageItems="+doc.pageItems.length+" placedItems="+doc.placedItems.length+
         " textFrames="+doc.textFrames.length+" layers="+doc.layers.length+" artboards="+doc.artboards.length);
for(var L=0;L<doc.layers.length;L++) out.push("  layer '"+doc.layers[L].name+"' items="+doc.layers[L].pageItems.length);
for(var i=0;i<doc.placedItems.length && i<20;i++){
  var f=null; try{f=doc.placedItems[i].file;}catch(e){}
  var b=doc.placedItems[i].visibleBounds;
  out.push("  "+(f?f.name:"(embedded)")+"  ["+b[0].toFixed(0)+","+b[1].toFixed(0)+"]");
}
doc.close(SaveOptions.DONOTSAVECHANGES);
var lf=new File("/Volumes/4 MB/_claude_tmp/check_deck.txt"); lf.open("w"); lf.write(out.join("\n")); lf.close();
out.join("\n");
