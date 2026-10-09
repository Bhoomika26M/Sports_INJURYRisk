import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import VideoStudio from './components/VideoStudio';
import BiomechanicalAnalysisView from './components/BiomechanicalAnalysisView';
import InjuryRiskView from './components/InjuryRiskView';
import RecommendationsView from './components/RecommendationsView';
import RoleDashboards from './components/RoleDashboards';
import AthleteManagement from './components/AthleteManagement';
import DatasetsView from './components/DatasetsView';
import { api } from './api/client';
import { Activity, Sparkles, CheckCircle2 } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('video_studio');
  const [activeRole, setActiveRole] = useState('athlete');
  const [athletes, setAthletes] = useState([]);
  const [selectedAthleteId, setSelectedAthleteId] = useState(1);
  const [videos, setVideos] = useState([]);
  const [currentVideo, setCurrentVideo] = useState(null);
  const [biomechanics, setBiomechanics] = useState(null);
  const [injuryRisk, setInjuryRisk] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [systemNotice, setSystemNotice] = useState('System initialized: Milestone 1, 2, and 3 operational.');

  // Load athletes and videos on mount
  useEffect(() => {
    loadInitialData();
  }, []);

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
      setSystemNotice('Sample video generated. Running AI Pose Estimation...');
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

  const selectedAthlete = athletes.find(a => a.id === selectedAthleteId) || athletes[0];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-cyan-500/30 selection:text-cyan-200">
      {/* Top Navigation */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        activeRole={activeRole}
        setActiveRole={setActiveRole}
        athletes={athletes}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* System Status Notification Strip */}
        <div className="flex items-center justify-between bg-slate-900/50 px-4 py-2 rounded-xl border border-slate-800 text-xs">
          <div className="flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span>
            <span className="text-slate-400">{systemNotice}</span>
          </div>
          <div className="flex items-center space-x-3 text-[11px] font-mono text-slate-400">
            <span>FastAPI Backend: <strong className="text-emerald-400">Online</strong></span>
            <span>MediaPipe Pose: <strong className="text-cyan-400">v1.1.0 Ready</strong></span>
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
      <footer className="border-t border-slate-900 bg-slate-950 py-4 text-center text-xs text-slate-500 font-mono">
        Sports Injury Risk Detection Platform • Developed through Milestone 3 (Pose Estimation, Biomechanics & Injury Prediction Engine)
      </footer>
    </div>
  );
}
