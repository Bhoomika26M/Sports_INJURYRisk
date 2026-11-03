import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { NotificationDropdown } from './NotificationDropdown';
import { 
  Activity, 
  User, 
  LogOut, 
  LayoutDashboard, 
  Upload, 
  Users, 
  ShieldCheck, 
  Menu, 
  X,
  Settings,
  Database
} from 'lucide-react';

const ROLE_STYLES = {
  athlete: { label: 'Athlete', bg: 'bg-indigo-950/70 text-indigo-300 border-indigo-700/50' },
  coach: { label: 'Coach', bg: 'bg-purple-950/70 text-purple-300 border-purple-700/50 shadow-[0_0_8px_rgba(168,85,247,0.25)]' },
  physiotherapist: { label: 'Physiotherapist', bg: 'bg-teal-950/70 text-teal-300 border-teal-700/50' },
  sports_scientist: { label: 'Sports Scientist', bg: 'bg-fuchsia-950/70 text-fuchsia-300 border-fuchsia-700/50' },
  administrator: { label: 'Administrator', bg: 'bg-rose-950/70 text-rose-300 border-rose-700/50' },
};

export const Navbar = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const roleStyle = user?.role ? (ROLE_STYLES[user.role] || { label: user.role, bg: 'bg-slate-900 text-slate-300 border-slate-700' }) : null;

  const isActive = (path) => location.pathname === path;

  return (
    <nav className="bg-black/70 backdrop-blur-xl border-b border-purple-900/30 px-4 sm:px-6 py-3 sticky top-0 z-40 text-slate-200">
      <div className="max-w-7xl mx-auto flex justify-between items-center">
        {/* Brand Logo & Desktop Nav Links */}
        <div className="flex items-center gap-6">
          <Link to="/" className="text-lg font-bold text-white flex items-center gap-2.5 tracking-tight group">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-purple-600 via-purple-500 to-indigo-500 flex items-center justify-center text-white shadow-[0_0_15px_rgba(168,85,247,0.4)] group-hover:shadow-[0_0_20px_rgba(168,85,247,0.7)] transition-all duration-300">
              <Activity size={18} />
            </div>
            <span>Athleti<span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-indigo-400 font-extrabold">Q</span></span>
          </Link>

          {user && (
            <div className="hidden md:flex items-center gap-1.5 text-xs font-semibold">
              <Link 
                to="/dashboard" 
                className={`px-3 py-1.5 rounded-xl flex items-center gap-1.5 transition ${
                  isActive('/dashboard') 
                    ? 'bg-purple-600/20 text-purple-300 border border-purple-500/40 shadow-[0_0_10px_rgba(168,85,247,0.2)]' 
                    : 'text-slate-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <LayoutDashboard size={15} /> Dashboard
              </Link>

              <Link 
                to="/upload" 
                className={`px-3 py-1.5 rounded-xl flex items-center gap-1.5 transition ${
                  isActive('/upload') 
                    ? 'bg-purple-600/20 text-purple-300 border border-purple-500/40 shadow-[0_0_10px_rgba(168,85,247,0.2)]' 
                    : 'text-slate-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <Upload size={15} /> Upload Video
              </Link>

              {user.role !== 'athlete' && (
                <Link 
                  to="/athletes" 
                  className={`px-3 py-1.5 rounded-xl flex items-center gap-1.5 transition ${
                    isActive('/athletes') 
                      ? 'bg-purple-600/20 text-purple-300 border border-purple-500/40 shadow-[0_0_10px_rgba(168,85,247,0.2)]' 
                      : 'text-slate-400 hover:text-white hover:bg-white/5'
                  }`}
                >
                  <Users size={15} /> Athletes
                </Link>
              )}

              {user.role === 'administrator' && (
                <Link 
                  to="/admin/users" 
                  className={`px-3 py-1.5 rounded-xl flex items-center gap-1.5 transition ${
                    isActive('/admin/users') 
                      ? 'bg-purple-600/20 text-purple-300 border border-purple-500/40 shadow-[0_0_10px_rgba(168,85,247,0.2)]' 
                      : 'text-slate-400 hover:text-white hover:bg-white/5'
                  }`}
                >
                  <ShieldCheck size={15} /> User Roles
                </Link>
              )}

              <Link 
                to="/datasets" 
                className={`px-3 py-1.5 rounded-xl flex items-center gap-1.5 transition ${
                  isActive('/datasets') 
                    ? 'bg-purple-600/20 text-purple-300 border border-purple-500/40 shadow-[0_0_10px_rgba(168,85,247,0.2)]' 
                    : 'text-slate-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <Database size={15} /> Datasets
              </Link>
            </div>
          )}
        </div>

        {/* User Profile & Actions (Desktop) */}
        <div className="hidden md:flex items-center gap-2.5">
          {user ? (
            <>
              <NotificationDropdown />

              {roleStyle && (
                <span className={`text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full border ${roleStyle.bg}`}>
                  {roleStyle.label}
                </span>
              )}

              <Link
                to="/profile"
                className="flex items-center gap-1.5 text-xs font-medium text-slate-200 hover:text-white bg-white/5 hover:bg-white/10 px-3 py-1.5 rounded-xl border border-white/10 transition"
              >
                <User size={14} className="text-purple-400" />
                <span>{user.full_name || user.email.split('@')[0]}</span>
              </Link>

              <button 
                onClick={handleLogout} 
                className="flex items-center gap-1 text-xs text-slate-400 hover:text-rose-400 font-medium p-1.5 rounded-xl hover:bg-rose-500/10 transition ml-1"
                title="Sign out"
                aria-label="Logout"
              >
                <LogOut size={15} />
              </button>
            </>
          ) : (
            <div className="flex items-center gap-2">
              <Link to="/login" className="text-slate-300 hover:text-white font-semibold text-xs px-3 py-1.5 rounded-xl transition">
                Sign In
              </Link>
              <Link to="/register" className="bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-semibold text-xs px-4 py-1.5 rounded-xl transition shadow-[0_0_15px_rgba(168,85,247,0.3)]">
                Register
              </Link>
            </div>
          )}
        </div>

        {/* Mobile Hamburger Button */}
        <div className="md:hidden flex items-center gap-2">
          {user && <NotificationDropdown />}
          {user && roleStyle && (
            <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${roleStyle.bg}`}>
              {roleStyle.label}
            </span>
          )}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-1.5 rounded-xl text-slate-400 hover:text-white hover:bg-white/5 focus:outline-none"
            aria-label="Toggle navigation menu"
          >
            {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden pt-3 pb-2 border-t border-white/10 mt-2 space-y-1 bg-black/90 p-3 rounded-2xl">
          {user ? (
            <>
              <Link 
                to="/dashboard" 
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium text-slate-300 hover:text-white hover:bg-white/5"
              >
                <LayoutDashboard size={16} /> Dashboard
              </Link>

              <Link 
                to="/upload" 
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium text-slate-300 hover:text-white hover:bg-white/5"
              >
                <Upload size={16} /> Upload Video
              </Link>

              {user.role !== 'athlete' && (
                <Link 
                  to="/athletes" 
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium text-slate-300 hover:text-white hover:bg-white/5"
                >
                  <Users size={16} /> Athletes
                </Link>
              )}

              <Link 
                to="/datasets" 
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium text-slate-300 hover:text-white hover:bg-white/5"
              >
                <Database size={16} /> Datasets & Biomechanics
              </Link>

              <Link 
                to="/profile" 
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium text-slate-300 hover:text-white hover:bg-white/5"
              >
                <Settings size={16} /> Profile & Settings
              </Link>

              <div className="pt-2 border-t border-white/10">
                <button
                  onClick={() => { setMobileMenuOpen(false); handleLogout(); }}
                  className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium text-rose-400 hover:bg-rose-500/10 text-left"
                >
                  <LogOut size={16} /> Logout
                </button>
              </div>
            </>
          ) : (
            <div className="space-y-1 pt-1">
              <Link 
                to="/login" 
                onClick={() => setMobileMenuOpen(false)}
                className="block px-3 py-2 rounded-xl text-sm font-medium text-slate-300 hover:text-white hover:bg-white/5"
              >
                Sign In
              </Link>
              <Link 
                to="/register" 
                onClick={() => setMobileMenuOpen(false)}
                className="block px-3 py-2 rounded-xl text-sm font-medium text-purple-400 font-bold hover:bg-white/5"
              >
                Create Account
              </Link>
            </div>
          )}
        </div>
      )}
    </nav>
  );
};
