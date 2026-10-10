import React from 'react';
import { ShieldAlert, AlertTriangle, AlertCircle, CheckCircle, Activity, Heart, Zap, Clock, TrendingUp } from 'lucide-react';

export default function InjuryRiskView({ injuryRisk, athlete }) {
  if (!injuryRisk) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-12 text-center space-y-3">
        <ShieldAlert className="w-12 h-12 text-slate-600 mx-auto animate-pulse" />
        <h3 className="text-base font-bold text-white">No Injury Risk Assessment Available</h3>
        <p className="text-xs text-slate-400 max-w-md mx-auto">
          Run the video analysis in the Video & Pose Tracker tab to compute the weighted predictive injury score.
        </p>
      </div>
    );
  }

  const score = injuryRisk.overall_injury_risk_score || 0;
  const category = injuryRisk.risk_category || 'Low Risk';
  const categoryRisks = injuryRisk.category_risks || {};
  const anomalies = injuryRisk.anomalies_detected || [];

  // Color schemes based on category
  const getBadgeStyle = (cat) => {
    switch (cat) {
      case 'Critical Risk':
      case 'Critical':
        return 'bg-rose-500/15 text-rose-400 border-rose-500/30';
      case 'High Risk':
      case 'High':
        return 'bg-rose-500/10 text-rose-300 border-rose-500/20';
      case 'Moderate Risk':
      case 'Moderate':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      default:
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
    }
  };

  const weightedComponents = [
    {
      name: 'Biomechanical Deviations',
      weight: '35%',
      score: injuryRisk.biomechanical_deviation_score,
      contrib: (0.35 * injuryRisk.biomechanical_deviation_score).toFixed(1),
      desc: 'Dynamic knee valgus, trunk lean, and landing stiffness penalties.'
    },
    {
      name: 'Historical Injury Factors',
      weight: '20%',
      score: injuryRisk.historical_injury_factor_score,
      contrib: (0.20 * injuryRisk.historical_injury_factor_score).toFixed(1),
      desc: 'Prior surgical reconstruction or recurrent joint laxity history.'
    },
    {
      name: 'Movement Asymmetry',
      weight: '20%',
      score: injuryRisk.movement_asymmetry_score,
      contrib: (0.20 * injuryRisk.movement_asymmetry_score).toFixed(1),
      desc: 'Bilateral limb kinetic discrepancy exceeding 15% threshold.'
    },
    {
      name: 'Training Load Indicators',
      weight: '15%',
      score: injuryRisk.training_load_indicator_score,
      contrib: (0.15 * injuryRisk.training_load_indicator_score).toFixed(1),
      desc: 'Acute-to-Chronic Workload Ratio (ACWR) and weekly hour spikes.'
    },
    {
      name: 'Fatigue Indicators',
      weight: '10%',
      score: injuryRisk.fatigue_indicator_score,
      contrib: (0.10 * injuryRisk.fatigue_indicator_score).toFixed(1),
      desc: 'Kinematic drift and progressive technique decay across repetitions.'
    }
  ];

  const overallScores = [
    { label: 'Movement Quality', value: injuryRisk.movement_quality_score, icon: Activity, color: 'text-cyan-400' },
    { label: 'Biomechanical Efficiency', value: injuryRisk.biomechanical_efficiency_score, icon: Zap, color: 'text-purple-400' },
    { label: 'Fatigue Risk Index', value: injuryRisk.fatigue_risk_score, icon: Clock, color: 'text-amber-400' },
    { label: 'Athlete Health Score', value: injuryRisk.overall_athlete_health_score, icon: Heart, color: 'text-emerald-400' },
  ];

  return (
    <div className="space-y-6">
      {/* Weighted Scoring Model Banner */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Composite Gauge Card */}
        <div className="bg-slate-900/80 p-6 rounded-2xl border border-slate-800 flex flex-col items-center justify-center text-center space-y-4 shadow-xl relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 opacity-10">
            <ShieldAlert className="w-36 h-36 text-rose-500" />
          </div>

          <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
            Composite Injury Risk Score
          </span>

          <div className="relative w-40 h-40 flex items-center justify-center">
            {/* SVG Circle Gauge */}
            <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="40" stroke="#1e293b" strokeWidth="8" fill="transparent" />
              <circle
                cx="50"
                cy="50"
                r="40"
                stroke={score > 85 ? '#f43f5e' : score > 60 ? '#fb7185' : score > 30 ? '#f59e0b' : '#10b981'}
                strokeWidth="8"
                strokeDasharray="251.2"
                strokeDashoffset={251.2 - (251.2 * score) / 100}
                strokeLinecap="round"
                fill="transparent"
                className="transition-all duration-1000 ease-out"
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-3xl font-black text-white font-mono">{score.toFixed(1)}</span>
              <span className="text-[10px] text-slate-400 font-mono">/ 100</span>
            </div>
          </div>

          <div>
            <span className={`inline-block px-3 py-1 rounded-full text-xs font-bold border ${getBadgeStyle(category)}`}>
              {category}
            </span>
            <p className="text-xs text-slate-400 mt-2 max-w-xs">
              Weighted composite calculation formulated from 5 biomechanical and physical risk variables.
            </p>
          </div>
        </div>

        {/* Weighted Formula Breakdown (PDF Page 6 exact model) */}
        <div className="lg:col-span-2 bg-slate-900/80 p-6 rounded-2xl border border-slate-800 space-y-4 shadow-xl">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-cyan-400" />
                Weighted Scoring Formula (PDF Architecture)
              </h3>
              <p className="text-[11px] text-slate-400">
                Formula: Deviations (35%) + Historical (20%) + Asymmetry (20%) + Training Load (15%) + Fatigue (10%)
              </p>
            </div>
            <span className="text-xs font-mono font-bold text-cyan-400 bg-cyan-950/60 px-2.5 py-1 rounded-lg border border-cyan-800/80">
              Score: {score}
            </span>
          </div>

          <div className="space-y-3">
            {weightedComponents.map((item, idx) => (
              <div key={idx} className="p-2.5 rounded-xl bg-slate-950/70 border border-slate-800/80 space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-200">
                    {item.name} <span className="text-cyan-400 font-mono text-[11px]">({item.weight})</span>
                  </span>
                  <div className="flex items-center gap-2 font-mono">
                    <span className="text-slate-400 text-[11px]">Subscore: {item.score}</span>
                    <span className="text-cyan-400 font-bold text-[11px]">Contrib: +{item.contrib}</span>
                  </div>
                </div>

                <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full"
                    style={{ width: `${Math.min(100, item.score)}%` }}
                  />
                </div>
                <p className="text-[10px] text-slate-400 truncate">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 4 Supporting Scores */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {overallScores.map((s, i) => {
          const Icon = s.icon;
          return (
            <div key={i} className="bg-slate-900/60 p-4 rounded-2xl border border-slate-800 flex items-center gap-3">
              <div className={`p-2.5 rounded-xl bg-slate-800/80 ${s.color}`}>
                <Icon className="w-5 h-5" />
              </div>
              <div>
                <p className="text-xs text-slate-400">{s.label}</p>
                <p className="text-xl font-black text-white font-mono">{s.value || 0} / 100</p>
              </div>
            </div>
          );
        })}
      </div>

      {/* 6 Specific Injury Categories Breakdown */}
      <div className="space-y-4">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-400" />
            Specific Injury Categories Prediction (6 Core Sports Risk Factors)
          </h3>
          <p className="text-xs text-slate-400">
            Multi-modal predictive classification matching the six injury profiles defined in the project specification.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Object.entries(categoryRisks).map(([key, item]) => (
            <div
              key={key}
              className="bg-slate-900/70 p-5 rounded-2xl border border-slate-800 hover:border-slate-700 transition-all space-y-3.5 flex flex-col justify-between"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-bold text-white">{item.category_name}</span>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${getBadgeStyle(item.risk_level)}`}>
                    {item.risk_level}
                  </span>
                </div>

                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-black text-white font-mono">{item.risk_score}</span>
                  <span className="text-xs text-slate-400 font-mono">({(item.probability * 100).toFixed(0)}% Probability)</span>
                </div>

                <p className="text-xs text-slate-300 leading-relaxed">{item.description}</p>
              </div>

              <div className="pt-3 border-t border-slate-800 space-y-1.5">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">Contributing Factors:</span>
                <ul className="space-y-1">
                  {(item.primary_factors || []).map((factor, fIdx) => (
                    <li key={fIdx} className="text-[11px] text-slate-400 flex items-start gap-1.5">
                      <span className="text-cyan-400 font-bold shrink-0">•</span>
                      <span>{factor}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Movement Anomaly Detection Timeline */}
      <div className="bg-slate-900/70 p-5 rounded-2xl border border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Activity className="w-4 h-4 text-cyan-400" />
              Detected Movement Anomalies & Kinematic Breaches
            </h3>
            <p className="text-[11px] text-slate-400">
              High-frequency temporal anomaly events pinpointed across movement video timeline.
            </p>
          </div>
          <span className="text-xs font-mono text-slate-400">
            Total Flags: {anomalies.length}
          </span>
        </div>

        {anomalies.length === 0 ? (
          <div className="p-6 text-center text-xs text-slate-500">
            No kinematic breaches detected exceeding safety thresholds.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {anomalies.map((anom, idx) => (
              <div key={idx} className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-200">{anom.anomaly_type}</span>
                  <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${getBadgeStyle(anom.severity)}`}>
                    {anom.severity}
                  </span>
                </div>
                <p className="text-[11px] text-slate-400">{anom.description}</p>
                <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono pt-1 border-t border-slate-800/80">
                  <span>Frame #{anom.frame_index}</span>
                  <span>Time: {anom.timestamp_sec.toFixed(2)}s</span>
                  <span className="text-rose-400 font-bold">{anom.metric_value.toFixed(1)}° (Threshold: {anom.threshold_value}°)</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
