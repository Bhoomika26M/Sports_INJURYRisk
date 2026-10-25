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
  Sparkles,
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
      <div className="max-w-6xl mx-auto py-20 px-4 text-center">
        <div className="w-8 h-8 border-3 border-purple-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        <p className="text-xs text-slate-500 font-medium">Aggregating biomechanical kinematics & research telemetry...</p>
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
          className="bg-purple-600 text-white text-xs font-semibold px-4 py-2 rounded-xl hover:bg-purple-700 transition"
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
    moderate_risk_count,
    low_risk_count,
    load_distribution
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
    <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8 space-y-6">
      {/* Header Banner */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 shadow-xs">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-8 h-8 rounded-xl bg-purple-50 text-purple-700 flex items-center justify-center">
              <Microscope size={18} />
            </div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">Sports Science & Biomechanics Research</h1>
            <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border bg-purple-50 text-purple-700 border-purple-200">
              Biomechanist Console
            </span>
          </div>
          <p className="text-xs text-slate-500">
            Angular velocity, multi-factor risk attribution, and quantitative bilateral kinematics.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            to="/athletes"
            className="bg-purple-600 hover:bg-purple-700 text-white font-medium text-xs px-3.5 py-2 rounded-xl flex items-center gap-1.5 shadow-xs transition"
          >
            <Activity size={14} /> All Kinematic Profiles
          </Link>
        </div>
      </div>

      {/* 4 Research Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Mean Bilateral Asymmetry */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Mean Asymmetry Index</span>
            <div className="w-7 h-7 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center">
              <Activity size={16} />
            </div>
          </div>
          <div className="my-2">
            <div className="text-2xl font-black text-purple-700">{avg_symmetry_index}°</div>
            <span className="text-[11px] text-purple-600 font-medium block mt-1">
              Bilateral knee flexion differential
            </span>
          </div>
          <span className="text-[11px] text-slate-500">Benchmark tolerance: &lt;10.0°</span>
        </div>

        {/* Population Risk Index */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Mean Composite Risk</span>
            <div className="w-7 h-7 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
              <TrendingUp size={16} />
            </div>
          </div>
          <div className="my-2">
            <div className="text-2xl font-black text-slate-900">{avg_risk_score}</div>
            <span className="text-[11px] text-blue-600 font-semibold block mt-1">
              Normalized kinematic index
            </span>
          </div>
          <span className="text-[11px] text-slate-500">n = {total_athletes} tracked subjects</span>
        </div>

        {/* Critical Variance Outliers */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Kinematic Outliers</span>
            <div className="w-7 h-7 rounded-lg bg-rose-50 text-rose-600 flex items-center justify-center">
              <Brain size={16} />
            </div>
          </div>
          <div className="my-2">
            <div className="text-2xl font-black text-rose-600">{high_risk_count}</div>
            <span className="text-[11px] text-rose-600 font-semibold block mt-1">
              &gt;2σ deviation from standard
            </span>
          </div>
          <span className="text-[11px] text-slate-500">{moderate_risk_count} borderline profiles</span>
        </div>

        {/* Engine Calibration */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Computer Vision Status</span>
            <div className="w-7 h-7 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <ShieldCheck size={16} />
            </div>
          </div>
          <div className="my-2">
            <div className="text-2xl font-black text-emerald-600">MediaPipe</div>
            <span className="text-[11px] text-emerald-700 font-semibold block mt-1">
              33 Landmark Topology
            </span>
          </div>
          <span className="text-[11px] text-slate-500">Sub-pixel spatial resolution</span>
        </div>
      </div>

      {/* Row 2: Biomechanical Asymmetry Chart & Multi-Factor Risk Attribution */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Asymmetry Variance Chart */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs lg:col-span-2">
          <div className="flex justify-between items-start mb-4">
            <div>
              <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <BarChart2 size={16} className="text-purple-600" />
                <span>Bilateral Knee Asymmetry Distribution (° Diff)</span>
              </h2>
              <p className="text-xs text-slate-500">Side-to-side angular variance during peak eccentric flexion</p>
            </div>
            <span className="text-[11px] text-slate-400 font-semibold">FIFA 11+ Threshold: 10°</span>
          </div>

          {symmetryChartData.length > 0 ? (
            <div className="h-60 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={symmetryChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="symmetry" radius={[6, 6, 0, 0]}>
                    {symmetryChartData.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={entry.symmetry > 15 ? '#f43f5e' : entry.symmetry > 10 ? '#f59e0b' : '#9333ea'}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-60 flex items-center justify-center bg-slate-50 rounded-xl text-slate-400 text-xs">
              No movement screenings recorded with symmetry data yet.
            </div>
          )}
        </div>

        {/* Multi-Factor Risk Attribution Model */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <Sliders size={16} className="text-purple-600" />
            <span>Risk Attribution Weighting</span>
          </h2>
          <p className="text-xs text-slate-500">
            Validated biomechanical weight vector applied by the injury risk engine.
          </p>

          <div className="space-y-3 pt-2 text-xs">
            <div>
              <div className="flex justify-between font-semibold mb-1">
                <span className="text-slate-700">Movement Asymmetry</span>
                <span className="text-purple-700 font-bold">30%</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                <div className="bg-purple-600 h-full w-[30%]" />
              </div>
            </div>

            <div>
              <div className="flex justify-between font-semibold mb-1">
                <span className="text-slate-700">Biomechanical Deviations</span>
                <span className="text-blue-700 font-bold">25%</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                <div className="bg-blue-600 h-full w-[25%]" />
              </div>
            </div>

            <div>
              <div className="flex justify-between font-semibold mb-1">
                <span className="text-slate-700">Cumulative Training Load</span>
                <span className="text-indigo-700 font-bold">20%</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                <div className="bg-indigo-600 h-full w-[20%]" />
              </div>
            </div>

            <div>
              <div className="flex justify-between font-semibold mb-1">
                <span className="text-slate-700">Historical Injury Factors</span>
                <span className="text-amber-700 font-bold">15%</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                <div className="bg-amber-600 h-full w-[15%]" />
              </div>
            </div>

            <div>
              <div className="flex justify-between font-semibold mb-1">
                <span className="text-slate-700">Fatigue & Angular Velocity</span>
                <span className="text-emerald-700 font-bold">10%</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                <div className="bg-emerald-600 h-full w-[10%]" />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Row 3: Quantitative Kinematic Telemetry Directory */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-slate-50/40">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Layers size={18} className="text-purple-600" />
              <span>Quantitative Kinematic Telemetry Table</span>
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Subject kinematic values, peak knee flexion indices, and composite risk coefficients.
            </p>
          </div>

          <div className="relative">
            <Search size={14} className="absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search subject..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="pl-8 pr-3 py-1.5 border border-slate-200 rounded-xl text-xs bg-white outline-none focus:ring-2 focus:ring-purple-100 focus:border-purple-600 w-52"
            />
          </div>
        </div>

        {filteredAthletes.length === 0 ? (
          <div className="p-12 text-center text-slate-400 text-xs">
            <Microscope size={32} className="mx-auto mb-2 opacity-40" />
            <p className="font-semibold text-slate-700 text-sm">No kinematic records found</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-100 text-slate-400 font-semibold uppercase text-[10px] tracking-wider bg-slate-50/70">
                  <th className="py-3 px-5">Subject ID & Name</th>
                  <th className="py-3 px-4">Symmetry (° Diff)</th>
                  <th className="py-3 px-4">Trunk Lean (°)</th>
                  <th className="py-3 px-4">Left Knee Flexion</th>
                  <th className="py-3 px-4">Right Knee Flexion</th>
                  <th className="py-3 px-4">Risk Coefficient</th>
                  <th className="py-3 px-5 text-right">Telemetry Analysis</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredAthletes.map(a => {
                  return (
                    <tr key={a.id} className="hover:bg-slate-50/80 transition font-mono">
                      <td className="py-3.5 px-5 font-sans">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-xl bg-purple-50 text-purple-700 font-bold flex items-center justify-center text-xs shrink-0">
                            #{a.id}
                          </div>
                          <div>
                            <div className="font-bold text-slate-900">{a.name}</div>
                            <div className="text-[11px] text-slate-400 font-normal">
                              {a.sport_type || 'General Athletics'}
                            </div>
                          </div>
                        </div>
                      </td>

                      <td className="py-3.5 px-4 font-mono font-semibold">
                        {a.symmetry_index !== null && a.symmetry_index !== undefined ? (
                          <span className={a.symmetry_index > 15 ? 'text-rose-600 font-bold' : 'text-slate-800'}>
                            {a.symmetry_index}°
                          </span>
                        ) : '—'}
                      </td>

                      <td className="py-3.5 px-4 font-mono font-semibold">
                        {a.max_trunk_lean !== null && a.max_trunk_lean !== undefined ? (
                          <span className={a.max_trunk_lean > 12 ? 'text-rose-600 font-bold' : 'text-slate-800'}>
                            {a.max_trunk_lean}°
                          </span>
                        ) : '—'}
                      </td>

                      <td className="py-3.5 px-4 font-mono text-slate-700">
                        {a.left_knee_min !== null && a.left_knee_min !== undefined ? `${a.left_knee_min}°` : '—'}
                      </td>

                      <td className="py-3.5 px-4 font-mono text-slate-700">
                        {a.right_knee_min !== null && a.right_knee_min !== undefined ? `${a.right_knee_min}°` : '—'}
                      </td>

                      <td className="py-3.5 px-4 font-sans">
                        {a.risk_score !== null && a.risk_score !== undefined ? (
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                            a.risk_score > 60 ? 'bg-rose-50 text-rose-700' :
                            a.risk_score >= 30 ? 'bg-amber-50 text-amber-700' : 'bg-emerald-50 text-emerald-700'
                          }`}>
                            {a.risk_score.toFixed(1)} / 100
                          </span>
                        ) : (
                          <span className="text-slate-400 italic">No score</span>
                        )}
                      </td>

                      <td className="py-3.5 px-5 text-right font-sans">
                        <Link
                          to={`/dashboard/athlete/${a.id}`}
                          className="bg-purple-600 hover:bg-purple-700 text-white font-semibold px-2.5 py-1.5 rounded-lg text-xs transition inline-flex items-center gap-1 shadow-xs"
                        >
                          <span>Review Full Kinematics</span>
                          <ChevronRight size={13} />
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
