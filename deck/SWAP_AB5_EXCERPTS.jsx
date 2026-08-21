// Replace the two EMBEDDED artboard-5 excerpts with LINKED, corrected versions.
// Identified from their burned-in timestamps: the one at (-46,1922) is "hidden in plate"
// (10:50/17:2x/30:23/35:23 -> 20260420 ptk2 eyfp cdc20 1 ablation_11) and the one at (-46,2503) is "polar"
// (10:54/21:11/26:26/31:26 -> 20250402 ptk_yfpcdc20_2). Both now carry her ROI requests: 5 um trimmed per
// side, the first two monitoring frames moved up (expressed as a zoom around the intended centre where the
// frame had no headroom), and the tighter polar crop.
// SAFE: each replacement takes the embedded item's OWN bounds, so nothing moves or resizes; the original is
// moved to the hidden `embedded_originals_20260817` layer, never deleted. Target layer fetched BY NAME —
// doc.layers.add() inserts at index 0, which is what briefly hid the swimmer.
#target illustrator
var HB=new File("/Volumes/4 MB/_claude_tmp/swap_ab5.txt");
function beat(m){try{HB.open("a");HB.writeln(m);HB.close();}catch(e){}}
var PDF="/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/";
app.userInteractionLevel=UserInteractionLevel.DONTDISPLAYALERTS;
var doc=app.open(new File("/Volumes/4 MB/1_DECKS/META_FIGURES_20260814.ai"));
var host; try{host=doc.layers.getByName("legend_bullets");}catch(e){host=doc.layers[0];}
var keep; try{keep=doc.layers.getByName("embedded_originals_20260817");}
catch(e){keep=doc.layers.add(); keep.name="embedded_originals_20260817";}
keep.visible=true;
var TARGETS=[{y:1922,f:"AB5_EXCERPT_hidden_in_plate.pdf"},{y:2503,f:"AB5_EXCERPT_polar.pdf"}];
var done=0;
for(var t=0;t<TARGETS.length;t++){
  for(var i=doc.rasterItems.length-1;i>=0;i--){
    var ri=doc.rasterItems[i], lay=""; try{lay=ri.layer.name;}catch(e){continue}
    if(lay!=="legend_bullets") continue;
    var b=ri.visibleBounds;
    if(Math.abs(b[1]-TARGETS[t].y)>4 || Math.abs(b[0]+46)>6) continue;
    var src=new File(PDF+TARGETS[t].f); if(!src.exists){beat("MISSING "+TARGETS[t].f); continue;}
    var w=b[2]-b[0], h=b[1]-b[3];
    var it=host.placedItems.add(); it.file=src;
    var s=Math.min(w/it.width, h/it.height);
    it.width=it.width*s; it.height=it.height*s;
    it.left=b[0]+(w-it.width)/2.0; it.top=b[1]-(h-it.height)/2.0;
    ri.move(keep,ElementPlacement.PLACEATEND); ri.hidden=true;
    done++; beat("swapped "+TARGETS[t].f+" at "+b[0].toFixed(0)+","+b[1].toFixed(0));
    break;
  }
}
keep.visible=false;
doc.save(); doc.close(SaveOptions.SAVECHANGES);
app.userInteractionLevel=UserInteractionLevel.DISPLAYALERTS;
beat("DONE swapped="+done); "swapped="+done;
