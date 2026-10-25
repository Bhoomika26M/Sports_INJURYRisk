import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { 
  LogOut, 
  User, 
  Upload, 
  Settings, 
  Users, 
  LayoutDashboard, 
  ShieldCheck, 
  Activity, 
  Menu,
  X
} from 'lucide-react';

const ROLE_STYLES = {
  athlete: { label: 'Athlete', bg: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  coach: { label: 'Coach', bg: 'bg-indigo-50 text-indigo-700 border-indigo-200' },
  physiotherapist: { label: 'Physiotherapist', bg: 'bg-teal-50 text-teal-700 border-teal-200' },
  sports_scientist: { label: 'Sports Scientist', bg: 'bg-purple-50 text-purple-700 border-purple-200' },
  administrator: { label: 'Administrator', bg: 'bg-rose-50 text-rose-700 border-rose-200' },
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

  const roleStyle = user?.role ? (ROLE_STYLES[user.role] || { label: user.role, bg: 'bg-slate-100 text-slate-800 border-slate-200' }) : null;

  const isActive = (path) => location.pathname === path;

  return (
    <nav className="bg-white border-b border-slate-200 px-4 sm:px-6 py-3 sticky top-0 z-40 shadow-xs">
      <div className="max-w-7xl mx-auto flex justify-between items-center">
        {/* Brand Logo & Desktop Nav Links */}
        <div className="flex items-center gap-6">
          <Link to="/" className="text-lg font-bold text-slate-900 flex items-center gap-2 tracking-tight">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-xs">
              <Activity size={18} />
            </div>
            <span>Athleti<span className="text-blue-600">Q</span></span>
          </Link>

          {user && (
            <div className="hidden md:flex items-center gap-1 text-xs font-semibold">
              <Link 
                to="/dashboard" 
                className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition ${
                  isActive('/dashboard') ? 'bg-blue-50 text-blue-700' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                }`}
              >
                <LayoutDashboard size={15} /> Dashboard
              </Link>

              {user.role === 'athlete' && (
                <Link 
                  to="/upload" 
                  className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition ${
                    isActive('/upload') ? 'bg-blue-50 text-blue-700' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                  }`}
                >
                  <Upload size={15} /> Upload Video
                </Link>
              )}

              {user.role !== 'athlete' && (
                <Link 
                  to="/athletes" 
                  className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition ${
                    isActive('/athletes') ? 'bg-blue-50 text-blue-700' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                  }`}
                >
                  <Users size={15} /> Athletes
                </Link>
              )}

              {user.role === 'administrator' && (
                <Link 
                  to="/admin/users" 
                  className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition ${
                    isActive('/admin/users') ? 'bg-blue-50 text-blue-700' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                  }`}
                >
                  <ShieldCheck size={15} /> User Roles
                </Link>
              )}
            </div>
          )}
        </div>

        {/* User Profile & Actions (Desktop) */}
        <div className="hidden md:flex items-center gap-2.5">
          {user ? (
            <>
              {roleStyle && (
                <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${roleStyle.bg}`}>
                  {roleStyle.label}
                </span>
              )}

              <Link
                to="/profile"
                className="flex items-center gap-1.5 text-xs font-medium text-slate-700 hover:text-blue-600 bg-slate-50 hover:bg-slate-100 px-2.5 py-1.5 rounded-lg border border-slate-200 transition"
              >
                <User size={14} className="text-slate-500" />
                <span>{user.full_name || user.email.split('@')[0]}</span>
              </Link>

              <button 
                onClick={handleLogout} 
                className="flex items-center gap-1 text-xs text-slate-500 hover:text-red-600 font-medium p-1.5 rounded-lg hover:bg-red-50 transition ml-1"
                title="Sign out"
                aria-label="Logout"
              >
                <LogOut size={15} />
              </button>
            </>
          ) : (
            <div className="flex items-center gap-2">
              <Link to="/login" className="text-slate-700 hover:text-blue-600 font-semibold text-xs px-3 py-1.5 rounded-lg transition">
                Sign In
              </Link>
              <Link to="/register" className="bg-blue-600 text-white font-semibold text-xs px-3.5 py-1.5 rounded-lg hover:bg-blue-700 transition shadow-xs">
                Register
              </Link>
            </div>
          )}
        </div>

        {/* Mobile Hamburger Button */}
        <div className="md:hidden flex items-center gap-2">
          {user && roleStyle && (
            <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${roleStyle.bg}`}>
              {roleStyle.label}
            </span>
          )}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-1.5 rounded-lg text-slate-600 hover:bg-slate-100 focus:outline-none"
            aria-label="Toggle navigation menu"
          >
            {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden pt-3 pb-2 border-t border-slate-100 mt-2 space-y-1">
          {user ? (
            <>
              <Link 
                to="/dashboard" 
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                <LayoutDashboard size={16} /> Dashboard
              </Link>

              {user.role === 'athlete' && (
                <Link 
                  to="/upload" 
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50"
                >
                  <Upload size={16} /> Upload Video
                </Link>
              )}

              {user.role !== 'athlete' && (
                <Link 
                  to="/athletes" 
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50"
                >
                  <Users size={16} /> Athletes
                </Link>
              )}

              <Link 
                to="/profile" 
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                <Settings size={16} /> Profile & Settings
              </Link>

              <div className="pt-2 border-t border-slate-100">
                <button
                  onClick={() => { setMobileMenuOpen(false); handleLogout(); }}
                  className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-red-600 hover:bg-red-50 text-left"
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
                className="block px-3 py-2 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                Sign In
              </Link>
              <Link 
                to="/register" 
                onClick={() => setMobileMenuOpen(false)}
                className="block px-3 py-2 rounded-lg text-sm font-medium text-blue-600 font-bold hover:bg-blue-50"
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
