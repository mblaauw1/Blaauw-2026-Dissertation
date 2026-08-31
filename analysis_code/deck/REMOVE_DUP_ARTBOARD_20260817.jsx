// Remove the DUPLICATE artboard from NEW_FIGURES_20260804.ai.
//
// USER 2026-08-17: "ok if two duplicate boards in that one then remove one".
// AB3 and AB4 carry the IDENTICAL rect (0, -3100, 3720, -5920) and the same name "NEW 2026-08-08", which
// is why every figure in that region reported as spanning two boards.
//
// SAFE BECAUSE AN ARTBOARD IS ONLY A VIEW RECTANGLE: removing one deletes NO artwork. The figures in that
// region simply belong to the single remaining board afterwards.
// The HIGHER index is removed so boards 1-3 keep their numbers; 5-8 shift down to 4-7, which is reported.
// Verified first that the two really are identical -- if they are not, this does nothing and says so.
#target illustrator

var AIP = "/Volumes/4 MB/1_DECKS/NEW_FIGURES_20260804.ai";
var TMP = "/Volumes/4 MB/_claude_tmp";
var HB  = new File(TMP + "/dupboard_heartbeat.txt");
function beat(m) { try { HB.open("a"); HB.writeln(m); HB.close(); } catch (e) {} }

app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
beat("START");
var doc = app.open(new File(AIP));
beat("opened " + doc.name);

var out = [];
function rectStr(r) { return r[0].toFixed(1)+","+r[1].toFixed(1)+","+r[2].toFixed(1)+","+r[3].toFixed(1); }

out.push("BEFORE: " + doc.artboards.length + " artboards");
var i;
for (i = 0; i < doc.artboards.length; i++)
  out.push("  AB" + (i+1) + "  " + doc.artboards[i].name + "  [" + rectStr(doc.artboards[i].artboardRect) + "]");

// find the FIRST exact-duplicate pair (same rect), remove the LATER one
var dupIdx = -1, keepIdx = -1;
for (i = 0; i < doc.artboards.length && dupIdx < 0; i++) {
  for (var j = i + 1; j < doc.artboards.length; j++) {
    if (rectStr(doc.artboards[i].artboardRect) === rectStr(doc.artboards[j].artboardRect)) {
      keepIdx = i; dupIdx = j; break;
    }
  }
}

var nitems = 0; try { nitems = doc.pageItems.length; } catch (e) {}
if (dupIdx < 0) {
  out.push("NO DUPLICATE PAIR FOUND -- nothing removed");
  doc.close(SaveOptions.DONOTSAVECHANGES);
} else {
  out.push("duplicate: AB" + (dupIdx+1) + " is identical to AB" + (keepIdx+1) + " -- removing AB" + (dupIdx+1));
  doc.artboards.remove(dupIdx);
  var after = 0; try { after = doc.pageItems.length; } catch (e) {}
  out.push("AFTER : " + doc.artboards.length + " artboards, pageItems " + nitems + " -> " + after +
           (nitems === after ? "  (no artwork touched)" : "  *** ARTWORK CHANGED ***"));
  for (i = 0; i < doc.artboards.length; i++)
    out.push("  AB" + (i+1) + "  " + doc.artboards[i].name + "  [" + rectStr(doc.artboards[i].artboardRect) + "]");
  try { doc.selection = null; } catch (e) {}
  var opts = new IllustratorSaveOptions();
  opts.compatibility = Compatibility.ILLUSTRATOR17;
  opts.pdfCompatible = false;
  doc.saveAs(new File(AIP), opts);
  doc.close(SaveOptions.SAVECHANGES);
  beat("saved");
}

var rf = new File(TMP + "/dupboard_report.txt"); rf.encoding = "UTF-8"; rf.open("w");
for (i = 0; i < out.length; i++) rf.writeln(out[i]);
rf.close();
app.userInteractionLevel = UserInteractionLevel.DISPLAYALERTS;
beat("ALLDONE");
out.join("\n");
