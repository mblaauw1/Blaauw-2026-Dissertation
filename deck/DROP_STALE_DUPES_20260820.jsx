// Remove ONLY the stale duplicate placements that this session's refit created (2026-08-20).
//
// WHY THIS IS NARROW: her decks contain DELIBERATE duplicates -- her own paper-figure copies -- and the
// standing rule is never to dedupe them. So this does not search for duplicates at all. It removes exactly
// the placements named in `dedupe_ops.json`, each identified by NAME **and** its recorded left/top, which
// python chose as the copy whose aspect does NOT match the current render (i.e. the stale one), or, where
// both matched, the copy this session added. Anything else is left untouched.
#target illustrator
var TMP="/Volumes/4 MB/_claude_tmp";
function readAll(p){var f=new File(p);f.encoding="UTF-8";f.open("r");var s=f.read();f.close();return s;}
var plan=eval("("+readAll(TMP+"/dedupe_ops.json")+")");
app.userInteractionLevel=UserInteractionLevel.DONTDISPLAYALERTS;
var byDeck={},i,j;
for(i=0;i<plan.ops.length;i++){var o=plan.ops[i];(byDeck[o.aiPath]=byDeck[o.aiPath]||[]).push(o);}
var report=[];
for(var aiPath in byDeck){
  var ops=byDeck[aiPath],doc=null;
  try{doc=app.open(new File(aiPath));}catch(e){report.push("OPEN FAIL "+aiPath);continue;}
  var docName=doc.name, lock=[];
  for(i=0;i<doc.layers.length;i++){var L=doc.layers[i],st={l:L,k:false};try{st.k=L.locked;L.locked=false;}catch(e){}lock.push(st);}
  for(i=0;i<ops.length;i++){
    var op=ops[i], removed=0;
    for(j=doc.pageItems.length-1;j>=0;j--){
      var it=doc.pageItems[j],nm="";
      try{nm=it.name||"";}catch(e){}
      if(nm!==op.name) continue;
      var b=null; try{b=it.geometricBounds;}catch(e){continue;}   // [L,T,R,B]
      if(Math.abs(b[0]-op.left)<1.5 && Math.abs(b[1]-op.top)<1.5){
        try{it.remove();removed++;}catch(e){}
      }
    }
    report.push(docName+"\t"+op.name+"\tremoved="+removed);
  }
  for(i=0;i<lock.length;i++){try{lock[i].l.locked=lock[i].k;}catch(e){}}
  try{doc.selection=null;}catch(e){}
  var so=new IllustratorSaveOptions(); so.compatibility=Compatibility.ILLUSTRATOR17; so.pdfCompatible=false;
  doc.saveAs(new File(aiPath),so); doc.close(SaveOptions.SAVECHANGES);
}
var rf=new File(TMP+"/dedupe_report.txt");rf.encoding="UTF-8";rf.open("w");
for(i=0;i<report.length;i++) rf.writeln(report[i]);
rf.close();
