#target illustrator
// Work out what the empty picture frames and the orphaned captions on copy.ai were FOR.
//   A. every placedItem with no resolvable file -> its exact bounds + the nearest text on the page
//   B. every caption-looking text frame -> the nearest placed item and how far away it is
//      (a caption 600pt from any art is genuinely orphaned; one 40pt away just failed my first
//       proximity test and is fine)
// Then the same geometry is looked up in a BACKUP .ai, where the link may still be intact.
// Read-only on both files.
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}

var CUR = "/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
var BAK = "/Volumes/4 MB/ablation_plots/ablation_figures_grouped copy_pre_rtfplots_20260722.ai";
var OUT = "/Volumes/4 MB/ablation_plots/COPYAI_EMPTY_DIAGNOSIS.txt";
var L = [];

function centre(b) { return [(b[0] + b[2]) / 2, (b[1] + b[3]) / 2]; }
function dist(a, b) { var dx = a[0] - b[0], dy = a[1] - b[1]; return Math.sqrt(dx * dx + dy * dy); }

function scan(path, tag, emptyBounds) {
  var d = app.open(new File(path));
  var placed = [], texts = [], empties = [];
  for (var i = 0; i < d.placedItems.length; i++) {
    var p = d.placedItems[i], f = null, b;
    try { b = p.visibleBounds; } catch (e) { continue; }
    try { f = p.file; } catch (e) {}
    if (f) placed.push({ nm: decodeURI(f.name), b: b, c: centre(b) });
    else empties.push({ b: b, c: centre(b) });
  }
  for (var i = 0; i < d.textFrames.length; i++) {
    var t = d.textFrames[i], tb;
    try { tb = t.visibleBounds; } catch (e) { continue; }
    var s = String(t.contents).replace(/[\r\n]+/g, " ");
    if (s.length > 3) texts.push({ s: s, b: tb, c: centre(tb) });
  }

  L.push("=== " + tag + " : " + placed.length + " linked, " + empties.length + " empty, " + texts.length + " texts");

  if (emptyBounds === null) {
    // FIRST PASS (current file): describe each empty frame + nearest text, and report its geometry
    L.push("");
    L.push("A. EMPTY PICTURE FRAMES (no file associated)");
    for (var i = 0; i < empties.length; i++) {
      var e = empties[i], best = null, bd = 1e9;
      for (var j = 0; j < texts.length; j++) {
        var dd = dist(e.c, texts[j].c);
        if (dd < bd) { bd = dd; best = texts[j]; }
      }
      L.push("  #" + (i + 1) + " bounds [" + Math.round(e.b[0]) + "," + Math.round(e.b[1]) + "," +
             Math.round(e.b[2]) + "," + Math.round(e.b[3]) + "]" +
             "  size " + Math.round(e.b[2] - e.b[0]) + "x" + Math.round(e.b[1] - e.b[3]) +
             "  | nearest text (" + Math.round(bd) + "pt): \"" +
             (best ? best.s.substr(0, 70) : "none") + "\"");
    }
    L.push("");
    L.push("B. CAPTION-LOOKING TEXT -> NEAREST ARTWORK");
    for (var j = 0; j < texts.length; j++) {
      var s = texts[j].s;
      if (!/^(G\d|N\d|DEMO|collagen|frap|polar|ablation|metaDur|firsthalf|ALLcohorts)/i.test(s)) continue;
      var best = null, bd = 1e9;
      for (var i = 0; i < placed.length; i++) {
        var dd = dist(texts[j].c, placed[i].c);
        if (dd < bd) { bd = dd; best = placed[i]; }
      }
      if (bd > 260) {   // only report the genuinely far ones
        L.push("  \"" + s.substr(0, 58) + "\"  -> nearest art " +
               Math.round(bd) + "pt away: " + (best ? best.nm : "none"));
      }
    }
  } else {
    // SECOND PASS (backup): what was linked at the empty frames' coordinates?
    L.push("");
    L.push("C. WHAT OCCUPIED THOSE COORDINATES IN THE BACKUP");
    for (var k = 0; k < emptyBounds.length; k++) {
      var target = emptyBounds[k], best = null, bd = 1e9;
      for (var i = 0; i < placed.length; i++) {
        var dd = dist(target, placed[i].c);
        if (dd < bd) { bd = dd; best = placed[i]; }
      }
      L.push("  frame #" + (k + 1) + " at [" + Math.round(target[0]) + "," + Math.round(target[1]) + "]" +
             " -> nearest linked art " + Math.round(bd) + "pt away: " + (best ? best.nm : "none"));
    }
  }
  var out = [];
  for (var i = 0; i < empties.length; i++) out.push(empties[i].c);
  d.close(SaveOptions.DONOTSAVECHANGES);
  return out;
}

var emptyCentres = scan(CUR, "CURRENT copy.ai", null);
if (new File(BAK).exists) scan(BAK, "BACKUP pre_rtfplots", emptyCentres);
else L.push("backup not found: " + BAK);

var f = new File(OUT); f.open("w"); f.write(L.join("\r\n")); f.close();
"wrote " + OUT;
