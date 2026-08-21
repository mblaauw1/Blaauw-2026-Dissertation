var DECK="/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
// find or open the deck
var d=null;
for(var i=0;i<app.documents.length;i++){ if(app.documents[i].name.indexOf("ablation_figures_grouped copy")>=0){ d=app.documents[i]; break; } }
if(!d){ d=app.open(new File(DECK)); }
app.activeDocument=d;
var re=/^(G5shape|G6[a-z]+)_/;
var n=0, err=0;
for(var i=0;i<d.placedItems.length;i++){
  var pi=d.placedItems[i]; var base;
  try{ base=decodeURI(pi.file.name).replace(/\.(pdf|png|svg)$/i,""); }catch(e){ continue; }
  if(!re.test(base)) continue;
  var pos=pi.position, w=pi.width, h=pi.height;
  try{ pi.file=new File(pi.file.fsName); pi.width=w; pi.height=h; pi.position=pos; n++; }catch(e){ err++; }
}
var opts=new IllustratorSaveOptions(); opts.pdfCompatible=false;
d.saveAs(new File(DECK), opts);
"relinked="+n+" err="+err;
