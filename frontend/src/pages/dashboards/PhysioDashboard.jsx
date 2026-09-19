import React from 'react';
import { Stethoscope, ClipboardList, Users, AlertTriangle, ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import DashboardShell, { StatCard, SectionTitle, ComingSoonBadge } from '../../components/dashboard/DashboardShell';

export default function PhysioDashboard() {
  return (
    <DashboardShell
      role="Physiotherapist"
      Icon={Stethoscope}
      accentColor="from-pink-500/10 to-pink-500/5 border-pink-500/20 text-pink-400"
      stats={
        <>
          <StatCard label="Athletes Under Care" value="—" sublabel="Assigned athletes" Icon={Users} accent="pink" />
          <StatCard label="Assessments Done" value="—" sublabel="All time" Icon={ClipboardList} accent="emerald" />
          <StatCard label="Injuries Logged" value="—" sublabel="This month" Icon={AlertTriangle} accent="amber" />
          <StatCard label="High-Risk Flags" value="—" sublabel="Needs review" Icon={Stethoscope} accent="red" />
        </>
      }
    >
      <div>
        <SectionTitle>Clinical Tools</SectionTitle>
        <div className="mt-4 grid sm:grid-cols-2 gap-4">
          <Link
            to="/athletes"
            id="dash-physio-athletes"
            className="glass-card glass-card-hover rounded-2xl p-5 flex items-center gap-4 group"
          >
            <div className="p-3 bg-pink-500/10 border border-pink-500/20 rounded-xl group-hover:bg-pink-500/20 transition">
              <Users className="h-5 w-5 text-pink-400" />
            </div>
            <div className="flex-1">
              <p className="font-semibold text-slate-100 text-sm">Athlete Profiles</p>
              <p className="text-xs text-slate-400 mt-0.5">Review injury history & assessments</p>
            </div>
            <ChevronRight className="h-4 w-4 text-slate-500 group-hover:text-slate-300 transition" />
          </Link>
          <div className="glass-card rounded-2xl p-5 flex items-center gap-4 opacity-60">
            <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl">
              <ClipboardList className="h-5 w-5 text-emerald-400" />
            </div>
            <div className="flex-1">
              <p className="font-semibold text-slate-100 text-sm flex items-center">
                Assessment Forms <ComingSoonBadge />
              </p>
              <p className="text-xs text-slate-400 mt-0.5">Record physical assessment data</p>
            </div>
          </div>
        </div>
      </div>

      <div>
        <SectionTitle>Recent Injury Records</SectionTitle>
        <div className="mt-4 glass-card rounded-2xl px-6 py-12 flex flex-col items-center text-center gap-3">
          <ClipboardList className="h-10 w-10 text-slate-600" />
          <p className="text-slate-400 text-sm font-medium">No injury records yet</p>
          <p className="text-slate-500 text-xs max-w-xs">
            Injury history records for your athletes will appear here after logging.
          </p>
        </div>
      </div>
    </DashboardShell>
  );
}
