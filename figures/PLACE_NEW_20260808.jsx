// Placement pass, 2026-08-08. ONE consolidated JSX (her rule: minimise Illustrator round-trips).
//
// Three jobs:
//   1. RELINK every placement on all four decks. All decks LINK the same _ai_relink PDFs, so re-rendering
//      a figure updates them all -- but only once each placement is re-pointed at its own docPath. That is
//      what pushes today's rebuilt figures (new annotations + the common-mode drift correction) onto the
//      boards. relink(file) forces the re-read; placedItem.update() is not a method and silently throws.
//   2. SWAP the superseded single-batch Hec1/Mad1 figure on META for the multi-batch one she asked for
//      ("not just from one group but from the multiple groups"). Swap in place, preserving position and
//      size, so the board layout is untouched.
//   3. PLACE the nine brand-new figures on NEW_FIGURES, on their OWN new artboard so nothing collides
//      with the 40 already there.
//
// META IS RELINKED AND SWAPPED, NEVER REBUILT -- she deletes figures from META deliberately and a rebuild
// would silently restore them.
// Artboards were DUMPED FIRST (DUMP_DECKS_20260808.jsx): META 9 boards 5100x5100, NEW_FIGURES AB1
// "NEW 2026-08-05" rect 0,-200,3740,-2900. The new board is placed BELOW that, inside the +/-16383 canvas.
// Saves use pdfCompatible=false (true bloats to ~588MB).
//
// HEARTBEAT: every step appends to place_heartbeat.txt so a watchdog can distinguish "working" from
// "hung" in seconds instead of waiting out a timeout.
#target illustrator
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}

var HB = new File("/Volumes/4 MB/_claude_tmp/place_heartbeat.txt");
function beat(msg) {
  try { HB.open("a"); HB.writeln((new Date()).getTime() + " " + msg); HB.close(); } catch (e) {}
}

var PDF = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/";
var META = "/Volumes/4 MB/ablation_plots/META_FIGURES_20260805.ai";
var NEWF = "/Volumes/4 MB/1_DECKS/NEW_FIGURES_20260804.ai";
var DOCS = [META, NEWF,
            "/Volumes/4 MB/1_DECKS/NEW_TIMESTRIPS_20260804.ai",
            "/Volumes/4 MB/1_DECKS/other_20260820.ai"];

var SWAP_ON_META = { "G5_hec1_mad1_dot_quant.pdf": "G5_hec1_mad1_multibatch_quant.pdf" };

var NEWFIGS = ["G1_imaging_rate_vs_metaphase_unmodified",
               "G5_mad1_kt_fluor_over_time",
               "G5_sac_active_kt_over_time",
               "G6_polar_dist_to_plate_over_metaphase",
               "G7_kt_movement_vs_context",
               "G7_prometa_single_vs_meta_triple",
               "G7_prophase_vs_prometaphase_triple",
               "G7_triple_converges_on_single",
               "G7_track_to_chromosome_assignment"];

var report = [];
beat("PLACE start");
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }

