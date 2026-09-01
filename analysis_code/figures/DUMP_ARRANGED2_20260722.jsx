#target illustrator
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch(e){}
var P="/Volumes/4 MB/1_DECKS/arranged_into_paper_figures_2.ai";
var d=app.open(new File(P));
function esc(s){ return String(s).replace(/\\/g,"\\\\").replace(/"/g,'\\"').replace(/[\r\n]+/g," "); }
function r1(n){ return Math.round(n*10)/10; }
var abs=[];
for (var a=0;a<d.artboards.length;a++){ var r=d.artboards[a].artboardRect;
  abs.push('{"i":'+a+',"name":"'+esc(d.artboards[a].name)+'","rect":['+r1(r[0])+','+r1(r[1])+','+r1(r[2])+','+r1(r[3])+']}'); }
function abOf(b){ var cx=(b[0]+b[2])/2, cy=(b[1]+b[3])/2;
  for(var a=0;a<d.artboards.length;a++){var r=d.artboards[a].artboardRect;
    if(cx>=r[0]&&cx<=r[2]&&cy<=r[1]&&cy>=r[3]) return a;} return -1; }
var items=[];
for (var i=0;i<d.placedItems.length;i++){ var pi=d.placedItems[i]; var fp="",base="",miss=1;
  try{ fp=decodeURI(pi.file.fsName); base=decodeURI(pi.file.name).replace(/\.(pdf|png|svg|eps)$/i,""); miss=(new File(fp)).exists?0:1; }catch(e){ base="(nofile)"; }
  var b; try{b=pi.visibleBounds;}catch(e){b=[0,0,0,0];}
  items.push('{"base":"'+esc(base)+'","file":"'+esc(fp)+'","missing":'+miss+',"b":['+r1(b[0])+','+r1(b[1])+','+r1(b[2])+','+r1(b[3])+'],"ab":'+abOf(b)+'}'); }
var tfs=[];
for (var i=0;i<d.textFrames.length;i++){ var t=d.textFrames[i]; var c=""; try{c=t.contents;}catch(e){}
  var b; try{b=t.visibleBounds;}catch(e){b=[0,0,0,0];}
  tfs.push('{"txt":"'+esc(c).substring(0,200)+'","b":['+r1(b[0])+','+r1(b[1])+','+r1(b[2])+','+r1(b[3])+'],"ab":'+abOf(b)+'}'); }
var out='{"n_placed":'+d.placedItems.length+',"n_text":'+d.textFrames.length+',"n_path":'+d.pathItems.length+',"artboards":['+abs.join(",")+'],"items":['+items.join(",")+'],"texts":['+tfs.join(",")+']}';
var f=new File("/Volumes/4 MB/_scratch/arranged2_20260722.json"); f.encoding="UTF-8"; f.open("w"); f.write(out); f.close();
var np=d.placedItems.length, nt=d.textFrames.length, na=d.artboards.length;
d.close(SaveOptions.DONOTSAVECHANGES);
"OK placed="+np+" text="+nt+" abs="+na;
