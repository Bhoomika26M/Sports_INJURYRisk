import React from 'react';
import { FlaskConical, Users, BarChart3, Database, ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import DashboardShell, { StatCard, SectionTitle, ComingSoonBadge } from '../../components/dashboard/DashboardShell';

export default function ScientistDashboard() {
  return (
    <DashboardShell
      role="Sports Scientist"
      Icon={FlaskConical}
      accentColor="from-amber-500/10 to-amber-500/5 border-amber-500/20 text-amber-400"
      stats={
        <>
          <StatCard label="Total Athletes" value="—" sublabel="In the system" Icon={Users} accent="amber" />
          <StatCard label="Analyses Run" value="—" sublabel="All time" Icon={BarChart3} accent="sky" />
          <StatCard label="Biomechanical Metrics" value="—" sublabel="Collected data points" Icon={Database} accent="violet" />
          <StatCard label="Model Accuracy" value="—" sublabel="ML pipeline" Icon={FlaskConical} accent="emerald" />
        </>
      }
    >
      <div>
        <SectionTitle>Research Tools</SectionTitle>
        <div className="mt-4 grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <Link
            to="/athletes"
            id="dash-sci-athletes"
            className="glass-card glass-card-hover rounded-2xl p-5 flex items-center gap-4 group"
          >
            <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl group-hover:bg-amber-500/20 transition">
              <Users className="h-5 w-5 text-amber-400" />
            </div>
            <div className="flex-1">
              <p className="font-semibold text-slate-100 text-sm">All Athletes</p>
              <p className="text-xs text-slate-400 mt-0.5">Full population access</p>
            </div>
            <ChevronRight className="h-4 w-4 text-slate-500 group-hover:text-slate-300 transition" />
          </Link>
          <div className="glass-card rounded-2xl p-5 flex items-center gap-4 opacity-60">
            <div className="p-3 bg-sky-500/10 border border-sky-500/20 rounded-xl">
              <BarChart3 className="h-5 w-5 text-sky-400" />
            </div>
            <div className="flex-1">
              <p className="font-semibold text-slate-100 text-sm flex items-center">
                Population Analytics <ComingSoonBadge />
              </p>
              <p className="text-xs text-slate-400 mt-0.5">Aggregate biomechanical trends</p>
            </div>
          </div>
          <div className="glass-card rounded-2xl p-5 flex items-center gap-4 opacity-60">
            <div className="p-3 bg-violet-500/10 border border-violet-500/20 rounded-xl">
              <Database className="h-5 w-5 text-violet-400" />
            </div>
            <div className="flex-1">
              <p className="font-semibold text-slate-100 text-sm flex items-center">
                Dataset Export <ComingSoonBadge />
              </p>
              <p className="text-xs text-slate-400 mt-0.5">Download metrics for research</p>
            </div>
          </div>
        </div>
      </div>

      <div>
        <SectionTitle>Risk Distribution</SectionTitle>
        <div className="mt-4 glass-card rounded-2xl px-6 py-12 flex flex-col items-center text-center gap-3">
          <BarChart3 className="h-10 w-10 text-slate-600" />
          <p className="text-slate-400 text-sm font-medium">Charts coming in the next sprint</p>
          <p className="text-slate-500 text-xs max-w-xs">
            Risk tier distributions and biomechanical metric charts will render here once the ML pipeline is connected.
          </p>
        </div>
      </div>
    </DashboardShell>
  );
}
