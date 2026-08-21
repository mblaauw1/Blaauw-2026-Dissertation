// The strips were laid out downward from y=-20, but a new document's artboard runs y 12000..0, so all the
// content ended up BELOW the artboard (and the resize to fit it was refused with 1200/'CoOA', because the
// requested rect fell outside the new document's canvas). Rather than fight the artboard, the ARTWORK is
// moved up into it -- one rigid translation, so relative layout is untouched -- and the result is checked
// against the artboard rect before saving.
#target illustrator
var AI="/Volumes/4 MB/ablation_plots/_superseded_decks/REVISED_TIMESTRIPS_20260811.ai";
var doc=app.open(new File(AI)); app.activeDocument=doc; var log=[];
var r=doc.artboards[0].artboardRect;
log.push("artboard ["+r[0].toFixed(0)+", "+r[1].toFixed(0)+", "+r[2].toFixed(0)+", "+r[3].toFixed(0)+"]");
var minX=1e9,maxX=-1e9,minY=1e9,maxY=-1e9;
for(var i=0;i<doc.pageItems.length;i++){var b=doc.pageItems[i].visibleBounds;
 if(b[0]<minX)minX=b[0]; if(b[2]>maxX)maxX=b[2]; if(b[3]<minY)minY=b[3]; if(b[1]>maxY)maxY=b[1];}
log.push("content before: T="+maxY.toFixed(0)+" B="+minY.toFixed(0)+" L="+minX.toFixed(0)+" R="+maxX.toFixed(0));
var dy=(r[1]-60)-maxY, dx=(r[0]+60)-minX;
for(var k=0;k<doc.pageItems.length;k++) doc.pageItems[k].translate(dx,dy);
minX=1e9;maxX=-1e9;minY=1e9;maxY=-1e9;
for(var j=0;j<doc.pageItems.length;j++){var b2=doc.pageItems[j].visibleBounds;
 if(b2[0]<minX)minX=b2[0]; if(b2[2]>maxX)maxX=b2[2]; if(b2[3]<minY)minY=b2[3]; if(b2[1]>maxY)maxY=b2[1];}
log.push("content after : T="+maxY.toFixed(0)+" B="+minY.toFixed(0)+" L="+minX.toFixed(0)+" R="+maxX.toFixed(0));
var inside=(minX>=r[0] && maxX<=r[2] && minY>=r[3] && maxY<=r[1]);
log.push("entirely inside artboard: "+(inside?"YES":"NO"));
var o=new IllustratorSaveOptions(); o.pdfCompatible=false;
doc.saveAs(new File(AI), o); log.push("saved");
doc.close(SaveOptions.DONOTSAVECHANGES);
var lf=new File("/Volumes/4 MB/_claude_tmp/fix_ab.txt"); lf.open("w"); lf.write(log.join("\n")); lf.close();
log.join("\n");
