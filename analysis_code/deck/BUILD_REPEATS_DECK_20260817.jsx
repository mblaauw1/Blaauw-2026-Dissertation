// Build "repeated figures 081726.ai" and place every repeat / superseded / retired figure on it.
// READ-ONLY with respect to her six live decks — this script only CREATES a new document.
//
// TRAPS DELIBERATELY AVOIDED (NOTES §8/§14):
//   - `path` is RESERVED in ExtendScript -> aiPath / pdfPath.
//   - ARTBOARDS may not leave the canvas (x/y within about +/-7475): 3x3 boards of 4800 pt with a 150 pt
//     gutter spans 14700 pt, i.e. +/-7350. Objects may sit outside the canvas; artboards may NOT.
//   - never doc.save() (error 8700) -> saveAs with IllustratorSaveOptions, pdfCompatible = false.
//   - never leave items selected.
//   - heartbeat every few items so a watchdog can tell "slow" from "hung".
#target illustrator

var TMP  = "/Volumes/4 MB/_claude_tmp";
var PDF  = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf";
var OUTP = "/Volumes/4 MB/1_DECKS/repeated figures 081726.ai";
var HB   = new File(TMP + "/repeats_deck_heartbeat.txt");

function beat(m) { try { HB.open("a"); HB.writeln(m); HB.close(); } catch (e) {} }

function readAll(fp) {
  var f = new File(fp); f.encoding = "UTF-8"; f.open("r");
  var s = f.read(); f.close(); return s;
}

app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
beat("START");

// ---- the plan (JSON written by _claude_tmp/build_repeats_plan_20260817.py) ----
var plan = eval("(" + readAll(TMP + "/repeats_plan_20260817.json") + ")");
var items = [];
var i, j;
for (i = 0; i < plan.moves.length; i++) {
  items.push({ name: plan.moves[i].name, note: plan.moves[i].reason,
               from: plan.deckfile[plan.moves[i].deck] });
}
for (i = 0; i < plan.archives.length; i++) {
  items.push({ name: plan.archives[i], note: "retired per-cell-line version; the live decks carry the new fit + SEM band figure",
               from: "(regenerated with PERCELL=1)" });
}
beat("items=" + items.length);

// ---- geometry: ONE artboard, sized to content -----------------------------------------------------
// 2026-08-17: two attempts at a 3x3 grid of artboards both died on Error 1200 / 'CoOA' at
// `artboards.add()`, at 4800 pt AND at 3600 pt boards — so the failure is the MULTI-ARTBOARD layout
// itself, not the grid size, exactly as recorded in NOTES ("ONE artboard, sized to content"; "stacking
// artboards past the canvas looks like a hang"). The whole problem disappears if the document is CREATED
// at the size it needs: no artboardRect assignment, no artboards.add, nothing to push past the canvas.
var NCOL = 16;                                      // 16 x 16 = 256 slots for 244 figures
var CELL = 900;
var PAD  = 24;
var NROW = Math.ceil(items.length / NCOL);
var W = NCOL * CELL, H = NROW * CELL;
beat("one artboard " + W + "x" + H + " cols=" + NCOL + " rows=" + NROW);

var doc = app.documents.add(DocumentColorSpace.RGB, W, H);
var lay = doc.layers[0]; lay.name = "figures";
try { doc.artboards[0].name = "repeated figures 081726"; } catch (e) {}

var placed = 0, missing = [];
for (i = 0; i < items.length; i++) {
  var cc = i % NCOL, rr = Math.floor(i / NCOL);
  var cx = cc * CELL + CELL / 2;
  var cy = -(rr * CELL + CELL / 2) + H;             // artboard 0 spans y = H (top) down to 0

  var pf = new File(PDF + "/" + items[i].name + ".pdf");
  if (!pf.exists) { missing.push(items[i].name); continue; }
  try {
    var it = lay.placedItems.add();
    it.file = pf;
    var bw = it.width, bh = it.height;
    var avail = CELL - 2 * PAD;
    var sc = Math.min(avail / bw, avail / bh);      // UNIFORM scale: never distort her figures
    if (sc > 0 && sc !== 1) it.resize(sc * 100, sc * 100);
    it.left = cx - it.width / 2;
    it.top  = cy + it.height / 2;
    it.name = items[i].name;
    placed++;
  } catch (e) { missing.push(items[i].name + " ERR " + e); }
  if (i % 10 === 0) beat("placed " + i + "/" + items.length);
}
beat("placed=" + placed + " missing=" + missing.length);

// one caption, so the deck says what it is without needing this script
var cap = doc.layers.add(); cap.name = "board_titles";
var tf = cap.textFrames.add();
tf.contents = "repeated figures 081726 — duplicates, superseded versions and retired per-cell line plots, "
            + "moved off META_FIGURES_20260814 / _20260813_supplemental / NEW_FIGURES_20260804 / "
            + "META_FIGURES_20260805 / supplemental / NEW_TIMESTRIPS_20260804";
tf.textRange.characterAttributes.size = 40;
tf.left = 20; tf.top = H - 10;

// ---- save ----
var opts = new IllustratorSaveOptions();
opts.compatibility = Compatibility.ILLUSTRATOR17;
opts.pdfCompatible = false;                          // NOTES: pdfCompatible=true is the hang/size trap
doc.saveAs(new File(OUTP), opts);
beat("saved " + OUTP);

// report
var rf = new File(TMP + "/repeats_deck_report.txt"); rf.encoding = "UTF-8"; rf.open("w");
rf.writeln("placed\t" + placed);
rf.writeln("missing\t" + missing.length);
for (j = 0; j < missing.length; j++) rf.writeln("MISSING\t" + missing[j]);
rf.close();

doc.close(SaveOptions.SAVECHANGES);
app.userInteractionLevel = UserInteractionLevel.DISPLAYALERTS;
beat("DONE placed=" + placed);
"placed=" + placed + " missing=" + missing.length + " boards=" + nBoards;
