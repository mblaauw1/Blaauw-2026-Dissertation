#@ String imgPath
#@ Double diameter

/*
 * kt_detect_probe.groovy — detection ONLY (no tracking), to characterize the
 * LoG quality histogram on low-SNR kinetochore data so a sensible detection
 * threshold can be chosen before committing to the (expensive) tracking step.
 *
 * Prints quality percentiles and the spot count at several candidate thresholds.
 */
import fiji.plugin.trackmate.Model
import fiji.plugin.trackmate.Settings
import fiji.plugin.trackmate.TrackMate
import fiji.plugin.trackmate.Logger
import fiji.plugin.trackmate.detection.LogDetectorFactory
import fiji.plugin.trackmate.tracking.jaqaman.SparseLAPTrackerFactory
import ij.IJ

def imp = IJ.openImage(imgPath)
def model = new Model(); model.setLogger(Logger.VOID_LOGGER)
def settings = new Settings(imp)
settings.detectorFactory = new LogDetectorFactory()
settings.detectorSettings = settings.detectorFactory.getDefaultSettings()
settings.detectorSettings['RADIUS']                   = (diameter / 2.0) as Double
settings.detectorSettings['TARGET_CHANNEL']           = 1 as Integer
settings.detectorSettings['THRESHOLD']                = 0.0 as Double
settings.detectorSettings['DO_MEDIAN_FILTERING']      = true
settings.detectorSettings['DO_SUBPIXEL_LOCALIZATION'] = true
// tracker required for checkInput(), but we only run detection below
settings.trackerFactory  = new SparseLAPTrackerFactory()
settings.trackerSettings = settings.trackerFactory.getDefaultSettings()

def tm = new TrackMate(model, settings)
tm.setNumThreads(4)
if (!tm.execDetection()) {
    System.err.println("detection failed: " + tm.getErrorMessage()); return
}
def spots = model.getSpots()
def qs = []
for (s in spots.iterable(false)) { qs.add(s.getFeature('QUALITY') as Double) }
qs.sort()
def n = qs.size()
def pct = { p -> n == 0 ? 0 : qs[(int)Math.min(n - 1, Math.round(p / 100.0 * n))] }
int nframes = imp.getNFrames()
println("PROBE n_spots=${n} over ${nframes} frames (~${(n/(double)nframes).round(1)}/frame)")
println("QUALITY percentiles: p50=${pct(50).round(3)} p90=${pct(90).round(3)} p95=${pct(95).round(3)} p99=${pct(99).round(3)} p99.9=${pct(99.9).round(3)} max=${qs[-1].round(3)}")
// spot count retained at candidate thresholds
[1.0,1.5,2.0,2.5,3.0,4.0,5.0,6.0,8.0].each { thr ->
    int keep = qs.count { it >= thr }
    println("  thr=${thr}: ${keep} spots (~${(keep/(double)nframes).round(1)}/frame)")
}
// Auto threshold (TrackMate's Otsu on the quality histogram) + a robust-stats option.
double auto = fiji.plugin.trackmate.util.TMUtils.otsuThreshold(qs as double[])
double mean = qs.sum() / n
double sd = Math.sqrt(qs.collect { (it - mean) * (it - mean) }.sum() / n)
println("AUTO otsu=${auto.round(3)}  (mean+3sd=${(mean+3*sd).round(3)})")
println("  -> otsu keeps ${qs.count { it >= auto }} spots (~${(qs.count { it >= auto }/(double)nframes).round(1)}/frame)")
