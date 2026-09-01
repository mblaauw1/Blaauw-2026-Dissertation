#target illustrator
app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
var AIF = "/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_pdf.ai";
var TARGET = "G2_metaphase_ablated.pdf";     // find the artboard holding this figure
var NEWPDF = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/G2_metaphase_ablated_abltometa.pdf";
var doc = app.open(new File(AIF));

// 1) locate the placed item whose link is the target figure
var tgt = null;
for (var i=0; i<doc.placedItems.length; i++){
  var pi = doc.placedItems[i];
  try { if (pi.file && String(pi.file.name).indexOf(TARGET) >= 0) { tgt = pi; break; } } catch(e){}
}
if (!tgt){ doc.close(SaveOptions.DONOTSAVECHANGES); throw new Error("FAILED target not found "+TARGET); }

// 2) which artboard contains it (by center point)
var vb = tgt.visibleBounds; // [L,T,R,B]
var cx=(vb[0]+vb[2])/2, cy=(vb[1]+vb[3])/2, ai=-1, r=null;
for (var a=0; a<doc.artboards.length; a++){
  var q=doc.artboards[a].artboardRect;
  if (cx>=q[0] && cx<=q[2] && cy<=q[1] && cy>=q[3]){ ai=a; r=q; break; }
}
if (ai<0){ ai=doc.artboards.length-1; r=doc.artboards[ai].artboardRect; }
var w=r[2]-r[0], h=r[1]-r[3];

// 3) preferred rect: directly BELOW the target artboard. Check overlap with any existing artboard.
var gap = h*0.12 + 40;
var nL=r[0], nT=r[3]-gap, nR=nL+w, nB=nT-h;
function overlaps(A){
  for (var a=0;a<doc.artboards.length;a++){
    var q=doc.artboards[a].artboardRect;   // [L,T,R,B]
    if (A[0] < q[2] && A[2] > q[0] && A[3] < q[1] && A[1] > q[3]) return true;
  }
  return false;
}
var newRect=[nL,nT,nR,nB]; var placedBelowTarget=true;
if (overlaps(newRect)){
  // fall back to clearly-free space: below the lowest artboard
  var minB=1e9;
  for (var a=0;a<doc.artboards.length;a++){ var q=doc.artboards[a].artboardRect; if (q[3]<minB) minB=q[3]; }
  nL=r[0]; nT=minB-gap; nR=nL+w; nB=nT-h; newRect=[nL,nT,nR,nB]; placedBelowTarget=false;
}

// 4) place the new figure linked, fit into the new rect
var np = doc.placedItems.add();
np.file = new File(NEWPDF);
var sc = Math.min((w*0.94)/np.width, (h*0.94)/np.height);
np.width *= sc; np.height *= sc;
np.position = [nL+(w-np.width)/2, nT-(h-np.height)/2];

// 5) add the artboard (Illustrator appends it at the end of the artboard list; its POSITION is below the target)
var nb = doc.artboards.add(newRect);
nb.name = "G2_metaphase_ablated_abltometa";

doc.save();
var msg = "OK new artboard '"+nb.name+"' (panel idx "+(doc.artboards.length-1)+") placed "+(placedBelowTarget? "DIRECTLY BELOW the G2_metaphase_ablated artboard (idx "+ai+")":"in FREE SPACE below all artboards (target idx "+ai+"'s row was occupied)")+"; figure linked to _ai_relink/pdf/G2_metaphase_ablated_abltometa.pdf";
doc.close(SaveOptions.SAVECHANGES);
app.userInteractionLevel = UserInteractionLevel.INTERACTIVE;
msg;
