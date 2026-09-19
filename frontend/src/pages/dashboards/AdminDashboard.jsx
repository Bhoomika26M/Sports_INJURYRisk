import React from 'react';
import { ShieldCheck, Users, UserPlus, Settings, Activity, ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import DashboardShell, { StatCard, SectionTitle, ComingSoonBadge } from '../../components/dashboard/DashboardShell';

export default function AdminDashboard() {
  return (
    <DashboardShell
      role="Admin"
      Icon={ShieldCheck}
      accentColor="from-red-500/10 to-red-500/5 border-red-500/20 text-red-400"
      stats={
        <>
          <StatCard label="Total Users" value="—" sublabel="All roles" Icon={Users} accent="red" />
          <StatCard label="Athletes" value="—" sublabel="Registered profiles" Icon={Activity} accent="sky" />
          <StatCard label="Assignments" value="—" sublabel="Active coach links" Icon={UserPlus} accent="violet" />
          <StatCard label="Analyses Today" value="—" sublabel="Videos processed" Icon={Settings} accent="emerald" />
        </>
      }
    >
      <div>
        <SectionTitle>Admin Controls</SectionTitle>
        <div className="mt-4 grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <Link
            to="/athletes"
            id="dash-admin-athletes"
            className="glass-card glass-card-hover rounded-2xl p-5 flex items-center gap-4 group"
          >
            <div className="p-3 bg-sky-500/10 border border-sky-500/20 rounded-xl group-hover:bg-sky-500/20 transition">
              <Users className="h-5 w-5 text-sky-400" />
            </div>
            <div className="flex-1">
              <p className="font-semibold text-slate-100 text-sm">All Athletes</p>
              <p className="text-xs text-slate-400 mt-0.5">View and manage every athlete</p>
            </div>
            <ChevronRight className="h-4 w-4 text-slate-500 group-hover:text-slate-300 transition" />
          </Link>

          <div className="glass-card rounded-2xl p-5 flex items-center gap-4 opacity-60">
            <div className="p-3 bg-violet-500/10 border border-violet-500/20 rounded-xl">
              <UserPlus className="h-5 w-5 text-violet-400" />
            </div>
            <div className="flex-1">
              <p className="font-semibold text-slate-100 text-sm flex items-center">
                Manage Users <ComingSoonBadge />
              </p>
              <p className="text-xs text-slate-400 mt-0.5">Create coaches, physios, scientists</p>
            </div>
          </div>

          <div className="glass-card rounded-2xl p-5 flex items-center gap-4 opacity-60">
            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl">
              <Settings className="h-5 w-5 text-red-400" />
            </div>
            <div className="flex-1">
              <p className="font-semibold text-slate-100 text-sm flex items-center">
                System Settings <ComingSoonBadge />
              </p>
              <p className="text-xs text-slate-400 mt-0.5">Configure app-wide settings</p>
            </div>
          </div>
        </div>
      </div>

      {/* Audit log placeholder */}
      <div>
        <SectionTitle>Recent System Activity</SectionTitle>
        <div className="mt-4 glass-card rounded-2xl divide-y divide-slate-800/60">
          {[
            'Admin panel active',
            'Database migrations applied',
            'Seed admin user created',
          ].map((item, i) => (
            <div key={i} className="flex items-center gap-3 px-5 py-3.5">
              <span className="h-2 w-2 rounded-full bg-emerald-500 flex-shrink-0" />
              <p className="text-sm text-slate-300">{item}</p>
              <span className="ml-auto text-xs text-slate-600">System</span>
            </div>
          ))}
        </div>
      </div>
    </DashboardShell>
  );
}
