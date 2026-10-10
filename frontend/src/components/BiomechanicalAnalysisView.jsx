import React from 'react';
import { Activity, ShieldCheck, AlertCircle, Compass, Scale, Gauge, Zap, TrendingUp, BarChart2 } from 'lucide-react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ReferenceLine, Legend, AreaChart, Area } from 'recharts';

export default function BiomechanicalAnalysisView({ biomechanics, currentVideo }) {
  if (!biomechanics) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-12 text-center space-y-3">
        <Activity className="w-12 h-12 text-slate-600 mx-auto animate-pulse" />
        <h3 className="text-base font-bold text-white">No Biomechanical Analysis Run Yet</h3>
        <p className="text-xs text-slate-400 max-w-md mx-auto">
          Please navigate to the Video & Pose Tracker tab and click "Run Biomechanical Analysis & Predictions" on a selected movement video.
        </p>
      </div>
    );
  }

  const m = biomechanics.metrics || {};
  const timeSeries = (biomechanics.time_series_data || []).map(pt => ({
    time: Number(pt.time.toFixed(2)),
    valgus_l: pt.knee_valgus_l,
    valgus_r: pt.knee_valgus_r,
    knee_l: pt.knee_angle_l,
    knee_r: pt.knee_angle_r,
    trunk: pt.trunk_lateral_lean,
    asymmetry: pt.bilateral_asymmetry
  }));

  const metricsGrid = [
    {
      label: 'Dynamic Knee Valgus (L/R Peak)',
      value: `${m.knee_valgus_left_max || 0}° / ${m.knee_valgus_right_max || 0}°`,
      benchmark: '< 10.0°',
      status: (m.knee_valgus_right_max > 15 || m.knee_valgus_left_max > 15) ? 'Critical' : (m.knee_valgus_right_max > 10 ? 'Warning' : 'Good'),
      description: 'Medial knee collapse during peak deceleration impact.'
    },
    {
      label: 'Hip Stability Score',
      value: `${m.hip_stability_score || 0} / 100`,
      sub: `Pelvic Drop: ${m.pelvic_drop_deg || 0}°`,
      benchmark: '> 80 (Drop < 2.5°)',
      status: m.hip_stability_score < 70 ? 'Warning' : 'Good',
      description: 'Lumbopelvic control and Trendelenburg sign resistance.'
    },
    {
      label: 'Peak Lateral Trunk Lean',
      value: `${m.trunk_lean_lateral_max || 0}°`,
      sub: `Forward Flexion: ${m.trunk_lean_forward_max || 0}°`,
      benchmark: '< 6.0°',
      status: m.trunk_lean_lateral_max > 10 ? 'Critical' : m.trunk_lean_lateral_max > 6 ? 'Warning' : 'Good',
      description: 'Lateral torso displacement creating lever-arm knee torque.'
    },
    {
      label: 'Landing Mechanics Score',
      value: `${m.landing_mechanics_score || 0} / 100`,
      sub: `Initial Contact Flex: ${m.initial_contact_knee_flexion_deg || 0}°`,
      benchmark: '> 75 (Soft Landing)',
      status: m.landing_mechanics_score < 60 ? 'Critical' : 'Good',
      description: 'Degree of knee flexion dampening ground impact shock.'
    },
    {
      label: 'Movement Symmetry Index',
      value: `${m.movement_symmetry_score || 0}%`,
      benchmark: '> 88% Symmetry',
      status: m.movement_symmetry_score < 80 ? 'Critical' : m.movement_symmetry_score < 88 ? 'Warning' : 'Good',
      description: 'Bilateral kinematic concordance between limbs.'
    },
    {
      label: 'Range of Motion (ROM) Score',
      value: `${m.range_of_motion_score || 0} / 100`,
      benchmark: '> 80',
      status: 'Good',
      description: 'Full articulation sweep throughout athletic movement cycle.'
    },
    {
      label: 'Estimated Ground Force Impact',
      value: `${m.force_impact_estimation_g || 0} G`,
      benchmark: '< 3.0 G',
      status: m.force_impact_estimation_g > 3.5 ? 'Critical' : m.force_impact_estimation_g > 2.8 ? 'Warning' : 'Good',
      description: 'Estimated kinetic ground reaction force multiplier.'
    },
    {
      label: 'Joint Collinear Alignment',
      value: `${m.joint_alignment_score || 0} / 100`,
      benchmark: '> 85',
      status: m.joint_alignment_score < 70 ? 'Warning' : 'Good',
      description: 'Ankle-knee-hip sagittal and frontal plane tracking fidelity.'
    },
    {
      label: 'Balance & Stability Index',
      value: `${m.balance_stability_index || 0} / 100`,
      benchmark: '> 80',
      status: m.balance_stability_index < 70 ? 'Warning' : 'Good',
      description: 'Center of mass trajectory stability relative to base of support.'
    },
    {
      label: 'Estimated Stride / Jump Reach',
      value: `${m.stride_length_est || 1.6} m`,
      benchmark: 'Sport Specific',
      status: 'Good',
      description: 'Effective kinematic extension stride distance.'
    }
  ];

  return (
    <div className="space-y-6">
      {/* Header Overview */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-slate-900/60 p-4 rounded-2xl border border-slate-800">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <BarChart2 className="w-5 h-5 text-cyan-400" />
            Biomechanical Assessment Studio
          </h2>
          <p className="text-xs text-slate-400">
            Session: <span className="text-slate-200 font-semibold">{currentVideo?.title || 'Movement Test'}</span> | Frames Analyzed: {biomechanics.total_frames_analyzed} at {biomechanics.mean_fps} FPS
          </p>
        </div>

        <div className="flex items-center gap-2 bg-slate-950 px-3 py-1.5 rounded-xl border border-slate-800 text-xs">
          <span className="text-slate-400">Overall Symmetry:</span>
          <span className="font-bold text-cyan-400">{m.movement_symmetry_score}%</span>
        </div>
      </div>

      {/* 10 Biomechanical Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3.5">
        {metricsGrid.map((metric, i) => (
          <div
            key={i}
            className="bg-slate-900/70 p-3.5 rounded-2xl border border-slate-800 hover:border-slate-700 transition-all space-y-2 relative overflow-hidden"
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-slate-400 truncate pr-1">{metric.label}</span>
              <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded uppercase ${
                metric.status === 'Critical'
                  ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                  : metric.status === 'Warning'
                  ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                  : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
              }`}>
                {metric.status}
              </span>
            </div>

            <div>
              <p className="text-lg font-black text-white font-mono tracking-tight">{metric.value}</p>
              {metric.sub && <p className="text-[10px] text-slate-400 font-mono">{metric.sub}</p>}
            </div>

            <div className="pt-1 border-t border-slate-800/80 flex items-center justify-between text-[10px] text-slate-500">
              <span>Norm: {metric.benchmark}</span>
            </div>
            <p className="text-[10px] text-slate-400 line-clamp-1">{metric.description}</p>
          </div>
        ))}
      </div>

      {/* Kinematics Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Dynamic Knee Valgus Chart */}
        <div className="bg-slate-900/70 p-5 rounded-2xl border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-rose-400" />
                Dynamic Knee Valgus Angle (Frontal Plane FPPA)
              </h3>
              <p className="text-[11px] text-slate-400">
                Red dotted line denotes the 15.0° clinical threshold for non-contact ACL rupture risk.
              </p>
            </div>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={timeSeries} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 10 }} unit="s" />
                <YAxis stroke="#64748b" tick={{ fontSize: 10 }} unit="°" domain={[0, 25]} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#090d16', borderColor: '#334155', borderRadius: '8px', fontSize: '11px' }}
                />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                <ReferenceLine y={15} stroke="#f43f5e" strokeDasharray="4 4" label={{ value: '15° High ACL Risk Threshold', fill: '#f43f5e', fontSize: 10, position: 'top' }} />
                <Line type="monotone" dataKey="valgus_l" stroke="#06b6d4" strokeWidth={2} dot={false} name="Left Valgus (°)" />
                <Line type="monotone" dataKey="valgus_r" stroke="#f43f5e" strokeWidth={2.5} dot={false} name="Right Valgus (°)" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Knee Flexion Angle & Landing Deceleration */}
        <div className="bg-slate-900/70 p-5 rounded-2xl border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Compass className="w-4 h-4 text-cyan-400" />
                Knee Flexion Range of Motion (Landing Cushion)
              </h3>
              <p className="text-[11px] text-slate-400">
                Lower degrees represent deeper knee bend. Stiff landing (&gt; 130°) amplifies impact strain.
              </p>
            </div>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={timeSeries} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="kneeFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 10 }} unit="s" />
                <YAxis stroke="#64748b" tick={{ fontSize: 10 }} unit="°" domain={[40, 180]} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#090d16', borderColor: '#334155', borderRadius: '8px', fontSize: '11px' }}
                />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                <Area type="monotone" dataKey="knee_l" stroke="#3b82f6" strokeWidth={2} fillOpacity={1} fill="url(#kneeFill)" name="Left Knee Flexion (°)" />
                <Line type="monotone" dataKey="knee_r" stroke="#a855f7" strokeWidth={2} dot={false} name="Right Knee Flexion (°)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
