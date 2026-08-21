#target illustrator
// Place k-k plot (significant -> highlight) + new metaphase abl->ana scatter; relink updated metaphase renders.
// Backgrounded (no activate). Save non-PDF-compatible.
app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
var COPY="/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
var PDF="/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/";
var d=null;
for (var q=0;q<app.documents.length;q++){ if(app.documents[q].name=="ablation_figures_grouped copy.ai"){ d=app.documents[q]; break; } }
var opened=false; if(!d){ d=app.open(new File(COPY)); opened=true; }
var lyr=d.activeLayer; var rep=[];
function baseOf(pi){ var f=null; try{f=pi.file;}catch(e){} if(!f) return null; return decodeURI(f.name).toLowerCase().replace(/\.(pdf|png|svg)$/,""); }
function findPlaced(base){ base=base.toLowerCase(); for (var i=0;i<d.placedItems.length;i++){ if(baseOf(d.placedItems[i])==base) return d.placedItems[i]; } return null; }
function overlaps(a,b){ return !(a[2]<=b[0]||a[0]>=b[2]||a[3]>=b[1]||a[1]<=b[3]); }
function collides(rect,self){ for(var i=0;i<d.placedItems.length;i++){ var it=d.placedItems[i]; if(it===self) continue; var b; try{b=it.visibleBounds;}catch(e){continue;} if(overlaps(rect,b)) return true; } return false; }
function placeBelow(item,anch,gap){ var ab=anch.visibleBounds,al=ab[0],abot=ab[3],aw=anch.width; var sc=aw/item.width; item.width*=sc; item.height*=sc; var ih=item.height,top=abot-gap,t=0; while(t<80){ var r=[al,top,al+item.width,top-ih]; if(!collides(r,item)) break; top-=(ih+gap); t++; } item.position=[al,top]; return t; }
function relink(base){ var pi=findPlaced(base), f=new File(PDF+base+".pdf"); if(pi&&f.exists){ try{pi.file=f; rep.push("relink "+base);}catch(e){rep.push("relinkERR "+base);} } else rep.push("relink-miss "+base); }
function placeNew(base,anchorBase,gap){ if(findPlaced(base)){ relink(base); return; } var anch=findPlaced(anchorBase); var f=new File(PDF+base+".pdf");
  if(!anch){ rep.push(base+": anchor '"+anchorBase+"' not found"); return; } if(!f.exists){ rep.push(base+": PDF missing"); return; }
  var it=lyr.placedItems.add(); it.file=f; var t=placeBelow(it,anch,gap); it.name=base; rep.push("placed "+base+" below "+anchorBase+" (tries="+t+")"); }

// updated renders -> relink
relink("G2_metaphase_ablated"); relink("G2_metaphase_ablated_abltometa");
// new plots -> place
placeNew("G2_metaphase_ablated_abltoana","G2_metaphase_ablated_abltometa",14);
placeNew("G3_kk_distance_vs_time_to_meta","G3_edge_distance",14);

// add k-k to the significance highlight layer (it is significant: rho=-0.41 p=0.002)
var hl=null; try{ hl=d.layers.getByName("SIG_HIGHLIGHT"); }catch(e){ hl=d.layers.add(); hl.name="SIG_HIGHLIGHT"; hl.zOrder(ZOrderMethod.SENDTOBACK); }
var it=findPlaced("G3_kk_distance_vs_time_to_meta");
if(it){ // avoid duplicate highlight
  var have=false; for(var i=0;i<hl.pathItems.length;i++){ if(hl.pathItems[i].name=="SIGHILITE G3_kk_distance_vs_time_to_meta"){have=true;break;} }
  if(!have){ var b=it.visibleBounds, P=18; var yc=new RGBColor(); yc.red=255;yc.green=238;yc.blue=120;
    var rr=hl.pathItems.roundedRectangle(b[1]+P,b[0]-P,(b[2]-b[0])+2*P,(b[1]-b[3])+2*P,14,14);
    rr.filled=true;rr.stroked=false;rr.fillColor=yc;rr.opacity=38;rr.name="SIGHILITE G3_kk_distance_vs_time_to_meta"; rep.push("highlighted k-k"); }
}
var so=new IllustratorSaveOptions(); so.pdfCompatible=false; d.saveAs(new File(COPY),so);
if(opened){ d.close(SaveOptions.DONOTSAVECHANGES); }
"DONE :: "+rep.join(" | ");
