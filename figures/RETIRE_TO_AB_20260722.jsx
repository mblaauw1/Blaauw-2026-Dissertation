#target illustrator
// Move every RETIRED figure onto the artboard already named "RETIRED", then repack that artboard so
// everything fits -- shrinking the figures already there if necessary (user instruction 2026-07-22).
// Nothing is deleted; figures are relocated, so any of this is reversible by moving them back.
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var COPY="/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
var TMP ="/Volumes/4 MB/ablation_plots/_tmp_retire_20260722.ai";
var RET = ["G1_violin2_mitotic_duration.pdf", "G1_violin2_mitotic_duration_zoom.pdf", "G1_violin2_no_dc_offtarget.pdf", "G1_violin2_no_dc_offtarget_zoom.pdf", "G1_violin2_sisterless_1234.pdf", "G1_violin2_sisterless_1234_zoom.pdf", "G2_dur_align_to_meta.pdf", "G2_dur_ana_to_cyto.pdf", "G2_dur_ana_to_cyto_zoom.pdf", "G2_dur_meta_to_ana.pdf", "G2_dur_meta_to_ana_zoom.pdf", "G2_dur_neb_to_meta.pdf", "G2_dur_neb_to_meta_zoom.pdf", "G2_duration_combined.pdf", "G2_duration_combined_zoom.pdf", "G2_phase_split_violin.pdf", "G2_phase_split_violin_v2.pdf", "G2_phase_split_violin_v2_tripledouble.pdf", "G4_exhaustion_violin.pdf", "G1_violin2_mitotic_duration.png", "G1_violin2_mitotic_duration_zoom.png", "G1_violin2_no_dc_offtarget.png", "G1_violin2_no_dc_offtarget_zoom.png", "G1_violin2_sisterless_1234.png", "G1_violin2_sisterless_1234_zoom.png", "G2_dur_align_to_meta.png", "G2_dur_ana_to_cyto.png", "G2_dur_ana_to_cyto_zoom.png", "G2_dur_meta_to_ana.png", "G2_dur_meta_to_ana_zoom.png", "G2_dur_neb_to_meta.png", "G2_dur_neb_to_meta_zoom.png", "G2_duration_combined.png", "G2_duration_combined_zoom.png", "G2_phase_split_violin.png", "G2_phase_split_violin_v2.png", "G2_phase_split_violin_v2_tripledouble.png", "G4_exhaustion_violin.png"];
var d = app.open(new File(COPY));
function lname(p){var f=null;try{f=p.file;}catch(e){}return f?decodeURI(f.name).toLowerCase():"";}
var want={}; for(var i=0;i<RET.length;i++) want[RET[i].toLowerCase()]=1;

// locate the RETIRED artboard by NAME (not by index -- indices shift)
var ri=-1;
for(var a=0;a<d.artboards.length;a++) if(d.artboards[a].name.toUpperCase().indexOf("RETIRED")>=0){ri=a;break;}
if(ri<0) throw new Error("no artboard named RETIRED");
var R=d.artboards[ri].artboardRect;   // [l,t,r,b]

// everything that should end up on it: what is already there + every retired figure anywhere
var members=[], moved=0, already=0;
for(var i2=0;i2<d.placedItems.length;i2++){
  var p=d.placedItems[i2], b;
  try{b=p.visibleBounds;}catch(e){continue;}
  var cx=(b[0]+b[2])/2, cy=(b[1]+b[3])/2;
  var onRet = (cx>=R[0]&&cx<=R[2]&&cy<=R[1]&&cy>=R[3]);
  var isRet = want[lname(p)]===1;
  if(onRet){ members.push(p); if(isRet) already++; }
  else if(isRet){ members.push(p); moved++; }
}

// pack them into a grid that fits the artboard, preserving each figure's aspect ratio
var n=members.length;
var cols=Math.ceil(Math.sqrt(n)); var rows=Math.ceil(n/cols);
var M=18, GAP=10;
var cw=((R[2]-R[0])-2*M-(cols-1)*GAP)/cols;
var ch=((R[1]-R[3])-2*M-(rows-1)*GAP)/rows;
for(var k=0;k<n;k++){
  var it=members[k], w=it.width, h=it.height;
  var s=Math.min(cw/w, ch/h);          // uniform scale -- never distorts
  it.width=w*s; it.height=h*s;
  var c=k%cols, r2=Math.floor(k/cols);
  var x=R[0]+M+c*(cw+GAP)+(cw-it.width)/2;
  var y=R[1]-M-r2*(ch+GAP)-(ch-it.height)/2;
  it.position=[x,y];
}
var mode="";
try{var so=new IllustratorSaveOptions(); so.pdfCompatible=true; d.saveAs(new File(TMP), so); mode="ok";}
catch(e){ mode="SAVE_FAILED "+e; }
"RETIRED artboard AB"+(ri+1)+" '"+d.artboards[ri].name+"'  moved_in="+moved+
"  already_there="+already+"  total_now="+n+"  grid="+cols+"x"+rows+"  save="+mode;
