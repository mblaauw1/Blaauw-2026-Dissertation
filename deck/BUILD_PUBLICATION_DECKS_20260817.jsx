// PASS E — the PUBLICATION copies of the main figure deck and the main supplemental deck.
//
// USER 2026-08-17: "Make a version of the main figure and main supplemental figure ai files that dont have
// any of the 'extra words' - you know, like the titles for the figures, or explanation sentences beneath
// them ... And in these versions, make x and y-axis labels extremely standardized."
//
// HOW THE TWO HALVES ARE DONE, and why here vs in the builders:
//   * The figure TITLES and the explanation sentences that sit INSIDE each plot are matplotlib text baked
//     into the linked PDF, so no Illustrator pass can remove them. They are stripped in the GENERATOR
//     (lib.apply_style under PUB=1, which also rewrites every axis label and cohort name through
//     canon_labels) and written to a parallel library, `_ai_relink/pdf_pub/`. This script just relinks.
//   * The figure titles that live ON THE DECK ("Figure 9: Creation of sisterless kinetochores ...") are
//     Illustrator TextFrames on her `board_titles` layer, with the working figure-id labels on `labels`.
//     Those two layers are HIDDEN, not deleted, so the publication copy can be turned back into the
//     working copy with two clicks and nothing of hers is destroyed. The schematic text on
//     `legend_bullets` and `figures` STAYS -- it is artwork, not commentary.
//
// SIZE: a pub figure is SHORTER than its working twin (the title is gone). Each relinked item therefore
// keeps its LEFT and TOP and is scaled UNIFORMLY to its original WIDTH, so columns stay aligned and the
// only change is that figures get shorter -- which can free space but can never create an overlap.
#target illustrator

var TMP = "/Volumes/4 MB/_claude_tmp";
var PUB = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf_pub";
var HB  = new File(TMP + "/pubdeck_heartbeat.txt");
function beat(m) { try { HB.open("a"); HB.writeln(m); HB.close(); } catch (e) {} }

var JOBS = [
  { src: "/Volumes/4 MB/1_DECKS/META_FIGURES_20260814.ai",
    dst: "/Volumes/4 MB/1_DECKS/META_FIGURES_20260814_PUBLICATION.ai" },
  { src: "/Volumes/4 MB/1_DECKS/META_FIGURES_20260813_supplemental.ai",
    dst: "/Volumes/4 MB/1_DECKS/META_FIGURES_20260813_supplemental_PUBLICATION.ai" }
];
var HIDE_LAYERS = ["board_titles", "labels"];

app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
beat("START");
var report = [];
var i, j;

for (j = 0; j < JOBS.length; j++) {
  var job = JOBS[j];
  beat("open " + job.src);
  var doc = app.open(new File(job.src));
  beat("opened " + doc.name);

  var lockState = [];
  for (i = 0; i < doc.layers.length; i++) {
    var Ly = doc.layers[i]; var st = { lay: Ly, lk: false };
    try { st.lk = Ly.locked; Ly.locked = false; } catch (e) {}
    lockState.push(st);
  }

  // ---- relink every figure that has a publication twin ----
  var relinked = 0, nopub = 0, names = [];
  for (i = 0; i < doc.pageItems.length; i++) {
    var it = doc.pageItems[i];
    if (it.typename !== "PlacedItem") continue;
    var nm = "";
    try { if (it.file) nm = it.file.name.replace(/\.(pdf|png|ai|eps)$/i, ""); } catch (e) {}
    if (!nm) continue;
    var pf = new File(PUB + "/" + nm + ".pdf");
    if (!pf.exists) { nopub++; names.push(nm); continue; }
    var b0 = null;
    try { b0 = it.visibleBounds; } catch (e) { continue; }
    var W0 = b0[2] - b0[0], L0 = b0[0], T0 = b0[1];
    try {
      it.file = pf;
      var b1 = it.visibleBounds;
      var W1 = b1[2] - b1[0];
      if (W1 > 0) {
        var sc = W0 / W1;
        if (sc !== 1) it.resize(sc * 100, sc * 100);
      }
      var b2 = it.visibleBounds;
      it.translate(L0 - b2[0], T0 - b2[1]);        // keep the original left/top anchor
      relinked++;
    } catch (e) {}
    if (i % 50 === 0) beat("relinked " + relinked);
  }
  beat("relinked=" + relinked + " no_pub_twin=" + nopub);

  // ---- hide the on-deck titles and the working labels ----
  // 🔴 HIDE THE TEXT, NOT THE LAYER. Hiding `board_titles` outright also hid the NINE PLACED FIGURES that
  // happen to live on that layer -- caught when a publication overlap turned out to be an invisible figure
  // sitting inside another one. Only TextFrames are hidden now, so her section titles and the working
  // figure-id labels go while every figure stays exactly where she put it.
  var hidden = [], nhid = 0;
  for (i = 0; i < doc.layers.length; i++) {
    var _nm = doc.layers[i].name;
    var _match = false;
    for (var k = 0; k < HIDE_LAYERS.length; k++) if (_nm === HIDE_LAYERS[k]) _match = true;
    if (!_match) continue;
    try { doc.layers[i].visible = true; doc.layers[i].locked = false; } catch (e) {}
    var _tfs = doc.layers[i].textFrames;
    for (var t2 = _tfs.length - 1; t2 >= 0; t2--) {
      try { _tfs[t2].hidden = true; nhid++; } catch (e) {}
    }
    hidden.push(_nm);
  }
  report.push(job.dst + "\tTEXT HIDDEN\t" + nhid + " text frames on " + hidden.join(","));

  for (i = 0; i < lockState.length; i++) { try { lockState[i].lay.locked = lockState[i].lk; } catch (e) {} }
  try { doc.selection = null; } catch (e) {}
  var opts = new IllustratorSaveOptions();
  opts.compatibility = Compatibility.ILLUSTRATOR17;
  opts.pdfCompatible = false;
  doc.saveAs(new File(job.dst), opts);            // saveAs to the NEW path: the working deck is untouched
  doc.close(SaveOptions.DONOTSAVECHANGES);
  beat("saved " + job.dst);
  report.push(job.dst + "\tRELINKED\t" + relinked + "\tNO_PUB_TWIN\t" + nopub +
              "\tHIDDEN\t" + hidden.join(",") + "\tMISSING\t" + names.slice(0, 40).join(" | "));
}

var rf = new File(TMP + "/pubdeck_report.txt"); rf.encoding = "UTF-8"; rf.open("w");
for (i = 0; i < report.length; i++) rf.writeln(report[i]);
rf.close();
app.userInteractionLevel = UserInteractionLevel.DISPLAYALERTS;
beat("ALLDONE");
report.join("\n");
