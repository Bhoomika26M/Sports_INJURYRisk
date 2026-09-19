"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiClient, fetchAsObjectUrl } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer
} from 'recharts';

type BiomechanicsSummary = {
  metric_name: string;
  peak_value: number | null;
  min_value: number | null;
  range_of_motion: number | null;
};

type BiomechanicsFrame = {
  frame_number: number;
  metric_name: string;
  metric_value: number;
  plane: string;
  confidence: string;
};

type BiomechanicsResponse = {
  video_id: string;
  detection_rate: number | null;
  limb_symmetry_index: number | null;
  summary: BiomechanicsSummary[];
  frames: BiomechanicsFrame[];
};

type RiskScoreBreakdownComponent = {
  points: number;
  max: number;
  detail?: string;
  flagged?: boolean;
  lsi?: number | null;
  caveat?: string;
};

type RiskScoreResponse = {
  status?: string;
  have?: number;
  need?: number;
  overall_score?: number;
  risk_category?: string;
  score_breakdown?: {
    movement_anomaly: RiskScoreBreakdownComponent;
    asymmetry_flag: RiskScoreBreakdownComponent;
    prior_injury_flag: RiskScoreBreakdownComponent;
  };
  methodology_note?: string;
};

type Recommendation = {
  category: string;
  title: string;
  description: string;
  priority: number;
};

type VideoDetails = {
  id: string;
  original_filename: string;
  movement_type: string;
  annotated_video_key?: string;
  fps: number;
};

