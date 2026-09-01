#target illustrator
// Build arranged_into_paper_figures_2.ai from the manual copies currently in copy.ai.
// Same coordinates, same linked PDF/PNG files -> a re-render of a figure updates BOTH docs.
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch(e){}

function readFile(p){ var f=new File(p); f.encoding="UTF-8"; f.open("r"); var s=f.read(); f.close(); return s; }
var plan = eval("("+readFile("/Volumes/4 MB/_scratch/arranged2_plan.json")+")");

var OUT="/Volumes/4 MB/1_DECKS/arranged_into_paper_figures_2.ai";
var d = app.documents.add(DocumentColorSpace.RGB, 612, 792);
// artboards: first one is the default; set it, then add the rest
d.artboards[0].artboardRect = plan.artboards[0].rect;
d.artboards[0].name = plan.artboards[0].name;
for (var a=1;a<plan.artboards.length;a++){
  var nb = d.artboards.add(plan.artboards[a].rect);
  nb.name = plan.artboards[a].name;
}

var placed=0, failed=[];
for (var i=0;i<plan.items.length;i++){
  var it=plan.items[i];
  var f=new File(it.file);
  if(!f.exists){ failed.push(it.base+" (file missing)"); continue; }
  try{
    var pi=d.placedItems.add();
    pi.file=f;
    var b=it.b;                       // [l,t,r,bo]
    var w=b[2]-b[0], h=b[1]-b[3];
    pi.width=w; pi.height=h;
    pi.position=[b[0], b[1]];         // top-left
    pi.name=it.base;
    placed++;
  }catch(e){ failed.push(it.base+" :: "+e); }
}

var ntxt=0;
for (var i=0;i<plan.texts.length;i++){
  var t=plan.texts[i];
  try{
    var tf=d.textFrames.add();
    tf.contents=t.txt;
    tf.textRange.characterAttributes.size=10;
    tf.position=[t.b[0], t.b[1]];
    ntxt++;
  }catch(e){}
}

var opt=new IllustratorSaveOptions();
opt.pdfCompatible=false;
d.saveAs(new File(OUT), opt);
var res="placed="+placed+" texts="+ntxt+" failed="+failed.length+(failed.length?(" :: "+failed.join(" | ")):"");
try{ d.close(SaveOptions.DONOTSAVECHANGES); }catch(e){}
res;
