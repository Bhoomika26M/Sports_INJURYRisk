import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Eye, EyeOff, LogIn, Activity } from 'lucide-react';
import api from '../api/axiosInstance';
import { useAuth } from '../context/AuthContext';

const ROLE_ROUTES = {
  athlete:         '/dashboard/athlete',
  coach:           '/dashboard/coach',
  physiotherapist: '/dashboard/physiotherapist',
  sports_scientist:'/dashboard/scientist',
  admin:           '/dashboard/admin',
};

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [form, setForm] = useState({ email: '', password: '' });
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const from = location.state?.from?.pathname;

  function handleChange(e) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
    setError('');
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    try {
      const { data } = await api.post('/auth/login', form);
      const user = await login(data);
      const dest = from || ROLE_ROUTES[user.role] || '/dashboard/athlete';
      navigate(dest, { replace: true });
    } catch (err) {
      const msg = err.response?.data?.detail ?? 'Login failed. Please try again.';
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center px-4">
      {/* Ambient glow */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 -left-40 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl" />
        <div className="absolute -bottom-40 -right-40 w-96 h-96 bg-emerald-500/5 rounded-full blur-3xl" />
      </div>

      <div className="relative w-full max-w-md">
        {/* Logo */}
        <div className="flex items-center justify-center gap-2 mb-8">
          <div className="p-2 bg-emerald-500/10 rounded-xl border border-emerald-500/20">
            <Activity className="h-7 w-7 text-emerald-400" />
          </div>
          <span className="text-xl font-bold text-slate-100 tracking-tight">
            Injury<span className="text-emerald-400">Guard</span>
          </span>
        </div>

        {/* Card */}
        <div className="glass-card rounded-2xl p-8 shadow-2xl">
          <h1 className="text-2xl font-bold text-slate-100 mb-1">Welcome back</h1>
          <p className="text-sm text-slate-400 mb-7">Sign in to your account to continue</p>

          <form onSubmit={handleSubmit} className="space-y-5" id="login-form">
            {/* Email */}
            <div>
              <label htmlFor="login-email" className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                Email address
              </label>
              <input
                id="login-email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={form.email}
                onChange={handleChange}
                placeholder="you@example.com"
                className="w-full bg-slate-900/80 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500
                           focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/70 transition"
              />
            </div>

            {/* Password */}
            <div>
              <label htmlFor="login-password" className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                Password
              </label>
              <div className="relative">
                <input
                  id="login-password"
                  name="password"
                  type={showPw ? 'text' : 'password'}
                  autoComplete="current-password"
                  required
                  value={form.password}
                  onChange={handleChange}
                  placeholder="••••••••"
                  className="w-full bg-slate-900/80 border border-slate-700 rounded-xl px-4 py-2.5 pr-10 text-sm text-slate-100 placeholder-slate-500
                             focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/70 transition"
                />
                <button
                  type="button"
                  id="toggle-password-visibility"
                  onClick={() => setShowPw((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition"
                  aria-label={showPw ? 'Hide password' : 'Show password'}
                >
                  {showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            {/* Error */}
            {error && (
              <div id="login-error" className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
                {error}
              </div>
            )}

            {/* Submit */}
            <button
              id="login-submit"
              type="submit"
              disabled={isLoading}
              className="w-full flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-500
                         disabled:opacity-60 disabled:cursor-not-allowed rounded-xl px-4 py-2.5 text-sm font-semibold
                         text-white shadow-lg shadow-emerald-500/20 transition-all duration-200 active:scale-[0.98]"
            >
              {isLoading ? (
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"/>
                </svg>
              ) : (
                <LogIn className="h-4 w-4" />
              )}
              {isLoading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-500">
            Don't have an account?{' '}
            <Link to="/register" id="go-to-register" className="text-emerald-400 hover:text-emerald-300 font-medium transition">
              Create one
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
