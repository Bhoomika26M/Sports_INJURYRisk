import React, { useState, useRef, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import api from '../api/client';
import { useAuth } from '../context/AuthContext';
import { BiomechanicsReport } from '../components/BiomechanicsReport';
import { AssessmentReport } from '../components/AssessmentReport';
import { AnomalyReport } from '../components/AnomalyReport';
import { RecommendationPanel } from '../components/RecommendationPanel';
import { ReportsExportModal } from '../components/ReportsExportModal';
import { 
  Upload, 
  Film, 
  CheckCircle2, 
  AlertCircle, 
  ChevronDown, 
  ChevronUp, 
  Play, 
  Sparkles,
  Layers,
  Activity,
  FileText,
  Trash2,
  Check,
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
  const [searchParams] = useSearchParams();
  const [assignedAthletes, setAssignedAthletes] = useState([]);
  const [file, setFile] = useState(null);
  const [movementType, setMovementType] = useState('squatting');
  const [uploadProgress, setUploadProgress] = useState(0);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [athleteId, setAthleteId] = useState('');
  const [reportModalVideo, setReportModalVideo] = useState(null);
  const [videos, setVideos] = useState([]);
  const [expandedVideo, setExpandedVideo] = useState(null);
  const [activeAnalysisTab, setActiveAnalysisTab] = useState('video');
  const [dragActive, setDragActive] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1.0);
  const [deletingId, setDeletingId] = useState(null);
  
  const fileInputRef = useRef(null);
  const playbackVideoRef = useRef(null);

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
        } else if (user) {
          const res = await api.get('/athletes/');
          const list = res.data || [];
          setAssignedAthletes(list);
          const paramAthleteId = searchParams.get('athlete_id') || searchParams.get('athleteId');
          if (paramAthleteId) {
            const parsed = Number(paramAthleteId);
            setAthleteId(parsed);
            fetchVideos(parsed);
          } else if (list.length > 0) {
            setAthleteId(list[0].id);
            fetchVideos(list[0].id);
          }
        }
      } catch (_err) {
        console.error("Athlete profile or roster fetch failed:", _err);
      }
    };
    fetchAthleteData();
  }, [user, searchParams]);

  const fetchVideos = async (id) => {
    try {
      const res = await api.get(`/videos/athlete/${id}`);
      setVideos(res.data);
    } catch (err) {
      console.error("Error fetching videos:", err);
    }
  };

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

    const maxBytes = 100 * 1024 * 1024;
    if (selectedFile.size > maxBytes) {
      setError(`File size (${(selectedFile.size / (1024 * 1024)).toFixed(1)}MB) exceeds 100MB limit. Please trim the clip.`);
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

  const toggleVideoView = (v) => {
    if (expandedVideo?.id === v.id) {
      setExpandedVideo(null);
    } else {
      setExpandedVideo(v);
      setActiveAnalysisTab('video');
    }
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-5xl mx-auto space-y-6">
      {/* Page Title */}
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
          <span>Movement Video Analysis</span>
        </h1>
        <p className="text-slate-400 text-xs mt-0.5">
          Automated MediaPipe Pose Estimation, 33-landmark tracking, joint kinematics, and clinical risk evaluation.
        </p>
      </div>

      {/* Target Athlete Selector for Staff */}
      {user?.role !== 'athlete' && (
        <div className="bg-[#11121a] p-5 rounded-2xl shadow-xl border border-white/10 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider">
              Target Athlete for Movement Analysis
            </label>
            <p className="text-xs text-slate-400 mt-0.5">
              Select an athlete from your roster to upload new movement recordings or review kinematic evaluations.
            </p>
          </div>
          {assignedAthletes.length === 0 ? (
            <div className="text-xs text-amber-300 bg-amber-500/15 px-3 py-1.5 rounded-xl border border-amber-500/30 font-medium">
              No athletes currently assigned to your monitoring roster
            </div>
          ) : (
            <select
              value={athleteId}
              onChange={(e) => {
                const newId = Number(e.target.value);
                setAthleteId(newId);
                setExpandedVideo(null);
                fetchVideos(newId);
              }}
              className="border border-white/10 rounded-xl px-3 py-2 text-xs font-semibold text-white bg-[#1c1d2e] focus:outline-none focus:ring-2 focus:ring-purple-500 max-w-sm"
            >
              {assignedAthletes.map(a => (
                <option key={a.id} value={a.id}>
                  #{a.id} — {a.name || a.sport_type || 'Athlete'} ({a.sport_type || 'General'} &bull; {a.position || 'Player'})
                </option>
              ))}
            </select>
          )}
        </div>
      )}

      {/* Upload Box */}
      <div className="bg-[#11121a] p-6 sm:p-8 rounded-2xl shadow-xl border border-white/10">
        {!athleteId ? (
          <div className="bg-amber-500/15 text-amber-300 p-4 rounded-xl border border-amber-500/30 text-xs flex items-center gap-2">
            <AlertCircle size={16} className="shrink-0" />
            <span>
              {user?.role === 'athlete'
                ? 'Please complete your athlete physical profile before uploading movement recordings.'
                : 'No athlete selected. Please assign or select an athlete to upload recordings.'}
            </span>
          </div>
        ) : (
          <form onSubmit={handleUpload} className="space-y-5">
            {message && (
              <div className="bg-emerald-500/15 text-emerald-300 p-3.5 rounded-xl border border-emerald-500/30 text-xs flex items-center gap-2">
                <CheckCircle2 size={16} className="text-emerald-400 shrink-0" />
                <span>{message}</span>
              </div>
            )}
            {error && (
              <div className="bg-rose-500/10 text-rose-300 p-3.5 rounded-xl border border-rose-500/30 text-xs flex items-center gap-2">
                <AlertCircle size={16} className="shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {/* Movement Pattern Selector */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-2">
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
                          ? 'border-purple-500 bg-purple-500/15 shadow-sm ring-1 ring-purple-500/30' 
                          : 'border-white/10 hover:border-white/20 bg-[#161724]'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-base">{p.icon}</span>
                        {isSelected && <Check size={14} className="text-purple-400 font-bold" />}
                      </div>
                      <span className="text-xs font-bold text-white block">{p.label}</span>
                      <span className="text-xs text-slate-400 leading-normal mt-0.5 line-clamp-2">{p.desc}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Drag & Drop Zone */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-2">
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
                    ? 'border-purple-500 bg-purple-500/10' 
                    : 'border-white/10 hover:border-purple-500/50 hover:bg-white/5'
                }`}
              >
                <div className="w-12 h-12 rounded-xl bg-purple-500/15 text-purple-400 flex items-center justify-center mb-3 border border-purple-500/30">
                  <Upload size={22} />
                </div>
                <p className="text-sm font-bold text-white">
                  {file ? file.name : 'Click to select or drag and drop video'}
                </p>
                <p className="text-xs text-slate-400 mt-1">
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
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs text-slate-300 font-medium">
                  <span>Uploading video to analysis engine...</span>
                  <span className="text-purple-400 font-bold">{uploadProgress}%</span>
                </div>
                <div className="w-full bg-[#1e1f2f] rounded-full h-2.5 overflow-hidden">
                  <div className="bg-purple-600 h-full transition-all duration-200" style={{ width: `${uploadProgress}%` }} />
                </div>
              </div>
            )}

            <div className="flex justify-between items-center pt-2 border-t border-white/5">
              <span className="text-xs text-slate-400">
                Validated for MediaPipe Pose 33-keypoint tracking
              </span>
              <button 
                type="submit" 
                disabled={!file || (uploadProgress > 0 && uploadProgress < 100)}
                className="bg-purple-600 hover:bg-purple-500 text-white font-semibold text-xs sm:text-sm py-2.5 px-5 rounded-xl shadow-lg shadow-purple-600/25 transition disabled:opacity-50 flex items-center gap-2"
              >
                <Film size={15} />
                {uploadProgress > 0 && uploadProgress < 100 ? `Uploading (${uploadProgress}%)...` : 'Process & Analyze Video'}
              </button>
            </div>
          </form>
        )}
      </div>

      {/* Videos List Table */}
      <div className="bg-[#11121a] rounded-2xl shadow-xl border border-white/10 overflow-hidden">
        <div className="px-6 py-4 border-b border-white/10 flex justify-between items-center bg-[#141522]">
          <div>
            <h2 className="font-bold text-white text-base">Movement Trials &amp; Pose Tracking History</h2>
            <p className="text-xs text-slate-400 mt-0.5">Processed video recordings and computer vision skeleton overlays</p>
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
          <div className="divide-y divide-white/5">
            {videos.map(v => {
              const filename = v.filename.split('.')[0];
              const isExpanded = expandedVideo?.id === v.id;
              const isProcessing = v.status === 'processing' || v.status === 'uploaded';
              const progressPct = v.processing_progress || 0;

              return (
                <div key={v.id} className="transition">
                  <div className="p-4 sm:px-6 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-white/5">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-purple-500/15 text-purple-400 border border-purple-500/30 flex items-center justify-center shrink-0">
                        <Film size={18} />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-xs text-white truncate max-w-xs" title={v.original_filename}>
                            {v.original_filename}
                          </span>
                          <span className="text-xs bg-[#1e1f2f] text-slate-300 border border-white/5 px-2 py-0.5 rounded-md font-semibold capitalize">
                            {v.movement_type || 'general'}
                          </span>
                        </div>
                        <div className="text-xs text-slate-400 flex items-center gap-2 mt-0.5">
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
                          <div className="w-24 bg-[#1e1f2f] rounded-full h-1.5 overflow-hidden">
                            <div className="bg-purple-600 h-full transition-all duration-300" style={{ width: `${progressPct}%` }} />
                          </div>
                          <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-purple-500/15 text-purple-300 border border-purple-500/30 animate-pulse">
                            Processing {progressPct > 0 ? `${progressPct}%` : '...'}
                          </span>
                        </div>
                      ) : (
                        <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider ${
                          v.status === 'completed' ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30' :
                          'bg-rose-500/15 text-rose-300 border border-rose-500/30'
                        }`}>
                          {v.status}
                        </span>
                      )}

                      {v.status === 'completed' && (
                        <button
                          onClick={() => setReportModalVideo(v)}
                          className="text-xs font-semibold px-3 py-1.5 rounded-xl border border-purple-500/30 bg-purple-500/15 text-purple-300 hover:bg-purple-600 hover:text-white transition flex items-center gap-1.5"
                          title="View Consolidated Individual Analysis Report"
                        >
                          <FileText size={13} />
                          <span>Full Report (PDF)</span>
                        </button>
                      )}

                      <button
                        onClick={() => toggleVideoView(v)}
                        className={`text-xs font-semibold px-3 py-1.5 rounded-xl border transition flex items-center gap-1 ${
                          isExpanded 
                            ? 'bg-purple-600 text-white border-purple-600' 
                            : 'bg-[#1c1d2e] text-slate-300 border-white/10 hover:border-white/20'
                        }`}
                      >
                        <span>{isExpanded ? 'Hide' : 'Review'}</span>
                        {isExpanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                      </button>

                      <button
                        onClick={() => handleDeleteVideo(v.id)}
                        disabled={deletingId === v.id}
                        className="p-1.5 rounded-xl text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 border border-white/10 transition"
                        title="Delete Video Recording"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </div>

                  {/* Expanded Analysis Drawer */}
                  {isExpanded && (
                    <div className="p-4 sm:p-6 bg-[#141522] border-t border-white/10 space-y-5">
                      {/* Quality & Validation Banner */}
                      {v.status === 'completed' && (
                        <div className="p-3.5 bg-[#161724] rounded-xl border border-white/10 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                          <div className="flex items-center gap-3 text-xs">
                            <div className="w-8 h-8 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 flex items-center justify-center shrink-0">
                              <ShieldCheck size={18} />
                            </div>
                            <div>
                              <div className="font-bold text-white flex items-center gap-2">
                                <span>MediaPipe Pose Tracking Complete</span>
                                <span className="bg-emerald-500/15 text-emerald-300 px-2 py-0.5 rounded-full text-[10px] font-bold border border-emerald-500/30">
                                  Tracked
                                </span>
                              </div>
                              <p className="text-xs text-slate-400 mt-0.5">
                                Pattern: <strong className="capitalize text-white">{v.movement_type || 'General'}</strong> &bull; Resolution: {v.width}x{v.height} &bull; Frame Rate: {v.fps} FPS
                              </p>
                            </div>
                          </div>

                          {/* Playback Speed Controls */}
                          <div className="flex items-center gap-1.5 text-xs">
                            <span className="text-xs text-slate-400 font-semibold mr-1">Slow Motion:</span>
                            {[0.5, 0.75, 1.0].map((speed) => (
                              <button
                                key={speed}
                                onClick={() => handleSpeedChange(speed)}
                                className={`px-2.5 py-1 rounded-lg text-xs font-semibold border transition ${
                                  playbackSpeed === speed
                                    ? 'bg-purple-600 text-white border-purple-600'
                                    : 'bg-[#1c1d2e] text-slate-300 border-white/10 hover:border-white/20'
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
                        <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-xs text-rose-300 flex items-start gap-2.5">
                          <ShieldAlert size={16} className="text-rose-400 shrink-0 mt-0.5" />
                          <div>
                            <strong className="block font-bold mb-0.5 text-rose-200">Pose Estimation Validation Failure</strong>
                            <p>{v.error_message || 'Video analysis encountered an unexpected processing issue.'}</p>
                          </div>
                        </div>
                      )}

                      {/* Sub-Tabs */}
                      <div className="flex border-b border-white/10 gap-4 text-xs font-semibold">
                        <button
                          onClick={() => setActiveAnalysisTab('video')}
                          className={`pb-2.5 flex items-center gap-1.5 border-b-2 transition ${
                            activeAnalysisTab === 'video'
                              ? 'border-purple-500 text-purple-400'
                              : 'border-transparent text-slate-400 hover:text-white'
                          }`}
                        >
                          <Play size={13} /> Video &amp; Skeleton Pose
                        </button>

                        {v.status === 'completed' && (
                          <>
                            <button
                              onClick={() => setActiveAnalysisTab('kinematics')}
                              className={`pb-2.5 flex items-center gap-1.5 border-b-2 transition ${
                                activeAnalysisTab === 'kinematics'
                                  ? 'border-purple-500 text-purple-400'
                                  : 'border-transparent text-slate-400 hover:text-white'
                              }`}
                            >
                              <Activity size={13} /> Joint Kinematics
                            </button>

                            <button
                              onClick={() => setActiveAnalysisTab('assessment')}
                              className={`pb-2.5 flex items-center gap-1.5 border-b-2 transition ${
                                activeAnalysisTab === 'assessment'
                                  ? 'border-purple-500 text-purple-400'
                                  : 'border-transparent text-slate-400 hover:text-white'
                              }`}
                            >
                              <Layers size={13} /> FIFA 11+ Movement Assessment
                            </button>

                            <button
                              onClick={() => setActiveAnalysisTab('recommendations')}
                              className={`pb-2.5 flex items-center gap-1.5 border-b-2 transition ${
                                activeAnalysisTab === 'recommendations'
                                  ? 'border-purple-500 text-purple-400'
                                  : 'border-transparent text-slate-400 hover:text-white'
                              }`}
                            >
                              <FileText size={13} /> Corrective Plan &amp; Anomalies
                            </button>
                          </>
                        )}
                      </div>

                      {/* Tab 1: Point-Plotted Video Playback */}
                      {activeAnalysisTab === 'video' && (
                        <div>
                          {v.status === 'completed' ? (
                            <div className="bg-[#11121a] p-4 sm:p-5 rounded-xl border border-white/10 space-y-3.5">
                              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2.5 border-b border-white/5">
                                <div>
                                  <span className="text-xs font-bold text-white flex items-center gap-2">
                                    <Sparkles size={14} className="text-purple-400" />
                                    Point-Plotted Biomechanical Movement Video
                                  </span>
                                  <p className="text-xs text-slate-400 mt-0.5">
                                    MediaPipe human pose keypoints, high-contrast skeleton overlays, and live joint angle telemetry.
                                  </p>
                                </div>
                                <div className="flex items-center gap-2 self-start sm:self-auto">
                                  <span className="text-xs font-bold px-2.5 py-0.5 rounded-md bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                                    {v.quality_score ? `Tracking Quality: ${v.quality_score}%` : 'Analysis Completed'}
                                  </span>
                                  <span className="text-xs font-semibold px-2.5 py-0.5 rounded-md bg-[#1e1f2f] text-slate-300 capitalize">
                                    {v.movement_type || 'General'}
                                  </span>
                                </div>
                              </div>

                              {/* Prominent Full-Width Point-Plotted Video Player */}
                              <div className="relative rounded-xl overflow-hidden bg-black border border-white/10 shadow-sm">
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
                                  <span className="text-xs text-slate-400 font-semibold mr-1">Slow Motion:</span>
                                  {[0.25, 0.5, 0.75, 1.0].map((speed) => (
                                    <button
                                      key={speed}
                                      onClick={() => handleSpeedChange(speed)}
                                      className={`px-2.5 py-1 rounded-lg text-xs font-semibold border transition ${
                                        playbackSpeed === speed
                                          ? 'bg-purple-600 text-white border-purple-600'
                                          : 'bg-[#1c1d2e] text-slate-300 border-white/10 hover:border-white/20'
                                      }`}
                                    >
                                      {speed}x
                                    </button>
                                  ))}

                                  <div className="h-4 w-[1px] bg-white/10 mx-1" />

                                  <button
                                    onClick={() => {
                                      if (playbackVideoRef.current) {
                                        playbackVideoRef.current.currentTime = Math.max(0, playbackVideoRef.current.currentTime - 0.05);
                                      }
                                    }}
                                    className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-[#1c1d2e] text-slate-300 border border-white/10 hover:border-white/20 transition"
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
                                    className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-[#1c1d2e] text-slate-300 border border-white/10 hover:border-white/20 transition"
                                    title="Step forward 1-2 frames"
                                  >
                                    +0.05s
                                  </button>
                                </div>

                                {/* Keypoint Joint Color Legend */}
                                <div className="flex items-center gap-3 text-xs text-slate-400">
                                  <span className="flex items-center gap-1 font-medium">
                                    <span className="w-2.5 h-2.5 rounded-full bg-[#818cf8] inline-block" /> Left Side
                                  </span>
                                  <span className="flex items-center gap-1 font-medium">
                                    <span className="w-2.5 h-2.5 rounded-full bg-[#f43f5e] inline-block" /> Right Side
                                  </span>
                                  <span className="flex items-center gap-1 font-medium">
                                    <span className="w-2.5 h-2.5 rounded-full bg-[#10b981] inline-block" /> Torso/Spine
                                  </span>
                                </div>
                              </div>
                            </div>
                          ) : (
                            <div className="w-full aspect-video rounded-xl bg-[#11121a] border border-white/10 flex flex-col items-center justify-center text-slate-400 text-xs p-8 text-center space-y-3">
                              <Sparkles size={28} className="text-purple-400 animate-spin" />
                              <div>
                                <span className="font-bold text-white text-sm block">Tracking MediaPipe Pose Landmarks &amp; Generating Point-Plotted Video...</span>
                                <span className="text-xs text-slate-400 mt-1 block max-w-md mx-auto">
                                  Extracting 33 human pose keypoints, drawing skeleton nodes, and measuring real-time joint kinematics.
                                </span>
                              </div>
                              <span className="text-xs text-purple-300 bg-purple-500/15 px-3 py-1 rounded-full font-semibold border border-purple-500/30">
                                Processing {v.processing_progress || 0}% Complete
                              </span>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Tab 2: Kinematics */}
                      {activeAnalysisTab === 'kinematics' && v.status === 'completed' && (
                        <div className="bg-[#11121a] p-5 rounded-xl border border-white/10">
                          <BiomechanicsReport videoId={v.id} />
                        </div>
                      )}

                      {/* Tab 3: Movement Quality */}
                      {activeAnalysisTab === 'assessment' && v.status === 'completed' && (
                        <div className="bg-[#11121a] p-5 rounded-xl border border-white/10">
                          <AssessmentReport videoId={v.id} />
                        </div>
                      )}

                      {/* Tab 4: Recommendations & Anomalies */}
                      {activeAnalysisTab === 'recommendations' && v.status === 'completed' && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div className="bg-[#11121a] p-5 rounded-xl border border-white/10">
                            <RecommendationPanel videoId={v.id} />
                          </div>
                          <div className="bg-[#11121a] p-5 rounded-xl border border-white/10">
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

      {/* Consolidated Individual Report Modal */}
      {reportModalVideo && (
        <ReportsExportModal
          isOpen={!!reportModalVideo}
          onClose={() => setReportModalVideo(null)}
          athleteId={athleteId}
          athleteName={assignedAthletes.find(a => a.id === athleteId)?.name || user?.name || `Athlete #${athleteId}`}
          videoId={reportModalVideo.id}
          videos={videos}
        />
      )}
    </div>
  );
};

export default VideoUpload;
