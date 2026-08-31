#target illustrator
// Backgrounded copy.ai repair (no activate): (1) remove stacked duplicate placements (keep first of each basename);
// (2) separate 2 known cross-plot overlaps; (3) place 4 missing collagen-vs-triple plots; (4) highlight the
// defensible statistically-significant plots (primary finding p<0.05). Saves NON-PDF-compatible. Dialogs off.
app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
var COPY="/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
var PDF="/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/";
var d=null;
for (var q=0;q<app.documents.length;q++){ if(app.documents[q].name=="ablation_figures_grouped copy.ai"){ d=app.documents[q]; break; } }
var opened=false; if(!d){ d=app.open(new File(COPY)); opened=true; }
var lyr=d.activeLayer; var rep=[];

function baseOf(pi){ var f=null; try{f=pi.file;}catch(e){} if(!f) return null;
  return decodeURI(f.name).toLowerCase().replace(/\.(pdf|png|svg)$/,""); }
function findPlaced(base){ base=base.toLowerCase();
  for (var i=0;i<d.placedItems.length;i++){ if(baseOf(d.placedItems[i])==base) return d.placedItems[i]; } return null; }
function overlaps(a,b){ return !(a[2]<=b[0] || a[0]>=b[2] || a[3]>=b[1] || a[1]<=b[3]); }
function collides(rect,selfItem){ for (var i=0;i<d.placedItems.length;i++){ var it=d.placedItems[i]; if(it===selfItem) continue;
  var b; try{b=it.visibleBounds;}catch(e){continue;} if(overlaps(rect,b)) return true; } return false; }
function placeBelow(item, anch, gap){ var ab=anch.visibleBounds; var al=ab[0], abot=ab[3], aw=anch.width;
  var sc=aw/item.width; item.width=item.width*sc; item.height=item.height*sc; var ih=item.height, top=abot-gap, tries=0;
  while(tries<80){ var rect=[al, top, al+item.width, top-ih]; if(!collides(rect,item)) break; top=top-(ih+gap); tries++; }
  item.position=[al, top]; return tries; }

// ---------- (1) remove stacked duplicate placements (keep FIRST of each basename) ----------
var seen={}, removed=0;
for (var i=d.placedItems.length-1;i>=0;i--){ }  // (iterate forward, collect dups to remove)
var toRemove=[];
var firstOf={};
for (var i=0;i<d.placedItems.length;i++){ var b=baseOf(d.placedItems[i]); if(!b) continue;
  if(firstOf[b]===undefined){ firstOf[b]=i; } else {
    // duplicate: only remove if it substantially overlaps the kept one (true stacked dup)
    var a1=d.placedItems[firstOf[b]].visibleBounds, a2=d.placedItems[i].visibleBounds;
    if(overlaps(a1,a2)) toRemove.push(d.placedItems[i]);
  }
}
for (var k=0;k<toRemove.length;k++){ try{ toRemove[k].remove(); removed++; }catch(e){} }
rep.push("removed "+removed+" stacked dup placements");

// ---------- (2) separate the 2 real cross-plot overlaps ----------
var OVL=[["single_sisterless_length_congression","G4_sisbehav_lastcongress_vs_duration"],
         ["G2_prophase_dynamics_zoom","G2_prometaphase_dynamics_lastablation"]];
for (var o=0;o<OVL.length;o++){ var mover=findPlaced(OVL[o][0]), anch=findPlaced(OVL[o][1]);
  if(mover&&anch){ var t=placeBelow(mover,anch,16); rep.push("separated "+OVL[o][0]+" (tries="+t+")"); }
  else rep.push("overlap-pair not both found: "+OVL[o][0]); }

// ---------- (3) place 4 missing collagen-vs-triple plots ----------
var ANCHORS=["G3_chromo_length","single_sisterless_length_congression","G4_sisbehav_fracjoined_vs_duration"];
function firstAnchor(){ for(var i=0;i<ANCHORS.length;i++){ var a=findPlaced(ANCHORS[i]); if(a) return a; } return null; }
var MISS=["custom_collagen_vs_triple_2or3_ontarget_roundness_meta_to_ana","custom_collagen_vs_triple_2or3_ontarget_area_meta_to_ana",
          "custom_collagen_vs_triple_offtarget_triple_roundness_meta_to_ana","custom_collagen_vs_triple_offtarget_triple_area_meta_to_ana"];
var prevBase=null;
for (var m=0;m<MISS.length;m++){ if(findPlaced(MISS[m])){ rep.push(MISS[m]+" already present"); prevBase=MISS[m]; continue; }
  var pf=new File(PDF+MISS[m]+".pdf"); if(!pf.exists){ rep.push(MISS[m]+" PDF MISSING"); continue; }
  var anch = prevBase? findPlaced(prevBase) : firstAnchor();
  if(!anch){ rep.push(MISS[m]+" no anchor"); continue; }
  var it=lyr.placedItems.add(); it.file=pf; var t=placeBelow(it,anch,14); it.name=MISS[m]; prevBase=MISS[m];
  rep.push("placed "+MISS[m]+" (tries="+t+")"); }

// ---------- (4) highlight defensible-significant plots (primary finding p<0.05) ----------
var SIG=["G4_sisbehav_lastcongress_vs_duration","pole_to_plate_jointime_vs_duration","pole_to_plate_behavior_vs_duration",
 "G4_polar_lagging_vs_duration","G1_survival","G1_violin1_attempts_vs_duration","G1_start_rounded_vs_duration",
 "G1_start_rounded_metaphase","G2_dur_meta_to_ana","G2_dur_meta_to_ana_journal","G2_duration_combined","G2_dur_ana_to_cyto",
 "G2_dur_ana_to_cyto_journal","G2_dur_align_to_meta","G2_dur_align_to_meta_journal","G2_metaphase_dynamics_prometa",
 "G2_phase_split_violin_v2","G2_phase_split_violin_v2_journal","G2_phase_split_violin_v2_tripledouble",
 "G2_phase_split_violin_v2_tripledouble_journal","G2_prometa_combined_13","G2_prometa_combined_123"];
var hl=null; try{ hl=d.layers.getByName("SIG_HIGHLIGHT"); }catch(e){ hl=d.layers.add(); hl.name="SIG_HIGHLIGHT"; }
for (var i=hl.pathItems.length-1;i>=0;i--){ try{hl.pathItems[i].remove();}catch(e){} }
hl.zOrder(ZOrderMethod.SENDTOBACK);
var yc=new RGBColor(); yc.red=255; yc.green=238; yc.blue=120; var PAD=18.0, nH=0;
for (var s=0;s<SIG.length;s++){ var it=findPlaced(SIG[s]); if(!it) continue; var b=it.visibleBounds;
  var rr=hl.pathItems.roundedRectangle(b[1]+PAD,b[0]-PAD,(b[2]-b[0])+2*PAD,(b[1]-b[3])+2*PAD,14,14);
  rr.filled=true; rr.stroked=false; rr.fillColor=yc; rr.opacity=38; rr.name="SIGHILITE "+SIG[s]; nH++; }
rep.push("highlighted "+nH+"/"+SIG.length+" significant plots");

var so=new IllustratorSaveOptions(); so.pdfCompatible=false;
d.saveAs(new File(COPY), so);
if(opened){ d.close(SaveOptions.DONOTSAVECHANGES); }
"DONE :: "+rep.join(" | ");
