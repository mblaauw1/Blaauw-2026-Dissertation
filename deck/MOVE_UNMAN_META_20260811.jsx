// Move the two unmanipulated-control strips onto an ARTBOARD.
//
// They were first placed below the existing artwork at y=-7738, but META's canvas floor is -7600 and its
// nine 5100pt artboards stop at y=-7350 -- so they sat off-canvas and off-board, where nothing prints.
// Measured free space per board: AB2 (x 3250..8350) has a 940pt empty band at y 4890..3950 and is the
// emptiest of the roomy boards (29 items), so both strips go there, side by side, inside the board.
#target illustrator
var AI="/Volumes/4 MB/ablation_plots/META_FIGURES_20260805.ai";
var NAMES=["unmanipulated-control","nf9_unmanipulated-control__20250320_ptk_yfpcdc20__1_xy3"];
var POS=[[3400,4800],[3992,4800]];
var log=[];
var doc=app.open(new File(AI)); app.activeDocument=doc;
var moved=0;
for(var k=0;k<NAMES.length;k++){
  var item=null,lbl=null;
  for(var i=0;i<doc.placedItems.length;i++){
    var f=null; try{f=doc.placedItems[i].file;}catch(e){f=null;}
    if(f && f.name.replace(/\.pdf$/i,"")===NAMES[k]){ item=doc.placedItems[i]; break; }
  }
  for(var t=0;t<doc.textFrames.length;t++){
    var c=""; try{c=String(doc.textFrames[t].contents).replace(/^\s+|\s+$/g,"");}catch(e){continue;}
    if(c===NAMES[k] || (NAMES[k].indexOf(c)===0 && c.length>20)){ lbl=doc.textFrames[t]; break; }
  }
  if(!item){ log.push("NOT FOUND: "+NAMES[k]); continue; }
  var b=item.visibleBounds;
  var dx=POS[k][0]-b[0], dy=POS[k][1]-b[1];
  item.translate(dx,dy); if(lbl) lbl.translate(dx,dy);
  var b2=item.visibleBounds;
  var onAB = (b2[0]>=3250 && b2[2]<=8350 && b2[3]>=-2250+0 && b2[1]<=8350);
  log.push(NAMES[k]+": ["+b[0].toFixed(0)+","+b[1].toFixed(0)+"] -> ["+b2[0].toFixed(0)+","+b2[1].toFixed(0)+
           "] .. ["+b2[2].toFixed(0)+","+b2[3].toFixed(0)+"]  insideAB2="+((b2[0]>=3250&&b2[2]<=8350&&b2[3]>=3250&&b2[1]<=8350)?"YES":"no"));
  moved++;
}
log.push("moved="+moved);
if(moved===0){ log.push("nothing moved; not saving"); doc.close(SaveOptions.DONOTSAVECHANGES); }
else { var o=new IllustratorSaveOptions(); o.pdfCompatible=false; doc.saveAs(new File(AI),o); log.push("saved"); doc.close(SaveOptions.DONOTSAVECHANGES); }
var lf=new File("/Volumes/4 MB/_claude_tmp/move_unman_report.txt"); lf.open("w"); lf.write(log.join("\n")); lf.close();
log.join("\n");
