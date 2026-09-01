// READ-ONLY geometry dump of META_FIGURES_20260814.ai: artboards + every item, tagged with the artboard
// that contains its centre. Written 2026-08-16 for NOTES §9f item [6]; adapted from DUMP_META_GEOM_20260811.jsx.
//
// TRAPS DELIBERATELY AVOIDED (all recorded in NOTES §8/§14):
//   - `path` is RESERVED in ExtendScript (resolves to the app bundle) -> use aiPath.
//   - never name a var `open`, and never `L` when a loop counter exists -> hoisting shadows them.
//   - never read a document property AFTER close() (Error 45) -> capture docName first.
//   - heartbeat every N items so a watchdog can tell "slow" from "hung" instead of waiting out a timeout.
#target illustrator

var aiPath = "/Volumes/4 MB/1_DECKS/META_FIGURES_20260814.ai";
var HB     = new File("/Volumes/4 MB/_claude_tmp/dump0814_verify_heartbeat.txt");

function beat(msg) {
  try { HB.open("a"); HB.writeln(msg); HB.close(); } catch (e) {}
}

// 2026-08-16: the first run sat at ~1.2% CPU with no heartbeat past "open" — the hang signature, not slow
// work. app.open() on this deck raises a MODAL (missing/modified links, fonts, colour profile) and a modal
// blocks the whole script with the app idle. Suppress alerts BEFORE opening, and restore after.
app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
beat("alerts suppressed");
beat("open " + aiPath);
var doc = app.open(new File(aiPath));
var docName = doc.name;                    // capture BEFORE any close
beat("opened " + docName);

var out = [];
var nAb = 0;
try { nAb = doc.artboards.length; } catch (e) {}
beat("artboards=" + nAb);

// ---- artboards first: index, name, rect ----
var abRect = [];
for (var a = 0; a < nAb; a++) {
  var r = null, an = "";
  try { r = doc.artboards[a].artboardRect; } catch (e) {}
  try { an = doc.artboards[a].name; } catch (e) {}
  if (r === null) { abRect.push(null); continue; }
  abRect.push(r);
  // artboardRect = [left, top, right, bottom]
  out.push("ARTBOARD\t" + (a + 1) + "\t" + an + "\t" +
           r[0].toFixed(1) + "\t" + r[1].toFixed(1) + "\t" + r[2].toFixed(1) + "\t" + r[3].toFixed(1) + "\t");
}

function abOf(b) {                          // b = visibleBounds [L,T,R,B]
  var cx = (b[0] + b[2]) / 2.0, cy = (b[1] + b[3]) / 2.0;
  for (var k = 0; k < abRect.length; k++) {
    var r = abRect[k];
    if (r === null) continue;
    if (cx >= r[0] && cx <= r[2] && cy <= r[1] && cy >= r[3]) return (k + 1);
  }
  return 0;                                 // outside every artboard
}

var n = 0;
try { n = doc.pageItems.length; } catch (e) {}
beat("items=" + n);

for (var i = 0; i < n; i++) {
  var kind = "?", nm = "", bnds = null, lay = "", linked = "";
  try {
    var it = doc.pageItems[i];
    try { kind = it.typename; } catch (e1) {}
    try { bnds = it.visibleBounds; } catch (e2) { bnds = null; }
    try {
      if (kind === "PlacedItem" && it.file) {
        nm     = it.file.name.replace(/\.(pdf|png|ai|eps)$/i, "");
        linked = it.file.fsName;
      }
    } catch (e3) {}
    try { if (!nm && kind === "TextFrame") nm = String(it.contents).substr(0, 60).replace(/[\t\r\n]/g, " "); } catch (e4) {}
    try { lay = it.layer.name; } catch (e5) {}
    if (bnds === null) continue;
    out.push(kind + "\t" + abOf(bnds) + "\t" + nm + "\t" +
             bnds[0].toFixed(1) + "\t" + bnds[1].toFixed(1) + "\t" +
             bnds[2].toFixed(1) + "\t" + bnds[3].toFixed(1) + "\t" + lay + "\t" + linked);
  } catch (e) {}
  if (i % 25 === 0) beat("item " + i + "/" + n);
}

doc.close(SaveOptions.DONOTSAVECHANGES);   // read-only: never save her file
app.userInteractionLevel = UserInteractionLevel.DISPLAYALERTS;
beat("closed");

var f = new File("/Volumes/4 MB/_claude_tmp/geom_0814_verify.tsv");
f.encoding = "UTF-8";
f.open("w");
f.writeln("kind\tartboard\tname\tL\tT\tR\tB\tlayer\tlinked");
for (var g = 0; g < out.length; g++) f.writeln(out[g]);
f.close();
beat("DONE rows=" + out.length);
"artboards=" + nAb + " items=" + n;
