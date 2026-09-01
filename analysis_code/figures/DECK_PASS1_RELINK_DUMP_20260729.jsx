// DECK PASS 1 of 2 (2026-07-29c) - one consolidated run, per the one-JSX-per-turn rule.
//
//   1. UPDATE LINKS on both decks. 296 of the 565 placed figures had their linked PDF re-rendered after
//      the decks were last saved at 15:02 (the 37-builder cohort rebuild, the lagging-shape and DC fixes,
//      the refreshed zoom/window companions). Nothing else in this pass changes artwork.
//   2. DUMP GEOMETRY: {figure: "AB##"} as before, PLUS each placement's visibleBounds. place_zooms.json
//      is the one JSX input with no generator precisely because "is this companion already beside its
//      parent" needs bounding boxes, which the old artboards dump did not record.
//   3. SAVE both decks (pdfCompatible=false - true bloats copy.ai to ~588 MB).
//
// Pass 2 applies titles / yellow / grey / marks / hygiene / companion placement.
// Every document value is read BEFORE d.close() - reading after raises Error 45.
// No variable is named `open` and no loop counter shadows a function (Error 24).
#target illustrator
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}
while (app.documents.length > 0) { app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }

var DOCS = ["/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai",
            "/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_kinetochore_overflow.ai"];
var TAG  = ["AB", "OV-AB"];
var report = [];
var abPairs = [];      // "name":"AB##"
var geoPairs = [];     // "name":[l,t,r,b,"AB##"]

function baseOf(it) {
  var f = null;
  try { f = it.file; } catch (e) {}
  if (!f) return "";
  var n = decodeURI(f.name);
  return n.replace(/\.(pdf|png|PDF|PNG)$/, "");
}

for (var k = 0; k < DOCS.length; k++) {
  var d = app.open(new File(DOCS[k]));
  var nUpd = 0, nFail = 0, nSeen = 0;

  // ---- 1. update every link ----
  for (var i = 0; i < d.placedItems.length; i++) {
    nSeen++;
    try { d.placedItems[i].update(); nUpd++; } catch (eU) { nFail++; }
  }

  // ---- 2. artboard + bounding box for every placement ----
  function abIndexOf(bnds) {
    var cxx = (bnds[0] + bnds[2]) / 2, cyy = (bnds[1] + bnds[3]) / 2;
    for (var a = 0; a < d.artboards.length; a++) {
      var r = d.artboards[a].artboardRect;      // [l, t, r, b]
      if (cxx >= r[0] && cxx <= r[2] && cyy <= r[1] && cyy >= r[3]) return a;
    }
    return -1;
  }
  for (var j = 0; j < d.placedItems.length; j++) {
    var it = d.placedItems[j];
    var nm = baseOf(it);
    if (!nm) continue;
    var b;
    try { b = it.visibleBounds; } catch (eB) { continue; }
    var ai = abIndexOf(b);
    var lbl = (ai < 0) ? "NONE" : (TAG[k] + (ai + 1));
    abPairs.push('"' + nm + '":"' + lbl + '"');
    geoPairs.push('"' + nm + '":[' + Math.round(b[0]) + ',' + Math.round(b[1]) + ',' +
                  Math.round(b[2]) + ',' + Math.round(b[3]) + ',"' + lbl + '"]');
  }

  // ---- 3. save (capture everything we need BEFORE closing) ----
  var docName = d.name, nAb = d.artboards.length, nPl = d.placedItems.length;
  var opts = new IllustratorSaveOptions();
  opts.pdfCompatible = false;
  var saved = "yes";
  try { d.saveAs(new File(DOCS[k]), opts); } catch (eS) { saved = "FAILED: " + eS; }
  try { d.close(SaveOptions.DONOTSAVECHANGES); } catch (eC) {}
  report.push(docName + " :: placements=" + nPl + " artboards=" + nAb +
              " linksUpdated=" + nUpd + " linkFailed=" + nFail + " saved=" + saved);
}

function dump(path, body) {
  var f = new File(path);
  f.encoding = "UTF-8";
  f.open("w");
  f.write(body);
  f.close();
}
dump("/Volumes/4 MB/_working/_deck_jsx_inputs/artboards.json", "{" + abPairs.join(",\n") + "}");
dump("/Volumes/4 MB/_working/_deck_jsx_inputs/geometry.json",  "{" + geoPairs.join(",\n") + "}");
report.push("artboards.json " + abPairs.length + " entries · geometry.json " + geoPairs.length + " entries");
report.join("\n");
