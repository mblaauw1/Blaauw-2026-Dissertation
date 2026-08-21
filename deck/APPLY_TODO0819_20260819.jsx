// APPLY the 2026-08-19 to-do list to the decks, from the generated plan
// (/Volumes/4 MB/_claude_tmp/todo0819_plan.json, written by ablation_plots/build_todo0819_deck_plan.py).
//
// OPERATIONS, applied in this order per deck so one never invalidates another's key:
//   relink       swap a placed figure's linked PDF, keeping its slot and its width
//   pieces       replace ONE placed figure with its independently movable pieces/panels, stacked in place
//   remove       delete a placed figure (it has moved to another deck)
//   place        add a figure, either at explicit coordinates (a sync-back) or in the first free slot
//   delartboard  delete an artboard (descending index, so earlier deletions do not shift later ones)
//
// TRAPS DELIBERATELY AVOIDED (NOTES §8/§14, and the ones this project has actually hit):
//   - `path` is RESERVED in ExtendScript -> aiPath.
//   - never doc.save() (error 8700) -> saveAs onto itself with pdfCompatible=false.
//   - setting `.file` acts on doc.activeLayer -> error 8705 on a locked/template layer. Every layer is
//     unlocked for the pass, the item's OWN layer is made active before a relink, and new art goes on our
//     own `session_20260819` layer, which is guaranteed writable and is one click for her to hide.
//   - removing shifts the collection -> walk pageItems BACKWARDS.
//   - a scripted edit that silently does nothing is the documented failure mode here, so every op reports
//     found/not-found and the totals are written to a report file for verification afterwards.
//   - artboard indices shift as boards are deleted -> deletions are sorted DESCENDING per deck.
//   - never leave items selected.
#target illustrator

var TMP = "/Volumes/4 MB/_claude_tmp";
var HB = new File(TMP + "/todo0819_heartbeat.txt");
function beat(m) { try { HB.open("a"); HB.writeln(m); HB.close(); } catch (e) {} }
function readAll(fp) { var f = new File(fp); f.encoding = "UTF-8"; f.open("r"); var s = f.read(); f.close(); return s; }

app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
beat("START " + new Date());

var plan = eval("(" + readAll(TMP + "/todo0819_plan.json") + ")");
var PDF = plan.pdf, PUBPDF = plan.pub_pdf;
var LAYNAME = "session_20260819";
var report = [];

function keyOf(it) {
  try { var b = it.visibleBounds; return it.typename + "|" + b[0].toFixed(1) + "|" + b[1].toFixed(1); }
  catch (e) { return null; }
}
function pdfFor(name, isPub) { return new File((isPub ? PUBPDF : PDF) + "/" + name + ".pdf"); }

// group ops by deck, preserving order within each kind
var byDeck = {};
for (var i = 0; i < plan.ops.length; i++) {
  var o = plan.ops[i];
  if (!byDeck[o.deck]) byDeck[o.deck] = [];
  byDeck[o.deck].push(o);
}

