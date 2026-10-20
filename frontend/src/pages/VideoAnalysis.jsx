import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { videosAPI } from '../services/api';
import ComparisonPanel from '../components/ComparisonPanel';
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
  const [showAnnotated, setShowAnnotated] = useState(true);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [generatingAnnotated, setGeneratingAnnotated] = useState(false);
  const [error, setError] = useState('');
  const pollRef = useRef(null);

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

        if (p.frames_processed) {
          // Cache-bust so the <img> always shows the newest frame
          await new Promise((resolve) => {
            const img = new Image();
            img.onload = () => {
              setPreviewOk(true);
              resolve();
            };
            img.onerror = () => {
              setPreviewOk(false);
              resolve();
            };
            img.src = `${videosAPI.getPreviewFrame(videoId)}&t=${Date.now()}`;
          });
        }

        if (p.status === 'completed') {
          stopPolling();
          setProcessing(false);
          await fetchVideo();
          await fetchAnalysis();
          await fetchRisk();
          await fetchComparison();
        } else if (p.status === 'failed') {
          stopPolling();
          setProcessing(false);
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
          className="mt-4 text-blue-500 hover:underline"
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
    <div className="max-w-4xl mx-auto mt-10 p-6 card">
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

      {/* Live step-by-step progress while the analysis runs */}
      {showLivePanel && (
        <div className="mb-6 p-4 bg-surface-container rounded border border-border">
          <h2 className="text-xl font-display font-semibold mb-2 text-text-primary">Live Analysis</h2>

          <div className="mb-2 flex items-center justify-between text-sm">
            <span className="font-medium text-text-primary">
              {progress?.stage_label || 'Starting analysis...'}
            </span>
            <span className="text-text-secondary font-mono">{fmt(progress?.percent, 0)}%</span>
          </div>
          <div className="w-full bg-border-muted rounded-lg h-4 mb-3 overflow-hidden relative">
            <div
              className="bg-primary h-full transition-all duration-500 ease-out"
              style={{ width: `${Math.max(0, Math.min(100, progress?.percent || 0))}%` }}
            />
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-xs font-mono font-semibold text-white mix-blend-difference">
                {fmt(progress?.percent, 0)}%
              </span>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm mb-3">
            <div>
              <div className="text-text-secondary text-xs">Frames</div>
              <div className="font-medium text-text-primary">
                {progress?.frames_processed ?? 0}
                {progress?.total_frames ? ` / ${progress.total_frames}` : ''}
              </div>
            </div>
            <div>
              <div className="text-text-secondary text-xs">Pose detected</div>
              <div className="font-medium text-text-primary">{progress?.valid_pose_frames ?? 0}</div>
            </div>
            <div>
              <div className="text-text-secondary text-xs">Mean confidence</div>
              <div className="font-medium text-text-primary">{fmt(progress?.mean_confidence, 3)}</div>
            </div>
            <div>
              <div className="text-text-secondary text-xs">Stage</div>
              <div className="font-medium text-text-primary">{progress?.stage || '—'}</div>
            </div>
          </div>

          {/* Live joint angles */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm mb-3">
            <div className="bg-white rounded p-2 border border-border">
              <div className="text-text-secondary text-xs">Left knee</div>
              <div className="font-medium text-text-primary">{fmt(liveAngles.knee_angle)}°</div>
            </div>
            <div className="bg-white rounded p-2 border border-border">
              <div className="text-text-secondary text-xs">Hip angle</div>
              <div className="font-medium text-text-primary">{fmt(liveAngles.hip_angle)}°</div>
            </div>
            <div className="bg-white rounded p-2 border border-border">
              <div className="text-text-secondary text-xs">Trunk lean</div>
              <div className="font-medium text-text-primary">{fmt(liveAngles.trunk_lean)}°</div>
            </div>
            <div className="bg-white rounded p-2 border border-border">
              <div className="text-text-secondary text-xs">Live risk</div>
              <div className="font-medium text-text-primary">
                {liveRisk ? `${fmt(liveRisk.overall_risk_score)} (${liveRisk.risk_level})` : '—'}
              </div>
            </div>
          </div>

          {/* Streaming risk findings while frames are processed */}
          {liveRisk && liveRisk.top_findings?.length > 0 && (
            <div className="mb-3 text-sm bg-white rounded p-2 border border-border">
              <div className="font-medium mb-1 text-text-primary">
                Streaming risk findings ({liveRisk.findings_count})
              </div>
              <ul className="list-disc list-inside text-text-secondary">
                {liveRisk.top_findings.map((issue, idx) => (
                  <li key={idx}>{issue}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Live skeleton overlay */}
          {previewOk && progress?.frames_processed > 0 && (
            <div className="mb-2">
              <img
                src={`${videosAPI.getPreviewFrame(videoId)}&t=${progress?.updated_at || ''}`}
                alt="Live skeleton overlay"
                className="w-full rounded border border-border"
                onError={() => setPreviewOk(false)}
              />
              <p className="text-xs text-text-secondary mt-1">
                Live skeleton overlay — updated as each chunk is processed
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

          {/* Per-finding explanation with anatomy and recommendations */}
          {risk.findings.length > 0 && (
            <div className="mb-4">
              <h3 className="font-semibold mb-2">Findings explained</h3>
              <div className="space-y-3">
                {risk.findings.map((f, idx) => (
                  <div key={idx} className="p-3 border rounded">
                    <div className="flex items-start justify-between gap-2">
                      <div className="font-medium">{f.issue}</div>
                      <span className={`text-xs px-2 py-1 rounded border capitalize ${SEVERITY_STYLES[f.severity] || ''}`}>
                        {f.severity}
                      </span>
                    </div>

                    {f.body_parts?.length > 0 && (
                      <div className="text-xs text-gray-600 mt-1">
                        Body parts: {f.body_parts.join(', ')}
                      </div>
                    )}

                    <p className="text-sm mt-2">{f.rationale}</p>

                    {f.scientific_term && (
                      <p className="text-sm mt-2">
                        <span className="font-medium">Clinical term:</span> {f.scientific_term}
                      </p>
                    )}

                    {f.structures_at_risk?.length > 0 && (
                      <p className="text-sm mt-1">
                        <span className="font-medium">Structures at risk:</span>{' '}
                        {f.structures_at_risk.join('; ')}
                      </p>
                    )}

                    {f.muscles?.primary?.length > 0 && (
                      <p className="text-sm mt-1">
                        <span className="font-medium">Muscles involved:</span>{' '}
                        {f.muscles.primary.join('; ')}
                      </p>
                    )}
                    {f.muscles?.stabilizers?.length > 0 && (
                      <p className="text-sm mt-1">
                        <span className="font-medium">Stabilisers:</span>{' '}
                        {f.muscles.stabilizers.join('; ')}
                      </p>
                    )}
                    {f.muscles_overactive?.length > 0 && (
                      <p className="text-sm mt-1 text-orange-800">
                        <span className="font-medium">Overactive:</span> {f.muscles_overactive.join('; ')}
                      </p>
                    )}
                    {f.muscles_underactive?.length > 0 && (
                      <p className="text-sm mt-1 text-blue-800">
                        <span className="font-medium">Underactive:</span> {f.muscles_underactive.join('; ')}
                      </p>
                    )}

                    {f.mechanism && (
                      <p className="text-sm mt-2 text-gray-700">
                        <span className="font-medium">Why this matters:</span> {f.mechanism}
                      </p>
                    )}

                    {f.evidence?.length > 0 && (
                      <div className="mt-2">
                        <div className="text-xs font-medium text-gray-600 mb-1">Measurements</div>
                        <table className="text-xs w-full">
                          <tbody>
                            {f.evidence.map((e, i) => (
                              <tr key={i} className="border-b">
                                <td className="py-1 text-gray-600">{e.metric.replace(/_/g, ' ')}</td>
                                <td className="py-1 text-right font-mono">
                                  {typeof e.value === 'number' ? e.value : '—'} {e.unit}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}

                    {f.recommended_actions?.length > 0 && (
                      <div className="mt-2">
                        <div className="text-xs font-medium text-gray-600">Recommended actions</div>
                        <ul className="list-disc list-inside text-sm">
                          {f.recommended_actions.map((a, i) => (
                            <li key={i}>{a}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Joint angles measured and the muscles that act on them */}
          {risk.joints_and_muscles?.length > 0 && (
            <div className="mb-4">
              <h3 className="font-semibold mb-2">Joints, angles and muscles</h3>
              <div className="overflow-x-auto">
                <table className="min-w-full text-xs">
                  <thead>
                    <tr className="border-b text-left">
                      <th className="py-1 pr-3">Joint</th>
                      <th className="py-1 pr-3">Side</th>
                      <th className="py-1 pr-3">Mean</th>
                      <th className="py-1 pr-3">Min</th>
                      <th className="py-1 pr-3">Max</th>
                      <th className="py-1 pr-3">ROM</th>
                      <th className="py-1">Muscles</th>
                    </tr>
                  </thead>
                  <tbody>
                    {risk.joints_and_muscles.map((j, idx) => (
                      <tr key={idx} className="border-b align-top">
                        <td className="py-1 pr-3 capitalize">{j.joint}</td>
                        <td className="py-1 pr-3">{j.side}</td>
                        <td className="py-1 pr-3">{fmt(j.mean_deg)}°</td>
                        <td className="py-1 pr-3">{fmt(j.min_deg)}°</td>
                        <td className="py-1 pr-3">{fmt(j.max_deg)}°</td>
                        <td className="py-1 pr-3">{fmt(j.rom_deg)}°</td>
                        <td className="py-1 text-gray-700">
                          {(j.muscles_primary || []).join('; ')}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Overall suggestions */}
          {risk.suggestions?.length > 0 && (
            <div className="p-3 bg-green-50 rounded">
              <h3 className="font-semibold mb-1">Suggested solutions / alternative movements</h3>
              <ul className="list-disc list-inside text-sm">
                {risk.suggestions.map((s, idx) => (
                  <li key={idx}>{s}</li>
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

          {/* 1. Video Player with Annotated Video */}
          <div className="mb-6 p-4 bg-surface rounded">
            <h3 className="font-display font-semibold mb-2 text-text-primary">1. Video Player</h3>

            {/* Toggle between original and annotated video */}
            {annotatedVideoUrl && (
              <div className="mb-3 flex gap-2">
                <button
                  onClick={() => setShowAnnotated(true)}
                  className={`px-3 py-1 rounded text-sm ${showAnnotated ? 'btn-primary' : 'btn-secondary'}`}
                >
                  Annotated (Skeleton)
                </button>
                <button
                  onClick={() => setShowAnnotated(false)}
                  className={`px-3 py-1 rounded text-sm ${!showAnnotated ? 'btn-primary' : 'btn-secondary'}`}
                >
                  Original
                </button>
              </div>
            )}

            {showAnnotated && annotatedVideoUrl ? (
              <div>
                <video
                  controls
                  className="w-full rounded border border-border"
                  src={annotatedVideoUrl}
                  onError={() => {
                    console.error('Annotated video failed to load, switching to original');
                    setShowAnnotated(false);
                  }}
                >
                  Your browser does not support the video tag.
                </video>
                <p className="text-sm text-success mt-2">✓ Annotated video with pose estimation visualization</p>
              </div>
            ) : video?.file_path ? (
              <div>
                <video
                  controls
                  className="w-full rounded border border-border"
                  src={videosAPI.getVideoUrl(videoId)}
                >
                  Your browser does not support the video tag.
                </video>
                <p className="text-sm text-text-secondary mt-2">Original video</p>
              </div>
            ) : generatingAnnotated ? (
              <div className="text-center py-4">
                <p className="text-primary">Generating annotated video with pose visualization...</p>
                <p className="text-sm text-text-secondary mt-2">This may take a moment for large videos</p>
              </div>
            ) : (
              <div className="text-center py-4">
                <p className="text-text-secondary mb-2">Annotated video not available for this run</p>
                <button
                  onClick={handleGenerateAnnotatedVideo}
                  className="btn-primary"
                >
                  Generate Annotated Video
                </button>
                <p className="text-sm text-text-secondary mt-2">
                  Annotated video includes skeleton visualization, bounding boxes, and biomechanical measurements
                </p>
              </div>
            )}
          </div>

          {/* 2. Skeleton View Info */}
          <div className="mb-6 p-4 bg-surface-container rounded">
            <h3 className="font-display font-semibold mb-2 text-text-primary">2. Skeleton View</h3>
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
        className="text-blue-500 hover:underline"
      >
        Back to Dashboard
      </button>
    </div>
  );
}

export default VideoAnalysis;
