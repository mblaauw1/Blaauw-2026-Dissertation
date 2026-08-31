// PASS C — finish the de-duplication and make room on 0814 artboard 4.
//
// WHY A SECOND SWEEP: pass B matched items by their recorded visibleBounds, and 13 of 215 did not match.
// The reason is benign and predictable: opening a deck REFRESHES its links, and the group1 line plots had
// just been re-rendered in the new fit+SEM style, so their bounds changed between the dump and the removal.
// Those 8 remaining duplicate NAMES are therefore matched by name on the decks that are not the keeper.
//
// AND THE RE-FLOW: her standing rule is "if theres not space for them just resize the other figures on that
// board". Artboard 4 of the main deck had no free slot for the two collagen-vs-pooled figures, so every
// figure already on that board is scaled about the board centre to open one — nothing is moved off-board and
// nothing is deleted.
#target illustrator

var TMP = "/Volumes/4 MB/_claude_tmp";
var PDF = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf";
var HB  = new File(TMP + "/sweep_heartbeat.txt");
function beat(m) { try { HB.open("a"); HB.writeln(m); HB.close(); } catch (e) {} }

var DECK = {
  "0814":     "/Volumes/4 MB/1_DECKS/META_FIGURES_20260814.ai",
  "0813supp": "/Volumes/4 MB/1_DECKS/META_FIGURES_20260813_supplemental.ai",
  "0805":     "/Volumes/4 MB/ablation_plots/META_FIGURES_20260805.ai"
};

// name -> the decks it must be REMOVED from (the keeper deck is not listed)
var DROP = {
  "0805": ["G1_area_combined_trendscaled", "G1_centroid_movement_combined_meta", "G1_plate_rotation_combined_meta",
           "G1_roundness_combined_trendscaled", "G1_start_rounded_metaphase", "G1_violin2_mitotic_duration_journal",
           "G2_kk_distance_by_phase", "G4_fluor_vs_duration_zoom"],
  "0813supp": ["G1_area_combined_trendscaled", "G1_roundness_combined_trendscaled", "G2_kk_distance_by_phase"]
};

var REFLOW = { deck: "0814", ab: 4, scale: 0.82,
               place: ["G1_area_collagen_vs_pooled", "G1_roundness_collagen_vs_pooled"], w: 1500 };

app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
beat("START");
var report = [];
var i, j, k;