for (var tag in byDeck) {
  var aiPath = plan.decks[tag];
  if (!aiPath) { report.push(tag + "\tNO PATH"); continue; }
  var ops = byDeck[tag];
  beat("=== " + tag + " open (" + ops.length + " ops)");
  var doc = null;
  try { doc = app.open(new File(aiPath)); } catch (eo) { report.push(tag + "\tOPEN FAIL\t" + eo); beat("OPEN FAIL " + tag); continue; }
  var docName = doc.name;
  beat(tag + " opened " + docName);

  // unlock everything for the pass, remember the state, restore before saving
  var lockState = [];
  for (i = 0; i < doc.layers.length; i++) {
    var Ly = doc.layers[i];
    var st = { lay: Ly, lk: false };
    try { st.lk = Ly.locked; Ly.locked = false; } catch (e) {}
    lockState.push(st);
  }
  // our own layer for anything NEW
  var lay = null;
  for (i = 0; i < doc.layers.length; i++) { if (doc.layers[i].name === LAYNAME) { lay = doc.layers[i]; break; } }
  if (lay === null) { lay = doc.layers.add(); lay.name = LAYNAME; }
  try { lay.locked = false; lay.visible = true; } catch (e) {}

  var nRelink = 0, nPieces = 0, nRemove = 0, nPlace = 0, nAb = 0, nMiss = 0;

  // ---- index the items we need by key, ONCE ------------------------------------------------------
  function findByKey(k) {
    for (var q = doc.pageItems.length - 1; q >= 0; q--) {
      if (keyOf(doc.pageItems[q]) === k) return doc.pageItems[q];
    }
    return null;
  }

  // ---- 1. RELINK ---------------------------------------------------------------------------------
  for (i = 0; i < ops.length; i++) {
    var op = ops[i];
    if (op.op !== "relink") continue;
    var it = findByKey(op.key);
    if (it === null) { nMiss++; report.push(tag + "\tRELINK NOT FOUND\t" + op.key + "\t-> " + op.to); continue; }
    var pf = pdfFor(op.to, op.pub);
    if (!pf.exists) { nMiss++; report.push(tag + "\tRELINK PDF MISSING\t" + op.to); continue; }
    var L0 = it.left, T0 = it.top, W0 = it.width;
    try { doc.activeLayer = it.layer; } catch (e) {}
    try {
      it.file = pf;
      // a publication figure is SHORTER than its working twin (no title), so keep LEFT/TOP and scale
      // uniformly back to the original WIDTH -- columns stay aligned, only the height changes.
      if (it.width > 0) { var sc = W0 / it.width; if (sc > 0 && sc !== 1) it.resize(sc * 100, sc * 100); }
      it.left = L0; it.top = T0; it.name = op.to;
      nRelink++;
      report.push(tag + "\tRELINK\t" + op.to);
    } catch (er) { nMiss++; report.push(tag + "\tRELINK FAILED\t" + op.to + "\t" + er); }
  }
  beat(tag + " relinked=" + nRelink);

  // ---- 2. PIECES (replace one placement with its movable pieces / panels) -------------------------
  for (i = 0; i < ops.length; i++) {
    var op2 = ops[i];
    if (op2.op !== "pieces") continue;
    var parent = findByKey(op2.key);
    if (parent === null) { nMiss++; report.push(tag + "\tPIECES PARENT NOT FOUND\t" + op2.name); continue; }
    var PL = parent.left, PT = parent.top, PW = parent.width;
    var ok = true;
    for (var j = 0; j < op2.names.length; j++) { if (!pdfFor(op2.names[j], op2.pub).exists) { ok = false; break; } }
    if (!ok) { nMiss++; report.push(tag + "\tPIECES PDF MISSING\t" + op2.name); continue; }
    try { parent.remove(); } catch (e) { report.push(tag + "\tPIECES PARENT REMOVE FAILED\t" + op2.name); }
    try { doc.activeLayer = lay; } catch (e) {}
    var y = PT;
    for (j = 0; j < op2.names.length; j++) {
      var np = lay.placedItems.add();
      np.file = pdfFor(op2.names[j], op2.pub);
      var s2 = PW / np.width;
      if (s2 > 0 && s2 !== 1) np.resize(s2 * 100, s2 * 100);
      np.left = PL; np.top = y;
      np.name = op2.names[j];
      y -= (np.height + 8);          // 8 pt gutter so the pieces read as separate objects, not one block
    }
    nPieces++;
    report.push(tag + "\tPIECES\t" + op2.name + "\t-> " + op2.names.length);
    if (nPieces % 5 === 0) beat(tag + " pieces=" + nPieces);
  }
  beat(tag + " pieces=" + nPieces);

  // ---- 3. REMOVE ---------------------------------------------------------------------------------
  for (i = 0; i < ops.length; i++) {
    var op3 = ops[i];
    if (op3.op !== "remove") continue;
    var r = findByKey(op3.key);
    if (r === null) { nMiss++; report.push(tag + "\tREMOVE NOT FOUND\t" + op3.name); continue; }
    try { r.remove(); nRemove++; report.push(tag + "\tREMOVE\t" + op3.name); }
    catch (e) { nMiss++; report.push(tag + "\tREMOVE FAILED\t" + op3.name); }
  }
  beat(tag + " removed=" + nRemove);

  // ---- 4. PLACE ----------------------------------------------------------------------------------
  for (i = 0; i < ops.length; i++) {
    var op4 = ops[i];
    if (op4.op !== "place") continue;
    var pf4 = pdfFor(op4.name, op4.pub);
    if (!pf4.exists) { nMiss++; report.push(tag + "\tPLACE PDF MISSING\t" + op4.name); continue; }
    try { doc.activeLayer = lay; } catch (e) {}
    var it4 = lay.placedItems.add();
    it4.file = pf4;
    if (op4.w && it4.width > 0) { var s4 = op4.w / it4.width; if (s4 > 0 && s4 !== 1) it4.resize(s4 * 100, s4 * 100); }
    it4.name = op4.name;
    if (op4.at) {                       // a sync-back: her publication copy's own coordinates
      it4.left = op4.at[0]; it4.top = op4.at[1];
      report.push(tag + "\tPLACE@\t" + op4.name);
    } else {
      var abi = (op4.ab || 1) - 1;
      if (abi < 0 || abi >= doc.artboards.length) { it4.remove(); nMiss++; report.push(tag + "\tNO ARTBOARD " + op4.ab + "\t" + op4.name); continue; }
      var R = doc.artboards[abi].artboardRect;   // [L,T,R,B]
      // what already occupies this board, so the new figure lands in genuinely free space
      var occ = [];
      for (var q2 = 0; q2 < doc.pageItems.length; q2++) {
        var p2 = doc.pageItems[q2];
        if (p2 === it4) continue;
        var pb = null;
        try { pb = p2.visibleBounds; } catch (e) { continue; }
        try { if (p2.parent.typename !== "Layer") continue; } catch (e) { continue; }
        if (pb[0] < R[2] && pb[2] > R[0] && pb[3] < R[1] && pb[1] > R[3]) occ.push(pb);
      }
      var w4 = it4.width, h4 = it4.height, STEP = 60, found = false, bx = R[0] + 40, by = R[1] - 40;
      for (var yy = R[1] - 40; yy - h4 > R[3] + 40 && !found; yy -= STEP) {
        for (var xx = R[0] + 40; xx + w4 < R[2] - 40 && !found; xx += STEP) {
          var free = true;
          for (var k2 = 0; k2 < occ.length; k2++) {
            var o2 = occ[k2];
            if (xx < o2[2] && xx + w4 > o2[0] && yy > o2[3] && yy - h4 < o2[1]) { free = false; break; }
          }
          if (free) { bx = xx; by = yy; found = true; }
        }
      }
      it4.left = bx; it4.top = by;
      report.push(tag + "\tPLACE ab" + op4.ab + "\t" + op4.name + "\t" + (found ? "free slot" : "NO FREE SLOT"));
    }
    nPlace++;
    if (nPlace % 10 === 0) beat(tag + " placed=" + nPlace);
  }
  beat(tag + " placed=" + nPlace);

  // ---- 5. DELETE ARTBOARDS (descending) -----------------------------------------------------------
  var dels = [];
  for (i = 0; i < ops.length; i++) if (ops[i].op === "delartboard") dels.push(ops[i].ab);
  dels.sort(function (a, b) { return b - a; });
  for (i = 0; i < dels.length; i++) {
    var idx = dels[i] - 1;
    if (idx < 0 || idx >= doc.artboards.length) { report.push(tag + "\tARTBOARD OUT OF RANGE\t" + dels[i]); continue; }
    try { doc.artboards[idx].remove(); nAb++; report.push(tag + "\tDELETE ARTBOARD\t" + dels[i]); }
    catch (e) { nMiss++; report.push(tag + "\tDELETE ARTBOARD FAILED\t" + dels[i] + "\t" + e); }
  }
  beat(tag + " artboards deleted=" + nAb + " now=" + doc.artboards.length);

  // ---- save in place ------------------------------------------------------------------------------
  for (i = 0; i < lockState.length; i++) { try { lockState[i].lay.locked = lockState[i].lk; } catch (e) {} }
  try { doc.selection = null; } catch (e) {}
  var opts = new IllustratorSaveOptions();
  opts.compatibility = Compatibility.ILLUSTRATOR17;
  opts.pdfCompatible = false;
  doc.saveAs(new File(aiPath), opts);
  beat(tag + " SAVED");
  doc.close(SaveOptions.SAVECHANGES);
  report.push(tag + "\tTOTALS\trelink=" + nRelink + "\tpieces=" + nPieces + "\tremove=" + nRemove +
              "\tplace=" + nPlace + "\tartboards_deleted=" + nAb + "\tmissed=" + nMiss);
}

var rf = new File(TMP + "/todo0819_report.txt"); rf.encoding = "UTF-8"; rf.open("w");
for (i = 0; i < report.length; i++) rf.writeln(report[i]);
rf.close();
app.userInteractionLevel = UserInteractionLevel.DISPLAYALERTS;
beat("ALLDONE " + new Date());
"ALLDONE";
