// Place NEW figures onto a named artboard, making room her way: SCALE THE BOARD'S EXISTING CONTENTS DOWN,
// never spill onto another artboard.
//
// HER RULE (2026-08-19, repeated 2026-08-20): "if something didn't fit on an artboard it was supposed to go
// on, dont place on another artboard (this will cause confusion). instead, scale down the items on the
// target artboard so there's room." And 2026-08-20: "do take caution to place edited plots with care, in as
// similar a place to the original."
//
// LESSONS BAKED IN (each cost a failed pass earlier today):
//   * every placed item gets `.name` set, so later passes can find it -- DUMP_ALL9 identifies a figure by its
//     LINKED FILENAME, but my own passes match `.name`, and an item with neither is unfindable.
//   * items are fitted INSIDE their slot preserving the PDF's own aspect, so nothing is ever stretched.
//   * nothing is parked off-board: if a figure will not fit, it is REPORTED, not hidden at (90000,90000).
#target illustrator
var TMP="/Volumes/4 MB/_claude_tmp";
var PDF="/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf";
var PUB="/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf_pub";
function readAll(p){var f=new File(p);f.encoding="UTF-8";f.open("r");var s=f.read();f.close();return s;}
var plan=eval("("+readAll(TMP+"/place_plan.json")+")");
app.userInteractionLevel=UserInteractionLevel.DONTDISPLAYALERTS;
var report=[];
for(var ji=0;ji<plan.jobs.length;ji++){
  var J=plan.jobs[ji], doc=null;
  try{doc=app.open(new File(J.deck));}catch(e){report.push("OPEN FAIL "+J.deck);continue;}
  var docName=doc.name, i, j, lock=[];
  for(i=0;i<doc.layers.length;i++){var L=doc.layers[i],st={l:L,k:false};try{st.k=L.locked;L.locked=false;}catch(e){}lock.push(st);}
  var ab=doc.artboards[J.ab-1].artboardRect;          // [L,T,R,B]
  var abL=ab[0], abT=ab[1], abR=ab[2], abB=ab[3];
  // 1. shrink what is already on this artboard toward its top-left, freeing a strip at the bottom
  var onboard=[], k;
  for(k=0;k<doc.pageItems.length;k++){
    var it=doc.pageItems[k], b=null;
    try{b=it.geometricBounds;}catch(e){continue;}
    var cx=(b[0]+b[2])/2, cy=(b[1]+b[3])/2;
    if(cx>=abL&&cx<=abR&&cy<=abT&&cy>=abB) onboard.push(it);
  }
  for(k=0;k<onboard.length;k++){
    var it2=onboard[k], b2=null;
    try{b2=it2.geometricBounds;}catch(e){continue;}
    try{
      it2.left = abL + (b2[0]-abL)*J.k;
      it2.top  = abT - (abT-b2[1])*J.k;
      it2.width  = (b2[2]-b2[0])*J.k;
      it2.height = (b2[1]-b2[3])*J.k;
    }catch(e){}
  }
  var freedTop = abB + (abT-abB)*(1.0-J.k) + (abT-abB)*0.02;
  // 2. lay the new figures out in a grid inside the freed strip
  var lay=null;
  for(i=0;i<doc.layers.length;i++) if(doc.layers[i].name===J.layer) lay=doc.layers[i];
  if(lay===null){lay=doc.layers.add();lay.name=J.layer;}
  try{doc.activeLayer=lay;}catch(e){}
  var n=J.names.length, cols=J.cols||4, rows=Math.ceil(n/cols);
  var pad=(abR-abL)*0.012;
  var cw=((abR-abL)-pad*(cols+1))/cols, ch=((freedTop-abB)-pad*(rows+1))/rows;
  var placed=0, failed=[];
  for(i=0;i<n;i++){
    var nm=J.names[i];
    var f=new File((J.pub?PUB:PDF)+"/"+nm+".pdf");
    if(!f.exists) f=new File(PDF+"/"+nm+".pdf");
    if(!f.exists){ failed.push(nm+" (no pdf)"); continue; }
    var np=lay.placedItems.add(); np.file=f; np.name=nm;
    var s=Math.min(cw/np.width, ch/np.height);
    if(s>0&&s!==1) np.resize(s*100,s*100);
    var c=i%cols, r=Math.floor(i/cols);
    np.left = abL + pad + c*(cw+pad) + (cw-np.width)/2;
    np.top  = freedTop - pad - r*(ch+pad) - (ch-np.height)/2;
    placed++;
  }
  for(i=0;i<lock.length;i++){try{lock[i].l.locked=lock[i].k;}catch(e){}}
  try{doc.selection=null;}catch(e){}
  var so=new IllustratorSaveOptions(); so.compatibility=Compatibility.ILLUSTRATOR17; so.pdfCompatible=false;
  doc.saveAs(new File(J.deck),so); doc.close(SaveOptions.SAVECHANGES);
  report.push(docName+"\tAB"+J.ab+"\tshrank "+onboard.length+" by "+J.k+"\tplaced "+placed+"/"+n
              +(failed.length?"\tFAILED: "+failed.join(", "):""));
}
var rf=new File(TMP+"/place_report.txt");rf.encoding="UTF-8";rf.open("w");
for(var q=0;q<report.length;q++) rf.writeln(report[q]);
rf.close();
