// Read-only: META's canvas limits and its content bounds, so the two control strips can be put somewhere
// that is actually inside the canvas. Probes are removed; the document is closed without saving.
#target illustrator
var AI="/Volumes/4 MB/ablation_plots/META_FIGURES_20260805.ai";
var doc=app.open(new File(AI)); var log=[];
function probe(L,T,R,B){ try{ var a=doc.artboards.add([L,T,R,B]); a.remove(); return true; }catch(e){ return false; } }
var lo=null; for(var y=-6000;y>=-12000;y-=100){ if(probe(0,y+200,300,y)) lo=y; else break; }
var hi=null; for(var y2=6000;y2<=12000;y2+=100){ if(probe(0,y2,300,y2-200)) hi=y2; else break; }
var lf2=null; for(var x=-6000;x>=-12000;x-=100){ if(probe(x,0,x+300,-200)) lf2=x; else break; }
var rt=null; for(var x2=6000;x2<=12000;x2+=100){ if(probe(x2-300,0,x2,-200)) rt=x2; else break; }
log.push("CANVAS  floor="+lo+"  ceiling="+hi+"  left="+lf2+"  right="+rt);
var minX=1e9,maxX=-1e9,minY=1e9,maxY=-1e9;
for(var i=0;i<doc.pageItems.length;i++){var b=doc.pageItems[i].visibleBounds;
  if(b[0]<minX)minX=b[0]; if(b[2]>maxX)maxX=b[2]; if(b[3]<minY)minY=b[3]; if(b[1]>maxY)maxY=b[1];}
log.push("CONTENT L="+minX.toFixed(0)+" T="+maxY.toFixed(0)+" R="+maxX.toFixed(0)+" B="+minY.toFixed(0));
for(var a2=0;a2<doc.artboards.length;a2++){var r=doc.artboards[a2].artboardRect;
  log.push("  AB"+a2+" ["+r[0].toFixed(0)+", "+r[1].toFixed(0)+", "+r[2].toFixed(0)+", "+r[3].toFixed(0)+"]");}
doc.close(SaveOptions.DONOTSAVECHANGES);
var f=new File("/Volumes/4 MB/_claude_tmp/meta_probe.txt"); f.open("w"); f.write(log.join("\n")); f.close();
log.join("\n");
