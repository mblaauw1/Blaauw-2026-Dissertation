#target illustrator
// READ-ONLY full inventory of copy.ai -> /Volumes/4 MB/_scratch/copyai_full_20260722b.json
// artboards, placed items (file, missing, bounds, layer), text frames, path items (fill/stroke, bounds).
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch(e){}
var COPY = "/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
var d = null;
for (var q=0;q<app.documents.length;q++){ if(app.documents[q].name=="ablation_figures_grouped copy.ai"){ d=app.documents[q]; break; } }
var opened=false; if(!d){ d=app.open(new File(COPY)); opened=true; }

function esc(s){ return String(s).replace(/\\/g,"\\\\").replace(/"/g,'\\"').replace(/[\r\n]+/g," "); }
function r1(n){ return Math.round(n*10)/10; }

var abs=[];
for (var a=0;a<d.artboards.length;a++){ var r=d.artboards[a].artboardRect;
  abs.push('{"i":'+a+',"name":"'+esc(d.artboards[a].name)+'","rect":['+r1(r[0])+','+r1(r[1])+','+r1(r[2])+','+r1(r[3])+']}'); }
function abOf(b){ var cx=(b[0]+b[2])/2, cy=(b[1]+b[3])/2;
  for(var a=0;a<d.artboards.length;a++){var r=d.artboards[a].artboardRect;
    if(cx>=r[0]&&cx<=r[2]&&cy<=r[1]&&cy>=r[3]) return a;} return -1; }

var items=[];
for (var i=0;i<d.placedItems.length;i++){ var pi=d.placedItems[i];
  var fp="", base="", miss=1;
  try{ fp=decodeURI(pi.file.fsName); base=decodeURI(pi.file.name).replace(/\.(pdf|png|svg|eps|tif|jpg)$/i,""); miss = (new File(fp)).exists?0:1; }catch(e){ base="(nofile)"; }
  var b; try{b=pi.visibleBounds;}catch(e){ b=[0,0,0,0]; }
  var ly=""; try{ ly=pi.layer.name; }catch(e){}
  items.push('{"i":'+i+',"base":"'+esc(base)+'","file":"'+esc(fp)+'","missing":'+miss+',"name":"'+esc(pi.name)+'","b":['+r1(b[0])+','+r1(b[1])+','+r1(b[2])+','+r1(b[3])+'],"ab":'+abOf(b)+',"layer":"'+esc(ly)+'"}');
}

var tfs=[];
for (var i=0;i<d.textFrames.length;i++){ var t=d.textFrames[i];
  var c=""; try{ c=t.contents; }catch(e){}
  var b; try{b=t.visibleBounds;}catch(e){ b=[0,0,0,0]; }
  var ly=""; try{ ly=t.layer.name; }catch(e){}
  tfs.push('{"i":'+i+',"txt":"'+esc(c).substring(0,300)+'","b":['+r1(b[0])+','+r1(b[1])+','+r1(b[2])+','+r1(b[3])+'],"ab":'+abOf(b)+',"layer":"'+esc(ly)+'"}');
}

function colStr(c){ try{ if(!c) return "none";
  if(c.typename=="RGBColor") return "rgb("+Math.round(c.red)+","+Math.round(c.green)+","+Math.round(c.blue)+")";
  if(c.typename=="CMYKColor") return "cmyk("+Math.round(c.cyan)+","+Math.round(c.magenta)+","+Math.round(c.yellow)+","+Math.round(c.black)+")";
  if(c.typename=="GrayColor") return "gray("+Math.round(c.gray)+")";
  return c.typename; }catch(e){ return "err"; } }
var paths=[];
for (var i=0;i<d.pathItems.length;i++){ var p=d.pathItems[i];
  var b; try{b=p.visibleBounds;}catch(e){ continue; }
  var fl=false, st=false, fc="none", sc="none", ly="";
  try{ fl=p.filled; if(fl) fc=colStr(p.fillColor); }catch(e){}
  try{ st=p.stroked; if(st) sc=colStr(p.strokeColor); }catch(e){}
  try{ ly=p.layer.name; }catch(e){}
  paths.push('{"i":'+i+',"name":"'+esc(p.name)+'","b":['+r1(b[0])+','+r1(b[1])+','+r1(b[2])+','+r1(b[3])+'],"ab":'+abOf(b)+',"fill":"'+fc+'","stroke":"'+sc+'","layer":"'+esc(ly)+'"}');
}

var out='{"n_placed":'+d.placedItems.length+',"n_text":'+d.textFrames.length+',"n_path":'+d.pathItems.length+
 ',"artboards":['+abs.join(",")+'],"items":['+items.join(",")+'],"texts":['+tfs.join(",")+'],"paths":['+paths.join(",")+']}';
var f=new File("/Volumes/4 MB/_scratch/copyai_full_20260722b.json"); f.encoding="UTF-8"; f.open("w"); f.write(out); f.close();
if(opened){ d.close(SaveOptions.DONOTSAVECHANGES); }
"OK placed="+d.placedItems.length+" text="+d.textFrames.length+" paths="+d.pathItems.length+" abs="+d.artboards.length;
