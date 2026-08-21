#target illustrator
// READ-ONLY inventory dump of copy.ai: every placed item (basename, bounds, artboard) + artboards.
// Writes JSON to /Volumes/4 MB/_copyai_inventory.json. Does NOT save the document (no hang risk).
app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
var COPY="/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
var d=null;
for (var q=0;q<app.documents.length;q++){ if(app.documents[q].name=="ablation_figures_grouped copy.ai"){ d=app.documents[q]; break; } }
var opened=false; if(!d){ d=app.open(new File(COPY)); opened=true; }

function esc(s){ return String(s).replace(/\\/g,"\\\\").replace(/"/g,'\\"'); }
// artboards
var abs=[];
for (var a=0;a<d.artboards.length;a++){ var r=d.artboards[a].artboardRect; // [l,t,r,b]
  abs.push('{"i":'+a+',"name":"'+esc(d.artboards[a].name)+'","rect":['+r[0]+','+r[1]+','+r[2]+','+r[3]+']}'); }
function abOf(cx,cy){ for (var a=0;a<d.artboards.length;a++){ var r=d.artboards[a].artboardRect;
  if(cx>=r[0]&&cx<=r[2]&&cy<=r[1]&&cy>=r[3]) return a; } return -1; }
// placed items
var items=[];
for (var i=0;i<d.placedItems.length;i++){ var pi=d.placedItems[i];
  var base=""; try{ base=decodeURI(pi.file.name).replace(/\.(pdf|png|svg)$/i,""); }catch(e){ base="(nofile)"; }
  var b; try{b=pi.visibleBounds;}catch(e){ b=[0,0,0,0]; }
  var cx=(b[0]+b[2])/2, cy=(b[1]+b[3])/2;
  items.push('{"base":"'+esc(base)+'","name":"'+esc(pi.name)+'","bounds":['+b[0].toFixed(1)+','+b[1].toFixed(1)+','+b[2].toFixed(1)+','+b[3].toFixed(1)+'],"ab":'+abOf(cx,cy)+'}');
}
var out='{"n_placed":'+d.placedItems.length+',"artboards":['+abs.join(",")+'],"items":['+items.join(",")+']}';
var f=new File("/Volumes/4 MB/_copyai_inventory.json"); f.encoding="UTF-8"; f.open("w"); f.write(out); f.close();
if(opened){ d.close(SaveOptions.DONOTSAVECHANGES); }
"dumped "+d.placedItems.length+" placed items, "+d.artboards.length+" artboards";
