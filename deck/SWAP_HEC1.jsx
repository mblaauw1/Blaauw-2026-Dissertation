// Replace the EMBEDDED 2-row hec1/Mad1 timestrip on artboard 1 with the rebuilt 3-row version that now
// carries the PHASE channel (user 2026-08-17). It was embedded, which is why re-rendering never changed it.
// Aspect changed (2 rows -> 3), so the replacement keeps the original's LEFT/TOP and WIDTH and lets the
// height grow — scaling into the old box would squash the panels.
#target illustrator
var HB=new File("/Volumes/4 MB/_claude_tmp/swap_hec1.txt");
function beat(m){try{HB.open("a");HB.writeln(m);HB.close();}catch(e){}}
app.userInteractionLevel=UserInteractionLevel.DONTDISPLAYALERTS;
var doc=app.open(new File("/Volumes/4 MB/1_DECKS/META_FIGURES_20260814.ai"));
var host; try{host=doc.layers.getByName("figures");}catch(e){host=doc.layers[0];}
var keep; try{keep=doc.layers.getByName("embedded_originals_20260817");}
catch(e){keep=doc.layers.add(); keep.name="embedded_originals_20260817";}
keep.visible=true;
var src=new File("/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/G5_item4_hec1_timestrip_xy6.pdf");
var done=0;
for(var i=doc.rasterItems.length-1;i>=0;i--){
  var ri=doc.rasterItems[i], lay=""; try{lay=ri.layer.name;}catch(e){continue}
  if(lay!=="figures") continue;
  var b=ri.visibleBounds, w=b[2]-b[0], h=b[1]-b[3];
  if(Math.abs(w-1306)>8 || Math.abs(h-872)>8) continue;      // the 2-row hec1 strip
  if(!src.exists){beat("MISSING pdf"); break;}
  var it=host.placedItems.add(); it.file=src;
  var s=w/it.width;                                          // match WIDTH, keep aspect
  it.width=it.width*s; it.height=it.height*s;
  it.left=b[0]; it.top=b[1];
  ri.move(keep,ElementPlacement.PLACEATEND); ri.hidden=true;
  done++; beat("swapped hec1 strip at "+b[0].toFixed(0)+","+b[1].toFixed(0)+" new h="+it.height.toFixed(0));
  break;
}
keep.visible=false;
doc.save(); doc.close(SaveOptions.SAVECHANGES);
app.userInteractionLevel=UserInteractionLevel.DISPLAYALERTS;
beat("DONE swapped="+done); "swapped="+done;
