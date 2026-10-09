import React, { useState, useEffect } from 'react';
import { Users, ShieldAlert, Award, Activity, Heart, CheckCircle2, AlertTriangle, ArrowUpRight, TrendingUp, Sparkles, Filter } from 'lucide-react';
import { api } from '../api/client';

export default function RoleDashboards({ activeRole, injuryRisk, athlete }) {
  const [coachData, setCoachData] = useState(null);
  const [physioData, setPhysioData] = useState(null);
  const [scientistData, setScientistData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadDashboards() {
      setLoading(true);
      try {
        const [c, p, s] = await Promise.all([
          api.getCoachDashboard(),
          api.getPhysioDashboard(),
          api.getScientistDashboard()
        ]);
        setCoachData(c);
        setPhysioData(p);
        setScientistData(s);
      } catch (err) {
        console.error('Failed to load dashboard data:', err);
      } finally {
        setLoading(false);
      }
    }
    loadDashboards();
  }, []);

  if (loading) {
    return (
      <div className="p-12 text-center text-xs text-slate-400">
        <Activity className="w-8 h-8 mx-auto animate-spin text-cyan-400 mb-2" />
        Loading intelligence dashboard aggregations...
      </div>
    );
  }

  // 1. COACH DASHBOARD
  if (activeRole === 'coach') {
    const summary = coachData?.summary || {};
    const roster = coachData?.roster || [];
    const alerts = coachData?.coach_action_alerts || [];

    return (
      <div className="space-y-6">
        <div className="bg-slate-900/60 p-4 rounded-2xl border border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Users className="w-5 h-5 text-amber-400" />
              Coach Team Intelligence & Squad Readiness
            </h2>
            <p className="text-xs text-slate-400">
              Squad-level injury risk monitoring, availability forecast, and workload modifications.
            </p>
          </div>
          <span className="px-3 py-1 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20 text-xs font-bold font-mono">
            Squad Availability: {summary.squad_availability_pct}%
          </span>
        </div>

        {/* Coach Summary Stat Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-slate-900/70 p-4 rounded-2xl border border-slate-800">
            <p className="text-xs text-slate-400">Total Squad Roster</p>
            <p className="text-2xl font-black text-white font-mono mt-1">{summary.total_squad_size} Athletes</p>
          </div>
          <div className="bg-slate-900/70 p-4 rounded-2xl border border-slate-800">
            <p className="text-xs text-slate-400">High Risk Alerts</p>
            <p className="text-2xl font-black text-rose-400 font-mono mt-1">{summary.high_risk_athletes}</p>
          </div>
          <div className="bg-slate-900/70 p-4 rounded-2xl border border-slate-800">
            <p className="text-xs text-slate-400">Moderate Watchlist</p>
            <p className="text-2xl font-black text-amber-400 font-mono mt-1">{summary.moderate_risk_athletes}</p>
          </div>
          <div className="bg-slate-900/70 p-4 rounded-2xl border border-slate-800">
            <p className="text-xs text-slate-400">Avg Movement Quality</p>
            <p className="text-2xl font-black text-cyan-400 font-mono mt-1">{summary.average_squad_movement_quality} / 100</p>
          </div>
        </div>

        {/* Coach Urgent Action Alerts */}
        {alerts.length > 0 && (
          <div className="bg-rose-950/20 border border-rose-800/40 p-4 rounded-2xl space-y-3">
            <h3 className="text-xs font-bold text-rose-300 uppercase tracking-wider flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-400" /> Urgent Coach Action Required
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {alerts.map((al, idx) => (
                <div key={idx} className="p-3 rounded-xl bg-slate-950/80 border border-rose-900/40 space-y-1">
                  <p className="text-xs font-bold text-white">{al.title}</p>
                  <p className="text-[11px] text-slate-400">{al.message}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Squad Roster Table */}
        <div className="bg-slate-900/70 rounded-2xl border border-slate-800 overflow-hidden shadow-xl">
          <div className="p-4 border-b border-slate-800 flex justify-between items-center">
            <h3 className="text-sm font-bold text-white">Full Team Biomechanical Readiness Roster</h3>
            <span className="text-xs text-slate-400">Ranked by Injury Risk Exposure</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/70 text-slate-400 border-b border-slate-800 font-mono text-[11px]">
                <tr>
                  <th className="p-3">Athlete</th>
                  <th className="p-3">Sport / Position</th>
                  <th className="p-3">ACWR</th>
                  <th className="p-3">Weekly Load</th>
                  <th className="p-3">Risk Score</th>
                  <th className="p-3">Category</th>
                  <th className="p-3">Movement Quality</th>
                  <th className="p-3">Readiness Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300 font-sans">
                {roster.map((ath) => (
                  <tr key={ath.id} className="hover:bg-slate-850/50 transition-colors">
                    <td className="p-3 font-semibold text-white">
                      <div>{ath.name}</div>
                      <div className="text-[10px] text-slate-500 font-mono">{ath.athlete_code}</div>
                    </td>
                    <td className="p-3">{ath.sport_type} • {ath.position}</td>
                    <td className="p-3 font-mono">
                      <span className={ath.acwr > 1.4 ? 'text-rose-400 font-bold' : 'text-slate-300'}>
                        {ath.acwr}
                      </span>
                    </td>
                    <td className="p-3 font-mono">{ath.training_load} hrs/wk</td>
                    <td className="p-3 font-mono font-bold text-white">{ath.risk_score}</td>
                    <td className="p-3">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                        ath.risk_category.includes('High') || ath.risk_category.includes('Critical')
                          ? 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                          : ath.risk_category.includes('Moderate')
                          ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                          : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                      }`}>
                        {ath.risk_category}
                      </span>
                    </td>
                    <td className="p-3 font-mono text-cyan-400">{ath.movement_quality}</td>
                    <td className="p-3">
                      <span className={`text-[11px] font-semibold ${
                        ath.readiness_status === 'Restricted Load' ? 'text-rose-400' : 'text-emerald-400'
                      }`}>
                        {ath.readiness_status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  }

  // 2. PHYSIOTHERAPIST DASHBOARD
  if (activeRole === 'physiotherapist') {
    const rehab = physioData?.rehab_registry || [];
    const focusAreas = physioData?.clinical_focus_areas || [];

    return (
      <div className="space-y-6">
        <div className="bg-slate-900/60 p-4 rounded-2xl border border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-cyan-400" />
              Physiotherapist Rehabilitation & Clinical Tracking
            </h2>
            <p className="text-xs text-slate-400">
              Joint range of motion, dynamic valgus tracking, and tailored rehabilitation progressions.
            </p>
          </div>
        </div>

        {/* Clinical Focus Areas */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {focusAreas.map((f, i) => (
            <div key={i} className="bg-slate-900/70 p-4 rounded-2xl border border-slate-800 space-y-2">
              <span className="text-xs font-semibold text-slate-400">{f.area}</span>
              <div className="flex items-baseline justify-between">
                <span className="text-2xl font-black text-rose-400 font-mono">{f.flagged_cases} Flagged</span>
                <span className="text-xs text-slate-500 font-mono">Norm: {f.target_norm}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Rehab Registry */}
        <div className="space-y-4">
          <h3 className="text-sm font-bold text-white">Athlete Rehabilitation Profiles</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {rehab.map((r) => (
              <div key={r.id} className="bg-slate-900/70 p-5 rounded-2xl border border-slate-800 space-y-3">
                <div className="flex items-start justify-between">
                  <div>
                    <h4 className="text-sm font-bold text-white">{r.name}</h4>
                    <p className="text-xs text-slate-400">{r.sport_type} • {r.athlete_code}</p>
                  </div>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                    r.risk_score > 60 ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                  }`}>
                    {r.risk_category} ({r.risk_score})
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-2 text-center text-xs">
                  <div className="p-2 rounded-xl bg-slate-950 border border-slate-800/80">
                    <span className="text-[10px] text-slate-400 block">Peak Valgus</span>
                    <span className="font-bold text-white font-mono">{r.knee_valgus_max}°</span>
                  </div>
                  <div className="p-2 rounded-xl bg-slate-950 border border-slate-800/80">
                    <span className="text-[10px] text-slate-400 block">Symmetry</span>
                    <span className="font-bold text-cyan-400 font-mono">{r.movement_symmetry}%</span>
                  </div>
                  <div className="p-2 rounded-xl bg-slate-950 border border-slate-800/80">
                    <span className="text-[10px] text-slate-400 block">Pelvic Drop</span>
                    <span className="font-bold text-white font-mono">{r.pelvic_drop}°</span>
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-800 text-[11px] text-slate-400">
                  <span className="font-semibold text-slate-300 block mb-1">Injury Background:</span>
                  {(r.injury_history || []).length > 0 ? (
                    r.injury_history.map((h, hIdx) => (
                      <span key={hIdx} className="inline-block bg-slate-950 px-2 py-0.5 rounded border border-slate-800 mr-1.5 mb-1 text-[10px]">
                        {h.injury_name} ({h.severity}, {h.status})
                      </span>
                    ))
                  ) : (
                    <span>No prior major structural surgeries recorded.</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // 3. SPORTS SCIENTIST DASHBOARD
  if (activeRole === 'sports_scientist') {
    const sci = scientistData?.scientific_overview || {};
    const dist = scientistData?.biomechanical_distributions || [];
    const insights = scientistData?.research_insights || [];

    return (
      <div className="space-y-6">
        <div className="bg-slate-900/60 p-4 rounded-2xl border border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Activity className="w-5 h-5 text-purple-400" />
              Sports Science Research & Biomechanical Analytics
            </h2>
            <p className="text-xs text-slate-400">
              Kinematic population distributions compared against SportsPose & Human3.6M normative standards.
            </p>
          </div>
        </div>

        {/* Scientific Key Indicators */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-slate-900/70 p-4 rounded-2xl border border-slate-800">
            <p className="text-xs text-slate-400">Population Valgus Mean</p>
            <p className="text-2xl font-black text-white font-mono mt-1">{sci.mean_dynamic_valgus_deg}°</p>
          </div>
          <div className="bg-slate-900/70 p-4 rounded-2xl border border-slate-800">
            <p className="text-xs text-slate-400">Bilateral Symmetry Mean</p>
            <p className="text-2xl font-black text-purple-400 font-mono mt-1">{sci.mean_bilateral_symmetry_pct}%</p>
          </div>
          <div className="bg-slate-900/70 p-4 rounded-2xl border border-slate-800">
            <p className="text-xs text-slate-400">Mean Deceleration Force</p>
            <p className="text-2xl font-black text-cyan-400 font-mono mt-1">{sci.mean_ground_reaction_force_g} G</p>
          </div>
          <div className="bg-slate-900/70 p-4 rounded-2xl border border-slate-800">
            <p className="text-xs text-slate-400">Video Datasets Analyzed</p>
            <p className="text-2xl font-black text-emerald-400 font-mono mt-1">{sci.total_analyses_completed}</p>
          </div>
        </div>

        {/* Biomechanical Benchmark Distribution Comparison */}
        <div className="bg-slate-900/70 p-5 rounded-2xl border border-slate-800 space-y-4">
          <h3 className="text-sm font-bold text-white">Cohort Kinematics vs SportsPose Gold-Standard Benchmark</h3>
          <div className="space-y-3">
            {dist.map((d, i) => (
              <div key={i} className="p-3 rounded-xl bg-slate-950/70 border border-slate-800 space-y-1.5">
                <div className="flex justify-between text-xs">
                  <span className="font-semibold text-slate-200">{d.metric}</span>
                  <span className="text-slate-400 font-mono">
                    Cohort: <strong className="text-white">{d.population_mean}{d.unit}</strong> | Benchmark: <strong className="text-cyan-400">{d.benchmark_sports_pose}{d.unit}</strong>
                  </span>
                </div>
                <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden flex">
                  <div
                    className="h-full bg-purple-500 rounded-full"
                    style={{ width: `${Math.min(100, (d.population_mean / (d.benchmark_sports_pose * 1.5)) * 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Research Insights */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {insights.map((ins, idx) => (
            <div key={idx} className="bg-slate-900/70 p-4 rounded-2xl border border-slate-800 space-y-2">
              <h4 className="text-xs font-bold text-cyan-300 uppercase tracking-wider">{ins.title}</h4>
              <p className="text-xs text-slate-300 leading-relaxed">{ins.finding}</p>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // 4. ATHLETE DASHBOARD (DEFAULT)
  const userScore = injuryRisk?.overall_injury_risk_score || 76.8;
  const userCat = injuryRisk?.risk_category || 'High Risk';
  const exList = injuryRisk?.corrective_recommendations?.exercises || [];

  return (
    <div className="space-y-6">
      <div className="bg-slate-900/60 p-4 rounded-2xl border border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Award className="w-5 h-5 text-emerald-400" />
            Athlete Personal Readiness & Injury Prevention Dashboard
          </h2>
          <p className="text-xs text-slate-400">
            Personal performance metrics for <strong className="text-white">Marcus Vance (ATH-101)</strong>
          </p>
        </div>
        <span className="px-3 py-1 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-bold font-mono">
          Status: Active Recovery Protocol
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Risk Card */}
        <div className="bg-slate-900/70 p-6 rounded-2xl border border-slate-800 space-y-4 text-center">
          <p className="text-xs font-bold uppercase tracking-wider text-slate-400">My Injury Risk Exposure</p>
          <div className="text-4xl font-black text-white font-mono">{userScore.toFixed(1)} / 100</div>
          <div>
            <span className="px-3 py-1 rounded-full text-xs font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20">
              {userCat}
            </span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Your dynamic knee valgus angle during drop jump was flagged at 18.9°. Please complete your corrective exercises below.
          </p>
        </div>

        {/* Daily Exercise Checklist */}
        <div className="lg:col-span-2 bg-slate-900/70 p-6 rounded-2xl border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-cyan-400" />
              Today's Prescribed Prevention Protocol
            </h3>
            <span className="text-xs text-slate-400 font-mono">3 Exercises Prescribed</span>
          </div>

          <div className="space-y-2.5">
            {exList.map((ex, i) => (
              <div key={i} className="p-3 rounded-xl bg-slate-950/70 border border-slate-800 flex items-center justify-between">
                <div className="space-y-0.5">
                  <p className="text-xs font-bold text-white">{ex.name}</p>
                  <p className="text-[11px] text-slate-400">{ex.sets} • {ex.reps} • Target: {ex.target_area}</p>
                </div>
                <input type="checkbox" className="w-4 h-4 rounded text-cyan-500 bg-slate-900 border-slate-700 cursor-pointer" />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
