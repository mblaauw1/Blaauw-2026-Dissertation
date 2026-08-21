#target illustrator
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var d = app.open(new File("/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai"));
function abOf(b){var cx=(b[0]+b[2])/2,cy=(b[1]+b[3])/2;
  for(var a=0;a<d.artboards.length;a++){var r=d.artboards[a].artboardRect;
    if(cx>=r[0]&&cx<=r[2]&&cy<=r[1]&&cy>=r[3])return "AB"+(a+1);}return "OFF";}
function lname(p){var f=null;try{f=p.file;}catch(e){}return f?decodeURI(f.name).replace(/\.[^.]+$/,""):"";}
// index every placed figure by name -> its bounds/artboard
var fig={};
for(var i=0;i<d.placedItems.length;i++){
  var p=d.placedItems[i],n=lname(p); if(!n) continue; var b;
  try{b=p.visibleBounds;}catch(e){continue;}
  (fig[n]=fig[n]||[]).push({b:b,ab:abOf(b)});
}
var lines=[];
for(var i2=0;i2<d.pathItems.length;i2++){
  var p2=d.pathItems[i2];
  if(!p2.name || p2.name.indexOf("SIGHILITE")!==0) continue;
  var b2; try{b2=p2.visibleBounds;}catch(e){continue;}
  var target=p2.name.replace(/^SIGHILITE\s*/,"");
  var f=fig[target];
  var status, where="";
  if(!f){ status="ORPHAN_no_such_figure"; }
  else {
    where=f[0].ab;
    // does the box still sit on top of its figure?
    var hit=false;
    for(var k=0;k<f.length;k++){var a=f[k].b;
      var l=Math.max(a[0],b2[0]),r=Math.min(a[2],b2[2]),t=Math.min(a[1],b2[1]),bo=Math.max(a[3],b2[3]);
      if(r>l&&t>bo){var ia=(r-l)*(t-bo),ba=(b2[2]-b2[0])*(b2[1]-b2[3]); if(ia>0.5*ba) hit=true;}}
    status = hit ? "OK_on_its_figure" : "DETACHED_figure_moved";
  }
  lines.push([abOf(b2), status, where, target].join("\t"));
}
var f2=new File("/Volumes/4 MB/ablation_plots/SIG_AUDIT_20260722.txt");
f2.open("w"); f2.write(lines.join("\n")); f2.close();
// also: which placed figures now sit on the RETIRED artboard
var ri=-1; for(var a3=0;a3<d.artboards.length;a3++) if(d.artboards[a3].name.toUpperCase().indexOf("RETIRED")>=0){ri=a3;break;}
var R=d.artboards[ri].artboardRect, onret=[];
for(var i3=0;i3<d.placedItems.length;i3++){
  var p3=d.placedItems[i3],b3; try{b3=p3.visibleBounds;}catch(e){continue;}
  var cx=(b3[0]+b3[2])/2,cy=(b3[1]+b3[3])/2;
  if(cx>=R[0]&&cx<=R[2]&&cy<=R[1]&&cy>=R[3]) onret.push(lname(p3));
}
var f3=new File("/Volumes/4 MB/ablation_plots/AB31_CONTENTS_20260722.txt");
f3.open("w"); f3.write(onret.join("\n")); f3.close();
d.close(SaveOptions.DONOTSAVECHANGES);
"wrote "+lines.length+" SIGHILITE rows and "+onret.length+" AB31 figures";
