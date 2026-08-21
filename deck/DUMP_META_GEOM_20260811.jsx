// Read-only geometry dump of META, per item, so free space on the artboards can be computed outside AI.
#target illustrator
var AI="/Volumes/4 MB/ablation_plots/META_FIGURES_20260805.ai";
var doc=app.open(new File(AI)); var out=["kind\tname\tL\tT\tR\tB\tlayer"]; var n=0;
try{ n=doc.pageItems.length; }catch(e){}
for(var i=0;i<n;i++){
  var kind="?",nm="",b=null,lay="";
  try{ var it=doc.pageItems[i];
    try{kind=it.typename;}catch(e1){}
    try{b=it.visibleBounds;}catch(e2){b=null;}
    try{ if(kind==="PlacedItem"&&it.file) nm=it.file.name.replace(/\.(pdf|png|ai|eps)$/i,""); }catch(e3){}
    try{ if(!nm&&kind==="TextFrame") nm=String(it.contents).substr(0,30).replace(/[\t\r\n]/g," "); }catch(e4){}
    try{ lay=it.layer.name; }catch(e5){}
    if(b===null) continue;
    out.push(kind+"\t"+nm+"\t"+b[0].toFixed(1)+"\t"+b[1].toFixed(1)+"\t"+b[2].toFixed(1)+"\t"+b[3].toFixed(1)+"\t"+lay);
  }catch(e){}
}
doc.close(SaveOptions.DONOTSAVECHANGES);
var f=new File("/Volumes/4 MB/_claude_tmp/meta_geom.tsv"); f.encoding="UTF-8"; f.open("w");
for(var g=0;g<out.length;g++) f.writeln(out[g]);
f.close(); "items="+n;
