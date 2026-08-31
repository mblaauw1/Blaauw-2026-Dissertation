// FULL geometry + visibility + z-order dump of META_FIGURES_20260814.ai, for the 30-item §9f audit.
//
// WHY EVERY ITEM KIND, NOT JUST LINKED PlacedItems: on 2026-08-17 a dump that named only linked
// PlacedItems made me tell her three times that a strip "was not on artboard 5" when it was there as an
// EMBEDDED RasterItem on the legend_bullets layer. An embedded raster has no link, so re-rendering the
// figure never updates it -- which is precisely the "an older version is hiding it" case she is asking
// about. So: dump PathItems too, dump hidden items, dump layer visibility, and dump Z-ORDER so a stale
// copy sitting ON TOP of a fresh one is detectable.
#target illustrator

var AIP = "/Volumes/4 MB/1_DECKS/META_FIGURES_20260814.ai";
var OUT = new File("/Volumes/4 MB/_claude_tmp/dump_0814_full.tsv");
var HB  = new File("/Volumes/4 MB/_claude_tmp/dump_0814_full.log");
function beat(m){ try{ HB.open("a"); HB.writeln(m); HB.close(); }catch(e){} }

app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
beat("opening");
var doc = app.open(new File(AIP));
beat("opened: " + doc.pageItems.length + " top-level pageItems, " + doc.layers.length + " layers");

// artboards
var abs = [];
for (var a = 0; a < doc.artboards.length; a++) {
  var r = doc.artboards[a].artboardRect;   // [L,T,R,B]
  abs.push({ i: a, name: doc.artboards[a].name, l: r[0], t: r[1], r: r[2], b: r[3] });
}

OUT.open("w");
OUT.writeln("kind\tname\tlink\tlayer\tlayerVisible\thidden\tzIndex\tleft\ttop\twidth\theight\tartboards\topacity");

function artboardsFor(l, t, w, h) {
  // EVERY artboard the item overlaps, not just the one containing its centre -- a centre test misfiles
  // anything spanning a boundary, which is how two figures ended up reported on the wrong board.
  var hit = [];
  for (var k = 0; k < abs.length; k++) {
    var A = abs[k];
    if (l < A.r && (l + w) > A.l && t > A.b && (t - h) < A.t) hit.push(A.i + 1);
  }
  return hit.length ? hit.join("|") : "-";
}

var z = 0;
function walk(container, layerName, layerVis) {
  for (var i = 0; i < container.pageItems.length; i++) {
    var it = container.pageItems[i];
    var kind = it.typename, nm = "", link = "";
    try { nm = it.name || ""; } catch (e) {}
    if (kind === "PlacedItem") {
      try { link = it.file ? it.file.fsName : "(no file)"; } catch (e) { link = "(unreadable)"; }
    } else if (kind === "RasterItem") {
      var emb = true;
      try { emb = it.embedded; } catch (e) {}
      link = emb ? "(EMBEDDED)" : "(linked raster)";
      try { if (!emb && it.file) link = it.file.fsName; } catch (e) {}
    } else if (kind === "GroupItem") {
      // descend: doc.pageItems does NOT recurse into groups, another way art hides from a dump
      walk(it, layerName, layerVis);
      continue;
    } else if (kind !== "TextFrame") {
      continue;   // paths/compound shapes: skip, they are decoration here
    }
    var b;
    try { b = it.visibleBounds; } catch (e) { continue; }
    var l = b[0], t = b[1], w = b[2] - b[0], h = b[1] - b[3];
    var hid = false, op = 100;
    try { hid = it.hidden; } catch (e) {}
    try { op = it.opacity; } catch (e) {}
    var txt = "";
    if (kind === "TextFrame") { try { txt = it.contents.replace(/[\t\r\n]/g, " ").substr(0, 60); } catch (e) {} }
    OUT.writeln([kind, (kind === "TextFrame" ? txt : nm), link, layerName, layerVis, hid, z++,
                 l.toFixed(1), t.toFixed(1), w.toFixed(1), h.toFixed(1),
                 artboardsFor(l, t, w, h), op.toFixed(0)].join("\t"));
  }
}

for (var L = 0; L < doc.layers.length; L++) {
  var lay = doc.layers[L];
  var vis = true; try { vis = lay.visible; } catch (e) {}
  beat("layer " + L + " '" + lay.name + "' visible=" + vis + " items=" + lay.pageItems.length);
  walk(lay, lay.name, vis);
}
OUT.close();

// artboard table, so the audit can name boards the way she does
var AB = new File("/Volumes/4 MB/_claude_tmp/dump_0814_artboards.tsv");
AB.open("w"); AB.writeln("index\tname\tleft\ttop\tright\tbottom");
for (var q = 0; q < abs.length; q++)
  AB.writeln([abs[q].i + 1, abs[q].name, abs[q].l.toFixed(1), abs[q].t.toFixed(1), abs[q].r.toFixed(1), abs[q].b.toFixed(1)].join("\t"));
AB.close();

doc.close(SaveOptions.DONOTSAVECHANGES);   // READ-ONLY: never touch her file in an audit
app.userInteractionLevel = UserInteractionLevel.DISPLAYALERTS;
beat("DONE rows=" + z);
"rows=" + z;
