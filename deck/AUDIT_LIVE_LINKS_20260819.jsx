// Definitive broken-link check: walk the LIVE placed items of every deck and test each one's .file.
// `strings` on a .ai also finds path records Illustrator keeps for items that no longer exist, so it
// over-reports; this asks the document itself.
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
  var n=0,bad=0,names=[];
  for(var i=0;i<doc.placedItems.length;i++){
    var p=doc.placedItems[i]; n++;
    var f=null; try{f=p.file;}catch(e){}
    if(f===null||!f.exists){bad++; try{names.push(p.name||"(unnamed)");}catch(e){names.push("(unnamed)");}}
  }
  out.push(DECKS[d][0]+"\tplaced="+n+"\tBROKEN="+bad+(bad?"\t"+names.slice(0,8).join(", "):""));
  doc.close(SaveOptions.DONOTSAVECHANGES);
}
var rf=new File(TMP+"/live_links_report.txt"); rf.encoding="UTF-8"; rf.open("w");
for(var i=0;i<out.length;i++) rf.writeln(out[i]);
rf.close();
app.userInteractionLevel=UserInteractionLevel.DISPLAYALERTS;
"DONE";
