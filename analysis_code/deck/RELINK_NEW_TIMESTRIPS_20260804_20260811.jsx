// Force META to re-read every linked file, so the deck shows the CURRENT art.
//
// The links are already correct -- they point at files rebuilt today -- but Illustrator caches each placed
// file's preview inside the .ai and only re-reads on an explicit link update. Several PDFs were rebuilt at
// 09:46, after the document's last save at 09:44, so the document is showing stale previews of current files.
//
// Re-assigning `.file` forces the re-read, but it also resizes the item to the new artwork's natural size --
// which would silently rescale her layout. So each item's position and size are recorded first and restored
// immediately after, and the totals are checked before saving.
#target illustrator
var AI="/Volumes/4 MB/1_DECKS/NEW_TIMESTRIPS_20260804.ai";
var doc=app.open(new File(AI)); app.activeDocument=doc;
var log=[]; var n0=doc.pageItems.length;
try{ var bak=new File(AI.replace(/\.ai$/,".bak_pre_relink_20260811.ai")); if(!bak.exists) (new File(AI)).copy(bak); }catch(e){ log.push("backup failed: "+e); }
var done=0, skipped=0, moved=0;
for(var i=0;i<doc.placedItems.length;i++){
  var it=doc.placedItems[i], f=null;
  try{ f=it.file; }catch(e){ f=null; }
  if(!f || !f.exists){ skipped++; continue; }
  var p=it.position, w=it.width, h=it.height;
  try{
    it.file=f;                       // forces a re-read of the linked artwork
    it.width=w; it.height=h;         // restore exact size
    it.position=p;                   // and exact position
    var p2=it.position;
    if(Math.abs(p2[0]-p[0])>0.5||Math.abs(p2[1]-p[1])>0.5) moved++;
    done++;
  }catch(e2){ skipped++; }
}
log.push("relinked="+done+"  skipped="+skipped+"  position drift="+moved);
log.push("pageItems "+n0+" -> "+doc.pageItems.length);
if(doc.pageItems.length!==n0){ log.push("ABORT: item count changed; not saving"); doc.close(SaveOptions.DONOTSAVECHANGES); }
else { var o=new IllustratorSaveOptions(); o.pdfCompatible=false; doc.saveAs(new File(AI),o); log.push("saved"); doc.close(SaveOptions.DONOTSAVECHANGES); }
var lf=new File("/Volumes/4 MB/_claude_tmp/relink_NEW_TIMESTRIPS_20260804.txt"); lf.open("w"); lf.write(log.join("\n")); lf.close();
log.join("\n");
