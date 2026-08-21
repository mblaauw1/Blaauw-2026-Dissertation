var d=app.activeDocument;
function inAny(it){
  var b=it.geometricBounds; // [l,t,r,btm]
  for(var i=0;i<d.artboards.length;i++){
    var r=d.artboards[i].artboardRect; // [l,t,r,b]
    if(b[0]>=r[0]-2 && b[2]<=r[2]+2 && b[1]<=r[1]+2 && b[3]>=r[3]-2) return true;
  }
  return false;
}
var off=0, offlist="";
var all=d.pageItems;
for(var i=0;i<all.length;i++){ if(!inAny(all[i])){ off++; if(offlist.length<200) offlist+=all[i].typename+","; } }
// per-artboard placed count
var res="placed="+d.placedItems.length+" text="+d.textFrames.length+" abs="+d.artboards.length+" OFF_ARTBOARD="+off;
res;
