// PASS B — remove the figures that moved to "repeated figures 081726.ai" from the six live decks, and place
// the four new figures she asked for. Every removal has a copy already sitting on the repeats deck (built and
// verified first, 244/244 placed), so nothing is lost at any point.
//
// TRAPS DELIBERATELY AVOIDED (NOTES §8/§14):
//   - `path` is RESERVED -> aiPath.
//   - never doc.save() (8700) -> saveAs onto itself with pdfCompatible=false.
//   - never revert her edits: this only removes items the plan names, matched by their EXACT recorded bounds.
//   - opening a deck REFRESHES its links, which is wanted here (the re-rendered figures come in).
//   - never leave items selected.
#target illustrator

var TMP  = "/Volumes/4 MB/_claude_tmp";
var PDF  = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf";
var HB   = new File(TMP + "/move_place_heartbeat.txt");
function beat(m) { try { HB.open("a"); HB.writeln(m); HB.close(); } catch (e) {} }
function readAll(fp) { var f = new File(fp); f.encoding = "UTF-8"; f.open("r"); var s = f.read(); f.close(); return s; }

var DECK = {
  "0814":     "/Volumes/4 MB/1_DECKS/META_FIGURES_20260814.ai",
  "0813supp": "/Volumes/4 MB/1_DECKS/META_FIGURES_20260813_supplemental.ai",
  "newfig":   "/Volumes/4 MB/1_DECKS/NEW_FIGURES_20260804.ai",
  "0805":     "/Volumes/4 MB/ablation_plots/META_FIGURES_20260805.ai",
  "supp":     "/Volumes/4 MB/1_DECKS/other.ai",
  "newts":    "/Volumes/4 MB/1_DECKS/NEW_TIMESTRIPS_20260804.ai"
};

// NEW FIGURES -> deck + 1-based artboard.
//   G1_violin2_all_cohorts : she named the destination outright ("to the supplemental figure, artboard 2").
//   the collagen table and the collagen-vs-pooled lines go on the MAIN deck: board 2 is the
//   "one sisterless KT does not delay metaphase, several do" board (durations), board 4 is the
//   "longer metaphase + cell-shape phenotypes" board — the shape traces belong there.
var NEW = [
  { deck: "0813supp", ab: 2, name: "G1_violin2_all_cohorts",           w: 1900 },
  { deck: "0814",     ab: 2, name: "G1_collagen_duration_table",       w: 1900 },
  { deck: "0814",     ab: 4, name: "G1_area_collagen_vs_pooled",       w: 1500 },
  { deck: "0814",     ab: 4, name: "G1_roundness_collagen_vs_pooled",  w: 1500 }
];

app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
beat("START");
var plan = eval("(" + readAll(TMP + "/repeats_plan_20260817.json") + ")");

// plan.moves -> per-deck lookup keyed by "kind|L|T" at one decimal, exactly as the dump wrote it
var want = {};
var i, j, k;
for (i = 0; i < plan.moves.length; i++) {
  var m = plan.moves[i];
  if (!want[m.deck]) want[m.deck] = {};
  want[m.deck][m.key] = m.name;
}

function keyOf(it) {
  try {
    var b = it.visibleBounds;
    return it.typename + "|" + b[0].toFixed(1) + "|" + b[1].toFixed(1);
  } catch (e) { return null; }
}

