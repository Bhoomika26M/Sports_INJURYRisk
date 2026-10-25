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
  Clock
} from 'lucide-react';

export const CoachDashboard = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [squadFilter, setSquadFilter] = useState('all'); // 'all' | 'squad'
  const [search, setSearch] = useState('');
  const [actionLoading, setActionLoading] = useState(null);

  const fetchSummary = async () => {
    try {
      setLoading(true);
      setError('');
      const res = await api.get('/dashboard/roster-summary');
      setSummary(res.data);
      if (res.data.assigned_count > 0) {
        setSquadFilter('squad');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load squad analytics');
    } finally {
      setLoading(false);
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
      <div className="max-w-6xl mx-auto py-20 px-4 text-center">
        <div className="w-8 h-8 border-3 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        <p className="text-xs text-slate-500 font-medium">Calibrating squad biomechanical telemetry...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-xl mx-auto py-12 px-4 text-center">
        <div className="bg-red-50 text-red-700 p-4 rounded-2xl border border-red-200 text-xs font-medium mb-3">
          {error}
        </div>
        <button
          onClick={fetchSummary}
          className="bg-indigo-600 text-white text-xs font-semibold px-4 py-2 rounded-xl hover:bg-indigo-700 transition"
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
    if (squadFilter === 'squad' && !a.is_assigned_to_me && assigned_count > 0) {
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
    <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8 space-y-6">
      {/* Header Banner */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 shadow-xs">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-8 h-8 rounded-xl bg-indigo-50 text-indigo-700 flex items-center justify-center">
              <Award size={18} />
            </div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">Coach Squad Overview</h1>
            <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border bg-indigo-50 text-indigo-700 border-indigo-200">
              Head Coach Console
            </span>
          </div>
          <p className="text-xs text-slate-500">
            Real-time injury risk intelligence, training load management, and squad readiness.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            to="/athletes"
            className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-xs px-3.5 py-2 rounded-xl flex items-center gap-1.5 shadow-xs transition"
          >
            <Users size={14} /> Full Athlete Directory
          </Link>
        </div>
      </div>

      {/* 4 Core Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Squad Readiness */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Squad Readiness</span>
            <div className="w-7 h-7 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <ShieldCheck size={16} />
            </div>
          </div>
          <div className="my-2">
            <div className="text-2xl font-black text-slate-900">{squad_readiness_pct}%</div>
            <div className="w-full bg-slate-100 rounded-full h-1.5 mt-2 overflow-hidden">
              <div
                className="bg-emerald-500 h-full rounded-full transition-all duration-500"
                style={{ width: `${squad_readiness_pct}%` }}
              />
            </div>
          </div>
          <span className="text-[11px] text-slate-500">Athletes cleared for full training</span>
        </div>

        {/* Average Risk Score */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Average Risk Score</span>
            <div className="w-7 h-7 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
              <Activity size={16} />
            </div>
          </div>
          <div className="my-2">
            <div className="text-2xl font-black text-slate-900 flex items-baseline gap-1">
              {avg_risk_score}
              <span className="text-xs font-normal text-slate-400">/ 100</span>
            </div>
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full inline-block mt-1 ${
              avg_risk_score > 60 ? 'bg-rose-50 text-rose-700' :
              avg_risk_score > 30 ? 'bg-amber-50 text-amber-700' : 'bg-emerald-50 text-emerald-700'
            }`}>
              {avg_risk_score > 60 ? 'Elevated Squad Load' : avg_risk_score > 30 ? 'Moderate Monitoring' : 'Optimal Conditioning'}
            </span>
          </div>
          <span className="text-[11px] text-slate-500">Across {total_athletes} monitored profiles</span>
        </div>

        {/* Flagged High-Risk */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">High Risk Alerts</span>
            <div className="w-7 h-7 rounded-lg bg-rose-50 text-rose-600 flex items-center justify-center">
              <ShieldAlert size={16} />
            </div>
          </div>
          <div className="my-2">
            <div className="text-2xl font-black text-rose-600">{high_risk_count}</div>
            <span className="text-[11px] text-rose-600 font-semibold block mt-1">
              {high_risk_count === 0 ? 'No acute risk alerts' : `${high_risk_count} athletes require load relief`}
            </span>
          </div>
          <span className="text-[11px] text-slate-500">{moderate_risk_count} in moderate vigilance</span>
        </div>

        {/* Squad Membership */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">My Assigned Squad</span>
            <div className="w-7 h-7 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <Users size={16} />
            </div>
          </div>
          <div className="my-2">
            <div className="text-2xl font-black text-indigo-700">{assigned_count}</div>
            <span className="text-[11px] text-indigo-600 font-medium block mt-1">
              {assigned_count === 0 ? 'No custom squad filtered' : `${assigned_count} athletes in your roster`}
            </span>
          </div>
          <span className="text-[11px] text-slate-500">{total_athletes} total available</span>
        </div>
      </div>

      {/* Row 2: Visual Risk Distribution & Coach Training Recommendations */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Risk & Load Breakdown */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-5">
          <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <BarChart3 size={16} className="text-indigo-600" />
            <span>Squad Risk & Load Distribution</span>
          </h2>

          {/* Risk Band Bar */}
          <div>
            <div className="flex justify-between text-xs text-slate-600 mb-1.5 font-medium">
              <span>Risk Tier Breakdown</span>
              <span>{low_risk_count} Low &bull; {moderate_risk_count} Mod &bull; {high_risk_count} High</span>
            </div>
            <div className="w-full bg-slate-100 h-3 rounded-full flex overflow-hidden">
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
            <div className="flex justify-between text-[10px] text-slate-400 mt-1">
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500" /> Low</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-500" /> Moderate</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-rose-500" /> High</span>
            </div>
          </div>

          {/* Training Load Distribution */}
          <div className="pt-3 border-t border-slate-100">
            <span className="text-xs font-semibold text-slate-700 block mb-2">Training Load Distribution</span>
            <div className="grid grid-cols-4 gap-2 text-center">
              <div className="p-2 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-[10px] text-slate-400 block font-semibold">Low</span>
                <strong className="text-sm text-slate-800">{load_distribution.Low || 0}</strong>
              </div>
              <div className="p-2 bg-blue-50/60 rounded-xl border border-blue-100">
                <span className="text-[10px] text-blue-600 block font-semibold">Medium</span>
                <strong className="text-sm text-blue-700">{load_distribution.Medium || 0}</strong>
              </div>
              <div className="p-2 bg-amber-50/60 rounded-xl border border-amber-100">
                <span className="text-[10px] text-amber-600 block font-semibold">High</span>
                <strong className="text-sm text-amber-700">{load_distribution.High || 0}</strong>
              </div>
              <div className="p-2 bg-rose-50/60 rounded-xl border border-rose-100">
                <span className="text-[10px] text-rose-600 block font-semibold">Exhaustive</span>
                <strong className="text-sm text-rose-700">{load_distribution.Exhaustive || 0}</strong>
              </div>
            </div>
          </div>

          {/* Bilateral Symmetry Benchmark */}
          <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
            <span className="text-slate-500">Squad Bilateral Symmetry Avg:</span>
            <span className="font-bold text-slate-800">{avg_symmetry_index}° diff</span>
          </div>
        </div>

        {/* Actionable Squad Coaching Recommendations */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs lg:col-span-2 flex flex-col justify-between">
          <div>
            <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2 mb-1">
              <Sparkles size={16} className="text-indigo-600" />
              <span>Squad Biomechanical Directives</span>
            </h2>
            <p className="text-xs text-slate-500 mb-4">
              Prescriptive guidelines tailored to current squad kinematic metrics and load intensities.
            </p>

            <div className="space-y-3 text-xs">
              <div className="p-3.5 bg-indigo-50/60 rounded-xl border border-indigo-100 flex items-start gap-3">
                <div className="w-6 h-6 rounded-lg bg-indigo-600 text-white flex items-center justify-center shrink-0 mt-0.5 text-xs font-bold">
                  1
                </div>
                <div>
                  <h3 className="font-bold text-indigo-950">Active Recovery & Load Moderation</h3>
                  <p className="text-indigo-900/80 mt-0.5">
                    {high_risk_count > 0 
                      ? `${high_risk_count} athletes are exhibiting composite risk scores > 60. Subsitute high-impact sprinting drills with low-impact neuromuscular conditioning.`
                      : "Squad overall load is well-calibrated. Maintain scheduled tactical and technical progressions without immediate volume restriction."}
                  </p>
                </div>
              </div>

              <div className="p-3.5 bg-blue-50/60 rounded-xl border border-blue-100 flex items-start gap-3">
                <div className="w-6 h-6 rounded-lg bg-blue-600 text-white flex items-center justify-center shrink-0 mt-0.5 text-xs font-bold">
                  2
                </div>
                <div>
                  <h3 className="font-bold text-blue-950">Bilateral Knee & Hip Symmetry Drills</h3>
                  <p className="text-blue-900/80 mt-0.5">
                    Incorporate unilateral single-leg stability exercises (Nordic hamstring curls, Bulgarian split squats) during pre-session warm-ups to equalize side-to-side force distribution.
                  </p>
                </div>
              </div>

              <div className="p-3.5 bg-emerald-50/60 rounded-xl border border-emerald-100 flex items-start gap-3">
                <div className="w-6 h-6 rounded-lg bg-emerald-600 text-white flex items-center justify-center shrink-0 mt-0.5 text-xs font-bold">
                  3
                </div>
                <div>
                  <h3 className="font-bold text-emerald-950">FIFA 11+ Movement Quality Protocol</h3>
                  <p className="text-emerald-900/80 mt-0.5">
                    Review jump-landing mechanics and trunk lean deviations. Athletes showing trunk lean &gt; 12° should focus on core isometric endurance.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {flaggedAthletes.length > 0 && (
            <div className="mt-4 pt-3 border-t border-slate-100 text-xs text-rose-700 flex items-center gap-1.5">
              <AlertCircle size={14} className="shrink-0" />
              <span>{flaggedAthletes.length} athletes flagged with movement asymmetry or elevated risk score.</span>
            </div>
          )}
        </div>
      </div>

      {/* Row 3: Athlete Performance Analytics & Squad Roster Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-slate-50/40">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Users size={18} className="text-indigo-600" />
              <span>Athlete Performance & Squad Directory</span>
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Monitor individual risk indices, symmetry differentials, and manage squad assignments.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
            {/* Squad Filter Pills */}
            <div className="bg-slate-100 p-1 rounded-xl flex text-xs font-semibold">
              <button
                onClick={() => setSquadFilter('all')}
                className={`px-3 py-1 rounded-lg transition ${
                  squadFilter === 'all' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                All Athletes ({total_athletes})
              </button>
              <button
                onClick={() => setSquadFilter('squad')}
                className={`px-3 py-1 rounded-lg transition ${
                  squadFilter === 'squad' ? 'bg-white text-indigo-600 shadow-xs' : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                My Squad ({assigned_count})
              </button>
            </div>

            {/* Search */}
            <div className="relative">
              <Search size={14} className="absolute left-3 top-2.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search athlete or sport..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="pl-8 pr-3 py-1.5 border border-slate-200 rounded-xl text-xs bg-white outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-600 w-48"
              />
            </div>
          </div>
        </div>

        {filteredAthletes.length === 0 ? (
          <div className="p-12 text-center text-slate-400 text-xs">
            <Users size={32} className="mx-auto mb-2 opacity-40" />
            <p className="font-semibold text-slate-700 text-sm">No athletes matching criteria</p>
            <p className="mt-1">
              {squadFilter === 'squad' 
                ? 'No athletes currently assigned to your squad. Switch to "All Athletes" to add members.'
                : 'No athletes registered in the database yet.'}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-100 text-slate-400 font-semibold uppercase text-[10px] tracking-wider bg-slate-50/70">
                  <th className="py-3 px-5">Athlete</th>
                  <th className="py-3 px-4">Risk Index</th>
                  <th className="py-3 px-4">Training Load</th>
                  <th className="py-3 px-4">Bilateral Symmetry</th>
                  <th className="py-3 px-4">Screenings</th>
                  <th className="py-3 px-4">Squad Status</th>
                  <th className="py-3 px-5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredAthletes.map(a => {
                  const hasRisk = a.risk_score !== null && a.risk_score !== undefined;
                  const isHigh = hasRisk && a.risk_score > 60;
                  const isMod = hasRisk && a.risk_score >= 30 && a.risk_score <= 60;

                  return (
                    <tr key={a.id} className="hover:bg-slate-50/80 transition">
                      <td className="py-3.5 px-5">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-xl bg-indigo-50 text-indigo-700 font-bold flex items-center justify-center text-xs shrink-0">
                            {a.name ? a.name[0] : 'A'}
                          </div>
                          <div>
                            <div className="font-bold text-slate-900">{a.name}</div>
                            <div className="text-[11px] text-slate-400">
                              {a.sport_type || 'General Athletics'} {a.position ? `&bull; ${a.position}` : ''}
                            </div>
                          </div>
                        </div>
                      </td>

                      <td className="py-3.5 px-4">
                        {hasRisk ? (
                          <div className="flex items-center gap-2">
                            <span className={`font-black text-sm ${
                              isHigh ? 'text-rose-600' : isMod ? 'text-amber-600' : 'text-emerald-600'
                            }`}>
                              {a.risk_score.toFixed(1)}
                            </span>
                            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                              isHigh ? 'bg-rose-50 text-rose-700' :
                              isMod ? 'bg-amber-50 text-amber-700' : 'bg-emerald-50 text-emerald-700'
                            }`}>
                              {a.risk_band || (isHigh ? 'High' : isMod ? 'Moderate' : 'Low')}
                            </span>
                          </div>
                        ) : (
                          <span className="text-slate-400 italic">No screen data</span>
                        )}
                      </td>

                      <td className="py-3.5 px-4">
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                          a.training_load === 'Exhaustive' ? 'bg-rose-50 text-rose-700 border-rose-200' :
                          a.training_load === 'High' ? 'bg-amber-50 text-amber-700 border-amber-200' :
                          a.training_load === 'Medium' ? 'bg-blue-50 text-blue-700 border-blue-200' :
                          'bg-slate-100 text-slate-600 border-slate-200'
                        }`}>
                          {a.training_load}
                        </span>
                      </td>

                      <td className="py-3.5 px-4">
                        {a.symmetry_index !== null && a.symmetry_index !== undefined ? (
                          <span className={`font-semibold ${a.symmetry_index > 15 ? 'text-rose-600 font-bold' : 'text-slate-700'}`}>
                            {a.symmetry_index}° diff
                          </span>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>

                      <td className="py-3.5 px-4">
                        <span className="font-semibold text-slate-700">{a.video_count} videos</span>
                      </td>

                      <td className="py-3.5 px-4">
                        {a.is_assigned_to_me ? (
                          <span className="text-[10px] font-bold text-indigo-700 bg-indigo-50 border border-indigo-200 px-2 py-0.5 rounded-full flex items-center gap-1 w-max">
                            <CheckCircle2 size={11} /> In Squad
                          </span>
                        ) : (
                          <span className="text-[10px] text-slate-400">Available</span>
                        )}
                      </td>

                      <td className="py-3.5 px-5 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleToggleSquad(a.id, a.is_assigned_to_me)}
                            disabled={actionLoading === a.id}
                            className={`p-1.5 rounded-lg border text-xs font-semibold transition ${
                              a.is_assigned_to_me
                                ? 'border-slate-200 text-slate-600 hover:bg-rose-50 hover:text-rose-600 hover:border-rose-200'
                                : 'border-indigo-200 bg-indigo-50 text-indigo-700 hover:bg-indigo-100'
                            }`}
                            title={a.is_assigned_to_me ? 'Remove from Squad' : 'Add to Squad'}
                          >
                            {a.is_assigned_to_me ? <UserMinus size={13} /> : <UserPlus size={13} />}
                          </button>

                          <Link
                            to={`/dashboard/athlete/${a.id}`}
                            className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold px-2.5 py-1.5 rounded-lg text-xs transition flex items-center gap-1 shadow-xs"
                          >
                            <span>Kinematics</span>
                            <ChevronRight size={13} />
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
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs p-6">
        <div className="flex justify-between items-center mb-4">
          <div>
            <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Clock size={16} className="text-indigo-600" />
              <span>Recent Video Movement Screenings</span>
            </h2>
            <p className="text-xs text-slate-500">Live feed of processed biomechanics and pose tracking trials across the squad</p>
          </div>
          <Link to="/athletes" className="text-xs text-indigo-600 hover:text-indigo-800 font-semibold">
            View All Trials &rarr;
          </Link>
        </div>

        {recent_screenings.length === 0 ? (
          <p className="text-xs text-slate-400 py-6 text-center">No video screenings uploaded recently.</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
            {recent_screenings.map(v => (
              <div key={v.id} className="p-3.5 bg-slate-50 rounded-xl border border-slate-200/80 flex flex-col justify-between">
                <div>
                  <div className="flex justify-between items-center mb-1.5">
                    <span className="text-[10px] font-bold text-slate-400 uppercase">Trial #{v.id}</span>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${
                      v.status === 'completed' ? 'bg-emerald-50 text-emerald-700' :
                      v.status === 'error' ? 'bg-rose-50 text-rose-700' : 'bg-blue-50 text-blue-700'
                    }`}>
                      {v.status}
                    </span>
                  </div>
                  <h4 className="font-bold text-xs text-slate-900 truncate">{v.athlete_name}</h4>
                  <p className="text-[11px] text-slate-400 truncate">{v.filename}</p>
                </div>

                <div className="mt-3 pt-2 border-t border-slate-200/60 flex justify-between items-center text-[10px] text-slate-500">
                  <span>{v.created_at ? new Date(v.created_at).toLocaleDateString() : 'Recent'}</span>
                  <Link
                    to={`/dashboard/athlete/${v.athlete_id}`}
                    className="font-semibold text-indigo-600 hover:text-indigo-800"
                  >
                    Review &rarr;
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
