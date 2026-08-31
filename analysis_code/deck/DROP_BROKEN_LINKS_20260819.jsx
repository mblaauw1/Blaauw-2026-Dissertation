// Remove the placed items whose linked file no longer exists.
//
// 0814 carries 3 of them: the `__piece5/6/7` placements left from the 2026-08-17 split of
// `nf9_3-sisterless__20260417_ptk2_eyfp_cdc20_ablation_18`. Today's re-render makes that strip split into
// FOUR pieces, not seven, so pieces 5-7 no longer exist on disk. Their placements are still in the file and
// draw as broken-link boxes.
//
// Deleting a placement is normally off-limits (never revert her edits) -- this is the narrow exception: the
// item has NO art to show, it was created by a script of mine two days ago, and pieces 1-4 of the same strip
// are present and correct. Only items whose file is genuinely missing are touched, and each is logged.
#target illustrator
var TMP="/Volumes/4 MB/_claude_tmp";
var DECKS=[["0814","/Volumes/4 MB/1_DECKS/META_FIGURES_20260814.ai"],
 ["0813supp","/Volumes/4 MB/1_DECKS/META_FIGURES_20260813_supplemental.ai"],
 ["newfig","/Volumes/4 MB/1_DECKS/NEW_FIGURES_20260804.ai"],
 ["other","/Volumes/4 MB/1_DECKS/other_20260820.ai"],
 ["newts","/Volumes/4 MB/1_DECKS/NEW_TIMESTRIPS_20260804.ai"],
 ["pub0814","/Volumes/4 MB/1_DECKS/META_FIGURES_20260814_PUBLICATION_20260820.ai"],
 ["pub0813","/Volumes/4 MB/1_DECKS/META_FIGURES_20260813_supplemental_PUBLICATION_20260820.ai"]];
app.userInteractionLevel=UserInteractionLevel.DONTDISPLAYALERTS;
var out=[];
for(var d=0;d<DECKS.length;d++){
  var doc=null;
  try{doc=app.open(new File(DECKS[d][1]));}catch(e){out.push(DECKS[d][0]+"\tOPEN FAIL");continue;}
  var lock=[],i;
  for(i=0;i<doc.layers.length;i++){var L=doc.layers[i],s={l:L,k:false};try{s.k=L.locked;L.locked=false;}catch(e){}lock.push(s);}
  var removed=0,paths=[];
  for(i=doc.placedItems.length-1;i>=0;i--){
    var p=doc.placedItems[i],f=null;
    try{f=p.file;}catch(e){}
    if(f===null||!f.exists){
      try{paths.push(f?f.name:"(no file)");}catch(e){paths.push("(no file)");}
      try{p.remove();removed++;}catch(e){}
    }
  }
  for(i=0;i<lock.length;i++){try{lock[i].l.locked=lock[i].k;}catch(e){}}
  if(removed>0){
    try{doc.selection=null;}catch(e){}
    var o=new IllustratorSaveOptions();o.compatibility=Compatibility.ILLUSTRATOR17;o.pdfCompatible=false;
    doc.saveAs(new File(DECKS[d][1]),o);
    doc.close(SaveOptions.SAVECHANGES);
  } else doc.close(SaveOptions.DONOTSAVECHANGES);
  out.push(DECKS[d][0]+"\tremoved="+removed+(removed?"\t"+paths.join(", "):""));
}
var rf=new File(TMP+"/drop_broken_report.txt");rf.encoding="UTF-8";rf.open("w");
for(var i=0;i<out.length;i++) rf.writeln(out[i]);
rf.close();
app.userInteractionLevel=UserInteractionLevel.DISPLAYALERTS;
"DONE";
