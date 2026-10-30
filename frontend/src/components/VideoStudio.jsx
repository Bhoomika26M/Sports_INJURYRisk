import React, { useState, useRef, useEffect } from 'react';
import { Play, Pause, Upload, Sparkles, RefreshCw, AlertTriangle, CheckCircle2, ChevronRight, Activity, Zap, Film, FolderOpen } from 'lucide-react';
import { api } from '../api/client';

export default function VideoStudio({
  videos,
  currentVideo,
  setCurrentVideo,
  biomechanics,
  injuryRisk,
  onRunAnalysis,
  onGenerateSample,
  onLoadDemoSample,
  onUploadVideo,
  isAnalyzing
}) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackMode, setPlaybackMode] = useState('original'); // 'processed' or 'original'
  const hasProcessedVideo = Boolean(currentVideo?.processed_video_path);

  useEffect(() => {
    setPlaybackMode(currentVideo?.processed_video_path ? 'processed' : 'original');
  }, [currentVideo?.id, currentVideo?.processed_video_path]);
  const [currentTime, setCurrentTime] = useState(0);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [sampleType, setSampleType] = useState('Drop Jump');
  const [uploadTitle, setUploadTitle] = useState('');
  const [uploadActivity, setUploadActivity] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStage, setUploadStage] = useState('Uploading video...');
  
  const [availableSamples, setAvailableSamples] = useState([]);
  const [selectedDemoSample, setSelectedDemoSample] = useState('');
  const [videoPlayError, setVideoPlayError] = useState('');

  useEffect(() => {
    let active = true;
    api.getDemoSamples().then((samples) => {
      if (active && Array.isArray(samples)) {
        setAvailableSamples(samples);
        if (samples.length > 0) {
          setSelectedDemoSample(samples[0].filename);
        }
      }
    }).catch(() => {});
    return () => { active = false; };
  }, []);

  useEffect(() => {
    setVideoPlayError('');
  }, [currentVideo?.id, playbackMode]);

  const handleLoadSampleClick = () => {
    if (!selectedDemoSample) return;
    const item = availableSamples.find(s => s.filename === selectedDemoSample);
    onLoadDemoSample?.(
      selectedDemoSample,
      item?.suggested_activity || 'Drop Jump',
      item?.title || selectedDemoSample
    );
  };

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
  const detectedFrameCount = timeSeries.filter((frame) => frame?.detected).length;
  const detectionCoverage = timeSeries.length ? detectedFrameCount / timeSeries.length : 0;
  const hasAnalysis = currentVideo?.status === 'analyzed' && timeSeries.length > 0;
  const currentFrameData = hasAnalysis
    ? timeSeries.reduce((prev, curr) => 
        Math.abs(curr.time - currentTime) < Math.abs(prev.time - currentTime) ? curr : prev
      , timeSeries[0])
    : null;

  const isCurrentFrameDetected = Boolean(currentFrameData?.detected);
  const currentValgusL = currentFrameData?.knee_valgus_l ?? null;
  const currentValgusR = currentFrameData?.knee_valgus_r ?? null;
  const currentTrunkLean = currentFrameData?.trunk_lateral_lean ?? null;
  const currentAsymmetry = currentFrameData?.bilateral_asymmetry ?? null;

  const maxValgusNow = (currentValgusL !== null && currentValgusR !== null)
    ? Math.max(currentValgusL, currentValgusR)
    : currentValgusL ?? currentValgusR ?? null;

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
      setUploadProgress(0);
      setUploadStage('Uploading video...');
      await onUploadVideo(formData, setUploadProgress, () => setUploadStage('Processing pose tracking...'));
      setUploadModalOpen(false);
      setSelectedFile(null);
      setUploadTitle('');
    } catch (err) {
      alert(err.message || 'Upload failed');
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
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
            Frame-by-frame 2D pose estimates and joint-angle measurements from uploaded clips.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Demo Samples Selector (Local backend/samples/) */}
          <div className="flex flex-wrap items-center gap-1.5 bg-slate-50 p-1.5 rounded-lg border border-slate-200">
            <span className="text-[11px] font-semibold text-slate-700 flex items-center gap-1 px-1">
              <FolderOpen className="w-3.5 h-3.5 text-teal-700" />
              Demo samples:
            </span>
            <select
              value={selectedDemoSample}
              onChange={(e) => setSelectedDemoSample(e.target.value)}
              className="bg-white text-xs text-slate-700 px-2 py-1 outline-none border border-slate-200 rounded-md cursor-pointer max-w-[220px] truncate"
              title="Select a video file from backend/samples/"
            >
              {availableSamples.length > 0 ? (
                availableSamples.map((s) => (
                  <option key={s.filename} value={s.filename}>
                    [{s.is_synthetic !== false ? 'Synthetic' : 'Recorded'}] {s.suggested_activity || 'Movement'} — {s.title} ({s.file_size_formatted})
                  </option>
                ))
              ) : (
                <option value="">No clips in backend/samples/</option>
              )}
            </select>
            <button
              onClick={handleLoadSampleClick}
              disabled={!selectedDemoSample || isAnalyzing}
              className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-teal-700 hover:bg-teal-800 text-white text-xs font-semibold shadow-xs transition-colors disabled:opacity-50"
              title="Load selected file from backend/samples/"
            >
              <Film className="w-3 h-3" />
              <span>Load Sample</span>
            </button>
            <span className="text-[10px] text-slate-400 border-l border-slate-300 pl-1.5 hidden md:inline">
              Folder: backend/samples/
            </span>
          </div>

          {/* Synthetic Movement Generator */}
          <div className="flex items-center gap-1.5 bg-slate-50 p-1.5 rounded-lg border border-slate-200">
            <select
              value={sampleType}
              onChange={(e) => setSampleType(e.target.value)}
              className="bg-white text-xs text-slate-700 px-2 py-1 outline-none border border-slate-200 rounded-md cursor-pointer"
            >
              <option value="Drop Jump">Synthetic Drop Jump</option>
              <option value="Side Cut">Synthetic Side Cut</option>
              <option value="Deep Squat">Synthetic Deep Squat</option>
              <option value="Running">Synthetic Running</option>
              <option value="Sprinting">Synthetic Sprinting</option>
              <option value="Throwing">Synthetic Throwing</option>
            </select>
            <button
              onClick={() => onGenerateSample(sampleType)}
              disabled={isAnalyzing}
              className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-slate-800 hover:bg-slate-900 text-white text-xs font-semibold shadow-xs transition-colors disabled:opacity-50"
              title="Generate new synthetic movement video"
            >
              <Sparkles className="w-3 h-3 text-teal-300" />
              <span>Generate Clip</span>
            </button>
          </div>

          <button
            onClick={() => setUploadModalOpen(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-teal-700 hover:bg-teal-800 text-white text-xs font-semibold shadow-xs transition-colors"
          >
            <Upload className="w-3.5 h-3.5" />
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
                controls
                onPlay={() => setIsPlaying(true)}
                onPause={() => setIsPlaying(false)}
                onError={() => setVideoPlayError('Unable to load video stream. Please ensure the file is an H.264 MP4 video.')}
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
                {currentVideo?.activity_type ? currentVideo.activity_type + ' movement' : 'No movement selected'}
              </span>
              {currentVideo?.status === 'analyzed' && (
                <span className={`px-2.5 py-1 rounded text-[11px] font-mono font-semibold border backdrop-blur-md flex items-center gap-1 ${detectionCoverage < 0.5 ? 'bg-amber-950/90 text-amber-200 border-amber-800/80' : 'bg-emerald-950/90 text-emerald-300 border-emerald-800/80'}`}>
                  {detectionCoverage < 0.5 ? <AlertTriangle className="w-3 h-3" /> : <CheckCircle2 className="w-3 h-3" />}
                  Pose coverage {Math.round(detectionCoverage * 100)}%
                </span>
              )}
            </div>

            {/* Live Playback Controls Overlay on Bottom */}
            <div className="pointer-events-none absolute bottom-0 inset-x-0 bg-gradient-to-t from-slate-950/90 via-slate-950/60 to-transparent p-4 opacity-90 group-hover:opacity-100 transition-opacity">
              <div className="flex items-center justify-between text-xs text-slate-200">
                <div className="flex items-center gap-3">
                  <button
                    onClick={togglePlay}
                    className="pointer-events-auto w-8 h-8 rounded-full bg-teal-600 hover:bg-teal-500 text-white flex items-center justify-center font-bold transition-transform active:scale-95 shadow-md"
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
                    disabled={!hasProcessedVideo}
                                        className={`pointer-events-auto px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
                      playbackMode === 'processed'
                        ? 'bg-teal-700 text-white font-semibold'
                        : 'text-slate-300 hover:text-white'
                    }`}
                  >
                    {hasProcessedVideo ? 'Skeleton & Angles Overlay' : 'Skeleton overlay (analyze first)'}
                  </button>
                  <button
                    onClick={() => setPlaybackMode('original')}
                    className={`pointer-events-auto px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
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

          {videoPlayError && (
            <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-700 shrink-0" />
              <span>{videoPlayError}</span>
            </div>
          )}
          {currentVideo?.status === 'analyzed' && timeSeries.length > 0 && detectionCoverage < 0.5 && (
            <div role="status" className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              Pose was detected in {detectedFrameCount} of {timeSeries.length} sampled frames ({Math.round(detectionCoverage * 100)}%). Treat these measurements cautiously; use a stationary camera, good lighting, and keep the athlete fully in frame.
            </div>
          )}

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
                  <span>Run Pose and Movement Analysis</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Playback-time telemetry column */}
        <div className="space-y-4">
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">Current-frame measurements</h3>
              <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                isAnalyzing
                  ? 'text-teal-800 bg-teal-50 border-teal-200 font-semibold animate-pulse'
                  : !hasAnalysis
                  ? 'text-slate-700 bg-slate-100 border-slate-200 font-semibold'
                  : isCurrentFrameDetected
                  ? 'text-teal-800 bg-teal-50 border-teal-200 font-semibold'
                  : 'text-amber-800 bg-amber-50 border-amber-200 font-semibold'
              }`}>
                {isAnalyzing ? 'Analyzing pose...' : !hasAnalysis ? (currentVideo?.status === 'failed' ? 'Analysis failed' : 'Analysis pending') : isCurrentFrameDetected ? 'Pose tracked' : 'Occluded frame'}
              </span>
            </div>

            {!hasAnalysis ? (
              <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 text-center space-y-1">
                <p className="text-xs font-semibold text-slate-800">No measurements yet</p>
                <p className="text-[11px] text-slate-600">Run pose analysis to show measurements from detected frames.</p>
              </div>
            ) : !isCurrentFrameDetected || maxValgusNow === null ? (
              <div className="p-4 rounded-lg bg-amber-50 border border-amber-200 text-center space-y-1">
                <AlertTriangle className="w-5 h-5 text-amber-700 mx-auto" />
                <p className="text-xs font-semibold text-amber-900">No pose measurement for this frame</p>
                <p className="text-[11px] text-amber-700">No usable landmarks were detected at {currentTime.toFixed(2)}s.</p>
              </div>
            ) : (
              <>
                <div className="space-y-1.5 p-3 rounded-lg bg-slate-50 border border-slate-200">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-slate-700">Knee valgus estimate (L / R)</span>
                    <span className="text-xs font-bold font-mono text-slate-900">
                      {currentValgusL !== null ? `${currentValgusL.toFixed(1)}°` : '—'} / {currentValgusR !== null ? `${currentValgusR.toFixed(1)}°` : '—'}
                    </span>
                  </div>
                  <div className="h-2 w-full bg-slate-200 rounded-full overflow-hidden flex">
                    <div className={`h-full transition-all duration-150 ${maxValgusNow > 15 ? 'bg-rose-600' : maxValgusNow > 10 ? 'bg-amber-500' : 'bg-emerald-600'}`} style={{ width: `${Math.min(100, (maxValgusNow / 25) * 100)}%` }} />
                  </div>
                  <div className="flex justify-between text-[10px] text-slate-500 font-mono"><span>0°</span><span>10°</span><span>&gt;15° demo flag</span></div>
                </div>
                <div className="space-y-1.5 p-3 rounded-lg bg-slate-50 border border-slate-200">
                  <div className="flex items-center justify-between"><span className="text-xs font-medium text-slate-700">Lateral trunk lean</span><span className="text-xs font-bold font-mono text-slate-800">{currentTrunkLean !== null ? `${currentTrunkLean.toFixed(1)}°` : '—'}</span></div>
                  <div className="h-1.5 w-full bg-slate-200 rounded-full overflow-hidden"><div className="h-full bg-teal-700 transition-all duration-150" style={{ width: `${Math.min(100, ((currentTrunkLean || 0) / 20) * 100)}%` }} /></div>
                </div>
                <div className="space-y-1.5 p-3 rounded-lg bg-slate-50 border border-slate-200">
                  <div className="flex items-center justify-between"><span className="text-xs font-medium text-slate-700">Bilateral asymmetry</span><span className="text-xs font-bold font-mono text-slate-800">{currentAsymmetry !== null ? `${currentAsymmetry.toFixed(1)}%` : '—'}</span></div>
                  <div className="h-1.5 w-full bg-slate-200 rounded-full overflow-hidden"><div className="h-full bg-slate-700 transition-all duration-150" style={{ width: `${Math.min(100, ((currentAsymmetry || 0) / 30) * 100)}%` }} /></div>
                </div>
                {maxValgusNow !== null && (
                  <div className={`p-3 rounded-lg border ${maxValgusNow > 15 ? 'bg-rose-50 border-rose-200 text-rose-900' : maxValgusNow > 10 ? 'bg-amber-50 border-amber-200 text-amber-900' : 'bg-emerald-50 border-emerald-200 text-emerald-900'}`}>
                    <p className="text-xs font-bold">{maxValgusNow > 15 ? 'High knee-valgus measure' : maxValgusNow > 10 ? 'Elevated knee-valgus measure' : 'Within current demo threshold'}</p>
                    <p className="text-[11px] opacity-90 mt-0.5">Approximate 2D pose estimate and rule-based flag; this is not a diagnosis or clinical clearance.</p>
                  </div>
                )}
              </>
            )}
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
                  required
                  value={uploadActivity}
                  onChange={(e) => setUploadActivity(e.target.value)}
                  className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-900 outline-none focus:border-teal-600 focus:ring-1 focus:ring-teal-600"
                >
                  <option value="">Choose a movement</option>
                  <option value="Drop Jump">Drop jump / landing</option>
                  <option value="Side Cut">Side cut / change of direction</option>
                  <option value="Deep Squat">Deep squat</option>
                  <option value="Running">Running</option>
                  <option value="Sprinting">Sprinting</option>
                  <option value="Throwing">Throwing</option>
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
                  disabled={isUploading || !selectedFile || !uploadActivity || !uploadTitle.trim()}
                  className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-teal-700 hover:bg-teal-800 text-white transition-colors disabled:opacity-50"
                >
                  {isUploading ? (uploadStage === 'Uploading video...' ? `Uploading video (${uploadProgress}%)` : uploadStage) : 'Upload Video'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
