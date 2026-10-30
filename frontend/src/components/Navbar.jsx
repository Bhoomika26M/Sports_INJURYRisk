import React from 'react';
import { Activity, ShieldAlert, Award, Video, Users, Database, Sparkles, LogIn, LogOut, UserCheck, ArrowLeftRight } from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, activeRole, setActiveRole, currentUser, onOpenAuth, onLogout }) {
  const roles = [
    { id: 'athlete', label: 'Athlete', name: 'Marcus Vance', icon: Award },
    { id: 'coach', label: 'Coach', name: 'Coach Martinez', icon: Users },
    { id: 'physiotherapist', label: 'Physiotherapist', name: 'Dr. Jenkins', icon: ShieldAlert },
    { id: 'sports_scientist', label: 'Sports Scientist', name: 'Dr. Volkov', icon: Activity },
    { id: 'administrator', label: 'Administrator', name: 'Sys Admin', icon: Database },
  ];

  const navItems = [
    { id: 'video_studio', label: 'Video & Pose Tracker', icon: Video },
    { id: 'comparison', label: 'Compare Sessions', icon: ArrowLeftRight },
    { id: 'biomechanics', label: 'Biomechanical Analysis', icon: Activity },
    { id: 'injury_risk', label: 'Risk Screening', icon: ShieldAlert },
    { id: 'recommendations', label: 'Corrective Exercises', icon: Sparkles },
    { id: 'dashboards', label: 'Intelligence Dashboards', icon: Award },
    { id: 'athletes', label: 'Athlete Profiles', icon: Users },
    { id: 'datasets', label: 'Reference Baselines', icon: Database },
  ];

  return (
    <header className="sticky top-0 z-40 bg-slate-900 border-b border-slate-800 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand Logo & Product Name */}
          <div
            className="flex items-center space-x-3 cursor-pointer select-none"
            onClick={() => setActiveTab('video_studio')}
          >
            <div className="w-9 h-9 rounded-lg bg-teal-700 flex items-center justify-center shadow-xs">
              <Activity className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-lg tracking-tight text-white">
                  Kinematix
                </span>
                <span className="text-[10px] font-medium px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                  Sports Biomechanics
                </span>
              </div>
              <p className="text-xs text-slate-400">Movement Analysis &amp; Injury Risk Intelligence</p>
            </div>
          </div>

          {/* Right Controls: Role Switcher & Auth */}
          <div className="flex items-center space-x-3">
            {/* Perspective Selector */}
            <div className="hidden md:flex items-center space-x-1 bg-slate-950 p-1 rounded-lg border border-slate-800">
              <span className="text-[11px] text-slate-400 px-2 font-medium">Role:</span>
              {roles.map((r) => {
                const Icon = r.icon;
                const isSelected = activeRole === r.id;
                return (
                  <button
                    key={r.id}
                    onClick={() => setActiveRole(r.id)}
                    className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                      isSelected
                        ? 'bg-slate-800 text-white font-semibold border border-slate-700 shadow-xs'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                    }`}
                  >
                    <Icon className={`w-3.5 h-3.5 ${isSelected ? 'text-teal-400' : 'text-slate-500'}`} />
                    <span>{r.label}</span>
                  </button>
                );
              })}
            </div>

            {/* User Session Button */}
            {currentUser ? (
              <div className="flex items-center space-x-2 bg-slate-950 pl-3 pr-1 py-1 rounded-lg border border-slate-800">
                <div className="flex items-center space-x-2 text-xs">
                  <UserCheck className="w-3.5 h-3.5 text-teal-400" />
                  <span className="text-slate-200 font-medium hidden sm:inline">{currentUser.full_name}</span>
                  <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-900 text-slate-300 border border-slate-700">
                    {currentUser.role.replace('_', ' ')}
                  </span>
                </div>
                <button
                  onClick={onLogout}
                  title="Sign Out"
                  className="p-1.5 rounded text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition-colors"
                >
                  <LogOut className="w-3.5 h-3.5" />
                </button>
              </div>
            ) : (
              <button
                onClick={() => onOpenAuth('login')}
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-teal-700 hover:bg-teal-800 text-white text-xs font-semibold shadow-xs transition-colors"
              >
                <LogIn className="w-3.5 h-3.5" />
                <span>Sign In</span>
              </button>
            )}
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex space-x-1 overflow-x-auto py-2.5 border-t border-slate-800/80 scrollbar-none">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex items-center space-x-2 px-3 py-1.5 rounded-md text-xs font-medium whitespace-nowrap transition-colors ${
                  isActive
                    ? 'bg-teal-700 text-white shadow-xs font-semibold'
                    : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </div>
      </div>
    </header>
  );
}
