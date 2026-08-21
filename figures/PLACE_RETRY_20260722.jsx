#target illustrator
// Operates on the ALREADY-OPEN document (it was left open when the previous saveAs was cancelled).
// Placement is IDEMPOTENT: a target already present is relinked, never duplicated.
// Saves to a NEW path — the in-place overwrite is what returned error 8700. The swap is done outside
// Illustrator only after the new file is verified (her standing rule: temp -> verify -> atomic swap).
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}
var d = app.activeDocument;
var PDFDIR = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/";
var TMP = "/Volumes/4 MB/ablation_plots/_tmp_copy_place_20260722.ai";
var TARGETS = ["G4_sisterless_cdc20_vs_bleaching.pdf", "G3_model_structured_performance.pdf"];
var ANCHOR = { "G4_sisterless_cdc20_vs_bleaching.pdf": ["g4_sisterless_fluor_postabl_vs_pole.pdf","g4_fluor_over_time.pdf"],
               "G3_model_structured_performance.pdf":  ["g3_plate_pole_predictive_model.pdf","g3_congression_score_vs_metaphase_duration.pdf"] };
function lname(p){var f=null;try{f=p.file;}catch(e){}return f?decodeURI(f.name).toLowerCase():"";}
var occupied=[],mine={},anchorOf={};
for(var i=0;i<d.placedItems.length;i++){
  var p=d.placedItems[i],n=lname(p),b;
  try{b=p.visibleBounds;}catch(e){continue;}
  var isT=false;
  for(var t=0;t<TARGETS.length;t++) if(n==TARGETS[t].toLowerCase()){mine[n]=p;isT=true;}
  if(!isT) occupied.push(b);
  for(var k in ANCHOR){var al=ANCHOR[k];
    for(var z=0;z<al.length;z++) if(n==al[z]){
      if(!anchorOf[k]) anchorOf[k]=p;
      else{var ob=anchorOf[k].visibleBounds,nb=b,onOld=false,onNew=false;
        for(var aa=0;aa<d.artboards.length;aa++){var rr=d.artboards[aa].artboardRect;
          var ocx=(ob[0]+ob[2])/2,ocy=(ob[1]+ob[3])/2,ncx=(nb[0]+nb[2])/2,ncy=(nb[1]+nb[3])/2;
          if(ocx>=rr[0]&&ocx<=rr[2]&&ocy<=rr[1]&&ocy>=rr[3])onOld=true;
          if(ncx>=rr[0]&&ncx<=rr[2]&&ncy<=rr[1]&&ncy>=rr[3])onNew=true;}
        if(!onOld&&onNew) anchorOf[k]=p;}
    }}
}
function overlaps(b){for(var i=0;i<occupied.length;i++){var a=occupied[i];
  var l=Math.max(a[0],b[0]),r=Math.min(a[2],b[2]),tp=Math.min(a[1],b[1]),bo=Math.max(a[3],b[3]);
  if(r>l&&tp>bo){var ia=(r-l)*(tp-bo),ba=(b[2]-b[0])*(b[1]-b[3]); if(ia>0.03*ba) return true;}}
  return false;}
var log=[];
for(var t2=0;t2<TARGETS.length;t2++){
  var nm=TARGETS[t2],key=nm.toLowerCase(),pi=mine[key],an=anchorOf[nm];
  if(pi){ try{pi.file=new File(PDFDIR+nm);}catch(e){} log.push(nm.replace(/\.pdf$/,"")+":ALREADY_PLACED_RELINKED"); continue; }
  var nf=new File(PDFDIR+nm);
  if(!nf.exists){log.push(nm+":NO_PDF");continue;}
  if(!an){log.push(nm+":NO_ANCHOR");continue;}
  pi=d.activeLayer.placedItems.add(); pi.file=nf; pi.name="NEW "+nm;
  var abw=an.visibleBounds[2]-an.visibleBounds[0],sc0=abw/pi.width;
  pi.width=pi.width*sc0; pi.height=pi.height*sc0;
  var ab=an.visibleBounds,acx=(ab[0]+ab[2])/2,acy=(ab[1]+ab[3])/2,ai=-1;
  for(var a2=0;a2<d.artboards.length;a2++){var r2=d.artboards[a2].artboardRect;
    if(acx>=r2[0]&&acx<=r2[2]&&acy<=r2[1]&&acy>=r2[3]){ai=a2;break;}}
  if(ai<0){log.push(nm+":ANCHOR_OFF_ARTBOARD");continue;}
  var R=d.artboards[ai].artboardRect,w=pi.width,h=pi.height,M=12,bestPos=null,bestD=1e18;
  var sx=Math.max(20,w/3),sy=Math.max(20,h/3);
  for(var x=R[0]+M;x+w<=R[2]-M;x+=sx)for(var y=R[1]-M;y-h>=R[3]+M;y-=sy){
    var c=[x,y,x+w,y-h]; if(overlaps(c))continue;
    var dx=(x+w/2)-acx,dy=(y-h/2)-acy,dd=dx*dx+dy*dy; if(dd<bestD){bestD=dd;bestPos=[x,y];}}
  if(!bestPos){var sc=0.45;pi.width=w*sc;pi.height=h*sc;w=pi.width;h=pi.height;
    for(var x3=R[0]+M;x3+w<=R[2]-M&&!bestPos;x3+=sx)for(var y3=R[1]-M;y3-h>=R[3]+M&&!bestPos;y3-=sy)
      if(!overlaps([x3,y3,x3+w,y3-h]))bestPos=[x3,y3];}
  if(!bestPos){log.push(nm+":NO_FREE_SLOT_ON_AB"+(ai+1));continue;}
  pi.position=bestPos; occupied.push([bestPos[0],bestPos[1],bestPos[0]+w,bestPos[1]-h]);
  log.push(nm.replace(/\.pdf$/,"")+":AB"+(ai+1));
}
var so=new IllustratorSaveOptions(); so.pdfCompatible=true;
d.saveAs(new File(TMP), so);
"PLACED: "+log.join(" | ")+"  SAVED_TO_TMP";
