#target illustrator
// READ-ONLY survey of yellow-filled shapes: what they are, where they sit, and whether any figure or
// text is underneath them. Nothing is modified -- deleting before looking is how real work gets lost.
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var d = app.open(new File("/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai"));

function isYellow(c){
  try{
    if(!c) return false;
    if(c.typename=="RGBColor")  return c.red>200 && c.green>180 && c.blue<140;
    if(c.typename=="CMYKColor") return c.cyan<20 && c.yellow>50 && c.black<20 && c.magenta<40;
    if(c.typename=="GrayColor") return false;
  }catch(e){}
  return false;
}
function abOf(b){
  var cx=(b[0]+b[2])/2, cy=(b[1]+b[3])/2;
  for(var a=0;a<d.artboards.length;a++){var r=d.artboards[a].artboardRect;
    if(cx>=r[0]&&cx<=r[2]&&cy<=r[1]&&cy>=r[3]) return "AB"+(a+1);}
  return "OFF";
}
// bounds of everything that is real content, to test whether a box covers anything
var content=[];
for(var i=0;i<d.placedItems.length;i++){try{content.push(d.placedItems[i].visibleBounds);}catch(e){}}
for(var i=0;i<d.textFrames.length;i++){try{content.push(d.textFrames[i].visibleBounds);}catch(e){}}
function coversContent(b){
  for(var i=0;i<content.length;i++){var a=content[i];
    var l=Math.max(a[0],b[0]),r=Math.min(a[2],b[2]),t=Math.min(a[1],b[1]),bo=Math.max(a[3],b[3]);
    if(r>l&&t>bo) return true;}
  return false;
}
var rows=[], n=0;
for(var i=0;i<d.pathItems.length;i++){
  var p=d.pathItems[i];
  var f=false; try{ f = p.filled && isYellow(p.fillColor); }catch(e){}
  if(!f) continue;
  var b; try{b=p.visibleBounds;}catch(e){continue;}
  n++;
  rows.push([abOf(b), Math.round(b[2]-b[0])+"x"+Math.round(b[1]-b[3]),
             (coversContent(b)?"over-content":"EMPTY"), (p.name||""), p.layer.name].join("\t"));
}
var out="yellow-filled pathItems: "+n+"  (of "+d.pathItems.length+" paths total)\nAB\tsize_pt\toverlap\tname\tlayer\n"+rows.join("\n");
d.close(SaveOptions.DONOTSAVECHANGES);
out;
