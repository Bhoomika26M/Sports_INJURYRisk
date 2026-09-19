import React from 'react';
import { Users, TrendingUp, AlertTriangle, Video, ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import DashboardShell, { StatCard, SectionTitle, ComingSoonBadge } from '../../components/dashboard/DashboardShell';

export default function CoachDashboard() {
  return (
    <DashboardShell
      role="Coach"
      Icon={Users}
      accentColor="from-violet-500/10 to-violet-500/5 border-violet-500/20 text-violet-400"
      stats={
        <>
          <StatCard label="Athletes Assigned" value="—" sublabel="Via admin assignment" Icon={Users} accent="violet" />
          <StatCard label="High-Risk Athletes" value="—" sublabel="Requiring attention" Icon={AlertTriangle} accent="red" />
          <StatCard label="Videos This Week" value="—" sublabel="Pending review" Icon={Video} accent="sky" />
          <StatCard label="Avg Risk Score" value="—" sublabel="Across team" Icon={TrendingUp} accent="amber" />
        </>
      }
    >
      <div>
        <SectionTitle>Athlete Roster</SectionTitle>
        <div className="mt-4 grid sm:grid-cols-2 gap-4">
          <Link
            to="/athletes"
            id="dash-coach-athletes"
            className="glass-card glass-card-hover rounded-2xl p-5 flex items-center gap-4 group"
          >
            <div className="p-3 bg-violet-500/10 border border-violet-500/20 rounded-xl group-hover:bg-violet-500/20 transition">
              <Users className="h-5 w-5 text-violet-400" />
            </div>
            <div className="flex-1">
              <p className="font-semibold text-slate-100 text-sm">View My Athletes</p>
              <p className="text-xs text-slate-400 mt-0.5">Browse assigned athlete profiles</p>
            </div>
            <ChevronRight className="h-4 w-4 text-slate-500 group-hover:text-slate-300 transition" />
          </Link>
          <div className="glass-card rounded-2xl p-5 flex items-center gap-4 opacity-60">
            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl">
              <AlertTriangle className="h-5 w-5 text-red-400" />
            </div>
            <div className="flex-1">
              <p className="font-semibold text-slate-100 text-sm flex items-center">
                Risk Alerts <ComingSoonBadge />
              </p>
              <p className="text-xs text-slate-400 mt-0.5">Athletes flagged for high injury risk</p>
            </div>
          </div>
        </div>
      </div>

      <div>
        <SectionTitle>Team Risk Overview</SectionTitle>
        <div className="mt-4 glass-card rounded-2xl px-6 py-12 flex flex-col items-center text-center gap-3">
          <TrendingUp className="h-10 w-10 text-slate-600" />
          <p className="text-slate-400 text-sm font-medium">No data available yet</p>
          <p className="text-slate-500 text-xs max-w-xs">
            Risk trend charts will appear once athletes have completed video analyses.
          </p>
        </div>
      </div>
    </DashboardShell>
  );
}
