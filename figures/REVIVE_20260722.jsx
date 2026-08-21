#target illustrator
// REVIVE two things and mark them so the revival is visible:
//   1. the 4 collagenON figures -- the CURRENT on-target versions, which were sitting on the RETIRED
//      artboard -- moved to the artboard named for collagen variants;
//   2. DEMO_lineplot_shape_by_metaphase -- registered, its SIGHILITE box exists, but the figure itself
//      was not in the document, leaving that box floating. Placing it resolves the orphan.
// Each revived figure gets a BROWN OUTLINE: a stroke-only rectangle (no fill) so a yellow SIGHILITE can
// still sit behind it and both read at once. Outlines go on their own layer so they can be removed
// wholesale later.
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var COPY="/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
var TMP ="/Volumes/4 MB/ablation_plots/_tmp_revive_20260722.ai";
var PDFDIR="/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/";
var d = app.open(new File(COPY));
function lname(p){var f=null;try{f=p.file;}catch(e){}return f?decodeURI(f.name).replace(/\.[^.]+$/,""):"";}
function abIndexByName(frag){
  for(var a=0;a<d.artboards.length;a++)
    if(d.artboards[a].name.toUpperCase().indexOf(frag)>=0) return a;
  return -1;
}
// brown, in whichever colour space this document uses
function brown(){
  if(d.documentColorSpace==DocumentColorSpace.CMYK){
    var c=new CMYKColor(); c.cyan=30; c.magenta=70; c.yellow=100; c.black=25; return c;
  }
  var r=new RGBColor(); r.red=139; r.green=69; r.blue=19; return r;
}
var LAYER="REVIVED_OUTLINE", lay=null;
try{ lay=d.layers.getByName(LAYER); }catch(e){ lay=d.layers.add(); lay.name=LAYER; }

var TARGET_AB = abIndexByName("COLLAGEN VARIANT");
if(TARGET_AB<0) TARGET_AB = abIndexByName("COLLAGEN");
var revived=[];

// ---- 1. move the collagenON figures off the RETIRED artboard
var WANT={"collagenON_vs_triple_area_binned":1,"collagenON_vs_triple_area_linear":1,
          "collagenON_vs_triple_roundness_binned":1,"collagenON_vs_triple_roundness_linear":1};
var move=[], existing=[];
var R=d.artboards[TARGET_AB].artboardRect;
for(var i=0;i<d.placedItems.length;i++){
  var p=d.placedItems[i], n=lname(p), b;
  try{b=p.visibleBounds;}catch(e){continue;}
  var cx=(b[0]+b[2])/2, cy=(b[1]+b[3])/2;
  var onTarget=(cx>=R[0]&&cx<=R[2]&&cy<=R[1]&&cy>=R[3]);
  if(WANT[n]===1 && !onTarget) move.push(p);
  else if(onTarget) existing.push(p);
}
// ---- 2. place the missing DEMO figure beside its siblings
var sibAB=-1;
for(var i2=0;i2<d.placedItems.length;i2++){
  if(lname(d.placedItems[i2])=="DEMO_lineplot_shape_by_metaphase_single"){
    var bb=d.placedItems[i2].visibleBounds, ccx=(bb[0]+bb[2])/2, ccy=(bb[1]+bb[3])/2;
    for(var a2=0;a2<d.artboards.length;a2++){var rr=d.artboards[a2].artboardRect;
      if(ccx>=rr[0]&&ccx<=rr[2]&&ccy<=rr[1]&&ccy>=rr[3]){sibAB=a2;break;}}
    break;
  }
}
var demo=null;
var nf=new File(PDFDIR+"DEMO_lineplot_shape_by_metaphase.pdf");
if(nf.exists && sibAB>=0){
  demo=d.activeLayer.placedItems.add(); demo.file=nf; demo.name="REVIVED DEMO_lineplot_shape_by_metaphase";
}

