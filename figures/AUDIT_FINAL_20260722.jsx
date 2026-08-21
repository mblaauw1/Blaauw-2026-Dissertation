#target illustrator
// Full integrity check of the CURRENT copy.ai after the jam/force-quit, on disk (not a temp).
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var d = app.open(new File("/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai"));
function lname(p){var f=null;try{f=p.file;}catch(e){}return f?decodeURI(f.name).replace(/\.[^.]+$/,""):"";}
function abOf(b){var cx=(b[0]+b[2])/2,cy=(b[1]+b[3])/2;
  for(var a=0;a<d.artboards.length;a++){var r=d.artboards[a].artboardRect;
    if(cx>=r[0]&&cx<=r[2]&&cy<=r[1]&&cy>=r[3])return a+1;}return 0;}
var fig={}, missing=[], noFile=0, unreadable=0;
for(var i=0;i<d.placedItems.length;i++){
  var p=d.placedItems[i], b;
  try{b=p.visibleBounds;}catch(e){unreadable++;continue;}
  var n=lname(p); if(n&&!fig[n]) fig[n]=b;
  var fp=""; try{fp=p.file?p.file.fsName:"";}catch(e){noFile++;continue;}
  if(!fp){noFile++;continue;}
  if(!(new File(fp)).exists) missing.push(decodeURI(fp));
}
// per-artboard item counts
var cnt=[]; for(var a2=0;a2<d.artboards.length;a2++) cnt.push(0);
var offA=0;
for(var i2=0;i2<d.placedItems.length;i2++){
  var b2; try{b2=d.placedItems[i2].visibleBounds;}catch(e){continue;}
  var k=abOf(b2); if(k) cnt[k-1]++; else offA++;
}
// SIGHILITE + revived outlines
var sig=0, sigFloat=0, outl=0;
for(var i3=0;i3<d.pathItems.length;i3++){
  var q=d.pathItems[i3], nm=q.name||"";
  if(nm.indexOf("REVIVED ")===0) outl++;
  if(nm.indexOf("SIGHILITE")!==0) continue;
  sig++;
  var t=nm.replace(/^SIGHILITE\s*/,""), fb=fig[t];
  if(!fb){sigFloat++;continue;}
  var b3; try{b3=q.visibleBounds;}catch(e){continue;}
  var l=Math.max(fb[0],b3[0]),r=Math.min(fb[2],b3[2]),tp=Math.min(fb[1],b3[1]),bo=Math.max(fb[3],b3[3]);
  var ia=(r>l&&tp>bo)?(r-l)*(tp-bo):0, ba=(b3[2]-b3[0])*(b3[1]-b3[3]);
  if(!(ba>0&&ia>0.5*ba)) sigFloat++;
}
var ri=0; for(var a3=0;a3<d.artboards.length;a3++) if(d.artboards[a3].name.toUpperCase().indexOf("RETIRED")>=0) ri=a3+1;
var out="OPENED OK\n"+
 "placedItems="+d.placedItems.length+"  textFrames="+d.textFrames.length+"  pathItems="+d.pathItems.length+
 "  artboards="+d.artboards.length+"  layers="+d.layers.length+"\n"+
 "links: missing="+missing.length+"  embedded/noFile="+noFile+"  unreadable_bounds="+unreadable+"\n"+
 "off-artboard placements="+offA+"\n"+
 "SIGHILITE="+sig+" floating="+sigFloat+"   REVIVED outlines="+outl+"   RETIRED artboard=AB"+ri+" ("+cnt[ri-1]+" items)\n"+
 "layers: ";
for(var L=0;L<d.layers.length;L++) out+=d.layers[L].name+"("+(d.layers[L].visible?"vis":"hidden")+") ";
if(missing.length){ out+="\nMISSING LINKS:"; for(var m=0;m<missing.length&&m<10;m++) out+="\n  "+missing[m]; }
d.close(SaveOptions.DONOTSAVECHANGES);
out;
