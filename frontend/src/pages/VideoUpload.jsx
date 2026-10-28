import React, { useState, useRef, useEffect } from 'react';
import api from '../api/client';
import { useAuth } from '../context/AuthContext';
import { BiomechanicsReport } from '../components/BiomechanicsReport';
import { AssessmentReport } from '../components/AssessmentReport';
import { AnomalyReport } from '../components/AnomalyReport';
import { RecommendationPanel } from '../components/RecommendationPanel';
import { 
  Upload, 
  Film, 
  CheckCircle2, 
  AlertCircle, 
  Clock, 
  ChevronDown, 
  ChevronUp, 
  Play, 
  Sparkles,
  Layers,
  Activity,
  FileText,
  Trash2,
  Gauge,
  Sliders,
  Check,
  Zap,
  ShieldCheck,
  ShieldAlert
} from 'lucide-react';

const MOVEMENT_PATTERNS = [
  { id: 'squatting', label: 'Squatting', icon: '🏋️', desc: 'Bilateral knee flexion, hip symmetry, valgus collapse' },
  { id: 'running', label: 'Running Gait', icon: '🏃', desc: 'Step frequency, heel-strike, pelvic stability' },
  { id: 'sprinting', label: 'Sprinting', icon: '⚡', desc: 'High velocity acceleration, hamstring extension' },
  { id: 'landing', label: 'Drop Landing', icon: '🦘', desc: 'Ground reaction absorption, knee abduction moments' },
  { id: 'jumping', label: 'Countermovement Jump', icon: '⬆️', desc: 'Vertical propulsion, takeoff & landing kinematics' },
  { id: 'cutting', label: 'Cutting / Agility', icon: '🔄', desc: 'Deceleration, plant-and-cut valgus angles' },
  { id: 'throwing', label: 'Throwing / Upper Body', icon: '⚾', desc: 'Shoulder angular velocity, trunk rotation' },
  { id: 'general', label: 'General Movement Drill', icon: '⚽', desc: 'General athletic screening' }
];

