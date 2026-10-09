import React from 'react';
import { Activity, ShieldAlert, Award, Video, FileText, Users, Database, Sparkles, ChevronDown } from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, activeRole, setActiveRole, currentUser, athletes }) {
  const roles = [
    { id: 'athlete', label: 'Athlete View', name: 'Marcus Vance', icon: Award, badgeColor: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' },
    { id: 'coach', label: 'Coach View', name: 'Coach Martinez', icon: Users, badgeColor: 'bg-amber-500/10 text-amber-400 border-amber-500/20' },
    { id: 'physiotherapist', label: 'Physiotherapist', name: 'Dr. Jenkins (PT)', icon: ShieldAlert, badgeColor: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20' },
    { id: 'sports_scientist', label: 'Sports Scientist', name: 'Dr. Volkov (PhD)', icon: Activity, badgeColor: 'bg-purple-500/10 text-purple-400 border-purple-500/20' },
    { id: 'administrator', label: 'Admin View', name: 'Sys Admin', icon: Database, badgeColor: 'bg-rose-500/10 text-rose-400 border-rose-500/20' },
  ];

  const currentRoleObj = roles.find(r => r.id === activeRole) || roles[0];

  const navItems = [
    { id: 'video_studio', label: 'Video & Pose Tracker', icon: Video, milestone: 'M2' },
    { id: 'biomechanics', label: 'Biomechanical Analysis', icon: Activity, milestone: 'M2' },
    { id: 'injury_risk', label: 'Injury Risk Prediction', icon: ShieldAlert, milestone: 'M3' },
    { id: 'recommendations', label: 'Corrective Exercises', icon: Sparkles, milestone: 'M3' },
    { id: 'dashboards', label: 'Intelligence Dashboards', icon: Award, milestone: 'M3' },
    { id: 'athletes', label: 'Athlete Profiles', icon: Users, milestone: 'M1' },
    { id: 'datasets', label: 'Biomechanics Datasets', icon: Database, milestone: 'M1' },
  ];

  return (
    <header className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-md border-b border-slate-800/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand Logo & Milestone Status */}
          <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setActiveTab('video_studio')}>
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
              <Activity className="w-6 h-6 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
                  Kinematix AI
                </span>
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                  Milestone 1-3 Live
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono">Sports Injury Risk Detection from Video</p>
            </div>
          </div>

          {/* Role Switcher */}
          <div className="flex items-center space-x-3">
            <span className="text-xs text-slate-400 font-medium hidden md:inline">Simulate Role:</span>
            <div className="flex items-center space-x-1.5 bg-slate-900/90 p-1 rounded-xl border border-slate-800">
              {roles.map((r) => {
                const Icon = r.icon;
                const isSelected = activeRole === r.id;
                return (
                  <button
                    key={r.id}
                    onClick={() => setActiveRole(r.id)}
                    className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                      isSelected
                        ? 'bg-slate-800 text-white shadow-sm border border-slate-700/80'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                    }`}
                  >
                    <Icon className={`w-3.5 h-3.5 ${isSelected ? 'text-cyan-400' : 'text-slate-500'}`} />
                    <span className="hidden lg:inline">{r.label}</span>
                    <span className="lg:hidden">{r.label.split(' ')[0]}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex space-x-1 overflow-x-auto py-2.5 border-t border-slate-900/80 scrollbar-none">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${
                  isActive
                    ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-cyan-400' : 'text-slate-500'}`} />
                <span>{item.label}</span>
                <span className={`text-[9px] px-1.5 py-0.2 rounded font-mono ${isActive ? 'bg-cyan-500/20 text-cyan-300' : 'bg-slate-800 text-slate-500'}`}>
                  {item.milestone}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </header>
  );
}
