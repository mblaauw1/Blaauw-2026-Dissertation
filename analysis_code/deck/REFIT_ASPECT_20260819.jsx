// Re-place any figure whose PLACED frame no longer matches the aspect of its source PDF (2026-08-19).
//
// WHY THIS EXISTS: a placed link keeps the frame it was given. Re-rendering a figure at a different shape
// therefore does NOT re-fit it -- the link still resolves, so every link check passes, while the art on the
// board is silently STRETCHED. That is the same failure mode as the piece-count bug: valid link, wrong art.
// `_claude_tmp/refit_aspect_plan.json` is built in python from the read-only geometry dumps plus `pdfinfo`,
// so the drift is measured, never guessed at.
//
// The item is REMOVED and PLACED AGAIN rather than resized: resizing a frame that is already distorted keeps
// the distortion. It is then fitted INSIDE its old slot (never larger, so no new overlap can be created) and
// anchored at the old top-left, which is where she put it.
#target illustrator
var TMP="/Volumes/4 MB/_claude_tmp";
var PDF="/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf";
var PUB="/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf_pub";
var HB=new File(TMP+"/refit_aspect_heartbeat.txt");
function beat(m){try{HB.open("a");HB.writeln(m);HB.close();}catch(e){}}
function readAll(p){var f=new File(p);f.encoding="UTF-8";f.open("r");var s=f.read();f.close();return s;}
var plan=eval("("+readAll(TMP+"/refit_aspect_plan.json")+")");
var LAY="session_20260819";
app.userInteractionLevel=UserInteractionLevel.DONTDISPLAYALERTS;
beat("START "+plan.ops.length+" ops");
var byDeck={},i,j;
for(i=0;i<plan.ops.length;i++){var o=plan.ops[i];(byDeck[o.aiPath]=byDeck[o.aiPath]||[]).push(o);}
var report=[];
for(var aiPath in byDeck){
  var ops=byDeck[aiPath],doc=null;
  try{doc=app.open(new File(aiPath));}catch(e){report.push("OPEN FAIL "+aiPath);continue;}
  var docName=doc.name, lock=[];
  for(i=0;i<doc.layers.length;i++){var L=doc.layers[i],st={l:L,k:false};try{st.k=L.locked;L.locked=false;}catch(e){}lock.push(st);}
  var lay=null;
  for(i=0;i<doc.layers.length;i++) if(doc.layers[i].name===LAY) lay=doc.layers[i];
  if(lay===null){lay=doc.layers.add();lay.name=LAY;}
  try{lay.locked=false;lay.visible=true;}catch(e){}
  for(i=0;i<ops.length;i++){
    var op=ops[i];
    for(j=doc.pageItems.length-1;j>=0;j--){
      var it=doc.pageItems[j],nm="";
      try{nm=it.name||"";}catch(e){}
      if(nm===op.name){try{it.remove();}catch(e){}}
    }
    try{doc.activeLayer=lay;}catch(e){}
    var pubdir=(op.deck.indexOf("pub")===0);
    var f=new File((pubdir?PUB:PDF)+"/"+op.name+".pdf");
    if(!f.exists) f=new File(PDF+"/"+op.name+".pdf");
    if(!f.exists){report.push(docName+"\tMISSING\t"+op.name);continue;}
    var np=lay.placedItems.add(); np.file=f;
    // fit INSIDE the old slot, preserving the new aspect -- never wider or taller than she allowed for it
    var s=Math.min(op.w/np.width, op.h/np.height);
    if(s>0&&s!==1) np.resize(s*100,s*100);
    np.left=op.left; np.top=op.top; np.name=op.name;
    report.push(docName+"\tREFIT\t"+op.name+"\tAB"+op.ab+"\t"+Math.round(np.width)+"x"+Math.round(np.height));
  }
  for(i=0;i<lock.length;i++){try{lock[i].l.locked=lock[i].k;}catch(e){}}
  try{doc.selection=null;}catch(e){}
  var so=new IllustratorSaveOptions(); so.compatibility=Compatibility.ILLUSTRATOR17; so.pdfCompatible=false;
  doc.saveAs(new File(aiPath),so); doc.close(SaveOptions.SAVECHANGES);
  beat(docName+" done");
}
var rf=new File(TMP+"/refit_aspect_report.txt");rf.encoding="UTF-8";rf.open("w");
for(i=0;i<report.length;i++) rf.writeln(report[i]);
rf.close(); beat("DONE");
