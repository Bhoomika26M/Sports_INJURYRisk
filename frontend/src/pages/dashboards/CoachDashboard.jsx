import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../../api/client';
import { useAuth } from '../../context/AuthContext';
import {
  Award,
  Users,
  ShieldAlert,
  ShieldCheck,
  TrendingUp,
  Activity,
  AlertCircle,
  Search,
  CheckCircle2,
  ChevronRight,
  UserPlus,
  UserMinus,
  Sparkles,
  BarChart3,
  Clock,
  FileText,
  FileSpreadsheet
} from 'lucide-react';
import { ReportsExportModal } from '../../components/ReportsExportModal';

export const CoachDashboard = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [squadFilter, setSquadFilter] = useState('all'); // 'all' | 'squad'
  const [search, setSearch] = useState('');
  const [actionLoading, setActionLoading] = useState(null);
  const [selectedReportAthlete, setSelectedReportAthlete] = useState(null);
  const [exportingTeamExcel, setExportingTeamExcel] = useState(false);

  const fetchSummary = async () => {
    try {
      setLoading(true);
      setError('');
      const res = await api.get('/dashboard/roster-summary');
      setSummary(res.data);
      if (res.data.assigned_count > 0) {
        setSquadFilter('squad');
      } else {
        setSquadFilter('all');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load squad analytics');
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadTeamExcel = async () => {
    try {
      setExportingTeamExcel(true);
      const res = await api.get('/reports/team/export/excel', { responseType: 'blob' });
      const blob = new Blob([res.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      });
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      const safeName = (user?.full_name || 'Squad').replace(/\s+/g, '_');
      link.download = `AthletiQ_Team_Analysis_${safeName}.xlsx`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(downloadUrl);
    } catch (err) {
      console.error('Failed to export team excel:', err);
      alert('Failed to generate Team Analysis Excel workbook. Please ensure assigned athletes exist.');
    } finally {
      setExportingTeamExcel(false);
    }
  };

  useEffect(() => {
    fetchSummary();
  }, []);

  const handleToggleSquad = async (athleteId, currentlyInSquad) => {
    try {
      setActionLoading(athleteId);
      if (currentlyInSquad) {
        await api.delete(`/athletes/${athleteId}/assign/${user.id}`);
      } else {
        await api.post(`/athletes/${athleteId}/assign?staff_id=${user.id}`);
      }
      await fetchSummary();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to update squad roster');
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto py-24 px-4 text-center">
        <div className="w-10 h-10 border-3 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-sm text-slate-300 font-medium">Calibrating squad biomechanical telemetry...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-xl mx-auto py-12 px-4 text-center">
        <div className="bg-rose-500/10 text-rose-300 p-5 rounded-2xl border border-rose-500/30 text-sm font-medium mb-4">
          {error}
        </div>
        <button
          onClick={fetchSummary}
          className="bg-purple-600 hover:bg-purple-500 text-white text-sm font-semibold px-5 py-2.5 rounded-xl transition shadow-lg shadow-purple-600/25"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!summary) return null;

  const {
    athletes,
    total_athletes,
    assigned_count,
    high_risk_count,
    moderate_risk_count,
    low_risk_count,
    avg_risk_score,
    avg_symmetry_index,
    squad_readiness_pct,
    load_distribution,
    recent_screenings
  } = summary;

  // Filter athletes
  const filteredAthletes = athletes.filter(a => {
    if (squadFilter === 'squad' && !a.is_assigned_to_me) {
      return false;
    }
    const q = search.toLowerCase();
    return (
      (a.name && a.name.toLowerCase().includes(q)) ||
      (a.sport_type && a.sport_type.toLowerCase().includes(q)) ||
      (a.position && a.position.toLowerCase().includes(q)) ||
      String(a.id).includes(q)
    );
  });

  const flaggedAthletes = athletes.filter(a => (a.risk_score && a.risk_score > 60) || (a.symmetry_index && a.symmetry_index > 15));

  return (
    <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8 space-y-8">
      {/* Header Banner */}
      <div className="bg-[#11121a] rounded-2xl border border-white/10 p-6 sm:p-7 flex flex-col md:flex-row justify-between items-start md:items-center gap-6 shadow-xl">
        <div className="space-y-1.5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-purple-600/20 border border-purple-500/40 text-purple-300 flex items-center justify-center shadow-sm">
              <Award size={20} />
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">Coach Squad Overview</h1>
            <span className="text-xs font-bold uppercase tracking-wider px-3 py-1 rounded-full border bg-purple-500/15 text-purple-300 border-purple-500/30">
              Head Coach Console
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-400">
            Real-time injury risk intelligence, training load management, and squad readiness analytics.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={handleDownloadTeamExcel}
            disabled={exportingTeamExcel}
            className="bg-[#1a1b28] hover:bg-[#232435] text-emerald-300 border border-emerald-500/30 font-semibold text-xs sm:text-sm px-4 py-2.5 rounded-xl flex items-center gap-2 shadow-sm transition disabled:opacity-50"
            title="Download multi-sheet team biomechanical analysis"
          >
            <FileSpreadsheet size={16} className={`text-emerald-400 ${exportingTeamExcel ? 'animate-bounce' : ''}`} />
            {exportingTeamExcel ? 'Generating Team Excel...' : 'Export Squad Analysis (Excel)'}
          </button>

          <Link
            to="/athletes"
            className="bg-[#1c1d2e] border border-white/10 hover:bg-[#25263a] text-slate-200 font-semibold text-xs sm:text-sm px-4 py-2.5 rounded-xl flex items-center gap-2 transition"
          >
            <Users size={16} className="text-purple-400" /> Full Athletes Directory
          </Link>
        </div>
      </div>

      {/* 4 Core Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* Squad Readiness */}
        <div className="bg-[#11121a] p-6 rounded-2xl border border-white/10 shadow-lg flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-xs sm:text-sm font-semibold uppercase tracking-wider text-slate-400">Squad Readiness</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 flex items-center justify-center">
              <ShieldCheck size={18} />
            </div>
          </div>
          <div className="my-3">
            <div className="text-3xl sm:text-4xl font-extrabold text-white">{squad_readiness_pct}%</div>
            <div className="w-full bg-[#1e1f2f] rounded-full h-2 mt-2.5 overflow-hidden">
              <div
                className="bg-emerald-500 h-full rounded-full transition-all duration-500"
                style={{ width: `${squad_readiness_pct}%` }}
              />
            </div>
          </div>
          <span className="text-xs text-slate-400">Athletes cleared for full competition</span>
        </div>

        {/* Average Risk Score */}
        <div className="bg-[#11121a] p-6 rounded-2xl border border-white/10 shadow-lg flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-xs sm:text-sm font-semibold uppercase tracking-wider text-slate-400">Average Risk Score</span>
            <div className="w-8 h-8 rounded-lg bg-purple-500/15 border border-purple-500/30 text-purple-400 flex items-center justify-center">
              <Activity size={18} />
            </div>
          </div>
          <div className="my-3">
            <div className="text-3xl sm:text-4xl font-extrabold text-white flex items-baseline gap-1.5">
              {avg_risk_score}
              <span className="text-sm font-normal text-slate-400">/ 100</span>
            </div>
            <span className={`text-xs font-bold px-2.5 py-1 rounded-full inline-block mt-2 ${
              avg_risk_score > 60 ? 'bg-rose-500/15 text-rose-300 border border-rose-500/30' :
              avg_risk_score > 30 ? 'bg-amber-500/15 text-amber-300 border border-amber-500/30' : 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
            }`}>
              {avg_risk_score > 60 ? 'Elevated Squad Load' : avg_risk_score > 30 ? 'Moderate Monitoring' : 'Optimal Conditioning'}
            </span>
          </div>
          <span className="text-xs text-slate-400">Across {total_athletes} monitored athletes</span>
        </div>

        {/* Flagged High-Risk */}
        <div className="bg-[#11121a] p-6 rounded-2xl border border-white/10 shadow-lg flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-xs sm:text-sm font-semibold uppercase tracking-wider text-slate-400">High Risk Alerts</span>
            <div className="w-8 h-8 rounded-lg bg-rose-500/15 border border-rose-500/30 text-rose-400 flex items-center justify-center">
              <ShieldAlert size={18} />
            </div>
          </div>
          <div className="my-3">
            <div className="text-3xl sm:text-4xl font-extrabold text-rose-400">{high_risk_count}</div>
            <span className="text-xs text-rose-300 font-semibold block mt-1.5">
              {high_risk_count === 0 ? 'No acute risk flags' : `${high_risk_count} athletes require load relief`}
            </span>
          </div>
          <span className="text-xs text-slate-400">{moderate_risk_count} athletes under moderate watch</span>
        </div>

        {/* Squad Membership */}
        <div className="bg-[#11121a] p-6 rounded-2xl border border-white/10 shadow-lg flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-xs sm:text-sm font-semibold uppercase tracking-wider text-slate-400">My Assigned Squad</span>
            <div className="w-8 h-8 rounded-lg bg-indigo-500/15 border border-indigo-500/30 text-indigo-400 flex items-center justify-center">
              <Users size={18} />
            </div>
          </div>
          <div className="my-3">
            <div className="text-3xl sm:text-4xl font-extrabold text-indigo-400">{assigned_count}</div>
            <span className="text-xs text-indigo-300 font-medium block mt-1.5">
              {assigned_count === 0 ? 'No athletes in squad' : `${assigned_count} athletes in your roster`}
            </span>
          </div>
          <span className="text-xs text-slate-400">{total_athletes} total in roster pool</span>
        </div>
      </div>

      {/* Row 2: Visual Risk Distribution & Coach Training Recommendations */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Risk & Load Breakdown */}
        <div className="bg-[#11121a] p-6 sm:p-7 rounded-2xl border border-white/10 shadow-xl space-y-6">
          <h2 className="text-base sm:text-lg font-bold text-white flex items-center gap-2.5">
            <BarChart3 size={18} className="text-purple-400" />
            <span>Squad Risk &amp; Load Distribution</span>
          </h2>

          {/* Risk Band Bar */}
          <div>
            <div className="flex justify-between text-xs sm:text-sm text-slate-300 mb-2 font-medium">
              <span>Risk Tier Breakdown</span>
              <span>{low_risk_count} Low &bull; {moderate_risk_count} Mod &bull; {high_risk_count} High</span>
            </div>
            <div className="w-full bg-[#1e1f2f] h-3.5 rounded-full flex overflow-hidden">
              <div 
                className="bg-emerald-500 h-full transition-all" 
                style={{ width: `${(low_risk_count / (total_athletes || 1)) * 100}%` }}
                title={`Low Risk: ${low_risk_count}`}
              />
              <div 
                className="bg-amber-500 h-full transition-all" 
                style={{ width: `${(moderate_risk_count / (total_athletes || 1)) * 100}%` }}
                title={`Moderate Risk: ${moderate_risk_count}`}
              />
              <div 
                className="bg-rose-500 h-full transition-all" 
                style={{ width: `${(high_risk_count / (total_athletes || 1)) * 100}%` }}
                title={`High Risk: ${high_risk_count}`}
              />
            </div>
            <div className="flex justify-between text-xs text-slate-400 mt-2">
              <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500" /> Low ({low_risk_count})</span>
              <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-amber-500" /> Mod ({moderate_risk_count})</span>
              <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-rose-500" /> High ({high_risk_count})</span>
            </div>
          </div>

          {/* Training Load Distribution */}
          <div className="pt-4 border-t border-white/5">
            <span className="text-xs sm:text-sm font-semibold text-slate-300 block mb-3">Training Load Distribution</span>
            <div className="grid grid-cols-4 gap-2.5 text-center">
              <div className="p-3 bg-[#161724] rounded-xl border border-white/5">
                <span className="text-xs text-slate-400 block font-semibold">Low</span>
                <strong className="text-base font-bold text-white">{load_distribution.Low || 0}</strong>
              </div>
              <div className="p-3 bg-purple-500/10 rounded-xl border border-purple-500/20">
                <span className="text-xs text-purple-300 block font-semibold">Medium</span>
                <strong className="text-base font-bold text-white">{load_distribution.Medium || 0}</strong>
              </div>
              <div className="p-3 bg-amber-500/10 rounded-xl border border-amber-500/20">
                <span className="text-xs text-amber-300 block font-semibold">High</span>
                <strong className="text-base font-bold text-white">{load_distribution.High || 0}</strong>
              </div>
              <div className="p-3 bg-rose-500/10 rounded-xl border border-rose-500/20">
                <span className="text-xs text-rose-300 block font-semibold">Exhaustive</span>
                <strong className="text-base font-bold text-white">{load_distribution.Exhaustive || 0}</strong>
              </div>
            </div>
          </div>

          {/* Bilateral Symmetry Benchmark */}
          <div className="pt-4 border-t border-white/5 flex items-center justify-between text-xs sm:text-sm">
            <span className="text-slate-400">Squad Bilateral Symmetry Avg:</span>
            <span className="font-bold text-white">{avg_symmetry_index}&deg; diff</span>
          </div>
        </div>

        {/* Actionable Squad Coaching Recommendations */}
        <div className="bg-[#11121a] p-6 sm:p-7 rounded-2xl border border-white/10 shadow-xl lg:col-span-2 flex flex-col justify-between space-y-4">
          <div>
            <h2 className="text-base sm:text-lg font-bold text-white flex items-center gap-2 mb-1">
              <Sparkles size={18} className="text-purple-400" />
              <span>Squad Biomechanical Directives</span>
            </h2>
            <p className="text-xs sm:text-sm text-slate-400 mb-4">
              Prescriptive guidelines tailored to current squad kinematic metrics and load intensities.
            </p>

            <div className="space-y-3.5 text-xs sm:text-sm">
              <div className="p-4 bg-purple-500/10 rounded-xl border border-purple-500/20 flex items-start gap-3.5">
                <div className="w-7 h-7 rounded-lg bg-purple-600 text-white flex items-center justify-center shrink-0 mt-0.5 text-xs font-bold">
                  1
                </div>
                <div>
                  <h3 className="font-bold text-white">Active Recovery & Load Moderation</h3>
                  <p className="text-slate-300 mt-1 leading-relaxed">
                    {high_risk_count > 0 
                      ? `${high_risk_count} athletes are exhibiting composite risk scores > 60. Substitute high-impact sprinting drills with low-impact neuromuscular conditioning.`
                      : "Squad overall load is well-calibrated. Maintain scheduled tactical and technical progressions without immediate volume restriction."}
                  </p>
                </div>
              </div>

              <div className="p-4 bg-indigo-500/10 rounded-xl border border-indigo-500/20 flex items-start gap-3.5">
                <div className="w-7 h-7 rounded-lg bg-indigo-600 text-white flex items-center justify-center shrink-0 mt-0.5 text-xs font-bold">
                  2
                </div>
                <div>
                  <h3 className="font-bold text-white">Bilateral Knee & Hip Symmetry Drills</h3>
                  <p className="text-slate-300 mt-1 leading-relaxed">
                    Incorporate unilateral single-leg stability exercises (Nordic hamstring curls, Bulgarian split squats) during pre-session warm-ups to equalize side-to-side force distribution.
                  </p>
                </div>
              </div>

              <div className="p-4 bg-emerald-500/10 rounded-xl border border-emerald-500/20 flex items-start gap-3.5">
                <div className="w-7 h-7 rounded-lg bg-emerald-600 text-white flex items-center justify-center shrink-0 mt-0.5 text-xs font-bold">
                  3
                </div>
                <div>
                  <h3 className="font-bold text-white">FIFA 11+ Movement Quality Protocol</h3>
                  <p className="text-slate-300 mt-1 leading-relaxed">
                    Review jump-landing mechanics and trunk lean deviations. Athletes showing trunk lean &gt; 12&deg; should focus on core isometric endurance.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {flaggedAthletes.length > 0 && (
            <div className="mt-4 pt-3.5 border-t border-white/5 text-xs sm:text-sm text-rose-400 flex items-center gap-2">
              <AlertCircle size={16} className="shrink-0" />
              <span>{flaggedAthletes.length} athletes flagged with movement asymmetry or elevated risk score.</span>
            </div>
          )}
        </div>
      </div>

      {/* Row 3: Athlete Performance Analytics & Squad Roster Table */}
      <div className="bg-[#11121a] rounded-2xl border border-white/10 shadow-xl overflow-hidden">
        <div className="p-6 border-b border-white/10 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-[#141522]">
          <div>
            <h2 className="text-base sm:text-lg font-bold text-white flex items-center gap-2.5">
              <Users size={20} className="text-purple-400" />
              <span>Athlete Performance &amp; Squad Directory</span>
            </h2>
            <p className="text-xs sm:text-sm text-slate-400 mt-1">
              Monitor individual risk indices, symmetry differentials, and manage squad assignments.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 w-full sm:w-auto">
            {/* Squad Filter Pills */}
            <div className="bg-[#1c1d2e] p-1 rounded-xl flex text-xs font-semibold border border-white/5">
              <button
                onClick={() => setSquadFilter('all')}
                className={`px-3.5 py-1.5 rounded-lg transition ${
                  squadFilter === 'all' ? 'bg-purple-600 text-white shadow-sm' : 'text-slate-400 hover:text-white'
                }`}
              >
                All Athletes ({total_athletes})
              </button>
              <button
                onClick={() => setSquadFilter('squad')}
                className={`px-3.5 py-1.5 rounded-lg transition ${
                  squadFilter === 'squad' ? 'bg-purple-600 text-white shadow-sm' : 'text-slate-400 hover:text-white'
                }`}
              >
                My Squad ({assigned_count})
              </button>
            </div>

            {/* Search */}
            <div className="relative">
              <Search size={15} className="absolute left-3.5 top-2.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search athlete or sport..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="pl-9 pr-4 py-2 border border-white/10 rounded-xl text-xs sm:text-sm bg-[#1c1d2e] text-white outline-none focus:ring-2 focus:ring-purple-500 w-56"
              />
            </div>
          </div>
        </div>

        {filteredAthletes.length === 0 ? (
          <div className="p-16 text-center text-slate-400 text-xs sm:text-sm">
            <Users size={36} className="mx-auto mb-3 opacity-30 text-purple-400" />
            <p className="font-semibold text-white text-base">No athletes matching criteria</p>
            <p className="mt-1 text-slate-400">
              {squadFilter === 'squad' 
                ? 'No athletes currently assigned to your squad. Switch to "All Athletes" to add members.'
                : 'No athletes registered in the database yet.'}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs sm:text-sm">
              <thead>
                <tr className="border-b border-white/10 text-slate-400 font-semibold uppercase text-xs tracking-wider bg-[#171826]">
                  <th className="py-3.5 px-6">Athlete</th>
                  <th className="py-3.5 px-4">Risk Index</th>
                  <th className="py-3.5 px-4">Training Load</th>
                  <th className="py-3.5 px-4">Bilateral Symmetry</th>
                  <th className="py-3.5 px-4">Screenings</th>
                  <th className="py-3.5 px-4">Squad Status</th>
                  <th className="py-3.5 px-6 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-slate-300">
                {filteredAthletes.map(a => {
                  const hasRisk = a.risk_score !== null && a.risk_score !== undefined;
                  const isHigh = hasRisk && a.risk_score > 60;
                  const isMod = hasRisk && a.risk_score >= 30 && a.risk_score <= 60;

                  return (
                    <tr key={a.id} className="hover:bg-white/5 transition">
                      <td className="py-4 px-6">
                        <div className="flex items-center gap-3">
                          <div className="w-9 h-9 rounded-xl bg-purple-500/20 text-purple-300 font-bold flex items-center justify-center text-sm shrink-0 border border-purple-500/30">
                            {a.name ? a.name[0] : 'A'}
                          </div>
                          <div>
                            <div className="font-bold text-white text-sm sm:text-base">{a.name}</div>
                            <div className="text-xs text-slate-400">
                              {a.sport_type || 'General Athletics'} {a.position ? `&bull; ${a.position}` : ''}
                            </div>
                          </div>
                        </div>
                      </td>

                      <td className="py-4 px-4">
                        {hasRisk ? (
                          <div className="flex items-center gap-2">
                            <span className={`font-black text-sm sm:text-base ${
                              isHigh ? 'text-rose-400' : isMod ? 'text-amber-400' : 'text-emerald-400'
                            }`}>
                              {a.risk_score.toFixed(1)}
                            </span>
                            <span className={`text-xs font-bold px-2.5 py-0.5 rounded-full ${
                              isHigh ? 'bg-rose-500/15 text-rose-300 border border-rose-500/30' :
                              isMod ? 'bg-amber-500/15 text-amber-300 border border-amber-500/30' : 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                            }`}>
                              {a.risk_band || (isHigh ? 'High' : isMod ? 'Moderate' : 'Low')}
                            </span>
                          </div>
                        ) : (
                          <span className="text-slate-400 italic">No screen data</span>
                        )}
                      </td>

                      <td className="py-4 px-4">
                        <span className={`text-xs font-bold px-2.5 py-1 rounded-full border ${
                          a.training_load === 'Exhaustive' ? 'bg-rose-500/15 text-rose-300 border-rose-500/30' :
                          a.training_load === 'High' ? 'bg-amber-500/15 text-amber-300 border-amber-500/30' :
                          a.training_load === 'Medium' ? 'bg-purple-500/15 text-purple-300 border-purple-500/30' :
                          'bg-white/5 text-slate-300 border-white/10'
                        }`}>
                          {a.training_load}
                        </span>
                      </td>

                      <td className="py-4 px-4">
                        {a.symmetry_index !== null && a.symmetry_index !== undefined ? (
                          <span className={`font-semibold ${a.symmetry_index > 15 ? 'text-rose-400 font-bold' : 'text-slate-200'}`}>
                            {a.symmetry_index}&deg; diff
                          </span>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>

                      <td className="py-4 px-4">
                        <span className="font-semibold text-slate-200">{a.video_count} video{a.video_count === 1 ? '' : 's'}</span>
                      </td>

                      <td className="py-4 px-4">
                        {a.is_assigned_to_me ? (
                          <span className="text-xs font-bold text-purple-300 bg-purple-500/15 border border-purple-500/30 px-3 py-1 rounded-full flex items-center gap-1.5 w-max">
                            <CheckCircle2 size={13} className="text-purple-400" /> In Squad
                          </span>
                        ) : (
                          <span className="text-xs text-slate-400">Available</span>
                        )}
                      </td>

                      <td className="py-4 px-6 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleToggleSquad(a.id, a.is_assigned_to_me)}
                            disabled={actionLoading === a.id}
                            className={`p-2 rounded-xl border text-xs font-semibold transition ${
                              a.is_assigned_to_me
                                ? 'border-white/10 text-slate-400 hover:bg-rose-500/15 hover:text-rose-300 hover:border-rose-500/30'
                                : 'border-purple-500/30 bg-purple-500/15 text-purple-300 hover:bg-purple-600 hover:text-white'
                            }`}
                            title={a.is_assigned_to_me ? 'Remove from Squad' : 'Add to Squad'}
                          >
                            {a.is_assigned_to_me ? <UserMinus size={15} /> : <UserPlus size={15} />}
                          </button>

                          <button
                            onClick={() => setSelectedReportAthlete({ id: a.id, name: a.name })}
                            className="p-2 rounded-xl border border-white/10 text-slate-300 hover:bg-white/10 hover:text-purple-400 text-xs font-semibold transition"
                            title="Export PDF / Excel Reports"
                          >
                            <FileText size={15} />
                          </button>

                          <Link
                            to={`/dashboard/athlete/${a.id}`}
                            className="bg-purple-600 hover:bg-purple-500 text-white font-semibold px-3 py-2 rounded-xl text-xs sm:text-sm transition flex items-center gap-1.5 shadow-md shadow-purple-600/20"
                          >
                            <span>Kinematics</span>
                            <ChevronRight size={14} />
                          </Link>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Row 4: Movement Quality Reports & Recent Movement Screenings */}
      <div className="bg-[#11121a] rounded-2xl border border-white/10 shadow-xl p-6 sm:p-7 space-y-4">
        <div className="flex justify-between items-center mb-2">
          <div>
            <h2 className="text-base sm:text-lg font-bold text-white flex items-center gap-2.5">
              <Clock size={18} className="text-purple-400" />
              <span>Recent Video Movement Screenings</span>
            </h2>
            <p className="text-xs sm:text-sm text-slate-400 mt-0.5">Live feed of processed biomechanics and pose tracking trials across the squad</p>
          </div>
          <Link to="/athletes" className="text-xs sm:text-sm text-purple-400 hover:text-purple-300 font-semibold flex items-center gap-1">
            View All Trials &rarr;
          </Link>
        </div>

        {recent_screenings.length === 0 ? (
          <p className="text-xs sm:text-sm text-slate-400 py-8 text-center">No video screenings uploaded recently.</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
            {recent_screenings.map(v => (
              <div key={v.id} className="p-4 bg-[#161724] rounded-xl border border-white/5 flex flex-col justify-between hover:border-purple-500/30 transition">
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-xs font-bold text-slate-400 uppercase">Trial #{v.id}</span>
                    <span className={`text-xs px-2.5 py-0.5 rounded-full font-bold ${
                      v.status === 'completed' ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30' :
                      v.status === 'error' ? 'bg-rose-500/15 text-rose-300 border border-rose-500/30' : 'bg-purple-500/15 text-purple-300 border border-purple-500/30'
                    }`}>
                      {v.status}
                    </span>
                  </div>
                  <h4 className="font-bold text-sm text-white truncate">{v.athlete_name}</h4>
                  <p className="text-xs text-slate-400 truncate mt-0.5">{v.filename}</p>
                </div>

                <div className="mt-4 pt-3 border-t border-white/5 flex justify-between items-center text-xs text-slate-400">
                  <span>{v.created_at ? new Date(v.created_at).toLocaleDateString() : 'Recent'}</span>
                  <Link
                    to={`/dashboard/athlete/${v.athlete_id}`}
                    className="font-semibold text-purple-400 hover:text-purple-300 flex items-center gap-1"
                  >
                    Review &rarr;
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Reports & Clinical Export Modal */}
      {selectedReportAthlete && (
        <ReportsExportModal
          isOpen={!!selectedReportAthlete}
          onClose={() => setSelectedReportAthlete(null)}
          athleteId={selectedReportAthlete.id}
          athleteName={selectedReportAthlete.name}
        />
      )}
    </div>
  );
};

export default CoachDashboard;
