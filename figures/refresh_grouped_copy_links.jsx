// Safely refresh all linked figures in "ablation_figures_grouped copy.ai" to their current on-disk versions,
// WITHOUT moving anything. Preserves each placed item's exact position + size (your arrangement) and only
// re-reads the linked file's content. REFUSES to run if the copy is open in Illustrator (so it can never
// discard unsaved edits). Run AFTER you have saved + closed the copy.
#target illustrator
app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;   // suppress any modal that cancels the scripted save
var COPY="/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
// 1) HARD SAFETY: abort if the copy is currently open (do not touch it)
for (var q=0;q<app.documents.length;q++){
  try{ if(app.documents[q].fullName && app.documents[q].fullName.fsName==COPY){
    throw new Error("ABORT: 'ablation_figures_grouped copy.ai' is OPEN — save + close it first, then re-run. Nothing was changed."); } }catch(e){ if((""+e).indexOf("ABORT")>=0) throw e; }
}
var d=app.open(new File(COPY));
var refreshed=0, missing=0, kept=0;
for (var i=0;i<d.placedItems.length;i++){
  var pi=d.placedItems[i]; var f=null; try{f=pi.file;}catch(e){}
  if(!f){ kept++; continue; }                 // embedded (none expected) -> leave
  if(!f.exists){ missing++; continue; }        // broken link -> leave as-is, count it
  var pos=pi.position, w=pi.width, h=pi.height; // remember EXACT placement
  try{
    pi.file=f;                                 // re-read the (possibly refreshed) linked file
    pi.position=pos; pi.width=w; pi.height=h;   // restore your arrangement precisely
    refreshed++;
  }catch(e2){ kept++; }
}
var so=new IllustratorSaveOptions(); so.pdfCompatible=false;   // drop the duplicate embedded-PDF stream: ~halves the 584MB save so it stops cancelling (8700)
d.saveAs(new File(COPY), so); d.close(SaveOptions.DONOTSAVECHANGES);
"refreshed="+refreshed+" placements | missing_link="+missing+" | untouched="+kept;
