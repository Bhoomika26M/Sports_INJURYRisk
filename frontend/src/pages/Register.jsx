import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Eye, EyeOff, UserPlus, Activity, CheckCircle2 } from 'lucide-react';
import api from '../api/axiosInstance';

const STRENGTH_RULES = [
  { label: 'At least 8 characters', test: (v) => v.length >= 8 },
  { label: 'Contains a number',      test: (v) => /\d/.test(v) },
  { label: 'Contains a letter',      test: (v) => /[a-zA-Z]/.test(v) },
];

function PasswordStrength({ password }) {
  const passed = STRENGTH_RULES.filter((r) => r.test(password)).length;
  const colors = ['bg-red-500', 'bg-amber-500', 'bg-emerald-500'];
  const labels = ['Weak', 'Fair', 'Strong'];

  if (!password) return null;
  return (
    <div className="mt-2 space-y-1.5">
      <div className="flex gap-1">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className={`h-1 flex-1 rounded-full transition-all duration-300 ${
              i < passed ? colors[passed - 1] : 'bg-slate-700'
            }`}
          />
        ))}
      </div>
      <p className={`text-xs ${passed < 2 ? 'text-red-400' : passed < 3 ? 'text-amber-400' : 'text-emerald-400'}`}>
        {labels[passed - 1] ?? 'Too short'}
      </p>
    </div>
  );
}

export default function Register() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ full_name: '', email: '', password: '', confirm: '' });
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  function handleChange(e) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
    setError('');
    setFieldErrors((prev) => ({ ...prev, [e.target.name]: '' }));
  }

  function validate() {
    const errs = {};
    if (!form.full_name.trim()) errs.full_name = 'Full name is required';
    if (!form.email) errs.email = 'Email is required';
    if (form.password.length < 8) errs.password = 'Password must be at least 8 characters';
    if (form.password !== form.confirm) errs.confirm = 'Passwords do not match';
    return errs;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length) { setFieldErrors(errs); return; }

    setIsLoading(true);
    setError('');
    try {
      await api.post('/auth/register', {
        full_name: form.full_name,
        email: form.email,
        password: form.password,
      });
      setSuccess(true);
      setTimeout(() => navigate('/login'), 1800);
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) {
        // Pydantic validation errors
        const map = {};
        detail.forEach((d) => {
          const field = d.loc?.[d.loc.length - 1];
          if (field) map[field] = d.msg;
        });
        setFieldErrors(map);
      } else {
        setError(typeof detail === 'string' ? detail : 'Registration failed. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center px-4 py-12">
      {/* Ambient glow */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl" />
        <div className="absolute bottom-0 left-0 w-80 h-80 bg-emerald-500/5 rounded-full blur-3xl" />
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

        <div className="glass-card rounded-2xl p-8 shadow-2xl">
          {success ? (
            <div className="flex flex-col items-center gap-4 py-6 text-center">
              <div className="p-3 bg-emerald-500/10 rounded-full border border-emerald-500/20">
                <CheckCircle2 className="h-10 w-10 text-emerald-400" />
              </div>
              <h2 className="text-xl font-bold text-slate-100">Account created!</h2>
              <p className="text-sm text-slate-400">Redirecting you to the login page…</p>
            </div>
          ) : (
            <>
              <h1 className="text-2xl font-bold text-slate-100 mb-1">Create an account</h1>
              <p className="text-sm text-slate-400 mb-7">
                Athletes register here. Staff accounts are created by an admin.
              </p>

              <form onSubmit={handleSubmit} className="space-y-5" id="register-form">
                {/* Full name */}
                <div>
                  <label htmlFor="reg-fullname" className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                    Full name
                  </label>
                  <input
                    id="reg-fullname"
                    name="full_name"
                    type="text"
                    autoComplete="name"
                    required
                    value={form.full_name}
                    onChange={handleChange}
                    placeholder="Jane Smith"
                    className={`w-full bg-slate-900/80 border ${fieldErrors.full_name ? 'border-red-500/60' : 'border-slate-700'} rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500
                               focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/70 transition`}
                  />
                  {fieldErrors.full_name && <p className="text-xs text-red-400 mt-1">{fieldErrors.full_name}</p>}
                </div>

                {/* Email */}
                <div>
                  <label htmlFor="reg-email" className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                    Email address
                  </label>
                  <input
                    id="reg-email"
                    name="email"
                    type="email"
                    autoComplete="email"
                    required
                    value={form.email}
                    onChange={handleChange}
                    placeholder="you@example.com"
                    className={`w-full bg-slate-900/80 border ${fieldErrors.email ? 'border-red-500/60' : 'border-slate-700'} rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500
                               focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/70 transition`}
                  />
                  {fieldErrors.email && <p className="text-xs text-red-400 mt-1">{fieldErrors.email}</p>}
                </div>

                {/* Password */}
                <div>
                  <label htmlFor="reg-password" className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                    Password
                  </label>
                  <div className="relative">
                    <input
                      id="reg-password"
                      name="password"
                      type={showPw ? 'text' : 'password'}
                      autoComplete="new-password"
                      required
                      value={form.password}
                      onChange={handleChange}
                      placeholder="••••••••"
                      className={`w-full bg-slate-900/80 border ${fieldErrors.password ? 'border-red-500/60' : 'border-slate-700'} rounded-xl px-4 py-2.5 pr-10 text-sm text-slate-100 placeholder-slate-500
                                 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/70 transition`}
                    />
                    <button
                      type="button"
                      id="toggle-reg-password"
                      onClick={() => setShowPw((v) => !v)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition"
                      aria-label={showPw ? 'Hide password' : 'Show password'}
                    >
                      {showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                  {fieldErrors.password && <p className="text-xs text-red-400 mt-1">{fieldErrors.password}</p>}
                  <PasswordStrength password={form.password} />
                </div>

                {/* Confirm password */}
                <div>
                  <label htmlFor="reg-confirm" className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                    Confirm password
                  </label>
                  <input
                    id="reg-confirm"
                    name="confirm"
                    type={showPw ? 'text' : 'password'}
                    autoComplete="new-password"
                    required
                    value={form.confirm}
                    onChange={handleChange}
                    placeholder="••••••••"
                    className={`w-full bg-slate-900/80 border ${fieldErrors.confirm ? 'border-red-500/60' : 'border-slate-700'} rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500
                               focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/70 transition`}
                  />
                  {fieldErrors.confirm && <p className="text-xs text-red-400 mt-1">{fieldErrors.confirm}</p>}
                </div>

                {/* Global error */}
                {error && (
                  <div id="register-error" className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
                    {error}
                  </div>
                )}

                {/* Submit */}
                <button
                  id="register-submit"
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
                    <UserPlus className="h-4 w-4" />
                  )}
                  {isLoading ? 'Creating account…' : 'Create account'}
                </button>
              </form>

              <p className="mt-6 text-center text-sm text-slate-500">
                Already have an account?{' '}
                <Link to="/login" id="go-to-login" className="text-emerald-400 hover:text-emerald-300 font-medium transition">
                  Sign in
                </Link>
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
