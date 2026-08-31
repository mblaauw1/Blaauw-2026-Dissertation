// Read-only: find the artboard holding the double-chromosome strip and export it to PNG, so what the DECK
// actually contains can be inspected directly instead of inferred from file mtimes.
#target illustrator
var AI="/Volumes/4 MB/ablation_plots/META_FIGURES_20260805.ai";
var doc=app.open(new File(AI)); var log=[];
var target=null;
for(var i=0;i<doc.placedItems.length;i++){
  var f=null; try{f=doc.placedItems[i].file;}catch(e){continue;}
  if(f && f.name.indexOf("double-chromosome")>=0){ target=doc.placedItems[i]; log.push("found link: "+f.fsName+"  modified="+f.modified); break; }
}
if(!target){ log.push("double-chromosome not found on META"); }
else{
  var b=target.visibleBounds;
  log.push("item bounds ["+b[0].toFixed(0)+","+b[1].toFixed(0)+","+b[2].toFixed(0)+","+b[3].toFixed(0)+"]");
  var idx=-1;
  for(var a=0;a<doc.artboards.length;a++){
    var r=doc.artboards[a].artboardRect;
    if(b[0]>=r[0]-1 && b[2]<=r[2]+1 && b[3]>=r[3]-1 && b[1]<=r[1]+1){ idx=a; break; }
  }
  log.push("on artboard "+idx);
  if(idx>=0){
    doc.artboards.setActiveArtboardIndex(idx);
    var opt=new ExportOptionsPNG24();
    opt.artBoardClipping=true; opt.horizontalScale=40; opt.verticalScale=40;
    doc.exportFile(new File("/Volumes/4 MB/_claude_tmp/meta_ab_check.png"), ExportType.PNG24, opt);
    log.push("exported artboard "+idx);
  }
}
doc.close(SaveOptions.DONOTSAVECHANGES);
var lf=new File("/Volumes/4 MB/_claude_tmp/export_ab.txt"); lf.open("w"); lf.write(log.join("\n")); lf.close();
log.join("\n");
