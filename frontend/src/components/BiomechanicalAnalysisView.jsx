import React from 'react';
import { Activity, ShieldCheck, AlertCircle, Compass, Scale, Gauge, Zap, TrendingUp, BarChart2, FileText, FileSpreadsheet } from 'lucide-react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ReferenceLine, Legend, AreaChart, Area } from 'recharts';
import { api } from '../api/client';

export default function BiomechanicalAnalysisView({ biomechanics, currentVideo }) {
  if (!biomechanics) {
    return (
      <div className="bg-white border border-slate-200 rounded-xl p-12 text-center space-y-3 shadow-xs">
        <Activity className="w-12 h-12 text-slate-400 mx-auto" />
        <h3 className="text-base font-bold text-slate-900">No Biomechanical Analysis Run Yet</h3>
        <p className="text-xs text-slate-500 max-w-md mx-auto">
          Please navigate to the Video &amp; Pose Tracker tab and click &quot;Run Pose Analysis &amp; Screening&quot; on a selected movement video.
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
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
        <div>
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <BarChart2 className="w-5 h-5 text-teal-700" />
            Biomechanical Assessment Studio
          </h2>
          <p className="text-xs text-slate-500">
            Session: <span className="text-slate-800 font-semibold">{currentVideo?.title || 'Movement Test'}</span> | Frames Analyzed: {biomechanics.total_frames_analyzed} at {biomechanics.mean_fps} FPS
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-2 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200 text-xs">
            <span className="text-slate-500">Overall Symmetry:</span>
            <span className="font-bold text-teal-800">{m.movement_symmetry_score}%</span>
          </div>

          {currentVideo?.id && (
            <div className="flex items-center gap-1.5">
              <a
                href={api.getPdfReportUrl(currentVideo.id)}
                target="_blank"
                rel="noreferrer"
                download
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-teal-50 hover:bg-teal-100 text-teal-800 border border-teal-200 text-xs font-semibold transition-colors"
                title="Download Biomechanical Assessment PDF Report"
              >
                <FileText className="w-3.5 h-3.5" />
                <span>PDF Report</span>
              </a>
              <a
                href={api.getExcelReportUrl(currentVideo.id)}
                target="_blank"
                rel="noreferrer"
                download
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200 text-xs font-semibold transition-colors"
                title="Download Biomechanical Kinematics Excel Spreadsheet"
              >
                <FileSpreadsheet className="w-3.5 h-3.5" />
                <span>Excel Data</span>
              </a>
            </div>
          )}
        </div>
      </div>

      {/* 10 Biomechanical Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3.5">
        {metricsGrid.map((metric, i) => (
          <div
            key={i}
            className="bg-white p-3.5 rounded-xl border border-slate-200 hover:border-slate-300 shadow-xs transition-colors space-y-2 relative overflow-hidden"
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-slate-600 truncate pr-1">{metric.label}</span>
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                metric.status === 'Critical'
                  ? 'bg-rose-50 text-rose-800 border border-rose-200'
                  : metric.status === 'Warning'
                  ? 'bg-amber-50 text-amber-800 border border-amber-200'
                  : 'bg-emerald-50 text-emerald-800 border border-emerald-200'
              }`}>
                {metric.status}
              </span>
            </div>

            <div>
              <p className="text-xl font-bold text-slate-900 font-mono tracking-tight">{metric.value}</p>
              {metric.sub && <p className="text-[11px] text-slate-500 font-mono">{metric.sub}</p>}
            </div>

            <div className="pt-1.5 border-t border-slate-100 flex items-center justify-between text-[10px] text-slate-500">
              <span>Norm: {metric.benchmark}</span>
            </div>
            <p className="text-[10px] text-slate-500 line-clamp-1">{metric.description}</p>
          </div>
        ))}
      </div>

      {/* Kinematics Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Dynamic Knee Valgus Chart */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-rose-700" />
                Dynamic Knee Valgus Angle (Frontal Plane FPPA)
              </h3>
              <p className="text-[11px] text-slate-500">
                Red dotted line marks a 15.0° demo reference; it is not a validated clinical threshold.
              </p>
            </div>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={timeSeries} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 10, fill: '#64748b' }} unit="s" />
                <YAxis stroke="#64748b" tick={{ fontSize: 10, fill: '#64748b' }} unit="°" domain={[0, 25]} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#ffffff', borderColor: '#cbd5e1', borderRadius: '8px', fontSize: '11px', color: '#0f172a', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}
                />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                <ReferenceLine y={15} stroke="#b91c1c" strokeDasharray="4 4" label={{ value: '15° High ACL Risk Threshold', fill: '#b91c1c', fontSize: 10, position: 'top' }} />
                <Line type="monotone" dataKey="valgus_l" stroke="#0f766e" strokeWidth={2} dot={false} connectNulls={false} name="Left Valgus (°)" />
                <Line type="monotone" dataKey="valgus_r" stroke="#b91c1c" strokeWidth={2.5} dot={false} connectNulls={false} name="Right Valgus (°)" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Knee Flexion Angle & Landing Deceleration */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Compass className="w-4 h-4 text-teal-700" />
                Knee Flexion Range of Motion (Landing Cushion)
              </h3>
              <p className="text-[11px] text-slate-500">
                Lower degrees represent deeper knee bend. Stiff landing (&gt; 130°) amplifies impact strain.
              </p>
            </div>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={timeSeries} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="kneeFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0f766e" stopOpacity={0.15}/>
                    <stop offset="95%" stopColor="#0f766e" stopOpacity={0.0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 10, fill: '#64748b' }} unit="s" />
                <YAxis stroke="#64748b" tick={{ fontSize: 10, fill: '#64748b' }} unit="°" domain={[40, 180]} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#ffffff', borderColor: '#cbd5e1', borderRadius: '8px', fontSize: '11px', color: '#0f172a', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}
                />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                <Area type="monotone" dataKey="knee_l" stroke="#0f766e" strokeWidth={2} fillOpacity={1} fill="url(#kneeFill)" connectNulls={false} name="Left Knee Flexion (°)" />
                <Line type="monotone" dataKey="knee_r" stroke="#334155" strokeWidth={2} dot={false} connectNulls={false} name="Right Knee Flexion (°)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
