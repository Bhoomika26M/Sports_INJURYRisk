import React from 'react';
import {
  Activity, Upload, TrendingUp, Shield,
  Play, ChevronRight, AlertTriangle,
} from 'lucide-react';
import DashboardShell, { StatCard, SectionTitle, ComingSoonBadge } from '../../components/dashboard/DashboardShell';
import { Link } from 'react-router-dom';

export default function AthleteDashboard() {
  return (
    <DashboardShell
      role="Athlete"
      Icon={Activity}
      accentColor="from-sky-500/10 to-sky-500/5 border-sky-500/20 text-sky-400"
      stats={
        <>
          <StatCard label="Risk Score" value="—" sublabel="No analysis yet" Icon={Shield} accent="sky" />
          <StatCard label="Videos Uploaded" value="0" sublabel="Upload your first" Icon={Upload} accent="emerald" />
          <StatCard label="Assessments" value="0" sublabel="Awaiting physio" Icon={TrendingUp} accent="violet" />
          <StatCard label="Injuries Logged" value="0" sublabel="No history recorded" Icon={AlertTriangle} accent="amber" />
        </>
      }
    >
      {/* Quick actions */}
      <div>
        <SectionTitle>Quick Actions</SectionTitle>
        <div className="grid sm:grid-cols-2 gap-4 mt-4">
          <Link
            to="/upload"
            id="dash-athlete-upload"
            className="glass-card glass-card-hover rounded-2xl p-5 flex items-center gap-4 group"
          >
            <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl group-hover:bg-emerald-500/20 transition">
              <Upload className="h-5 w-5 text-emerald-400" />
            </div>
            <div className="flex-1">
              <p className="font-semibold text-slate-100 text-sm">Upload Movement Video</p>
              <p className="text-xs text-slate-400 mt-0.5">Submit a squat, jump landing, or running clip</p>
            </div>
            <ChevronRight className="h-4 w-4 text-slate-500 group-hover:text-slate-300 transition" />
          </Link>
          <div className="glass-card rounded-2xl p-5 flex items-center gap-4 opacity-60">
            <div className="p-3 bg-violet-500/10 border border-violet-500/20 rounded-xl">
              <TrendingUp className="h-5 w-5 text-violet-400" />
            </div>
            <div className="flex-1">
              <p className="font-semibold text-slate-100 text-sm flex items-center gap-1">
                Risk History <ComingSoonBadge />
              </p>
              <p className="text-xs text-slate-400 mt-0.5">View past risk scores over time</p>
            </div>
          </div>
        </div>
      </div>

      {/* Recent analyses placeholder */}
      <div>
        <SectionTitle>Recent Analyses</SectionTitle>
        <div className="mt-4 glass-card rounded-2xl px-6 py-12 flex flex-col items-center text-center gap-3">
          <Play className="h-10 w-10 text-slate-600" />
          <p className="text-slate-400 text-sm font-medium">No analyses yet</p>
          <p className="text-slate-500 text-xs max-w-xs">
            Upload a video to get your first biomechanical risk assessment powered by pose estimation.
          </p>
        </div>
      </div>
    </DashboardShell>
  );
}
