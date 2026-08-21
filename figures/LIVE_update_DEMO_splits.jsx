#target illustrator
// Live, non-destructive update of the OPEN 'grouped copy.ai':
//  (1) relink the two stale combined DEMO plots IN PLACE to their _single (content swap, layout unchanged)
//  (2) stage the two _triple figures below all artwork, labeled, to drag into place
// Operates ONLY on the already-open document (no app.open / no close). Saves at the end.
var COPY="/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
var PDF="/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/";
var RELINK=[  // combined basename (lowercased) -> its _single replacement
  {from:"demo_lineplot_shape_by_metaphase.pdf",  to:PDF+"DEMO_lineplot_shape_by_metaphase_single.pdf",  name:"DEMO lineplot shape single"},
  {from:"demo_shape_rate_vs_metaphase.pdf",       to:PDF+"DEMO_shape_rate_vs_metaphase_single.pdf",       name:"DEMO shape-rate single"}
];
var STAGE=[  // _triple figures to add as NEW staged placements
  {path:PDF+"DEMO_lineplot_shape_by_metaphase_triple.pdf", base:"DEMO_lineplot_shape_by_metaphase_triple.pdf"},
  {path:PDF+"DEMO_shape_rate_vs_metaphase_triple.pdf",     base:"DEMO_shape_rate_vs_metaphase_triple.pdf"}
];

var d=null;
for (var q=0;q<app.documents.length;q++){
  if(app.documents[q].name=="ablation_figures_grouped copy.ai"){ d=app.documents[q]; break; } }
var opened=false;
if(!d){ d=app.open(new File(COPY)); opened=true; }
var lyr=d.activeLayer;

// (1) relink combined -> single, preserving on-canvas position & width
var relinked=0, notfound=[];
for (var r=0;r<RELINK.length;r++){
  var hit=false;
  for (var i=0;i<d.placedItems.length;i++){
    var pi=d.placedItems[i], f=null; try{f=pi.file;}catch(e){}
    if(!f) continue;
    if(decodeURI(f.name).toLowerCase()==RELINK[r].from){
      var pos=pi.position, w=pi.width, h=pi.height;
      var nf=new File(RELINK[r].to);
      if(!nf.exists){ notfound.push(RELINK[r].to); continue; }
      pi.file=nf;                               // relink (same aspect -> restore width keeps layout)
      var sc=w/pi.width; pi.width=pi.width*sc; pi.height=pi.height*sc; pi.position=pos;
      pi.name=RELINK[r].name; relinked++; hit=true;
    }
  }
  if(!hit) notfound.push(RELINK[r].from+" (not placed)");
}

// (2) already-linked basenames (stem, extension-agnostic) so we never stage a dup
var have={};
for (var i=0;i<d.placedItems.length;i++){ var f=null; try{f=d.placedItems[i].file;}catch(e){}
  if(f) have[decodeURI(f.name).toLowerCase().replace(/\.(pdf|png|svg)$/,"")]=true; }

// bounding box of all artwork -> stage BELOW it
var gb=null, it=d.pageItems;
for (var i=0;i<it.length;i++){ var b; try{b=it[i].visibleBounds;}catch(e){continue;}
  if(!gb) gb=[b[0],b[1],b[2],b[3]];
  else { if(b[0]<gb[0])gb[0]=b[0]; if(b[1]>gb[1])gb[1]=b[1]; if(b[2]>gb[2])gb[2]=b[2]; if(b[3]<gb[3])gb[3]=b[3]; } }
var left=gb?gb[0]:0, bottom=gb?gb[3]:0;
var STAGE_TOP=bottom-320, CW=520.0, CH=400.0, M=16.0, CAPH=26.0;
var added=0, missing=[];
for (var i=0;i<STAGE.length;i++){
  var stem=STAGE[i].base.toLowerCase().replace(/\.(pdf|png|svg)$/,"");
  if(have[stem]) continue; have[stem]=true;
  var file=new File(STAGE[i].path);
  if(!file.exists){ missing.push(STAGE[i].base); continue; }
  var x0=left+i*CW, top=STAGE_TOP;
  var pi=lyr.placedItems.add(); pi.file=file;
  var sc=Math.min((CW-2*M)/pi.width, (CH-CAPH-2*M)/pi.height);
  pi.width=pi.width*sc; pi.height=pi.height*sc;
  pi.position=[x0+(CW-pi.width)/2, top-M]; pi.name="NEW "+STAGE[i].base;
  var tf=lyr.textFrames.add(); tf.contents=STAGE[i].base.replace(/\.pdf$/i,"");
  tf.textRange.characterAttributes.size=11; tf.position=[x0+M, top-(CH-CAPH+8)];
  added++;
}
if(added>0){ var hd=lyr.textFrames.add();
  hd.contents="↓↓  "+added+" NEW _triple FIGURE(S) — drag into place next to their _single  ↓↓";
  hd.textRange.characterAttributes.size=26; hd.position=[left, STAGE_TOP+70]; }

var so=new IllustratorSaveOptions(); so.pdfCompatible=true;
d.saveAs(new File(COPY), so);
if(opened){ d.close(SaveOptions.DONOTSAVECHANGES); }
"relinked="+relinked+"  staged_triple="+added+"  missing="+missing.length+"  notfound="+notfound.length+(notfound.length?(" :: "+notfound.join(" | ")):"");
