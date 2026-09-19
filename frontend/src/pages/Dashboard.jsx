import React from 'react';
import { Link } from 'react-router-dom';
import { 
  ShieldAlert, 
  AlertTriangle, 
  CheckCircle2, 
  TrendingUp, 
  Video, 
  ArrowRight,
  UserCheck
} from 'lucide-react';

export default function Dashboard() {
  const kpis = [
    { title: 'Screened Athletes', value: '42', change: '+12% this month', icon: UserCheck, color: 'text-cyan-400' },
    { title: 'High-Risk Alerts', value: '3', change: 'Immediate attention', icon: ShieldAlert, color: 'text-rose-400' },
    { title: 'Moderate Risk Flags', value: '8', change: 'Corrective drills set', icon: AlertTriangle, color: 'text-amber-400' },
    { title: 'Clear / Low Risk', value: '31', change: '74% roster readiness', icon: CheckCircle2, color: 'text-emerald-400' },
  ];

  const recentTrials = [
    {
      id: 'v-101',
      athlete: 'Marcus Sterling',
      sport: 'Basketball (Guard)',
      movement: 'Jump Landing',
      date: 'Today, 14:20',
      valgusAngle: '16.4°',
      riskTier: 'HIGH',
      riskScore: 84,
      targetRisk: 'ACL Tear Risk',
    },
    {
      id: 'v-102',
      athlete: 'Elena Rostova',
      sport: 'Soccer (Winger)',
      movement: 'Running Gait',
      date: 'Today, 11:45',
      valgusAngle: '7.2°',
      riskTier: 'MODERATE',
      riskScore: 56,
      targetRisk: 'Hamstring Strain Risk',
    },
    {
      id: 'v-103',
      athlete: 'Devon Vance',
      sport: 'Track & Field',
      movement: 'Squat Assessment',
      date: 'Yesterday',
      valgusAngle: '4.1°',
      riskTier: 'LOW',
      riskScore: 18,
      targetRisk: 'Symmetrical / Normal',
    },
  ];

  return (
    <div className="space-y-8">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 p-6 rounded-2xl border border-slate-800 shadow-xl">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Biomechanical Risk Overview
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Real-time computer vision kinematics and injury risk surveillance.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            to="/upload"
            className="inline-flex items-center px-4 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-semibold text-sm transition-all shadow-lg shadow-emerald-500/20 hover:scale-[1.02]"
          >
            <Video className="w-4 h-4 mr-2" />
            Upload New Video
          </Link>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {kpis.map((kpi, index) => {
          const Icon = kpi.icon;
          return (
            <div key={index} className="glass-card p-5 rounded-2xl relative overflow-hidden">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-400 tracking-wider uppercase">
                  {kpi.title}
                </span>
                <Icon className={`w-5 h-5 ${kpi.color}`} />
              </div>
              <div className="mt-4 flex items-baseline justify-between">
                <span className="text-3xl font-extrabold text-white">{kpi.value}</span>
                <span className="text-xs text-slate-400 font-medium">{kpi.change}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Recent Movement Screenings Section */}
      <div className="glass-card rounded-2xl p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-lg font-bold text-white">Recent Movement Screenings</h2>
            <p className="text-xs text-slate-400">Automated video analysis and metric extractions</p>
          </div>
          <Link
            to="/athletes"
            className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 flex items-center gap-1"
          >
            View All Athletes <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 text-xs uppercase tracking-wider">
                <th className="pb-3 font-semibold">Athlete</th>
                <th className="pb-3 font-semibold">Movement Type</th>
                <th className="pb-3 font-semibold">Peak Valgus</th>
                <th className="pb-3 font-semibold">Primary Finding</th>
                <th className="pb-3 font-semibold">Risk Tier</th>
                <th className="pb-3 font-semibold">Recorded</th>
                <th className="pb-3 font-semibold text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {recentTrials.map((trial) => {
                const isHigh = trial.riskTier === 'HIGH';
                const isMod = trial.riskTier === 'MODERATE';
                const badgeClass = isHigh
                  ? 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                  : isMod
                  ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                  : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';

                return (
                  <tr key={trial.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-4 font-medium text-white">
                      <div>{trial.athlete}</div>
                      <span className="text-xs text-slate-500">{trial.sport}</span>
                    </td>
                    <td className="py-4 text-slate-300">{trial.movement}</td>
                    <td className="py-4 font-mono text-slate-200">{trial.valgusAngle}</td>
                    <td className="py-4 text-slate-300">{trial.targetRisk}</td>
                    <td className="py-4">
                      <span className={`px-2.5 py-1 text-xs font-bold rounded-full border ${badgeClass}`}>
                        {trial.riskTier} ({trial.riskScore})
                      </span>
                    </td>
                    <td className="py-4 text-xs text-slate-500">{trial.date}</td>
                    <td className="py-4 text-right">
                      <button className="text-xs font-medium text-slate-400 hover:text-emerald-400 transition-colors">
                        Review Kinematics &rarr;
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
