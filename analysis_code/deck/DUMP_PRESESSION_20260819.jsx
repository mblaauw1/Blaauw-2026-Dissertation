// READ-ONLY dump of the PRE-SESSION publication decks -- the state of the files at the moment she copied
// figures out of them into the 0819 to-do PDF. Needed because "which artboard she copied from" is a fact
// about the deck AS IT WAS, and today's passes moved several figures.
// Same traps avoided as DUMP_ALL9: aiPath (path is reserved), capture doc.name before close, artboard by
// OVERLAP, RasterItems recorded too, alerts suppressed, heartbeat.
#target illustrator
var TMP="/Volumes/4 MB/_claude_tmp";
var HB=new File(TMP+"/dump_pre_heartbeat.txt");
function beat(m){try{HB.open("a");HB.writeln(m);HB.close();}catch(e){}}
var DECKS=[["prepub0814","/Volumes/4 MB/_master_backups/META_FIGURES_20260814_PUBLICATION_pre_todo0819_20260819_134854.ai"],
           ["prepub0813","/Volumes/4 MB/_master_backups/META_FIGURES_20260813_supplemental_PUBLICATION_pre_todo0819_20260819_134855.ai"]];
app.userInteractionLevel=UserInteractionLevel.DONTDISPLAYALERTS;
beat("START");
for(var d=0;d<DECKS.length;d++){
  var tag=DECKS[d][0], aiPath=DECKS[d][1];
  var f=new File(aiPath);
  if(!f.exists){beat("MISSING "+aiPath);continue;}
  var doc=null; try{doc=app.open(f);}catch(e){beat("OPEN FAIL "+tag+" "+e);continue;}
  var docName=doc.name; beat(tag+" opened "+docName);
  var out=[]; out.push(["kind","ab","name","L","T","R","B","layer","link"].join("\t"));
  var i,j;
  var AB=[]; for(i=0;i<doc.artboards.length;i++){var R=doc.artboards[i].artboardRect;AB.push(R);
    out.push(["ARTBOARD",(i+1),doc.artboards[i].name,R[0],R[1],R[2],R[3],"",""].join("\t"));}
  for(i=0;i<doc.pageItems.length;i++){
    var it=doc.pageItems[i],b=null;
    try{b=it.visibleBounds;}catch(e){continue;}
    var nm=""; try{nm=it.name||"";}catch(e){}
    var lk=""; try{if(it.typename==="PlacedItem"&&it.file)lk=it.file.name.replace(/\.(pdf|png)$/i,"");}catch(e){}
    if(!nm&&lk)nm=lk;
    var abs=[];
    for(j=0;j<AB.length;j++){var R2=AB[j];
      if(b[0]<R2[2]&&b[2]>R2[0]&&b[3]<R2[1]&&b[1]>R2[3])abs.push(j+1);}
    var lay=""; try{lay=it.layer.name;}catch(e){}
    out.push([it.typename,abs.join("/"),nm,b[0],b[1],b[2],b[3],lay,lk].join("\t"));
    if(i%300===0)beat(tag+" item "+i+"/"+doc.pageItems.length);
  }
  var of=new File(TMP+"/geom_"+tag+".tsv"); of.encoding="UTF-8"; of.open("w");
  for(i=0;i<out.length;i++) of.writeln(out[i]);
  of.close();
  beat(tag+" WROTE "+out.length);
  doc.close(SaveOptions.DONOTSAVECHANGES);
}
app.userInteractionLevel=UserInteractionLevel.DISPLAYALERTS;
beat("ALLDONE");
"ALLDONE";