var report = [];
for (var tag in DECK) {
  var newHere = [];
  for (i = 0; i < NEW.length; i++) if (NEW[i].deck === tag) newHere.push(NEW[i]);
  var wantHere = want[tag];
  if (!wantHere && newHere.length === 0) continue;

  beat("open " + tag);
  var doc = app.open(new File(DECK[tag]));
  var docName = doc.name;
  beat("opened " + docName);

  // ---- removals (walk BACKWARDS: removing shifts the collection) ----
  // Unlock every layer for the pass and restore each layer's state afterwards: a locked layer silently
  // makes remove() fail, which would have left duplicates behind with no error to show for it.
  var lockState = [];
  for (i = 0; i < doc.layers.length; i++) {
    var Ly = doc.layers[i];
    var st = { lay: Ly, lk: false, vs: true };
    try { st.lk = Ly.locked; Ly.locked = false; } catch (e) {}
    try { st.vs = Ly.visible; } catch (e) {}
    lockState.push(st);
  }
  var removed = 0, notfound = 0;
  if (wantHere) {
    var seen = {};
    for (i = doc.pageItems.length - 1; i >= 0; i--) {
      var it = doc.pageItems[i];
      var kk = keyOf(it);
      if (kk === null || !wantHere[kk]) continue;
      try { it.remove(); removed++; seen[kk] = 1; } catch (e) {}
      if (removed % 20 === 0) beat(tag + " removed " + removed);
    }
    for (var kx in wantHere) if (!seen[kx]) notfound++;
  }
  beat(tag + " removed=" + removed + " notfound=" + notfound);

  // ---- placements ----
  var addedNames = [];
  for (j = 0; j < newHere.length; j++) {
    var spec = newHere[j];
    var pf = new File(PDF + "/" + spec.name + ".pdf");
    if (!pf.exists) { report.push(tag + "\tMISSING PDF\t" + spec.name); continue; }
    var abi = spec.ab - 1;
    if (abi < 0 || abi >= doc.artboards.length) { report.push(tag + "\tNO ARTBOARD " + spec.ab + "\t" + spec.name); continue; }
    var R = doc.artboards[abi].artboardRect;      // [L,T,R,B]

    // collect what is already on this board, so the new figure lands in genuinely free space
    var occ = [];
    for (i = 0; i < doc.pageItems.length; i++) {
      var p = doc.pageItems[i];
      var pb = null;
      try { pb = p.visibleBounds; } catch (e) { continue; }
      try { if (p.parent.typename !== "Layer") continue; } catch (e) { continue; }
      if (pb[0] < R[2] && pb[2] > R[0] && pb[3] < R[1] && pb[1] > R[3]) occ.push(pb);
    }

    // TARGET LAYER — a DEDICATED NEW LAYER, not one of hers.
    // Two runs died with Error 8705 ("Target layer cannot be modified") at `it2.file = pf`, first on
    // doc.layers[0] and then on the by-name/by-content pick, even with every layer unlocked: setting .file
    // acts on doc.activeLayer, and on these decks that lands on a locked or template layer. Adding our own
    // layer sidesteps the whole question, is guaranteed writable, and has the side benefit that everything
    // this session placed is identifiable and reversible in one click on her side.
    var LAYNAME = "session_20260817";
    var lay = null;
    for (i = 0; i < doc.layers.length; i++) { if (doc.layers[i].name === LAYNAME) { lay = doc.layers[i]; break; } }
    if (lay === null) { lay = doc.layers.add(); lay.name = LAYNAME; }
    try { lay.locked = false; lay.visible = true; } catch (e) {}
    try { doc.activeLayer = lay; } catch (e) {}
    var it2 = lay.placedItems.add();
    it2.file = pf;
    var sc = spec.w / it2.width;
    if (sc > 0 && sc !== 1) it2.resize(sc * 100, sc * 100);
    var w = it2.width, h = it2.height;

    // scan the board on a coarse grid for the first slot that overlaps nothing
    var STEP = 60, found = false, bx = R[0] + 40, by = R[1] - 40;
    for (var yy = R[1] - 40; yy - h > R[3] + 40 && !found; yy -= STEP) {
      for (var xx = R[0] + 40; xx + w < R[2] - 40 && !found; xx += STEP) {
        var ok = true;
        for (k = 0; k < occ.length; k++) {
          var o = occ[k];
          if (xx < o[2] && xx + w > o[0] && yy > o[3] && yy - h < o[1]) { ok = false; break; }
        }
        if (ok) { bx = xx; by = yy; found = true; }
      }
    }
    it2.left = bx; it2.top = by;
    it2.name = spec.name;
    addedNames.push(spec.name + (found ? "" : " (NO FREE SLOT - placed top-left, re-flow needed)"));
    report.push(tag + "\tPLACED ab" + spec.ab + "\t" + spec.name + "\t" + (found ? "free slot" : "NO FREE SLOT"));
  }

  // ---- save in place ----
  for (i = 0; i < lockState.length; i++) { try { lockState[i].lay.locked = lockState[i].lk; } catch (e) {} }
  try { doc.selection = null; } catch (e) {}
  var opts = new IllustratorSaveOptions();
  opts.compatibility = Compatibility.ILLUSTRATOR17;
  opts.pdfCompatible = false;
  doc.saveAs(new File(DECK[tag]), opts);
  beat(tag + " saved");
  doc.close(SaveOptions.SAVECHANGES);
  report.push(tag + "\tREMOVED\t" + removed + "\tNOTFOUND\t" + notfound + "\tADDED\t" + addedNames.join(" | "));
}

var rf = new File(TMP + "/move_place_report.txt"); rf.encoding = "UTF-8"; rf.open("w");
for (i = 0; i < report.length; i++) rf.writeln(report[i]);
rf.close();
app.userInteractionLevel = UserInteractionLevel.DISPLAYALERTS;
beat("ALLDONE");
report.join("\n");
