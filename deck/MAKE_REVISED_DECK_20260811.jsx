// A NEW file holding EVERY timestrip revised on 2026-08-11, each with its revisions applied.
//
// USER: "just make a new file and put every timestrip ive had you revise this mornign on it. make sure it
// has the revisiosn i told you to do as you place it."
//
// NO artboardRect ASSIGNMENT ANYWHERE. The first attempt placed all 16, then tried to size the artboard to
// the content; that threw 1200/'CoOA', and a failed artboardRect assignment ROLLS THE DOCUMENT BACK -- on a
// new document that means back to EMPTY, which is what then got saved. The document is therefore created at
// a size already big enough for the content (measured from that run: 2133 x 8489 pt) and never resized.
#target illustrator
var OUT="/Volumes/4 MB/ablation_plots/_superseded_decks/REVISED_TIMESTRIPS_20260811.ai";
var W=2400, H=9200;
var ITEMS=[
 {
  "n": "nf10_off-target__20250402_ptk_yfpcdc20_22",
  "f": "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/nf10_off-target__20250402_ptk_yfpcdc20_22.pdf",
  "c": "off-target 20250402 ptk_yfpcdc20_22: abl ROI up 5um, mon ROI right 8um, 15um off top+right, monitoring frame 1 down 10um"
 },
 {
  "n": "nf10_1-sisterless-persistent-polar__20250402_ptk_yfpcdc20_2",
  "f": "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/nf10_1-sisterless-persistent-polar__20250402_ptk_yfpcdc20_2.pdf",
  "c": "1-sisterless persistent-polar 20250402 ptk_yfpcdc20_2: whole-cell crop tightened to cell + 5um each side"
 },
 {
  "n": "nf9_double-chromosome__20260420_ptk2_eyfp_cdc20_1_ablation_71",
  "f": "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/nf9_double-chromosome__20260420_ptk2_eyfp_cdc20_1_ablation_71.pdf",
  "c": "double-chromosome ablation_71: duplicate 0:13 zoom column removed, ablation magnification matched to monitoring (both 29.7um), ROIs up 15um"
 },
 {
  "n": "nf9_3-sisterless__20260417_ptk2_eyfp_cdc20_ablation_18",
  "f": "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/nf9_3-sisterless__20260417_ptk2_eyfp_cdc20_ablation_18.pdf",
  "c": "3-sisterless ablation_18: whole-cell ROI down 3um"
 },
 {
  "n": "2-sisterless_aligned",
  "f": "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/2-sisterless_aligned.pdf",
  "c": "2-sisterless ablation_19: ablation-2 frames 39/42/1:51, whole-cell crop 10um shorter all sides, post frame ROI down 5um left 2.5um"
 },
 {
  "n": "G5_mad1_timestrip_20260303_Mad1_Ptk_Eyfpmad1_ablation_10_aligned",
  "f": "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/G5_mad1_timestrip_20260303_Mad1_Ptk_Eyfpmad1_ablation_10_aligned.pdf",
  "c": "Mad1 ablation_10: ablation ROI left 10um up 5um, 5um off left+right, 10um off bottom"
 },
 {
  "n": "G5_item4_hec1_timestrip_xy5",
  "f": "/Volumes/4 MB/ablation_figures_20260625/group4/G5_item4_hec1_timestrip_xy5.png",
  "c": "hec1/mad1 xy5: third panel ROI right 15um"
 },
 {
  "n": "20250711_double_ablation_18_frap0_aligned",
  "f": "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/20250711_double_ablation_18_frap0_aligned.pdf",
  "c": "FRAP double ablation_18 #0: 10um top / 5um sides / 4um bottom trim, crop box now detected from fluor (phase render is 0 bytes)"
 },
 {
  "n": "unmanipulated-control",
  "f": "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/unmanipulated-control.pdf",
  "c": "unmanipulated control 20250321 ptk_yfpcdc20__2_xy1 (no ablation)"
 },
 {
  "n": "nf9_unmanipulated-control__20250320_ptk_yfpcdc20__1_xy3",
  "f": "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/nf9_unmanipulated-control__20250320_ptk_yfpcdc20__1_xy3.pdf",
  "c": "unmanipulated control 20250320 ptk_yfpcdc20__1_xy3 (no ablation)"
 },
 {
  "n": "G5_lagfrag_20250411_ptk_yfpcdc20_11_t9",
  "f": "/Volumes/4 MB/ablation_figures_20260625/group5/G5_lagfrag_20250411_ptk_yfpcdc20_11_t9.png",
  "c": "fragmenting laggard 20250411_ptk_yfpcdc20_11_t9: one frame per minute from anaphase, brightfield+fluor context rows with locator box"
 },
 {
  "n": "G5_lagfrag_20250806_single_ablation_3_t3",
  "f": "/Volumes/4 MB/ablation_figures_20260625/group5/G5_lagfrag_20250806_single_ablation_3_t3.png",
  "c": "fragmenting laggard 20250806_single_ablation_3_t3: one frame per minute from anaphase, brightfield+fluor context rows with locator box"
 },
 {
  "n": "G5_lagfrag_20250910_triple_ablation_collagen_14_t2",
  "f": "/Volumes/4 MB/ablation_figures_20260625/group5/G5_lagfrag_20250910_triple_ablation_collagen_14_t2.png",
  "c": "fragmenting laggard 20250910_triple_ablation_collagen_14_t2: one frame per minute from anaphase, brightfield+fluor context rows with locator box"
 },
 {
  "n": "G5_lagfrag_20250910_triple_ablation_collagen_22_t3",
  "f": "/Volumes/4 MB/ablation_figures_20260625/group5/G5_lagfrag_20250910_triple_ablation_collagen_22_t3.png",
  "c": "fragmenting laggard 20250910_triple_ablation_collagen_22_t3: one frame per minute from anaphase, brightfield+fluor context rows with locator box"
 },
 {
  "n": "G5_lagfrag_20250923_triple_ablation_collagen_2_t1",
  "f": "/Volumes/4 MB/ablation_figures_20260625/group5/G5_lagfrag_20250923_triple_ablation_collagen_2_t1.png",
  "c": "fragmenting laggard 20250923_triple_ablation_collagen_2_t1: one frame per minute from anaphase, brightfield+fluor context rows with locator box"
 },
 {
  "n": "G5_lagfrag_20260416_single_ablation_15_t2",
  "f": "/Volumes/4 MB/ablation_figures_20260625/group5/G5_lagfrag_20260416_single_ablation_15_t2.png",
  "c": "fragmenting laggard 20260416_single_ablation_15_t2: one frame per minute from anaphase, brightfield+fluor context rows with locator box"
 }
];
var log=[];
var doc=app.documents.add(DocumentColorSpace.RGB, W, H);
var r=doc.artboards[0].artboardRect;
log.push("artboard ["+r[0].toFixed(0)+", "+r[1].toFixed(0)+", "+r[2].toFixed(0)+", "+r[3].toFixed(0)+"]");
var x=r[0]+60, y=r[1]-70, placed=0, failed=[];
for (var k=0;k<ITEMS.length;k++){
  var f=new File(ITEMS[k].f);
  if(!f.exists){ failed.push(ITEMS[k].n+" (missing)"); continue; }
  try{
    var it=doc.placedItems.add(); it.file=f;
    var w=it.width,h=it.height,s=Math.min(2200/w,400/h,1.0);
    it.width=w*s; it.height=h*s;
    var t1=doc.textFrames.add(); t1.contents=ITEMS[k].n;
    t1.textRange.characterAttributes.size=15; t1.position=[x, y];
    var t2=doc.textFrames.add(); t2.contents=ITEMS[k].c;
    t2.textRange.characterAttributes.size=10; t2.position=[x, y-20];
    it.position=[x, y-32];
    y -= (h*s + 110);
    placed++;
  }catch(e){ failed.push(ITEMS[k].n+" ("+e+")"); }
}
log.push("placed="+placed+" failed="+failed.length+"  lowest y="+y.toFixed(0));
for(var q=0;q<failed.length;q++) log.push("   FAILED: "+failed[q]);
var minX=1e9,maxX=-1e9,minY=1e9,maxY=-1e9;
for(var i2=0;i2<doc.pageItems.length;i2++){var b=doc.pageItems[i2].visibleBounds;
 if(b[0]<minX)minX=b[0]; if(b[2]>maxX)maxX=b[2]; if(b[3]<minY)minY=b[3]; if(b[1]>maxY)maxY=b[1];}
log.push("items="+doc.pageItems.length+"  content T="+maxY.toFixed(0)+" B="+minY.toFixed(0)+" R="+maxX.toFixed(0));
log.push("all inside artboard: "+((minX>=r[0]&&maxX<=r[2]&&minY>=r[3]&&maxY<=r[1])?"YES":"NO"));
if(doc.pageItems.length===0){ log.push("EMPTY -- not saving"); }
else { var o=new IllustratorSaveOptions(); o.pdfCompatible=false; doc.saveAs(new File(OUT), o); log.push("saved "+OUT); }
doc.close(SaveOptions.DONOTSAVECHANGES);
var lf=new File("/Volumes/4 MB/_claude_tmp/newdeck_report.txt"); lf.open("w"); lf.write(log.join("\n")); lf.close();
log.join("\n");
