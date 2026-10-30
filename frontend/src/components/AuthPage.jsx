import React, { useEffect, useRef, useState } from 'react';
import { Activity, ArrowRight, CheckCircle2, LockKeyhole, Mail, UserRound } from 'lucide-react';
import { api } from '../api/client';

export default function AuthPage({ onClose, onAuthSuccess, initialMode = 'login', initialToken = '' }) {
  const [mode, setMode] = useState(initialMode);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [token, setToken] = useState(initialToken);
  const [newPassword, setNewPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const callbacks = useRef({ onClose, onAuthSuccess });
  callbacks.current = { onClose, onAuthSuccess };

  useEffect(() => {
    setMode(initialMode);
    setToken(initialToken);
  }, [initialMode, initialToken]);

  useEffect(() => {
    setError('');
    setNotice('');
  }, [mode]);

  const changeMode = (next) => {
    const route = next === 'forgot' ? '/forgot-password' : next === 'reset' ? '/reset-password' : next === 'register' ? '/register' : '/sign-in';
    window.history.pushState({}, '', route);
    setMode(next);
  };

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError('');
    setNotice('');
    try {
      if (mode === 'login') {
        const result = await api.login(email, password);
        onAuthSuccess(result.user);
        onClose();
      } else if (mode === 'register') {
        await api.register({ email, password, full_name: fullName, role: 'athlete' });
        const result = await api.login(email, password);
        onAuthSuccess(result.user);
        onClose();
      } else if (mode === 'forgot') {
        const result = await api.forgotPassword(email);
        setNotice(result.message);
      } else {
        const result = await api.resetPassword(token, newPassword);
        setNotice(result.message);
        window.setTimeout(() => changeMode('login'), 1800);
      }
    } catch (err) {
      setError(err.message || 'Please try again.');
    } finally {
      setBusy(false);
    }
  };

  const title = { login: 'Welcome back', register: 'Create your account', forgot: 'Reset your password', reset: 'Choose a new password' }[mode];
  const desc = {
    login: 'Sign in to your movement analysis workspace.',
    register: 'Create an athlete account to get started.',
    forgot: 'If your account exists and email delivery is configured, we will send a secure reset link.',
    reset: 'Reset links expire after 15 minutes and can be used once.',
  }[mode];

  return (
    <main className="min-h-screen bg-slate-100 px-4 py-8 sm:px-8 lg:grid lg:grid-cols-[minmax(0,1fr)_minmax(360px,460px)] lg:items-center lg:gap-12 lg:px-16">
      <section className="mx-auto hidden w-full max-w-xl lg:block">
        <div className="mb-14 flex items-center gap-3 text-left select-none">
          <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-teal-800 text-white"><Activity className="h-6 w-6" /></span>
          <span><b className="block text-xl text-slate-900">Kinematix</b><small className="text-slate-500">Sports movement analysis</small></span>
        </div>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-teal-800">Movement intelligence</p>
        <h1 className="mt-4 text-5xl font-semibold leading-tight tracking-tight text-slate-950">See how athletes move.<br />Understand what to improve.</h1>
        <p className="mt-6 max-w-lg text-lg leading-8 text-slate-600">Review movement videos, pose tracking and biomechanical measures in one workspace.</p>
      </section>

      <section className="mx-auto w-full max-w-md">
        <div className="mb-6 flex items-center justify-between lg:hidden select-none">
          <b className="flex items-center gap-2 text-slate-900"><Activity className="h-5 w-5 text-teal-800" />Kinematix</b>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-lg sm:p-8">
          <h2 className="text-2xl font-semibold tracking-tight text-slate-950">{title}</h2>
          <p className="mt-2 text-sm text-slate-600">{desc}</p>

          <div className="my-6 flex rounded-xl bg-slate-100 p-1">
            <button type="button" onClick={() => changeMode('login')} className={`flex-1 rounded-lg px-3 py-2 text-sm font-medium ${mode === 'login' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600'}`}>Sign in</button>
            <button type="button" onClick={() => changeMode('register')} className={`flex-1 rounded-lg px-3 py-2 text-sm font-medium ${mode === 'register' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600'}`}>Create account</button>
          </div>

          {error && <div role="alert" className="mb-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2.5 text-sm text-rose-800">{error}</div>}
          {notice && <div role="status" className="mb-4 flex items-start gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2.5 text-sm text-emerald-900"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />{notice}</div>}

          <form onSubmit={submit} className="space-y-4">
            {mode === 'register' && <label className="block text-sm font-medium text-slate-700">Full name<div className="relative mt-1.5"><UserRound className="absolute left-3 top-3 h-4 w-4 text-slate-400" /><input required autoComplete="name" value={fullName} onChange={(e) => setFullName(e.target.value)} className="w-full rounded-lg border border-slate-300 py-2.5 pl-10 pr-3 text-sm text-slate-900 outline-none focus:border-teal-700" placeholder="Your name" /></div></label>}
            {mode !== 'reset' && <label className="block text-sm font-medium text-slate-700">Email address<div className="relative mt-1.5"><Mail className="absolute left-3 top-3 h-4 w-4 text-slate-400" /><input type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} className="w-full rounded-lg border border-slate-300 py-2.5 pl-10 pr-3 text-sm text-slate-900 outline-none focus:border-teal-700" placeholder="you@example.com" /></div></label>}
            {mode === 'login' && <label className="block text-sm font-medium text-slate-700">Password<div className="relative mt-1.5"><LockKeyhole className="absolute left-3 top-3 h-4 w-4 text-slate-400" /><input type="password" required autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} className="w-full rounded-lg border border-slate-300 py-2.5 pl-10 pr-3 text-sm text-slate-900 outline-none focus:border-teal-700" placeholder="Enter your password" /></div></label>}
            {mode === 'register' && <label className="block text-sm font-medium text-slate-700">Password<div className="relative mt-1.5"><LockKeyhole className="absolute left-3 top-3 h-4 w-4 text-slate-400" /><input type="password" required minLength={8} autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} className="w-full rounded-lg border border-slate-300 py-2.5 pl-10 pr-3 text-sm text-slate-900 outline-none focus:border-teal-700" placeholder="At least 8 characters" /></div></label>}
            {mode === 'reset' && <><label className="block text-sm font-medium text-slate-700">New password<div className="relative mt-1.5"><LockKeyhole className="absolute left-3 top-3 h-4 w-4 text-slate-400" /><input type="password" required minLength={8} autoComplete="new-password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} className="w-full rounded-lg border border-slate-300 py-2.5 pl-10 pr-3 text-sm text-slate-900 outline-none focus:border-teal-700" placeholder="At least 8 characters" /></div></label><label className="block text-sm font-medium text-slate-700">Reset token<div className="relative mt-1.5"><LockKeyhole className="absolute left-3 top-3 h-4 w-4 text-slate-400" /><input required value={token} onChange={(e) => setToken(e.target.value)} className="w-full rounded-lg border border-slate-300 py-2.5 pl-10 pr-3 text-sm text-slate-900 outline-none focus:border-teal-700" placeholder="Token from your reset email" /></div></label></>}
            {mode === 'login' && <button type="button" onClick={() => changeMode('forgot')} className="-mt-1 text-sm font-medium text-teal-800 hover:underline">Forgot password?</button>}
            <button type="submit" disabled={busy} className="flex w-full items-center justify-center gap-2 rounded-lg bg-teal-800 px-4 py-3 text-sm font-semibold text-white transition hover:bg-teal-900 disabled:cursor-wait disabled:opacity-60">{busy ? 'Please wait...' : mode === 'login' ? 'Sign in' : mode === 'register' ? 'Create account' : mode === 'forgot' ? 'Send reset link' : 'Update password'}{!busy && <ArrowRight className="h-4 w-4" />}</button>
          </form>

          {mode === 'login' && import.meta.env.DEV && (
            <div className="mt-5 rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
              <b className="text-slate-800">Demo login:</b> athlete@sportsai.com / password123
            </div>
          )}

          {mode !== 'login' && <button type="button" onClick={() => changeMode('login')} className="mt-5 w-full text-center text-sm font-medium text-teal-800 hover:underline">Return to sign in</button>}
        </div>
        <p className="mt-5 text-center text-xs text-slate-500">Movement-analysis results are informational and are not a medical diagnosis.</p>
      </section>
    </main>
  );
}
