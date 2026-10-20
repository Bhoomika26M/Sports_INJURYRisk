import React, { useState, useRef } from 'react';
import { Play, Pause, Upload, Sparkles, RefreshCw, AlertTriangle, CheckCircle2, ChevronRight, Activity, Zap } from 'lucide-react';

export default function VideoStudio({
  videos,
  currentVideo,
  setCurrentVideo,
  biomechanics,
  injuryRisk,
  onRunAnalysis,
  onGenerateSample,
  onUploadVideo,
  isAnalyzing
}) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackMode, setPlaybackMode] = useState('processed'); // 'processed' or 'original'
  const [currentTime, setCurrentTime] = useState(0);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [sampleType, setSampleType] = useState('Jump Landing (High Knee Valgus)');
  const [uploadTitle, setUploadTitle] = useState('');
  const [uploadActivity, setUploadActivity] = useState('Landing');
  const [selectedFile, setSelectedFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  
  const videoRef = useRef(null);

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
      setIsPlaying(false);
    } else {
      videoRef.current.play();
      setIsPlaying(true);
    }
  };

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  };

  // Find nearest telemetry frame for current time
  const timeSeries = biomechanics?.time_series_data || [];
  const currentFrameData = timeSeries.length > 0
    ? timeSeries.reduce((prev, curr) => 
        Math.abs(curr.time - currentTime) < Math.abs(prev.time - currentTime) ? curr : prev
      , timeSeries[0])
    : null;

  const isCurrentFrameDetected = currentFrameData ? currentFrameData.detected : true;
  const currentValgusL = currentFrameData?.knee_valgus_l ?? null;
  const currentValgusR = currentFrameData?.knee_valgus_r ?? null;
  const currentTrunkLean = currentFrameData?.trunk_lateral_lean ?? null;
  const currentAsymmetry = currentFrameData?.bilateral_asymmetry ?? null;

  const maxValgusNow = (currentValgusL !== null && currentValgusR !== null)
    ? Math.max(currentValgusL, currentValgusR)
    : (biomechanics?.metrics?.knee_valgus_right_max || 0.0);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      if (!uploadTitle) {
        setUploadTitle(e.target.files[0].name.replace(/\.[^/.]+$/, ""));
      }
    }
  };

  const handleUploadSubmit = async (e) => {
    e.preventDefault();
    if (!selectedFile) return;
    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('title', uploadTitle || 'Uploaded Athlete Movement');
      formData.append('activity_type', uploadActivity);
      formData.append('athlete_id', '1');
      await onUploadVideo(formData);
      setUploadModalOpen(false);
      setSelectedFile(null);
      setUploadTitle('');
    } catch (err) {
      alert(err.message || 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  // Video URL source
  const videoSrc = currentVideo
    ? (playbackMode === 'processed' && currentVideo.processed_video_path
        ? `/api/videos/${currentVideo.id}/processed_stream`
        : `/api/videos/${currentVideo.id}/stream`)
    : '';

  return (
    <div className="space-y-6">
      {/* Top Action Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
        <div>
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <Activity className="w-5 h-5 text-teal-700" />
            Pose Estimation &amp; Video Capture Engine
          </h2>
          <p className="text-xs text-slate-500">
            MediaPipe 33-point markerless skeleton extraction with sub-millisecond dynamic joint angle telemetry.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <div className="flex items-center gap-1.5 bg-slate-50 p-1 rounded-lg border border-slate-200">
            <select
              value={sampleType}
              onChange={(e) => setSampleType(e.target.value)}
              className="bg-white text-xs text-slate-700 px-2 py-1 outline-none border border-slate-200 rounded-md cursor-pointer"
            >
              <option value="Jump Landing (High Knee Valgus)">Drop Jump (Knee Valgus Risk)</option>
              <option value="Cutting Drill (Lateral Inversion)">Side Cut (Ankle / ACL Risk)</option>
              <option value="Deep Squat Mechanics">Deep Squat (Lumbar / Asymmetry)</option>
            </select>
            <button
              onClick={() => onGenerateSample(sampleType)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-teal-700 hover:bg-teal-800 text-white text-xs font-semibold shadow-xs transition-colors"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Generate Sample Motion</span>
            </button>
          </div>

          <button
            onClick={() => setUploadModalOpen(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium border border-slate-300 shadow-xs transition-colors"
          >
            <Upload className="w-3.5 h-3.5 text-teal-700" />
            <span>Upload Video</span>
          </button>
        </div>
      </div>

      {/* Main Video Viewport & Telemetry HUD */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Video Player Column */}
        <div className="lg:col-span-2 space-y-3">
          <div className="relative aspect-video bg-slate-950 rounded-xl overflow-hidden border border-slate-300 shadow-xs flex items-center justify-center group">
            {videoSrc ? (
              <video
                ref={videoRef}
                key={`${currentVideo?.id}-${playbackMode}`}
                src={videoSrc}
                className="w-full h-full object-contain"
                onTimeUpdate={handleTimeUpdate}
                onEnded={() => setIsPlaying(false)}
                playsInline
                loop
              />
            ) : (
              <div className="text-center p-8">
                <Activity className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                <p className="text-sm text-slate-300 font-medium">No video loaded</p>
                <p className="text-xs text-slate-500 mt-1">Select or generate a sample video to begin pose estimation.</p>
              </div>
            )}

            {/* Video Overlay Status Badge */}
            <div className="absolute top-4 left-4 flex items-center gap-2">
              <span className="px-2.5 py-1 rounded text-[11px] font-mono font-semibold bg-slate-900/90 text-slate-200 border border-slate-700 backdrop-blur-md">
                {currentVideo?.activity_type || 'Landing'} Movement
              </span>
              {currentVideo?.status === 'analyzed' && (
                <span className="px-2.5 py-1 rounded text-[11px] font-mono font-semibold bg-emerald-950/90 text-emerald-300 border border-emerald-800/80 backdrop-blur-md flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" /> Pose Tracked
                </span>
              )}
            </div>

            {/* Live Playback Controls Overlay on Bottom */}
            <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-slate-950/90 via-slate-950/60 to-transparent p-4 opacity-90 group-hover:opacity-100 transition-opacity">
              <div className="flex items-center justify-between text-xs text-slate-200">
                <div className="flex items-center gap-3">
                  <button
                    onClick={togglePlay}
                    className="w-8 h-8 rounded-full bg-teal-600 hover:bg-teal-500 text-white flex items-center justify-center font-bold transition-transform active:scale-95 shadow-md"
                  >
                    {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
                  </button>
                  <span className="font-mono text-xs">
                    {currentTime.toFixed(2)}s / {(currentVideo?.duration_seconds || 3.0).toFixed(2)}s
                  </span>
                </div>

                {/* View Mode Switcher */}
                <div className="flex items-center gap-1 bg-slate-900/90 p-1 rounded-lg border border-slate-800">
                  <button
                    onClick={() => setPlaybackMode('processed')}
                    className={`px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
                      playbackMode === 'processed'
                        ? 'bg-teal-700 text-white font-semibold'
                        : 'text-slate-300 hover:text-white'
                    }`}
                  >
                    Skeleton &amp; Angles Overlay
                  </button>
                  <button
                    onClick={() => setPlaybackMode('original')}
                    className={`px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
                      playbackMode === 'original'
                        ? 'bg-teal-700 text-white font-semibold'
                        : 'text-slate-300 hover:text-white'
                    }`}
                  >
                    Original Video
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Analysis Action Strip */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs">
            <div>
              <p className="text-xs font-semibold text-slate-900">{currentVideo?.title || 'No video selected'}</p>
              <p className="text-[11px] text-slate-500">
                Resolution: {currentVideo?.resolution || '1280x720'} | FPS: {currentVideo?.fps || 30} | Duration: {currentVideo?.duration_seconds || 3.0}s
              </p>
            </div>

            <button
              onClick={() => currentVideo && onRunAnalysis(currentVideo.id)}
              disabled={isAnalyzing || !currentVideo}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition-colors shadow-xs ${
                isAnalyzing
                  ? 'bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200'
                  : 'bg-teal-700 hover:bg-teal-800 text-white active:scale-98'
              }`}
            >
              {isAnalyzing ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin text-teal-600" />
                  <span>Processing MediaPipe Keypoints...</span>
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4 text-teal-200" />
                  <span>Run Biomechanical Analysis &amp; Predictions</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Real-time Telemetry HUD Column */}
        <div className="space-y-4">
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">Instantaneous Biomechanics</h3>
              <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                isCurrentFrameDetected
                  ? 'text-teal-800 bg-teal-50 border-teal-200 font-semibold'
                  : 'text-amber-800 bg-amber-50 border-amber-200 font-semibold'
              }`}>
                {isCurrentFrameDetected ? 'Pose Tracked' : 'Occluded Frame'}
              </span>
            </div>

            {/* If frame is occluded, show honest clear message */}
            {!isCurrentFrameDetected ? (
              <div className="p-4 rounded-lg bg-amber-50 border border-amber-200 text-center space-y-1">
                <AlertTriangle className="w-5 h-5 text-amber-700 mx-auto" />
                <p className="text-xs font-semibold text-amber-900">Athlete Momentarily Occluded</p>
                <p className="text-[11px] text-amber-700">No landmarks detected at {currentTime.toFixed(2)}s. Real measurements resume upon re-acquisition.</p>
              </div>
            ) : (
              <>
                {/* Dynamic Knee Valgus Gauge */}
                <div className="space-y-1.5 p-3 rounded-lg bg-slate-50 border border-slate-200">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-slate-700">Dynamic Knee Valgus (L / R)</span>
                    <span className={`text-xs font-bold font-mono ${maxValgusNow > 15 ? 'text-rose-700' : maxValgusNow > 10 ? 'text-amber-700' : 'text-emerald-700'}`}>
                      {currentValgusL !== null ? `${currentValgusL.toFixed(1)}°` : '—'} / {currentValgusR !== null ? `${currentValgusR.toFixed(1)}°` : '—'}
                    </span>
                  </div>
                  <div className="h-2 w-full bg-slate-200 rounded-full overflow-hidden flex">
                    <div
                      className={`h-full transition-all duration-150 ${maxValgusNow > 15 ? 'bg-rose-600' : maxValgusNow > 10 ? 'bg-amber-500' : 'bg-emerald-600'}`}
                      style={{ width: `${Math.min(100, (maxValgusNow / 25) * 100)}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-[10px] text-slate-500 font-mono">
                    <span>0° Normal</span>
                    <span>10° Mild</span>
                    <span className="text-rose-700 font-semibold">&gt;15° ACL Threshold</span>
                  </div>
                </div>

                {/* Lateral Trunk Lean */}
                <div className="space-y-1.5 p-3 rounded-lg bg-slate-50 border border-slate-200">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-slate-700">Lateral Trunk Lean</span>
                    <span className={`text-xs font-bold font-mono ${(currentTrunkLean || 0) > 10 ? 'text-rose-700' : 'text-slate-800'}`}>
                      {currentTrunkLean !== null ? `${currentTrunkLean.toFixed(1)}°` : '—'}
                    </span>
                  </div>
                  <div className="h-1.5 w-full bg-slate-200 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-teal-700 transition-all duration-150"
                      style={{ width: `${Math.min(100, ((currentTrunkLean || 0) / 20) * 100)}%` }}
                    />
                  </div>
                </div>

                {/* Bilateral Asymmetry */}
                <div className="space-y-1.5 p-3 rounded-lg bg-slate-50 border border-slate-200">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-slate-700">Bilateral Asymmetry</span>
                    <span className={`text-xs font-bold font-mono ${(currentAsymmetry || 0) > 15 ? 'text-amber-700' : 'text-slate-800'}`}>
                      {currentAsymmetry !== null ? `${currentAsymmetry.toFixed(1)}%` : '—'}
                    </span>
                  </div>
                  <div className="h-1.5 w-full bg-slate-200 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-slate-700 transition-all duration-150"
                      style={{ width: `${Math.min(100, ((currentAsymmetry || 0) / 30) * 100)}%` }}
                    />
                  </div>
                </div>
              </>
            )}

            {/* Real-time Status Card */}
            <div className={`p-3 rounded-lg border ${
              maxValgusNow > 15
                ? 'bg-rose-50 border-rose-200 text-rose-900'
                : maxValgusNow > 10
                ? 'bg-amber-50 border-amber-200 text-amber-900'
                : 'bg-emerald-50 border-emerald-200 text-emerald-900'
            }`}>
              <div className="flex items-start gap-2">
                {maxValgusNow > 15 ? (
                  <AlertTriangle className="w-4 h-4 text-rose-700 shrink-0 mt-0.5" />
                ) : (
                  <CheckCircle2 className="w-4 h-4 text-emerald-700 shrink-0 mt-0.5" />
                )}
                <div>
                  <p className="text-xs font-bold">
                    {maxValgusNow > 15
                      ? 'Severe Medial Knee Collapse'
                      : maxValgusNow > 10
                      ? 'Moderate Knee Valgus Strain'
                      : 'Safe Biomechanical Alignment'}
                  </p>
                  <p className="text-[11px] opacity-90 mt-0.5">
                    {maxValgusNow > 15
                      ? 'Abduction torque on knee joint exceeds safe threshold. Immediate ACL intervention suggested.'
                      : 'Joint vectors within nominal sports biomechanical physiological corridor.'}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Video Library Switcher Card */}
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">Recorded Athlete Sessions</h3>
            <div className="space-y-2 max-h-52 overflow-y-auto pr-1">
              {videos.map((vid) => (
                <div
                  key={vid.id}
                  onClick={() => setCurrentVideo(vid)}
                  className={`p-2.5 rounded-lg border text-xs cursor-pointer transition-colors flex items-center justify-between ${
                    currentVideo?.id === vid.id
                      ? 'bg-teal-50 border-teal-300 text-slate-900 font-semibold'
                      : 'bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100 hover:border-slate-300'
                  }`}
                >
                  <div className="truncate pr-2">
                    <p className="truncate">{vid.title}</p>
                    <p className="text-[10px] text-slate-500 font-normal">{vid.activity_type} • {vid.duration_seconds}s</p>
                  </div>
                  <ChevronRight className="w-4 h-4 shrink-0 text-slate-400" />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Upload Modal */}
      {uploadModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
          <div className="bg-white border border-slate-200 rounded-xl max-w-md w-full p-6 space-y-4 shadow-xl">
            <div className="flex justify-between items-center pb-2 border-b border-slate-100">
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Upload className="w-4 h-4 text-teal-700" /> Upload Athlete Movement Video
              </h3>
              <button
                onClick={() => setUploadModalOpen(false)}
                className="text-slate-400 hover:text-slate-700 text-sm font-semibold p-1"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleUploadSubmit} className="space-y-3">
              <div>
                <label className="text-xs font-medium text-slate-700 block mb-1">Session Title</label>
                <input
                  type="text"
                  placeholder="e.g. Marcus Vance - Jump Landing Assessment"
                  value={uploadTitle}
                  onChange={(e) => setUploadTitle(e.target.value)}
                  className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-900 outline-none focus:border-teal-600 focus:ring-1 focus:ring-teal-600"
                  required
                />
              </div>

              <div>
                <label className="text-xs font-medium text-slate-700 block mb-1">Sport Movement Activity</label>
                <select
                  value={uploadActivity}
                  onChange={(e) => setUploadActivity(e.target.value)}
                  className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-900 outline-none focus:border-teal-600 focus:ring-1 focus:ring-teal-600"
                >
                  <option value="Landing">Landing / Drop Jump</option>
                  <option value="Squatting">Squatting Mechanics</option>
                  <option value="Running">Running / Treadmill</option>
                  <option value="Sprinting">High-Speed Sprinting</option>
                  <option value="Cutting Movements">Side Cutting &amp; Agility</option>
                  <option value="Throwing">Overhead Throwing</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-medium text-slate-700 block mb-1">Select Video File (.mp4, .mov, .webm)</label>
                <input
                  type="file"
                  accept="video/*"
                  onChange={handleFileChange}
                  className="w-full text-xs text-slate-600 file:mr-3 file:py-1.5 file:px-3 file:rounded-md file:border file:border-slate-300 file:text-xs file:font-medium file:bg-slate-50 file:text-slate-700 hover:file:bg-slate-100 cursor-pointer"
                  required
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setUploadModalOpen(false)}
                  className="px-3.5 py-1.5 rounded-lg text-xs font-medium text-slate-600 hover:bg-slate-100 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isUploading || !selectedFile}
                  className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-teal-700 hover:bg-teal-800 text-white transition-colors disabled:opacity-50"
                >
                  {isUploading ? 'Uploading & Processing...' : 'Upload Video'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
