import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../../api/client';
import { useAuth } from '../../context/AuthContext';
import {
  Stethoscope,
  Activity,
  ShieldCheck,
  Users,
  Search,
  ChevronRight,
  UserPlus,
  UserMinus,
  CheckCircle2,
  HeartPulse,
  Bandage,
  FileText
} from 'lucide-react';
import { ReportsExportModal } from '../../components/ReportsExportModal';

export const PhysiotherapistDashboard = () => {
  const { user } = useAuth();
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filterMode, setFilterMode] = useState('all'); // 'all' | 'assigned' | 'injured'
  const [search, setSearch] = useState('');
  const [actionLoading, setActionLoading] = useState(null);
  const [selectedReportAthlete, setSelectedReportAthlete] = useState(null);

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
      <div className="max-w-6xl mx-auto py-24 px-4 text-center">
        <div className="w-10 h-10 border-3 border-teal-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-sm text-slate-300 font-medium">Loading clinical kinematics & rehabilitation data...</p>
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
          className="bg-teal-600 hover:bg-teal-500 text-white text-sm font-semibold px-5 py-2.5 rounded-xl transition shadow-lg shadow-teal-600/25"
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
    avg_symmetry_index,
    injury_distribution
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
    <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8 space-y-8">
      {/* Header Banner */}
      <div className="bg-[#11121a] rounded-2xl border border-white/10 p-6 sm:p-7 flex flex-col md:flex-row justify-between items-start md:items-center gap-6 shadow-xl">
        <div className="space-y-1.5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-teal-500/20 border border-teal-500/40 text-teal-300 flex items-center justify-center shadow-sm">
              <Stethoscope size={20} />
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">Physiotherapy & Rehabilitation</h1>
            <span className="text-xs font-bold uppercase tracking-wider px-3 py-1 rounded-full border bg-teal-500/15 text-teal-300 border-teal-500/30">
              Clinical Specialist
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-400">
            Rehabilitation tracking, movement compensation analytics, and return-to-play kinematic screening.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            to="/athletes"
            className="bg-[#1a1b28] hover:bg-[#232435] text-slate-200 border border-white/10 font-semibold text-xs sm:text-sm px-4 py-2.5 rounded-xl flex items-center gap-2 transition"
          >
            <Users size={16} className="text-teal-400" /> Patient Directory
          </Link>
        </div>
      </div>

      {/* 4 Clinical Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* Active Patients in Care */}
        <div className="bg-[#11121a] p-6 rounded-2xl border border-white/10 shadow-lg flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-xs sm:text-sm font-semibold uppercase tracking-wider text-slate-400">Assigned Patients</span>
            <div className="w-8 h-8 rounded-lg bg-teal-500/15 border border-teal-500/30 text-teal-400 flex items-center justify-center">
              <Users size={18} />
            </div>
          </div>
          <div className="my-3">
            <div className="text-3xl sm:text-4xl font-extrabold text-white">{assigned_count}</div>
            <span className="text-xs text-teal-300 font-medium block mt-1.5">
              {assigned_count === 0 ? 'No patients directly linked' : `${assigned_count} patients in active care`}
            </span>
          </div>
          <span className="text-xs text-slate-400">{total_athletes} registered in department</span>
        </div>

        {/* Recorded Injury History */}
        <div className="bg-[#11121a] p-6 rounded-2xl border border-white/10 shadow-lg flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-xs sm:text-sm font-semibold uppercase tracking-wider text-slate-400">Documented Injuries</span>
            <div className="w-8 h-8 rounded-lg bg-amber-500/15 border border-amber-500/30 text-amber-400 flex items-center justify-center">
              <Bandage size={18} />
            </div>
          </div>
          <div className="my-3">
            <div className="text-3xl sm:text-4xl font-extrabold text-amber-400">{athletesWithHistory.length}</div>
            <span className="text-xs text-amber-300 font-medium block mt-1.5">
              Prior orthopedic / soft-tissue history
            </span>
          </div>
          <span className="text-xs text-slate-400">Tracked for re-injury prevention</span>
        </div>

        {/* Movement Asymmetry Flags */}
        <div className="bg-[#11121a] p-6 rounded-2xl border border-white/10 shadow-lg flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-xs sm:text-sm font-semibold uppercase tracking-wider text-slate-400">Asymmetry Alerts</span>
            <div className="w-8 h-8 rounded-lg bg-rose-500/15 border border-rose-500/30 text-rose-400 flex items-center justify-center">
              <HeartPulse size={18} />
            </div>
          </div>
          <div className="my-3">
            <div className="text-3xl sm:text-4xl font-extrabold text-rose-400">{athletesWithAsymmetryFlag.length}</div>
            <span className="text-xs text-rose-300 font-medium block mt-1.5">
              &gt;12&deg; bilateral difference detected
            </span>
          </div>
          <span className="text-xs text-slate-400">Target for neuromuscular rehab</span>
        </div>

        {/* Cohort Bilateral Symmetry */}
        <div className="bg-[#11121a] p-6 rounded-2xl border border-white/10 shadow-lg flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-xs sm:text-sm font-semibold uppercase tracking-wider text-slate-400">Cohort Symmetry Avg</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 flex items-center justify-center">
              <ShieldCheck size={18} />
            </div>
          </div>
          <div className="my-3">
            <div className="text-3xl sm:text-4xl font-extrabold text-emerald-400">{avg_symmetry_index}&deg;</div>
            <span className="text-xs font-bold px-2.5 py-0.5 rounded-full inline-block mt-1.5 bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
              FIFA 11+ Normative: &lt;10&deg;
            </span>
          </div>
          <span className="text-xs text-slate-400">Mean bilateral deviation</span>
        </div>
      </div>

      {/* Row 2: Anatomical Injury Distribution & Evidence-Based Guidelines */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Anatomical Injury Distribution from Real DB */}
        <div className="bg-[#11121a] p-6 sm:p-7 rounded-2xl border border-white/10 shadow-xl space-y-4">
          <h2 className="text-base sm:text-lg font-bold text-white flex items-center gap-2.5">
            <Bandage size={18} className="text-teal-400" />
            <span>Documented Injury Anatomical Sites</span>
          </h2>
          <p className="text-xs text-slate-400">
            Pathological distribution extracted from documented athlete injury histories.
          </p>

          <div className="space-y-3 pt-2">
            {Object.keys(injury_distribution).length === 0 ? (
              <p className="text-xs text-slate-400 py-6 text-center">No past injuries logged in database.</p>
            ) : (
              Object.entries(injury_distribution).map(([site, count]) => (
                <div key={site} className="text-xs">
                  <div className="flex justify-between items-center mb-1 text-slate-300">
                    <span className="font-semibold">{site}</span>
                    <span className="font-bold text-teal-300 bg-teal-500/15 px-2 py-0.5 rounded-md border border-teal-500/30">
                      {count} cases
                    </span>
                  </div>
                  <div className="w-full bg-[#1e1f2f] rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-teal-500 h-full rounded-full transition-all"
                      style={{ width: `${Math.min((count / (total_athletes || 1)) * 100, 100)}%` }}
                    />
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="pt-3 border-t border-white/5 text-xs text-slate-400 flex items-center justify-between">
            <span>High Risk Patients:</span>
            <strong className="text-rose-400">{high_risk_count} requiring load intervention</strong>
          </div>
        </div>

        {/* Clinical Movement Correction Protocols */}
        <div className="bg-[#11121a] p-6 sm:p-7 rounded-2xl border border-white/10 shadow-xl lg:col-span-2 flex flex-col justify-between space-y-4">
          <div>
            <h2 className="text-base sm:text-lg font-bold text-white flex items-center gap-2 mb-1">
              <Activity size={18} className="text-teal-400" />
              <span>Evidence-Based Rehabilitation Directives</span>
            </h2>
            <p className="text-xs text-slate-400 mb-4">
              Kinematic compensation protocols aligned with FIFA 11+ and sports physiotherapy standards.
            </p>

            <div className="space-y-3.5 text-xs sm:text-sm">
              <div className="p-4 bg-teal-500/10 rounded-xl border border-teal-500/20 flex items-start gap-3.5">
                <div className="w-7 h-7 rounded-lg bg-teal-600 text-white flex items-center justify-center shrink-0 mt-0.5 text-xs font-bold">
                  A
                </div>
                <div>
                  <h3 className="font-bold text-white">ACL & Patellofemoral Flexion Restoration</h3>
                  <p className="text-slate-300 mt-1 leading-relaxed text-xs">
                    Athletes demonstrating knee flexion deficits (&lt;70&deg; at peak stance during drop-landing) must undergo progressive eccentric quadriceps and hamstring co-activation drills to prevent knee valgus collapse.
                  </p>
                </div>
              </div>

              <div className="p-4 bg-blue-500/10 rounded-xl border border-blue-500/20 flex items-start gap-3.5">
                <div className="w-7 h-7 rounded-lg bg-blue-600 text-white flex items-center justify-center shrink-0 mt-0.5 text-xs font-bold">
                  B
                </div>
                <div>
                  <h3 className="font-bold text-white">Trunk Lean & Core Pelvic Stabilization</h3>
                  <p className="text-slate-300 mt-1 leading-relaxed text-xs">
                    Excessive lateral trunk lean (&gt;10&deg;) shifts the ground reaction force vector laterally, increasing knee abduction moment. Prescribe isometric anti-rotational core holds and lateral gluteus medius loading.
                  </p>
                </div>
              </div>

              <div className="p-4 bg-purple-500/10 rounded-xl border border-purple-500/20 flex items-start gap-3.5">
                <div className="w-7 h-7 rounded-lg bg-purple-600 text-white flex items-center justify-center shrink-0 mt-0.5 text-xs font-bold">
                  C
                </div>
                <div>
                  <h3 className="font-bold text-white">Return-to-Play Movement Quality Clearance</h3>
                  <p className="text-slate-300 mt-1 leading-relaxed text-xs">
                    Clearance criteria require bilateral symmetry index &lt; 10&deg;, composite risk index &lt; 30, and zero kinematic anomaly flags under maximum match-velocity movements.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3.5 border-t border-white/5 flex justify-between items-center text-xs">
            <span className="text-slate-400">Physiotherapy Clinical Matrix Calibrated</span>
            <span className="font-semibold text-teal-400 flex items-center gap-1.5">
              <CheckCircle2 size={14} /> Active Clinical Standards
            </span>
          </div>
        </div>
      </div>

      {/* Row 3: Patient Recovery & Movement Correction Directory */}
      <div className="bg-[#11121a] rounded-2xl border border-white/10 shadow-xl overflow-hidden">
        <div className="p-6 border-b border-white/10 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-[#141522]">
          <div>
            <h2 className="text-base sm:text-lg font-bold text-white flex items-center gap-2.5">
              <Users size={20} className="text-teal-400" />
              <span>Patient Kinematics &amp; Rehabilitation Directory</span>
            </h2>
            <p className="text-xs sm:text-sm text-slate-400 mt-1">
              Review joint range of motion, past injuries, and manage clinical assignments.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 w-full sm:w-auto">
            {/* Filter Mode Pills */}
            <div className="bg-[#1c1d2e] p-1 rounded-xl flex text-xs font-semibold border border-white/5">
              <button
                onClick={() => setFilterMode('all')}
                className={`px-3 py-1.5 rounded-lg transition ${
                  filterMode === 'all' ? 'bg-teal-600 text-white shadow-sm' : 'text-slate-400 hover:text-white'
                }`}
              >
                All ({total_athletes})
              </button>
              <button
                onClick={() => setFilterMode('assigned')}
                className={`px-3 py-1.5 rounded-lg transition ${
                  filterMode === 'assigned' ? 'bg-teal-600 text-white shadow-sm' : 'text-slate-400 hover:text-white'
                }`}
              >
                In My Care ({assigned_count})
              </button>
              <button
                onClick={() => setFilterMode('injured')}
                className={`px-3 py-1.5 rounded-lg transition ${
                  filterMode === 'injured' ? 'bg-teal-600 text-white shadow-sm' : 'text-slate-400 hover:text-white'
                }`}
              >
                Injury History ({athletesWithHistory.length})
              </button>
            </div>

            {/* Search */}
            <div className="relative">
              <Search size={15} className="absolute left-3.5 top-2.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search patient..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="pl-9 pr-4 py-2 border border-white/10 rounded-xl text-xs sm:text-sm bg-[#1c1d2e] text-white outline-none focus:ring-2 focus:ring-teal-500 w-48"
              />
            </div>
          </div>
        </div>

        {filteredAthletes.length === 0 ? (
          <div className="p-16 text-center text-slate-400 text-xs sm:text-sm">
            <Stethoscope size={36} className="mx-auto mb-3 opacity-30 text-teal-400" />
            <p className="font-semibold text-white text-base">No patients matching filter</p>
            <p className="mt-1 text-slate-400">Try switching filter modes or adjusting your search query.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs sm:text-sm">
              <thead>
                <tr className="border-b border-white/10 text-slate-400 font-semibold uppercase text-xs tracking-wider bg-[#171826]">
                  <th className="py-3.5 px-6">Patient Name</th>
                  <th className="py-3.5 px-4">Injury History</th>
                  <th className="py-3.5 px-4">Symmetry Diff</th>
                  <th className="py-3.5 px-4">Trunk Lean</th>
                  <th className="py-3.5 px-4">Risk Level</th>
                  <th className="py-3.5 px-4">Care Status</th>
                  <th className="py-3.5 px-6 text-right">Clinical Actions</th>
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
                          <div className="w-9 h-9 rounded-xl bg-teal-500/20 text-teal-300 font-bold flex items-center justify-center text-sm shrink-0 border border-teal-500/30">
                            {a.name ? a.name[0] : 'P'}
                          </div>
                          <div>
                            <div className="font-bold text-white text-sm sm:text-base">{a.name}</div>
                            <div className="text-xs text-slate-400">
                              {a.sport_type || 'Athletics'} {a.position ? `&bull; ${a.position}` : ''}
                            </div>
                          </div>
                        </div>
                      </td>

                      <td className="py-4 px-4">
                        {a.injury_count > 0 ? (
                          <span className="font-semibold text-amber-300 bg-amber-500/15 px-2.5 py-1 rounded-full text-xs border border-amber-500/30">
                            {a.injury_count} past incidents
                          </span>
                        ) : (
                          <span className="text-emerald-300 text-xs font-semibold bg-emerald-500/15 px-2.5 py-1 rounded-full border border-emerald-500/30">
                            No prior trauma
                          </span>
                        )}
                      </td>

                      <td className="py-4 px-4">
                        {a.symmetry_index !== null && a.symmetry_index !== undefined ? (
                          <span className={`font-semibold ${a.symmetry_index > 12 ? 'text-rose-400 font-bold' : 'text-slate-200'}`}>
                            {a.symmetry_index}&deg; diff
                          </span>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>

                      <td className="py-4 px-4">
                        {a.max_trunk_lean !== null && a.max_trunk_lean !== undefined ? (
                          <span className={`font-semibold ${a.max_trunk_lean > 12 ? 'text-rose-400 font-bold' : 'text-slate-200'}`}>
                            {a.max_trunk_lean}&deg;
                          </span>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>

                      <td className="py-4 px-4">
                        {hasRisk ? (
                          <span className={`text-xs font-bold px-2.5 py-1 rounded-full ${
                            isHigh ? 'bg-rose-500/15 text-rose-300 border border-rose-500/30' :
                            isMod ? 'bg-amber-500/15 text-amber-300 border border-amber-500/30' : 
                            'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                          }`}>
                            {a.risk_score.toFixed(1)} &bull; {a.risk_band || 'Score'}
                          </span>
                        ) : (
                          <span className="text-slate-400 italic">Pending trial</span>
                        )}
                      </td>

                      <td className="py-4 px-4">
                        {a.is_assigned_to_me ? (
                          <span className="text-xs font-bold text-teal-300 bg-teal-500/15 border border-teal-500/30 px-3 py-1 rounded-full flex items-center gap-1.5 w-max">
                            <CheckCircle2 size={13} className="text-teal-400" /> Under Care
                          </span>
                        ) : (
                          <span className="text-xs text-slate-400">Available</span>
                        )}
                      </td>

                      <td className="py-4 px-6 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleTogglePatient(a.id, a.is_assigned_to_me)}
                            disabled={actionLoading === a.id}
                            className={`p-2 rounded-xl border text-xs font-semibold transition ${
                              a.is_assigned_to_me
                                ? 'border-white/10 text-slate-400 hover:bg-rose-500/15 hover:text-rose-300 hover:border-rose-500/30'
                                : 'border-teal-500/30 bg-teal-500/15 text-teal-300 hover:bg-teal-600 hover:text-white'
                            }`}
                            title={a.is_assigned_to_me ? 'Discharge from My Care' : 'Assign to My Care'}
                          >
                            {a.is_assigned_to_me ? <UserMinus size={15} /> : <UserPlus size={15} />}
                          </button>

                          <button
                            onClick={() => setSelectedReportAthlete({ id: a.id, name: a.name })}
                            className="p-2 rounded-xl border border-white/10 text-slate-300 hover:bg-white/10 hover:text-teal-400 text-xs font-semibold transition"
                            title="Export PDF / Excel Reports"
                          >
                            <FileText size={15} />
                          </button>

                          <Link
                            to={`/dashboard/athlete/${a.id}`}
                            className="bg-teal-600 hover:bg-teal-500 text-white font-semibold px-3 py-2 rounded-xl text-xs sm:text-sm transition flex items-center gap-1.5 shadow-md shadow-teal-600/20"
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

export default PhysiotherapistDashboard;