for (var tag in DECK) {
  var drop = DROP[tag] || [];
  var doReflow = (REFLOW.deck === tag);
  if (drop.length === 0 && !doReflow) continue;

  beat("open " + tag);
  var doc = app.open(new File(DECK[tag]));
  beat("opened " + doc.name);

  // unlock every layer for the pass; restore before saving
  var lockState = [];
  for (i = 0; i < doc.layers.length; i++) {
    var Ly = doc.layers[i]; var st = { lay: Ly, lk: false };
    try { st.lk = Ly.locked; Ly.locked = false; } catch (e) {}
    lockState.push(st);
  }

  // ---- name-based removals ----
  var want = {};
  for (i = 0; i < drop.length; i++) want[drop[i]] = 1;
  var removed = 0;
  if (drop.length) {
    for (i = doc.pageItems.length - 1; i >= 0; i--) {
      var it = doc.pageItems[i];
      var nm = "";
      try { if (it.typename === "PlacedItem" && it.file) nm = it.file.name.replace(/\.(pdf|png|ai|eps)$/i, ""); } catch (e) {}
      if (!nm || !want[nm]) continue;
      try { it.remove(); removed++; } catch (e) {}
    }
  }
  beat(tag + " name-removed=" + removed);
  report.push(tag + "\tNAME-REMOVED\t" + removed);

  // ---- artboard re-flow + placement ----
  if (doReflow) {
    var abi = REFLOW.ab - 1;
    var R = doc.artboards[abi].artboardRect;
    var ccx = (R[0] + R[2]) / 2, ccy = (R[1] + R[3]) / 2;

    // every TOP-LEVEL item whose bounds sit on this board, scaled about the board centre
    var onboard = [];
    for (i = 0; i < doc.pageItems.length; i++) {
      var p = doc.pageItems[i], pb = null;
      try { pb = p.visibleBounds; } catch (e) { continue; }
      try { if (p.parent.typename !== "Layer") continue; } catch (e) { continue; }
      if (pb[0] < R[2] && pb[2] > R[0] && pb[3] < R[1] && pb[1] > R[3]) onboard.push(p);
    }
    var sc = REFLOW.scale;
    for (i = 0; i < onboard.length; i++) {
      var p2 = onboard[i], b2 = null;
      try { b2 = p2.visibleBounds; } catch (e) { continue; }
      var cxi = (b2[0] + b2[2]) / 2, cyi = (b2[1] + b2[3]) / 2;
      try {
        p2.resize(sc * 100, sc * 100);
        var b3 = p2.visibleBounds;
        var ncx = ccx + (cxi - ccx) * sc, ncy = ccy + (cyi - ccy) * sc;
        p2.translate(ncx - (b3[0] + b3[2]) / 2, ncy - (b3[1] + b3[3]) / 2);
      } catch (e) {}
    }
    beat(tag + " reflowed " + onboard.length + " items on ab" + REFLOW.ab);
    report.push(tag + "\tREFLOW ab" + REFLOW.ab + "\t" + onboard.length + " items scaled " + sc);

    // the two collagen figures were already added by pass B (stacked, no free slot). Find them by name and
    // re-seat them into the space the re-flow just opened, rather than adding a second copy.
    var targets = [];
    for (i = 0; i < doc.pageItems.length; i++) {
      var q = doc.pageItems[i], qn = "";
      try { if (q.typename === "PlacedItem" && q.file) qn = q.file.name.replace(/\.(pdf|png|ai|eps)$/i, ""); } catch (e) {}
      for (j = 0; j < REFLOW.place.length; j++) if (qn === REFLOW.place[j]) targets.push(q);
    }
    for (j = 0; j < targets.length; j++) {
      var t = targets[j];
      // occupancy EXCLUDING the ones we are seating
      var occ = [];
      for (i = 0; i < doc.pageItems.length; i++) {
        var o = doc.pageItems[i], ob = null;
        var skip = false;
        for (k = 0; k < targets.length; k++) if (targets[k] === o) skip = true;
        if (skip) continue;
        try { ob = o.visibleBounds; } catch (e) { continue; }
        try { if (o.parent.typename !== "Layer") continue; } catch (e) { continue; }
        if (ob[0] < R[2] && ob[2] > R[0] && ob[3] < R[1] && ob[1] > R[3]) occ.push(ob);
      }
      for (k = 0; k < j; k++) { try { occ.push(targets[k].visibleBounds); } catch (e) {} }
      var w = t.width, h = t.height, STEP = 50, found = false, bx = R[0] + 40, by = R[1] - 40;
      for (var yy = R[1] - 40; yy - h > R[3] + 40 && !found; yy -= STEP) {
        for (var xx = R[0] + 40; xx + w < R[2] - 40 && !found; xx += STEP) {
          var ok = true;
          for (k = 0; k < occ.length; k++) {
            var oo = occ[k];
            if (xx < oo[2] && xx + w > oo[0] && yy > oo[3] && yy - h < oo[1]) { ok = false; break; }
          }
          if (ok) { bx = xx; by = yy; found = true; }
        }
      }
      t.left = bx; t.top = by;
      report.push(tag + "\tRESEAT\t" + REFLOW.place[j] + "\t" + (found ? "free slot" : "STILL NO SLOT"));
      beat(tag + " reseat " + j + " found=" + found);
    }
  }

  for (i = 0; i < lockState.length; i++) { try { lockState[i].lay.locked = lockState[i].lk; } catch (e) {} }
  try { doc.selection = null; } catch (e) {}
  var opts = new IllustratorSaveOptions();
  opts.compatibility = Compatibility.ILLUSTRATOR17;
  opts.pdfCompatible = false;
  doc.saveAs(new File(DECK[tag]), opts);
  doc.close(SaveOptions.SAVECHANGES);
  beat(tag + " saved");
}

var rf = new File(TMP + "/sweep_report.txt"); rf.encoding = "UTF-8"; rf.open("w");
for (i = 0; i < report.length; i++) rf.writeln(report[i]);
rf.close();
app.userInteractionLevel = UserInteractionLevel.DISPLAYALERTS;
beat("ALLDONE");
report.join("\n");
