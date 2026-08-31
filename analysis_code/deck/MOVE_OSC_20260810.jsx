// The ZM strip landed at y=-7490, past the measured canvas floor (-7475) and so off every artboard.
// The new band only reaches x=2278 while the canvas runs to 8750, so there is ample room to its RIGHT,
// inside the canvas. Move the strip and its label there. Nothing else is touched.
#target illustrator
var TARGET="/Volumes/4 MB/1_DECKS/NEW_FIGURES_20260804.ai";
var NAME="G6_osc_metric_sensitivity_threegroup";
var log=[];
var doc=app.open(new File(TARGET)); app.activeDocument=doc;
var item=null;
for(var i=0;i<doc.placedItems.length;i++){
  var f=null; try{f=doc.placedItems[i].file;}catch(e){f=null;}
  if(f && f.name.replace(/\.pdf$/i,"")===NAME){ item=doc.placedItems[i]; break; }
}
var lbl=null;
for(var t=0;t<doc.textFrames.length;t++){
  var c=""; try{c=String(doc.textFrames[t].contents).replace(/^\s+|\s+$/g,"");}catch(e){continue;}
  if(c===NAME){ lbl=doc.textFrames[t]; break; }
}
if(!item){ log.push("strip NOT FOUND; not saving"); doc.close(SaveOptions.DONOTSAVECHANGES); }
else{
  var b=item.visibleBounds;
  log.push("was at ["+b[0].toFixed(0)+", "+b[1].toFixed(0)+"] .. ["+b[2].toFixed(0)+", "+b[3].toFixed(0)+"]");
  var NX=2400, NY=-6760;                     // right of the band, inside the canvas
  var dx=NX-b[0], dy=NY-b[1];
  item.translate(dx,dy);
  if(lbl) lbl.translate(dx,dy);
  var b2=item.visibleBounds;
  log.push("now at  ["+b2[0].toFixed(0)+", "+b2[1].toFixed(0)+"] .. ["+b2[2].toFixed(0)+", "+b2[3].toFixed(0)+"]");
  log.push("inside canvas (floor -7475, right 8750): "+((b2[3]>-7475 && b2[2]<8750)?"YES":"NO"));
  var o=new IllustratorSaveOptions(); o.pdfCompatible=false;
  doc.saveAs(new File(TARGET),o); log.push("saved");
  doc.close(SaveOptions.DONOTSAVECHANGES);
}
var lf=new File("/Volumes/4 MB/_claude_tmp/move_osc_report.txt"); lf.open("w"); lf.write(log.join("\n")); lf.close();
log.join("\n");
