import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import api from '../api/client';
import { useAuth } from '../context/AuthContext';
import AnomalyTimeline from '../components/AnomalyTimeline';
import { RecommendationPanel } from '../components/RecommendationPanel';
import { ReportsExportModal } from '../components/ReportsExportModal';
import { ArrowLeft, ShieldCheck, Activity, Upload, ChevronRight, Users, Award, Stethoscope, Settings, AlertTriangle, Zap, Heart, Gauge, FileText, Download } from 'lucide-react';

export const AthleteDashboard = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { athleteId } = useParams();
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [reportsModalOpen, setReportsModalOpen] = useState(false);

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        setLoading(true);
        setError(null);
        let endpoint = '/dashboard/me';
        if (athleteId) {
          endpoint = `/dashboard/athlete/${athleteId}`;
        } else if (user?.role !== 'athlete') {
          navigate('/dashboard', { replace: true });
          return;
        }

        const res = await api.get(endpoint);
        setDashboardData(res.data);
      } catch (err) {
        if (err.response?.status === 404) {
          setError('Profile not found. Please create an athlete profile first.');
        } else if (err.response?.status === 403) {
          setError('You are not authorized to view this athlete dashboard.');
        } else {
          setError('Failed to load dashboard data.');
        }
      } finally {
        setLoading(false);
      }
    };

    if (user) {
      fetchDashboard();
    }
  }, [user, athleteId, navigate]);

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto py-16 px-4 text-center">
        <div className="w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        <p className="text-xs text-slate-500 font-medium">Loading athlete metrics & kinematics...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 max-w-xl mx-auto text-center">
        <div className="bg-red-50 text-red-700 p-5 rounded-2xl border border-red-200 text-xs font-medium mb-4">
          {error}
        </div>
        {error.includes('profile first') && (
          <button 
            onClick={() => navigate('/profile')} 
            className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold px-4 py-2 rounded-xl transition"
          >
            Create Athlete Profile
          </button>
        )}
      </div>
    );
  }

  if (!dashboardData) return null;

  const { risk_score, injury_predictions, latest_analysis, anomalies, anomaly_overview, trend_data, video_count, athlete } = dashboardData;
  const coach = dashboardData.coach || athlete?.coach;
  const physiotherapist = dashboardData.physiotherapist || athlete?.physiotherapist;

  const getRiskBandBadge = (band) => {
    if (!band) return <span className="text-slate-500 font-semibold">Unknown</span>;
    if (band.startsWith('Low')) {
      return <span className="bg-emerald-50 text-emerald-700 border border-emerald-200 px-2.5 py-0.5 rounded-full text-xs font-bold">{band}</span>;
    }
    if (band.startsWith('Moderate')) {
      return <span className="bg-amber-50 text-amber-700 border border-amber-200 px-2.5 py-0.5 rounded-full text-xs font-bold">{band}</span>;
    }
    if (band.startsWith('High')) {
      return <span className="bg-orange-50 text-orange-700 border border-orange-200 px-2.5 py-0.5 rounded-full text-xs font-bold">{band}</span>;
    }
    return <span className="bg-rose-50 text-rose-700 border border-rose-200 px-2.5 py-0.5 rounded-full text-xs font-bold">{band}</span>;
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-6xl mx-auto space-y-6">
      {/* Back button if staff viewing athlete */}
      {athleteId && (
        <button
          onClick={() => navigate('/athletes')}
          className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-blue-600 transition"
        >
          <ArrowLeft size={15} /> Back to Athletes Directory
        </button>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            {athleteId ? `Athlete Movement Screening (#${athleteId})` : 'My Movement & Injury Risk Overview'}
          </h1>
          <p className="text-slate-500 text-xs mt-0.5">
            Biomechanical analysis, bilateral symmetry tracking, and clinical risk scoring.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setReportsModalOpen(true)}
            className="bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 font-semibold text-xs py-2.5 px-4 rounded-xl shadow-xs transition flex items-center gap-1.5"
            title="Download PDF & Excel Reports"
          >
            <FileText size={14} className="text-blue-600" /> Export Reports
          </button>
          {user?.role === 'athlete' && (
            <Link 
              to="/upload" 
              className="bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs py-2.5 px-4 rounded-xl shadow-xs transition flex items-center gap-1.5"
            >
              <Upload size={14} /> Upload Video
            </Link>
          )}
        </div>
      </div>

      {video_count === 0 ? (
        <div className="bg-white p-10 rounded-2xl shadow-xs border border-slate-200 text-center">
          <div className="w-12 h-12 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mx-auto mb-3">
            <Activity size={24} />
          </div>
          <h2 className="text-base font-bold text-slate-800 mb-1">No Movement Videos Analyzed Yet</h2>
          <p className="text-xs text-slate-500 mb-5 max-w-md mx-auto">
            Upload your first video of a squat, running gait, or jump-landing test to generate your biomechanical profile and risk assessment.
          </p>
          <Link 
            to="/upload" 
            className="inline-flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold px-4 py-2.5 rounded-xl shadow-xs transition"
          >
            <Upload size={14} /> Upload Video
          </Link>
        </div>
      ) : (
        <>
          {/* Clinical Disclaimer Callout */}
          <div className="bg-blue-50/60 border border-blue-100 rounded-xl p-3.5 text-xs text-blue-900 flex items-start gap-2.5">
            <ShieldCheck size={16} className="text-blue-600 shrink-0 mt-0.5" />
            <p className="leading-relaxed">
              <strong>Clinical Advisory:</strong> This screening index is a preventive biomechanical assessment based on computer vision tracking. It does not replace a diagnostic clinical consultation with a sports physician or licensed physiotherapist.
            </p>
          </div>

          {/* Module 8: Risk Scoring Engine - 5 Explicit Scores */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5">
            {/* Score 1: Injury Risk Score */}
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Injury Risk</span>
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${
                  (risk_score?.injury_risk_score ?? risk_score?.composite_score ?? 0) >= 65 ? 'bg-rose-50 text-rose-700 border border-rose-200' :
                  (risk_score?.injury_risk_score ?? risk_score?.composite_score ?? 0) >= 35 ? 'bg-amber-50 text-amber-700 border border-amber-200' :
                  'bg-emerald-50 text-emerald-700 border border-emerald-200'
                }`}>
                  {risk_score?.risk_category || 'Low Risk'}
                </span>
              </div>
              <div className="text-2xl font-black text-slate-900">
                {risk_score?.injury_risk_score !== undefined && risk_score?.injury_risk_score !== null ? risk_score.injury_risk_score.toFixed(1) : (risk_score?.composite_score?.toFixed(1) ?? 'N/A')}
                <span className="text-xs font-normal text-slate-400">/100</span>
              </div>
              <span className="text-[10px] text-slate-500 mt-1 block">Weighted risk model</span>
            </div>

            {/* Score 2: Movement Quality */}
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Movement Quality</span>
                <Activity size={13} className="text-blue-500" />
              </div>
              <div className="text-2xl font-black text-slate-900">
                {risk_score?.movement_quality_score !== undefined ? risk_score.movement_quality_score.toFixed(1) : '100.0'}
                <span className="text-xs font-normal text-slate-400">/100</span>
              </div>
              <span className="text-[10px] text-slate-500 mt-1 block">Kinematic execution</span>
            </div>

            {/* Score 3: Biomechanical Efficiency */}
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Bio Efficiency</span>
                <Gauge size={13} className="text-indigo-500" />
              </div>
              <div className="text-2xl font-black text-slate-900">
                {risk_score?.biomechanical_efficiency_score !== undefined ? risk_score.biomechanical_efficiency_score.toFixed(1) : '100.0'}
                <span className="text-xs font-normal text-slate-400">/100</span>
              </div>
              <span className="text-[10px] text-slate-500 mt-1 block">Symmetry & alignment</span>
            </div>

            {/* Score 4: Fatigue Risk */}
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Fatigue Risk</span>
                <Zap size={13} className="text-amber-500" />
              </div>
              <div className="text-2xl font-black text-slate-900">
                {risk_score?.fatigue_risk_score !== undefined ? risk_score.fatigue_risk_score.toFixed(1) : '0.0'}
                <span className="text-xs font-normal text-slate-400">/100</span>
              </div>
              <span className="text-[10px] text-slate-500 mt-1 block">Acute & chronic load</span>
            </div>

            {/* Score 5: Overall Health */}
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs col-span-2 sm:col-span-1">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Overall Health</span>
                <Heart size={13} className="text-rose-500" />
              </div>
              <div className="text-2xl font-black text-slate-900">
                {risk_score?.overall_athlete_health_score !== undefined ? risk_score.overall_athlete_health_score.toFixed(1) : '100.0'}
                <span className="text-xs font-normal text-slate-400">/100</span>
              </div>
              <span className="text-[10px] text-slate-500 mt-1 block">Composite vitality index</span>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            {/* Composite Risk Score Card */}
            <div className="bg-white p-6 rounded-2xl shadow-xs border border-slate-200 lg:col-span-2 flex flex-col justify-between">
              <div>
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                      Composite Injury Risk Index
                    </span>
                    <div className="text-3xl font-black text-slate-900 mt-1 flex items-baseline gap-1">
                      {risk_score?.composite_score !== null ? risk_score.composite_score.toFixed(1) : 'N/A'}
                      <span className="text-sm font-normal text-slate-400">/ 100</span>
                    </div>
                  </div>
                  <div>
                    {getRiskBandBadge(risk_score?.risk_band)}
                  </div>
                </div>

                {/* Progress bar */}
                <div className="w-full bg-slate-100 rounded-full h-2 mb-4 overflow-hidden">
                  <div 
                    className={`h-full transition-all duration-500 ${
                      (risk_score?.composite_score || 0) > 60 ? 'bg-rose-500' :
                      (risk_score?.composite_score || 0) > 30 ? 'bg-amber-500' : 'bg-emerald-500'
                    }`}
                    style={{ width: `${Math.min(risk_score?.composite_score || 0, 100)}%` }}
                  />
                </div>

                <div className="flex items-center justify-between text-xs text-slate-600 py-3 border-y border-slate-100">
                  <span className="text-slate-400">Screening Confidence Index:</span>
                  <strong className="text-slate-800">{risk_score?.confidence_score?.toFixed(0) || 0}%</strong>
                </div>
              </div>

              {risk_score?.contributing_factors?.length > 0 && (
                <div className="mt-4 pt-2">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block mb-2">
                    Key Contributing Factors:
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {risk_score.contributing_factors.map((factor, i) => (
                      <span key={i} className="bg-slate-100 text-slate-700 text-xs px-2.5 py-1 rounded-lg">
                        {factor}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Quick Metrics Card */}
            <div className="bg-white p-6 rounded-2xl shadow-xs border border-slate-200 flex flex-col justify-between">
              <div>
                <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block mb-3">
                  Latest Movement Metrics
                </span>
                {latest_analysis ? (
                  <div className="space-y-3 text-xs">
                    <div className="flex justify-between items-center py-1.5 border-b border-slate-100">
                      <span className="text-slate-500">Symmetry Index</span>
                      <strong className="text-slate-900">{latest_analysis.aggregates?.symmetry_index ?? 'N/A'}° diff</strong>
                    </div>
                    <div className="flex justify-between items-center py-1.5 border-b border-slate-100">
                      <span className="text-slate-500">Max Trunk Lean</span>
                      <strong className="text-slate-900">{latest_analysis.aggregates?.max_trunk_lean ?? 'N/A'}°</strong>
                    </div>
                    <div className="flex justify-between items-center py-1.5 border-b border-slate-100">
                      <span className="text-slate-500">Left Knee Flexion Min</span>
                      <strong className="text-slate-900">{latest_analysis.aggregates?.left_knee_min ?? 'N/A'}°</strong>
                    </div>
                    <div className="flex justify-between items-center py-1.5">
                      <span className="text-slate-500">Right Knee Flexion Min</span>
                      <strong className="text-slate-900">{latest_analysis.aggregates?.right_knee_min ?? 'N/A'}°</strong>
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-slate-400 py-4">No completed analysis metrics available.</p>
                )}
              </div>

              {user?.role === 'athlete' && (
                <Link 
                  to="/upload" 
                  className="mt-4 text-xs font-semibold text-blue-600 hover:text-blue-800 flex items-center justify-center gap-1 py-1.5 rounded-lg bg-blue-50/50 hover:bg-blue-50 transition"
                >
                  Manage Movement Videos <ChevronRight size={14} />
                </Link>
              )}
            </div>
          </div>

          {/* Module 7: Movement Anomaly & Technique Assessment */}
          {anomaly_overview && (
            <div className="bg-white p-6 rounded-2xl shadow-xs border border-slate-200 space-y-4">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
                <div>
                  <h2 className="text-base font-bold text-slate-900 tracking-tight flex items-center gap-2">
                    <Activity size={18} className="text-indigo-600" />
                    <span>Movement Anomaly & Technique Assessment</span>
                  </h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Technique grading, execution faults, motion inconsistency analysis, and intra-trial fatigue drift.
                  </p>
                </div>
                {anomaly_overview.technique_assessment && (
                  <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${
                    anomaly_overview.technique_assessment.technique_grade === 'Optimal' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' :
                    anomaly_overview.technique_assessment.technique_grade === 'Good' ? 'bg-blue-50 text-blue-700 border border-blue-200' :
                    anomaly_overview.technique_assessment.technique_grade === 'Suboptimal' ? 'bg-amber-50 text-amber-700 border border-amber-200' :
                    'bg-rose-50 text-rose-700 border border-rose-200'
                  }`}>
                    Technique: {anomaly_overview.technique_assessment.technique_grade} ({anomaly_overview.technique_assessment.technique_score}/100)
                  </span>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-1">
                {/* 1. Technique & Faults */}
                <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-2">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                    Execution Mechanics & Faults
                  </span>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    {anomaly_overview.technique_assessment?.execution_summary || "Kinematic patterns evaluated against standard biomechanical planes."}
                  </p>
                  {anomaly_overview.technique_assessment?.primary_faults?.length > 0 && (
                    <ul className="text-[11px] text-slate-700 space-y-1 pt-1">
                      {anomaly_overview.technique_assessment.primary_faults.map((fault, idx) => (
                        <li key={idx} className="flex items-start gap-1.5">
                          <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 mt-1.5 shrink-0" />
                          <span>{fault}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                {/* 2. Motion Inconsistency */}
                <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-2">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                    Motion Inconsistency & Smoothness
                  </span>
                  <div className="flex justify-between items-center text-xs pt-1">
                    <span className="text-slate-500">Consistency Rating</span>
                    <strong className="text-slate-900">{anomaly_overview.motion_inconsistency?.consistency_rating || "Consistent"}</strong>
                  </div>
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-slate-500">Smoothness / Jerk Index</span>
                    <strong className="text-slate-900">{anomaly_overview.motion_inconsistency?.smoothness_jerk_score?.toFixed(1) || "90.0"}/100</strong>
                  </div>
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-slate-500">Coeff. of Variation</span>
                    <strong className="text-slate-900">{anomaly_overview.motion_inconsistency?.coefficient_of_variation_pct?.toFixed(1) || "0.0"}%</strong>
                  </div>
                  <div className="flex justify-between items-center text-xs pt-1 border-t border-slate-200/60">
                    <span className="text-slate-500">Movement Deviations</span>
                    <strong className="text-indigo-600 font-bold">{anomaly_overview.movement_deviations_count || 0} flagged</strong>
                  </div>
                </div>

                {/* 3. Fatigue & Decline Alerts */}
                <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-2">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                    Fatigue Monitoring & Performance Alerts
                  </span>
                  {(anomaly_overview.fatigue_indicators?.length > 0 || anomaly_overview.performance_decline_alerts?.length > 0) ? (
                    <div className="space-y-2 pt-1">
                      {anomaly_overview.fatigue_indicators?.map((ind, idx) => (
                        <div key={idx} className="p-2 rounded-lg bg-amber-50/80 border border-amber-200 text-[11px] text-amber-900 flex items-start gap-1.5">
                          <Zap size={12} className="text-amber-600 mt-0.5 shrink-0" />
                          <span>{ind}</span>
                        </div>
                      ))}
                      {anomaly_overview.performance_decline_alerts?.map((alert, idx) => (
                        <div key={idx} className="p-2 rounded-lg bg-rose-50/80 border border-rose-200 text-[11px] text-rose-900 flex items-start gap-1.5">
                          <AlertTriangle size={12} className="text-rose-600 mt-0.5 shrink-0" />
                          <span>{alert}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-slate-500 pt-1">
                      No kinematic fatigue drift or performance decline alerts flagged across this trial. Movement kinematics remained stable.
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Module 6: Injury Risk Prediction Engine - 6 Categories */}
          {injury_predictions?.categories && (
            <div className="bg-white p-6 rounded-2xl shadow-xs border border-slate-200 space-y-4">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
                <div>
                  <h2 className="text-base font-bold text-slate-900 tracking-tight flex items-center gap-2">
                    <ShieldCheck size={18} className="text-blue-600" />
                    <span>Injury Risk Prediction Engine</span>
                  </h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Evidence-based injury probabilities calibrated against kinematic screening and athlete profile context.
                  </p>
                </div>
                {injury_predictions.high_risk_alerts_count > 0 && (
                  <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-rose-50 text-rose-700 border border-rose-200 flex items-center gap-1.5">
                    <AlertTriangle size={13} />
                    {injury_predictions.high_risk_alerts_count} High-Risk Movement Alert{injury_predictions.high_risk_alerts_count > 1 ? 's' : ''}
                  </span>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pt-1">
                {Object.entries(injury_predictions.categories).map(([key, cat]) => {
                  const isHigh = cat.risk_level === 'High' || cat.risk_level === 'Critical';
                  const isMod = cat.risk_level === 'Moderate';
                  return (
                    <div 
                      key={key} 
                      className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-white hover:border-slate-300 transition flex flex-col justify-between"
                    >
                      <div>
                        <div className="flex justify-between items-start gap-2 mb-2">
                          <h3 className="font-bold text-xs text-slate-900">{cat.name}</h3>
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            isHigh ? 'bg-rose-50 text-rose-700 border border-rose-200' :
                            isMod ? 'bg-amber-50 text-amber-700 border border-amber-200' :
                            'bg-emerald-50 text-emerald-700 border border-emerald-200'
                          }`}>
                            {cat.risk_level} ({cat.probability_pct}%)
                          </span>
                        </div>

                        {/* Progress Bar */}
                        <div className="w-full bg-slate-200 rounded-full h-1.5 mb-3 overflow-hidden">
                          <div 
                            className={`h-full rounded-full transition-all duration-300 ${
                              isHigh ? 'bg-rose-500' : isMod ? 'bg-amber-500' : 'bg-emerald-500'
                            }`}
                            style={{ width: `${Math.min(cat.probability_pct, 100)}%` }}
                          />
                        </div>

                        {/* Risk Factors */}
                        <div className="space-y-1 mb-3">
                          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                            Key Drivers:
                          </span>
                          <ul className="text-[11px] text-slate-600 space-y-0.5">
                            {cat.risk_factors.slice(0, 2).map((rf, idx) => (
                              <li key={idx} className="line-clamp-1 flex items-center gap-1.5">
                                <span className="w-1 h-1 rounded-full bg-slate-400 shrink-0" />
                                <span>{rf}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      </div>

                      {/* Corrective Focus */}
                      {cat.prevention_protocols && cat.prevention_protocols.length > 0 && (
                        <div className="pt-2.5 border-t border-slate-200/70 text-[10px] text-slate-500">
                          <strong className="text-slate-700 block mb-0.5">Corrective Focus:</strong>
                          <span className="line-clamp-1 text-slate-600">{cat.prevention_protocols[0]}</span>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Coaching & Clinical Staff Card */}
          <div className="bg-white p-5 rounded-2xl shadow-xs border border-slate-200">
            <div className="flex justify-between items-center mb-3">
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-2">
                <Users size={16} className="text-blue-600" />
                <span>My Coaching & Clinical Support Team</span>
              </h2>
              {user?.role === 'athlete' && (
                <Link
                  to="/profile"
                  className="text-xs font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-1"
                >
                  <Settings size={13} /> Change Staff
                </Link>
              )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              <div className="p-3.5 rounded-xl border border-slate-100 bg-slate-50/70 flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-700 flex items-center justify-center shrink-0">
                  <Award size={16} />
                </div>
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-700 block">
                    Head Coach
                  </span>
                  {coach ? (
                    <>
                      <div className="text-xs font-bold text-slate-900 mt-0.5">{coach.full_name}</div>
                      <div className="text-[11px] text-slate-500">{coach.email}</div>
                      {coach.organization && (
                        <div className="text-[10px] text-slate-400 mt-0.5">{coach.organization}</div>
                      )}
                    </>
                  ) : (
                    <div className="text-xs text-slate-400 mt-1">
                      No Head Coach assigned. {user?.role === 'athlete' && (
                        <Link to="/profile" className="text-blue-600 underline ml-1">Assign in profile</Link>
                      )}
                    </div>
                  )}
                </div>
              </div>

              <div className="p-3.5 rounded-xl border border-slate-100 bg-slate-50/70 flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-teal-50 text-teal-700 flex items-center justify-center shrink-0">
                  <Stethoscope size={16} />
                </div>
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-teal-700 block">
                    Physiotherapist
                  </span>
                  {physiotherapist ? (
                    <>
                      <div className="text-xs font-bold text-slate-900 mt-0.5">{physiotherapist.full_name}</div>
                      <div className="text-[11px] text-slate-500">{physiotherapist.email}</div>
                      {physiotherapist.specialization && (
                        <div className="text-[10px] text-slate-400 mt-0.5">{physiotherapist.specialization}</div>
                      )}
                    </>
                  ) : (
                    <div className="text-xs text-slate-400 mt-1">
                      No Physiotherapist assigned. {user?.role === 'athlete' && (
                        <Link to="/profile" className="text-blue-600 underline ml-1">Assign in profile</Link>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Trend & Components Breakdown */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* Symmetry Trend Chart */}
            <div className="bg-white p-6 rounded-2xl shadow-xs border border-slate-200">
              <h2 className="text-sm font-bold text-slate-800 mb-3">Symmetry Trend (Recent Screenings)</h2>
              {trend_data && trend_data.length > 1 ? (
                <div className="h-56 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={trend_data}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                      <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 11 }} domain={[0, 'auto']} />
                      <Tooltip />
                      <Line type="monotone" dataKey="symmetry_index" stroke="#2563eb" strokeWidth={2} name="Symmetry Index (°)" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="h-56 w-full flex items-center justify-center bg-slate-50 rounded-xl border border-dashed border-slate-200 text-xs text-slate-400">
                  Upload at least 2 videos to view longitudinal symmetry progression.
                </div>
              )}
            </div>

            {/* Components Breakdown */}
            <div className="bg-white p-6 rounded-2xl shadow-xs border border-slate-200">
              <h2 className="text-sm font-bold text-slate-800 mb-3">Risk Factor Components</h2>
              <div className="space-y-3.5">
                {risk_score?.components && Object.entries(risk_score.components).map(([key, comp]) => (
                  <div key={key}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="capitalize font-medium text-slate-700">{key.replace(/_/g, ' ')}</span>
                      <span className="text-slate-400 font-medium">
                        {comp.is_missing ? 'No Data' : `${comp.score?.toFixed(1)} / 100`}
                      </span>
                    </div>
                    <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                      <div 
                        className={`h-full rounded-full transition-all duration-300 ${
                          comp.is_missing ? 'bg-slate-300' :
                          comp.score > 60 ? 'bg-rose-500' :
                          comp.score > 30 ? 'bg-amber-500' : 'bg-emerald-500'
                        }`} 
                        style={{ width: `${comp.is_missing ? 100 : comp.score}%`, opacity: comp.is_missing ? 0.3 : 1 }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Actionable Recommendations & Anomalies */}
          <div className="bg-white p-6 rounded-2xl shadow-xs border border-slate-200">
            <h2 className="text-sm font-bold text-slate-800 mb-4">Latest Insights & Action Plan</h2>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div>
                <RecommendationPanel videoId={latest_analysis?.video_id} />
              </div>
              <div>
                <AnomalyTimeline anomalies={anomalies} />
              </div>
            </div>
          </div>
        </>
      )}

      {/* Reports & Clinical Export Modal */}
      <ReportsExportModal
        isOpen={reportsModalOpen}
        onClose={() => setReportsModalOpen(false)}
        athleteId={athlete?.id || dashboardData?.athlete_id || athleteId}
        athleteName={athlete?.name}
        videos={dashboardData?.videos || []}
      />
    </div>
  );
};
