// Re-place the timestrips whose piece COUNT changed when the ablation zoom was tightened (2026-08-19).
//
// WHY THIS IS NECESSARY AND NOT COSMETIC: a strip that used to cut into 4 pieces and now cuts into 5 still
// has 4 resolvable placements on the deck -- so a link check passes -- but `__piece2` now contains a
// DIFFERENT portion of the strip than it did, and the last portion is missing entirely. Silent wrong art is
// worse than a broken link, which is why this is driven off a count comparison rather than a link test.
//
// Every stale piece of the named strip is removed and the CURRENT full set is stacked at the recorded
// top-left, at the recorded width, on the session layer. RELAY_PIECES then normalises the scale.
#target illustrator
var TMP="/Volumes/4 MB/_claude_tmp";
var HB=new File(TMP+"/repieces_heartbeat.txt");
function beat(m){try{HB.open("a");HB.writeln(m);HB.close();}catch(e){}}
function readAll(p){var f=new File(p);f.encoding="UTF-8";f.open("r");var s=f.read();f.close();return s;}
var plan=eval("("+readAll(TMP+"/repieces_plan.json")+")");
var LAY="session_20260819";
app.userInteractionLevel=UserInteractionLevel.DONTDISPLAYALERTS;
beat("START");
var byDeck={},i,j;
for(i=0;i<plan.ops.length;i++){var o=plan.ops[i];(byDeck[o.aiPath]=byDeck[o.aiPath]||[]).push(o);}
var report=[];
for(var aiPath in byDeck){
  var ops=byDeck[aiPath],doc=null;
  try{doc=app.open(new File(aiPath));}catch(e){report.push("OPEN FAIL "+aiPath);continue;}
  var docName=doc.name;
  var lock=[];
  for(i=0;i<doc.layers.length;i++){var L=doc.layers[i],st={l:L,k:false};try{st.k=L.locked;L.locked=false;}catch(e){}lock.push(st);}
  var lay=null;
  for(i=0;i<doc.layers.length;i++) if(doc.layers[i].name===LAY) lay=doc.layers[i];
  if(lay===null){lay=doc.layers.add();lay.name=LAY;}
  try{lay.locked=false;lay.visible=true;}catch(e){}
  var removed=0,added=0;
  // 🔴 2026-08-21: match on the LINKED FILENAME as well as `.name`, and walk INTO groups.
  // Matching `.name` alone only finds items THIS script placed -- anything she placed or regrouped was
  // invisible to the removal pass, so the re-place added a second copy instead of replacing. That is
  // exactly the duplicate saga of 2026-08-20. DUMP_ALL9 identifies a figure by its linked filename, so
  // this pass now uses the same identity, and doc.pageItems does not reach inside groups.
  function collectAll(container, out){
    for(var q=0;q<container.pageItems.length;q++){
      var it2=container.pageItems[q]; out.push(it2);
      if(it2.typename==="GroupItem"){ try{ collectAll(it2,out); }catch(e){} }
    }
    return out;
  }
  function idOf(it){
    var nm="";
    try{ nm=it.name||""; }catch(e){}
    if(!nm){ try{ if(it.file) nm=decodeURI(it.file.name).replace(/\.pdf$/i,""); }catch(e){} }
    return nm;
  }
  for(i=0;i<ops.length;i++){
    var op=ops[i],pre=op.base+"__piece";
    var all=collectAll(doc,[]);
    for(j=all.length-1;j>=0;j--){
      var it=all[j],nm=idOf(it);
      if(nm.indexOf(pre)===0){try{it.remove();removed++;}catch(e){}}
    }
    try{doc.activeLayer=lay;}catch(e){}
    var y=op.at[1];
    for(j=0;j<op.names.length;j++){
      var f=new File((op.pub?plan.pub_pdf:plan.pdf)+"/"+op.names[j]+".pdf");
      if(!f.exists){report.push(docName+"\tMISSING\t"+op.names[j]);continue;}
      var np=lay.placedItems.add(); np.file=f;
      var s=op.w/np.width; if(s>0&&s!==1) np.resize(s*100,s*100);
      np.left=op.at[0]; np.top=y; np.name=op.names[j];
      y-=(np.height+8); added++;
    }
    report.push(docName+"\tREPIECED\t"+op.base+"\t-> "+op.names.length);
  }
  for(i=0;i<lock.length;i++){try{lock[i].l.locked=lock[i].k;}catch(e){}}
  try{doc.selection=null;}catch(e){}
  var so=new IllustratorSaveOptions(); so.compatibility=Compatibility.ILLUSTRATOR17; so.pdfCompatible=false;
  doc.saveAs(new File(aiPath),so); doc.close(SaveOptions.SAVECHANGES);
  report.push(docName+"\tTOTALS\tremoved="+removed+"\tadded="+added);
  beat(docName+" removed="+removed+" added="+added);
}
var rf=new File(TMP+"/repieces_report.txt");rf.encoding="UTF-8";rf.open("w");
for(i=0;i<report.length;i++) rf.writeln(report[i]);
rf.close();
app.userInteractionLevel=UserInteractionLevel.DISPLAYALERTS;
beat("ALLDONE");
"ALLDONE";
