import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import VideoStudio from './components/VideoStudio';
import BiomechanicalAnalysisView from './components/BiomechanicalAnalysisView';
import InjuryRiskView from './components/InjuryRiskView';
import RecommendationsView from './components/RecommendationsView';
import RoleDashboards from './components/RoleDashboards';
import AthleteManagement from './components/AthleteManagement';
import DatasetsView from './components/DatasetsView';
import AuthPage from './components/AuthPage';
import VideoComparisonView from './components/VideoComparisonView';
import { api } from './api/client';
import { Activity, Sparkles, CheckCircle2 } from 'lucide-react';

export default function App() {
  const hasResetToken = new URLSearchParams(window.location.search).has('token');
  const initialAuthRoute = ['/sign-in', '/register', '/forgot-password', '/reset-password'].includes(window.location.pathname);
  const [isAuthRoute, setIsAuthRoute] = useState(initialAuthRoute);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);
  const [activeTab, setActiveTab] = useState('video_studio');
  const [activeRole, setActiveRole] = useState('athlete');
  const [currentUser, setCurrentUser] = useState(null);
  const routeMode = { '/register': 'register', '/forgot-password': 'forgot', '/reset-password': 'reset' }[window.location.pathname] || 'login';
  const [authMode, setAuthMode] = useState(hasResetToken ? 'reset' : routeMode);
  const [authResetToken, setAuthResetToken] = useState('');

  const [athletes, setAthletes] = useState([]);
  const [selectedAthleteId, setSelectedAthleteId] = useState(1);
  const [videos, setVideos] = useState([]);
  const [currentVideo, setCurrentVideo] = useState(null);
  const [biomechanics, setBiomechanics] = useState(null);
  const [injuryRisk, setInjuryRisk] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [serviceHealth, setServiceHealth] = useState({ status: 'checking', mediapipe_ready: false });
  const [systemNotice, setSystemNotice] = useState('Kinematix movement analysis workspace.');

  // Check authentication and load athletes/videos on mount
  useEffect(() => {
    checkForResetToken();
    const initAuth = async () => {
      try {
        const user = await api.getCurrentUser();
        if (user) {
          setCurrentUser(user);
          setActiveRole(user.role);
          await loadInitialData();
        } else {
          setCurrentUser(null);
          if (!['/sign-in', '/register', '/forgot-password', '/reset-password'].includes(window.location.pathname)) {
            window.history.replaceState({}, '', '/sign-in');
          }
        }
      } catch {
        setCurrentUser(null);
        if (!['/sign-in', '/register', '/forgot-password', '/reset-password'].includes(window.location.pathname)) {
          window.history.replaceState({}, '', '/sign-in');
        }
      } finally {
        setIsCheckingAuth(false);
      }
    };
    initAuth();

    const refreshHealth = async () => {
      try {
        setServiceHealth(await api.getHealth());
      } catch {
        setServiceHealth({ status: 'offline', mediapipe_ready: false });
      }
    };
    refreshHealth();
    const healthTimer = window.setInterval(refreshHealth, 15000);
    const handlePopState = () => {
      const routeMode = { '/register': 'register', '/forgot-password': 'forgot', '/reset-password': 'reset' }[window.location.pathname] || 'login';
      setAuthMode(new URLSearchParams(window.location.search).has('token') ? 'reset' : routeMode);
    };
    window.addEventListener('popstate', handlePopState);
    return () => {
      window.clearInterval(healthTimer);
      window.removeEventListener('popstate', handlePopState);
    };
  }, []);

  const checkForResetToken = () => {
    // A reset link from email opens the dedicated reset-password page.
    const urlParams = new URLSearchParams(window.location.search);
    let token = urlParams.get('reset_token') || urlParams.get('token');
    
    if (!token && window.location.hash.includes('token=')) {
      const hashParams = new URLSearchParams(window.location.hash.split('?')[1]);
      token = hashParams.get('token');
    }

    if (token) {
      setAuthResetToken(token);
      setAuthMode('reset');
      setIsAuthRoute(true);
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
    setBiomechanics(null);
    setInjuryRisk(null);
    loadVideoAnalytics(vid.id);
  };

  const handleRunAnalysis = async (videoId) => {
    setIsAnalyzing(true);
    setBiomechanics(null);
    setInjuryRisk(null);
    setSystemNotice('Running MediaPipe Pose Estimation & Biomechanical Modeling...');
    try {
      const res = await api.runAnalysis(videoId);
      setSystemNotice('Pose analysis and rule-based screening completed successfully.');
      
      // Refresh current video and analytics
      const updatedVid = await api.getVideo(videoId);
      setCurrentVideo(updatedVid);
      
      // Update videos list
      const vidList = await api.getVideos();
      setVideos(vidList);

      await loadVideoAnalytics(videoId);
    } catch (err) {
      try {
        const failedVideo = await api.getVideo(videoId);
        setCurrentVideo(failedVideo);
        setVideos(await api.getVideos());
      } catch {
        // Keep the original request error visible if status refresh also fails.
      }
      alert(err.message || 'Analysis failed');
      setSystemNotice('Analysis failed. Check the video and try again.');
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

  const handleLoadDemoSample = async (filename, activityType, title) => {
    setIsAnalyzing(true);
    setSystemNotice(`Loading local demo sample: ${filename}...`);
    try {
      const newVid = await api.loadDemoSample(filename, activityType, title, selectedAthleteId);
      const vidList = await api.getVideos();
      setVideos(vidList);
      setCurrentVideo(newVid);
      setSystemNotice(`Loaded "${newVid.title}".`);
    } catch (err) {
      alert(err.message || 'Failed to load demo sample');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleUploadVideo = async (formData, onProgress, onProcessing) => {
    const newVid = await api.uploadVideo(formData, onProgress);
    const vidList = await api.getVideos();
    setVideos(vidList);
    setCurrentVideo(newVid);
    setSystemNotice(`Uploaded "${newVid.title}". Starting pose tracking analysis.`);
    onProcessing?.();
    await handleRunAnalysis(newVid.id);
  };

  const handleOpenAuth = (mode = 'login') => {
    setAuthMode(mode);
    window.history.pushState({}, '', mode === 'reset' ? '/reset-password' : '/sign-in');
    setIsAuthRoute(true);
  };

  const handleCloseAuth = () => {
    window.history.pushState({}, '', '/');
    setAuthResetToken('');
    setIsAuthRoute(false);
  };

  const handleLogout = async () => {
    await api.logout();
    setCurrentUser(null);
    setVideos([]);
    setCurrentVideo(null);
    setBiomechanics(null);
    setInjuryRisk(null);
    setAthletes([]);
    window.history.replaceState({}, '', '/sign-in');
    setAuthMode('login');
    setSystemNotice('User session ended. Signed out successfully.');
  };

  const handleAuthSuccess = (user) => {
    setCurrentUser(user);
    if (user?.role) {
      setActiveRole(user.role);
    }
    setSystemNotice(`Welcome back, ${user.full_name} (${user.role}).`);
    window.history.replaceState({}, '', '/');
    loadInitialData();
  };

  const selectedAthlete = athletes.find(a => a.id === selectedAthleteId) || athletes[0];

  if (isCheckingAuth) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-center space-y-3">
          <Activity className="w-10 h-10 text-teal-400 animate-pulse mx-auto" />
          <p className="text-sm font-medium text-slate-300">Loading Kinematix workspace...</p>
        </div>
      </div>
    );
  }

  if (!currentUser) {
    const currentMode = {
      '/register': 'register',
      '/forgot-password': 'forgot',
      '/reset-password': 'reset'
    }[window.location.pathname] || 'login';

    return (
      <AuthPage
        onAuthSuccess={handleAuthSuccess}
        initialMode={currentMode}
        initialToken={authResetToken}
      />
    );
  }

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
            <span className={`w-2 h-2 rounded-full ${serviceHealth.status === 'healthy' ? 'bg-teal-600' : serviceHealth.status === 'offline' ? 'bg-rose-600' : 'bg-slate-400'}`}></span>
            <span className="text-slate-700 font-medium">{systemNotice}</span>
          </div>
          <div className="flex items-center space-x-3 text-[11px] font-mono text-slate-500">
            <span>Backend: <strong className={`font-semibold ${serviceHealth.status === 'healthy' ? 'text-teal-700' : serviceHealth.status === 'offline' ? 'text-rose-700' : 'text-slate-600'}`}>{serviceHealth.status === 'healthy' ? 'Online' : serviceHealth.status === 'offline' ? 'Offline' : 'Checking'}</strong></span>
            <span>Pose model: <strong className={`font-semibold ${serviceHealth.mediapipe_ready ? 'text-teal-700' : 'text-amber-700'}`}>{serviceHealth.mediapipe_ready ? 'Ready' : serviceHealth.status === 'healthy' ? 'Unavailable' : 'Unknown'}</strong></span>
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
            onLoadDemoSample={handleLoadDemoSample}
            onUploadVideo={handleUploadVideo}
            isAnalyzing={isAnalyzing}
          />
        )}

        {activeTab === 'comparison' && <VideoComparisonView videos={videos} />}

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

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-4 text-center text-xs text-slate-500 font-mono">
        Kinematix • Sports Movement Biomechanics &amp; Injury Risk Intelligence Platform
      </footer>
    </div>
  );
}
