import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { videosAPI } from '../services/api';
import ComparisonPanel from '../components/ComparisonPanel';
import DualVideoPlayer from '../components/DualVideoPlayer';
import FindingCard from '../components/FindingCard';
import AngleGaugeBar from '../components/AngleGaugeBar';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const IN_PROGRESS_STATUSES = ['preprocessing', 'pose_estimation', 'analyzing'];

const SEVERITY_STYLES = {
  low: 'bg-gray-100 text-gray-700 border-gray-300',
  moderate: 'bg-yellow-100 text-yellow-800 border-yellow-300',
  high: 'bg-orange-100 text-orange-800 border-orange-300',
  critical: 'bg-red-100 text-red-800 border-red-300',
};

const RISK_LEVEL_STYLES = {
  low: 'bg-green-100 text-green-800 border-green-300',
  moderate: 'bg-yellow-100 text-yellow-800 border-yellow-300',
  high: 'bg-orange-100 text-orange-800 border-orange-300',
  critical: 'bg-red-100 text-red-800 border-red-300',
};

// Plain-language names for the risk tags returned by the risk engine
const RISK_TAG_LABELS = {
  lumbar_strain: 'Lumbar spine loading',
  knee_overload_asymmetry: 'Asymmetric knee loading',
  limited_rom_knee: 'Limited knee range of motion',
  movement_control_deficit: 'Reduced movement control',
  pose_quality: 'Measurement quality',
};

const fmt = (v, digits = 1) => (v === null || v === undefined ? '—' : Number(v).toFixed(digits));

