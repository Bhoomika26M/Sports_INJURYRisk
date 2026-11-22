import React, { useEffect, useMemo, useRef, useState } from 'react';
import { ArrowLeftRight, Activity, AlertCircle, Pause, Play, Upload, X, CheckCircle, Loader2 } from 'lucide-react';
import { api } from '../api/client';

const metricRows = [
  ['Knee valgus left (max)', 'knee_valgus_left_max', '°'],
  ['Knee valgus right (max)', 'knee_valgus_right_max', '°'],
  ['Lateral trunk lean (max)', 'trunk_lean_lateral_max', '°'],
  ['Movement symmetry', 'movement_symmetry_score', '/100'],
  ['Range of motion', 'range_of_motion_score', '/100'],
];

function displayValue(value, suffix = '', coverage = 100) {
  if (coverage === 0) return 'Insufficient pose data';
  return value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value))
    ? `${Number(value).toFixed(1)}${suffix}`
    : 'Not analyzed';
}

function formatTime(seconds) {
  if (!Number.isFinite(seconds)) return '0:00';
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`;
}

export default function VideoComparisonView({ videos = [], onVideosUpdated }) {
  const [internalVideos, setInternalVideos] = useState(videos);

  useEffect(() => {
    setInternalVideos(videos);
  }, [videos]);

  const analyzed = useMemo(
    () => internalVideos.filter((video) => video.status === 'analyzed' && video.processed_video_path),
    [internalVideos]
  );

  const [leftId, setLeftId] = useState('');
  const [rightId, setRightId] = useState('');
  const [leftData, setLeftData] = useState(null);
  const [rightData, setRightData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [playError, setPlayError] = useState('');
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [leftDuration, setLeftDuration] = useState(0);
  const [rightDuration, setRightDuration] = useState(0);
  const leftPlayer = useRef(null);
  const rightPlayer = useRef(null);
  const syncLock = useRef(false);

  // Upload modal state
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [targetSession, setTargetSession] = useState('A');
  const [uploadTitle, setUploadTitle] = useState('');
  const [uploadActivity, setUploadActivity] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStage, setUploadStage] = useState('idle'); // 'idle' | 'uploading' | 'uploaded' | 'analyzing' | 'done' | 'error'
  const [uploadError, setUploadError] = useState('');
  const [uploadedVideo, setUploadedVideo] = useState(null);

  useEffect(() => {
    if (analyzed.length > 0) {
      setLeftId((current) => {
        const stillValid = analyzed.some((v) => String(v.id) === String(current));
        return stillValid ? current : String(analyzed[0].id);
      });
      setRightId((current) => {
        const fallback = analyzed.length > 1 ? String(analyzed[1].id) : String(analyzed[0].id);
        const stillValid = analyzed.some((v) => String(v.id) === String(current));
        return stillValid && current !== String(analyzed[0].id) ? current : fallback;
      });
    }
  }, [analyzed]);

  useEffect(() => {
    let cancelled = false;
    async function loadComparisons() {
      setError('');
      setLeftData(null);
      setRightData(null);
      if (!leftId || !rightId) return;
      setLoading(true);
      try {
        const [leftBiomechanics, leftRisk, rightBiomechanics, rightRisk] = await Promise.all([
          api.getBiomechanics(leftId),
          api.getInjuryRisk(leftId),
          api.getBiomechanics(rightId),
          api.getInjuryRisk(rightId),
        ]);
        if (!cancelled) {
          setLeftData({ biomechanics: leftBiomechanics, risk: leftRisk });
          setRightData({ biomechanics: rightBiomechanics, risk: rightRisk });
        }
      } catch (err) {
        if (!cancelled) setError(err.message || 'Could not load comparison metrics.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    loadComparisons();
    return () => {
      cancelled = true;
    };
  }, [leftId, rightId]);

  useEffect(() => {
    setIsPlaying(false);
    setCurrentTime(0);
    setLeftDuration(0);
    setRightDuration(0);
    setPlayError('');
    [leftPlayer.current, rightPlayer.current].forEach((player) => {
      if (player) {
        player.pause();
        player.currentTime = 0;
      }
    });
  }, [leftId, rightId]);

  const selectedVideo = (id) => internalVideos.find((video) => String(video.id) === String(id));
  const getCoverage = (data) => {
    const frames = data?.biomechanics?.time_series_data || [];
    if (!frames.length) return 0;
    const detected = frames.filter((frame) => frame?.detected).length;
    return (detected / frames.length) * 100;
  };
  const coverageLabel = (data) => {
    const frames = data?.biomechanics?.time_series_data || [];
    if (!frames.length) return 'Unavailable';
    const detected = frames.filter((frame) => frame?.detected).length;
    return `${Math.round((detected / frames.length) * 100)}% (${detected}/${frames.length})`;
  };

  const leftVideo = selectedVideo(leftId);
  const rightVideo = selectedVideo(rightId);

  const isSyntheticVideo = (video) => {
    if (!video) return false;
    const title = (video.title || '').toLowerCase();
    const filename = (video.original_filename || '').toLowerCase();
    const filePath = (video.file_path || '').toLowerCase();
    return title.includes('synthetic') || filename.includes('synthetic') || filePath.includes('synthetic');
  };

  const leftCoverage = getCoverage(leftData);
  const rightCoverage = getCoverage(rightData);
  const hasLowCoverage = (leftData && leftCoverage < 40) || (rightData && rightCoverage < 40);

  const duration =
    leftDuration > 0 && rightDuration > 0
      ? Math.min(leftDuration, rightDuration)
      : Math.min(Number(leftVideo?.duration_seconds) || 0, Number(rightVideo?.duration_seconds) || 0);

  const canPlayBoth = Boolean(leftVideo?.processed_video_path && rightVideo?.processed_video_path);

  const syncPlayers = (time) => {
    const boundedTime = Math.max(0, Math.min(time, duration || time));
    setCurrentTime(boundedTime);
    syncLock.current = true;
    [leftPlayer.current, rightPlayer.current].forEach((player) => {
      if (player && Math.abs(player.currentTime - boundedTime) > 0.08) player.currentTime = boundedTime;
    });
    window.setTimeout(() => {
      syncLock.current = false;
    }, 0);
  };

  const togglePlayback = async () => {
    const p1 = leftPlayer.current;
    const p2 = rightPlayer.current;
    if (!p1 || !p2) return;
    if (!canPlayBoth) {
      setPlayError('Both sessions must have a completed pose overlay video to play.');
      return;
    }
    setPlayError('');
    if (isPlaying) {
      p1.pause();
      p2.pause();
      setIsPlaying(false);
      return;
    }
    if (duration > 0 && currentTime >= duration) {
      syncPlayers(0);
    } else {
      syncPlayers(currentTime);
    }
    try {
      await Promise.all([p1.play(), p2.play()]);
      setIsPlaying(true);
    } catch {
      p1.pause();
      p2.pause();
      setIsPlaying(false);
      setPlayError('Synchronized playback could not start. Please ensure both overlay videos are reachable.');
    }
  };

  const handleLeftTimeUpdate = () => {
    if (syncLock.current || !leftPlayer.current) return;
    const time = leftPlayer.current.currentTime;
    if (duration > 0 && time >= duration) {
      [leftPlayer.current, rightPlayer.current].forEach((player) => player?.pause());
      setCurrentTime(duration);
      setIsPlaying(false);
      return;
    }
    setCurrentTime(time);
    const right = rightPlayer.current;
    if (right && Math.abs(right.currentTime - time) > 0.12) {
      right.currentTime = Math.min(time, right.duration || time);
    }
  };

  const handleSeek = (event) => {
    syncPlayers(Number(event.target.value));
  };

  // Upload modal handlers
  const openUploadModal = (sessionLetter) => {
    setTargetSession(sessionLetter);
    setUploadTitle('');
    setUploadActivity('');
    setSelectedFile(null);
    setUploadProgress(0);
    setUploadStage('idle');
    setUploadError('');
    setUploadedVideo(null);
    setUploadModalOpen(true);
  };

  const closeUploadModal = () => {
    setUploadModalOpen(false);
    setUploadStage('idle');
    setSelectedFile(null);
    setUploadedVideo(null);
    setUploadError('');
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      if (!uploadTitle.trim()) {
        const defaultName = file.name.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' ');
        setUploadTitle(`Session ${targetSession} - ${defaultName}`);
      }
    }
  };

  const triggerPoseAnalysis = async (videoToAnalyze) => {
    if (!videoToAnalyze) return;
    setUploadStage('analyzing');
    setUploadError('');

    try {
      const analysisResult = await api.runAnalysis(videoToAnalyze.id);
      if (!analysisResult?.processed_video_path) {
        throw new Error('Pose analysis completed but pose overlay video was not generated.');
      }

      // Check detection coverage from time_series_data
      const frames = analysisResult?.biomechanics?.time_series_data || [];
      const hasDetections = frames.some((f) => f?.detected);
      if (frames.length > 0 && !hasDetections) {
        throw new Error('No athlete pose was detected. Please ensure full athlete body is visible in the frame.');
      }

      // Refresh videos from backend
      const freshVideos = await api.getVideos();
      setInternalVideos(freshVideos);
      onVideosUpdated?.(freshVideos);

      // Automatically select this completed upload into target slot
      if (targetSession === 'A') {
        setLeftId(String(videoToAnalyze.id));
      } else {
        setRightId(String(videoToAnalyze.id));
      }

      setUploadStage('done');
    } catch (err) {
      setUploadStage('error');
      setUploadError(err.message || 'Pose tracking analysis failed.');
    }
  };

  const handleUploadSubmit = async (e) => {
    e.preventDefault();
    if (!selectedFile || !uploadActivity || !uploadTitle.trim()) return;

    setUploadStage('uploading');
    setUploadProgress(0);
    setUploadError('');

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('title', uploadTitle.trim());
      formData.append('activity_type', uploadActivity);
      formData.append('athlete_id', '1');

      const uploaded = await api.uploadVideo(formData, (progress) => {
        setUploadProgress(progress);
      });

      setUploadedVideo(uploaded);
      setUploadStage('uploaded');

      // Immediately run pose tracking analysis
      await triggerPoseAnalysis(uploaded);
    } catch (err) {
      setUploadStage('error');
      setUploadError(err.message || 'Video upload failed.');
    }
  };

  const movementMismatch =
    leftVideo && rightVideo && leftVideo.activity_type && rightVideo.activity_type && leftVideo.activity_type !== rightVideo.activity_type;

  return (
    <section className="space-y-6">
      {/* Page Header */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="rounded-xl bg-teal-50 p-2.5 text-teal-800">
              <ArrowLeftRight className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-900">Movement Comparison</h1>
              <p className="mt-1 text-sm text-slate-600">
                Compare two analyzed sessions side by side. Upload videos directly or select from previous sessions to analyze and compare kinematics.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={() => openUploadModal('A')}
              className="inline-flex items-center gap-1.5 rounded-lg bg-teal-800 px-3.5 py-2 text-xs font-semibold text-white hover:bg-teal-900 transition-colors shadow-xs"
            >
              <Upload className="h-3.5 w-3.5" />
              Upload Session A
            </button>
            <button
              type="button"
              onClick={() => openUploadModal('B')}
              className="inline-flex items-center gap-1.5 rounded-lg bg-teal-800 px-3.5 py-2 text-xs font-semibold text-white hover:bg-teal-900 transition-colors shadow-xs"
            >
              <Upload className="h-3.5 w-3.5" />
              Upload Session B
            </button>
          </div>
        </div>
      </div>

      {/* Compact Session A / Session B Selection Cards */}
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-bold uppercase tracking-wider text-teal-800">Session A</span>
              {leftVideo && (
                <span className="text-[11px] font-medium text-slate-600 bg-slate-100 px-2 py-0.5 rounded">
                  {leftVideo.activity_type}
                </span>
              )}
            </div>
            <p className="text-sm font-semibold text-slate-900 truncate">
              {leftVideo ? leftVideo.title : 'No session selected'}
            </p>
            <p className="text-xs text-slate-500 mt-0.5">
              {leftVideo ? `${leftVideo.duration_seconds}s • ${leftVideo.resolution || 'Standard'}` : 'Select a previous session below or upload a new video'}
            </p>
            {isSyntheticVideo(leftVideo) && (
              <span className="mt-2 inline-flex items-center text-[11px] font-medium text-amber-800 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded">
                Reference simulation — not clinical athlete footage.
              </span>
            )}
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
            <button
              type="button"
              onClick={() => openUploadModal('A')}
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-teal-800 hover:text-teal-900"
            >
              <Upload className="h-3.5 w-3.5" />
              Upload Session A
            </button>
            {leftVideo?.processed_video_path ? (
              <span className="inline-flex items-center gap-1 text-[11px] font-medium text-teal-700">
                <CheckCircle className="h-3 w-3" /> Overlay ready
              </span>
            ) : (
              <span className="text-[11px] text-slate-400">No overlay</span>
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-bold uppercase tracking-wider text-teal-800">Session B</span>
              {rightVideo && (
                <span className="text-[11px] font-medium text-slate-600 bg-slate-100 px-2 py-0.5 rounded">
                  {rightVideo.activity_type}
                </span>
              )}
            </div>
            <p className="text-sm font-semibold text-slate-900 truncate">
              {rightVideo ? rightVideo.title : 'No session selected'}
            </p>
            <p className="text-xs text-slate-500 mt-0.5">
              {rightVideo ? `${rightVideo.duration_seconds}s • ${rightVideo.resolution || 'Standard'}` : 'Select a previous session below or upload a new video'}
            </p>
            {isSyntheticVideo(rightVideo) && (
              <span className="mt-2 inline-flex items-center text-[11px] font-medium text-amber-800 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded">
                Reference simulation — not clinical athlete footage.
              </span>
            )}
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
            <button
              type="button"
              onClick={() => openUploadModal('B')}
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-teal-800 hover:text-teal-900"
            >
              <Upload className="h-3.5 w-3.5" />
              Upload Session B
            </button>
            {rightVideo?.processed_video_path ? (
              <span className="inline-flex items-center gap-1 text-[11px] font-medium text-teal-700">
                <CheckCircle className="h-3 w-3" /> Overlay ready
              </span>
            ) : (
              <span className="text-[11px] text-slate-400">No overlay</span>
            )}
          </div>
        </div>
      </div>

      {/* Movement mismatch note */}
      {movementMismatch && (
        <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700">
          <AlertCircle className="h-4 w-4 text-slate-500 shrink-0" />
          <span>For meaningful comparison, select two sessions of the same movement type.</span>
        </div>
      )}

      {/* Low pose coverage warning */}
      {hasLowCoverage && (
        <div role="alert" className="flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
          <AlertCircle className="h-4 w-4 text-amber-700 shrink-0" />
          <span>
            Warning: Low pose detection coverage detected ({leftCoverage < 40 ? `Session A: ${Math.round(leftCoverage)}%` : ''}
            {leftCoverage < 40 && rightCoverage < 40 ? ', ' : ''}
            {rightCoverage < 40 ? `Session B: ${Math.round(rightCoverage)}%` : ''}). Measurements may be incomplete.
          </span>
        </div>
      )}

      {analyzed.length < 2 ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-900">
          Upload and analyze at least two videos to compare them here. Use the <strong>Upload Session A</strong> and <strong>Upload Session B</strong> buttons above to upload and process videos directly.
        </div>
      ) : (
        <>
          {/* Side by Side Pose-Overlay Videos */}
          <div className="grid gap-4 lg:grid-cols-2">
            {[
              {
                label: 'Session A',
                id: leftId,
                setId: setLeftId,
                otherId: rightId,
                video: leftVideo,
                playerRef: leftPlayer,
                durationSetter: setLeftDuration,
                timeUpdate: handleLeftTimeUpdate,
              },
              {
                label: 'Session B',
                id: rightId,
                setId: setRightId,
                otherId: leftId,
                video: rightVideo,
                playerRef: rightPlayer,
                durationSetter: setRightDuration,
                timeUpdate: () => {},
              },
            ].map(({ label, id, setId, otherId, video, playerRef, durationSetter, timeUpdate }) => (
              <article key={label} className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
                <div className="p-4">
                  <div className="flex items-center justify-between mb-2">
                    <label className="block text-xs font-semibold uppercase tracking-wide text-slate-600">{label}</label>
                    <button
                      type="button"
                      onClick={() => openUploadModal(label.endsWith('A') ? 'A' : 'B')}
                      className="inline-flex items-center gap-1 text-[11px] font-medium text-teal-800 hover:text-teal-900"
                    >
                      <Upload className="h-3 w-3" /> Upload new
                    </button>
                  </div>
                  <select
                    value={id}
                    onChange={(event) => setId(event.target.value)}
                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
                  >
                    {analyzed.map((option) => {
                      const isSynth = isSyntheticVideo(option);
                      const cleanTitle = option.title.replace(/^Synthetic Demo:\s*/i, '').replace(/^Demo:\s*/i, '');
                      const prefix = isSynth && !cleanTitle.toLowerCase().includes('simulation') ? '[Simulation] ' : '';
                      return (
                        <option key={option.id} value={option.id} disabled={String(option.id) === String(otherId)}>
                          {prefix}{cleanTitle} — {option.activity_type}
                        </option>
                      );
                    })}
                  </select>
                </div>
                {video && (
                  <>
                    <div className="relative aspect-video bg-slate-950 rounded-xl overflow-hidden border border-slate-200">
                      <video
                        key={video.id}
                        ref={playerRef}
                        muted
                        controls
                        playsInline
                        preload="auto"
                        className="h-full w-full object-contain"
                        src={`/api/videos/${video.id}/processed_stream`}
                        onLoadedMetadata={(event) => {
                          durationSetter(event.currentTarget.duration);
                          if (event.currentTarget.currentTime === 0) {
                            try {
                              event.currentTarget.currentTime = 0.01;
                            } catch {}
                          }
                        }}
                        onTimeUpdate={timeUpdate}
                        onEnded={() => {
                          leftPlayer.current?.pause();
                          rightPlayer.current?.pause();
                          setIsPlaying(false);
                        }}
                        onError={() => {
                          setPlayError(
                            `Pose overlay video is unavailable for ${label} (${video.title}). Please ensure analysis has run successfully.`
                          );
                        }}
                      />
                      <span className="absolute left-3 top-3 rounded-md bg-slate-900/80 px-2 py-1 text-[11px] font-medium text-white shadow-xs">
                        Pose overlay
                      </span>
                      {isSyntheticVideo(video) && (
                        <span className="absolute right-3 top-3 rounded-md bg-amber-900/85 px-2 py-1 text-[11px] font-semibold text-white shadow-xs">
                          Simulation
                        </span>
                      )}
                    </div>
                    <div className="p-4">
                      <div className="flex items-center justify-between gap-2">
                        <p className="font-semibold text-slate-900 truncate">
                          {video.title.replace(/^Synthetic Demo:\s*/i, '').replace(/^Demo:\s*/i, '')}
                        </p>
                        {isSyntheticVideo(video) && (
                          <span className="shrink-0 rounded bg-amber-100 text-amber-800 border border-amber-200 text-[10px] font-semibold px-1.5 py-0.5">
                            Simulation
                          </span>
                        )}
                      </div>
                      <p className="mt-1 text-xs text-slate-500">
                        {video.activity_type} · {video.duration_seconds}s · {video.resolution}
                      </p>
                      {isSyntheticVideo(video) && (
                        <p className="mt-2 text-[11px] font-medium text-amber-800 bg-amber-50 border border-amber-200 rounded px-2 py-1">
                          Reference simulation — not clinical athlete footage. Movement-analysis results support screening and review; they are not a medical diagnosis.
                        </p>
                      )}
                    </div>
                  </>
                )}
              </article>
            ))}
          </div>

          {/* Synchronized Playback Controls */}
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={togglePlayback}
                disabled={!canPlayBoth}
                className="inline-flex items-center gap-2 rounded-lg bg-teal-800 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-900 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                title={!canPlayBoth ? 'Both sessions must have valid pose overlay videos' : ''}
              >
                {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                {isPlaying ? 'Pause both' : 'Play both'}
              </button>
              <span className="min-w-28 font-mono text-xs text-slate-600">
                {formatTime(currentTime)} / {formatTime(duration)}
              </span>
              <input
                aria-label="Seek both comparison videos"
                type="range"
                min="0"
                max={duration || 0}
                step="0.01"
                value={Math.min(currentTime, duration || currentTime)}
                onChange={handleSeek}
                disabled={!duration || !canPlayBoth}
                className="min-w-48 flex-1 accent-teal-700"
              />
              <span className="text-xs text-slate-500">Synchronized playback</span>
            </div>
            {playError && (
              <p role="alert" className="mt-3 text-sm text-rose-700">
                {playError}
              </p>
            )}
          </div>

          {/* Biomechanical Comparison Table */}
          {error && (
            <div role="alert" className="flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
              <AlertCircle className="h-4 w-4" />
              {error}
            </div>
          )}
          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="flex items-center gap-2 border-b border-slate-200 px-4 py-3">
              <Activity className="h-4 w-4 text-teal-700" />
              <h2 className="font-semibold text-slate-900">Measured comparison</h2>
            </div>
            {loading ? (
              <p className="p-4 text-sm text-slate-600">Loading results…</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-50 text-xs uppercase text-slate-600">
                    <tr>
                      <th className="px-4 py-3">Measure</th>
                      <th className="px-4 py-3">Session A</th>
                      <th className="px-4 py-3">Session B</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    <tr>
                      <th className="px-4 py-3 font-medium text-slate-700">Rule-based risk score</th>
                      <td className="px-4 py-3">{displayValue(leftData?.risk?.overall_injury_risk_score, '/100', leftCoverage)}</td>
                      <td className="px-4 py-3">{displayValue(rightData?.risk?.overall_injury_risk_score, '/100', rightCoverage)}</td>
                    </tr>
                    <tr>
                      <th className="px-4 py-3 font-medium text-slate-700">Pose detection coverage</th>
                      <td className="px-4 py-3">{coverageLabel(leftData)}</td>
                      <td className="px-4 py-3">{coverageLabel(rightData)}</td>
                    </tr>
                    <tr>
                      <th className="px-4 py-3 font-medium text-slate-700">Risk category</th>
                      <td className="px-4 py-3">
                        {leftCoverage === 0 ? 'Insufficient pose data' : leftData?.risk?.risk_category || 'Not analyzed'}
                      </td>
                      <td className="px-4 py-3">
                        {rightCoverage === 0 ? 'Insufficient pose data' : rightData?.risk?.risk_category || 'Not analyzed'}
                      </td>
                    </tr>
                    {metricRows.map(([label, key, suffix]) => (
                      <tr key={key}>
                        <th className="px-4 py-3 font-medium text-slate-700">{label}</th>
                        <td className="px-4 py-3">{displayValue(leftData?.biomechanics?.metrics?.[key], suffix, leftCoverage)}</td>
                        <td className="px-4 py-3">{displayValue(rightData?.biomechanics?.metrics?.[key], suffix, rightCoverage)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <p className="border-t border-slate-100 px-4 py-3 text-xs text-slate-500">
              Compare pose coverage before interpreting scores. Movement-analysis results support screening and review; they are not a medical diagnosis.
            </p>
          </div>
        </>
      )}

      {/* Upload and Analysis Modal */}
      {uploadModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-xs">
          <div className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-xl max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <div className="rounded-lg bg-teal-50 p-2 text-teal-800">
                  <Upload className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900">Upload Video for Session {targetSession}</h3>
                  <p className="text-xs text-slate-500">Directly add a new session into the comparison view</p>
                </div>
              </div>
              <button
                type="button"
                onClick={closeUploadModal}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="mt-4 space-y-4">
              {uploadStage === 'idle' && (
                <form onSubmit={handleUploadSubmit} className="space-y-4">
                  <div>
                    <label className="text-xs font-semibold text-slate-700 block mb-1">
                      Session Title <span className="text-rose-600">*</span>
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Session A - Landing Assessment"
                      value={uploadTitle}
                      onChange={(e) => setUploadTitle(e.target.value)}
                      className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-900 outline-none focus:border-teal-700 focus:ring-1 focus:ring-teal-700"
                      required
                    />
                  </div>

                  <div>
                    <label className="text-xs font-semibold text-slate-700 block mb-1">
                      Movement Type <span className="text-rose-600">*</span>
                    </label>
                    <select
                      required
                      value={uploadActivity}
                      onChange={(e) => setUploadActivity(e.target.value)}
                      className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-900 outline-none focus:border-teal-700 focus:ring-1 focus:ring-teal-700"
                    >
                      <option value="">Choose a movement type</option>
                      <option value="Drop Jump">Drop jump / landing</option>
                      <option value="Side Cut">Side cut / change of direction</option>
                      <option value="Deep Squat">Deep squat</option>
                      <option value="Running">Running</option>
                      <option value="Sprinting">Sprinting</option>
                      <option value="Throwing">Throwing</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-xs font-semibold text-slate-700 block mb-1">
                      Local Video File (.mp4, .mov, .webm) <span className="text-rose-600">*</span>
                    </label>
                    <input
                      type="file"
                      accept="video/*"
                      onChange={handleFileChange}
                      className="w-full text-xs text-slate-600 file:mr-3 file:py-2 file:px-3 file:rounded-lg file:border file:border-slate-300 file:text-xs file:font-semibold file:bg-slate-50 file:text-slate-700 hover:file:bg-slate-100 cursor-pointer"
                      required
                    />
                    <p className="mt-1 text-[11px] text-slate-500">
                      Recommended: Short H.264 clip, stable camera, full athlete body visible.
                    </p>
                  </div>

                  <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
                    <button
                      type="button"
                      onClick={closeUploadModal}
                      className="px-4 py-2 rounded-lg text-xs font-medium text-slate-600 hover:bg-slate-100 transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={!selectedFile || !uploadActivity || !uploadTitle.trim()}
                      className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold bg-teal-800 hover:bg-teal-900 text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <Upload className="h-3.5 w-3.5" />
                      Upload &amp; Analyze Session {targetSession}
                    </button>
                  </div>
                </form>
              )}

              {uploadStage === 'uploading' && (
                <div className="py-6 text-center space-y-3">
                  <div className="flex justify-center">
                    <Loader2 className="h-8 w-8 animate-spin text-teal-800" />
                  </div>
                  <h4 className="text-sm font-semibold text-slate-900">Uploading Video File</h4>
                  <p className="text-xs text-slate-500">Uploading {selectedFile?.name || 'video'} to server...</p>
                  <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden mt-3">
                    <div
                      className="bg-teal-700 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                  <span className="text-xs font-mono text-slate-500">{uploadProgress}%</span>
                </div>
              )}

              {(uploadStage === 'uploaded' || uploadStage === 'analyzing') && uploadedVideo && (
                <div className="space-y-4">
                  <div>
                    <span className="text-xs font-semibold text-slate-700 block mb-1.5">Original Video Preview</span>
                    <div className="relative aspect-video rounded-xl overflow-hidden bg-slate-950 border border-slate-200">
                      <video
                        controls
                        playsInline
                        preload="auto"
                        className="h-full w-full object-contain"
                        src={`/api/videos/${uploadedVideo.id}/stream`}
                      />
                      <span className="absolute left-3 top-3 rounded-md bg-slate-900/80 px-2 py-1 text-[11px] font-medium text-white shadow-xs">
                        Original video
                      </span>
                    </div>
                  </div>

                  <div className="rounded-xl border border-teal-200 bg-teal-50 p-4 text-center space-y-2">
                    <div className="flex items-center justify-center gap-2 text-teal-900 font-semibold text-sm">
                      <Loader2 className="h-4 w-4 animate-spin text-teal-700" />
                      Analyzing pose kinematics with MediaPipe...
                    </div>
                    <p className="text-xs text-teal-800">
                      Detecting joint landmarks, estimating valgus angles, and rendering the pose skeleton overlay.
                    </p>
                  </div>
                </div>
              )}

              {uploadStage === 'done' && uploadedVideo && (
                <div className="space-y-4">
                  <div className="flex items-center gap-2 rounded-xl border border-teal-200 bg-teal-50 p-3 text-xs text-teal-900">
                    <CheckCircle className="h-4 w-4 text-teal-700 shrink-0" />
                    <span>
                      Pose overlay generated successfully! This session has been assigned to <strong>Session {targetSession}</strong> in the comparison view.
                    </span>
                  </div>

                  <div>
                    <span className="text-xs font-semibold text-slate-700 block mb-1.5">Generated Pose Overlay Video</span>
                    <div className="relative aspect-video rounded-xl overflow-hidden bg-slate-950 border border-slate-200">
                      <video
                        controls
                        playsInline
                        preload="auto"
                        className="h-full w-full object-contain"
                        src={`/api/videos/${uploadedVideo.id}/processed_stream`}
                      />
                      <span className="absolute left-3 top-3 rounded-md bg-teal-900/90 px-2 py-1 text-[11px] font-medium text-white shadow-xs">
                        Pose overlay
                      </span>
                    </div>
                  </div>

                  <div className="flex justify-end pt-3 border-t border-slate-100">
                    <button
                      type="button"
                      onClick={closeUploadModal}
                      className="px-5 py-2 rounded-lg text-xs font-semibold bg-teal-800 hover:bg-teal-900 text-white transition-colors"
                    >
                      Apply &amp; View in Comparison
                    </button>
                  </div>
                </div>
              )}

              {uploadStage === 'error' && (
                <div className="space-y-4">
                  {uploadedVideo && (
                    <div>
                      <span className="text-xs font-semibold text-slate-700 block mb-1.5">Original Video Preview</span>
                      <div className="relative aspect-video rounded-xl overflow-hidden bg-slate-950 border border-slate-200">
                        <video
                          controls
                          playsInline
                          preload="auto"
                          className="h-full w-full object-contain"
                          src={`/api/videos/${uploadedVideo.id}/stream`}
                        />
                      </div>
                    </div>
                  )}

                  <div className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800 space-y-1">
                    <div className="flex items-center gap-2 font-semibold">
                      <AlertCircle className="h-4 w-4 text-rose-700 shrink-0" />
                      <span>Processing Error</span>
                    </div>
                    <p>{uploadError}</p>
                    <p className="text-[11px] text-rose-700 mt-1">
                      Videos without a valid pose overlay cannot be compared. Please check video framing and lighting.
                    </p>
                  </div>

                  <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
                    <button
                      type="button"
                      onClick={closeUploadModal}
                      className="px-4 py-2 rounded-lg text-xs font-medium text-slate-600 hover:bg-slate-100 transition-colors"
                    >
                      Close
                    </button>
                    {uploadedVideo && (
                      <button
                        type="button"
                        onClick={() => triggerPoseAnalysis(uploadedVideo)}
                        className="px-4 py-2 rounded-lg text-xs font-semibold bg-teal-800 hover:bg-teal-900 text-white transition-colors"
                      >
                        Retry Analysis
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
