// Read-only: the FULL linked path of every placed item on META, so a stale/indirect link can be spotted.
#target illustrator
var AI="/Volumes/4 MB/ablation_plots/META_FIGURES_20260805.ai";
var doc=app.open(new File(AI)); var out=[];
for(var i=0;i<doc.placedItems.length;i++){
  var f=null; try{f=doc.placedItems[i].file;}catch(e){f=null;}
  if(!f){ out.push("EMBEDDED\t(no file)\t-"); continue; }
  var exists=f.exists?"ok":"MISSING";
  out.push(exists+"\t"+f.fsName+"\t"+(f.exists?f.modified:"-"));
}
doc.close(SaveOptions.DONOTSAVECHANGES);
var lf=new File("/Volumes/4 MB/_claude_tmp/meta_paths.txt"); lf.encoding="UTF-8"; lf.open("w");
for(var k=0;k<out.length;k++) lf.writeln(out[k]);
lf.close(); "n="+doc.placedItems.length;