for (var k = 0; k < DOCS.length; k++) {
  // `path` IS RESERVED IN EXTENDSCRIPT -- naming a variable `path` silently resolved to the Illustrator
  // APPLICATION path (/Applications/Adobe%20Illustrator%202026), so app.open() tried to open the app
  // bundle and threw Error 1200/-54, which reads exactly like a permissions failure and is not one.
  // Same family as the recorded `open`/`L` ExtendScript shadowing bugs. Hence `docPath`.
  var docPath = DOCS[k];
  if (!(new File(docPath)).exists) { report.push(docPath + " :: MISSING"); beat("missing " + docPath); continue; }
  // RETRY THE OPEN. A freshly-relaunched Illustrator answers a trivial AppleScript within seconds but is
  // not yet able to open a document from the exFAT volume, and fails with Error 1200 / -54 -- which reads
  // like a permissions problem and is not one (the same file opened fine from a minimal script moments
  // later, the volume is writable, and there are no lock files). So: retry a few times with a pause
  // instead of aborting the whole pass on a warm-up race.
  var d = null, openErr = null;
  for (var att = 1; att <= 5 && !d; att++) {
    try { d = app.open(new File(docPath)); }
    catch (eO) {
      openErr = eO;
      beat("open attempt " + att + " failed on " + docPath + " :: " + eO);
      var t0 = (new Date()).getTime();
      while ((new Date()).getTime() - t0 < 4000) { /* pause without a sleep API */ }
    }
  }
  if (!d) { report.push(docPath + " :: OPEN FAILED after 5 attempts :: " + openErr);
            beat("OPEN FAILED " + docPath); continue; }
  var before = d.placedItems.length;
  var ok = 0, gone = 0, err = 0, swapped = 0, added = 0;

  // ---- 1. relink everything ----
  for (var i = d.placedItems.length - 1; i >= 0; i--) {
    var it = d.placedItems[i], f = null;
    try { f = it.file; } catch (eF) {}
    if (!f) { err++; continue; }
    var p = f.fsName, base = f.name;
    // ---- 2. swap on META, in place ----
    if (docPath === META && SWAP_ON_META[base]) {
      var np = new File(PDF + SWAP_ON_META[base]);
      if (np.exists) {
        // The replacement has a DIFFERENT aspect ratio from the figure it supersedes. relink() keeps the
        // existing frame, which would STRETCH it. So: remember the old box, relink, then rescale the new
        // artwork to FIT that box preserving its own aspect, and re-centre it there. The board layout is
        // unchanged; only the figure inside the slot changes.
        var ob = it.visibleBounds;                       // [left, top, right, bottom]
        var oL = ob[0], oT = ob[1], oW = ob[2] - ob[0], oH = ob[1] - ob[3];
        try {
          it.relink(np);
          var s2 = Math.min(oW / it.width, oH / it.height);
          it.width = it.width * s2; it.height = it.height * s2;
          it.left = oL + (oW - it.width) / 2;
          it.top  = oT - (oH - it.height) / 2;
          swapped++; ok++; beat("swapped " + base + " -> " + SWAP_ON_META[base]); continue;
        } catch (eS) { err++; continue; }
      }
    }
    if (!(new File(p)).exists) { gone++; continue; }
    try { it.relink(new File(p)); ok++; } catch (eR) { err++; }
  }
  beat("relinked " + d.name + " ok=" + ok + " swapped=" + swapped + " missing=" + gone + " err=" + err);

  // ---- 3. place the new figures, on their own artboard, only on NEW_FIGURES ----
  if (docPath === NEWF) {
    var LFIG = null;
    for (var li = 0; li < d.layers.length; li++) {
      if (d.layers[li].name === "figures") { LFIG = d.layers[li]; break; }
    }
    if (!LFIG) { LFIG = d.layers.add(); LFIG.name = "figures"; }
    // board below AB1 (which is 0,-200 .. 3740,-2900)
    var COLS = 3, CW = 1240, CH = 940, PAD = 40;
    var L0 = 0, T0 = -3100;
    var rows = Math.ceil(NEWFIGS.length / COLS);
    var boardRect = [L0, T0, L0 + COLS * CW, T0 - rows * CH];
    var ab = d.artboards.add(boardRect); ab.name = "NEW 2026-08-08";
    beat("added artboard NEW 2026-08-08 " + Math.round(boardRect[0]) + "," + Math.round(boardRect[1]) +
         "," + Math.round(boardRect[2]) + "," + Math.round(boardRect[3]));
    for (var n = 0; n < NEWFIGS.length; n++) {
      var file = new File(PDF + NEWFIGS[n] + ".pdf");
      if (!file.exists) { report.push("  NEW MISSING PDF: " + NEWFIGS[n]); beat("missing pdf " + NEWFIGS[n]); continue; }
      var pi = null;
      try { pi = LFIG.placedItems.add(); pi.file = file; } catch (eA) {
        report.push("  place failed " + NEWFIGS[n] + " " + eA); beat("place FAILED " + NEWFIGS[n]); continue;
      }
      // scale to FIT the cell, preserving aspect (a cell is a budget, not a frame)
      var cw = CW - 2 * PAD, ch = CH - 2 * PAD;
      var s = Math.min(cw / pi.width, ch / pi.height);
      pi.width = pi.width * s; pi.height = pi.height * s;
      var col = n % COLS, row = Math.floor(n / COLS);
      pi.left = L0 + col * CW + PAD + (cw - pi.width) / 2;
      pi.top  = T0 - row * CH - PAD - (ch - pi.height) / 2;
      added++;
      beat("placed " + NEWFIGS[n]);
    }
  }

  var after = d.placedItems.length;
  // CAPTURE THE NAME BEFORE CLOSING. Reading a document property after d.close() throws Error 45 and
  // killed this pass twice, right after META saved — it looked like a hang because osascript simply
  // vanished while Illustrator sat idle. This is the trap already recorded in NOTES section 8.
  var dname = d.name;
  var opts = new IllustratorSaveOptions(); opts.pdfCompatible = false;
  var mode = "saved";
  try { d.saveAs(new File(docPath), opts); } catch (eS2) { mode = "SAVE_FAILED " + eS2; }
  beat("saved " + dname + " " + mode);
  try { d.close(SaveOptions.DONOTSAVECHANGES); } catch (eC) {}
  report.push(dname + " :: placed " + before + " -> " + after + " relinked=" + ok +
              " swapped=" + swapped + " added=" + added + " missingFile=" + gone +
              " errors=" + err + " save=" + mode);
}
beat("PLACE done");
var rf = new File("/Volumes/4 MB/_claude_tmp/place_report_20260808.txt");
rf.open("w"); rf.write(report.join("\n")); rf.close();
report.join("\n");
