// Read-only: where did today's four new figures actually land, and do they overlap anything?
#target illustrator
var TARGET="/Volumes/4 MB/1_DECKS/NEW_FIGURES_20260804.ai";
var WANT=["G9_drug_timestrip_zm18_aligned","G6_osc_metric_sensitivity_threegroup",
          "G6_period_by_definition_panels","G6_amplitude_by_definition_panels"];
var doc=app.open(new File(TARGET));
var out=[], boxes=[];
for(var i=0;i<doc.placedItems.length;i++){
  var f=null; try{f=doc.placedItems[i].file;}catch(e){f=null;}
  if(!f) continue;
  var nm=f.name.replace(/\.pdf$/i,"");
  for(var w=0;w<WANT.length;w++) if(WANT[w]===nm){
    var b=doc.placedItems[i].visibleBounds;
    out.push(nm+"\tL="+b[0].toFixed(0)+" T="+b[1].toFixed(0)+" R="+b[2].toFixed(0)+" B="+b[3].toFixed(0)
             +"\tinCanvas="+((b[3]>-7475 && b[2]<8750 && b[0]>-7250 && b[1]<8750)?"YES":"NO"));
    boxes.push([nm,b]);
  }
}
for(var a=0;a<boxes.length;a++) for(var c=a+1;c<boxes.length;c++){
  var A=boxes[a][1],B=boxes[c][1];
  var ov=!(A[2]<B[0]||B[2]<A[0]||A[3]>B[1]||B[3]>A[1]);
  if(ov) out.push("OVERLAP\t"+boxes[a][0]+" <-> "+boxes[c][0]);
}
out.push("total placed on deck="+doc.placedItems.length+"  artboards="+doc.artboards.length);
doc.close(SaveOptions.DONOTSAVECHANGES);
var lf=new File("/Volumes/4 MB/_claude_tmp/bounds_check.txt"); lf.open("w"); lf.write(out.join("\n")); lf.close();
out.join("\n");
