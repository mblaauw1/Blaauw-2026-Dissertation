// Where does "RETIRED" text actually live? Count every text frame containing it, per artboard, in
// BOTH decks - the earlier audit only reported non-retired boards and returned 0, which does not
// distinguish "correctly placed" from "no stamps exist at all".
#target illustrator
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var DOCS=["/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai",
          "/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_kinetochore_overflow.ai"];
var rep=[];
for(var k=0;k<DOCS.length;k++){
  var d=app.open(new File(DOCS[k]));
  var ri=-1;
  for(var a=0;a<d.artboards.length;a++) if(d.artboards[a].name.toUpperCase().indexOf("RETIRED")>=0){ri=a;break;}
  function abOf(it){ var b; try{b=it.visibleBounds;}catch(e){return -1;}
    var cx=(b[0]+b[2])/2, cy=(b[1]+b[3])/2;
    for(var q=0;q<d.artboards.length;q++){ var R=d.artboards[q].artboardRect;
      if(cx>=R[0]&&cx<=R[2]&&cy<=R[1]&&cy>=R[3]) return q; } return -1; }
  var perAb={}, total=0, samples=[];
  for(var t=0;t<d.textFrames.length;t++){
    var s=""; try{ s=String(d.textFrames[t].contents); }catch(e){}
    if(s.toUpperCase().indexOf("RETIRED")<0) continue;
    total++;
    var ab=abOf(d.textFrames[t]); var key="AB"+(ab+1);
    perAb[key]=(perAb[key]||0)+1;
    if(ab!==ri && samples.length<10) samples.push(key+": "+s.substring(0,40));
  }
  var lst=[]; for(var kk in perAb) lst.push(kk+"="+perAb[kk]);
  rep.push(DOCS[k].replace(/^.*\//,"")+" :: textFrames=" + d.textFrames.length +
           " containing RETIRED=" + total + " retiredBoard=AB"+(ri+1) +
           " byArtboard[" + lst.join(",") + "]" +
           (samples.length? " OFFBOARD_SAMPLES["+samples.join(" ; ")+"]" : ""));
  d.close(SaveOptions.DONOTSAVECHANGES);
}
rep.join("\n");