function VideoAnalysis() {
  const { videoId } = useParams();
  const navigate = useNavigate();
  const [video, setVideo] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [risk, setRisk] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [comparisonLoading, setComparisonLoading] = useState(false);
  const [comparisonError, setComparisonError] = useState('');
  const [progress, setProgress] = useState(null);
  const [previewOk, setPreviewOk] = useState(false);
  const [annotatedVideoUrl, setAnnotatedVideoUrl] = useState(null);
  // True once the live player has produced its first frame. Until then (and if
  // the stream never becomes readable) the still-image preview is shown.
  const [livePlayable, setLivePlayable] = useState(false);
  const [showAnnotated, setShowAnnotated] = useState(true);
  // True while the live player has caught up with the writer and is waiting
  // for more frames. Surfaced in the UI so a pause reads as "buffering" rather
  // than as playback being broken.
  const [waitingForFrames, setWaitingForFrames] = useState(false);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [generatingAnnotated, setGeneratingAnnotated] = useState(false);
  const [error, setError] = useState('');
  const pollRef = useRef(null);
  // The live <video> element, so playback can resume as fragments arrive.
  const liveVideoRef = useRef(null);

  useEffect(() => {
    fetchVideo();

    return () => stopPolling();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [videoId]);

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  /**
   * Live playback pacing.
   *
   * The annotated file is written far slower than real time (a 30s clip takes
   * minutes to analyse, because detection/pose run per frame), so the player
   * inevitably reaches the end of the bytes that exist. The old approach
   * reloaded the whole source on every end event, which produced a
   * play/stutter/reload loop: a few seconds of motion, a hard reset, and
   * visible jumping - the "screenshots changing" feel.
   *
   * Instead we:
   *   1. record where playback stopped,
   *   2. wait until the file has actually grown (polling its size over the
   *      existing range-capable endpoint, so no reload happens until there is
   *      genuinely more to play), and
   *   3. resume from that exact position.
   *
   * The source is reloaded only after the writer has produced more data, so
   * the player no longer thrashes between the end of the file and the start.
   */
  const resumeLivePlayback = () => {
    if (!processing) return; // finished: leaving it stopped is correct
    const el = liveVideoRef.current;
    if (!el) return;

    const resumeAt = el.currentTime > 0.5 ? el.currentTime - 0.3 : 0;
    const knownLength = el.duration && isFinite(el.duration) ? el.duration : 0;
    setWaitingForFrames(true);

    // Poll the endpoint until the media has grown beyond what we have already
    // played. Each poll is a deliberate delay, so this cannot spin.
    const startedAt = Date.now();
    const POLL_MS = 1200;
    const MAX_WAIT_MS = 30000;

    const check = () => {
      if (!processing) {
        setWaitingForFrames(false);
        return;
      }
      if (Date.now() - startedAt > MAX_WAIT_MS) {
        // Do not sit idle forever if growth stalls (e.g. encoder finished
        // early, or a frame with no detection). Fall through and retry once.
        setWaitingForFrames(false);
        return;
      }

      const probe = document.createElement('video');
      probe.preload = 'metadata';
      probe.muted = true;
      const probeUrl = `${videosAPI.getAnnotatedVideo(videoId)}&t=${Date.now()}`;
      const cleanup = () => {
        probe.removeAttribute('src');
        probe.load();
      };
      probe.onloadedmetadata = () => {
        const grown = isFinite(probe.duration) && probe.duration > knownLength + 0.15;
        cleanup();
        if (grown) {
          resumeAtPosition(resumeAt);
        } else {
          setTimeout(check, POLL_MS);
        }
      };
      probe.onerror = () => {
        cleanup();
        setTimeout(check, POLL_MS);
      };
      probe.src = probeUrl;
    };

    const resumeAtPosition = (position) => {
      const target = liveVideoRef.current;
      if (!target || !processing) {
        setWaitingForFrames(false);
        return;
      }
      const fresh = `${videosAPI.getAnnotatedVideo(videoId)}&t=${Date.now()}`;
      const onReady = () => {
        target.removeEventListener('loadedmetadata', onReady);
        try {
          target.currentTime = position;
        } catch (err) {
          // Seeking may fail before enough data exists; next resume catches up.
        }
        setWaitingForFrames(false);
        target.play().catch(() => {
          // Autoplay can be blocked; controls remain available.
        });
      };
      target.addEventListener('loadedmetadata', onReady);
      target.src = fresh;
      target.load();
    };

    // First check after a short delay so the writer has time to append.
    setTimeout(check, 600);
  };

  /**
   * Poll the live progress endpoint: it streams the current stage, percent,
   * frames processed, live joint angles, a streaming risk summary, and the
   * newest annotated (skeleton overlay) frame.
   */
  const startPolling = () => {
    stopPolling();
    const tick = async () => {
      try {
        const response = await videosAPI.getProgress(videoId);
        const p = response.data;
        setProgress(p);

        // As soon as frames have been written, the annotated output is a
        // fragmented MP4 that can be played while it is still being written.
        // Point the player at it now instead of waiting for completion, and
        // keep the URL stable so the browser is not forced to restart.
        if (p.frames_processed > 0) {
          setAnnotatedVideoUrl((current) =>
            current || videosAPI.getAnnotatedVideo(videoId)
          );
        }

        if (p.frames_processed) {
          // Cache-bust image preview asynchronously without blocking progress ticks
          const img = new Image();
          img.onload = () => setPreviewOk(true);
          img.onerror = () => setPreviewOk(false);
          img.src = `${videosAPI.getPreviewFrame(videoId)}&t=${Date.now()}`;
        }

        if (p.status === 'completed') {
          stopPolling();
          setProcessing(false);
          setWaitingForFrames(false);
          await fetchVideo();
          await fetchAnalysis();
          await fetchRisk();
          await fetchComparison();
        } else if (p.status === 'failed') {
          stopPolling();
          setProcessing(false);
          setWaitingForFrames(false);
          setError('Processing failed: ' + (p.error || 'unknown error'));
        }
      } catch (err) {
        // Transient network error — keep polling
      }
    };
    tick();
    pollRef.current = setInterval(tick, 1500);
  };

  const fetchVideo = async () => {
    try {
      const response = await videosAPI.getById(videoId);
      setVideo(response.data);
      const status = response.data.processing_status;

      if (status === 'completed') {
        await fetchAnalysis();
        await fetchRisk();
        await fetchComparison();
      } else if (IN_PROGRESS_STATUSES.includes(status)) {
        // Resume live progress after a page refresh mid-analysis
        setProcessing(true);
        startPolling();
      } else if (status === 'failed') {
        setError('Processing failed: ' + (response.data.processing_error || 'unknown error'));
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to fetch video');
    } finally {
      setLoading(false);
    }
  };

  const fetchAnalysis = async () => {
    try {
      const response = await videosAPI.getAnalysis(videoId);
      setAnalysis(response.data);
      // The annotated video is written during analysis, so it is normally
      // already available — the button below is only a fallback.
      setAnnotatedVideoUrl(videosAPI.getAnnotatedVideo(videoId));
    } catch (err) {
      console.error('Failed to fetch analysis:', err);
    }
  };

  /**
   * Load the comparison against the athlete's rolling baseline. This is the
   * comparison recorded when the analysis completed, so it does not change as
   * the athlete uploads more videos. A 404 simply means the video has no
   * completed analysis yet.
   */
  const fetchComparison = async () => {
    setComparisonLoading(true);
    setComparisonError('');
    try {
      const response = await videosAPI.getComparison(videoId);
      setComparison(response.data);
    } catch (err) {
      if (err.response?.status === 404) {
        setComparison(null);
        setComparisonError('');
      } else {
        const detail = err.response?.data?.detail;
        setComparisonError(
          typeof detail === 'string' ? detail : 'Comparison unavailable.'
        );
      }
    } finally {
      setComparisonLoading(false);
    }
  };

  const fetchRisk = async () => {
    try {
      const response = await videosAPI.getRisk(videoId);
      setRisk(response.data);
    } catch (err) {
      // 404 is expected until pose analysis exists
      if (err.response?.status !== 404) {
        console.error('Failed to fetch risk assessment:', err);
      }
    }
  };

  const handleGenerateAnnotatedVideo = async () => {
    setGeneratingAnnotated(true);
    try {
      await videosAPI.generateAnnotatedVideo(videoId);
      setAnnotatedVideoUrl(videosAPI.getAnnotatedVideo(videoId));
    } catch (err) {
      setError('Failed to generate annotated video: ' + (err.response?.data?.detail || err.message));
    } finally {
      setGeneratingAnnotated(false);
    }
  };

  const prepareChartData = (keypointsData) => {
    if (!keypointsData || !Array.isArray(keypointsData)) return [];

    return keypointsData.map(frame => {
      const kneeKeypoints = frame.keypoints?.filter(kp => kp.name.includes('knee')) || [];
      const hipKeypoints = frame.keypoints?.filter(kp => kp.name.includes('hip')) || [];

      return {
        frame: frame.frame,
        timestamp: frame.timestamp?.toFixed(2),
        knee_y: kneeKeypoints.length > 0 ? kneeKeypoints[0].y : null,
        hip_y: hipKeypoints.length > 0 ? hipKeypoints[0].y : null,
      };
    });
  };

  const handleProcess = async () => {
    setProcessing(true);
    setError('');
    setProgress(null);
    setPreviewOk(false);

    try {
      // Returns immediately — analysis runs in the background on the server
      await videosAPI.process(videoId);
      startPolling();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to start processing');
      setProcessing(false);
    }
  };

  if (loading) {
    return <div className="text-center mt-10">Loading...</div>;
  }

  if (error && !video) {
    return (
      <div className="max-w-2xl mx-auto mt-10 p-6 bg-white rounded-lg shadow-md">
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
        <button
          onClick={() => navigate('/')}
          className="mt-4 text-primary hover:text-primary-hover font-medium hover:underline"
        >
          Go back
        </button>
      </div>
    );
  }

  const showLivePanel = processing || (progress && IN_PROGRESS_STATUSES.includes(progress.status));
  const liveAngles = progress?.current_angles || {};
  const liveRisk = progress?.risk;

  return (
    <div className="w-full mt-4 p-4 sm:p-6 lg:p-8 card border border-border bg-white shadow-sm">
      <h1 className="text-3xl font-display font-bold mb-6 text-text-primary">Video Analysis</h1>

      {error && (
        <div className="bg-error-light border border-error text-error px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {/* Video Information */}
      <div className="mb-6 p-4 bg-surface rounded">
        <h2 className="text-xl font-display font-semibold mb-2 text-text-primary">Video Information</h2>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <strong className="text-text-primary">Filename:</strong> {video.original_filename}
          </div>
          <div>
            <strong className="text-text-primary">Activity:</strong> {video.activity_type}
          </div>
          <div>
            <strong className="text-text-primary">Status:</strong> {video.processing_status}
          </div>
          <div>
            <strong className="text-text-primary">Duration:</strong> {video.duration ? video.duration.toFixed(2) : 'N/A'}s
          </div>
          <div>
            <strong className="text-text-primary">Resolution:</strong> {video.width && video.height ? `${video.width}x${video.height}` : 'N/A'}
          </div>
          <div>
            <strong className="text-text-primary">FPS:</strong> {video.fps ? video.fps.toFixed(2) : 'N/A'}
          </div>
        </div>
      </div>

      {/* Processing Controls */}
      {video.processing_status === 'uploaded' && (
        <div className="mb-6">
          <button
            onClick={handleProcess}
            disabled={processing}
            className="btn-primary disabled:bg-text-muted disabled:cursor-not-allowed"
          >
            {processing ? 'Processing...' : 'Start Analysis'}
          </button>
        </div>
      )}

      {/* Dual Video Synchronized Side-by-Side Comparison (Top of the Analysis) */}
      {video && video.processing_status === 'completed' && (
        <DualVideoPlayer
          trialVideo={video}
          athleteId={video.athlete_id}
          activityType={video.activity_type}
        />
      )}

      {/* Live step-by-step progress while the analysis runs */}
      {showLivePanel && (
        <div className="mb-6 p-5 bg-gradient-to-br from-indigo-50/60 via-white to-slate-50 rounded-2xl border-2 border-indigo-200/80 shadow-md">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2.5">
              <span className="w-3 h-3 rounded-full bg-indigo-600 animate-ping" />
              <h2 className="text-xl font-display font-bold text-gray-900 tracking-tight">
                Live Kinematic Telemetry
              </h2>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-indigo-100 text-indigo-700 uppercase tracking-wider">
                Real-Time Streaming
              </span>
            </div>
            <span className="text-lg font-mono font-bold text-indigo-600">
              {progress?.percent != null ? `${Math.round(progress.percent)}%` : '0%'}
            </span>
          </div>

          <div className="mb-2 flex items-center justify-between text-xs text-gray-600">
            <span className="font-semibold text-gray-800 flex items-center gap-2">
              <span className="inline-block w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
              {progress?.stage_label || 'Initializing pose estimation model...'}
            </span>
            <span className="font-mono text-gray-500">
              {progress?.frames_processed ? `${progress.frames_processed} frames computed` : 'Preparing video stream'}
            </span>
          </div>

          {/* Dynamic Animated Progress Bar */}
          <div className="w-full bg-gray-200 rounded-full h-3.5 mb-4 overflow-hidden relative shadow-inner">
            <div
              className="h-full bg-gradient-to-r from-indigo-500 via-indigo-600 to-amber-500 transition-all duration-300 ease-out"
              style={{ width: `${Math.max(5, Math.min(100, progress?.percent || 5))}%` }}
            />
          </div>

          {/* Metric Telemetry Gauges */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm mb-4">
            <div className="bg-white p-3 rounded-xl border border-gray-200 shadow-sm">
              <div className="text-gray-500 text-[11px] font-medium uppercase tracking-wider">Frames Processed</div>
              <div className="font-display font-bold text-gray-900 text-lg mt-0.5">
                {progress?.frames_processed ?? 0}
                <span className="text-xs font-normal text-gray-400">
                  {progress?.total_frames ? ` / ${progress.total_frames}` : ''}
                </span>
              </div>
            </div>
            <div className="bg-white p-3 rounded-xl border border-gray-200 shadow-sm">
              <div className="text-gray-500 text-[11px] font-medium uppercase tracking-wider">Pose Detected</div>
              <div className="font-display font-bold text-emerald-600 text-lg mt-0.5">
                {progress?.valid_pose_frames ?? 0}
              </div>
            </div>
            <div className="bg-white p-3 rounded-xl border border-gray-200 shadow-sm">
              <div className="text-gray-500 text-[11px] font-medium uppercase tracking-wider">Mean Confidence</div>
              <div className="font-display font-bold text-indigo-600 text-lg mt-0.5">
                {progress?.mean_confidence != null ? `${(progress.mean_confidence * 100).toFixed(1)}%` : '—'}
              </div>
            </div>
            <div className="bg-white p-3 rounded-xl border border-gray-200 shadow-sm">
              <div className="text-gray-500 text-[11px] font-medium uppercase tracking-wider">Pipeline Stage</div>
              <div className="font-display font-bold text-amber-700 text-base mt-0.5 capitalize">
                {progress?.stage?.replace(/_/g, ' ') || 'Starting'}
              </div>
            </div>
          </div>

          {/* Live Joint Angles */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm mb-4">
            <div className="bg-white rounded-xl p-3 border border-gray-200 shadow-sm">
              <div className="text-gray-500 text-[11px] font-medium">Knee Angle</div>
              <div className="font-mono font-bold text-gray-900 text-lg mt-0.5">
                {liveAngles.knee_angle != null ? `${fmt(liveAngles.knee_angle)}°` : '—'}
              </div>
            </div>
            <div className="bg-white rounded-xl p-3 border border-gray-200 shadow-sm">
              <div className="text-gray-500 text-[11px] font-medium">Hip Angle</div>
              <div className="font-mono font-bold text-gray-900 text-lg mt-0.5">
                {liveAngles.hip_angle != null ? `${fmt(liveAngles.hip_angle)}°` : '—'}
              </div>
            </div>
            <div className="bg-white rounded-xl p-3 border border-gray-200 shadow-sm">
              <div className="text-gray-500 text-[11px] font-medium">Trunk Lean</div>
              <div className="font-mono font-bold text-gray-900 text-lg mt-0.5">
                {liveAngles.trunk_lean != null ? `${fmt(liveAngles.trunk_lean)}°` : '—'}
              </div>
            </div>
            <div className="bg-white rounded-xl p-3 border border-gray-200 shadow-sm">
              <div className="text-gray-500 text-[11px] font-medium">Live Risk Score</div>
              <div className="font-mono font-bold text-rose-600 text-lg mt-0.5">
                {liveRisk ? `${fmt(liveRisk.overall_risk_score)} (${liveRisk.risk_level})` : 'Calculating...'}
              </div>
            </div>
          </div>

          {/* Streaming risk findings while frames are processed */}
          {liveRisk && liveRisk.top_findings?.length > 0 && (
            <div className="mb-4 text-sm bg-amber-50/80 rounded-xl p-3.5 border border-amber-200">
              <div className="font-bold mb-1.5 text-amber-950 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-amber-500" />
                Streaming Live Risk Findings ({liveRisk.findings_count})
              </div>
              <ul className="list-disc list-inside text-amber-900 text-xs space-y-1">
                {liveRisk.top_findings.map((issue, idx) => (
                  <li key={idx}>{issue}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Live annotated playback. The annotated output is a fragmented
              MP4, so it is playable while analysis is still running. The
              still-frame preview below is only a fallback for the brief
              window before the first fragment is decodable, or if the
              streaming encoder is unavailable. */}
          {annotatedVideoUrl && progress?.frames_processed > 0 && (
            <div className="mb-2">
              <video
                ref={liveVideoRef}
                key={annotatedVideoUrl}
                src={annotatedVideoUrl}
                className="w-full rounded border border-border bg-black"
                controls
                autoPlay
                muted
                playsInline
                onLoadedData={() => setLivePlayable(true)}
                onError={() => setLivePlayable(false)}
                onEnded={resumeLivePlayback}
              />
              <p className="text-xs text-text-secondary mt-1">
                Live annotated playback — skeleton mapping and tracking, updating
                as the analysis runs
              </p>
              {waitingForFrames && (
                <p className="text-xs text-primary mt-1 flex items-center gap-2">
                  <span className="inline-block w-3 h-3 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                  Caught up with the analysis — waiting for the next frames…
                </p>
              )}
            </div>
          )}

          {/* Fallback still frame, shown only until live video is playing */}
          {!livePlayable && previewOk && progress?.frames_processed > 0 && (
            <div className="mb-2">
              <img
                src={`${videosAPI.getPreviewFrame(videoId)}&t=${progress?.updated_at || ''}`}
                alt="Live skeleton overlay"
                className="w-full rounded border border-border"
                onError={() => setPreviewOk(false)}
              />
              <p className="text-xs text-text-secondary mt-1">
                Live skeleton overlay — playable video starts momentarily
              </p>
            </div>
          )}
        </div>
      )}

      {/* Explainable injury-risk assessment */}
      {risk && (
        <div className="mb-6 p-4 bg-white rounded border-2 border-border">
          <h2 className="text-xl font-display font-semibold mb-3 text-text-primary">Injury Risk Assessment</h2>

          <div className="flex items-center gap-4 mb-4">
            <div className={`px-4 py-3 rounded-lg border text-center ${RISK_LEVEL_STYLES[risk.risk_level] || ''}`}>
              <div className="text-3xl font-display font-bold">{fmt(risk.overall_risk_score)}</div>
              <div className="text-xs font-mono uppercase tracking-wide">/ 100 risk</div>
            </div>
            <div>
              <div className="font-display font-semibold capitalize text-text-primary">{risk.risk_level} risk</div>
              <div className="text-sm text-text-secondary">
                {risk.findings.length} finding{risk.findings.length === 1 ? '' : 's'} from{' '}
                {risk.joints_and_muscles?.length || 0} measured joint angles
              </div>
              {risk.risk_of?.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {risk.risk_of.map((tag) => (
                    <span key={tag} className="text-xs bg-surface text-text-secondary px-2 py-1 rounded">
                      {RISK_TAG_LABELS[tag] || tag}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* How the score was computed */}
          {risk.explanation?.how_score_arrived_at?.length > 0 && (
            <div className="mb-4 p-3 bg-gray-50 rounded">
              <h3 className="font-semibold mb-2">How this score was computed</h3>
              <div className="text-xs font-mono whitespace-pre-wrap text-gray-800">
                {risk.explanation.how_score_arrived_at.join('\n')}
              </div>
            </div>
          )}

          {/* Per-finding explanation with anatomy, predicted injury, stick figures, and recommendations */}
          {risk.findings.length > 0 && (
            <div className="mb-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-2 mb-4 border-b border-gray-200">
                <div>
                  <h3 className="text-xl font-display font-bold text-gray-900">Findings & Injury Risk Explanations</h3>
                  <p className="text-xs text-gray-500 mt-0.5">
                    Biomechanical pathology diagnosis, technical calculations, stick figure movement corrections, and mitigation protocol
                  </p>
                </div>
                <div className="mt-2 sm:mt-0 flex items-center gap-2">
                  <span className="text-xs bg-gray-100 text-gray-700 font-mono px-2.5 py-1 rounded-md font-semibold">
                    {risk.findings.length} Flagged Pattern{risk.findings.length === 1 ? '' : 's'}
                  </span>
                </div>
              </div>

              <div className="space-y-6">
                {risk.findings.map((f, idx) => (
                  <FindingCard
                    key={idx}
                    finding={f}
                    index={idx}
                    activityType={video?.activity_type || 'squat'}
                    keypointsData={analysis?.pose_analysis?.keypoints_data}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Part-by-part joint angles measured, visual gauge vs recommended/normal, and muscles */}
          {risk.joints_and_muscles?.length > 0 && (
            <div className="mb-6 p-5 bg-white rounded-xl border border-gray-200 shadow-sm">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 mb-4 border-b border-gray-100 gap-2">
                <div>
                  <h3 className="text-lg font-display font-bold text-gray-900">
                    Part-by-Part Joint Angles & Normative Comparison
                  </h3>
                  <p className="text-xs text-gray-500">
                    Calculated joint kinematics evaluated against physiological sports medicine thresholds
                  </p>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <span className="inline-flex items-center gap-1 font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">
                    <span className="w-2 h-2 rounded-full bg-emerald-500" /> Optimal Range
                  </span>
                  <span className="inline-flex items-center gap-1 font-semibold text-rose-700 bg-rose-50 px-2 py-0.5 rounded">
                    <span className="w-2 h-2 rounded-full bg-rose-500" /> High Stress Zone
                  </span>
                </div>
              </div>

              {/* Visual Angle Gauges Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mb-5">
                {risk.joints_and_muscles.map((j, idx) => (
                  <AngleGaugeBar
                    key={idx}
                    joint={j.joint}
                    currentVal={j.mean_deg}
                    romVal={j.rom_deg}
                    activity={video?.activity_type || 'squat'}
                  />
                ))}
              </div>

              {/* Detailed Breakdown Table */}
              <div className="overflow-x-auto">
                <table className="min-w-full text-xs text-left">
                  <thead>
                    <tr className="border-b border-gray-200 bg-gray-50/80 text-gray-600 uppercase font-semibold tracking-wider">
                      <th className="py-2.5 px-3">Joint</th>
                      <th className="py-2.5 px-3">Side</th>
                      <th className="py-2.5 px-3">Mean Angle</th>
                      <th className="py-2.5 px-3">Min Angle</th>
                      <th className="py-2.5 px-3">Max Angle</th>
                      <th className="py-2.5 px-3">Range of Motion (ROM)</th>
                      <th className="py-2.5 px-3">Status vs Normal</th>
                      <th className="py-2.5 px-3">Engaged Musculature</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 font-mono">
                    {risk.joints_and_muscles.map((j, idx) => {
                      const isHigh = j.joint === 'trunk' ? (j.mean_deg > 32 || j.max_deg > 40) : false;
                      const isLowRom = j.joint === 'knee' ? (j.rom_deg < 75) : false;

                      return (
                        <tr key={idx} className="hover:bg-gray-50/50 transition-colors">
                          <td className="py-2.5 px-3 capitalize font-sans font-semibold text-gray-900">{j.joint}</td>
                          <td className="py-2.5 px-3 capitalize text-gray-600">{j.side}</td>
                          <td className="py-2.5 px-3 font-bold text-gray-900">{fmt(j.mean_deg)}°</td>
                          <td className="py-2.5 px-3 text-gray-600">{fmt(j.min_deg)}°</td>
                          <td className="py-2.5 px-3 text-gray-600">{fmt(j.max_deg)}°</td>
                          <td className="py-2.5 px-3 font-semibold text-indigo-700">{fmt(j.rom_deg)}°</td>
                          <td className="py-2.5 px-3 font-sans">
                            {isHigh ? (
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-rose-100 text-rose-800">
                                Beyond Normal
                              </span>
                            ) : isLowRom ? (
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-amber-100 text-amber-800">
                                Sub-Optimal ROM
                              </span>
                            ) : (
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-emerald-100 text-emerald-800">
                                Normal Range
                              </span>
                            )}
                          </td>
                          <td className="py-2.5 px-3 font-sans text-gray-600 text-[11px] leading-snug">
                            {(j.muscles_primary || []).join('; ')}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Overall suggestions */}
          {risk.suggestions?.length > 0 && (
            <div className="p-4 bg-emerald-50/80 border border-emerald-200 rounded-xl mb-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="p-1 bg-emerald-200 text-emerald-900 rounded">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </span>
                <h3 className="font-bold text-emerald-950 text-sm">Suggested Solutions & Alternative Movements</h3>
              </div>
              <ul className="grid grid-cols-1 md:grid-cols-2 gap-2 mt-2">
                {risk.suggestions.map((s, idx) => (
                  <li key={idx} className="flex items-start gap-2 bg-white/80 p-2.5 rounded-lg border border-emerald-100 text-xs text-emerald-950 font-medium">
                    <span className="text-emerald-600 font-bold">•</span>
                    <span>{s}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Comparison against the athlete's rolling baseline */}
      {(comparison || comparisonLoading || comparisonError) && (
        <ComparisonPanel
          comparison={comparison}
          loading={comparisonLoading}
          error={comparisonError}
        />
      )}

      {/* Analysis Results */}
      {analysis && analysis.pose_analysis && (
        <div className="mb-6">
          <h2 className="text-xl font-semibold mb-4">Analysis Results</h2>

          {/* 1. Skeleton View Info */}
          <div className="mb-6 p-4 bg-surface-container rounded">
            <h3 className="font-display font-semibold mb-2 text-text-primary">1. Skeleton View</h3>
            <div className="text-sm text-text-secondary">
              <p><strong className="text-text-primary">Athlete Detection:</strong> YOLO11n + ByteTrack tracking</p>
              <p><strong className="text-text-primary">Pose Estimation:</strong> MediaPipe BlazePose (33 landmarks)</p>
              <p><strong className="text-text-primary">Visualization:</strong> Keypoints, skeletal connections, bounding box, tracker ID</p>
              {analysis.pose_analysis.tracking_data && (
                <p><strong className="text-text-primary">Tracking IDs Detected:</strong> {new Set(analysis.pose_analysis.tracking_data.flatMap(t => t.tracked_objects?.map(o => o.track_id) || [])).size}</p>
              )}
            </div>
          </div>

          {/* 3. Pose Quality */}
          <div className="mb-6 p-4 bg-success-light rounded">
            <h3 className="font-display font-semibold mb-2 text-text-primary">3. Pose Quality</h3>
            {analysis.pose_analysis.pose_quality && (
              <div className="grid grid-cols-2 gap-2 text-sm text-text-secondary">
                <div>Valid Frames: {analysis.pose_analysis.pose_quality.valid_frames}</div>
                <div>Quality: {analysis.pose_analysis.pose_quality.quality_percentage?.toFixed(1)}%</div>
                <div>Mean Confidence: {analysis.pose_analysis.pose_quality.mean_confidence?.toFixed(3)}</div>
                <div>Low Confidence Frames: {analysis.pose_analysis.pose_quality.low_confidence_frames}</div>
              </div>
            )}
          </div>

          {/* 4. Movement Windows */}
          {analysis.pose_analysis.movement_windows && analysis.pose_analysis.movement_windows.length > 0 && (
            <div className="mb-6 p-4 bg-orange-50 rounded">
              <h3 className="font-semibold mb-2">4. Movement Windows</h3>
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="py-2">Rep/Phase</th>
                      <th className="py-2">Start</th>
                      <th className="py-2">End</th>
                      <th className="py-2">Duration</th>
                      <th className="py-2">Phase</th>
                    </tr>
                  </thead>
                  <tbody>
                    {analysis.pose_analysis.movement_windows.map((window, idx) => (
                      <tr key={idx} className="border-b">
                        <td className="py-2">
                          {window.repetition_number ? `Rep ${window.repetition_number}` :
                           window.jump_number ? `Jump ${window.jump_number}` :
                           window.stride_number ? `Stride ${window.stride_number}` : '-'}
                        </td>
                        <td className="py-2">{window.start_time?.toFixed(2)}s</td>
                        <td className="py-2">{window.end_time?.toFixed(2)}s</td>
                        <td className="py-2">{window.duration?.toFixed(2)}s</td>
                        <td className="py-2">{window.phase}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* 5. Biomechanics */}
          {analysis.biomechanical_analysis && (
            <div className="mb-6 p-4 bg-purple-50 rounded">
              <h3 className="font-semibold mb-2">5. Biomechanics</h3>

              {analysis.biomechanical_analysis.joint_angles && (
                <div className="mb-3">
                  <h4 className="font-medium">Range of Motion</h4>
                  <div className="text-sm mt-1">
                    {analysis.biomechanical_analysis.joint_angles.knee_left && (
                      <div>Left Knee: {analysis.biomechanical_analysis.joint_angles.knee_left.rom?.toFixed(1)}°</div>
                    )}
                    {analysis.biomechanical_analysis.joint_angles.knee_right && (
                      <div>Right Knee: {analysis.biomechanical_analysis.joint_angles.knee_right.rom?.toFixed(1)}°</div>
                    )}
                    {analysis.biomechanical_analysis.joint_angles.hip_left && (
                      <div>Left Hip: {analysis.biomechanical_analysis.joint_angles.hip_left.rom?.toFixed(1)}°</div>
                    )}
                    {analysis.biomechanical_analysis.joint_angles.hip_right && (
                      <div>Right Hip: {analysis.biomechanical_analysis.joint_angles.hip_right.rom?.toFixed(1)}°</div>
                    )}
                  </div>
                </div>
              )}

              {analysis.biomechanical_analysis.symmetry && (
                <div className="mb-3">
                  <h4 className="font-medium">Symmetry</h4>
                  <div className="text-sm mt-1">
                    <div>Knee Asymmetry: {analysis.biomechanical_analysis.symmetry.knee_asymmetry?.mean_asymmetry?.toFixed(2)}°</div>
                    <div>Hip Asymmetry: {analysis.biomechanical_analysis.symmetry.hip_asymmetry?.mean_asymmetry?.toFixed(2)}°</div>
                  </div>
                </div>
              )}

              {analysis.biomechanical_analysis.trunk_lean && (
                <div className="mb-3">
                  <h4 className="font-medium">Trunk Lean</h4>
                  <div className="text-sm mt-1">
                    <div>Mean: {analysis.biomechanical_analysis.trunk_lean.mean?.toFixed(2)}°</div>
                    <div>Max: {analysis.biomechanical_analysis.trunk_lean.max?.toFixed(2)}°</div>
                    <div>Min: {analysis.biomechanical_analysis.trunk_lean.min?.toFixed(2)}°</div>
                  </div>
                </div>
              )}

              {analysis.biomechanical_analysis.velocity && (
                <div className="mb-3">
                  <h4 className="font-medium">Velocity</h4>
                  <div className="text-sm mt-1">
                    <div>Knee Mean: {analysis.biomechanical_analysis.velocity.knee_mean?.toFixed(2)}°/s</div>
                    <div>Knee Max: {analysis.biomechanical_analysis.velocity.knee_max?.toFixed(2)}°/s</div>
                  </div>
                </div>
              )}

              {analysis.biomechanical_analysis.acceleration && (
                <div className="mb-3">
                  <h4 className="font-medium">Acceleration</h4>
                  <div className="text-sm mt-1">
                    <div>Knee Mean: {analysis.biomechanical_analysis.acceleration.knee_mean?.toFixed(2)}°/s²</div>
                    <div>Knee Max: {analysis.biomechanical_analysis.acceleration.knee_max?.toFixed(2)}°/s²</div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* 6. Charts */}
          {analysis.pose_analysis.keypoints_data && (
            <div className="mb-6 p-4 bg-indigo-50 rounded">
              <h3 className="font-semibold mb-2">6. Time-Series Charts</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={prepareChartData(analysis.pose_analysis.keypoints_data)}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="frame" label={{ value: 'Frame', position: 'insideBottom', offset: -5 }} />
                    <YAxis label={{ value: 'Y Position', angle: -90, position: 'insideLeft' }} />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="knee_y" stroke="#8884d8" name="Knee Y" dot={false} />
                    <Line type="monotone" dataKey="hip_y" stroke="#82ca9d" name="Hip Y" dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <p className="text-xs text-gray-600 mt-2">Keypoint vertical trajectory over time</p>
            </div>
          )}

          {/* 7. Movement Quality */}
          {analysis.biomechanical_analysis?.movement_quality && (
            <div className="mb-6 p-4 bg-teal-50 rounded">
              <h3 className="font-semibold mb-2">7. Movement Quality</h3>
              <div className="text-sm mb-2">
                <strong>Overall Score:</strong> {analysis.biomechanical_analysis.movement_quality.score?.toFixed(1)}/100
              </div>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>Confidence: {analysis.biomechanical_analysis.movement_quality.components?.confidence?.toFixed(1)}</div>
                <div>Symmetry: {analysis.biomechanical_analysis.movement_quality.components?.symmetry?.toFixed(1)}</div>
                <div>Alignment: {analysis.biomechanical_analysis.movement_quality.components?.alignment?.toFixed(1)}</div>
                <div>Stability: {analysis.biomechanical_analysis.movement_quality.components?.stability?.toFixed(1)}</div>
                <div>ROM: {analysis.biomechanical_analysis.movement_quality.components?.rom?.toFixed(1)}</div>
                <div>Smoothness: {analysis.biomechanical_analysis.movement_quality.components?.smoothness?.toFixed(1)}</div>
              </div>
              {analysis.biomechanical_analysis.movement_quality.raw_measurements && (
                <div className="mt-2 text-xs text-gray-600">
                  <p>Raw Measurements:</p>
                  <p>Mean Left Knee: {analysis.biomechanical_analysis.movement_quality.raw_measurements.mean_left_knee?.toFixed(1)}°</p>
                  <p>Mean Right Knee: {analysis.biomechanical_analysis.movement_quality.raw_measurements.mean_right_knee?.toFixed(1)}°</p>
                  <p>Max Trunk Lean: {analysis.biomechanical_analysis.movement_quality.raw_measurements.max_trunk_lean?.toFixed(1)}°</p>
                </div>
              )}
            </div>
          )}

          {/* 8. Movement-Change Analysis */}
          {analysis.pose_analysis.movement_change_analysis && analysis.pose_analysis.movement_change_analysis.status === 'success' && (
            <div className="mb-6 p-4 bg-pink-50 rounded">
              <h3 className="font-semibold mb-2">8. Movement-Change Analysis (Early vs Late)</h3>
              <p className="text-xs text-gray-600 mb-2">
                Note: This is a movement-change indicator, NOT a medical fatigue diagnosis.
              </p>
              <div className="text-sm mb-2">
                <strong>Total Repetitions:</strong> {analysis.pose_analysis.movement_change_analysis.total_repetitions}
                <span className="ml-4">Early: {analysis.pose_analysis.movement_change_analysis.early_count}</span>
                <span className="ml-4">Late: {analysis.pose_analysis.movement_change_analysis.late_count}</span>
              </div>
              {analysis.pose_analysis.movement_change_analysis.early_vs_late_comparison && (
                <div className="text-sm">
                  <h4 className="font-medium mt-2">Key Changes:</h4>
                  {analysis.pose_analysis.movement_change_analysis.early_vs_late_comparison.rom_mean && (
                    <div>ROM: {analysis.pose_analysis.movement_change_analysis.early_vs_late_comparison.rom_mean.direction}
                      ({analysis.pose_analysis.movement_change_analysis.early_vs_late_comparison.rom_mean.percentage_change?.toFixed(1)}%)</div>
                  )}
                  {analysis.pose_analysis.movement_change_analysis.early_vs_late_comparison.symmetry_mean && (
                    <div>Symmetry: {analysis.pose_analysis.movement_change_analysis.early_vs_late_comparison.symmetry_mean.direction}
                      ({analysis.pose_analysis.movement_change_analysis.early_vs_late_comparison.symmetry_mean.percentage_change?.toFixed(1)}%)</div>
                  )}
                  {analysis.pose_analysis.movement_change_analysis.early_vs_late_comparison.trunk_lean_mean && (
                    <div>Trunk Lean: {analysis.pose_analysis.movement_change_analysis.early_vs_late_comparison.trunk_lean_mean.direction}
                      ({analysis.pose_analysis.movement_change_analysis.early_vs_late_comparison.trunk_lean_mean.percentage_change?.toFixed(1)}%)</div>
                  )}
                </div>
              )}
            </div>
          )}

          <div className="mt-4 p-4 bg-yellow-50 rounded text-sm">
            <strong>Disclaimer:</strong> This system provides biomechanical movement analysis and injury-risk
            indicators with suggested corrective actions. It is not a medical diagnosis.
          </div>
        </div>
      )}

      <button
        onClick={() => navigate('/')}
        className="text-primary hover:text-primary-hover font-medium hover:underline"
      >
        ← Back to Dashboard
      </button>
    </div>
  );
}

export default VideoAnalysis;
