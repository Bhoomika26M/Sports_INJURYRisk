import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../../api/client';
import {
  Microscope,
  Activity,
  Layers,
  TrendingUp,
  Search,
  ChevronRight,
  ShieldCheck,
  Brain,
  Sliders,
  BarChart2
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell
} from 'recharts';

export const SportsScientistDashboard = () => {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');

  const fetchSummary = async () => {
    try {
      setLoading(true);
      setError('');
      const res = await api.get('/dashboard/roster-summary');
      setSummary(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load sports science telemetry');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSummary();
  }, []);

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto py-24 px-4 text-center">
        <div className="w-10 h-10 border-3 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-sm text-slate-300 font-medium">Aggregating biomechanical kinematics & research telemetry...</p>
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
    avg_risk_score,
    avg_symmetry_index,
    high_risk_count,
    moderate_risk_count
  } = summary;

  // Chart data: athletes with symmetry data
  const symmetryChartData = athletes
    .filter(a => a.symmetry_index !== null && a.symmetry_index !== undefined)
    .slice(0, 10)
    .map(a => ({
      name: a.name.split(' ')[0] || `A#${a.id}`,
      symmetry: a.symmetry_index,
      risk: a.risk_score || 0
    }));

  const filteredAthletes = athletes.filter(a => {
    const q = search.toLowerCase();
    return (
      (a.name && a.name.toLowerCase().includes(q)) ||
      (a.sport_type && a.sport_type.toLowerCase().includes(q)) ||
      String(a.id).includes(q)
    );
  });

  return (
    <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8 space-y-8">
      {/* Header Banner */}
      <div className="bg-[#11121a] rounded-2xl border border-white/10 p-6 sm:p-7 flex flex-col md:flex-row justify-between items-start md:items-center gap-6 shadow-xl">
        <div className="space-y-1.5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-purple-500/20 border border-purple-500/40 text-purple-300 flex items-center justify-center shadow-sm">
              <Microscope size={20} />
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">Sports Science &amp; Biomechanics</h1>
            <span className="text-xs font-bold uppercase tracking-wider px-3 py-1 rounded-full border bg-purple-500/15 text-purple-300 border-purple-500/30">
              Biomechanist Console
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-400">
            Angular kinematics, multi-factor risk attribution, and quantitative bilateral movement analysis.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            to="/datasets"
            className="bg-[#1a1b28] hover:bg-[#232435] text-slate-200 border border-white/10 font-semibold text-xs sm:text-sm px-4 py-2.5 rounded-xl flex items-center gap-2 transition"
          >
            <Activity size={16} className="text-purple-400" /> Research Datasets
          </Link>
        </div>
      </div>

      {/* 4 Research Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* Mean Bilateral Asymmetry */}
        <div className="bg-[#11121a] p-6 rounded-2xl border border-white/10 shadow-lg flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-xs sm:text-sm font-semibold uppercase tracking-wider text-slate-400">Mean Asymmetry Index</span>
            <div className="w-8 h-8 rounded-lg bg-purple-500/15 border border-purple-500/30 text-purple-400 flex items-center justify-center">
              <Activity size={18} />
            </div>
          </div>
          <div className="my-3">
            <div className="text-3xl sm:text-4xl font-extrabold text-white">{avg_symmetry_index}&deg;</div>
            <span className="text-xs text-purple-300 font-medium block mt-1.5">
              Bilateral knee flexion differential
            </span>
          </div>
          <span className="text-xs text-slate-400">FIFA 11+ Normative: &lt;10.0&deg;</span>
        </div>

        {/* Population Risk Index */}
        <div className="bg-[#11121a] p-6 rounded-2xl border border-white/10 shadow-lg flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-xs sm:text-sm font-semibold uppercase tracking-wider text-slate-400">Mean Composite Risk</span>
            <div className="w-8 h-8 rounded-lg bg-indigo-500/15 border border-indigo-500/30 text-indigo-400 flex items-center justify-center">
              <TrendingUp size={18} />
            </div>
          </div>
          <div className="my-3">
            <div className="text-3xl sm:text-4xl font-extrabold text-indigo-400">{avg_risk_score}</div>
            <span className="text-xs text-indigo-300 font-medium block mt-1.5">
              Population risk index / 100
            </span>
          </div>
          <span className="text-xs text-slate-400">n = {total_athletes} monitored subjects</span>
        </div>

        {/* Critical Variance Outliers */}
        <div className="bg-[#11121a] p-6 rounded-2xl border border-white/10 shadow-lg flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-xs sm:text-sm font-semibold uppercase tracking-wider text-slate-400">Kinematic Outliers</span>
            <div className="w-8 h-8 rounded-lg bg-rose-500/15 border border-rose-500/30 text-rose-400 flex items-center justify-center">
              <Brain size={18} />
            </div>
          </div>
          <div className="my-3">
            <div className="text-3xl sm:text-4xl font-extrabold text-rose-400">{high_risk_count}</div>
            <span className="text-xs text-rose-300 font-medium block mt-1.5">
              Elevated risk (&gt;60 score)
            </span>
          </div>
          <span className="text-xs text-slate-400">{moderate_risk_count} borderline profiles</span>
        </div>

        {/* Engine Calibration */}
        <div className="bg-[#11121a] p-6 rounded-2xl border border-white/10 shadow-lg flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-xs sm:text-sm font-semibold uppercase tracking-wider text-slate-400">Pose Estimation</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 flex items-center justify-center">
              <ShieldCheck size={18} />
            </div>
          </div>
          <div className="my-3">
            <div className="text-3xl sm:text-4xl font-extrabold text-emerald-400">MediaPipe</div>
            <span className="text-xs text-emerald-300 font-medium block mt-1.5">
              33 Landmark Topology
            </span>
          </div>
          <span className="text-xs text-slate-400">Sub-pixel spatial tracking</span>
        </div>
      </div>

      {/* Row 2: Biomechanical Asymmetry Chart & Spec Risk Model Weighting */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Asymmetry Variance Chart */}
        <div className="bg-[#11121a] p-6 sm:p-7 rounded-2xl border border-white/10 shadow-xl lg:col-span-2 space-y-4">
          <div className="flex justify-between items-start">
            <div>
              <h2 className="text-base sm:text-lg font-bold text-white flex items-center gap-2">
                <BarChart2 size={18} className="text-purple-400" />
                <span>Bilateral Knee Asymmetry Distribution (&deg; Diff)</span>
              </h2>
              <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
                Side-to-side angular variance during peak eccentric knee flexion
              </p>
            </div>
            <span className="text-xs text-slate-400 font-medium bg-[#1e1f2f] px-3 py-1 rounded-full border border-white/5">
              FIFA 11+ Threshold: &le;10&deg;
            </span>
          </div>

          {symmetryChartData.length > 0 ? (
            <div className="h-64 w-full pt-2">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={symmetryChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.06)" />
                  <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#94a3b8' }} />
                  <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#161724',
                      borderColor: 'rgba(255,255,255,0.1)',
                      borderRadius: '0.75rem',
                      color: '#fff',
                      fontSize: '12px'
                    }}
                  />
                  <Bar dataKey="symmetry" radius={[6, 6, 0, 0]}>
                    {symmetryChartData.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={entry.symmetry > 15 ? '#f43f5e' : entry.symmetry > 10 ? '#f59e0b' : '#a855f7'}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-64 flex items-center justify-center bg-[#161724] rounded-xl text-slate-400 text-xs sm:text-sm border border-white/5">
              No movement screenings recorded with symmetry data yet.
            </div>
          )}
        </div>

        {/* Multi-Factor Risk Attribution Model (Documented Spec Weights) */}
        <div className="bg-[#11121a] p-6 sm:p-7 rounded-2xl border border-white/10 shadow-xl space-y-4">
          <h2 className="text-base sm:text-lg font-bold text-white flex items-center gap-2">
            <Sliders size={18} className="text-purple-400" />
            <span>Documented Risk Weighting</span>
          </h2>
          <p className="text-xs text-slate-400">
            Weighted composite scoring model specified in project requirements (Page 6).
          </p>

          <div className="space-y-3.5 pt-2 text-xs">
            <div>
              <div className="flex justify-between font-semibold mb-1 text-slate-300">
                <span>Biomechanical Deviations</span>
                <span className="text-purple-300 font-bold">35%</span>
              </div>
              <div className="w-full bg-[#1e1f2f] rounded-full h-2 overflow-hidden">
                <div className="bg-purple-500 h-full w-[35%]" />
              </div>
            </div>

            <div>
              <div className="flex justify-between font-semibold mb-1 text-slate-300">
                <span>Historical Injury Factors</span>
                <span className="text-amber-300 font-bold">20%</span>
              </div>
              <div className="w-full bg-[#1e1f2f] rounded-full h-2 overflow-hidden">
                <div className="bg-amber-500 h-full w-[20%]" />
              </div>
            </div>

            <div>
              <div className="flex justify-between font-semibold mb-1 text-slate-300">
                <span>Movement Asymmetry</span>
                <span className="text-indigo-300 font-bold">20%</span>
              </div>
              <div className="w-full bg-[#1e1f2f] rounded-full h-2 overflow-hidden">
                <div className="bg-indigo-500 h-full w-[20%]" />
              </div>
            </div>

            <div>
              <div className="flex justify-between font-semibold mb-1 text-slate-300">
                <span>Training Load Indicators</span>
                <span className="text-blue-300 font-bold">15%</span>
              </div>
              <div className="w-full bg-[#1e1f2f] rounded-full h-2 overflow-hidden">
                <div className="bg-blue-500 h-full w-[15%]" />
              </div>
            </div>

            <div>
              <div className="flex justify-between font-semibold mb-1 text-slate-300">
                <span>Fatigue Indicators</span>
                <span className="text-emerald-300 font-bold">10%</span>
              </div>
              <div className="w-full bg-[#1e1f2f] rounded-full h-2 overflow-hidden">
                <div className="bg-emerald-500 h-full w-[10%]" />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Row 3: Quantitative Kinematic Telemetry Directory */}
      <div className="bg-[#11121a] rounded-2xl border border-white/10 shadow-xl overflow-hidden">
        <div className="p-6 border-b border-white/10 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-[#141522]">
          <div>
            <h2 className="text-base sm:text-lg font-bold text-white flex items-center gap-2.5">
              <Layers size={20} className="text-purple-400" />
              <span>Quantitative Kinematic Telemetry</span>
            </h2>
            <p className="text-xs sm:text-sm text-slate-400 mt-1">
              Subject kinematic values, peak knee flexion indices, and composite risk coefficients.
            </p>
          </div>

          <div className="relative">
            <Search size={15} className="absolute left-3.5 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search subject or sport..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="pl-9 pr-4 py-2 border border-white/10 rounded-xl text-xs sm:text-sm bg-[#1c1d2e] text-white outline-none focus:ring-2 focus:ring-purple-500 w-56"
            />
          </div>
        </div>

        {filteredAthletes.length === 0 ? (
          <div className="p-16 text-center text-slate-400 text-xs sm:text-sm">
            <Microscope size={36} className="mx-auto mb-3 opacity-30 text-purple-400" />
            <p className="font-semibold text-white text-base">No kinematic records found</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs sm:text-sm">
              <thead>
                <tr className="border-b border-white/10 text-slate-400 font-semibold uppercase text-xs tracking-wider bg-[#171826]">
                  <th className="py-3.5 px-6">Subject</th>
                  <th className="py-3.5 px-4">Symmetry Diff</th>
                  <th className="py-3.5 px-4">Trunk Lean</th>
                  <th className="py-3.5 px-4">Left Knee Flexion</th>
                  <th className="py-3.5 px-4">Right Knee Flexion</th>
                  <th className="py-3.5 px-4">Risk Coefficient</th>
                  <th className="py-3.5 px-6 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-slate-300">
                {filteredAthletes.map(a => {
                  return (
                    <tr key={a.id} className="hover:bg-white/5 transition">
                      <td className="py-4 px-6">
                        <div className="flex items-center gap-3">
                          <div className="w-9 h-9 rounded-xl bg-purple-500/20 text-purple-300 font-bold flex items-center justify-center text-xs shrink-0 border border-purple-500/30">
                            #{a.id}
                          </div>
                          <div>
                            <div className="font-bold text-white text-sm sm:text-base">{a.name}</div>
                            <div className="text-xs text-slate-400">
                              {a.sport_type || 'General Athletics'}
                            </div>
                          </div>
                        </div>
                      </td>

                      <td className="py-4 px-4 font-mono">
                        {a.symmetry_index !== null && a.symmetry_index !== undefined ? (
                          <span className={a.symmetry_index > 15 ? 'text-rose-400 font-bold' : 'text-slate-200'}>
                            {a.symmetry_index}&deg;
                          </span>
                        ) : '—'}
                      </td>

                      <td className="py-4 px-4 font-mono">
                        {a.max_trunk_lean !== null && a.max_trunk_lean !== undefined ? (
                          <span className={a.max_trunk_lean > 12 ? 'text-rose-400 font-bold' : 'text-slate-200'}>
                            {a.max_trunk_lean}&deg;
                          </span>
                        ) : '—'}
                      </td>

                      <td className="py-4 px-4 font-mono text-slate-300">
                        {a.left_knee_min !== null && a.left_knee_min !== undefined ? `${a.left_knee_min}°` : '—'}
                      </td>

                      <td className="py-4 px-4 font-mono text-slate-300">
                        {a.right_knee_min !== null && a.right_knee_min !== undefined ? `${a.right_knee_min}°` : '—'}
                      </td>

                      <td className="py-4 px-4">
                        {a.risk_score !== null && a.risk_score !== undefined ? (
                          <span className={`text-xs font-bold px-2.5 py-1 rounded-full ${
                            a.risk_score > 60 ? 'bg-rose-500/15 text-rose-300 border border-rose-500/30' :
                            a.risk_score >= 30 ? 'bg-amber-500/15 text-amber-300 border border-amber-500/30' : 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                          }`}>
                            {a.risk_score.toFixed(1)} / 100
                          </span>
                        ) : (
                          <span className="text-slate-400 italic">No score</span>
                        )}
                      </td>

                      <td className="py-4 px-6 text-right">
                        <Link
                          to={`/dashboard/athlete/${a.id}`}
                          className="bg-purple-600 hover:bg-purple-500 text-white font-semibold px-3 py-2 rounded-xl text-xs sm:text-sm transition inline-flex items-center gap-1.5 shadow-md shadow-purple-600/20"
                        >
                          <span>Kinematics</span>
                          <ChevronRight size={14} />
                        </Link>
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

export default SportsScientistDashboard;
