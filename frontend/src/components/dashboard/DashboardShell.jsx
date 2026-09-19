/**
 * Shared DashboardShell – wraps role-specific dashboard pages.
 * Provides a greeting, stat cards, and a placeholder content area.
 */
import React from 'react';
import { useAuth } from '../../context/AuthContext';

export function StatCard({ label, value, sublabel, Icon, accent = 'emerald' }) {
  const accents = {
    emerald: 'from-emerald-500/10 to-emerald-500/5 border-emerald-500/20 text-emerald-400',
    sky:     'from-sky-500/10 to-sky-500/5 border-sky-500/20 text-sky-400',
    amber:   'from-amber-500/10 to-amber-500/5 border-amber-500/20 text-amber-400',
    violet:  'from-violet-500/10 to-violet-500/5 border-violet-500/20 text-violet-400',
    pink:    'from-pink-500/10 to-pink-500/5 border-pink-500/20 text-pink-400',
    red:     'from-red-500/10 to-red-500/5 border-red-500/20 text-red-400',
  };
  return (
    <div className={`glass-card rounded-2xl p-5 bg-gradient-to-br ${accents[accent]} border`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">{label}</p>
          <p className="text-3xl font-bold text-slate-100">{value}</p>
          {sublabel && <p className="text-xs text-slate-500 mt-1">{sublabel}</p>}
        </div>
        {Icon && (
          <div className={`p-2 rounded-xl bg-gradient-to-br ${accents[accent]} border`}>
            <Icon className="h-5 w-5" />
          </div>
        )}
      </div>
    </div>
  );
}

export function SectionTitle({ children }) {
  return (
    <h2 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
      <span className="h-4 w-0.5 bg-emerald-500 rounded-full" />
      {children}
    </h2>
  );
}

export function ComingSoonBadge() {
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-800 border border-slate-700 text-xs text-slate-500 ml-2">
      Coming soon
    </span>
  );
}

export default function DashboardShell({ role, accentColor, Icon, stats, children }) {
  const { user } = useAuth();
  const greeting = () => {
    const h = new Date().getHours();
    if (h < 12) return 'Good morning';
    if (h < 17) return 'Good afternoon';
    return 'Good evening';
  };

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className={`p-2.5 rounded-xl bg-gradient-to-br ${accentColor} border`}>
            <Icon className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-100">
              {greeting()}, {user?.full_name?.split(' ')[0] ?? 'there'} 👋
            </h1>
            <p className="text-sm text-slate-400 mt-0.5">{role} Dashboard</p>
          </div>
        </div>
        <div className="text-xs text-slate-500 bg-slate-900/60 border border-slate-800 rounded-lg px-3 py-1.5">
          {new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
        </div>
      </div>

      {/* Stats grid */}
      {stats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {stats}
        </div>
      )}

      {/* Main content */}
      {children}
    </div>
  );
}
