import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import GoogleSignInButton from '../components/GoogleSignInButton';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const notice = location.state?.notice;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(email, password);
      navigate('/dashboard');
    } catch (err) {
      // Handle error - could be string or object
      const errorDetail = err.response?.data?.detail;
      if (typeof errorDetail === 'string') {
        setError(errorDetail);
      } else if (Array.isArray(errorDetail)) {
        setError(errorDetail.map(e => e.msg).join(', '));
      } else if (typeof errorDetail === 'object') {
        setError(errorDetail.msg || 'Login failed');
      } else {
        setError('Login failed');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F9F9FF] text-[#141B2B] flex flex-col justify-between relative overflow-hidden py-8 px-4 sm:px-6 lg:px-8">
      {/* Background ambient gradient glow */}
      <div className="absolute -top-32 -left-24 w-96 h-96 rounded-full bg-[#BD4006]/10 blur-3xl pointer-events-none" />
      <div className="absolute -bottom-36 -right-20 w-[28rem] h-[28rem] rounded-full bg-[#6CF8BB]/20 blur-3xl pointer-events-none" />

      <div className="w-full max-w-xl mx-auto flex flex-col gap-4 relative z-10 my-auto">
        {/* Laboratory Status Bar Strip */}
        <div className="w-full bg-[#E1E8FD]/80 rounded-lg px-3.5 py-1.5 flex items-center justify-between shadow-sm border border-[#E1BFB5]/30">
          <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-wider text-[#594139]">
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#006C49] opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-[#006C49]" />
            </span>
            <span>Node 04 // Optical Telemetry Gate</span>
          </div>
          <div className="flex items-center gap-1 font-mono text-[10px] text-[#006C49] font-bold">
            <span>120Hz CALIBRATED</span>
          </div>
        </div>

        {/* Main Login Card */}
        <div className="w-full bg-white rounded-2xl shadow-xl border border-gray-100 p-6 sm:p-8 flex flex-col gap-6">
          {/* Identity Header */}
          <div className="flex flex-col items-center text-center gap-1">
            <div className="w-12 h-12 rounded-xl bg-[#FFDBCF] text-[#BD4006] flex items-center justify-center font-display font-bold text-2xl shadow-sm mb-1">
              K
            </div>
            <span className="font-mono text-[11px] uppercase tracking-widest text-[#BD4006] font-bold">
              Biomechanical Risk Engine v4.2
            </span>
            <h1 className="font-display text-2xl sm:text-3xl font-bold text-[#141B2B] tracking-tight">
              Sign in to Telemetry Hub
            </h1>
            <p className="text-xs sm:text-sm text-[#594139] max-w-sm mt-0.5">
              AI-Powered Movement Analysis & Real-time Biomechanics for High-Performance Athletics
            </p>
          </div>

          {/* Rapid Sandbox Personas */}
          <div className="w-full bg-[#F1F3FF] rounded-xl p-3 flex flex-col gap-1.5 border border-[#E9EDFF]">
            <div className="flex items-center justify-between px-1">
              <span className="font-mono text-[11px] uppercase tracking-wider text-[#594139] font-bold flex items-center gap-1">
                ⚡ Rapid Sandbox Personas
              </span>
              <span className="text-[10px] text-[#006C49] font-semibold">1-Click Sign In</span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-1.5">
              <button
                type="button"
                onClick={async () => {
                  setEmail('admin@athletics.org');
                  setPassword('password123');
                  setError('');
                  setLoading(true);
                  try {
                    await login('admin@athletics.org', 'password123');
                    navigate('/dashboard');
                  } catch (err) {
                    setError('Quick sign in failed');
                  } finally {
                    setLoading(false);
                  }
                }}
                className="p-2 rounded-lg text-left bg-white hover:bg-gray-50 border border-red-200 shadow-sm transition-all text-xs flex flex-col justify-between"
              >
                <div className="font-mono font-bold text-[#BD4006]">Admin</div>
                <div className="text-[10px] text-gray-500 truncate">System Admin</div>
              </button>

              <button
                type="button"
                onClick={async () => {
                  setEmail('coach@athletics.org');
                  setPassword('password123');
                  setError('');
                  setLoading(true);
                  try {
                    await login('coach@athletics.org', 'password123');
                    navigate('/dashboard');
                  } catch (err) {
                    setError('Quick sign in failed');
                  } finally {
                    setLoading(false);
                  }
                }}
                className="p-2 rounded-lg text-left bg-white hover:bg-gray-50 border border-gray-200 shadow-sm transition-all text-xs flex flex-col justify-between"
              >
                <div className="font-mono font-bold text-[#059669]">Coach</div>
                <div className="text-[10px] text-gray-500 truncate">Coach Miller</div>
              </button>

              <button
                type="button"
                onClick={async () => {
                  setEmail('physio@athletics.org');
                  setPassword('password123');
                  setError('');
                  setLoading(true);
                  try {
                    await login('physio@athletics.org', 'password123');
                    navigate('/dashboard');
                  } catch (err) {
                    setError('Quick sign in failed');
                  } finally {
                    setLoading(false);
                  }
                }}
                className="p-2 rounded-lg text-left bg-white hover:bg-gray-50 border border-gray-200 shadow-sm transition-all text-xs flex flex-col justify-between"
              >
                <div className="font-mono font-bold text-[#7C3AED]">Physio</div>
                <div className="text-[10px] text-gray-500 truncate">Dr. Sarah Lin</div>
              </button>

              <button
                type="button"
                onClick={async () => {
                  setEmail('scientist@biomech.lab');
                  setPassword('password123');
                  setError('');
                  setLoading(true);
                  try {
                    await login('scientist@biomech.lab', 'password123');
                    navigate('/dashboard');
                  } catch (err) {
                    setError('Quick sign in failed');
                  } finally {
                    setLoading(false);
                  }
                }}
                className="p-2 rounded-lg text-left bg-white hover:bg-gray-50 border border-gray-200 shadow-sm transition-all text-xs flex flex-col justify-between"
              >
                <div className="font-mono font-bold text-[#D97706]">Scientist</div>
                <div className="text-[10px] text-gray-500 truncate">Dr. Thorne</div>
              </button>

              <button
                type="button"
                onClick={async () => {
                  setEmail('athlete@athletics.org');
                  setPassword('password123');
                  setError('');
                  setLoading(true);
                  try {
                    await login('athlete@athletics.org', 'password123');
                    navigate('/dashboard');
                  } catch (err) {
                    setError('Quick sign in failed');
                  } finally {
                    setLoading(false);
                  }
                }}
                className="p-2 rounded-lg text-left bg-white hover:bg-gray-50 border border-gray-200 shadow-sm transition-all text-xs flex flex-col justify-between"
              >
                <div className="font-mono font-bold text-[#1C1613]">Athlete</div>
                <div className="text-[10px] text-gray-500 truncate">Marcus Vance</div>
              </button>
            </div>
          </div>

          <form className="space-y-4" onSubmit={handleSubmit}>
            {notice && !error && (
              <div className="bg-[#ECFDF5] border border-[#10B981] text-[#065F46] text-xs px-3.5 py-2.5 rounded-lg">
                {notice}
              </div>
            )}
            {error && (
              <div className="bg-[#FFDAD6] border border-[#BA1A1A] text-[#93000A] text-xs px-3.5 py-2.5 rounded-lg">
                {error}
              </div>
            )}

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-[#141B2B] mb-1" htmlFor="email">
                  Institutional Email Address
                </label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  required
                  className="input-field w-full text-sm"
                  placeholder="coach.miller@athletics.org"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="block text-xs font-semibold uppercase tracking-wider text-[#141B2B]" htmlFor="password">
                    Security Password
                  </label>
                  <Link to="/forgot-password" className="text-xs text-[#BD4006] hover:text-[#A33605] font-medium">
                    Forgot password?
                  </Link>
                </div>
                <input
                  id="password"
                  name="password"
                  type="password"
                  required
                  className="input-field w-full text-sm"
                  placeholder="••••••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
            </div>

            <div>
              <button
                type="submit"
                disabled={loading}
                className="btn-primary w-full py-2.5 shadow-md flex items-center justify-center gap-2 font-display text-base"
              >
                {loading ? 'Authenticating...' : 'Sign In to Telemetry'}
              </button>
            </div>

            <div className="relative my-3">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-200" />
              </div>
              <div className="relative flex justify-center text-xs">
                <span className="px-2 bg-white text-[#594139] uppercase tracking-wider font-mono text-[10px]">
                  Federated Identity
                </span>
              </div>
            </div>

            <GoogleSignInButton next="/dashboard" />

            <div className="text-center pt-2">
              <Link to="/register" className="text-xs text-[#BD4006] hover:text-[#A33605] font-semibold">
                Don't have an athlete/coach account? Register here →
              </Link>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default Login;
