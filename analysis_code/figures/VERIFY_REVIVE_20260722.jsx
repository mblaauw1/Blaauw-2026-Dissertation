#target illustrator
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var d = app.open(new File("/Volumes/4 MB/ablation_plots/_tmp_revive_20260722.ai"));
function lname(p){var f=null;try{f=p.file;}catch(e){}return f?decodeURI(f.name).replace(/\.[^.]+$/,""):"";}
function abOf(b){var cx=(b[0]+b[2])/2,cy=(b[1]+b[3])/2;
  for(var a=0;a<d.artboards.length;a++){var r=d.artboards[a].artboardRect;
    if(cx>=r[0]&&cx<=r[2]&&cy<=r[1]&&cy>=r[3])return "AB"+(a+1);}return "OFF";}
var fig={}, missing=0;
for(var i=0;i<d.placedItems.length;i++){
  var p=d.placedItems[i],n=lname(p),b; try{b=p.visibleBounds;}catch(e){continue;}
  if(n&&!fig[n]) fig[n]=b;
  var fp=""; try{fp=p.file?p.file.fsName:"";}catch(e){}
  if(fp&&!(new File(fp)).exists) missing++;
}
var chk=["collagenON_vs_triple_area_binned","collagenON_vs_triple_area_linear",
         "collagenON_vs_triple_roundness_binned","collagenON_vs_triple_roundness_linear",
         "DEMO_lineplot_shape_by_metaphase"];
var out=[];
for(var c=0;c<chk.length;c++) out.push("  "+chk[c]+" -> "+(fig[chk[c]]?abOf(fig[chk[c]]):"NOT PLACED"));
// outlines + floating highlights
var outl=0; for(var i2=0;i2<d.pathItems.length;i2++) if((d.pathItems[i2].name||"").indexOf("REVIVED ")===0) outl++;
var floating=0, tot=0;
for(var i3=0;i3<d.pathItems.length;i3++){
  var q=d.pathItems[i3];
  if(!q.name||q.name.indexOf("SIGHILITE")!==0) continue; tot++;
  var t=q.name.replace(/^SIGHILITE\s*/,""), fb=fig[t];
  if(!fb){floating++;continue;}
  var b2; try{b2=q.visibleBounds;}catch(e){continue;}
  var l=Math.max(fb[0],b2[0]),r=Math.min(fb[2],b2[2]),tp=Math.min(fb[1],b2[1]),bo=Math.max(fb[3],b2[3]);
  var ia=(r>l&&tp>bo)?(r-l)*(tp-bo):0, ba=(b2[2]-b2[0])*(b2[1]-b2[3]);
  if(!(ba>0&&ia>0.5*ba)) floating++;
}
var res="placedItems="+d.placedItems.length+" artboards="+d.artboards.length+" textFrames="+d.textFrames.length+
        " missingLinks="+missing+"\nrevived:\n"+out.join("\n")+
        "\nbrown outlines="+outl+"  SIGHILITE total="+tot+" floating="+floating;
d.close(SaveOptions.DONOTSAVECHANGES);
res;
