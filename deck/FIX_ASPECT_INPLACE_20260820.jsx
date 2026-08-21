// Correct a placed item's BOX aspect in place -- no remove, no re-place, so no duplicate can be created.
//
// WHY IN PLACE: for a LINKED placed item the art is rendered from the PDF into the box, so a box whose
// aspect differs from the PDF's simply STRETCHES it. Setting the box back to the PDF aspect un-stretches it
// exactly. (The "re-place, never resize" rule applies when the LINK CONTENT changed and the frame must be
// re-derived; here the link is fine and only the frame is wrong.)
//
// This exists because REFIT_ASPECT's remove-then-place could not match these two items by name on
// other_20260820.ai -- it added a second copy instead -- and a position-based delete then removed the wrong
// one, because both copies sat at the same left/top. Resizing touches exactly one object and cannot duplicate.
#target illustrator
var TMP="/Volumes/4 MB/_claude_tmp";
function readAll(p){var f=new File(p);f.encoding="UTF-8";f.open("r");var s=f.read();f.close();return s;}
var plan=eval("("+readAll(TMP+"/fix_aspect_plan.json")+")");

// 🔴 doc.pageItems DOES NOT REACH ITEMS NESTED INSIDE GROUPS in this Illustrator version. That is the root
// cause of the whole duplicate episode on other_20260820.ai: REFIT_ASPECT's remove-by-name silently matched
// nothing, so it ADDED a second copy; a position-based delete then removed whichever copy it hit first,
// because both sat at the same left/top. Everything that searches by name must recurse.
// 🔴 AND THE IDENTITY IS THE LINKED FILENAME, NOT it.name. DUMP_ALL9 derives a figure's name from
// `it.file.name` minus its extension; `it.name` is set only on items one of my own scripts placed. Matching
// on it.name alone therefore found nothing for any figure SHE had placed -- which is exactly the set this
// was trying to fix. Match on either.
function itemKey(it){
  var nm="";
  try{ if(it.file) nm=String(it.file.name).replace(/\.(pdf|png|ai|eps)$/i,""); }catch(e){}
  if(!nm){ try{ nm=it.name||""; }catch(e2){} }
  return nm;
}
function collectNamed(container, name, out){
  var k;
  for(k=0;k<container.pageItems.length;k++){
    var it=container.pageItems[k];
    var nm=itemKey(it), nm2="";
    try{nm2=it.name||"";}catch(e){}
    if(nm===name || nm2===name) out.push(it);
  }
  for(k=0;k<container.groupItems.length;k++) collectNamed(container.groupItems[k], name, out);
  return out;
}
function findNamed(doc, name){
  var out=[], k;
  for(k=0;k<doc.layers.length;k++) collectNamed(doc.layers[k], name, out);
  return out;
}

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
    var op=ops[i], done=0;
    var hits=findNamed(doc, op.name);
    for(j=0;j<hits.length;j++){
      var it=hits[j];
      var b=null; try{b=it.geometricBounds;}catch(e){continue;}      // [L,T,R,B]
      var w=b[2]-b[0], h=b[1]-b[3];
      if(w<=0||h<=0) continue;
      // fit INSIDE the current box at the correct aspect, anchored top-left -- never larger, so no new overlap
      var nw=w, nh=w/op.aspect;
      if(nh>h){ nh=h; nw=h*op.aspect; }
      try{
        it.width=nw; it.height=nh; it.left=b[0]; it.top=b[1];
        done++;
        report.push(docName+"\t"+op.name+"\t"+Math.round(w)+"x"+Math.round(h)+" -> "+Math.round(nw)+"x"+Math.round(nh));
      }catch(e){ report.push(docName+"\t"+op.name+"\tRESIZE FAILED "+e); }
    }
    if(!done) report.push(docName+"\t"+op.name+"\tNOT FOUND");
  }
  for(i=0;i<lock.length;i++){try{lock[i].l.locked=lock[i].k;}catch(e){}}
  try{doc.selection=null;}catch(e){}
  var so=new IllustratorSaveOptions(); so.compatibility=Compatibility.ILLUSTRATOR17; so.pdfCompatible=false;
  doc.saveAs(new File(aiPath),so); doc.close(SaveOptions.SAVECHANGES);
}
var rf=new File(TMP+"/fix_aspect_report.txt");rf.encoding="UTF-8";rf.open("w");
for(i=0;i<report.length;i++) rf.writeln(report[i]);
rf.close();
