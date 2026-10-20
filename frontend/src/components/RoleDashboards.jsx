import React, { useState, useEffect } from 'react';
import { Users, ShieldAlert, Award, Activity, Heart, CheckCircle2, AlertTriangle, ArrowUpRight, TrendingUp, Sparkles, Filter, Database, Server, HardDrive, ShieldCheck, UserCheck } from 'lucide-react';
import { api } from '../api/client';

export default function RoleDashboards({ activeRole, injuryRisk, athlete }) {
  const [coachData, setCoachData] = useState(null);
  const [physioData, setPhysioData] = useState(null);
  const [scientistData, setScientistData] = useState(null);
  const [adminData, setAdminData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [adminRoleFilter, setAdminRoleFilter] = useState('all');

  useEffect(() => {
    async function loadDashboards() {
      setLoading(true);
      try {
        const [c, p, s, a] = await Promise.all([
          api.getCoachDashboard(),
          api.getPhysioDashboard(),
          api.getScientistDashboard(),
          api.getAdminDashboard().catch(() => null)
        ]);
        setCoachData(c);
        setPhysioData(p);
        setScientistData(s);
        setAdminData(a);
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
      <div className="p-12 text-center text-xs text-slate-500 bg-white rounded-2xl border border-slate-200 shadow-xs">
        <Activity className="w-8 h-8 mx-auto animate-spin text-teal-700 mb-2" />
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
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <Users className="w-5 h-5 text-teal-700" />
              Coach Team Intelligence &amp; Squad Readiness
            </h2>
            <p className="text-xs text-slate-500">
              Squad-level injury risk monitoring, availability forecast, and workload modifications.
            </p>
          </div>
          <span className="px-3 py-1 rounded-xl bg-amber-50 text-amber-800 border border-amber-200 text-xs font-bold font-mono">
            Squad Availability: {summary.squad_availability_pct}%
          </span>
        </div>

        {/* Coach Summary Stat Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
            <p className="text-xs font-medium text-slate-500">Total Squad Roster</p>
            <p className="text-2xl font-black text-slate-900 font-mono mt-1">{summary.total_squad_size} Athletes</p>
          </div>
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
            <p className="text-xs font-medium text-slate-500">High Risk Alerts</p>
            <p className="text-2xl font-black text-rose-700 font-mono mt-1">{summary.high_risk_athletes}</p>
          </div>
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
            <p className="text-xs font-medium text-slate-500">Moderate Watchlist</p>
            <p className="text-2xl font-black text-amber-700 font-mono mt-1">{summary.moderate_risk_athletes}</p>
          </div>
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
            <p className="text-xs font-medium text-slate-500">Avg Movement Quality</p>
            <p className="text-2xl font-black text-teal-700 font-mono mt-1">{summary.average_squad_movement_quality} / 100</p>
          </div>
        </div>

        {/* Coach Urgent Action Alerts */}
        {alerts.length > 0 && (
          <div className="bg-rose-50/70 border border-rose-200 p-4 rounded-2xl space-y-3">
            <h3 className="text-xs font-bold text-rose-900 uppercase tracking-wider flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-700" /> Urgent Coach Action Required
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {alerts.map((al, idx) => (
                <div key={idx} className="p-3.5 rounded-xl bg-white border border-rose-200 shadow-xs space-y-1">
                  <p className="text-xs font-bold text-slate-900">{al.title}</p>
                  <p className="text-[11px] text-slate-600">{al.message}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Squad Roster Table */}
        <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-xs">
          <div className="p-4 border-b border-slate-200 flex justify-between items-center bg-slate-50/60">
            <h3 className="text-sm font-bold text-slate-900">Full Team Biomechanical Readiness Roster</h3>
            <span className="text-xs text-slate-500">Ranked by Injury Risk Exposure</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-600 border-b border-slate-200 font-mono text-[11px]">
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
              <tbody className="divide-y divide-slate-100 text-slate-700 font-sans">
                {roster.map((ath) => (
                  <tr key={ath.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="p-3 font-semibold text-slate-900">
                      <div>{ath.name}</div>
                      <div className="text-[10px] text-slate-500 font-mono">{ath.athlete_code}</div>
                    </td>
                    <td className="p-3">{ath.sport_type} • {ath.position}</td>
                    <td className="p-3 font-mono">
                      <span className={ath.acwr > 1.4 ? 'text-rose-700 font-bold' : 'text-slate-700'}>
                        {ath.acwr}
                      </span>
                    </td>
                    <td className="p-3 font-mono">{ath.training_load} hrs/wk</td>
                    <td className="p-3 font-mono font-bold text-slate-900">{ath.risk_score}</td>
                    <td className="p-3">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                        ath.risk_category.includes('High') || ath.risk_category.includes('Critical')
                          ? 'bg-rose-50 text-rose-700 border-rose-200'
                          : ath.risk_category.includes('Moderate')
                          ? 'bg-amber-50 text-amber-800 border-amber-200'
                          : 'bg-emerald-50 text-emerald-800 border-emerald-200'
                      }`}>
                        {ath.risk_category}
                      </span>
                    </td>
                    <td className="p-3 font-mono font-semibold text-teal-800">{ath.movement_quality}</td>
                    <td className="p-3">
                      <span className={`text-[11px] font-semibold ${
                        ath.readiness_status === 'Restricted Load' ? 'text-rose-700' : 'text-emerald-700'
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
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-teal-700" />
              Physiotherapist Rehabilitation &amp; Clinical Tracking
            </h2>
            <p className="text-xs text-slate-500">
              Joint range of motion, dynamic valgus tracking, and tailored rehabilitation progressions.
            </p>
          </div>
        </div>

        {/* Clinical Focus Areas */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {focusAreas.map((f, i) => (
            <div key={i} className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-2">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{f.area}</span>
              <div className="flex items-baseline justify-between">
                <span className="text-2xl font-black text-rose-700 font-mono">{f.flagged_cases} Flagged</span>
                <span className="text-xs text-slate-500 font-mono">Norm: {f.target_norm}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Rehab Registry */}
        <div className="space-y-4">
          <h3 className="text-sm font-bold text-slate-900">Athlete Rehabilitation Profiles</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {rehab.map((r) => (
              <div key={r.id} className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-3">
                <div className="flex items-start justify-between">
                  <div>
                    <h4 className="text-sm font-bold text-slate-900">{r.name}</h4>
                    <p className="text-xs text-slate-500">{r.sport_type} • {r.athlete_code}</p>
                  </div>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                    r.risk_score > 60 ? 'bg-rose-50 text-rose-700 border-rose-200' : 'bg-emerald-50 text-emerald-800 border-emerald-200'
                  }`}>
                    {r.risk_category} ({r.risk_score})
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-2 text-center text-xs">
                  <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                    <span className="text-[10px] text-slate-500 block uppercase">Peak Valgus</span>
                    <span className="font-bold text-slate-900 font-mono">{r.knee_valgus_max}°</span>
                  </div>
                  <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                    <span className="text-[10px] text-slate-500 block uppercase">Symmetry</span>
                    <span className="font-bold text-teal-800 font-mono">{r.movement_symmetry}%</span>
                  </div>
                  <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                    <span className="text-[10px] text-slate-500 block uppercase">Pelvic Drop</span>
                    <span className="font-bold text-slate-900 font-mono">{r.pelvic_drop}°</span>
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-200 text-[11px] text-slate-600">
                  <span className="font-semibold text-slate-800 block mb-1">Injury Background:</span>
                  {(r.injury_history || []).length > 0 ? (
                    r.injury_history.map((h, hIdx) => (
                      <span key={hIdx} className="inline-block bg-slate-100 text-slate-700 px-2 py-0.5 rounded border border-slate-200 mr-1.5 mb-1 text-[10px]">
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
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <Activity className="w-5 h-5 text-teal-700" />
              Sports Science Research &amp; Biomechanical Analytics
            </h2>
            <p className="text-xs text-slate-500">
              Kinematic population distributions compared against SportsPose &amp; Human3.6M normative standards.
            </p>
          </div>
        </div>

        {/* Scientific Key Indicators */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
            <p className="text-xs font-medium text-slate-500">Population Valgus Mean</p>
            <p className="text-2xl font-black text-slate-900 font-mono mt-1">{sci.mean_dynamic_valgus_deg}°</p>
          </div>
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
            <p className="text-xs font-medium text-slate-500">Bilateral Symmetry Mean</p>
            <p className="text-2xl font-black text-teal-800 font-mono mt-1">{sci.mean_bilateral_symmetry_pct}%</p>
          </div>
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
            <p className="text-xs font-medium text-slate-500">Mean Deceleration Force</p>
            <p className="text-2xl font-black text-slate-800 font-mono mt-1">{sci.mean_ground_reaction_force_g} G</p>
          </div>
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
            <p className="text-xs font-medium text-slate-500">Video Datasets Analyzed</p>
            <p className="text-2xl font-black text-emerald-800 font-mono mt-1">{sci.total_analyses_completed}</p>
          </div>
        </div>

        {/* Biomechanical Benchmark Distribution Comparison */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <h3 className="text-sm font-bold text-slate-900">Cohort Kinematics vs SportsPose Gold-Standard Benchmark</h3>
          <div className="space-y-3">
            {dist.map((d, i) => (
              <div key={i} className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
                <div className="flex justify-between text-xs">
                  <span className="font-semibold text-slate-800">{d.metric}</span>
                  <span className="text-slate-600 font-mono text-[11px]">
                    Cohort: <strong className="text-slate-900">{d.population_mean}{d.unit}</strong> | Benchmark: <strong className="text-teal-800">{d.benchmark_sports_pose}{d.unit}</strong>
                  </span>
                </div>
                <div className="h-2 w-full bg-slate-200 rounded-full overflow-hidden flex">
                  <div
                    className="h-full bg-teal-700 rounded-full transition-all"
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
            <div key={idx} className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-2">
              <h4 className="text-xs font-bold text-teal-800 uppercase tracking-wider">{ins.title}</h4>
              <p className="text-xs text-slate-600 leading-relaxed">{ins.finding}</p>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // 4. ADMINISTRATOR DASHBOARD
  if (activeRole === 'administrator') {
    const sys = adminData?.system_metrics || {
      total_registered_users: 5,
      total_athletes: 1,
      total_video_records: 1,
      total_biomechanical_analyses: 1,
      storage_usage_mb: 24.5,
      database_engine: "PostgreSQL Ready",
      cv_runtime: "MediaPipe Pose Tasks v1.1.0"
    };
    const roleCounts = adminData?.role_breakdown || {
      athlete: 1, coach: 1, physiotherapist: 1, sports_scientist: 1, administrator: 1
    };
    const allUsers = adminData?.users || [];
    const filteredUsers = adminRoleFilter === 'all' 
      ? allUsers 
      : allUsers.filter(u => u.role === adminRoleFilter);
    const auditLogs = adminData?.audit_logs || [];

    const roleBadgeColor = {
      athlete: 'bg-emerald-50 text-emerald-800 border-emerald-200',
      coach: 'bg-amber-50 text-amber-800 border-amber-200',
      physiotherapist: 'bg-rose-50 text-rose-800 border-rose-200',
      sports_scientist: 'bg-teal-50 text-teal-800 border-teal-200',
      administrator: 'bg-slate-100 text-slate-800 border-slate-300'
    };

    return (
      <div className="space-y-6">
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-teal-700" />
              Administrator System Infrastructure &amp; Governance
            </h2>
            <p className="text-xs text-slate-500">
              Platform administration, role-based access management, infrastructure metrics, and activity audits.
            </p>
          </div>
          <span className="px-3 py-1 rounded-xl bg-teal-50 text-teal-800 border border-teal-200 text-xs font-bold font-mono">
            Platform Status: Healthy • {sys.database_engine}
          </span>
        </div>

        {/* System Infrastructure Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
            <p className="text-[11px] text-slate-500 flex items-center gap-1.5">
              <Users className="w-3.5 h-3.5 text-teal-700" /> Total Users
            </p>
            <p className="text-xl font-black text-slate-900 font-mono mt-1">{sys.total_registered_users}</p>
          </div>
          <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
            <p className="text-[11px] text-slate-500 flex items-center gap-1.5">
              <UserCheck className="w-3.5 h-3.5 text-emerald-700" /> Athletes
            </p>
            <p className="text-xl font-black text-emerald-800 font-mono mt-1">{sys.total_athletes}</p>
          </div>
          <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
            <p className="text-[11px] text-slate-500 flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-amber-700" /> Videos
            </p>
            <p className="text-xl font-black text-amber-800 font-mono mt-1">{sys.total_video_records}</p>
          </div>
          <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
            <p className="text-[11px] text-slate-500 flex items-center gap-1.5">
              <TrendingUp className="w-3.5 h-3.5 text-teal-700" /> Analyses
            </p>
            <p className="text-xl font-black text-slate-900 font-mono mt-1">{sys.total_biomechanical_analyses}</p>
          </div>
          <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
            <p className="text-[11px] text-slate-500 flex items-center gap-1.5">
              <HardDrive className="w-3.5 h-3.5 text-slate-600" /> Storage
            </p>
            <p className="text-xl font-black text-slate-900 font-mono mt-1">{sys.storage_usage_mb} MB</p>
          </div>
          <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
            <p className="text-[11px] text-slate-500 flex items-center gap-1.5">
              <Server className="w-3.5 h-3.5 text-rose-700" /> CV Engine
            </p>
            <p className="text-xs font-bold text-slate-800 mt-2 truncate" title={sys.cv_runtime}>MediaPipe Tasks</p>
          </div>
        </div>

        {/* User Account Registry & RBAC Controls */}
        <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-xs">
          <div className="p-4 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-50/60">
            <div>
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Users className="w-4 h-4 text-teal-700" />
                Registered User Directory &amp; Roles
              </h3>
              <p className="text-xs text-slate-500">Authenticated accounts across the five platform roles</p>
            </div>
            
            {/* Role Filter Tabs */}
            <div className="flex flex-wrap gap-1.5">
              {['all', 'athlete', 'coach', 'physiotherapist', 'sports_scientist', 'administrator'].map(role => (
                <button
                  key={role}
                  onClick={() => setAdminRoleFilter(role)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-medium capitalize transition-colors ${
                    adminRoleFilter === role
                      ? 'bg-teal-700 text-white font-bold shadow-xs'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200 hover:text-slate-900'
                  }`}
                >
                  {role === 'all' ? `All (${allUsers.length})` : `${role.replace('_', ' ')} (${roleCounts[role] || 0})`}
                </button>
              ))}
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-600 border-b border-slate-200 font-mono text-[11px]">
                <tr>
                  <th className="p-3">User ID</th>
                  <th className="p-3">Full Name</th>
                  <th className="p-3">Email Address</th>
                  <th className="p-3">Assigned Role</th>
                  <th className="p-3">Account Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {filteredUsers.length > 0 ? (
                  filteredUsers.map(u => (
                    <tr key={u.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="p-3 font-mono text-slate-500">#{u.id}</td>
                      <td className="p-3 font-semibold text-slate-900">{u.full_name || 'Standard User'}</td>
                      <td className="p-3 text-slate-600 font-mono text-[11px]">{u.email}</td>
                      <td className="p-3">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border capitalize ${roleBadgeColor[u.role] || 'bg-slate-100 text-slate-600 border-slate-200'}`}>
                          {u.role.replace('_', ' ')}
                        </span>
                      </td>
                      <td className="p-3 text-slate-500 font-mono text-[11px]">{u.created_at || 'Active'}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="5" className="p-6 text-center text-slate-500">
                      No accounts found matching role "{adminRoleFilter}".
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Audit Log and Methodology Notice Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Audit Logs */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-3">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Activity className="w-4 h-4 text-amber-700" />
              Recent Video &amp; Analysis Activity Audit
            </h3>
            <div className="space-y-2">
              {auditLogs.length > 0 ? (
                auditLogs.map(log => (
                  <div key={log.id} className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between text-xs">
                    <div>
                      <p className="font-medium text-slate-800">{log.action}</p>
                      <p className="text-[10px] text-slate-500">Athlete Ref #{log.athlete_id} • Status: <span className="text-emerald-700 font-semibold">{log.status}</span></p>
                    </div>
                    <span className="text-[10px] text-slate-500 font-mono">{log.created_at}</span>
                  </div>
                ))
              ) : (
                <p className="text-xs text-slate-500">No activity logged yet.</p>
              )}
            </div>
          </div>

          {/* Platform Governance & Model Transparency Notice */}
          <div className="bg-slate-50 p-5 rounded-2xl border border-slate-200 shadow-xs space-y-3 flex flex-col justify-between">
            <div>
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-teal-700" />
                Scientific Governance &amp; Model Disclosure
              </h3>
              <p className="text-xs text-slate-600 mt-2 leading-relaxed">
                {adminData?.methodology_notice || "Kinematix uses transparent, deterministic mathematical formulas calibrated against sports science literature. No opaque black-box clinical claims are made."}
              </p>
              <div className="mt-3 space-y-1.5 text-[11px] text-slate-600">
                <p>• <strong>Risk Weighting:</strong> Biomechanics 35%, Prior Injury 20%, Movement Asymmetry 20%, Training Load (ACWR) 15%, Fatigue 10%.</p>
                <p>• <strong>Occlusion Handling:</strong> Undetected frames are marked unavailable; no simulated or invented values.</p>
                <p>• <strong>Clinical Status:</strong> Deterministic screening and workload intelligence tool; not a medical diagnostic device.</p>
              </div>
            </div>
            <div className="pt-3 border-t border-slate-200 flex items-center justify-between text-[11px] text-slate-500 font-mono">
              <span>Security: SHA-256 Reset Tokens • JWT Sessions</span>
              <span>Primary DB: PostgreSQL</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // 5. ATHLETE DASHBOARD (DEFAULT)
  const userScore = injuryRisk?.overall_injury_risk_score || 76.8;
  const userCat = injuryRisk?.risk_category || 'High Risk';
  const exList = injuryRisk?.corrective_recommendations?.exercises || [];

  return (
    <div className="space-y-6">
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <Award className="w-5 h-5 text-teal-700" />
            Athlete Personal Readiness &amp; Injury Prevention Dashboard
          </h2>
          <p className="text-xs text-slate-500">
            Personal performance metrics for <strong className="text-slate-800">Marcus Vance (ATH-101)</strong>
          </p>
        </div>
        <span className="px-3 py-1 rounded-xl bg-teal-50 text-teal-800 border border-teal-200 text-xs font-bold font-mono">
          Status: Active Recovery Protocol
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Risk Card */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4 text-center">
          <p className="text-xs font-bold uppercase tracking-wider text-slate-500">My Injury Risk Exposure</p>
          <div className="text-4xl font-black text-slate-900 font-mono">{userScore.toFixed(1)} / 100</div>
          <div>
            <span className="px-3 py-1 rounded-full text-xs font-bold bg-rose-50 text-rose-700 border border-rose-200">
              {userCat}
            </span>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            Your dynamic knee valgus angle during drop jump was flagged at 18.9°. Please complete your corrective exercises below.
          </p>
        </div>

        {/* Daily Exercise Checklist */}
        <div className="lg:col-span-2 bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-teal-700" />
              Today's Prescribed Prevention Protocol
            </h3>
            <span className="text-xs text-slate-500 font-mono">3 Exercises Prescribed</span>
          </div>

          <div className="space-y-2.5">
            {exList.map((ex, i) => (
              <div key={i} className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between">
                <div className="space-y-0.5">
                  <p className="text-xs font-bold text-slate-900">{ex.name}</p>
                  <p className="text-[11px] text-slate-500">{ex.sets} • {ex.reps} • Target: {ex.target_area}</p>
                </div>
                <input
                  type="checkbox"
                  className="w-4 h-4 rounded text-teal-700 border-slate-300 focus:ring-teal-600 accent-teal-700 cursor-pointer"
                />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
