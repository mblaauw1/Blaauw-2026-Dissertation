#target illustrator
// Audit every placed figure in `ablation_figures_grouped copy.ai` and report, per placement:
//   * is it ON an artboard (not floating in space)?
//   * does it OVERLAP another placement?
//   * does it have a caption naming its data source (manual / TrackMate / example imaging)?
//   * is it numbered?
//   * is its linked file missing (dead link)?
// Read-only: opens, measures, closes WITHOUT saving.
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}

var COPY = "/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai";
var OUT  = "/Volumes/4 MB/ablation_plots/COPYAI_PLACEMENT_AUDIT.csv";

for (var q = 0; q < app.documents.length; q++) {
  if (app.documents[q].fullName && app.documents[q].fullName.fsName == COPY) {
    throw new Error("ABORT: copy.ai is open — close it first.");
  }
}
var d = app.open(new File(COPY));

// artboard rectangles
var abs = [];
for (var a = 0; a < d.artboards.length; a++) abs.push(d.artboards[a].artboardRect); // [l,t,r,b]
function onArtboard(b) {
  for (var a = 0; a < abs.length; a++) {
    var r = abs[a];
    // require the CENTRE to sit inside an artboard
    var cx = (b[0] + b[2]) / 2, cy = (b[1] + b[3]) / 2;
    if (cx >= r[0] && cx <= r[2] && cy <= r[1] && cy >= r[3]) return a + 1;
  }
  return 0;
}

// gather placements
var items = [];
for (var i = 0; i < d.placedItems.length; i++) {
  var p = d.placedItems[i], f = null, missing = 0;
  try { f = p.file; } catch (e) {}
  var nm = f ? decodeURI(f.name) : "(no link)";
  try { if (f && !f.exists) missing = 1; } catch (e) { missing = 1; }
  var b;
  try { b = p.visibleBounds; } catch (e) { continue; }
  items.push({ nm: nm, b: b, ab: onArtboard(b), missing: missing });
}

// pairwise overlap (area of intersection > 12% of the smaller item)
function inter(a, b) {
  var l = Math.max(a[0], b[0]), r = Math.min(a[2], b[2]);
  var t = Math.min(a[1], b[1]), bo = Math.max(a[3], b[3]);
  if (r <= l || t <= bo) return 0;
  return (r - l) * (t - bo);
}
for (var i = 0; i < items.length; i++) items[i].ov = 0;
for (var i = 0; i < items.length; i++) {
  for (var j = i + 1; j < items.length; j++) {
    var A = items[i].b, B = items[j].b;
    var ia = inter(A, B);
    if (ia <= 0) continue;
    var aa = (A[2] - A[0]) * (A[1] - A[3]), ab2 = (B[2] - B[0]) * (B[1] - B[3]);
    if (ia > 0.12 * Math.min(aa, ab2)) { items[i].ov++; items[j].ov++; }
  }
}

// captions: any text frame whose centre is within 90pt below a placement
var texts = [];
for (var i = 0; i < d.textFrames.length; i++) {
  var t = d.textFrames[i], tb;
  try { tb = t.visibleBounds; } catch (e) { continue; }
  texts.push({ s: String(t.contents), b: tb });
}
function captionFor(b) {
  var best = "";
  for (var i = 0; i < texts.length; i++) {
    var tb = texts[i].b;
    var cx = (tb[0] + tb[2]) / 2;
    if (cx < b[0] - 40 || cx > b[2] + 40) continue;
    if (tb[1] > b[3] + 6 || tb[1] < b[3] - 110) continue;   // just under the figure
    if (String(texts[i].s).length > best.length) best = String(texts[i].s);
  }
  return best;
}

var rows = ["name,artboard,overlaps,missing_link,has_source_label,is_numbered,caption"];
var nOff = 0, nOv = 0, nMiss = 0, nNoSrc = 0, nNoNum = 0;
for (var i = 0; i < items.length; i++) {
  var cap = captionFor(items[i].b);
  var hasSrc = /manual|trackmate|example imaging|\[data:/i.test(cap) ? 1 : 0;
  var isNum  = /(^|[^0-9])(\d{1,3})[\).\s]/.test(cap) || /fig(ure)?\s*\d/i.test(cap) ? 1 : 0;
  if (!items[i].ab) nOff++;
  if (items[i].ov) nOv++;
  if (items[i].missing) nMiss++;
  if (!hasSrc) nNoSrc++;
  if (!isNum) nNoNum++;
  rows.push([items[i].nm, items[i].ab, items[i].ov, items[i].missing, hasSrc, isNum,
             '"' + cap.replace(/"/g, "'").replace(/[\r\n]+/g, " ").substr(0, 120) + '"'].join(","));
}
var f = new File(OUT); f.open("w"); f.write(rows.join("\r\n")); f.close();
d.close(SaveOptions.DONOTSAVECHANGES);
"placements=" + items.length + " off_artboard=" + nOff + " overlapping=" + nOv +
  " dead_links=" + nMiss + " no_source_label=" + nNoSrc + " unnumbered=" + nNoNum +
  " -> " + OUT;