function formatMetricName(name: string) {
  return name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

export default function ResultsPage() {
  const { id } = useParams() as { id: string };
  const router = useRouter();
  const [data, setData] = useState<BiomechanicsResponse | null>(null);
  const [video, setVideo] = useState<VideoDetails | null>(null);
  const [riskScore, setRiskScore] = useState<RiskScoreResponse | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendation[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);

  // Hook 1: Fetch all data
  useEffect(() => {
    async function loadData() {
      try {
        const [v, b] = await Promise.all([
          apiClient.fetchWithAuth(`/videos/${id}`),
          apiClient.fetchWithAuth(`/videos/${id}/biomechanics`)
        ]);

        setVideo(v);
        setData(b);

        try {
          const rs = await apiClient.fetchWithAuth(`/videos/${id}/risk-score`);
          setRiskScore(rs);
          if (!rs.status) {
            const recs = await apiClient.fetchWithAuth(`/videos/${id}/recommendations`);
            setRecommendations(recs);
          }
        } catch (e) {
          console.error("Failed to load risk score", e);
        }
        
        if (v.annotated_video_key) {
          const url = await fetchAsObjectUrl(`/videos/${id}/file`);
          setVideoUrl(url);
        }
      } catch (err: any) {
        setError(err.message || "Failed to load results");
      }
    }
    loadData();
  }, [id]);

  // Hook 2: Cleanup object URL on unmount (MUST BE BEFORE ANY CONDITIONAL RETURN)
  useEffect(() => {
    return () => {
      if (videoUrl) URL.revokeObjectURL(videoUrl);
    };
  }, [videoUrl]);

  if (error) {
    return (
      <div className="max-w-3xl mx-auto py-12">
        <div className="neu-card rounded-2xl p-6 border-red-200 text-red-600 flex items-center gap-3">
          <svg className="w-5 h-5 text-red-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="text-sm font-medium">{error}</span>
        </div>
      </div>
    );
  }

  if (!data || !video) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="neu-card p-6 rounded-2xl flex items-center gap-3 text-slate-700">
          <svg className="animate-spin h-5 w-5 text-blue-600" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span className="text-sm font-medium">Loading biomechanical analysis results...</span>
        </div>
      </div>
    );
  }

  // Process frame data for Recharts
  const chartDataMap = new Map<number, any>();
  const metricsSet = new Set<string>();

  data.frames.forEach(f => {
    metricsSet.add(f.metric_name);
    if (!chartDataMap.has(f.frame_number)) {
      chartDataMap.set(f.frame_number, { frame_number: f.frame_number, time_sec: f.frame_number / (video.fps || 30) });
    }
    const entry = chartDataMap.get(f.frame_number);
    entry[f.metric_name] = f.metric_value;
  });

  const chartData = Array.from(chartDataMap.values()).sort((a, b) => a.frame_number - b.frame_number);

  const getQualityLabel = (rate: number | null) => {
    if (rate === null) return { text: "Unknown", color: "bg-slate-100 text-slate-500 border border-slate-200" };
    if (rate >= 0.95) return { text: "Excellent", color: "bg-emerald-50 text-emerald-700 border border-emerald-200" };
    if (rate >= 0.85) return { text: "Good", color: "bg-emerald-50 text-emerald-700 border border-emerald-200" };
    if (rate >= 0.70) return { text: "Fair", color: "bg-amber-50 text-amber-700 border border-amber-200" };
    return { text: "Poor", color: "bg-red-50 text-red-700 border border-red-200" };
  };
  const quality = getQualityLabel(data.detection_rate);

  // Line colors for chart
  const colors = ["#2563eb", "#059669", "#d97706", "#dc2626", "#7c3aed"];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-slate-900">
              Biomechanical Analysis
            </h1>
            <span className={`px-3 py-1 rounded-full text-xs font-black uppercase tracking-wider ${quality.color}`}>
              {quality.text} Tracking
            </span>
          </div>
          <p className="text-xs sm:text-sm font-semibold text-slate-600">
            {video.original_filename} • <span className="capitalize font-bold text-slate-900">{video.movement_type}</span>
          </p>
        </div>

        <div>
          <a
            href={`/api/v1/videos/${id}/biomechanics/export.csv`}
            download
            className="bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white text-xs sm:text-sm font-black px-5 py-3 rounded-xl shadow-lg shadow-blue-600/30 inline-flex items-center gap-2 cursor-pointer transition-all"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            <span>Export CSV</span>
          </a>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {data.summary.map(s => {
          const isQualitative = s.metric_name.includes("valgus");
          return (
            <div 
              key={s.metric_name} 
              className="bg-white rounded-2xl p-5 border-2 border-slate-300 relative group flex flex-col justify-between"
              style={{ boxShadow: "6px 6px 16px rgba(148, 163, 184, 0.38), -6px -6px 16px rgba(255, 255, 255, 0.95)" }}
            >
              <div className="flex justify-between items-start mb-2">
                <h3 className="text-xs font-black uppercase tracking-wider text-slate-600 truncate" title={formatMetricName(s.metric_name)}>
                  {formatMetricName(s.metric_name)}
                </h3>
                <span className="text-[11px] font-bold text-slate-500">
                  {isQualitative ? "Qualitative" : "±6–17°"}
                </span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-black text-slate-900">
                  {s.peak_value !== null ? s.peak_value.toFixed(1) : "--"}°
                </span>
                {s.range_of_motion !== null && (
                  <span className="text-xs font-black text-blue-700 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded-full">
                    RoM {s.range_of_motion.toFixed(1)}°
                  </span>
                )}
              </div>
            </div>
          );
        })}

        {data.limb_symmetry_index !== null && (
          <div 
            className="bg-white rounded-2xl p-5 border-2 border-slate-300 flex flex-col justify-between"
            style={{ boxShadow: "6px 6px 16px rgba(148, 163, 184, 0.38), -6px -6px 16px rgba(255, 255, 255, 0.95)" }}
          >
            <div className="flex justify-between items-start mb-2">
              <h3 className="text-xs font-black uppercase tracking-wider text-slate-600">
                Symmetry Index (LSI)
              </h3>
              <span className="text-[11px] font-bold text-slate-500">Target ≥ 90%</span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-black text-slate-900">
                {data.limb_symmetry_index.toFixed(1)}%
              </span>
            </div>
            <p className="text-[11px] font-bold text-slate-500 mt-2">100% indicates bilateral symmetry</p>
          </div>
        )}
      </div>

      {/* Main Grid: Video Player & Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Kinematic Overlay Video */}
        <div 
          className="bg-white rounded-2xl border-2 border-slate-300 overflow-hidden flex flex-col"
          style={{ boxShadow: "6px 6px 16px rgba(148, 163, 184, 0.38), -6px -6px 16px rgba(255, 255, 255, 0.95)" }}
        >
          <div className="px-6 py-4 border-b-2 border-slate-200 bg-slate-50 flex items-center justify-between">
            <h3 className="text-sm font-black text-slate-900">Kinematic Pose Overlay</h3>
            <span className="text-xs font-black text-slate-500 uppercase tracking-wider">Video Feed</span>
          </div>
          <div className="flex-1 bg-slate-950 aspect-video flex items-center justify-center relative">
            {videoUrl ? (
              <video 
                src={videoUrl} 
                controls 
                loop 
                className="w-full h-full object-contain"
              />
            ) : (
              <div className="text-center text-slate-400 p-6">
                <svg className="w-10 h-10 mx-auto text-slate-600 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                <span className="text-xs font-semibold">Kinematic overlay not generated</span>
              </div>
            )}
          </div>
        </div>

        {/* Joint Angles Chart */}
        <div 
          className="bg-white rounded-2xl border-2 border-slate-300 p-6 flex flex-col"
          style={{ boxShadow: "6px 6px 16px rgba(148, 163, 184, 0.38), -6px -6px 16px rgba(255, 255, 255, 0.95)" }}
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-black text-slate-900">Joint Angles Over Time</h3>
            <span className="text-xs font-black text-slate-500">Kinematics Curve</span>
          </div>
          <div className="h-[340px] w-full flex-1">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 10, right: 15, bottom: 20, left: -10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#cbd5e1" vertical={false} />
                <XAxis 
                  dataKey="time_sec" 
                  stroke="#64748b" 
                  tickFormatter={(val) => `${val.toFixed(1)}s`}
                  tick={{ fill: '#475569', fontSize: 11, fontWeight: 600 }}
                  tickMargin={8}
                />
                <YAxis 
                  stroke="#64748b" 
                  tick={{ fill: '#475569', fontSize: 11, fontWeight: 600 }} 
                  unit="°"
                />
                <RechartsTooltip 
                  contentStyle={{ backgroundColor: '#ffffff', borderColor: '#cbd5e1', borderRadius: '12px', borderWidth: '2px', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                  itemStyle={{ color: '#0f172a', fontSize: '12px', fontWeight: 600 }}
                  labelFormatter={(val) => `Time: ${Number(val).toFixed(2)}s`}
                />
                <Legend wrapperStyle={{ paddingTop: '12px', fontSize: '11px', fontWeight: 700 }} />
                {Array.from(metricsSet).map((metric, i) => {
                  const isQualitative = metric.includes('valgus');
                  return (
                    <Line
                      key={metric}
                      type="monotone"
                      dataKey={metric}
                      name={formatMetricName(metric)}
                      stroke={colors[i % colors.length]}
                      strokeWidth={2.5}
                      dot={false}
                      activeDot={{ r: 5 }}
                      strokeDasharray={isQualitative ? "4 4" : undefined}
                    />
                  );
                })}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Risk Score & Recommendations */}
      {riskScore && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Risk Score Breakdown Card */}
          <div 
            className="bg-white rounded-2xl border-2 border-slate-300 p-6 lg:col-span-1 flex flex-col justify-between"
            style={{ boxShadow: "6px 6px 16px rgba(148, 163, 184, 0.38), -6px -6px 16px rgba(255, 255, 255, 0.95)" }}
          >
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-black text-slate-900">Injury Risk Scoring</h3>
                <span className="text-[10px] uppercase font-black text-slate-500 tracking-wider">Heuristic Model</span>
              </div>

              {riskScore.status === "insufficient_baseline_data" ? (
                <div className="bg-slate-50 border-2 border-slate-300 rounded-xl p-5 text-center text-slate-600 my-4">
                  <p className="font-black text-xs text-slate-800 mb-1">Baseline In Progress</p>
                  <p className="text-xs font-semibold text-slate-600">Need 10 verified samples to score. Have {riskScore.have}.</p>
                </div>
              ) : (
                <div className="space-y-6 my-2">
                  <div className="flex items-baseline justify-between pb-4 border-b-2 border-slate-100">
                    <div>
                      <span className="text-4xl font-black text-slate-900">{riskScore.overall_score}</span>
                      <span className="text-xs text-slate-500 ml-1.5 font-bold">/ 100</span>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-xs font-black uppercase tracking-wider ${
                      riskScore.risk_category === 'low' ? 'bg-emerald-100 text-emerald-800 border border-emerald-300' :
                      riskScore.risk_category === 'moderate' ? 'bg-amber-100 text-amber-800 border border-amber-300' :
                      'bg-red-100 text-red-800 border border-red-300'
                    }`}>
                      {riskScore.risk_category} Risk
                    </span>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <div className="flex justify-between text-xs font-black text-slate-800 mb-1">
                        <span>Movement Anomaly</span>
                        <span className="text-blue-700">{riskScore.score_breakdown?.movement_anomaly.points} pts</span>
                      </div>
                      <div className="text-[11px] font-semibold text-slate-600 mb-1.5">{riskScore.score_breakdown?.movement_anomaly.detail}</div>
                      <div className="w-full bg-slate-100 border border-slate-300 rounded-full h-3 overflow-hidden p-0.5">
                        <div className="bg-blue-600 h-full rounded-full shadow-sm" style={{ width: `${((riskScore.score_breakdown?.movement_anomaly.points || 0) / 70) * 100}%` }}></div>
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between text-xs font-black text-slate-800 mb-1">
                        <span>Asymmetry Flag</span>
                        <span className={riskScore.score_breakdown?.asymmetry_flag.flagged ? "text-amber-700 font-black" : "text-slate-500 font-bold"}>
                          {riskScore.score_breakdown?.asymmetry_flag.flagged ? "Flagged (LSI < 90%)" : "Normal"}
                        </span>
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between text-xs font-black text-slate-800 mb-1">
                        <span>Prior Injury Factor</span>
                        <span className={riskScore.score_breakdown?.prior_injury_flag.flagged ? "text-red-700 font-black" : "text-slate-500 font-bold"}>
                          {riskScore.score_breakdown?.prior_injury_flag.flagged ? "Relevant History Flagged" : "No Prior History"}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className="pt-4 border-t-2 border-slate-100 text-[11px] font-medium text-slate-500 leading-relaxed italic">
              {riskScore.methodology_note || "Scores are based on peer-reviewed biomechanical literature heuristics. Frontal-plane measurements are qualitative estimates."}
            </div>
          </div>

          {/* Recommendations Card */}
          {recommendations && recommendations.length > 0 && (
            <div 
              className="bg-white rounded-2xl border-2 border-slate-300 p-6 lg:col-span-2 flex flex-col justify-between"
              style={{ boxShadow: "6px 6px 16px rgba(148, 163, 184, 0.38), -6px -6px 16px rgba(255, 255, 255, 0.95)" }}
            >
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-black text-slate-900">Corrective Exercise Recommendations</h3>
                  <span className="text-[10px] uppercase font-black text-slate-500 tracking-wider">Clinical Guidance</span>
                </div>

                <div className="space-y-3">
                  {recommendations.sort((a, b) => a.priority - b.priority).map((rec, i) => (
                    <div key={i} className="p-4 rounded-xl bg-slate-50 border-2 border-slate-200 flex items-start gap-3">
                      <span className="w-7 h-7 rounded-xl bg-blue-600 text-white text-xs font-black flex items-center justify-center shrink-0 shadow-sm">
                        {rec.priority}
                      </span>
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <h4 className="text-xs font-black text-slate-900">{rec.title}</h4>
                          <span className="text-[10px] font-black text-blue-800 bg-blue-100 px-2 py-0.5 rounded border border-blue-200 uppercase">
                            {rec.category.replace('_', ' ')}
                          </span>
                        </div>
                        <p className="text-xs font-medium text-slate-700 leading-relaxed">{rec.description}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="pt-4 border-t-2 border-slate-100 text-[11px] font-semibold text-slate-500 mt-4">
                Recommendations must be supervised and adjusted by a qualified physiotherapist or certified coach.
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
