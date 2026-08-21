// PASS F — swap the current FRAP plot for the BPS-poster version, on every deck that carries it, and put
// the superseded one on the repeats deck.
//
// USER 2026-08-17: "the frap plot from the bps poster we made a few months ago: its far better than the
// frap plot we have now, and i want to replace the frap plot we have now with this version, but in order
// to do so i need to have a record of the data that i can include in my thesis, so find the data that this
// plot was created from before subbing it into any illustrator docs."
// THE DATA CAME FIRST: `/Volumes/4 MB/4_TABLES_AND_REPORTS/frap_bps_poster_data_20260817/` holds the CSVs, the measuring tool
// and the poster's own render, with a README tracing poster -> PDF -> script -> data. The figure was then
// REBUILT from that data as `G4_frap_bps_trace_kinetics` (n=6 complete / n=7 FRAP, matching the poster
// legend exactly), so it now lives in the pipeline instead of being a foreign PDF.
//
// The replacement keeps the old figure's LEFT/TOP and WIDTH, so nothing else on the board moves.
#target illustrator

var PDF = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf";
var TMP = "/Volumes/4 MB/_claude_tmp";
var HB  = new File(TMP + "/frapswap_heartbeat.txt");
function beat(m) { try { HB.open("a"); HB.writeln(m); HB.close(); } catch (e) {} }

var OLD = "G4_frap_vs_ablation_selected_combined_20s";
var NEW = "G4_frap_bps_trace_kinetics";

var DECKS = [
  "/Volumes/4 MB/1_DECKS/META_FIGURES_20260814.ai",
  "/Volumes/4 MB/1_DECKS/META_FIGURES_20260813_supplemental.ai",
  "/Volumes/4 MB/1_DECKS/NEW_FIGURES_20260804.ai",
  "/Volumes/4 MB/ablation_plots/META_FIGURES_20260805.ai",
  "/Volumes/4 MB/1_DECKS/other.ai",
  "/Volumes/4 MB/1_DECKS/NEW_TIMESTRIPS_20260804.ai"
];
var REPEATS = "/Volumes/4 MB/1_DECKS/repeated figures 081726.ai";

app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
beat("START");
var report = [], i, j, swapped_total = 0;

for (j = 0; j < DECKS.length; j++) {
  var doc = app.open(new File(DECKS[j]));
  beat("opened " + doc.name);
  var lockState = [];
  for (i = 0; i < doc.layers.length; i++) {
    var Ly = doc.layers[i]; var st = { lay: Ly, lk: false };
    try { st.lk = Ly.locked; Ly.locked = false; } catch (e) {}
    lockState.push(st);
  }
  var swapped = 0;
  for (i = 0; i < doc.pageItems.length; i++) {
    var it = doc.pageItems[i];
    if (it.typename !== "PlacedItem") continue;
    var nm = "";
    try { if (it.file) nm = it.file.name.replace(/\.(pdf|png|ai|eps)$/i, ""); } catch (e) {}
    if (nm !== OLD) continue;
    var pf = new File(PDF + "/" + NEW + ".pdf");
    if (!pf.exists) { report.push(doc.name + "\tNEW PDF MISSING"); break; }
    var b0 = it.visibleBounds, L0 = b0[0], T0 = b0[1], W0 = b0[2] - b0[0];
    try {
      it.file = pf;
      var b1 = it.visibleBounds, W1 = b1[2] - b1[0];
      if (W1 > 0 && W0 / W1 !== 1) it.resize((W0 / W1) * 100, (W0 / W1) * 100);
      var b2 = it.visibleBounds;
      it.translate(L0 - b2[0], T0 - b2[1]);
      it.name = NEW;
      swapped++;
    } catch (e) { report.push(doc.name + "\tSWAP ERROR " + e); }
  }
  for (i = 0; i < lockState.length; i++) { try { lockState[i].lay.locked = lockState[i].lk; } catch (e) {} }
  if (swapped) {
    try { doc.selection = null; } catch (e) {}
    var opts = new IllustratorSaveOptions();
    opts.compatibility = Compatibility.ILLUSTRATOR17;
    opts.pdfCompatible = false;
    doc.saveAs(new File(DECKS[j]), opts);
    swapped_total += swapped;
  }
  report.push(doc.name + "\tSWAPPED\t" + swapped);
  doc.close(swapped ? SaveOptions.SAVECHANGES : SaveOptions.DONOTSAVECHANGES);
  beat(DECKS[j] + " swapped=" + swapped);
}

// the superseded version joins the repeats deck, in the first free cell of its grid
if (swapped_total > 0) {
  var rd = app.open(new File(REPEATS));
  var lay = rd.layers[0];
  for (i = 0; i < rd.layers.length; i++) if (rd.layers[i].name === "figures") lay = rd.layers[i];
  try { lay.locked = false; rd.activeLayer = lay; } catch (e) {}
  var R = rd.artboards[0].artboardRect;
  var CELL = 900, PAD = 24, NCOL = 16;
  var n = 0; try { n = lay.placedItems.length; } catch (e) {}
  var cc = n % NCOL, rr = Math.floor(n / NCOL);
  var cx = R[0] + cc * CELL + CELL / 2, cy = R[1] - (rr * CELL + CELL / 2);
  var of = new File(PDF + "/" + OLD + ".pdf");
  if (of.exists) {
    var ni = lay.placedItems.add();
    ni.file = of;
    var sc = (CELL - 2 * PAD) / Math.max(ni.width, ni.height);
    if (sc !== 1) ni.resize(sc * 100, sc * 100);
    ni.left = cx - ni.width / 2; ni.top = cy + ni.height / 2;
    ni.name = OLD;
    report.push("repeats deck\tADDED superseded\t" + OLD);
  }
  try { rd.selection = null; } catch (e) {}
  var o2 = new IllustratorSaveOptions();
  o2.compatibility = Compatibility.ILLUSTRATOR17; o2.pdfCompatible = false;
  rd.saveAs(new File(REPEATS), o2);
  rd.close(SaveOptions.SAVECHANGES);
  beat("repeats updated");
}

var rf = new File(TMP + "/frapswap_report.txt"); rf.encoding = "UTF-8"; rf.open("w");
for (i = 0; i < report.length; i++) rf.writeln(report[i]);
rf.close();
app.userInteractionLevel = UserInteractionLevel.DISPLAYALERTS;
beat("ALLDONE");
report.join("\n");
