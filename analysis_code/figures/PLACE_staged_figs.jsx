#target illustrator
// Reposition the 9 staged figures from the staging block to sit directly below a named sibling already
// in the deck (so each lands on the correct artboard next to its group). Collision-avoided (search downward
// for a free slot). Removes the "NEW " labels + staging header. Saves NON-PDF-compatible (lean). Dialogs off.
app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
var COPY="/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
// ordered: {staged base (no ext), anchor base (no ext)} — anchor must exist OR be placed earlier in this list
var MAP=[
 ["DEMO_lineplot_shape_by_metaphase_triple","DEMO_lineplot_shape_by_metaphase_single"],
 ["DEMO_shape_rate_vs_metaphase_triple","DEMO_shape_rate_vs_metaphase_single"],
 ["single_sisterless_length_congression","pole_to_plate_behavior_vs_duration"],
 ["triple_prometa_ablation_to_mitosis","pole_to_plate_jointime_vs_duration"],
 ["metaphase_duration_delta_from_unmodified","G1_violin2_mitotic_duration"],
 ["ablation_count_by_cohort","G1_survival"],
 ["ablation_count_on_vs_offpooled","ablation_count_by_cohort"],
 ["G4_zm_by_target","G4_zm_by_target_zoom"],
 ["20250501_ptk_yfpcdc20_12_frap0","20250411_ptk_yfpcdc20_13_frap0_aligned"]
];
var GAP=14.0;

var d=null;
for (var q=0;q<app.documents.length;q++){ if(app.documents[q].name=="ablation_figures_grouped copy.ai"){ d=app.documents[q]; break; } }
var opened=false; if(!d){ d=app.open(new File(COPY)); opened=true; }

function baseOf(pi){ var f=null; try{f=pi.file;}catch(e){} if(!f) return null;
  return decodeURI(f.name).toLowerCase().replace(/\.(pdf|png|svg)$/,""); }
function findPlaced(base){ base=base.toLowerCase();
  for (var i=0;i<d.placedItems.length;i++){ if(baseOf(d.placedItems[i])==base) return d.placedItems[i]; } return null; }
function overlaps(a,b){ // visibleBounds = [left,top,right,bottom]; top>bottom
  return !(a[2]<=b[0] || a[0]>=b[2] || a[3]>=b[1] || a[1]<=b[3]); }
function collides(rect,selfItem){
  for (var i=0;i<d.placedItems.length;i++){ var it=d.placedItems[i]; if(it===selfItem) continue;
    var b; try{b=it.visibleBounds;}catch(e){continue;} if(overlaps(rect,b)) return true; } return false; }

var report=[];
for (var m=0;m<MAP.length;m++){
  var sb=MAP[m][0], ab=MAP[m][1];
  var item=findPlaced(sb), anch=findPlaced(ab);
  if(!item){ report.push(sb+": staged item NOT FOUND"); continue; }
  if(!anch){ report.push(sb+": anchor '"+ab+"' NOT FOUND (left in place)"); continue; }
  var ab_b=anch.visibleBounds;                 // [l,t,r,b]
  var aw=anch.width, al=ab_b[0], at=ab_b[1], abot=ab_b[3];
  // match width to anchor
  var sc=aw/item.width; item.width=item.width*sc; item.height=item.height*sc;
  var ih=item.height;
  // candidate: directly below anchor, left-aligned; search downward for a free slot
  var top=abot-GAP, tries=0;
  while(tries<40){
    var rect=[al, top, al+item.width, top-ih];
    if(!collides(rect,item)) break;
    top=top-(ih+GAP); tries++;
  }
  item.position=[al, top];
  item.name=sb;                                // drop the "NEW " marker
  report.push(sb+" -> below "+ab+" (tries="+tries+")");
}
// cleanup: delete the staging header + leftover "NEW ..." caption textframes
var kill=[];
for (var i=0;i<d.textFrames.length;i++){ var t=d.textFrames[i]; var c="";
  try{c=t.contents;}catch(e){}
  if(c && (c.indexOf("NEW _triple")>=0 || c.indexOf("figure(s) from the PDF deck")>=0 || c.indexOf("drag into")>=0)) kill.push(t);
  else { for (var m2=0;m2<MAP.length;m2++){ if(c===MAP[m2][0]){ kill.push(t); break; } } }
}
for (var k=0;k<kill.length;k++){ try{kill[k].remove();}catch(e){} }

var so=new IllustratorSaveOptions(); so.pdfCompatible=false;
d.saveAs(new File(COPY), so);
if(opened){ d.close(SaveOptions.DONOTSAVECHANGES); }
"placed="+report.length+" :: "+report.join(" | ")+" | labels_removed="+kill.length;
