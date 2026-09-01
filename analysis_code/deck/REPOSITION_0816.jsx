// Reposition the two candidate sheets onto the artboards she actually named.
// Caught by VERIFY PASS 1 (an independent re-dump of the deck): both had been placed by coordinate and
// their CENTRES fell outside the intended board — `G1_meta_ana_pair_candidates` slipped from artboard 4
// into 7, and `G6kk_zoom_candidates` from 8 into 9. Target boxes come from a largest-free-rectangle scan
// of the verified dump, so neither lands on top of an existing figure.
#target illustrator

var AIP = "/Volumes/4 MB/1_DECKS/META_FIGURES_20260814.ai";
var HB  = new File("/Volumes/4 MB/_claude_tmp/place_heartbeat.txt");
function beat(m){ try{ HB.open("a"); HB.writeln(m); HB.close(); }catch(e){} }

// name -> free box on the intended artboard: [L, T, R, B]
var MOVE = {
  "G1_meta_ana_pair_candidates": [-5700, 1400, -2250,  325],   // artboard 4
  "G6kk_zoom_candidates":        [-2050, -6650, 1300, -7350]   // artboard 8
};

app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
beat("reposition: open");
var doc = app.open(new File(AIP));
var docName = doc.name;
var moved = 0;

for (var i = doc.placedItems.length - 1; i >= 0; i--) {
  var pi = doc.placedItems[i], base = "";
  try { base = pi.file.name.replace(/\.(pdf|png|ai|eps)$/i, ""); } catch (e) { continue; }
  if (!MOVE.hasOwnProperty(base)) continue;
  var bx = MOVE[base];
  var maxW = bx[2] - bx[0], maxH = bx[1] - bx[3];
  var s = Math.min(maxW / pi.width, maxH / pi.height);   // uniform, never distorts
  pi.width  = pi.width  * s;
  pi.height = pi.height * s;
  pi.left = bx[0] + (maxW - pi.width) / 2.0;             // centred in the free box
  pi.top  = bx[1] - (maxH - pi.height) / 2.0;
  moved++;
  beat("moved " + base + " -> " + pi.left.toFixed(0) + "," + pi.top.toFixed(0));
}

doc.save();
doc.close(SaveOptions.SAVECHANGES);
app.userInteractionLevel = UserInteractionLevel.DISPLAYALERTS;
beat("DONE moved=" + moved);
"moved=" + moved;
