// READ-ONLY geometry dump of ALL SIX live decks: artboards + items, with artboard assignment by OVERLAP
// (not centre) and RasterItem/embedded coverage. Written 2026-08-17 for the overlap audit + repeats audit.
//
// TRAPS DELIBERATELY AVOIDED (NOTES §8/§14):
//   - `path` is RESERVED in ExtendScript -> use aiPath.
//   - never read a doc property AFTER close() (Error 45) -> capture docName first.
//   - artboard assignment by CENTRE misfiles anything spanning a boundary -> record ALL overlapped boards.
//   - a scan that names only PlacedItems with a .file is BLIND to embedded art -> record RasterItems too,
//     and never exclude a layer by NAME.
//   - modal on open (missing links / fonts / profile) looks like a hang -> DONTDISPLAYALERTS first.
//   - heartbeat every N items so a watchdog can tell "slow" from "hung".
#target illustrator

var DECKS = [
  ["0814",     "/Volumes/4 MB/1_DECKS/META_FIGURES_20260814.ai"],
  ["0813supp", "/Volumes/4 MB/1_DECKS/META_FIGURES_20260813_supplemental.ai"],
  ["newfig",   "/Volumes/4 MB/1_DECKS/NEW_FIGURES_20260804.ai"],
  ["0805",     "/Volumes/4 MB/ablation_plots/META_FIGURES_20260805.ai"],
  ["supp",     "/Volumes/4 MB/1_DECKS/other.ai"],
  ["newts",    "/Volumes/4 MB/1_DECKS/NEW_TIMESTRIPS_20260804.ai"]
];

var HB = new File("/Volumes/4 MB/_claude_tmp/dump_all6_heartbeat.txt");
function beat(msg) { try { HB.open("a"); HB.writeln(msg); HB.close(); } catch (e) {} }

app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
beat("START alerts suppressed");

var summary = [];

for (var d = 0; d < DECKS.length; d++) {
  var tag = DECKS[d][0], aiPath = DECKS[d][1];
  beat("=== deck " + tag + " open");

  var doc = null;
  try { doc = app.open(new File(aiPath)); } catch (eo) { beat("OPEN FAIL " + tag + " " + eo); continue; }
  var docName = doc.name;
  beat("opened " + docName);

  var out = [];
  var nAb = 0;
  try { nAb = doc.artboards.length; } catch (e) {}
  beat(tag + " artboards=" + nAb);

  var abRect = [];
  for (var a = 0; a < nAb; a++) {
    var r = null, an = "";
    try { r = doc.artboards[a].artboardRect; } catch (e) {}
    try { an = doc.artboards[a].name; } catch (e) {}
    if (r === null) { abRect.push(null); continue; }
    abRect.push(r);
    out.push("ARTBOARD\t" + (a + 1) + "\t\t\t\t" + an + "\t" +
             r[0].toFixed(1) + "\t" + r[1].toFixed(1) + "\t" + r[2].toFixed(1) + "\t" + r[3].toFixed(1) + "\t\t\t");
  }

  // ALL artboards the bounds overlap, plus the one containing the centre.
  function abList(b) {
    var hits = [];
    for (var k = 0; k < abRect.length; k++) {
      var r = abRect[k];
      if (r === null) continue;
      // rects: [L,T,R,B] with T > B in Illustrator's y-up space
      if (b[0] < r[2] && b[2] > r[0] && b[3] < r[1] && b[1] > r[3]) hits.push(k + 1);
    }
    return hits.length ? hits.join(",") : "0";
  }
  function abCentre(b) {
    var cx = (b[0] + b[2]) / 2.0, cy = (b[1] + b[3]) / 2.0;
    for (var k = 0; k < abRect.length; k++) {
      var r = abRect[k];
      if (r === null) continue;
      if (cx >= r[0] && cx <= r[2] && cy <= r[1] && cy >= r[3]) return (k + 1);
    }
    return 0;
  }

  var n = 0;
  try { n = doc.pageItems.length; } catch (e) {}
  beat(tag + " items=" + n);

  var kept = 0;
  for (var i = 0; i < n; i++) {
    try {
      var it = doc.pageItems[i];
      var kind = "?";
      try { kind = it.typename; } catch (e1) {}

      var ptype = "";
      try { ptype = it.parent.typename; } catch (e2) {}
      var toplev = (ptype === "Layer") ? "1" : "0";

      // Nested vector scaffolding would swamp the dump; keep it only at top level.
      if (toplev === "0" && (kind === "PathItem" || kind === "CompoundPathItem")) continue;

      var bnds = null;
      try { bnds = it.visibleBounds; } catch (e3) { bnds = null; }
      if (bnds === null) continue;

      var nm = "", linked = "", emb = "";
      try {
        if (kind === "PlacedItem" && it.file) {
          nm = it.file.name.replace(/\.(pdf|png|ai|eps)$/i, "");
          linked = it.file.fsName;
        }
      } catch (e4) {}
      try { if (kind === "RasterItem") { emb = it.embedded ? "embedded" : "linked"; } } catch (e5) {}
      try {
        if (!nm && kind === "RasterItem" && it.file) { nm = it.file.name; linked = it.file.fsName; }
      } catch (e6) {}
      try { if (!nm && kind === "TextFrame") nm = String(it.contents).substr(0, 200).replace(/[\t\r\n]/g, " "); } catch (e7) {}
      try { if (!nm) nm = String(it.name).substr(0, 80); } catch (e8) {}

      var lay = "";
      try { lay = it.layer.name; } catch (e9) {}

      var hid = "";
      try { hid = it.hidden ? "hidden" : ""; } catch (e10) {}

      out.push(kind + "\t" + abCentre(bnds) + "\t" + abList(bnds) + "\t" + toplev + "\t" + emb + hid + "\t" + nm + "\t" +
               bnds[0].toFixed(1) + "\t" + bnds[1].toFixed(1) + "\t" +
               bnds[2].toFixed(1) + "\t" + bnds[3].toFixed(1) + "\t" + lay + "\t" + linked);
      kept++;
    } catch (e) {}
    if (i % 200 === 0) beat(tag + " item " + i + "/" + n);
  }

  doc.close(SaveOptions.DONOTSAVECHANGES);   // read-only: never save her files
  beat(tag + " closed kept=" + kept);

  var f = new File("/Volumes/4 MB/_claude_tmp/geom6_" + tag + ".tsv");
  f.encoding = "UTF-8";
  f.open("w");
  f.writeln("kind\tab_centre\tab_overlap\ttoplevel\tflags\tname\tL\tT\tR\tB\tlayer\tlinked");
  for (var g = 0; g < out.length; g++) f.writeln(out[g]);
  f.close();
  summary.push(tag + ":ab=" + nAb + ",items=" + n + ",kept=" + kept);
  beat(tag + " WROTE rows=" + out.length);
}

app.userInteractionLevel = UserInteractionLevel.DISPLAYALERTS;
beat("ALLDONE " + summary.join(" | "));
summary.join(" | ");
