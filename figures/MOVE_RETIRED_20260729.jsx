// Move EVERY figure flagged retired in PLOT_SETTINGS onto the RETIRED artboard (user 2026-07-29:
// "there are many plots on the non-retirement artboards that are, nonetheless, branded with the
// 'retirement' red text. either remove this branding or move them to the retirement artboard").
// 27 ids carry retired=True with a retired_on / retired_reason / superseded_by record.
// Figures are MOVED, never deleted, then the retired board is repacked so nothing overlaps.
#target illustrator
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
function readFile(p){ var f=new File(p); f.encoding="UTF-8"; f.open("r"); var s=f.read(); f.close(); return s; }
var RET = eval("(" + readFile("/Volumes/4 MB/_working/_deck_jsx_inputs/retired.json") + ")");
var want = {}; for (var i=0;i<RET.length;i++) want[String(RET[i]).toLowerCase()] = 1;

var PATH = "/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
var d = app.open(new File(PATH));
function lname(p){ var f=null; try{f=p.file;}catch(e){} return f?decodeURI(f.name).toLowerCase().replace(/\.(pdf|png)$/,""):""; }
function abOf(it){ var b; try{b=it.visibleBounds;}catch(e){return -1;}
  var cx=(b[0]+b[2])/2, cy=(b[1]+b[3])/2;
  for(var a=0;a<d.artboards.length;a++){ var R=d.artboards[a].artboardRect;
    if(cx>=R[0]&&cx<=R[2]&&cy<=R[1]&&cy>=R[3]) return a; } return -1; }
var ri=-1;
for(var a0=0;a0<d.artboards.length;a0++) if(d.artboards[a0].name.toUpperCase().indexOf("RETIRED")>=0){ri=a0;break;}
if(ri<0) throw new Error("no RETIRED artboard");

var offboard=[], members=[];
for(var i2=0;i2<d.placedItems.length;i2++){
  var p=d.placedItems[i2], n=lname(p), ab=abOf(p);
  if(ab===ri){ members.push(p); continue; }
  if(want[n]){ offboard.push(n+" @AB"+(ab+1)); members.push(p); }
}
var R=d.artboards[ri].artboardRect, n2=members.length;
var cols=Math.ceil(Math.sqrt(n2)), rows=Math.ceil(n2/cols), M=18, GAP=10;
var cw=((R[2]-R[0])-2*M-(cols-1)*GAP)/cols, ch=((R[1]-R[3])-2*M-(rows-1)*GAP)/rows;
for(var m=0;m<n2;m++){
  var it=members[m], iw=it.width, ih=it.height, s=Math.min(cw/iw, ch/ih);
  it.width=iw*s; it.height=ih*s;
  var c=m%cols, r2=Math.floor(m/cols);
  it.position=[R[0]+M+c*(cw+GAP)+(cw-it.width)/2, R[1]-M-r2*(ch+GAP)-(ch-it.height)/2];
}
var mode="";
try{ var so=new IllustratorSaveOptions(); so.pdfCompatible=false; d.saveAs(new File(PATH), so); mode="saved"; }
catch(e3){ mode="SAVE_FAILED "+e3; }
var tot=d.placedItems.length, abn=d.artboards[ri].name;
try{ d.close(SaveOptions.DONOTSAVECHANGES); }catch(e4){}
"retired ids in settings="+RET.length+"  MOVED onto AB"+(ri+1)+" '"+abn+"'="+offboard.length+
"  retired board now holds="+n2+"  placed_total="+tot+"  grid="+cols+"x"+rows+"  save="+mode+
"\nmoved: "+offboard.join(" ; ");
