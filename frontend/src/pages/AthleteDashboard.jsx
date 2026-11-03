import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import api from '../api/client';
import { useAuth } from '../context/AuthContext';
import { 
  ArrowLeft, 
  Upload, 
  Download, 
  User, 
  Activity, 
  Calendar,
  AlertCircle,
  CheckCircle,
  FileText
} from 'lucide-react';

export const AthleteDashboard = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { athleteId } = useParams();
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [exportingPdf, setExportingPdf] = useState(false);

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

  const handleDownloadReport = async (vidId = '') => {
    try {
      setExportingPdf(true);
      const profileId = dashboardData?.athlete?.id || athleteId;
      let url = `/reports/${profileId}/export/pdf?report_type=comprehensive`;
      if (vidId) url += `&video_id=${vidId}`;
      const res = await api.get(url, { responseType: 'blob' });
      const blob = new Blob([res.data], { type: 'application/pdf' });
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      const safeName = (dashboardData?.athlete?.name || 'Athlete').replace(/\s+/g, '_');
      link.download = `AthletiQ_Assessment_${safeName}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(downloadUrl);
    } catch (err) {
      console.error('Failed to export PDF:', err);
      alert('Could not download assessment report. Please ensure analysis data exists.');
    } finally {
      setExportingPdf(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto py-20 px-4 text-center">
        <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        <p className="text-sm text-slate-400">Loading athlete assessment...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-md mx-auto py-16 px-4 text-center">
        <div className="bg-rose-500/10 text-rose-300 border border-rose-500/20 p-5 rounded-xl text-sm mb-4">
          {error}
        </div>
        {error.includes('profile first') && (
          <button 
            onClick={() => navigate('/profile')} 
            className="bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium px-4 py-2 rounded-lg transition"
          >
            Create Athlete Profile
          </button>
        )}
      </div>
    );
  }

  if (!dashboardData) return null;

  const { 
    risk_score, 
    injury_predictions, 
    latest_analysis, 
    anomalies, 
    recommendations,
    video_count, 
    athlete,
    videos = [] 
  } = dashboardData;

  const coach = dashboardData.coach || athlete?.coach;
  const physiotherapist = dashboardData.physiotherapist || athlete?.physiotherapist;

  // Extract clean risk score and band
  const primaryRiskScore = risk_score?.injury_risk_score !== undefined && risk_score?.injury_risk_score !== null 
    ? risk_score.injury_risk_score 
    : (risk_score?.composite_score ?? 0);

  const rawBand = risk_score?.risk_band || risk_score?.risk_category || 'Low Risk';
  const cleanBand = rawBand.replace(/\s*\(.*?\)/g, '').trim();

  const getRiskBadge = (band) => {
    if (band.startsWith('Critical') || band.startsWith('High')) {
      return <span className="px-2.5 py-1 text-xs font-semibold rounded bg-rose-950/60 text-rose-300 border border-rose-800/60">{band}</span>;
    }
    if (band.startsWith('Moderate')) {
      return <span className="px-2.5 py-1 text-xs font-semibold rounded bg-amber-950/60 text-amber-300 border border-amber-800/60">{band}</span>;
    }
    return <span className="px-2.5 py-1 text-xs font-semibold rounded bg-emerald-950/60 text-emerald-300 border border-emerald-800/60">{band}</span>;
  };

  // Empirical kinematics values (actual measured or clean null)
  const kneeValgus = latest_analysis?.aggregates?.knee_valgus?.min_knee_ankle_ratio;
  const trunkLean = latest_analysis?.aggregates?.max_trunk_lean;
  const asymmetry = latest_analysis?.aggregates?.symmetry_index;
  const qualityScore = risk_score?.movement_quality_score ?? 90.0;

  return (
    <div className="max-w-6xl mx-auto py-8 px-4 sm:px-6 space-y-6">
      {/* Back button if staff viewing athlete */}
      {athleteId && (
        <button
          onClick={() => navigate('/athletes')}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-400 hover:text-white transition"
        >
          <ArrowLeft size={14} /> Back to Athletes Roster
        </button>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* 1. Header Profile & Assigned Coach Strip                           */}
      {/* ------------------------------------------------------------------ */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-white tracking-tight">
              {athlete?.name || (athleteId ? `Athlete #${athleteId}` : 'My Movement Assessment')}
            </h1>
            <span className="text-xs px-2.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 font-medium">
              {athlete?.sport_type || 'General Athletics'} {athlete?.position ? `• ${athlete.position}` : ''}
            </span>
          </div>
          
          <div className="flex flex-wrap items-center gap-4 mt-2 text-xs text-slate-400">
            <span><strong>Age:</strong> {athlete?.age || '—'}</span>
            <span>&bull;</span>
            <span><strong>Height:</strong> {athlete?.height_cm ? `${athlete.height_cm} cm` : '—'}</span>
            <span>&bull;</span>
            <span><strong>Weight:</strong> {athlete?.weight_kg ? `${athlete.weight_kg} kg` : '—'}</span>
            <span>&bull;</span>
            <span>
              <strong>Assigned Coach:</strong>{' '}
              {coach ? (
                <span className="text-slate-200">{coach.full_name}</span>
              ) : (
                <span className="text-slate-500">None {user?.role === 'athlete' && <Link to="/profile" className="text-indigo-400 underline ml-1">Assign</Link>}</span>
              )}
            </span>
            {physiotherapist && (
              <>
                <span>&bull;</span>
                <span><strong>Physiotherapist:</strong> <span className="text-slate-200">{physiotherapist.full_name}</span></span>
              </>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2.5 w-full md:w-auto">
          <button
            onClick={() => handleDownloadReport()}
            disabled={exportingPdf || video_count === 0}
            className="flex-1 md:flex-initial inline-flex items-center justify-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium px-4 py-2 rounded-lg transition disabled:opacity-40"
          >
            <Download size={14} />
            {exportingPdf ? 'Exporting PDF...' : 'Download Report (PDF)'}
          </button>
          
          {user?.role === 'athlete' && (
            <Link 
              to="/upload" 
              className="flex-1 md:flex-initial inline-flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium px-4 py-2 rounded-lg transition"
            >
              <Upload size={14} /> Upload Video
            </Link>
          )}
        </div>
      </div>

      {video_count === 0 ? (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-10 text-center space-y-3">
          <Activity size={32} className="mx-auto text-slate-500" />
          <h2 className="text-base font-semibold text-white">No Movement Trials Screened Yet</h2>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            Upload a movement video (squat, jump landing, sprint, cutting) to run pose estimation and evaluate injury risk factors.
          </p>
          <div className="pt-2">
            <Link 
              to="/upload" 
              className="inline-flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium px-4 py-2 rounded-lg transition"
            >
              <Upload size={14} /> Upload Video Trial
            </Link>
          </div>
        </div>
      ) : (
        <>
          {/* ------------------------------------------------------------------ */}
          {/* 2. Primary Assessment Overview (Score & Quality)                   */}
          {/* ------------------------------------------------------------------ */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Risk Score */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-2">
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wider block">Injury Risk Score</span>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-bold text-white">{primaryRiskScore.toFixed(1)}</span>
                <span className="text-xs text-slate-400">/ 100</span>
              </div>
              <div>{getRiskBadge(cleanBand)}</div>
              <p className="text-xs text-slate-400 pt-1 border-t border-slate-800/80">
                Weighted index based on biomechanical deviation, symmetry, and injury history.
              </p>
            </div>

            {/* Movement Quality Score */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-2">
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wider block">Movement Quality Score</span>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-bold text-white">{qualityScore.toFixed(1)}</span>
                <span className="text-xs text-slate-400">/ 100</span>
              </div>
              <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 font-medium inline-block">
                {qualityScore >= 80 ? 'Optimal Technique' : qualityScore >= 60 ? 'Moderate Compensations' : 'Movement Breakdown'}
              </span>
              <p className="text-xs text-slate-400 pt-1 border-t border-slate-800/80">
                Evaluation against normative biomechanical standards for movement mechanics.
              </p>
            </div>

            {/* Screening Summary */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-2">
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wider block">Screening Status</span>
              <div className="text-3xl font-bold text-white">{video_count}</div>
              <span className="text-xs text-slate-400 block">Completed Movement Trials</span>
              <p className="text-xs text-slate-400 pt-1 border-t border-slate-800/80">
                Latest trial screened on {videos[0]?.created_at || 'Recent'}.
              </p>
            </div>
          </div>

          {/* ------------------------------------------------------------------ */}
          {/* 3. Measured Biomechanical Indicators                               */}
          {/* ------------------------------------------------------------------ */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <h2 className="text-sm font-semibold text-white tracking-tight">
              Biomechanical Indicators (Latest Trial)
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {/* Knee Valgus */}
              <div className="bg-slate-950/50 border border-slate-800 p-3.5 rounded-lg">
                <span className="text-xs text-slate-400 block mb-1">Dynamic Knee Valgus</span>
                <div className="text-xl font-bold text-white">
                  {kneeValgus !== undefined && kneeValgus !== null ? Number(kneeValgus).toFixed(2) : '—'}
                  <span className="text-xs font-normal text-slate-400 ml-1">ratio</span>
                </div>
                <span className="text-[11px] text-slate-400 block mt-1">Normative threshold: &ge; 0.85</span>
              </div>

              {/* Trunk Lean */}
              <div className="bg-slate-950/50 border border-slate-800 p-3.5 rounded-lg">
                <span className="text-xs text-slate-400 block mb-1">Max Trunk Lean</span>
                <div className="text-xl font-bold text-white">
                  {trunkLean !== undefined && trunkLean !== null ? `${Number(trunkLean).toFixed(1)}°` : '—'}
                </div>
                <span className="text-[11px] text-slate-400 block mt-1">Normative threshold: &lt; 30.0°</span>
              </div>

              {/* Symmetry */}
              <div className="bg-slate-950/50 border border-slate-800 p-3.5 rounded-lg">
                <span className="text-xs text-slate-400 block mb-1">Limb Movement Asymmetry</span>
                <div className="text-xl font-bold text-white">
                  {asymmetry !== undefined && asymmetry !== null ? `${Number(asymmetry).toFixed(1)}%` : '—'}
                </div>
                <span className="text-[11px] text-slate-400 block mt-1">Normative threshold: &lt; 15.0%</span>
              </div>
            </div>
          </div>

          {/* ------------------------------------------------------------------ */}
          {/* 4. Injury Risk Categories Breakdown                                */}
          {/* ------------------------------------------------------------------ */}
          {injury_predictions?.categories && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
              <h2 className="text-sm font-semibold text-white tracking-tight">
                Injury Risk Categories
              </h2>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {Object.entries(injury_predictions.categories).map(([key, cat]) => (
                  <div key={key} className="bg-slate-950/50 border border-slate-800 p-3.5 rounded-lg flex flex-col justify-between">
                    <div>
                      <div className="flex justify-between items-center mb-1.5">
                        <span className="text-xs font-medium text-slate-200">{cat.name}</span>
                        <span className={`text-[11px] font-semibold px-2 py-0.5 rounded ${
                          cat.risk_level === 'High' || cat.risk_level === 'Critical'
                            ? 'bg-rose-950/60 text-rose-300 border border-rose-800/60'
                            : cat.risk_level === 'Moderate'
                            ? 'bg-amber-950/60 text-amber-300 border border-amber-800/60'
                            : 'bg-emerald-950/60 text-emerald-300 border border-emerald-800/60'
                        }`}>
                          {cat.risk_level} ({cat.probability_pct}%)
                        </span>
                      </div>
                      
                      {cat.risk_factors && cat.risk_factors.length > 0 && (
                        <p className="text-[11px] text-slate-400 line-clamp-2 mt-1">
                          Factors: {cat.risk_factors.join(', ')}
                        </p>
                      )}
                    </div>

                    {cat.prevention_protocols && cat.prevention_protocols[0] && (
                      <div className="pt-2 mt-2 border-t border-slate-800/60 text-[11px] text-slate-400">
                        Focus: <span className="text-slate-300">{cat.prevention_protocols[0]}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ------------------------------------------------------------------ */}
          {/* 5. Movement Concerns & Corrective Drills (2 Columns)               */}
          {/* ------------------------------------------------------------------ */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Movement Concerns */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
              <h2 className="text-sm font-semibold text-white tracking-tight flex items-center gap-2">
                <AlertCircle size={15} className="text-amber-400" />
                <span>Detected Movement Deviations</span>
              </h2>

              {(!anomalies || anomalies.length === 0) ? (
                <p className="text-xs text-slate-400 py-4">No significant movement anomalies detected. Movement mechanics within reference boundaries.</p>
              ) : (
                <ul className="divide-y divide-slate-800 text-xs">
                  {anomalies.slice(0, 5).map((a, i) => (
                    <li key={i} className="py-2.5 flex items-start justify-between gap-3">
                      <div>
                        <span className="font-medium text-slate-200 block">{a.metric.replace(/_/g, ' ')}</span>
                        <span className="text-slate-400 text-[11px]">{a.explanation || `Observed: ${a.observed_value}`}</span>
                      </div>
                      <span className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded shrink-0 ${
                        a.severity === 'critical' || a.severity === 'high' ? 'bg-rose-950/60 text-rose-300' : 'bg-amber-950/60 text-amber-300'
                      }`}>
                        {a.severity}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Recommendations */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
              <h2 className="text-sm font-semibold text-white tracking-tight flex items-center gap-2">
                <CheckCircle size={15} className="text-emerald-400" />
                <span>Targeted Corrective Recommendations</span>
              </h2>

              {(!recommendations || recommendations.length === 0) ? (
                <p className="text-xs text-slate-400 py-4">Maintain current training schedule and movement warmup protocols.</p>
              ) : (
                <ul className="divide-y divide-slate-800 text-xs">
                  {recommendations.slice(0, 5).map((r, i) => (
                    <li key={i} className="py-2.5 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-slate-200">{r.title || r.exercise}</span>
                        <span className="text-[11px] text-indigo-400 font-medium">{r.sets_reps || r.frequency || 'Daily'}</span>
                      </div>
                      <p className="text-[11px] text-slate-400">{r.description || r.purpose}</p>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {/* ------------------------------------------------------------------ */}
          {/* 6. Screening History Table                                         */}
          {/* ------------------------------------------------------------------ */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
            <h2 className="text-sm font-semibold text-white tracking-tight">
              Screening History
            </h2>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950/60 text-slate-400 border-b border-slate-800 font-medium">
                  <tr>
                    <th className="px-3.5 py-2.5">Trial</th>
                    <th className="px-3.5 py-2.5">Activity</th>
                    <th className="px-3.5 py-2.5">Date</th>
                    <th className="px-3.5 py-2.5">Tracking Quality</th>
                    <th className="px-3.5 py-2.5 text-right">Report</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800 text-slate-300">
                  {videos.map((vid) => (
                    <tr key={vid.id} className="hover:bg-slate-800/40 transition">
                      <td className="px-3.5 py-2.5 font-medium text-white">Trial #{vid.id}</td>
                      <td className="px-3.5 py-2.5 capitalize">{vid.movement_type || 'General'}</td>
                      <td className="px-3.5 py-2.5 text-slate-400">{vid.created_at || 'Recent'}</td>
                      <td className="px-3.5 py-2.5">
                        {vid.quality_score !== null && vid.quality_score !== undefined
                          ? `${Number(vid.quality_score).toFixed(0)}%`
                          : 'Processed'}
                      </td>
                      <td className="px-3.5 py-2.5 text-right">
                        <button
                          onClick={() => handleDownloadReport(vid.id)}
                          className="inline-flex items-center gap-1 text-indigo-400 hover:text-indigo-300 font-medium"
                        >
                          <FileText size={12} /> PDF
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default AthleteDashboard;
