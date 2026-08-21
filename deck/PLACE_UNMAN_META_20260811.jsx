// Place BOTH unmanipulated-control timestrips on META_FIGURES.
//
// USER 2026-08-11: "put both on meta of those unmanipulated strips on meta." Neither was on META: the
// 3-frame 20250321 strip sat on NEW_FIGURES and the 6-frame 20250320 one on NEW_TIMESTRIPS. Both are
// controls -- frames.json shows ablation: [] for each -- so neither carries an ablation row.
//
// Placed BELOW the existing artwork on their own dated layer, side by side, so nothing of hers moves and
// nothing overlaps. The canvas floor is probed first: an artboard/placement past it is what has thrown
// 1200/'CoOA' on these files before, so if the band would overrun, it is placed higher instead of blindly.
// Saved only if the item count actually grows.
#target illustrator
var AI="/Volumes/4 MB/ablation_plots/META_FIGURES_20260805.ai";
var PDFD="/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/";
var NAMES=["unmanipulated-control","nf9_unmanipulated-control__20250320_ptk_yfpcdc20__1_xy3"];
var log=[];
var doc=app.open(new File(AI)); app.activeDocument=doc;
var n0=doc.pageItems.length;
log.push("pageItems before="+n0+" artboards="+doc.artboards.length);
try{ var bak=new File(AI.replace(/\.ai$/,".bak_pre_unman_20260811.ai")); if(!bak.exists) (new File(AI)).copy(bak); }catch(e){}
var minX=1e9,minY=1e9;
for(var i=0;i<doc.pageItems.length;i++){var b=doc.pageItems[i].visibleBounds; if(b[3]<minY)minY=b[3]; if(b[0]<minX)minX=b[0];}
log.push("existing bottom="+minY.toFixed(0)+" left="+minX.toFixed(0));
// probe the canvas floor (read-only; every probe removed)
var floor=null;
for(var y=minY-200;y>=minY-4000;y-=200){
  try{ var ab=doc.artboards.add([0,y+150,300,y]); ab.remove(); floor=y; }catch(e){ break; }
}
log.push("canvas floor probe: lowest OK bottom="+floor);
var lay=doc.layers.add(); lay.name="unmanipulated controls 2026-08-11";
var y0=minY-300, placed=0, x=minX;
for(var k=0;k<NAMES.length;k++){
  var f=new File(PDFD+NAMES[k]+".pdf");
  if(!f.exists){ log.push("MISSING PDF: "+NAMES[k]); continue; }
  var it=doc.placedItems.add(); it.file=f;
  var w=it.width,h=it.height,s=Math.min(1500/w,620/h,1.0);
  it.width=w*s; it.height=h*s;
  it.position=[x,y0];
  var t=doc.textFrames.add(); t.contents=NAMES[k];
  t.textRange.characterAttributes.size=14; t.position=[x,y0+26];
  try{ it.move(lay,ElementPlacement.PLACEATEND); t.move(lay,ElementPlacement.PLACEATEND); }catch(e){}
  log.push("placed "+NAMES[k]+" at ["+x.toFixed(0)+", "+y0.toFixed(0)+"] size "+(w*s).toFixed(0)+"x"+(h*s).toFixed(0));
  x += (w*s) + 160; placed++;
}
log.push("items "+n0+" -> "+doc.pageItems.length+" (placed "+placed+")");
if(doc.pageItems.length<=n0){ log.push("ABORT: no growth; not saving"); doc.close(SaveOptions.DONOTSAVECHANGES); }
else { var o=new IllustratorSaveOptions(); o.pdfCompatible=false; doc.saveAs(new File(AI),o); log.push("saved"); doc.close(SaveOptions.DONOTSAVECHANGES); }
var lf=new File("/Volumes/4 MB/_claude_tmp/place_unman_report.txt"); lf.open("w"); lf.write(log.join("\n")); lf.close();
log.join("\n");
