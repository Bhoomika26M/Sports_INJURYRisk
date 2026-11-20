import React, { useState, useEffect, useRef } from 'react';
import { videosAPI } from '../services/api';
import ComparisonPanel from './ComparisonPanel';

const fmt = (v, digits = 1) => (v === null || v === undefined ? '—' : Number(v).toFixed(digits));

/**
 * DualVideoPlayer
 * Side-by-side synchronized video comparison player with baseline form selection:
 * - Option 1: Gold Standard Benchmark Video (per activity)
 * - Option 2: Same athlete's previous videos or other available videos
 * - Supports both active processing (live streaming) and completed analysis runs.
 */
const DualVideoPlayer = ({
  trialVideo,
  athleteId,
  activityType,
  allVideos = [],
  isProcessing = false,
  progress = null,
  annotatedVideoUrl = null,
}) => {
  const [availableBaselines, setAvailableBaselines] = useState([]);
  const [selectedBaselineId, setSelectedBaselineId] = useState('');
  const [baselineVideo, setBaselineVideo] = useState(null);
  const [pairwiseComparison, setPairwiseComparison] = useState(null);
  const [loadingComparison, setLoadingComparison] = useState(false);
  const [comparisonError, setComparisonError] = useState('');

  // Video display modes
  const [trialAnnotated, setTrialAnnotated] = useState(true);
  const [baselineAnnotated, setBaselineAnnotated] = useState(true);

  // Playback synchronization
  const trialVideoRef = useRef(null);
  const baselineVideoRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackRate, setPlaybackRate] = useState(1.0);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  // Load available baseline candidates
  useEffect(() => {
    loadBaselines();
  }, [trialVideo?.id, athleteId, activityType]);

  const loadBaselines = async () => {
    try {
      // Fetch all completed videos
      const resp = await videosAPI.getAll();
      const videos = resp.data || [];

      // Filter for videos that are completed and have same activity type
      const candidates = videos.filter(
        (v) =>
          v.id !== trialVideo?.id &&
          v.processing_status === 'completed' &&
          (!activityType || v.activity_type === activityType)
      );

      // Sort: System benchmark first, then same athlete's previous videos, then others
      candidates.sort((a, b) => {
        const aIsBenchmark = a.original_filename?.toLowerCase().includes('gold') || a.athlete_id === 3;
        const bIsBenchmark = b.original_filename?.toLowerCase().includes('gold') || b.athlete_id === 3;
        if (aIsBenchmark && !bIsBenchmark) return -1;
        if (!aIsBenchmark && bIsBenchmark) return 1;
        const aSameAthlete = a.athlete_id === athleteId;
        const bSameAthlete = b.athlete_id === athleteId;
        if (aSameAthlete && !bSameAthlete) return -1;
        if (!aSameAthlete && bSameAthlete) return 1;
        return b.id - a.id;
      });

      setAvailableBaselines(candidates);

      // Auto-select top recommendation (Benchmark if available, else first prior video)
      if (candidates.length > 0 && !selectedBaselineId) {
        setSelectedBaselineId(candidates[0].id.toString());
      }
    } catch (err) {
      console.error('Failed to load baseline candidates:', err);
    }
  };

  // When selected baseline changes, fetch pairwise analysis if trial is completed
  useEffect(() => {
    if (!selectedBaselineId || !trialVideo?.id) return;
    const baseId = parseInt(selectedBaselineId, 10);
    const chosen = availableBaselines.find((v) => v.id === baseId);
    setBaselineVideo(chosen || null);

    if (trialVideo.processing_status === 'completed') {
      fetchPairwise(baseId);
    } else {
      setPairwiseComparison(null);
    }
  }, [selectedBaselineId, trialVideo?.id, trialVideo?.processing_status, availableBaselines]);

  const fetchPairwise = async (baseId) => {
    setLoadingComparison(true);
    setComparisonError('');
    try {
      const resp = await videosAPI.compareWithVideo(trialVideo.id, baseId);
      setPairwiseComparison(resp.data);
    } catch (err) {
      setComparisonError(err.response?.data?.detail || 'Failed to compare videos');
    } finally {
      setLoadingComparison(false);
    }
  };

  // Coordinated playback handlers
  const togglePlay = () => {
    const t = trialVideoRef.current;
    const b = baselineVideoRef.current;
    if (!t && !b) return;

    if (isPlaying) {
      if (t) t.pause();
      if (b) b.pause();
      setIsPlaying(false);
    } else {
      if (t) t.play().catch(() => {});
      if (b) b.play().catch(() => {});
      setIsPlaying(true);
    }
  };

  const handleSeek = (e) => {
    const time = parseFloat(e.target.value);
    setCurrentTime(time);
    if (trialVideoRef.current) trialVideoRef.current.currentTime = time;
    if (baselineVideoRef.current) baselineVideoRef.current.currentTime = time;
  };

  const handleTimeUpdate = () => {
    if (trialVideoRef.current) {
      setCurrentTime(trialVideoRef.current.currentTime);
      if (trialVideoRef.current.duration) {
        setDuration(trialVideoRef.current.duration);
      }
    }
  };

  const handleRateChange = (rate) => {
    setPlaybackRate(rate);
    if (trialVideoRef.current) trialVideoRef.current.playbackRate = rate;
    if (baselineVideoRef.current) baselineVideoRef.current.playbackRate = rate;
  };

  const syncVideos = () => {
    if (trialVideoRef.current && baselineVideoRef.current) {
      baselineVideoRef.current.currentTime = trialVideoRef.current.currentTime;
    }
  };

  return (
    <div className="bg-white rounded-2xl border-2 border-indigo-200/80 shadow-md p-4 sm:p-5 mb-6 overflow-hidden">
      {/* Header & Baseline Selection Bar */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between pb-3.5 mb-3.5 border-b border-gray-100 gap-3">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="w-3 h-3 rounded-full bg-emerald-500 animate-pulse" />
            <h2 className="text-xl font-display font-bold text-gray-900 tracking-tight">
              Dual-Stream Biomechanical Comparison
            </h2>
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-bold bg-indigo-50 text-indigo-700 border border-indigo-200">
              Side-by-Side Sync
            </span>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Compare active trial mechanics against a certified clinical baseline or benchmark form.
          </p>
        </div>

        {/* Baseline Selector Dropdown */}
        <div className="flex items-center gap-2 bg-gray-50 p-2 rounded-xl border border-gray-200">
          <label className="text-xs font-semibold text-gray-700 whitespace-nowrap flex items-center gap-1.5">
            <span className="text-amber-500 font-bold">★</span> Baseline Source:
          </label>
          <select
            value={selectedBaselineId}
            onChange={(e) => setSelectedBaselineId(e.target.value)}
            className="text-xs bg-white border border-gray-300 rounded-lg px-3 py-1.5 font-medium text-gray-800 shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            {availableBaselines.length === 0 ? (
              <option value="">No other videos available for {activityType || 'activity'}</option>
            ) : (
              availableBaselines.map((v) => {
                const isBench = v.original_filename?.toLowerCase().includes('gold') || v.athlete_id === 3;
                const isSame = v.athlete_id === athleteId;
                const tag = isBench ? '[Gold Standard Benchmark]' : isSame ? '[Athlete Prior Session]' : `[Athlete #${v.athlete_id}]`;
                return (
                  <option key={v.id} value={v.id}>
                    {tag} Video #{v.id} - {v.original_filename}
                  </option>
                );
              })
            )}
          </select>
        </div>
      </div>

      {/* Side-by-Side Video Players */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        {/* LEFT VIEWPORT: Baseline Video */}
        <div className="flex flex-col bg-slate-900 rounded-xl overflow-hidden border border-slate-800 shadow-inner">
          <div className="px-3 py-2 bg-slate-800/90 border-b border-slate-700 flex items-center justify-between text-xs text-slate-200 font-mono">
            <div className="flex items-center gap-2 font-semibold">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              <span>BASELINE REFERENCE</span>
              {baselineVideo?.original_filename?.toLowerCase().includes('gold') && (
                <span className="bg-amber-400/20 text-amber-300 px-1.5 py-0.5 rounded text-[10px] border border-amber-400/30 font-bold">
                  ★ GOLD FORM
                </span>
              )}
            </div>
            {baselineVideo && (
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => setBaselineAnnotated(!baselineAnnotated)}
                  className={`px-2 py-0.5 rounded text-[10px] font-semibold transition-colors ${
                    baselineAnnotated ? 'bg-indigo-600 text-white' : 'bg-slate-700 text-slate-300'
                  }`}
                >
                  {baselineAnnotated ? 'Overlay On' : 'Raw'}
                </button>
              </div>
            )}
          </div>

          <div className="relative aspect-video max-h-[38vh] flex items-center justify-center bg-black">
            {baselineVideo ? (
              <video
                ref={baselineVideoRef}
                key={`baseline-${baselineVideo.id}-${baselineAnnotated}`}
                src={
                  baselineAnnotated
                    ? videosAPI.getAnnotatedVideo(baselineVideo.id)
                    : videosAPI.getVideoUrl(baselineVideo.id)
                }
                className="w-full h-full max-h-[38vh] object-contain"
                muted
                playsInline
                preload="metadata"
                onError={(e) => {
                  console.warn('Baseline video failed to load, falling back to raw if annotated was on', e);
                  if (baselineAnnotated) setBaselineAnnotated(false);
                }}
              />
            ) : (
              <div className="text-center p-6 text-slate-400 text-xs">
                Select a baseline video above to begin side-by-side comparison
              </div>
            )}
          </div>
          <div className="px-3 py-1.5 bg-slate-950 text-[11px] text-slate-400 flex justify-between truncate">
            <span className="truncate">{baselineVideo?.original_filename || 'No baseline selected'}</span>
            <span className="font-mono text-slate-500">Video #{baselineVideo?.id || '—'}</span>
          </div>
        </div>

        {/* RIGHT VIEWPORT: Current Trial Video */}
        <div className="flex flex-col bg-slate-900 rounded-xl overflow-hidden border border-slate-800 shadow-inner">
          <div className="px-3 py-2 bg-slate-800/90 border-b border-slate-700 flex items-center justify-between text-xs text-slate-200 font-mono">
            <div className="flex items-center gap-2 font-semibold">
              <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />
              <span>CURRENT TRIAL TEST</span>
              <span className="bg-indigo-400/20 text-indigo-300 px-1.5 py-0.5 rounded text-[10px] border border-indigo-400/30 font-bold">
                EVALUATION
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => setTrialAnnotated(!trialAnnotated)}
                className={`px-2 py-0.5 rounded text-[10px] font-semibold transition-colors ${
                  trialAnnotated ? 'bg-indigo-600 text-white' : 'bg-slate-700 text-slate-300'
                }`}
              >
                {trialAnnotated ? 'Overlay On' : 'Raw'}
              </button>
            </div>
          </div>

          <div className="relative aspect-video max-h-[38vh] flex items-center justify-center bg-black">
            <video
              ref={trialVideoRef}
              key={`trial-${trialVideo.id}-${trialAnnotated}-${annotatedVideoUrl || ''}`}
              src={
                trialAnnotated
                  ? (annotatedVideoUrl || videosAPI.getAnnotatedVideo(trialVideo.id))
                  : videosAPI.getVideoUrl(trialVideo.id)
              }
              className="w-full h-full max-h-[38vh] object-contain"
              playsInline
              preload="metadata"
              onTimeUpdate={handleTimeUpdate}
              onError={(e) => {
                console.warn('Trial video failed to load, falling back to raw if annotated was on', e);
                if (trialAnnotated) setTrialAnnotated(false);
              }}
            />
          </div>
          <div className="px-3 py-1.5 bg-slate-950 text-[11px] text-slate-400 flex justify-between truncate">
            <span className="truncate">{trialVideo.original_filename}</span>
            <span className="font-mono text-slate-500">Video #{trialVideo.id}</span>
          </div>
        </div>
      </div>

      {/* Unified Playback Bar & Sync Scrubbing Controls */}
      <div className="p-3.5 bg-slate-100 rounded-xl border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={togglePlay}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-lg shadow-sm transition-all flex items-center gap-2"
          >
            {isPlaying ? (
              <>
                <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
                </svg>
                Pause Both
              </>
            ) : (
              <>
                <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M8 5v14l11-7z" />
                </svg>
                Play Synchronized
              </>
            )}
          </button>

          <button
            type="button"
            onClick={syncVideos}
            title="Re-synchronize timestamps"
            className="px-3 py-2 bg-white hover:bg-gray-50 border border-gray-300 text-gray-700 text-xs font-semibold rounded-lg shadow-sm"
          >
            ↺ Align Clocks
          </button>

          {/* Speed selectors */}
          <div className="flex items-center bg-white border border-gray-300 rounded-lg p-0.5 text-[11px] font-mono">
            {[0.25, 0.5, 1.0].map((rate) => (
              <button
                key={rate}
                type="button"
                onClick={() => handleRateChange(rate)}
                className={`px-2 py-1 rounded ${
                  playbackRate === rate ? 'bg-indigo-600 text-white font-bold' : 'text-gray-600 hover:text-black'
                }`}
              >
                {rate}x
              </button>
            ))}
          </div>
        </div>

        {/* Global Timeline Scrubber */}
        <div className="flex-1 max-w-md flex items-center gap-2">
          <span className="text-[11px] font-mono text-gray-500 w-10 text-right">
            {fmt(currentTime, 1)}s
          </span>
          <input
            type="range"
            min="0"
            max={duration || 10}
            step="0.05"
            value={currentTime}
            onChange={handleSeek}
            className="w-full accent-indigo-600 cursor-pointer"
          />
          <span className="text-[11px] font-mono text-gray-500 w-10">
            {fmt(duration, 1)}s
          </span>
        </div>
      </div>

      {/* Side-by-Side Biomechanical Divergence Analysis */}
      {pairwiseComparison && (
        <div className="mt-2">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-display font-bold text-gray-900 text-base flex items-center gap-2">
              <span className="p-1 rounded bg-indigo-100 text-indigo-700">⚖</span>
              Biomechanical Deltas: Trial vs. Chosen Baseline
            </h3>
            <span className="text-xs text-gray-500">
              Evaluated against: <strong className="text-gray-800">{baselineVideo?.original_filename || 'Baseline'}</strong>
            </span>
          </div>

          <ComparisonPanel
            comparison={pairwiseComparison}
            loading={loadingComparison}
            error={comparisonError}
          />
        </div>
      )}
    </div>
  );
};

export default DualVideoPlayer;

