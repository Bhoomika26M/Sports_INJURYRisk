import React, { useState } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import {
  Activity, Menu, X, LogOut, User,
  LayoutDashboard, Users, Upload, Stethoscope, FlaskConical, ShieldCheck,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const ROLE_META = {
  athlete:          { label: 'Athlete',          color: 'text-sky-400',     bg: 'bg-sky-500/10 border-sky-500/20' },
  coach:            { label: 'Coach',             color: 'text-violet-400',  bg: 'bg-violet-500/10 border-violet-500/20' },
  physiotherapist:  { label: 'Physiotherapist',   color: 'text-pink-400',    bg: 'bg-pink-500/10 border-pink-500/20' },
  sports_scientist: { label: 'Sports Scientist',  color: 'text-amber-400',   bg: 'bg-amber-500/10 border-amber-500/20' },
  admin:            { label: 'Admin',             color: 'text-red-400',     bg: 'bg-red-500/10 border-red-500/20' },
};

const NAV_BY_ROLE = {
  athlete:          [
    { to: '/dashboard/athlete',         label: 'My Dashboard', Icon: LayoutDashboard },
    { to: '/upload',                    label: 'Upload Video',  Icon: Upload },
  ],
  coach:            [
    { to: '/dashboard/coach',           label: 'Dashboard',    Icon: LayoutDashboard },
    { to: '/athletes',                  label: 'My Athletes',   Icon: Users },
    { to: '/upload',                    label: 'Upload Video',  Icon: Upload },
  ],
  physiotherapist:  [
    { to: '/dashboard/physiotherapist', label: 'Dashboard',    Icon: LayoutDashboard },
    { to: '/athletes',                  label: 'Athletes',      Icon: Users },
    { to: '/upload',                    label: 'Upload Video',  Icon: Upload },
  ],
  sports_scientist: [
    { to: '/dashboard/scientist',       label: 'Dashboard',    Icon: LayoutDashboard },
    { to: '/athletes',                  label: 'All Athletes',  Icon: Users },
    { to: '/upload',                    label: 'Upload Video',  Icon: Upload },
  ],
  admin:            [
    { to: '/dashboard/admin',           label: 'Admin Panel',  Icon: ShieldCheck },
    { to: '/athletes',                  label: 'Athletes',      Icon: Users },
    { to: '/upload',                    label: 'Upload Video',  Icon: Upload },
  ],
};

function NavItem({ to, label, Icon, onClick }) {
  return (
    <NavLink
      to={to}
      onClick={onClick}
      className={({ isActive }) =>
        `flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150
         ${isActive
           ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
           : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60'}`
      }
    >
      <Icon className="h-4 w-4 flex-shrink-0" />
      {label}
    </NavLink>
  );
}

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  const meta = user ? ROLE_META[user.role] : null;
  const navItems = user ? (NAV_BY_ROLE[user.role] ?? []) : [];

  function handleLogout() {
    logout();
    navigate('/login');
  }

  return (
    <header className="sticky top-0 z-50 border-b border-slate-800/80 bg-slate-950/90 backdrop-blur-lg">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between gap-4">

          {/* Brand */}
          <Link to={user ? (NAV_BY_ROLE[user.role]?.[0]?.to ?? '/') : '/login'}
                id="nav-brand" className="flex items-center gap-2.5 flex-shrink-0">
            <div className="p-1.5 bg-emerald-500/10 rounded-lg border border-emerald-500/20">
              <Activity className="h-5 w-5 text-emerald-400" />
            </div>
            <span className="text-base font-bold text-slate-100 tracking-tight hidden sm:block">
              Injury<span className="text-emerald-400">Guard</span>
            </span>
          </Link>

          {/* Desktop nav */}
          {user && (
            <nav className="hidden md:flex items-center gap-1 flex-1 ml-4" aria-label="Primary navigation">
              {navItems.map((item) => (
                <NavItem key={item.to} {...item} />
              ))}
            </nav>
          )}

          {/* Right section */}
          <div className="flex items-center gap-3 flex-shrink-0">
            {user ? (
              <>
                {/* Role badge */}
                {meta && (
                  <div className={`hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${meta.bg} ${meta.color}`}>
                    {meta.label}
                  </div>
                )}

                {/* User name */}
                <div className="hidden md:flex items-center gap-1.5 text-sm text-slate-400">
                  <User className="h-3.5 w-3.5" />
                  <span className="max-w-[120px] truncate">{user.full_name}</span>
                </div>

                {/* Logout */}
                <button
                  id="nav-logout"
                  onClick={handleLogout}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm text-slate-400 hover:text-red-400 hover:bg-red-500/10 border border-transparent hover:border-red-500/20 transition-all duration-150"
                  aria-label="Sign out"
                >
                  <LogOut className="h-4 w-4" />
                  <span className="hidden sm:block">Sign out</span>
                </button>

                {/* Mobile hamburger */}
                <button
                  id="nav-mobile-menu"
                  className="md:hidden p-1.5 text-slate-400 hover:text-slate-100 rounded-lg hover:bg-slate-800 transition"
                  onClick={() => setMobileOpen((v) => !v)}
                  aria-label="Toggle menu"
                >
                  {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
                </button>
              </>
            ) : (
              <div className="flex items-center gap-2">
                <Link to="/login" id="nav-login"
                  className="px-3 py-1.5 text-sm text-slate-300 hover:text-slate-100 rounded-lg hover:bg-slate-800 transition">
                  Sign in
                </Link>
                <Link to="/register" id="nav-register"
                  className="px-3 py-1.5 text-sm bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded-lg shadow-sm shadow-emerald-500/20 transition">
                  Register
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      {user && mobileOpen && (
        <div className="md:hidden border-t border-slate-800/80 bg-slate-950/95 px-4 py-3 space-y-1">
          {meta && (
            <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 mb-3 rounded-full text-xs font-semibold border ${meta.bg} ${meta.color}`}>
              {meta.label} — {user.full_name}
            </div>
          )}
          {navItems.map((item) => (
            <NavItem key={item.to} {...item} onClick={() => setMobileOpen(false)} />
          ))}
          <button
            onClick={() => { setMobileOpen(false); handleLogout(); }}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-red-400 hover:bg-red-500/10 transition"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </button>
        </div>
      )}
    </header>
  );
}
