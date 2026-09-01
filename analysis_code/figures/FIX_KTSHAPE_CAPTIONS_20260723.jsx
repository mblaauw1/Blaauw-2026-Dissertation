#target illustrator
// Replace the 17 prose kinetochore-shape captions with the deck-standard '<#>. <base>   [data: ...]'
// so verify_deck_complete's numbered-caption check passes.
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch(e){}
function readFile(p){ var f=new File(p); f.encoding="UTF-8"; f.open("r"); var s=f.read(); f.close(); return s; }
var R = eval("("+readFile("/Volumes/4 MB/_scratch/ktshape_caption_fix.json")+")").repl;
var COPY="/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
while (app.documents.length>0){ app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var d=app.open(new File(COPY));
var fixed=0, tfs=d.textFrames;
for (var i=0;i<tfs.length;i++){
  var cur=tfs[i].contents;
  if (R.hasOwnProperty(cur)){ tfs[i].contents=R[cur]; fixed++; }
}
var opt=new IllustratorSaveOptions(); opt.pdfCompatible=false;
d.saveAs(new File(COPY), opt);
"captions_fixed="+fixed;
