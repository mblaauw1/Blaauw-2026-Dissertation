// META_FIGURES_20260814.ai — 2026-08-16 session placement pass.
// (1) REFRESH every linked figure so the re-rendered PDFs actually appear on her deck,
// (2) SWAP the two artboard-4 figures for their trend-scaled (trimmed-to-anaphase) versions,
// (3) PLACE the new figures she asked for.
// Traps honoured (NOTES §8/§14): no var named `path`/`open`/`L`; document name captured BEFORE close;
// alerts suppressed before open (a modal blocks the whole script with Illustrator idle at ~1% CPU);
// heartbeat per step so a watchdog can tell slow from hung; ONE save at the end.
#target illustrator

var AIP = "/Volumes/4 MB/1_DECKS/META_FIGURES_20260814.ai";
var PDF = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/";
var HB  = new File("/Volumes/4 MB/_claude_tmp/place_heartbeat.txt");
function beat(m){ try{ HB.open("a"); HB.writeln(m); HB.close(); }catch(e){} }

// figures to swap: current linked basename -> replacement basename
var SWAP = {
  "G1_centroid_movement_combined_meta": "G1_centroid_movement_combined_meta_trendscaled",
  "G1_plate_rotation_combined_meta":    "G1_plate_rotation_combined_meta_trendscaled"
};

// new placements: [basename, x_left, y_top, max_width, max_height]
var ADD = [];   // relink only   // relink only   // relink only   // relink only   // final pass: refresh links only, nothing new to place

app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
beat("open");
var doc = app.open(new File(AIP));
var docName = doc.name;
beat("opened " + docName);

// ---- 1 + 2: refresh every link, swapping the two that need a different source ------------------
var n = doc.placedItems.length, refreshed = 0, swapped = 0, failed = 0;
beat("placed=" + n);
for (var i = n - 1; i >= 0; i--) {
  var pi = doc.placedItems[i];
  var base = "";
  try { base = pi.file.name.replace(/\.(pdf|png|ai|eps)$/i, ""); } catch (e) { continue; }
  var want = SWAP.hasOwnProperty(base) ? SWAP[base] : base;
  var f = new File(PDF + want + ".pdf");
  if (!f.exists) { failed++; continue; }
  try {
    pi.relink(f);                       // re-reads from disk; same placement box
    if (want !== base) swapped++; else refreshed++;
  } catch (e) { failed++; }
  if (i % 10 === 0) beat("relink " + i + "/" + n);
}
beat("refreshed=" + refreshed + " swapped=" + swapped + " failed=" + failed);

// ---- 3: place the new figures ------------------------------------------------------------------
var lay;
try { lay = doc.layers.getByName("session_20260816"); }
catch (e) { lay = doc.layers.add(); lay.name = "session_20260816"; }

var added = 0;
for (var j = 0; j < ADD.length; j++) {
  var spec = ADD[j];
  var pf = new File(PDF + spec[0] + ".pdf");
  if (!pf.exists) { beat("MISSING " + spec[0]); continue; }
  try {
    var it = lay.placedItems.add();
    it.file = pf;
    var w = it.width, h = it.height;
    var s = Math.min(spec[3] / w, spec[4] / h);       // uniform scale, never distorts
    it.width = w * s; it.height = h * s;
    it.left = spec[1]; it.top = spec[2];
    added++;
    beat("placed " + spec[0]);
  } catch (e) { beat("FAILED " + spec[0] + " :: " + e); }
}

beat("saving");
doc.save();
doc.close(SaveOptions.SAVECHANGES);
app.userInteractionLevel = UserInteractionLevel.DISPLAYALERTS;
beat("DONE refreshed=" + refreshed + " swapped=" + swapped + " added=" + added + " failed=" + failed);
"refreshed=" + refreshed + " swapped=" + swapped + " added=" + added + " failed=" + failed;
