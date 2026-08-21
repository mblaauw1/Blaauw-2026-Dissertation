#target illustrator
// ONE consolidated copy.ai pass (2026-07-19):
//  (1) relink hec1 timestrips (xy2/4/5/6 + dot_quant) to current renders
//  (2) place 5 new plots below anchors, collision-avoided, de-stacking any existing copy
//  (3) draw soft-yellow highlight rects BEHIND the verified-significant relationship plots
// Saves NON-PDF-compatible (lean). Dialogs suppressed.
app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
var COPY="/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
var PDF="/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/";
var G4="/Volumes/4 MB/ablation_figures_20260625/group4/";

var d=null;
for (var q=0;q<app.documents.length;q++){ if(app.documents[q].name=="ablation_figures_grouped copy.ai"){ d=app.documents[q]; break; } }
var opened=false; if(!d){ d=app.open(new File(COPY)); opened=true; }
var lyr=d.activeLayer;
var report=[];

function baseOf(pi){ var f=null; try{f=pi.file;}catch(e){} if(!f) return null;
  return decodeURI(f.name).toLowerCase().replace(/\.(pdf|png|svg)$/,""); }
function findPlaced(base){ base=base.toLowerCase();
  for (var i=0;i<d.placedItems.length;i++){ if(baseOf(d.placedItems[i])==base) return d.placedItems[i]; } return null; }
function overlaps(a,b){ return !(a[2]<=b[0] || a[0]>=b[2] || a[3]>=b[1] || a[1]<=b[3]); }
function collides(rect,selfItem){
  for (var i=0;i<d.placedItems.length;i++){ var it=d.placedItems[i]; if(it===selfItem) continue;
    var b; try{b=it.visibleBounds;}catch(e){continue;} if(overlaps(rect,b)) return true; } return false; }
function placeBelow(item, anch, gap){
  var ab=anch.visibleBounds; var al=ab[0], abot=ab[3], aw=anch.width;
  var sc=aw/item.width; item.width=item.width*sc; item.height=item.height*sc;
  var ih=item.height, top=abot-gap, tries=0;
  while(tries<60){ var rect=[al, top, al+item.width, top-ih]; if(!collides(rect,item)) break; top=top-(ih+gap); tries++; }
  item.position=[al, top]; return tries;
}

// ---------- (1) RELINK hec1 timestrips + dot_quant ----------
var HEC=["G5_item4_hec1_timestrip_xy2","G5_item4_hec1_timestrip_xy4","G5_item4_hec1_timestrip_xy5",
         "G5_item4_hec1_timestrip_xy6","G5_hec1_mad1_dot_quant"];
for (var h=0;h<HEC.length;h++){
  var pi=findPlaced(HEC[h]); var pngf=new File(G4+HEC[h]+".png");
  if(pi && pngf.exists){ try{ pi.file=pngf; report.push("relink "+HEC[h]); }catch(e){ report.push("RELINK-ERR "+HEC[h]+": "+e); } }
  else if(!pi){ report.push("hec1 NOT PLACED (staged below): "+HEC[h]); }
  else { report.push("hec1 png MISSING: "+HEC[h]); }
}

// ---------- (2) PLACE 5 new plots below anchors (de-stack if already present) ----------
// [plot, anchor, gap]
var NEW=[
 ["G4_congression_score_vs_duration","G4_sisbehav_lastcongress_vs_duration",14],
 ["G4_congression_score_sum_vs_duration","G4_congression_score_vs_duration",14],
 ["G4_congression_score_ranked","G4_congression_score_sum_vs_duration",14],
 ["G4_lagging_vs_congression_fraction","pole_to_plate_jointime_vs_duration",14],
 ["G4_lagging_count_vs_congression_time","G4_lagging_vs_congression_fraction",14]
];
for (var n=0;n<NEW.length;n++){
  var pb=NEW[n][0], ab=NEW[n][1], gap=NEW[n][2];
  var anch=findPlaced(ab);
  if(!anch){ report.push(pb+": anchor '"+ab+"' NOT FOUND — skipped"); continue; }
  var item=findPlaced(pb);
  if(!item){
    var pf=new File(PDF+pb+".pdf");
    if(!pf.exists){ report.push(pb+": PDF missing — skipped"); continue; }
    item=lyr.placedItems.add(); item.file=pf;
  }
  var t=placeBelow(item, anch, gap); item.name=pb;
  report.push(pb+" -> below "+ab+" (tries="+t+")");
}

// ---------- (3) SIGNIFICANCE highlights (behind, on a bottom layer) ----------
var SIG=["G4_sisbehav_lastcongress_vs_duration","pole_to_plate_jointime_vs_duration"];
var hl=null;
try{ hl=d.layers.getByName("SIG_HIGHLIGHT"); }catch(e){ hl=d.layers.add(); hl.name="SIG_HIGHLIGHT"; }
// clear old highlight rects
for (var i=hl.pathItems.length-1;i>=0;i--){ try{hl.pathItems[i].remove();}catch(e){} }
hl.zOrder(ZOrderMethod.SENDTOBACK);
var PAD=20.0;
var yc=new RGBColor(); yc.red=255; yc.green=238; yc.blue=120;
for (var s=0;s<SIG.length;s++){
  var it=findPlaced(SIG[s]);
  if(!it){ report.push("SIG anchor not placed: "+SIG[s]); continue; }
  var b=it.visibleBounds; // [l,t,r,b]
  var rr=hl.pathItems.roundedRectangle(b[1]+PAD, b[0]-PAD, (b[2]-b[0])+2*PAD, (b[1]-b[3])+2*PAD, 14,14);
  rr.filled=true; rr.stroked=false; rr.fillColor=yc; rr.opacity=38; rr.name="SIGHILITE "+SIG[s];
  report.push("highlight "+SIG[s]);
}

var so=new IllustratorSaveOptions(); so.pdfCompatible=false;
d.saveAs(new File(COPY), so);
if(opened){ d.close(SaveOptions.DONOTSAVECHANGES); }
"DONE :: "+report.join(" | ");
