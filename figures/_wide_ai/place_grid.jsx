// Place wide timestrip PNGs (LINKED) into a 2D grid of paginated artboards in ONE .ai.
// Artboard coords must stay within ~±16383pt, so pages are laid out in a 2D grid CENTERED on the origin.
#target illustrator
app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
var MANIFEST = "__MANIFEST__";
var OUTAI    = "__OUTAI__";
var START    = __START__;
var COUNT    = __COUNT__;
var PERPAGE  = 24, COLS = 4, ROWS = 6;      // 24 timestrips per artboard-page
var CELLW = 360, CELLH = 250, PAD = 18;
var PAGEGAP = 70;
var PAGES_PER_ROW = 7;                        // 2D grid of pages (keeps within canvas)

function readLines(p){ var f=new File(p); f.open("r"); var s=f.read(); f.close(); return s.split("\n"); }
var raw = readLines(MANIFEST); var paths=[];
for (var i=0;i<raw.length;i++){ var t=raw[i].replace(/^\s+|\s+$/g,""); if(t.length>3) paths.push(t); }
if (COUNT<0) COUNT = paths.length - START;
var end = Math.min(START+COUNT, paths.length);

var pageW = COLS*(CELLW+PAD)+PAD;
var pageH = ROWS*(CELLH+PAD)+PAD;
var pitchX = pageW+PAGEGAP, pitchY = pageH+PAGEGAP;
var totalPages = Math.ceil(paths.length/PERPAGE);
var pageRows = Math.ceil(totalPages/PAGES_PER_ROW);
var originX = -(PAGES_PER_ROW*pitchX)/2;      // center the whole page-grid on origin
var originY =  (pageRows*pitchY)/2;

function pageRect(page){
  var px = page%PAGES_PER_ROW, py = Math.floor(page/PAGES_PER_ROW);
  var x0 = originX + px*pitchX;
  var y1 = originY - py*pitchY;
  return [x0, y1, x0+pageW, y1-pageH];
}

var f=new File(OUTAI);
var doc = f.exists ? app.open(f) : app.documents.add(DocumentColorSpace.RGB, 100, 100);
while (doc.artboards.length < Math.ceil(end/PERPAGE)){
  doc.artboards.add(pageRect(doc.artboards.length));
}
var placed=0;
for (var idx=START; idx<end; idx++){
  var page = Math.floor(idx/PERPAGE), inpage = idx%PERPAGE;
  var col = inpage%COLS, row = Math.floor(inpage/COLS);
  var r = pageRect(page);            // [L,T,R,B]
  var cellX = r[0] + PAD + col*(CELLW+PAD);
  var cellY = r[1] - PAD - row*(CELLH+PAD);
  var pf = new File(paths[idx]);
  if (!pf.exists) continue;
  var pi = doc.placedItems.add(); pi.file = pf;      // LINKED
  var s = Math.min(CELLW/pi.width, CELLH/pi.height);
  pi.width *= s; pi.height *= s;
  pi.position = [cellX + (CELLW-pi.width)/2, cellY - (CELLH-pi.height)/2];
  placed++;
}
var opt = new IllustratorSaveOptions(); opt.pdfCompatible = false;
doc.saveAs(new File(OUTAI), opt);
"" + placed + " placed; artboards=" + doc.artboards.length;
