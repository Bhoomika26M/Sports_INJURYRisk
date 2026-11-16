import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { authAPI } from '../services/api';

const RESEND_SECONDS = 60;

const extractError = (err, fallback) => {
  const detail = err.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((e) => e.msg).join(', ');
  if (detail && typeof detail === 'object') return detail.msg || fallback;
  return fallback;
};

const ForgotPassword = () => {
  const navigate = useNavigate();

  const [step, setStep] = useState('email'); // 'email' | 'reset'
  const [email, setEmail] = useState('');
  const [otp, setOtp] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [cooldown, setCooldown] = useState(0);

  const timerRef = useRef(null);

  useEffect(() => () => clearInterval(timerRef.current), []);

  const startCooldown = () => {
    setCooldown(RESEND_SECONDS);
    clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      setCooldown((s) => {
        if (s <= 1) {
          clearInterval(timerRef.current);
          return 0;
        }
        return s - 1;
      });
    }, 1000);
  };

  const requestCode = async (e) => {
    if (e) e.preventDefault();
    setError('');
    setLoading(true);
    try {
      // Always returns the same generic response (no account enumeration).
      await authAPI.forgotPassword({ email });
      setMessage(
        'If an account exists for that email, a 6-digit verification code has been sent. It expires in 5 minutes.'
      );
      setStep('reset');
      startCooldown();
    } catch (err) {
      setError(extractError(err, 'Could not send the verification code. Please try again.'));
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    if (cooldown > 0) return;
    setError('');
    setLoading(true);
    try {
      await authAPI.forgotPassword({ email });
      setMessage('A new verification code has been sent if the account exists.');
      startCooldown();
    } catch (err) {
      setError(extractError(err, 'Could not resend the code. Please try again.'));
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async (e) => {
    e.preventDefault();
    setError('');

    if (otp.length !== 6 || !/^\d{6}$/.test(otp)) {
      setError('Enter the 6-digit verification code from the email.');
      return;
    }
    if (newPassword.length < 8) {
      setError('New password must be at least 8 characters long.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setLoading(true);
    try {
      await authAPI.resetPassword({ email, otp, new_password: newPassword });
      // Clear sensitive state before leaving the page.
      setOtp('');
      setNewPassword('');
      setConfirmPassword('');
      navigate('/login', { replace: true, state: { notice: 'Password reset. Please sign in.' } });
    } catch (err) {
      // Deliberately do not reveal which part failed.
      setError(extractError(err, 'Invalid or expired verification code.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-display font-bold text-text-primary">
            Reset your password
          </h2>
          <p className="mt-2 text-center text-sm text-text-secondary">
            {step === 'email'
              ? 'Enter your email and we will send you a verification code.'
              : 'Enter the code from your email and choose a new password.'}
          </p>
        </div>

        {error && (
          <div className="bg-error-light border border-error text-error px-4 py-3 rounded" role="alert">
            {error}
          </div>
        )}
        {message && step === 'reset' && (
          <div className="bg-amber-50 border border-amber-200 text-amber-900 px-4 py-3 rounded">
            {message}
          </div>
        )}

        {step === 'email' ? (
          <form className="mt-8 space-y-6" onSubmit={requestCode}>
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-text-primary">
                Email address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                required
                autoComplete="email"
                className="input-field w-full mt-1"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div>
              <button
                type="submit"
                disabled={loading}
                className="btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Sending...' : 'Send verification code'}
              </button>
            </div>
          </form>
        ) : (
          <form className="mt-8 space-y-6" onSubmit={handleReset}>
            <div>
              <label htmlFor="otp" className="block text-sm font-medium text-text-primary">
                Verification code
              </label>
              <input
                id="otp"
                name="otp"
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={6}
                required
                className="input-field w-full mt-1 tracking-[0.5em] text-center font-mono font-bold"
                placeholder="000000"
                value={otp}
                onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
              />
            </div>

            <div>
              <label htmlFor="newPassword" className="block text-sm font-medium text-text-primary">
                New password
              </label>
              <input
                id="newPassword"
                name="newPassword"
                type="password"
                autoComplete="new-password"
                required
                minLength={8}
                className="input-field w-full mt-1"
                placeholder="At least 8 characters"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
              />
            </div>

            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-text-primary">
                Confirm new password
              </label>
              <input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                autoComplete="new-password"
                required
                minLength={8}
                className="input-field w-full mt-1"
                placeholder="Re-enter new password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
              />
            </div>

            <div>
              <button
                type="submit"
                disabled={loading}
                className="btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Resetting...' : 'Reset password'}
              </button>
            </div>

            <div className="text-center text-sm">
              <button
                type="button"
                onClick={handleResend}
                disabled={cooldown > 0 || loading}
                className="text-primary hover:text-primary-hover font-medium disabled:text-text-muted disabled:cursor-not-allowed"
              >
                {cooldown > 0 ? `Resend code in ${cooldown}s` : 'Resend code'}
              </button>
            </div>
          </form>
        )}

        <div className="text-center">
          <Link to="/login" className="text-primary hover:text-primary-hover text-sm font-medium">
            Back to sign in
          </Link>
        </div>
      </div>
    </div>
  );
};

export default ForgotPassword;
