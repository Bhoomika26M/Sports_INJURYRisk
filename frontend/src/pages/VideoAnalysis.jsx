import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { videosAPI } from '../services/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

function VideoAnalysis() {
  const { videoId } = useParams();
  const navigate = useNavigate();
  const [video, setVideo] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [annotatedVideoUrl, setAnnotatedVideoUrl] = useState(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchVideo();
  }, [videoId]);

  const fetchVideo = async () => {
    try {
      const response = await videosAPI.getById(videoId);
      setVideo(response.data);
      
      if (response.data.processing_status === 'completed') {
        fetchAnalysis();
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
      
      // Try to get annotated video URL
      setAnnotatedVideoUrl(videosAPI.getAnnotatedVideo(videoId));
    } catch (err) {
      console.error('Failed to fetch analysis:', err);
    }
  };

  const handleGenerateAnnotatedVideo = async () => {
    try {
      await videosAPI.generateAnnotatedVideo(videoId);
      setAnnotatedVideoUrl(videosAPI.getAnnotatedVideo(videoId));
    } catch (err) {
      setError('Failed to generate annotated video: ' + (err.response?.data?.detail || err.message));
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
    
    try {
      await videosAPI.process(videoId);
      // Poll for completion
      const interval = setInterval(async () => {
        const response = await videosAPI.getById(videoId);
        setVideo(response.data);
        
        if (response.data.processing_status === 'completed') {
          clearInterval(interval);
          setProcessing(false);
          fetchAnalysis();
        } else if (response.data.processing_status === 'failed') {
          clearInterval(interval);
          setProcessing(false);
          setError('Processing failed: ' + response.data.processing_error);
        }
      }, 2000);
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

  return (
    <div className="max-w-4xl mx-auto mt-10 p-6 bg-white rounded-lg shadow-md">
      <h1 className="text-3xl font-bold mb-6">Video Analysis</h1>
      
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}
      
      {/* Video Information */}
      <div className="mb-6 p-4 bg-gray-50 rounded">
        <h2 className="text-xl font-semibold mb-2">Video Information</h2>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <strong>Filename:</strong> {video.original_filename}
          </div>
          <div>
            <strong>Activity:</strong> {video.activity_type}
          </div>
          <div>
            <strong>Status:</strong> {video.processing_status}
          </div>
          <div>
            <strong>Duration:</strong> {video.duration ? video.duration.toFixed(2) : 'N/A'}s
          </div>
          <div>
            <strong>Resolution:</strong> {video.width && video.height ? `${video.width}x${video.height}` : 'N/A'}
          </div>
          <div>
            <strong>FPS:</strong> {video.fps ? video.fps.toFixed(2) : 'N/A'}
          </div>
        </div>
      </div>
      
      {/* Processing Controls */}
      {video.processing_status === 'uploaded' && (
        <div className="mb-6">
          <button
            onClick={handleProcess}
            disabled={processing}
            className="bg-blue-500 text-white py-2 px-4 rounded-lg hover:bg-blue-600 disabled:bg-gray-400"
          >
            {processing ? 'Processing...' : 'Start Analysis'}
          </button>
        </div>
      )}
      
      {processing && (
        <div className="mb-6 p-4 bg-blue-50 rounded">
          <p className="text-blue-700">Processing video... This may take several minutes.</p>
        </div>
      )}
      
      {/* Analysis Results */}
      {analysis && analysis.pose_analysis && (
        <div className="mb-6">
          <h2 className="text-xl font-semibold mb-4">Analysis Results</h2>
          
          {/* 1. Video Player with Annotated Video */}
          <div className="mb-6 p-4 bg-gray-50 rounded">
            <h3 className="font-semibold mb-2">1. Video Player</h3>
            {annotatedVideoUrl ? (
              <video
                controls
                className="w-full rounded"
                src={annotatedVideoUrl}
              >
                Your browser does not support the video tag.
              </video>
            ) : (
              <div className="text-center py-4">
                <button
                  onClick={handleGenerateAnnotatedVideo}
                  className="bg-green-500 text-white py-2 px-4 rounded-lg hover:bg-green-600"
                >
                  Generate Annotated Video
                </button>
                <p className="text-sm text-gray-600 mt-2">
                  Annotated video includes skeleton visualization, bounding boxes, and biomechanical measurements
                </p>
              </div>
            )}
          </div>
          
          {/* 2. Skeleton View Info */}
          <div className="mb-6 p-4 bg-blue-50 rounded">
            <h3 className="font-semibold mb-2">2. Skeleton View</h3>
            <div className="text-sm">
              <p><strong>Athlete Detection:</strong> YOLO11n + ByteTrack tracking</p>
              <p><strong>Pose Estimation:</strong> MediaPipe BlazePose (33 landmarks)</p>
              <p><strong>Visualization:</strong> Keypoints, skeletal connections, bounding box, tracker ID</p>
              {analysis.pose_analysis.tracking_data && (
                <p><strong>Tracking IDs Detected:</strong> {new Set(analysis.pose_analysis.tracking_data.flatMap(t => t.tracked_objects?.map(o => o.track_id) || [])).size}</p>
              )}
            </div>
          </div>
          
          {/* 3. Pose Quality */}
          <div className="mb-6 p-4 bg-green-50 rounded">
            <h3 className="font-semibold mb-2">3. Pose Quality</h3>
            {analysis.pose_analysis.pose_quality && (
              <div className="grid grid-cols-2 gap-2 text-sm">
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
            <strong>Disclaimer:</strong> This system provides biomechanical movement analysis and is not a medical diagnosis.
            Injury-risk prediction will be available in the next milestone.
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
