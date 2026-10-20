import React, { useState, useEffect } from 'react';
import { ShieldAlert, AlertTriangle, AlertCircle, CheckCircle, Activity, Heart, Zap, Clock, TrendingUp, FileText, FileSpreadsheet, Info, Calendar } from 'lucide-react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, Legend } from 'recharts';
import { api } from '../api/client';

export default function InjuryRiskView({ injuryRisk, athlete, currentVideo }) {
  const [trends, setTrends] = useState([]);
  const [loadingTrends, setLoadingTrends] = useState(false);

  const athleteId = athlete?.id || injuryRisk?.athlete_id || 1;

  useEffect(() => {
    let isMounted = true;
    async function loadTrends() {
      try {
        setLoadingTrends(true);
        const data = await api.getAthleteRiskTrends(athleteId);
        if (isMounted && data?.trends) {
          setTrends(data.trends);
        }
      } catch (err) {
        console.error('Failed to load risk trends:', err);
      } finally {
        if (isMounted) setLoadingTrends(false);
      }
    }
    if (athleteId) {
      loadTrends();
    }
    return () => { isMounted = false; };
  }, [athleteId, injuryRisk?.id]);

  if (!injuryRisk) {
    return (
      <div className="bg-white border border-slate-200 rounded-xl p-12 text-center space-y-3 shadow-xs">
        <ShieldAlert className="w-12 h-12 text-slate-400 mx-auto" />
        <h3 className="text-base font-bold text-slate-900">No Injury Risk Assessment Available</h3>
        <p className="text-xs text-slate-500 max-w-md mx-auto">
          Run the video analysis in the Video &amp; Pose Tracker tab to compute the weighted predictive injury score.
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
        return 'bg-rose-50 text-rose-800 border-rose-200';
      case 'High Risk':
      case 'High':
        return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'Moderate Risk':
      case 'Moderate':
        return 'bg-amber-50 text-amber-800 border-amber-200';
      default:
        return 'bg-emerald-50 text-emerald-800 border-emerald-200';
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
    { label: 'Movement Quality', value: injuryRisk.movement_quality_score, icon: Activity, color: 'text-teal-700' },
    { label: 'Biomechanical Efficiency', value: injuryRisk.biomechanical_efficiency_score, icon: Zap, color: 'text-slate-700' },
    { label: 'Fatigue Risk Index', value: injuryRisk.fatigue_risk_score, icon: Clock, color: 'text-amber-700' },
    { label: 'Athlete Health Score', value: injuryRisk.overall_athlete_health_score, icon: Heart, color: 'text-emerald-700' },
  ];

  const exportVideoId = currentVideo?.id || injuryRisk.video_id;

  return (
    <div className="space-y-6">
      {/* Header & Export Controls */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-rose-700" />
            Injury Risk &amp; Predictive Biomechanics
          </h2>
          <p className="text-xs text-slate-500">
            Multi-factor predictive model combining biomechanics (35%), injury history (20%), asymmetry (20%), workload (15%), and fatigue (10%).
          </p>
        </div>

        {exportVideoId && (
          <div className="flex items-center gap-2 shrink-0">
            <a
              href={api.getPdfReportUrl(exportVideoId)}
              target="_blank"
              rel="noreferrer"
              download
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-teal-50 hover:bg-teal-100 text-teal-800 border border-teal-200 text-xs font-semibold transition-colors"
              title="Download Full PDF Risk & Biomechanics Report"
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Export PDF Report</span>
            </a>
            <a
              href={api.getExcelReportUrl(exportVideoId)}
              target="_blank"
              rel="noreferrer"
              download
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200 text-xs font-semibold transition-colors"
              title="Download Kinematics & Risk Excel Workbook"
            >
              <FileSpreadsheet className="w-3.5 h-3.5" />
              <span>Export Excel Data</span>
            </a>
          </div>
        )}
      </div>

      {/* Weighted Scoring Model Banner */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Composite Gauge Card */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs flex flex-col items-center justify-center text-center space-y-3 relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 opacity-5">
            <ShieldAlert className="w-36 h-36 text-slate-900" />
          </div>

          <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
            Composite Injury Risk Score
          </span>

          <div className="relative w-40 h-40 flex items-center justify-center">
            {/* SVG Circle Gauge */}
            <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="40" stroke="#f1f5f9" strokeWidth="8" fill="transparent" />
              <circle
                cx="50"
                cy="50"
                r="40"
                stroke={score > 85 ? '#b91c1c' : score > 60 ? '#c2410c' : score > 30 ? '#d97706' : '#15803d'}
                strokeWidth="8"
                strokeDasharray="251.2"
                strokeDashoffset={251.2 - (251.2 * score) / 100}
                strokeLinecap="round"
                fill="transparent"
                className="transition-all duration-1000 ease-out"
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-3xl font-bold text-slate-900 font-mono">{score.toFixed(1)}</span>
              <span className="text-[10px] text-slate-500 font-mono">/ 100</span>
            </div>
          </div>

          <div>
            <span className={`inline-block px-3 py-0.5 rounded-full text-xs font-bold border ${getBadgeStyle(category)}`}>
              {category}
            </span>
            <p className="text-xs text-slate-500 mt-2 max-w-xs leading-relaxed">
              Weighted composite calculation formulated from 5 biomechanical and physical risk variables.
            </p>
          </div>
        </div>

        {/* Weighted Formula Breakdown */}
        <div className="lg:col-span-2 bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-teal-700" />
                Weighted Scoring Model (Biomechanics &amp; Physical Load Architecture)
              </h3>
              <p className="text-[11px] text-slate-500">
                Formula: Deviations (35%) + Historical (20%) + Asymmetry (20%) + Training Load (15%) + Fatigue (10%)
              </p>
            </div>
            <span className="text-xs font-mono font-bold text-slate-800 bg-slate-100 px-2.5 py-1 rounded-md border border-slate-200">
              Score: {score}
            </span>
          </div>

          <div className="space-y-3">
            {weightedComponents.map((item, idx) => (
              <div key={idx} className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-800">
                    {item.name} <span className="text-teal-700 font-mono text-[11px]">({item.weight})</span>
                  </span>
                  <div className="flex items-center gap-2 font-mono">
                    <span className="text-slate-500 text-[11px]">Subscore: {item.score}</span>
                    <span className="text-teal-800 font-bold text-[11px]">Contrib: +{item.contrib}</span>
                  </div>
                </div>

                <div className="h-1.5 w-full bg-slate-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-teal-700 rounded-full"
                    style={{ width: `${Math.min(100, item.score)}%` }}
                  />
                </div>
                <p className="text-[10px] text-slate-500 truncate">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Scientific Methodology Notice Card */}
      <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 flex items-start gap-3">
        <Info className="w-5 h-5 text-teal-700 shrink-0 mt-0.5" />
        <div className="space-y-1 text-xs">
          <p className="font-bold text-slate-800">Rule-Based Deterministic Risk Methodology</p>
          <p className="text-slate-600 leading-relaxed">
            Kinematix evaluates injury risk using deterministic, rule-based algorithms formulated from peer-reviewed sports medicine and biomechanics literature (Hewett et al. dynamic valgus, Gabbett ACWR workload spikes, Limb Symmetry Index). Kinematix is designed for athletic screening, movement monitoring, and workload intelligence. It does not provide medical diagnoses or replace qualified clinical evaluation.
          </p>
        </div>
      </div>

      {/* Longitudinal Risk Score Trends Section */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-teal-700" />
              Longitudinal Injury Risk &amp; Movement Quality Trends
            </h3>
            <p className="text-[11px] text-slate-500">
              Historical progression across athlete video assessment sessions tracking risk mitigation and movement symmetry.
            </p>
          </div>
          <span className="text-xs font-mono text-slate-700 bg-slate-100 px-2.5 py-1 rounded-md border border-slate-200">
            {trends.length} Recorded Session{trends.length === 1 ? '' : 's'}
          </span>
        </div>

        <div className="h-60 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={trends.length > 0 ? trends.map(t => ({
                session: `S${t.session_index}`,
                date: t.created_at,
                'Injury Risk': t.overall_injury_risk_score,
                'Movement Quality': t.movement_quality_score,
                'Asymmetry Score': t.movement_asymmetry_score
              })) : [{
                session: 'Current',
                date: 'Today',
                'Injury Risk': score,
                'Movement Quality': injuryRisk.movement_quality_score || 65,
                'Asymmetry Score': injuryRisk.movement_asymmetry_score || 75
              }]}
              margin={{ top: 10, right: 20, left: -20, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="session" stroke="#64748b" tick={{ fontSize: 11, fill: '#64748b' }} />
              <YAxis stroke="#64748b" tick={{ fontSize: 11, fill: '#64748b' }} domain={[0, 100]} />
              <Tooltip
                contentStyle={{ backgroundColor: '#ffffff', borderColor: '#cbd5e1', borderRadius: '8px', fontSize: '11px', color: '#0f172a', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}
              />
              <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
              <Line type="monotone" dataKey="Injury Risk" stroke="#b91c1c" strokeWidth={2.5} dot={{ r: 4 }} name="Overall Injury Risk (/100)" />
              <Line type="monotone" dataKey="Movement Quality" stroke="#15803d" strokeWidth={2} dot={{ r: 4 }} name="Movement Quality (/100)" />
              <Line type="monotone" dataKey="Asymmetry Score" stroke="#d97706" strokeWidth={2} dot={{ r: 3 }} name="Asymmetry Index (/100)" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 4 Supporting Scores */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {overallScores.map((s, i) => {
          const Icon = s.icon;
          return (
            <div key={i} className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center gap-3">
              <div className={`p-2.5 rounded-lg bg-slate-50 border border-slate-200 ${s.color}`}>
                <Icon className="w-5 h-5" />
              </div>
              <div>
                <p className="text-xs text-slate-500 font-medium">{s.label}</p>
                <p className="text-xl font-bold text-slate-900 font-mono">{s.value || 0} / 100</p>
              </div>
            </div>
          );
        })}
      </div>

      {/* 6 Specific Injury Categories Breakdown */}
      <div className="space-y-4">
        <div>
          <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-600" />
            Specific Injury Categories Prediction (6 Core Sports Risk Factors)
          </h3>
          <p className="text-xs text-slate-500">
            Multi-modal predictive classification matching the six injury profiles defined in the project specification.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Object.entries(categoryRisks).map(([key, item]) => (
            <div
              key={key}
              className="bg-white p-5 rounded-xl border border-slate-200 hover:border-slate-300 shadow-xs transition-colors space-y-3.5 flex flex-col justify-between"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-bold text-slate-900">{item.category_name}</span>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${getBadgeStyle(item.risk_level)}`}>
                    {item.risk_level}
                  </span>
                </div>

                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-bold text-slate-900 font-mono">{item.risk_score}</span>
                  <span className="text-xs text-slate-500 font-mono">({(item.probability * 100).toFixed(0)}% Probability)</span>
                </div>

                <p className="text-xs text-slate-600 leading-relaxed">{item.description}</p>
              </div>

              <div className="pt-3 border-t border-slate-100 space-y-1.5">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">Contributing Factors:</span>
                <ul className="space-y-1">
                  {(item.primary_factors || []).map((factor, fIdx) => (
                    <li key={fIdx} className="text-[11px] text-slate-600 flex items-start gap-1.5">
                      <span className="text-teal-700 font-bold shrink-0">•</span>
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
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Activity className="w-4 h-4 text-teal-700" />
              Detected Movement Anomalies &amp; Kinematic Breaches
            </h3>
            <p className="text-[11px] text-slate-500">
              High-frequency temporal anomaly events pinpointed across movement video timeline.
            </p>
          </div>
          <span className="text-xs font-mono text-slate-700 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
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
              <div key={idx} className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-800">{anom.anomaly_type}</span>
                  <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border ${getBadgeStyle(anom.severity)}`}>
                    {anom.severity}
                  </span>
                </div>
                <p className="text-[11px] text-slate-600">{anom.description}</p>
                <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono pt-1.5 border-t border-slate-200">
                  <span>Frame #{anom.frame_index}</span>
                  <span>Time: {anom.timestamp_sec.toFixed(2)}s</span>
                  <span className="text-rose-700 font-bold">{anom.metric_value.toFixed(1)}° (Threshold: {anom.threshold_value}°)</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