// pack the collagen artboard: existing + moved in
var members=existing.concat(move);
var n=members.length, cols=Math.ceil(Math.sqrt(n)), rows=Math.ceil(n/cols), M=18, GAP=10;
var cw=((R[2]-R[0])-2*M-(cols-1)*GAP)/cols, ch=((R[1]-R[3])-2*M-(rows-1)*GAP)/rows;
for(var k=0;k<n;k++){
  var it=members[k], s=Math.min(cw/it.width, ch/it.height);
  it.width*=s; it.height*=s;
  var c=k%cols, r2=Math.floor(k/cols);
  it.position=[R[0]+M+c*(cw+GAP)+(cw-it.width)/2, R[1]-M-r2*(ch+GAP)-(ch-it.height)/2];
}
for(var m=0;m<move.length;m++) revived.push(move[m]);

// seat the DEMO figure in a free slot on its siblings' artboard
if(demo){
  var Rs=d.artboards[sibAB].artboardRect;
  var occ=[];
  for(var i3=0;i3<d.placedItems.length;i3++){
    if(d.placedItems[i3]===demo) continue;
    try{occ.push(d.placedItems[i3].visibleBounds);}catch(e){}
  }
  function free(bx){
    for(var q=0;q<occ.length;q++){var a=occ[q];
      var l=Math.max(a[0],bx[0]),r=Math.min(a[2],bx[2]),t=Math.min(a[1],bx[1]),bo=Math.max(a[3],bx[3]);
      if(r>l&&t>bo){var ia=(r-l)*(t-bo),ba=(bx[2]-bx[0])*(bx[1]-bx[3]); if(ia>0.03*ba) return false;}}
    return true;
  }
  var sc=440/demo.width; demo.width*=sc; demo.height*=sc;
  var w=demo.width,h=demo.height,got=null;
  for(var x=Rs[0]+12;x+w<=Rs[2]-12&&!got;x+=Math.max(20,w/3))
    for(var y=Rs[1]-12;y-h>=Rs[3]+12&&!got;y-=Math.max(20,h/3))
      if(free([x,y,x+w,y-h])) got=[x,y];
  if(!got){ demo.width*=0.45; demo.height*=0.45; w=demo.width; h=demo.height;
    for(var x2=Rs[0]+12;x2+w<=Rs[2]-12&&!got;x2+=Math.max(20,w/3))
      for(var y2=Rs[1]-12;y2-h>=Rs[3]+12&&!got;y2-=Math.max(20,h/3))
        if(free([x2,y2,x2+w,y2-h])) got=[x2,y2]; }
  if(got){ demo.position=got; revived.push(demo); }
}

// ---- brown outlines on the revived figures (stroke only, so a yellow highlight still shows through)
var col=brown(), drawn=0;
for(var v=0;v<revived.length;v++){
  var bb2=revived[v].visibleBounds, pad=5;
  var rect=lay.pathItems.rectangle(bb2[1]+pad, bb2[0]-pad,
                                   (bb2[2]-bb2[0])+2*pad, (bb2[1]-bb2[3])+2*pad);
  rect.filled=false; rect.stroked=true; rect.strokeColor=col; rect.strokeWidth=3;
  rect.name="REVIVED "+lname(revived[v]);
  drawn++;
}
// re-anchor the previously-orphaned SIGHILITE onto the now-present DEMO figure
var fixed=0;
if(demo){
  for(var i4=0;i4<d.pathItems.length;i4++){
    var q=d.pathItems[i4];
    if(q.name=="SIGHILITE DEMO_lineplot_shape_by_metaphase"){
      var fb=demo.visibleBounds;
      q.width=fb[2]-fb[0]; q.height=fb[1]-fb[3]; q.position=[fb[0],fb[1]]; fixed++;
    }
  }
}
var mode="";
try{var so=new IllustratorSaveOptions(); so.pdfCompatible=true; d.saveAs(new File(TMP), so); mode="ok";}
catch(e){ mode="SAVE_FAILED "+e; }
"target_AB=AB"+(TARGET_AB+1)+" '"+d.artboards[TARGET_AB].name+"'  collagen_moved="+move.length+
"  demo_placed="+(demo?"yes on AB"+(sibAB+1):"NO")+"  brown_outlines="+drawn+
"  orphan_SIGHILITE_reanchored="+fixed+"  save="+mode;
