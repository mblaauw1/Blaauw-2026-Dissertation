#@ String  imgPath
#@ String  outDir
#@ Double  diameter
#@ Double  quality
#@ Double  linkdist
#@ Double  gapdist
#@ Integer maxgap
#@ Integer minTrackSpots
#@ Double  mergedist
#@ Double  targetspf

/*
 * kt_trackmate.groovy — headless TrackMate kinetochore tracking (TrackMate 8.x).
 *
 * Detects kinetochore-sized puncta (LoG, estimated diameter = `diameter` um,
 * median-filtered, sub-pixel) in a single-channel monitoring stack, links them
 * with the Sparse-LAP tracker, and exports:
 *   <name>.trackmate.xml   full TrackMate session (re-openable in Fiji GUI)
 *   <name>.spots.csv       every spot in a track: track, frame, x/y um, quality, intensity
 *   <name>.tracks.csv      per-track summary: n spots, duration, displacement, speed
 *
 * Real (non-uniform) frame times live in the <name>_timing.csv sidecar from prep;
 * velocities should be computed against that, not the nominal 20 s interval.
 */

import fiji.plugin.trackmate.Model
import fiji.plugin.trackmate.Settings
import fiji.plugin.trackmate.TrackMate
import fiji.plugin.trackmate.Logger
import fiji.plugin.trackmate.Spot
import fiji.plugin.trackmate.detection.LogDetectorFactory
import fiji.plugin.trackmate.tracking.jaqaman.SparseLAPTrackerFactory
import fiji.plugin.trackmate.io.TmXmlWriter
import ij.IJ
import java.io.File

def imp = IJ.openImage(imgPath)
if (imp == null) { System.err.println("CANNOT OPEN " + imgPath); return }
def base = new File(imgPath).getName().replaceAll(/_KTmon\.tif$/, "")

def model = new Model()
model.setLogger(Logger.IJ_LOGGER)

def settings = new Settings(imp)

import fiji.plugin.trackmate.features.FeatureFilter

// ---- Detector: LoG, kinetochore-sized. Detect-all, then adaptively threshold. ----
settings.detectorFactory = new LogDetectorFactory()
settings.detectorSettings = settings.detectorFactory.getDefaultSettings()
settings.detectorSettings['RADIUS']                  = (diameter / 2.0) as Double  // um
settings.detectorSettings['TARGET_CHANNEL']          = 1 as Integer
settings.detectorSettings['THRESHOLD']               = 0.0 as Double  // detect all; threshold applied below
settings.detectorSettings['DO_MEDIAN_FILTERING']     = true
settings.detectorSettings['DO_SUBPIXEL_LOCALIZATION']= true

// ---- Tracker: Sparse LAP with gap closing across acquisition seams ----
settings.trackerFactory  = new SparseLAPTrackerFactory()
settings.trackerSettings = settings.trackerFactory.getDefaultSettings()
settings.trackerSettings['LINKING_MAX_DISTANCE']      = linkdist as Double  // um
settings.trackerSettings['GAP_CLOSING_MAX_DISTANCE']  = gapdist  as Double  // um
settings.trackerSettings['MAX_FRAME_GAP']             = maxgap   as Integer
settings.trackerSettings['ALLOW_TRACK_SPLITTING']     = false
settings.trackerSettings['ALLOW_TRACK_MERGING']       = false

settings.addAllAnalyzers()

def trackmate = new TrackMate(model, settings)
trackmate.setNumThreads(Runtime.runtime.availableProcessors())

// 1) detect everything
if (!trackmate.execDetection()) { System.err.println("detection: " + trackmate.getErrorMessage()); return }

// 2) choose quality threshold: fixed if quality>=0, else adaptive = p99.9 of the
//    detection-quality distribution (the per-movie noise ceiling; KTs are the tail).
//    Validated: 0420 -> ~2.0, 20250901 -> ~3.6. Auto-adapts to each date's brightness.
double thr
if (quality >= 0) {
    thr = quality
    println("${base}: fixed quality threshold = ${thr}")
} else if (targetspf != null && targetspf > 0) {
    // V3 (2026-07-22): PER-FRAME density threshold, not global.
    // The old rule took the top (targetspf * nframes) spots by QUALITY across the WHOLE movie. eYFP-Cdc20
    // bleaches, so late frames are globally dimmer and lost the ranking wholesale — measured recall fell
    // 76% -> 66% from the start to the end of the tracked window, and whole batches scored ~0%. Ranking
    // WITHIN each frame makes the detector insensitive to any drift in overall brightness over time, which
    // is exactly the "same shape and brightness but half of them are missed" symptom.
    // thr stays 0 here (keep everything); the per-frame prune happens after feature computation.
    thr = 0.0
    println("${base}: per-frame density thresholding (top ${targetspf}/frame) applied after feature computation")
} else {
    def qs = []
    for (s in model.getSpots().iterable(false)) { qs.add(s.getFeature('QUALITY') as Double) }
    qs.sort()
    int nq = qs.size()
    thr = nq > 0 ? qs[(int) Math.min(nq - 1, Math.round(0.999 * nq))] : 0.0
    println("${base}: adaptive quality threshold (p99.9) = ${thr.round(3)}  (from ${nq} raw spots)")
}

