#target illustrator
// READ-ONLY. Operates on the ALREADY-OPEN document (no open/save), so it cannot damage anything.
// Purpose: find the links Illustrator cannot read — the cause of the frap_candidates.png dialog and,
// most likely, of the saveAs being cancelled.
var d = app.activeDocument;
var broken = [], missing = 0, embedded = 0, total = 0, frap = [];
for (var i = 0; i < d.placedItems.length; i++) {
  var p = d.placedItems[i]; total++;
  var fp = "";
  try { fp = p.file ? p.file.fsName : ""; } catch (e) { embedded++; continue; }
  if (!fp) { embedded++; continue; }
  var f = new File(fp);
  var nm = decodeURI(f.name);
  if (!f.exists) { missing++; broken.push(nm + " -> " + fp); }
  if (nm.toLowerCase().indexOf("frap_candidates") >= 0) {
    frap.push(nm + " | exists=" + f.exists + " | " + fp);
  }
}
var out = "placedItems=" + total + "  embedded/nofile=" + embedded + "  MISSING=" + missing;
out += "\n--- frap_candidates links ---";
for (var k = 0; k < frap.length; k++) out += "\n" + frap[k];
out += "\n--- first missing links ---";
for (var b = 0; b < broken.length && b < 20; b++) out += "\n" + broken[b];
out;
