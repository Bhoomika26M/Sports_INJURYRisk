import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import VideoStudio from './components/VideoStudio';
import BiomechanicalAnalysisView from './components/BiomechanicalAnalysisView';
import InjuryRiskView from './components/InjuryRiskView';
import RecommendationsView from './components/RecommendationsView';
import RoleDashboards from './components/RoleDashboards';
import AthleteManagement from './components/AthleteManagement';
import DatasetsView from './components/DatasetsView';
import AuthModal from './components/AuthModal';
import { api } from './api/client';
import { Activity, Sparkles, CheckCircle2 } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('video_studio');
  const [activeRole, setActiveRole] = useState('athlete');
  const [currentUser, setCurrentUser] = useState(null);
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const [authMode, setAuthMode] = useState('login');
  const [authResetToken, setAuthResetToken] = useState('');

  const [athletes, setAthletes] = useState([]);
  const [selectedAthleteId, setSelectedAthleteId] = useState(1);
  const [videos, setVideos] = useState([]);
  const [currentVideo, setCurrentVideo] = useState(null);
  const [biomechanics, setBiomechanics] = useState(null);
  const [injuryRisk, setInjuryRisk] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [systemNotice, setSystemNotice] = useState('Kinematix operational: Computer vision pose tracking and risk engine ready.');

  // Check authentication and load athletes/videos on mount
  useEffect(() => {
    checkCurrentUser();
    checkForResetToken();
    loadInitialData();
  }, []);

  const checkCurrentUser = async () => {
    try {
      const user = await api.getCurrentUser();
      if (user) {
        setCurrentUser(user);
        setActiveRole(user.role);
      }
    } catch {
      // User is not signed in
    }
  };

  const checkForResetToken = () => {
    // Check URL query param or hash for reset token
    const urlParams = new URLSearchParams(window.location.search);
    let token = urlParams.get('reset_token') || urlParams.get('token');
    
    if (!token && window.location.hash.includes('token=')) {
      const hashParams = new URLSearchParams(window.location.hash.split('?')[1]);
      token = hashParams.get('token');
    }

    if (token) {
      setAuthResetToken(token);
      setAuthMode('reset');
      setIsAuthOpen(true);
    }
  };

  const loadInitialData = async () => {
    try {
      const athList = await api.getAthletes();
      setAthletes(athList);

      const vidList = await api.getVideos();
      setVideos(vidList);

      if (vidList.length > 0) {
        const primaryVid = vidList[0];
        setCurrentVideo(primaryVid);
        loadVideoAnalytics(primaryVid.id);
      }
    } catch (err) {
      console.error('Initial data load error:', err);
    }
  };

  const loadVideoAnalytics = async (videoId) => {
    try {
      const [bio, risk] = await Promise.all([
        api.getBiomechanics(videoId),
        api.getInjuryRisk(videoId)
      ]);
      setBiomechanics(bio);
      setInjuryRisk(risk);
    } catch (err) {
      console.error('Error loading video analytics:', err);
    }
  };

  const handleSelectVideo = (vid) => {
    setCurrentVideo(vid);
    loadVideoAnalytics(vid.id);
  };

  const handleRunAnalysis = async (videoId) => {
    setIsAnalyzing(true);
    setSystemNotice('Running MediaPipe Pose Estimation & Biomechanical Modeling...');
    try {
      const res = await api.runAnalysis(videoId);
      setSystemNotice('Biomechanical analysis and injury risk prediction completed successfully!');
      
      // Refresh current video and analytics
      const updatedVid = await api.getVideo(videoId);
      setCurrentVideo(updatedVid);
      
      // Update videos list
      const vidList = await api.getVideos();
      setVideos(vidList);

      await loadVideoAnalytics(videoId);
      setActiveTab('biomechanics');
    } catch (err) {
      alert(err.message || 'Analysis failed');
      setSystemNotice('Analysis encountered an issue.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleGenerateSample = async (movementType) => {
    setIsAnalyzing(true);
    setSystemNotice(`Generating synthetic athletic movement capture: ${movementType}...`);
    try {
      const newVid = await api.generateSampleVideo(movementType, selectedAthleteId);
      const vidList = await api.getVideos();
      setVideos(vidList);
      setCurrentVideo(newVid);
      setSystemNotice('Sample video generated. Running pose estimation...');
      await handleRunAnalysis(newVid.id);
    } catch (err) {
      alert(err.message || 'Sample generation failed');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleUploadVideo = async (formData) => {
    const newVid = await api.uploadVideo(formData);
    const vidList = await api.getVideos();
    setVideos(vidList);
    setCurrentVideo(newVid);
    setSystemNotice(`Uploaded "${newVid.title}". Ready for pose tracking analysis.`);
    await handleRunAnalysis(newVid.id);
  };

  const handleOpenAuth = (mode = 'login') => {
    setAuthMode(mode);
    setIsAuthOpen(true);
  };

  const handleLogout = async () => {
    await api.logout();
    setCurrentUser(null);
    setSystemNotice('User session ended. Signed out successfully.');
  };

  const handleAuthSuccess = (user) => {
    setCurrentUser(user);
    if (user?.role) {
      setActiveRole(user.role);
    }
    setSystemNotice(`Welcome back, ${user.full_name} (${user.role}).`);
  };

  const selectedAthlete = athletes.find(a => a.id === selectedAthleteId) || athletes[0];

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900 flex flex-col font-sans">
      {/* Top Navigation */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        activeRole={activeRole}
        setActiveRole={setActiveRole}
        currentUser={currentUser}
        onOpenAuth={handleOpenAuth}
        onLogout={handleLogout}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* System Status Notification Strip */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 bg-white px-4 py-2.5 rounded-xl border border-slate-200 shadow-xs text-xs">
          <div className="flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-teal-600"></span>
            <span className="text-slate-700 font-medium">{systemNotice}</span>
          </div>
          <div className="flex items-center space-x-3 text-[11px] font-mono text-slate-500">
            <span>FastAPI Backend: <strong className="text-teal-700 font-semibold">Online</strong></span>
            <span>MediaPipe Pose: <strong className="text-slate-700 font-semibold">v1.1.0 Ready</strong></span>
          </div>
        </div>

        {/* Tab Views */}
        {activeTab === 'video_studio' && (
          <VideoStudio
            videos={videos}
            currentVideo={currentVideo}
            setCurrentVideo={handleSelectVideo}
            biomechanics={biomechanics}
            injuryRisk={injuryRisk}
            onRunAnalysis={handleRunAnalysis}
            onGenerateSample={handleGenerateSample}
            onUploadVideo={handleUploadVideo}
            isAnalyzing={isAnalyzing}
          />
        )}

        {activeTab === 'biomechanics' && (
          <BiomechanicalAnalysisView
            biomechanics={biomechanics}
            currentVideo={currentVideo}
          />
        )}

        {activeTab === 'injury_risk' && (
          <InjuryRiskView
            injuryRisk={injuryRisk}
            athlete={selectedAthlete}
            currentVideo={currentVideo}
          />
        )}

        {activeTab === 'recommendations' && (
          <RecommendationsView
            injuryRisk={injuryRisk}
          />
        )}

        {activeTab === 'dashboards' && (
          <RoleDashboards
            activeRole={activeRole}
            injuryRisk={injuryRisk}
            athlete={selectedAthlete}
          />
        )}

        {activeTab === 'athletes' && (
          <AthleteManagement
            athletes={athletes}
            onRefreshAthletes={loadInitialData}
            onSelectAthlete={setSelectedAthleteId}
            selectedAthleteId={selectedAthleteId}
          />
        )}

        {activeTab === 'datasets' && (
          <DatasetsView />
        )}
      </main>

      {/* Authentication Modal */}
      <AuthModal
        isOpen={isAuthOpen}
        onClose={() => setIsAuthOpen(false)}
        onAuthSuccess={handleAuthSuccess}
        initialMode={authMode}
        initialToken={authResetToken}
      />

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-4 text-center text-xs text-slate-500 font-mono">
        Kinematix • Sports Movement Biomechanics &amp; Injury Risk Intelligence Platform
      </footer>
    </div>
  );
}
