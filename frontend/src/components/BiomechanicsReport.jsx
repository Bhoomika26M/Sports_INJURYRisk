import { useState, useEffect } from 'react';
import api from '../api/client';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Activity, ShieldCheck, Compass } from 'lucide-react';

export const BiomechanicsReport = ({ videoId }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchAnalysis = async () => {
      try {
        const res = await api.get(`/analysis/${videoId}`);
        setData(res.data);
      } catch (err) {
        setError(err.response?.data?.detail || 'Failed to load biomechanics analysis');
      } finally {
        setLoading(false);
      }
    };
    if (videoId) {
      fetchAnalysis();
    }
  }, [videoId]);

  if (loading) return <div className="p-8 text-center text-xs text-slate-400">Loading biomechanical kinematics...</div>;
  if (error) return <div className="p-4 bg-rose-500/10 text-rose-300 text-xs rounded-xl border border-rose-500/30">{error}</div>;
  if (!data) return null;

  const agg = data.aggregates || {};
  const valgus = agg.knee_valgus || {};
  const landing = agg.landing_mechanics || {};
  const force = agg.force_estimation || {};
  const hipStab = agg.hip_stability || {};
  const stride = agg.stride_and_gait || {};
  const balance = agg.balance_metrics || {};
  const posture = agg.posture_assessment || {};
  const rom = agg.range_of_motion || {};
  const sym = agg.movement_symmetry || {};

  const chartData = (data.metrics_over_time || [])
    .filter(m => m.quality_flag === 'OK')
    .map(m => ({
      time: (m.timestamp_ms / 1000).toFixed(2),
      leftKnee: m.left_knee_angle ? Math.round(m.left_knee_angle) : null,
      rightKnee: m.right_knee_angle ? Math.round(m.right_knee_angle) : null,
      trunkLean: m.trunk_lean ? Math.round(m.trunk_lean) : null,
      kneeValgus: m.knee_valgus_ratio ? Math.round(m.knee_valgus_ratio * 100) : null,
      pelvicDrop: m.pelvic_drop_angle ? Math.round(m.pelvic_drop_angle) : null
    }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h3 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
          <Activity size={18} className="text-purple-400" />
          <span>Biomechanical Analysis Engine</span>
        </h3>
        <p className="text-xs text-slate-400 mt-0.5">
          Full-body kinematic telemetry, dynamic valgus tracking, ground reaction forces, and posture stability.
        </p>
      </div>
      
      {data.disclaimer && (
        <div className="bg-purple-500/10 border border-purple-500/20 rounded-xl p-3.5 text-xs text-purple-200 flex items-start gap-2.5">
          <ShieldCheck size={16} className="text-purple-400 shrink-0 mt-0.5" />
          <p className="leading-relaxed">{data.disclaimer}</p>
        </div>
      )}

      {/* Primary Kinematic Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
        <div className="bg-[#161724] p-4 rounded-xl border border-white/5">
          <span className="text-xs text-slate-400 font-semibold uppercase block">Knee Valgus Ratio</span>
          <div className="flex items-baseline gap-1 mt-1">
            <p className="text-xl font-bold text-white">{valgus.min_knee_ankle_ratio ?? 'N/A'}</p>
            <span className="text-xs text-slate-400">KAR</span>
          </div>
          <span className={`text-xs font-bold mt-1.5 inline-block px-2.5 py-0.5 rounded-full ${
            valgus.dynamic_valgus_detected ? 'bg-rose-500/15 text-rose-300 border border-rose-500/30' : 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
          }`}>
            {valgus.valgus_risk_tier || 'Optimal Alignment'}
          </span>
        </div>

        <div className="bg-[#161724] p-4 rounded-xl border border-white/5">
          <span className="text-xs text-slate-400 font-semibold uppercase block">Landing Mechanics</span>
          <div className="flex items-baseline gap-1 mt-1">
            <p className="text-xl font-bold text-white">{landing.flexion_depth_deg ? `${landing.flexion_depth_deg}°` : 'N/A'}</p>
            <span className="text-xs text-slate-400">Flexion</span>
          </div>
          <span className={`text-xs font-bold mt-1.5 inline-block px-2.5 py-0.5 rounded-full ${
            landing.landing_stiffness?.startsWith('Stiff') ? 'bg-rose-500/15 text-rose-300 border border-rose-500/30' : 'bg-purple-500/15 text-purple-300 border border-purple-500/30'
          }`}>
            {landing.landing_stiffness || 'Normal Damping'}
          </span>
        </div>

        <div className="bg-[#161724] p-4 rounded-xl border border-white/5">
          <span className="text-xs text-slate-400 font-semibold uppercase block">Estimated Peak vGRF</span>
          <div className="flex items-baseline gap-1 mt-1">
            <p className="text-xl font-bold text-indigo-400">{force.peak_vgrf_bw ? `${force.peak_vgrf_bw}x` : 'N/A'}</p>
            <span className="text-xs text-slate-400">BW</span>
          </div>
          <span className="text-xs font-semibold text-slate-400 mt-1.5 block">
            {force.impact_severity || 'Low Impact Rate'}
          </span>
        </div>

        <div className="bg-[#161724] p-4 rounded-xl border border-white/5">
          <span className="text-xs text-slate-400 font-semibold uppercase block">Limb Symmetry Index</span>
          <div className="flex items-baseline gap-1 mt-1">
            <p className="text-xl font-bold text-emerald-400">{sym.limb_symmetry_index_pct ? `${sym.limb_symmetry_index_pct}%` : 'N/A'}</p>
            <span className="text-xs text-slate-400">LSI</span>
          </div>
          <span className="text-xs font-semibold text-slate-400 mt-1.5 block">
            {sym.symmetry_status || 'Diff <= 10°'}
          </span>
        </div>
      </div>

      {/* Secondary Biomechanical Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
        <div className="bg-[#161724] p-4 rounded-xl border border-white/5">
          <span className="text-xs text-slate-400 font-semibold block">Pelvic Drop Angle</span>
          <p className="text-lg font-bold text-white mt-0.5">{hipStab.max_pelvic_drop_deg ? `${hipStab.max_pelvic_drop_deg}°` : 'N/A'}</p>
          <span className="text-xs text-slate-400">{hipStab.stability_status || 'Level Pelvis'}</span>
        </div>

        <div className="bg-[#161724] p-4 rounded-xl border border-white/5">
          <span className="text-xs text-slate-400 font-semibold block">Max Trunk Lean</span>
          <p className="text-lg font-bold text-white mt-0.5">{agg.max_trunk_lean ? `${agg.max_trunk_lean}°` : 'N/A'}</p>
          <span className="text-xs text-slate-400">{posture.max_coronal_lateral_sway ? `Lateral: ${posture.max_coronal_lateral_sway}°` : 'Sagittal lean'}</span>
        </div>

        <div className="bg-[#161724] p-4 rounded-xl border border-white/5">
          <span className="text-xs text-slate-400 font-semibold block">Balance Stability</span>
          <p className="text-lg font-bold text-white mt-0.5">{balance.balance_stability_score ? `${balance.balance_stability_score}/100` : 'N/A'}</p>
          <span className="text-xs text-slate-400">{balance.medial_lateral_sway_std_px ? `Sway: ±${balance.medial_lateral_sway_std_px}px` : 'Dynamic COM'}</span>
        </div>

        <div className="bg-[#161724] p-4 rounded-xl border border-white/5">
          <span className="text-xs text-slate-400 font-semibold block">Stride & Gait Ratio</span>
          <p className="text-lg font-bold text-white mt-0.5">{stride.max_stride_ratio ?? 'N/A'}</p>
          <span className="text-xs text-slate-400">{stride.overstriding_risk ? 'Overstriding Risk' : 'Normal Cadence'}</span>
        </div>
      </div>

      {/* Range of Motion (ROM) Details */}
      {Object.keys(rom).length > 0 && (
        <div className="bg-[#161724] p-4 rounded-xl border border-white/5">
          <h4 className="font-bold text-white text-xs mb-3 flex items-center gap-1.5">
            <Compass size={14} className="text-purple-400" />
            <span>Joint Range of Motion (ROM) & Excursion</span>
          </h4>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="p-3 bg-[#11121a] rounded-lg border border-white/5">
              <span className="text-slate-400 text-xs uppercase font-bold block">Left Knee ROM</span>
              <strong className="text-white text-sm">{rom.left_knee_rom ? `${rom.left_knee_rom}°` : 'N/A'}</strong>
              <span className="text-xs text-slate-400 block mt-0.5">Min: {agg.left_knee_min}°</span>
            </div>
            <div className="p-3 bg-[#11121a] rounded-lg border border-white/5">
              <span className="text-slate-400 text-xs uppercase font-bold block">Right Knee ROM</span>
              <strong className="text-white text-sm">{rom.right_knee_rom ? `${rom.right_knee_rom}°` : 'N/A'}</strong>
              <span className="text-xs text-slate-400 block mt-0.5">Min: {agg.right_knee_min}°</span>
            </div>
            <div className="p-3 bg-[#11121a] rounded-lg border border-white/5">
              <span className="text-slate-400 text-xs uppercase font-bold block">Hip Flexion ROM</span>
              <strong className="text-white text-sm">{rom.left_hip_rom ? `${rom.left_hip_rom}°` : 'N/A'}</strong>
              <span className="text-xs text-slate-400 block mt-0.5">Bilateral excursion</span>
            </div>
            <div className="p-3 bg-[#11121a] rounded-lg border border-white/5">
              <span className="text-slate-400 text-xs uppercase font-bold block">Ankle Excursion</span>
              <strong className="text-white text-sm">{rom.left_ankle_rom ? `${rom.left_ankle_rom}°` : 'N/A'}</strong>
              <span className="text-xs text-slate-400 block mt-0.5">Dorsi/Plantar</span>
            </div>
          </div>
        </div>
      )}

      {/* Knee Angles Over Time */}
      <div>
        <h4 className="font-bold text-white text-xs mb-2">Bilateral Knee Flexion Kinematics</h4>
        <div className="h-60 w-full bg-[#161724] p-3 rounded-xl border border-white/5">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.06)" />
              <XAxis dataKey="time" tick={{ fontSize: 11, fill: '#94a3b8' }} />
              <YAxis domain={[0, 180]} tick={{ fontSize: 11, fill: '#94a3b8' }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#11121a',
                  borderColor: 'rgba(255,255,255,0.1)',
                  borderRadius: '0.75rem',
                  color: '#fff',
                  fontSize: '12px'
                }}
              />
              <Legend verticalAlign="top" height={30} wrapperStyle={{ fontSize: '11px', color: '#cbd5e1' }} />
              <Line type="monotone" dataKey="leftKnee" name="Left Knee (°)" stroke="#818cf8" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="rightKnee" name="Right Knee (°)" stroke="#f43f5e" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Trunk Lean & Valgus Ratio Over Time */}
      <div>
        <h4 className="font-bold text-white text-xs mb-2">Posture & Frontal Plane Alignment Trajectory</h4>
        <div className="h-56 w-full bg-[#161724] p-3 rounded-xl border border-white/5">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.06)" />
              <XAxis dataKey="time" tick={{ fontSize: 11, fill: '#94a3b8' }} />
              <YAxis domain={[0, 'auto']} tick={{ fontSize: 11, fill: '#94a3b8' }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#11121a',
                  borderColor: 'rgba(255,255,255,0.1)',
                  borderRadius: '0.75rem',
                  color: '#fff',
                  fontSize: '12px'
                }}
              />
              <Legend verticalAlign="top" height={30} wrapperStyle={{ fontSize: '11px', color: '#cbd5e1' }} />
              <Line type="monotone" dataKey="trunkLean" name="Trunk Lean (°)" stroke="#a855f7" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="pelvicDrop" name="Pelvic Drop (°)" stroke="#f59e0b" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

export default BiomechanicsReport;
