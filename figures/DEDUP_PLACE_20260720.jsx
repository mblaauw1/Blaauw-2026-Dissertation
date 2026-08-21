#target illustrator
// copy.ai integrity pass: (A) remove floating off-artboard duplicate copies (keep on-artboard copy);
// (B) dedup redundant copies on the RETIRED board (keep 1 each); (C) place 5 missing DEMO plots.
// NEVER removes a basename's last copy. Leaves manual-artboard (22-29) duplicates intact. Backgrounded, non-PDF save.
app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
var COPY="/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
var PDF="/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/";
var d=null; for(var q=0;q<app.documents.length;q++){if(app.documents[q].name=="ablation_figures_grouped copy.ai"){d=app.documents[q];break;}}
var opened=false; if(!d){d=app.open(new File(COPY));opened=true;}
var lyr=d.activeLayer; var rep=[];
function baseOf(pi){var f=null;try{f=pi.file;}catch(e){}if(!f)return null;return decodeURI(f.name).replace(/\.(pdf|png|svg)$/i,"");}
function inAnyArtboard(b){ var cx=(b[0]+b[2])/2, cy=(b[1]+b[3])/2;
  for(var a=0;a<d.artboards.length;a++){var r=d.artboards[a].artboardRect; if(cx>=r[0]&&cx<=r[2]&&cy<=r[1]&&cy>=r[3]) return true;} return false; }
function copiesOf(base){ var out=[]; for(var i=0;i<d.placedItems.length;i++){ if(baseOf(d.placedItems[i])==base) out.push(d.placedItems[i]); } return out; }
function findPlaced(base){ for(var i=0;i<d.placedItems.length;i++){ if(baseOf(d.placedItems[i])==base) return d.placedItems[i]; } return null; }
function overlaps(a,b){ return !(a[2]<=b[0]||a[0]>=b[2]||a[3]>=b[1]||a[1]<=b[3]); }
function collides(rect,self){ for(var i=0;i<d.placedItems.length;i++){var it=d.placedItems[i];if(it===self)continue;var b;try{b=it.visibleBounds;}catch(e){continue;}if(overlaps(rect,b))return true;} return false; }

// (A) remove floating off-artboard duplicate copies (keep an on-artboard copy)
var FLOAT=["20250411_ptk_yfpcdc20_13_frap0_aligned","DEMO_lineplot_shape_by_metaphase_single","G1_survival",
"G1_violin1_attempts_vs_duration","G1_violin2_mitotic_duration_journal","G2_duration_combined","G2_duration_statgrid",
"G4_cdc20_intensity_near_poles","G4_exhaustion_statgrid","G4_exhaustion_violin_journal","G4_frap_vs_complete_targeted"];
var remA=0;
for(var i=0;i<FLOAT.length;i++){ var cs=copiesOf(FLOAT[i]); if(cs.length<2) continue;
  var onboard=0; for(var j=0;j<cs.length;j++){ var b; try{b=cs[j].visibleBounds;}catch(e){continue;} if(inAnyArtboard(b)) onboard++; }
  if(onboard<1) continue; // safety: never remove if none is on a board
  for(var j=cs.length-1;j>=0;j--){ var b; try{b=cs[j].visibleBounds;}catch(e){continue;} if(!inAnyArtboard(b)){ try{cs[j].remove(); remA++;}catch(e){} } }
}
rep.push("removed "+remA+" floating dup copies");

// (B) dedup redundant copies on the retired board (keep FIRST of each)
var AB30=["collagenON_vs_triple_area_binned","collagenON_vs_triple_area_linear","collagenON_vs_triple_roundness_binned",
"collagenON_vs_triple_roundness_linear","collagen_vs_triple_area","collagen_vs_triple_roundness"];
var remB=0;
for(var i=0;i<AB30.length;i++){ var cs=copiesOf(AB30[i]); for(var j=cs.length-1;j>=1;j--){ try{cs[j].remove(); remB++;}catch(e){} } }
rep.push("removed "+remB+" retired-board redundant copies");

// (C) place 5 missing DEMO plots below a placed DEMO sibling
var MISS=["DEMO_lineplot_shape_by_metaphase","DEMO_lineplot_shape_by_metaphase_area",
"DEMO_lineplot_shape_by_metaphase_single_area","DEMO_lineplot_shape_by_metaphase_triple_area","DEMO_shape_rate_vs_metaphase"];
var prev="DEMO_lineplot_shape_by_metaphase_single";
for(var i=0;i<MISS.length;i++){ if(findPlaced(MISS[i])){ rep.push(MISS[i]+" already present"); prev=MISS[i]; continue; }
  var anch=findPlaced(prev); var f=new File(PDF+MISS[i]+".pdf");
  if(!anch){ rep.push(MISS[i]+": no anchor"); continue; } if(!f.exists){ rep.push(MISS[i]+": PDF missing"); continue; }
  var it=lyr.placedItems.add(); it.file=f; var ab=anch.visibleBounds,al=ab[0],abot=ab[3],aw=anch.width;
  var sc=aw/it.width; it.width*=sc; it.height*=sc; var ih=it.height,top=abot-14,t=0;
  while(t<80){var r=[al,top,al+it.width,top-ih]; if(!collides(r,it))break; top-=(ih+14); t++;}
  it.position=[al,top]; it.name=MISS[i]; prev=MISS[i]; rep.push("placed "+MISS[i]+" (tries="+t+")");
}
var so=new IllustratorSaveOptions(); so.pdfCompatible=false; d.saveAs(new File(COPY),so);
if(opened){d.close(SaveOptions.DONOTSAVECHANGES);}
"DONE :: "+rep.join(" | ");
