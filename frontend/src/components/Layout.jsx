import React from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const Layout = () => {
  const { user, logout } = useAuth();
  const location = useLocation();

  const isActive = (path) => location.pathname === path;

  const getRoleBadgeClass = (role) => {
    const roleClasses = {
      athlete: 'badge-athlete',
      coach: 'badge-coach',
      physiotherapist: 'badge-physiotherapist',
      sports_scientist: 'badge-sports-scientist',
      administrator: 'badge-administrator',
    };
    return roleClasses[role] || 'badge-athlete';
  };

  return (
    <div className="min-h-screen bg-[#F9F9FF] text-[#141B2B] flex flex-col justify-between">
      {/* Top Clinical Header Bar */}
      <header className="sticky top-0 z-40 bg-white/90 backdrop-blur-md border-b border-[#E1BFB5]/30 shadow-[0_1px_8px_rgba(0,0,0,0.03)]">
        <div className="w-full px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-6">
              {/* Brand Logo & Title */}
              <Link to="/dashboard" className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-[#BD4006] text-white flex items-center justify-center font-display font-bold text-lg shadow-sm">
                  K
                </div>
                <div className="flex flex-col">
                  <span className="font-display font-bold text-base tracking-tight text-[#141B2B]">
                    KinetiK <span className="text-[#BD4006]">Risk</span>
                  </span>
                  <span className="font-mono text-[9px] uppercase tracking-wider text-[#594139]">
                    Biomechanical Telemetry
                  </span>
                </div>
              </Link>

              <div className="hidden lg:block h-6 w-px bg-[#E1BFB5]/40" />

              {/* Navigation Links */}
              <nav className="hidden sm:flex items-center space-x-1">
                <Link
                  to="/dashboard"
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    isActive('/dashboard')
                      ? 'bg-[#BD4006] text-white shadow-sm font-semibold'
                      : 'text-[#594139] hover:bg-[#F1F3FF] hover:text-[#141B2B]'
                  }`}
                >
                  Dashboard
                </Link>
                <Link
                  to="/athletes"
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    isActive('/athletes')
                      ? 'bg-[#BD4006] text-white shadow-sm font-semibold'
                      : 'text-[#594139] hover:bg-[#F1F3FF] hover:text-[#141B2B]'
                  }`}
                >
                  Athletes
                </Link>
                <Link
                  to="/videos/upload"
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    isActive('/videos/upload')
                      ? 'bg-[#BD4006] text-white shadow-sm font-semibold'
                      : 'text-[#594139] hover:bg-[#F1F3FF] hover:text-[#141B2B]'
                  }`}
                >
                  Upload Video
                </Link>
              </nav>
            </div>

            {/* Right Status Badges & User Context */}
            <div className="flex items-center space-x-3">
              <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#ECFDF5] border border-[#6CF8BB]/50 text-[#006C49] font-mono text-[11px] font-semibold">
                <span className="w-2 h-2 rounded-full bg-[#006C49] animate-pulse" />
                <span>120Hz Calibrated</span>
              </div>

              <div className="flex items-center space-x-2 pl-2 border-l border-[#E5E7EB]">
                <div className="flex flex-col text-right hidden sm:block">
                  <span className="text-xs font-semibold text-[#141B2B] leading-tight">{user?.full_name}</span>
                  <span className="text-[10px] text-[#594139] capitalize">{user?.role?.replace(/_/g, ' ')}</span>
                </div>
                <span className={getRoleBadgeClass(user?.role)}>{user?.role}</span>
              </div>

              <Link
                to="/profile"
                className="text-xs text-[#594139] hover:text-[#141B2B] font-medium p-1.5 rounded hover:bg-[#F1F3FF] transition-colors"
                title="Profile settings"
              >
                Profile
              </Link>
              <button
                onClick={logout}
                className="text-xs text-[#BA1A1A] hover:text-red-700 font-medium px-2 py-1 rounded hover:bg-red-50 transition-colors"
              >
                Logout
              </button>
            </div>
          </div>
        </div>

        {/* Secondary Sub-Bar / Telemetry Breadcrumb Strip */}
        <div className="h-7 w-full px-4 sm:px-6 lg:px-8 bg-[#F1F3FF] border-t border-[#E1BFB5]/20 flex items-center justify-between text-[11px] font-mono text-[#594139]">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-[#006C49]" />
            <span className="font-semibold text-[#141B2B]">Node 04 // Optical Gateway</span>
            <span className="text-gray-300">/</span>
            <span>AI Movement Biomechanics v4.2</span>
          </div>
          <div className="hidden sm:flex items-center gap-3 text-[10px]">
            <span>ISO 13485 CLASS II</span>
            <span>•</span>
            <span>HIPAA VALIDATED</span>
          </div>
        </div>
      </header>

      <main className="w-full flex-1 px-4 sm:px-6 lg:px-8 py-6">
        <Outlet />
      </main>
    </div>
  );
};

export default Layout;
