import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../../api/client';
import { useAuth } from '../../context/AuthContext';
import {
  Stethoscope,
  Activity,
  ShieldAlert,
  ShieldCheck,
  Users,
  Search,
  ChevronRight,
  UserPlus,
  UserMinus,
  CheckCircle2,
  HeartPulse,
  Flame,
  FileCheck2,
  Bandage
} from 'lucide-react';

export const PhysiotherapistDashboard = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filterMode, setFilterMode] = useState('all'); // 'all' | 'assigned' | 'injured'
  const [search, setSearch] = useState('');
  const [actionLoading, setActionLoading] = useState(null);

  const fetchSummary = async () => {
    try {
      setLoading(true);
      setError('');
      const res = await api.get('/dashboard/roster-summary');
      setSummary(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load physiotherapy telemetry');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSummary();
  }, []);

  const handleTogglePatient = async (athleteId, currentlyAssigned) => {
    try {
      setActionLoading(athleteId);
      if (currentlyAssigned) {
        await api.delete(`/athletes/${athleteId}/assign/${user.id}`);
      } else {
        await api.post(`/athletes/${athleteId}/assign?staff_id=${user.id}`);
      }
      await fetchSummary();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to update patient roster');
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto py-20 px-4 text-center">
        <div className="w-8 h-8 border-3 border-teal-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        <p className="text-xs text-slate-500 font-medium">Loading clinical kinematics & recovery telemetry...</p>
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
          className="bg-teal-600 text-white text-xs font-semibold px-4 py-2 rounded-xl hover:bg-teal-700 transition"
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
    injury_distribution,
    recent_screenings
  } = summary;

  // Filter athletes
  const filteredAthletes = athletes.filter(a => {
    if (filterMode === 'assigned' && !a.is_assigned_to_me) return false;
    if (filterMode === 'injured' && a.injury_count === 0) return false;
    const q = search.toLowerCase();
    return (
      (a.name && a.name.toLowerCase().includes(q)) ||
      (a.sport_type && a.sport_type.toLowerCase().includes(q)) ||
      (a.position && a.position.toLowerCase().includes(q)) ||
      String(a.id).includes(q)
    );
  });

  const athletesWithHistory = athletes.filter(a => a.injury_count > 0);
  const athletesWithAsymmetryFlag = athletes.filter(a => a.symmetry_index && a.symmetry_index > 12);

  return (
    <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8 space-y-6">
      {/* Header Banner */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 shadow-xs">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-8 h-8 rounded-xl bg-teal-50 text-teal-700 flex items-center justify-center">
              <Stethoscope size={18} />
            </div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">Physiotherapy & Rehabilitation Console</h1>
            <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border bg-teal-50 text-teal-700 border-teal-200">
              Clinical Specialist
            </span>
          </div>
          <p className="text-xs text-slate-500">
            Rehabilitation tracking, movement compensation analytics, and return-to-play kinematic screening.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            to="/athletes"
            className="bg-teal-600 hover:bg-teal-700 text-white font-medium text-xs px-3.5 py-2 rounded-xl flex items-center gap-1.5 shadow-xs transition"
          >
            <Users size={14} /> Full Patient Roster
          </Link>
        </div>
      </div>

      {/* 4 Clinical Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Active Patients in Care */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Assigned Patients</span>
            <div className="w-7 h-7 rounded-lg bg-teal-50 text-teal-600 flex items-center justify-center">
              <Users size={16} />
            </div>
          </div>
          <div className="my-2">
            <div className="text-2xl font-black text-slate-900">{assigned_count}</div>
            <span className="text-[11px] text-teal-700 font-medium block mt-1">
              {assigned_count === 0 ? 'No patients directly linked' : `${assigned_count} patients in clinical caseload`}
            </span>
          </div>
          <span className="text-[11px] text-slate-500">{total_athletes} total in institution</span>
        </div>

        {/* Recorded Injury History */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Rehab / Past Injuries</span>
            <div className="w-7 h-7 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
              <Bandage size={16} />
            </div>
          </div>
          <div className="my-2">
            <div className="text-2xl font-black text-amber-700">{athletesWithHistory.length}</div>
            <span className="text-[11px] text-amber-700 font-semibold block mt-1">
              {athletesWithHistory.length} athletes with documented injury history
            </span>
          </div>
          <span className="text-[11px] text-slate-500">Under longitudinal tracking</span>
        </div>

        {/* Movement Asymmetry Flags */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Kinematic Asymmetry Flags</span>
            <div className="w-7 h-7 rounded-lg bg-rose-50 text-rose-600 flex items-center justify-center">
              <HeartPulse size={16} />
            </div>
          </div>
          <div className="my-2">
            <div className="text-2xl font-black text-rose-600">{athletesWithAsymmetryFlag.length}</div>
            <span className="text-[11px] text-rose-600 font-semibold block mt-1">
              &gt;12° Bilateral Asymmetry detected
            </span>
          </div>
          <span className="text-[11px] text-slate-500">Potential compensation pattern</span>
        </div>

        {/* Clinical Cohort Risk Index */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Cohort Bilateral Symmetry</span>
            <div className="w-7 h-7 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <ShieldCheck size={16} />
            </div>
          </div>
          <div className="my-2">
            <div className="text-2xl font-black text-slate-900">{avg_symmetry_index}° diff</div>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full inline-block mt-1 bg-emerald-50 text-emerald-700">
              FIFA 11+ Normative: &lt;10°
            </span>
          </div>
          <span className="text-[11px] text-slate-500">Mean bilateral deviation</span>
        </div>
      </div>

      {/* Row 2: Anatomical Injury Distribution & Clinical Correction Guidelines */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Anatomical Injury Distribution from Real DB */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <Bandage size={16} className="text-teal-600" />
            <span>Documented Injury Anatomical Sites</span>
          </h2>
          <p className="text-xs text-slate-500">
            Pathological distribution extracted from documented athlete injury histories.
          </p>

          <div className="space-y-3 pt-2">
            {Object.keys(injury_distribution).length === 0 ? (
              <p className="text-xs text-slate-400 py-4 text-center">No past injuries logged in database.</p>
            ) : (
              Object.entries(injury_distribution).map(([site, count]) => (
                <div key={site} className="text-xs">
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-semibold text-slate-700">{site}</span>
                    <span className="font-bold text-teal-700 bg-teal-50 px-2 py-0.5 rounded-md border border-teal-200">
                      {count} cases
                    </span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                    <div
                      className="bg-teal-600 h-full rounded-full transition-all"
                      style={{ width: `${Math.min((count / (total_athletes || 1)) * 100, 100)}%` }}
                    />
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="pt-3 border-t border-slate-100 text-xs text-slate-500 flex items-center justify-between">
            <span>High Risk Patients:</span>
            <strong className="text-rose-600">{high_risk_count} requiring active intervention</strong>
          </div>
        </div>

        {/* Clinical Movement Correction Protocols */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs lg:col-span-2 flex flex-col justify-between">
          <div>
            <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2 mb-1">
              <FileCheck2 size={16} className="text-teal-600" />
              <span>Evidence-Based Rehabilitation Directives</span>
            </h2>
            <p className="text-xs text-slate-500 mb-4">
              Kinematic compensation protocols aligned with FIFA 11+ and sports physiotherapy standards.
            </p>

            <div className="space-y-3 text-xs">
              <div className="p-3.5 bg-teal-50/60 rounded-xl border border-teal-100 flex items-start gap-3">
                <div className="w-6 h-6 rounded-lg bg-teal-600 text-white flex items-center justify-center shrink-0 mt-0.5 text-xs font-bold">
                  A
                </div>
                <div>
                  <h3 className="font-bold text-teal-950">ACL & Patellofemoral Flexion Restoration</h3>
                  <p className="text-teal-900/80 mt-0.5">
                    Athletes demonstrating knee flexion deficits (&lt;70° at peak stance during drop-landing) must undergo progressive eccentric quadriceps and hamstring co-activation drills to prevent knee valgus collapse.
                  </p>
                </div>
              </div>

              <div className="p-3.5 bg-blue-50/60 rounded-xl border border-blue-100 flex items-start gap-3">
                <div className="w-6 h-6 rounded-lg bg-blue-600 text-white flex items-center justify-center shrink-0 mt-0.5 text-xs font-bold">
                  B
                </div>
                <div>
                  <h3 className="font-bold text-blue-950">Trunk Lean & Core Pelvic Stabilization</h3>
                  <p className="text-blue-900/80 mt-0.5">
                    Excessive lateral trunk lean (&gt;10°) shifts the ground reaction force vector laterally, increasing knee abduction moment. Prescribe isometric anti-rotational core holds and lateral gluteus medius loading.
                  </p>
                </div>
              </div>

              <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 flex items-start gap-3">
                <div className="w-6 h-6 rounded-lg bg-slate-700 text-white flex items-center justify-center shrink-0 mt-0.5 text-xs font-bold">
                  C
                </div>
                <div>
                  <h3 className="font-bold text-slate-900">Return-to-Play Movement Quality Clearance</h3>
                  <p className="text-slate-600 mt-0.5">
                    Clearance criteria require bilateral symmetry index &lt; 10°, composite risk index &lt; 30, and zero kinematic anomaly flags under maximum match-velocity movements.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 flex justify-between items-center text-xs">
            <span className="text-slate-500">Physiotherapy Clinical Matrix Calibrated</span>
            <span className="font-semibold text-teal-700 flex items-center gap-1">
              <CheckCircle2 size={13} /> Active Clinical Standards
            </span>
          </div>
        </div>
      </div>

      {/* Row 3: Patient Recovery & Movement Correction Directory */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-slate-50/40">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Users size={18} className="text-teal-600" />
              <span>Patient Kinematics & Rehabilitation Directory</span>
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Review joint range of motion, past injuries, and manage clinical assignments.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
            {/* Filter Mode Pills */}
            <div className="bg-slate-100 p-1 rounded-xl flex text-xs font-semibold">
              <button
                onClick={() => setFilterMode('all')}
                className={`px-3 py-1 rounded-lg transition ${
                  filterMode === 'all' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                All ({total_athletes})
              </button>
              <button
                onClick={() => setFilterMode('assigned')}
                className={`px-3 py-1 rounded-lg transition ${
                  filterMode === 'assigned' ? 'bg-white text-teal-700 shadow-xs' : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                In My Care ({assigned_count})
              </button>
              <button
                onClick={() => setFilterMode('injured')}
                className={`px-3 py-1 rounded-lg transition ${
                  filterMode === 'injured' ? 'bg-white text-amber-700 shadow-xs' : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                Injury History ({athletesWithHistory.length})
              </button>
            </div>

            {/* Search */}
            <div className="relative">
              <Search size={14} className="absolute left-3 top-2.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search patient..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="pl-8 pr-3 py-1.5 border border-slate-200 rounded-xl text-xs bg-white outline-none focus:ring-2 focus:ring-teal-100 focus:border-teal-600 w-44"
              />
            </div>
          </div>
        </div>

        {filteredAthletes.length === 0 ? (
          <div className="p-12 text-center text-slate-400 text-xs">
            <Stethoscope size={32} className="mx-auto mb-2 opacity-40" />
            <p className="font-semibold text-slate-700 text-sm">No patients matching filter</p>
            <p className="mt-1">Try switching filter modes or adjusting your search query.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-100 text-slate-400 font-semibold uppercase text-[10px] tracking-wider bg-slate-50/70">
                  <th className="py-3 px-5">Patient Name</th>
                  <th className="py-3 px-4">Injury History</th>
                  <th className="py-3 px-4">Symmetry Diff</th>
                  <th className="py-3 px-4">Trunk Lean</th>
                  <th className="py-3 px-4">Risk Level</th>
                  <th className="py-3 px-4">Care Status</th>
                  <th className="py-3 px-5 text-right">Clinical Actions</th>
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
                          <div className="w-8 h-8 rounded-xl bg-teal-50 text-teal-700 font-bold flex items-center justify-center text-xs shrink-0">
                            {a.name ? a.name[0] : 'P'}
                          </div>
                          <div>
                            <div className="font-bold text-slate-900">{a.name}</div>
                            <div className="text-[11px] text-slate-400">
                              {a.sport_type || 'Athletics'} &bull; Age: {a.age || '—'}
                            </div>
                          </div>
                        </div>
                      </td>

                      <td className="py-3.5 px-4">
                        {a.injury_count > 0 ? (
                          <span className="font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full text-[10px] border border-amber-200">
                            {a.injury_count} past incidents
                          </span>
                        ) : (
                          <span className="text-emerald-700 text-[10px] font-semibold bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                            No prior trauma
                          </span>
                        )}
                      </td>

                      <td className="py-3.5 px-4">
                        {a.symmetry_index !== null && a.symmetry_index !== undefined ? (
                          <span className={`font-semibold ${a.symmetry_index > 12 ? 'text-rose-600 font-bold' : 'text-slate-700'}`}>
                            {a.symmetry_index}° diff
                          </span>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>

                      <td className="py-3.5 px-4">
                        {a.max_trunk_lean !== null && a.max_trunk_lean !== undefined ? (
                          <span className={`font-semibold ${a.max_trunk_lean > 12 ? 'text-rose-600 font-bold' : 'text-slate-700'}`}>
                            {a.max_trunk_lean}°
                          </span>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>

                      <td className="py-3.5 px-4">
                        {hasRisk ? (
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                            isHigh ? 'bg-rose-50 text-rose-700 border border-rose-200' :
                            isMod ? 'bg-amber-50 text-amber-700 border border-amber-200' : 
                            'bg-emerald-50 text-emerald-700 border border-emerald-200'
                          }`}>
                            {a.risk_score.toFixed(1)} &bull; {a.risk_band || 'Score'}
                          </span>
                        ) : (
                          <span className="text-slate-400 italic">Pending trial</span>
                        )}
                      </td>

                      <td className="py-3.5 px-4">
                        {a.is_assigned_to_me ? (
                          <span className="text-[10px] font-bold text-teal-700 bg-teal-50 border border-teal-200 px-2 py-0.5 rounded-full flex items-center gap-1 w-max">
                            <CheckCircle2 size={11} /> Under Care
                          </span>
                        ) : (
                          <span className="text-[10px] text-slate-400">Not Assigned</span>
                        )}
                      </td>

                      <td className="py-3.5 px-5 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleTogglePatient(a.id, a.is_assigned_to_me)}
                            disabled={actionLoading === a.id}
                            className={`p-1.5 rounded-lg border text-xs font-semibold transition ${
                              a.is_assigned_to_me
                                ? 'border-slate-200 text-slate-600 hover:bg-rose-50 hover:text-rose-600'
                                : 'border-teal-200 bg-teal-50 text-teal-700 hover:bg-teal-100'
                            }`}
                            title={a.is_assigned_to_me ? 'Discharge from My Care' : 'Assign to My Care'}
                          >
                            {a.is_assigned_to_me ? <UserMinus size={13} /> : <UserPlus size={13} />}
                          </button>

                          <Link
                            to={`/dashboard/athlete/${a.id}`}
                            className="bg-teal-600 hover:bg-teal-700 text-white font-semibold px-2.5 py-1.5 rounded-lg text-xs transition flex items-center gap-1 shadow-xs"
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
    </div>
  );
};
