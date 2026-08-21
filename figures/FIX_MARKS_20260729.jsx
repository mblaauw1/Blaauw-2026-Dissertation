// (a) Report where the 26 RED RETIRED_MARKS rectangles sit - red is not one of the four defined
//     conventions (yellow=significant, brown=revived, blue=model, grey=family), so any red box on a
//     NON-retired artboard is mislabelling a live figure.
// (b) Make the grey FAMILY_GROUP blocks actually visible: 13% of mid-grey on white is ~6% darkening.
//     Raise to a darker grey at higher opacity, still well below the 38% yellow so the yellow reads on top.
#target illustrator
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
// run over BOTH decks (2026-07-29): the overflow board also carries titles and, once its figures had
// real recorded data, significance rects - so any restyle must reach it too.
var DOCS=["/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai",
          "/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_kinetochore_overflow.ai"];
var REPORT=[];
for (var dk=0; dk<DOCS.length; dk++){
var PATH=DOCS[dk];
var d=app.open(new File(PATH));
var ri=-1;
for(var a=0;a<d.artboards.length;a++) if(d.artboards[a].name.toUpperCase().indexOf("RETIRED")>=0){ri=a;break;}
// the overflow deck has no RETIRED artboard; ri stays -1 and the red audit simply reports nothing
function abOf(it){ var b; try{b=it.visibleBounds;}catch(e){return -1;}
  var cx=(b[0]+b[2])/2, cy=(b[1]+b[3])/2;
  for(var q=0;q<d.artboards.length;q++){ var R=d.artboards[q].artboardRect;
    if(cx>=R[0]&&cx<=R[2]&&cy<=R[1]&&cy>=R[3]) return q; } return -1; }

// (a) where are the red marks?
var perAb={}, offboard=[];
try{
  var RL=d.layers.getByName("RETIRED_MARKS");
  for(var i=0;i<RL.pageItems.length;i++){
    var ab=abOf(RL.pageItems[i]), key="AB"+(ab+1);
    perAb[key]=(perAb[key]||0)+1;
    if(ab!==ri && offboard.length<24) offboard.push(key+":"+(RL.pageItems[i].name||RL.pageItems[i].typename));
  }
}catch(e){}

// (b) grey visible
var greyFixed=0;
try{
  var FL=d.layers.getByName("FAMILY_GROUP");
  for(var g=0;g<FL.pathItems.length;g++){
    var r=FL.pathItems[g];
    var c=new RGBColor(); c.red=120; c.green=124; c.blue=132;   // slightly blue-grey, reads as a group block
    r.fillColor=c; r.opacity=30; r.stroked=true;
    var s=new RGBColor(); s.red=95; s.green=99; s.blue=108;
    r.strokeColor=s; r.strokeWidth=0.75; greyFixed++;
  }
}catch(e2){}

var mode="";
try{ var so=new IllustratorSaveOptions(); so.pdfCompatible=false; d.saveAs(new File(PATH), so); mode="saved"; }
catch(e3){ mode="SAVE_FAILED "+e3; }
var lst=[]; for(var k in perAb) lst.push(k+"="+perAb[k]);
try{ d.close(SaveOptions.DONOTSAVECHANGES); }catch(e4){}
REPORT.push(PATH.replace(/^.*\//,"")+" :: RETIRED_MARKS ["+lst.join(", ")+"] retiredBoard=AB"+(ri+1)+
  "  red off-board="+offboard.length+"  grey restyled="+greyFixed+"  save="+mode);
}
REPORT.join("\n");