// 3) apply as the initial spot filter, then compute features + track + filter tracks
settings.initialSpotFilterValue = thr as Double
trackmate.execInitialSpotFiltering()
trackmate.computeSpotFeatures(true)
// ---- PER-FRAME DE-DUPLICATION (user 2026-07-20): a stretched/fractured KT is detected as 2+ spots per frame;
//      those competing spots spawn parallel tracks that gap-closing can't merge (time-overlapping) -> fragmentation.
//      Collapse spots within `mergedist` um per frame, keeping the highest-QUALITY one -> one spot/frame/KT -> one track.
// ---- V3 PER-FRAME QUALITY PRUNE -------------------------------------------------------------
// Keep only the top `targetspf` spots of EACH frame by QUALITY. Independent of how bright the movie is
// at that moment, so photobleaching cannot silently switch the detector off later in the movie.
if (targetspf != null && targetspf > 0 && quality < 0) {
    def _sp = model.getSpots()
    int _cut = 0
    for (Integer ff : new ArrayList(_sp.keySet())) {
        def fs = []
        for (s in _sp.iterable(ff, false)) fs.add(s)
        if (fs.size() <= targetspf) continue
        fs.sort { -(it.getFeature('QUALITY') as Double) }
        for (int k = (int) targetspf; k < fs.size(); k++) { _sp.remove(fs[k], ff); _cut++ }
    }
    _sp.setVisible(true)
    println("${base}: per-frame prune removed ${_cut} low-quality spots (kept top ${targetspf}/frame)")
}

double mdist = (mergedist != null && mergedist > 0) ? mergedist : (diameter as Double)
def _spots = model.getSpots()
int _removed = 0
for (Integer ff : new ArrayList(_spots.keySet())) {
    def fs = []
    for (s in _spots.iterable(ff, true)) fs.add(s)
    fs.sort { -(it.getFeature('QUALITY') as Double) }
    def kept = []
    for (s in fs) {
        double sx = s.getFeature('POSITION_X') as Double
        double sy = s.getFeature('POSITION_Y') as Double
        boolean dup = false
        for (k in kept) {
            double dx = sx - (k.getFeature('POSITION_X') as Double)
            double dy = sy - (k.getFeature('POSITION_Y') as Double)
            if (Math.sqrt(dx*dx + dy*dy) < mdist) { dup = true; break }
        }
        if (dup) { _spots.remove(s, ff); _removed++ } else kept.add(s)
    }
}
_spots.setVisible(true)
println("${base}: merged ${_removed} per-frame duplicate spots (<${mdist}um) to stop track fragmentation")
if (!trackmate.execTracking()) { System.err.println("tracking: " + trackmate.getErrorMessage()); return }
trackmate.computeEdgeFeatures(true)
trackmate.computeTrackFeatures(true)

// ---- Track-length filter: real KTs persist; noise spots form short tracks ----
settings.addTrackFilter(new FeatureFilter('NUMBER_SPOTS', (double) minTrackSpots, true))
trackmate.execTrackFiltering(true)

def tm = model.getTrackModel()
def ids = tm.trackIDs(true)  // visible tracks only (passing the filter)
def nspots = model.getSpots().getNSpots(true)
println("${base}: ${nspots} spots, ${ids.size()} tracks")

// ---- XML (full re-openable session) ----
def xw = new TmXmlWriter(new File(outDir, base + ".trackmate.xml"))
xw.appendModel(model); xw.appendSettings(settings); xw.writeToFile()

// ---- spots.csv ----
def sf = new File(outDir, base + ".spots.csv")
sf.withWriter { w ->
    w.writeLine("track_id,frame,t_sec_nominal,x_um,y_um,radius_um,quality,mean_intensity,total_intensity,snr,contrast")
    for (id in ids) {
        def spots = tm.trackSpots(id).sort { it.getFeature('FRAME') }
        for (s in spots) {
            def g = { k -> def v = s.getFeature(k); v == null ? "" : v }
            w.writeLine([
                id,
                (g('FRAME') as Double) as Integer,
                g('POSITION_T'),
                g('POSITION_X'), g('POSITION_Y'),
                g('RADIUS'), g('QUALITY'),
                g('MEAN_INTENSITY_CH1'), g('TOTAL_INTENSITY_CH1'),
                g('SNR_CH1'), g('CONTRAST_CH1'),
            ].join(","))
        }
    }
}

// ---- tracks.csv (per-track summary) ----
def fm = model.getFeatureModel()
def trf = new File(outDir, base + ".tracks.csv")
trf.withWriter { w ->
    w.writeLine("track_id,n_spots,frame_start,frame_end,duration_frames,total_distance_um,net_displacement_um,mean_speed_um_per_frame,track_displacement_um")
    for (id in ids) {
        def g = { k -> def v = fm.getTrackFeature(id, k); v == null ? "" : v }
        def spots = tm.trackSpots(id).sort { it.getFeature('FRAME') }
        def f0 = spots[0].getFeature('FRAME') as Integer
        def f1 = spots[-1].getFeature('FRAME') as Integer
        w.writeLine([
            id, spots.size(), f0, f1, (f1 - f0),
            g('TOTAL_DISTANCE_TRAVELED'),
            g('TRACK_DISPLACEMENT'),
            g('TRACK_MEAN_SPEED'),
            g('TRACK_DISPLACEMENT'),
        ].join(","))
    }
}
println("  wrote XML + spots.csv + tracks.csv to ${outDir}")