export const VideoUpload = () => {
  const { user } = useAuth();
  const [file, setFile] = useState(null);
  const [movementType, setMovementType] = useState('squatting');
  const [uploadProgress, setUploadProgress] = useState(0);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [athleteId, setAthleteId] = useState('');
  const [videos, setVideos] = useState([]);
  const [expandedVideo, setExpandedVideo] = useState(null);
  const [activeAnalysisTab, setActiveAnalysisTab] = useState('video');
  const [landmarksData, setLandmarksData] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1.0);
  const [deletingId, setDeletingId] = useState(null);
  
  const fileInputRef = useRef(null);
  const playbackVideoRef = useRef(null);

  // Dynamic uploads URL resolver
  const uploadsBaseUrl = import.meta.env.VITE_API_URL 
    ? import.meta.env.VITE_API_URL.replace('/api/v1', '').replace(/\/$/, '') 
    : 'http://localhost:8000';

  useEffect(() => {
    const fetchAthleteData = async () => {
      try {
        if (user?.role === 'athlete') {
          const profileRes = await api.get('/athletes/me');
          if (profileRes.data) {
            setAthleteId(profileRes.data.id);
            fetchVideos(profileRes.data.id);
          }
        }
      } catch (_err) {
        console.error("Athlete profile not found.");
      }
    };
    fetchAthleteData();
  }, [user]);

  const fetchVideos = async (id) => {
    try {
      const res = await api.get(`/videos/athlete/${id}`);
      setVideos(res.data);
    } catch (err) {
      console.error("Error fetching videos:", err);
    }
  };

  // Poll processing videos and update progress percentage
  useEffect(() => {
    let intervalId;
    const hasProcessing = videos.some(v => v.status === 'uploaded' || v.status === 'processing');
    if (hasProcessing && athleteId) {
      intervalId = setInterval(async () => {
        try {
          const res = await api.get(`/videos/athlete/${athleteId}`);
          setVideos(res.data);
        } catch (_e) {
          // ignore
        }
      }, 2500);
    }
    return () => clearInterval(intervalId);
  }, [videos, athleteId]);

  const handleSpeedChange = (speed) => {
    setPlaybackSpeed(speed);
    if (playbackVideoRef.current) {
      playbackVideoRef.current.playbackRate = speed;
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const validateAndSetFile = (selectedFile) => {
    setError('');
    setMessage('');
    setUploadProgress(0);

    const validExtensions = ['.mp4', '.mov', '.avi', '.webm'];
    const ext = '.' + selectedFile.name.split('.').pop().toLowerCase();
    
    if (!validExtensions.includes(ext)) {
      setError(`Unsupported format (${ext}). Please select an MP4, MOV, AVI, or WEBM video file.`);
      setFile(null);
      return;
    }

    const maxBytes = 100 * 1024 * 1024; // 100MB
    if (selectedFile.size > maxBytes) {
      setError(`File size (${(selectedFile.size / (1024 * 1024)).toFixed(1)}MB) exceeds the 100MB limit. Please compress or trim the clip.`);
      setFile(null);
      return;
    }

    if (selectedFile.size === 0) {
      setError('Selected file is empty (0 bytes).');
      setFile(null);
      return;
    }

    setFile(selectedFile);
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return setError('Please select a video file.');
    if (!athleteId) return setError('Athlete Profile not found. Please create an athlete profile first.');

    const formData = new FormData();
    formData.append('file', file);
    formData.append('athlete_id', athleteId);
    formData.append('movement_type', movementType);

    try {
      setMessage('');
      setError('');
      
      await api.post('/videos/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setUploadProgress(percentCompleted);
          }
        }
      });
      
      setMessage('Video uploaded successfully. MediaPipe Pose Estimation & kinematic tracking is underway!');
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      fetchVideos(athleteId);
    } catch (err) {
      setUploadProgress(0);
      setError(err.response?.data?.detail || 'Failed to upload video');
    }
  };

  const handleDeleteVideo = async (videoId) => {
    if (!window.confirm('Are you sure you want to delete this movement trial and all generated biomechanical analysis?')) {
      return;
    }
    try {
      setDeletingId(videoId);
      await api.delete(`/videos/${videoId}`);
      if (expandedVideo?.id === videoId) {
        setExpandedVideo(null);
      }
      fetchVideos(athleteId);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to delete video');
    } finally {
      setDeletingId(null);
    }
  };

  const toggleVideoView = async (v) => {
    if (expandedVideo?.id === v.id) {
      setExpandedVideo(null);
      setLandmarksData(null);
    } else {
      setExpandedVideo(v);
      setActiveAnalysisTab('video');
      setLandmarksData(null);
      if (v.status === 'completed') {
        try {
          const res = await api.get(`/videos/${v.id}/landmarks`);
          setLandmarksData(res.data);
        } catch (e) {
          console.error("Could not fetch landmarks JSON", e);
        }
      }
    }
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-5xl mx-auto space-y-6">
      {/* Page Title */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
          <span>Movement Video Analysis</span>
        </h1>
        <p className="text-slate-500 text-xs mt-0.5">
          Automated MediaPipe Pose Estimation, 33-landmark tracking, joint kinematics, and clinical risk evaluation.
        </p>
      </div>

      {/* Upload Box */}
      <div className="bg-white p-6 sm:p-8 rounded-2xl shadow-xs border border-slate-200">
        {!athleteId ? (
          <div className="bg-amber-50 text-amber-800 p-4 rounded-xl border border-amber-200 text-xs flex items-center gap-2">
            <AlertCircle size={16} className="shrink-0" />
            <span>Please complete your athlete physical profile before uploading movement recordings.</span>
          </div>
        ) : (
          <form onSubmit={handleUpload} className="space-y-5">
            {message && (
              <div className="bg-emerald-50 text-emerald-800 p-3.5 rounded-xl border border-emerald-200 text-xs flex items-center gap-2">
                <CheckCircle2 size={16} className="text-emerald-600 shrink-0" />
                <span>{message}</span>
              </div>
            )}
            {error && (
              <div className="bg-red-50 text-red-700 p-3.5 rounded-xl border border-red-200 text-xs flex items-center gap-2">
                <AlertCircle size={16} className="shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {/* Movement Pattern Selector */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
                1. Select Movement Pattern
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {MOVEMENT_PATTERNS.map((p) => {
                  const isSelected = movementType === p.id;
                  return (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => setMovementType(p.id)}
                      className={`p-3 rounded-xl border text-left transition flex flex-col justify-between ${
                        isSelected 
                          ? 'border-blue-600 bg-blue-50/50 shadow-xs ring-1 ring-blue-500/30' 
                          : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-base">{p.icon}</span>
                        {isSelected && <Check size={14} className="text-blue-600 font-bold" />}
                      </div>
                      <span className="text-xs font-bold text-slate-900 block">{p.label}</span>
                      <span className="text-[10px] text-slate-400 leading-tight mt-0.5 line-clamp-2">{p.desc}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Drag & Drop Zone */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
                2. Upload Movement Video File
              </label>
              <div
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`p-8 border-2 border-dashed rounded-2xl text-center cursor-pointer transition flex flex-col items-center justify-center ${
                  dragActive 
                    ? 'border-blue-600 bg-blue-50/50' 
                    : 'border-slate-200 hover:border-blue-400 hover:bg-slate-50/60'
                }`}
              >
                <div className="w-12 h-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center mb-3">
                  <Upload size={22} />
                </div>
                <p className="text-xs font-bold text-slate-800">
                  {file ? file.name : 'Click to select or drag and drop video'}
                </p>
                <p className="text-[11px] text-slate-400 mt-1">
                  MP4, MOV, AVI, or WEBM &bull; Max 100MB &bull; Recommended 30-60 FPS full-body capture
                </p>
                <input 
                  type="file" 
                  accept="video/mp4,video/quicktime,video/x-msvideo,video/webm"
                  onChange={handleFileChange}
                  ref={fileInputRef}
                  className="hidden" 
                />
              </div>
            </div>

            {/* Upload Progress */}
            {uploadProgress > 0 && uploadProgress < 100 && (
              <div className="space-y-1">
                <div className="flex justify-between text-[11px] text-slate-500 font-medium">
                  <span>Uploading video to analysis engine...</span>
                  <span>{uploadProgress}%</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                  <div className="bg-blue-600 h-full transition-all duration-200" style={{ width: `${uploadProgress}%` }} />
                </div>
              </div>
            )}

            <div className="flex justify-between items-center pt-1 border-t border-slate-100">
              <span className="text-[11px] text-slate-400">
                Validated for MediaPipe Pose 33-keypoint tracking
              </span>
              <button 
                type="submit" 
                disabled={!file || (uploadProgress > 0 && uploadProgress < 100)}
                className="bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs py-2.5 px-5 rounded-xl shadow-xs transition disabled:opacity-50 flex items-center gap-1.5"
              >
                <Film size={14} />
                {uploadProgress > 0 && uploadProgress < 100 ? `Uploading (${uploadProgress}%)...` : 'Process & Analyze Video'}
              </button>
            </div>
          </form>
        )}
      </div>

      {/* Videos List Table */}
      <div className="bg-white rounded-2xl shadow-xs border border-slate-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
          <div>
            <h2 className="font-bold text-slate-900 text-sm">Movement Trials & Pose Tracking History</h2>
            <p className="text-xs text-slate-500">Processed video recordings and computer vision skeleton overlays</p>
          </div>
          <span className="text-xs font-semibold text-slate-400">
            {videos.length} {videos.length === 1 ? 'recording' : 'recordings'}
          </span>
        </div>

        {videos.length === 0 ? (
          <div className="p-10 text-center text-slate-400 text-xs">
            <Film size={28} className="mx-auto mb-2 opacity-40" />
            No movement videos recorded yet. Upload your first movement trial above.
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {videos.map(v => {
              const filename = v.filename.split('.')[0];
              const isExpanded = expandedVideo?.id === v.id;
              const isProcessing = v.status === 'processing' || v.status === 'uploaded';
              const progressPct = v.processing_progress || 0;

              return (
                <div key={v.id} className="transition">
                  <div className="p-4 sm:px-6 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-50/60">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-slate-100 text-slate-600 flex items-center justify-center shrink-0">
                        <Film size={18} />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-xs text-slate-900 truncate max-w-xs" title={v.original_filename}>
                            {v.original_filename}
                          </span>
                          <span className="text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded-md font-semibold capitalize">
                            {v.movement_type || 'general'}
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-400 flex items-center gap-2 mt-0.5">
                          <span>{new Date(v.created_at).toLocaleDateString()}</span>
                          <span>&bull;</span>
                          <span>{v.duration_sec ? `${Math.round(v.duration_sec)}s` : 'N/A'}</span>
                          <span>&bull;</span>
                          <span>{(v.size_bytes / (1024 * 1024)).toFixed(1)} MB</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 self-end sm:self-auto">
                      {isProcessing ? (
                        <div className="flex items-center gap-2">
                          <div className="w-24 bg-slate-100 rounded-full h-1.5 overflow-hidden">
                            <div className="bg-blue-600 h-full transition-all duration-300" style={{ width: `${progressPct}%` }} />
                          </div>
                          <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200 animate-pulse">
                            Processing {progressPct > 0 ? `${progressPct}%` : '...'}
                          </span>
                        </div>
                      ) : (
                        <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider ${
                          v.status === 'completed' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' :
                          'bg-rose-50 text-rose-700 border border-rose-200'
                        }`}>
                          {v.status}
                        </span>
                      )}

                      <button
                        onClick={() => toggleVideoView(v)}
                        className={`text-xs font-semibold px-3 py-1.5 rounded-lg border transition flex items-center gap-1 ${
                          isExpanded 
                            ? 'bg-slate-900 text-white border-slate-900' 
                            : 'bg-white text-slate-700 border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                        }`}
                      >
                        <span>{isExpanded ? 'Hide' : 'Review'}</span>
                        {isExpanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                      </button>

                      <button
                        onClick={() => handleDeleteVideo(v.id)}
                        disabled={deletingId === v.id}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 border border-slate-200 transition"
                        title="Delete Video Recording"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </div>

                  {/* Expanded Analysis Drawer */}
                  {isExpanded && (
                    <div className="p-4 sm:p-6 bg-slate-50/80 border-t border-slate-200 space-y-5">
                      {/* Quality & Validation Banner */}
                      {v.status === 'completed' && (
                        <div className="p-3.5 bg-white rounded-xl border border-slate-200 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                          <div className="flex items-center gap-3 text-xs">
                            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
                              <ShieldCheck size={18} />
                            </div>
                            <div>
                              <div className="font-bold text-slate-800 flex items-center gap-2">
                                <span>MediaPipe Pose Tracking Complete</span>
                                <span className="bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded-full text-[10px] font-bold border border-emerald-200">
                                  Tracked
                                </span>
                              </div>
                              <p className="text-[11px] text-slate-500">
                                Pattern: <strong className="capitalize">{v.movement_type || 'General'}</strong> &bull; Resolution: {v.width}x{v.height} &bull; Frame Rate: {v.fps} FPS
                              </p>
                            </div>
                          </div>

                          {/* Playback Speed Controls */}
                          <div className="flex items-center gap-1.5 text-xs">
                            <span className="text-[11px] text-slate-400 font-semibold mr-1">Slow Motion:</span>
                            {[0.5, 0.75, 1.0].map((speed) => (
                              <button
                                key={speed}
                                onClick={() => handleSpeedChange(speed)}
                                className={`px-2 py-0.5 rounded-lg text-xs font-semibold border transition ${
                                  playbackSpeed === speed
                                    ? 'bg-blue-600 text-white border-blue-600'
                                    : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
                                }`}
                              >
                                {speed}x
                              </button>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Error Banner */}
                      {v.status === 'error' && (
                        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 flex items-start gap-2.5">
                          <ShieldAlert size={16} className="text-rose-600 shrink-0 mt-0.5" />
                          <div>
                            <strong className="block font-bold mb-0.5">Pose Estimation Validation Failure</strong>
                            <p>{v.error_message || 'Video analysis encountered an unexpected processing issue.'}</p>
                          </div>
                        </div>
                      )}

                      {/* Sub-Tabs */}
                      <div className="flex border-b border-slate-200 gap-4 text-xs font-semibold">
                        <button
                          onClick={() => setActiveAnalysisTab('video')}
                          className={`pb-2 flex items-center gap-1.5 border-b-2 transition ${
                            activeAnalysisTab === 'video'
                              ? 'border-blue-600 text-blue-600'
                              : 'border-transparent text-slate-500 hover:text-slate-800'
                          }`}
                        >
                          <Play size={13} /> Video & Skeleton Pose
                        </button>

                        {v.status === 'completed' && (
                          <>
                            <button
                              onClick={() => setActiveAnalysisTab('kinematics')}
                              className={`pb-2 flex items-center gap-1.5 border-b-2 transition ${
                                activeAnalysisTab === 'kinematics'
                                  ? 'border-blue-600 text-blue-600'
                                  : 'border-transparent text-slate-500 hover:text-slate-800'
                              }`}
                            >
                              <Activity size={13} /> Joint Kinematics
                            </button>

                            <button
                              onClick={() => setActiveAnalysisTab('assessment')}
                              className={`pb-2 flex items-center gap-1.5 border-b-2 transition ${
                                activeAnalysisTab === 'assessment'
                                  ? 'border-blue-600 text-blue-600'
                                  : 'border-transparent text-slate-500 hover:text-slate-800'
                              }`}
                            >
                              <Layers size={13} /> FIFA 11+ Movement Assessment
                            </button>

                            <button
                              onClick={() => setActiveAnalysisTab('recommendations')}
                              className={`pb-2 flex items-center gap-1.5 border-b-2 transition ${
                                activeAnalysisTab === 'recommendations'
                                  ? 'border-blue-600 text-blue-600'
                                  : 'border-transparent text-slate-500 hover:text-slate-800'
                              }`}
                            >
                              <FileText size={13} /> Corrective Plan & Anomalies
                            </button>
                          </>
                        )}
                      </div>

                      {/* Tab 1: Point-Plotted Video Playback (No Original Video Needed After Processing) */}
                      {activeAnalysisTab === 'video' && (
                        <div>
                          {v.status === 'completed' ? (
                            <div className="bg-white p-4 sm:p-5 rounded-xl border border-slate-200 space-y-3.5">
                              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2.5 border-b border-slate-100">
                                <div>
                                  <span className="text-xs font-bold text-slate-900 flex items-center gap-2">
                                    <Sparkles size={14} className="text-blue-600" />
                                    Point-Plotted Biomechanical Movement Video
                                  </span>
                                  <p className="text-[11px] text-slate-500 mt-0.5">
                                    MediaPipe human pose keypoints, high-contrast skeleton overlays, and live joint angle telemetry.
                                  </p>
                                </div>
                                <div className="flex items-center gap-2 self-start sm:self-auto">
                                  <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-md bg-emerald-50 text-emerald-700 border border-emerald-200">
                                    {v.quality_score ? `Tracking Quality: ${v.quality_score}%` : 'Analysis Completed'}
                                  </span>
                                  <span className="text-[10px] font-semibold px-2.5 py-0.5 rounded-md bg-slate-100 text-slate-600 capitalize">
                                    {v.movement_type || 'General'}
                                  </span>
                                </div>
                              </div>

                              {/* Prominent Full-Width Point-Plotted Video Player */}
                              <div className="relative rounded-xl overflow-hidden bg-slate-950 border border-slate-800 shadow-sm">
                                <video 
                                  ref={playbackVideoRef} 
                                  controls 
                                  playsInline
                                  src={`${uploadsBaseUrl}/uploads/${filename}_annotated.mp4`} 
                                  className="w-full aspect-video object-contain" 
                                />
                              </div>

                              {/* Playback Speed, Frame Stepping & Color Legend Controls */}
                              <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
                                <div className="flex items-center gap-1.5 text-xs">
                                  <span className="text-[11px] text-slate-400 font-semibold mr-1">Slow Motion:</span>
                                  {[0.25, 0.5, 0.75, 1.0].map((speed) => (
                                    <button
                                      key={speed}
                                      onClick={() => handleSpeedChange(speed)}
                                      className={`px-2.5 py-1 rounded-lg text-xs font-semibold border transition ${
                                        playbackSpeed === speed
                                          ? 'bg-blue-600 text-white border-blue-600 shadow-xs'
                                          : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
                                      }`}
                                    >
                                      {speed}x
                                    </button>
                                  ))}

                                  <div className="h-4 w-[1px] bg-slate-200 mx-1" />

                                  <button
                                    onClick={() => {
                                      if (playbackVideoRef.current) {
                                        playbackVideoRef.current.currentTime = Math.max(0, playbackVideoRef.current.currentTime - 0.05);
                                      }
                                    }}
                                    className="px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-slate-50 text-slate-700 border border-slate-200 hover:bg-slate-100 transition"
                                    title="Step backward 1-2 frames"
                                  >
                                    -0.05s
                                  </button>
                                  <button
                                    onClick={() => {
                                      if (playbackVideoRef.current) {
                                        playbackVideoRef.current.currentTime += 0.05;
                                      }
                                    }}
                                    className="px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-slate-50 text-slate-700 border border-slate-200 hover:bg-slate-100 transition"
                                    title="Step forward 1-2 frames"
                                  >
                                    +0.05s
                                  </button>
                                </div>

                                {/* Keypoint Joint Color Legend */}
                                <div className="flex items-center gap-3 text-[10px] text-slate-500">
                                  <span className="flex items-center gap-1 font-medium">
                                    <span className="w-2.5 h-2.5 rounded-full bg-[#2578eb] inline-block ring-1 ring-slate-900" /> Left Side
                                  </span>
                                  <span className="flex items-center gap-1 font-medium">
                                    <span className="w-2.5 h-2.5 rounded-full bg-[#ef4444] inline-block ring-1 ring-slate-900" /> Right Side
                                  </span>
                                  <span className="flex items-center gap-1 font-medium">
                                    <span className="w-2.5 h-2.5 rounded-full bg-[#10b981] inline-block ring-1 ring-slate-900" /> Torso/Spine
                                  </span>
                                </div>
                              </div>
                            </div>
                          ) : (
                            <div className="w-full aspect-video rounded-xl bg-slate-100 border border-slate-200 flex flex-col items-center justify-center text-slate-400 text-xs p-8 text-center space-y-3">
                              <Sparkles size={28} className="text-blue-500 animate-spin" />
                              <div>
                                <span className="font-bold text-slate-800 text-sm block">Tracking MediaPipe Pose Landmarks & Generating Point-Plotted Video...</span>
                                <span className="text-xs text-slate-500 mt-1 block max-w-md mx-auto">
                                  Extracting 33 human pose keypoints, drawing high-contrast joint nodes and measuring real-time joint angles.
                                </span>
                              </div>
                              <span className="text-[11px] text-blue-600 bg-blue-50 px-3 py-1 rounded-full font-semibold border border-blue-100">
                                Processing {v.processing_progress || 0}% Complete
                              </span>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Tab 2: Kinematics */}
                      {activeAnalysisTab === 'kinematics' && v.status === 'completed' && (
                        <div className="bg-white p-5 rounded-xl border border-slate-200">
                          <BiomechanicsReport videoId={v.id} />
                        </div>
                      )}

                      {/* Tab 3: Movement Quality */}
                      {activeAnalysisTab === 'assessment' && v.status === 'completed' && (
                        <div className="bg-white p-5 rounded-xl border border-slate-200">
                          <AssessmentReport videoId={v.id} />
                        </div>
                      )}

                      {/* Tab 4: Recommendations & Anomalies */}
                      {activeAnalysisTab === 'recommendations' && v.status === 'completed' && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div className="bg-white p-5 rounded-xl border border-slate-200">
                            <RecommendationPanel videoId={v.id} />
                          </div>
                          <div className="bg-white p-5 rounded-xl border border-slate-200">
                            <AnomalyReport videoId={v.id} videoRef={playbackVideoRef} />
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
