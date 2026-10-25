import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { 
  Eye, 
  EyeOff, 
  Activity, 
  Award, 
  Stethoscope, 
  Microscope, 
  ShieldAlert, 
  Mail, 
  Lock, 
  ArrowRight,
  ShieldCheck,
  AlertCircle
} from 'lucide-react';
import { GoogleAuthButton } from '../components/GoogleAuthButton';

const DEMO_ROLES = [
  { id: 'athlete', label: 'Athlete', email: 'demo_athlete@example.com', name: 'Demo Athlete', icon: Activity },
  { id: 'coach', label: 'Coach', email: 'demo_coach@example.com', name: 'Coach Vance', icon: Award },
  { id: 'physiotherapist', label: 'Physiotherapist', email: 'demo_physio@example.com', name: 'Dr. Sarah Physio', icon: Stethoscope },
  { id: 'sports_scientist', label: 'Sports Scientist', email: 'demo_scientist@example.com', name: 'Dr. Elena Biomechanics', icon: Microscope },
  { id: 'administrator', label: 'Administrator', email: 'demo_admin@example.com', name: 'System Admin', icon: ShieldAlert },
];

export const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  
  const { user, login, loginOAuth } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (user) {
      navigate('/dashboard', { replace: true });
    }
  }, [user, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setError('');
      setLoading(true);
      await login(email, password);
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid email or password. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickDemoLogin = async (demo) => {
    try {
      setError('');
      setLoading(true);
      await loginOAuth({
        provider: 'demo',
        email: demo.email,
        full_name: demo.name,
        role: demo.id
      });
    } catch (err) {
      setError(err.response?.data?.detail || `Failed to sign in as ${demo.label}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-65px)] flex items-center justify-center bg-slate-50 p-4 sm:p-6 lg:p-8">
      <div className="max-w-4xl w-full grid grid-cols-1 lg:grid-cols-12 rounded-2xl overflow-hidden shadow-xl border border-slate-200 bg-white">
        
        {/* Left Branding Panel */}
        <div className="hidden lg:flex lg:col-span-5 bg-slate-900 p-8 flex-col justify-between text-white">
          <div>
            <div className="flex items-center gap-2.5 mb-6">
              <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-md">
                <Activity size={22} />
              </div>
              <span className="text-xl font-bold tracking-tight">Athleti<span className="text-blue-500">Q</span></span>
            </div>

            <h1 className="text-2xl font-extrabold tracking-tight leading-snug mb-3">
              Movement Screening & Injury Risk Analytics
            </h1>
            <p className="text-slate-400 text-sm leading-relaxed mb-6">
              Computer vision and clinical biomechanics for athletes, coaches, and sports clinicians.
            </p>

            <div className="space-y-3 border-t border-slate-800 pt-6">
              <div className="flex items-center gap-3 text-xs text-slate-300">
                <div className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                <span>Automated joint angle and bilateral symmetry tracking</span>
              </div>
              <div className="flex items-center gap-3 text-xs text-slate-300">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                <span>Evidence-based clinical movement thresholds</span>
              </div>
              <div className="flex items-center gap-3 text-xs text-slate-300">
                <div className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
                <span>Actionable injury prevention recommendations</span>
              </div>
            </div>
          </div>

          <div className="pt-6 border-t border-slate-800/80 text-xs text-slate-400 flex items-center gap-2">
            <ShieldCheck size={16} className="text-emerald-400 shrink-0" />
            <span>Clinical screening tool &bull; Non-diagnostic</span>
          </div>
        </div>

        {/* Right Authentication Form Panel */}
        <div className="lg:col-span-7 p-6 sm:p-10 flex flex-col justify-between">
          <div>
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Sign in</h2>
              <p className="text-slate-500 text-sm mt-1">
                Enter your credentials or continue with Google to access your account.
              </p>
            </div>

            {error && (
              <div className="mb-5 p-3.5 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs font-medium flex items-start gap-2.5">
                <AlertCircle size={16} className="shrink-0 mt-0.5 text-red-600" />
                <span className="flex-1">{error}</span>
              </div>
            )}

            {/* Google Authentication */}
            <div className="mb-5">
              <GoogleAuthButton
                role="athlete"
                onSuccess={() => navigate('/dashboard')}
                onError={(err) => setError(err)}
              />

              <div className="relative my-5 text-center">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-slate-200" />
                </div>
                <span className="relative bg-white px-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Or continue with email
                </span>
              </div>
            </div>

            {/* Email & Password Form */}
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Email Address
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Mail size={16} />
                  </div>
                  <input
                    type="email"
                    autoComplete="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="name@organization.com"
                    required
                    className="w-full pl-10 pr-3.5 py-2.5 text-sm rounded-xl border border-slate-200 focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100 transition"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Password
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Lock size={16} />
                  </div>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter your password"
                    required
                    className="w-full pl-10 pr-10 py-2.5 text-sm rounded-xl border border-slate-200 focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100 transition"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-600 focus:outline-none"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full mt-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2.5 px-4 rounded-xl shadow-sm transition duration-150 flex items-center justify-center gap-2 disabled:opacity-50 text-sm"
              >
                {loading ? 'Signing in...' : 'Sign In'}
                {!loading && <ArrowRight size={15} />}
              </button>
            </form>
          </div>

          {/* Quick Demo Access Bar */}
          <div className="mt-8 pt-5 border-t border-slate-100">
            <div className="text-center mb-2.5">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                Quick Demo Access
              </span>
            </div>
            <div className="flex flex-wrap gap-1.5 justify-center">
              {DEMO_ROLES.map((demo) => {
                const Icon = demo.icon;
                return (
                  <button
                    key={demo.id}
                    type="button"
                    onClick={() => handleQuickDemoLogin(demo)}
                    disabled={loading}
                    className="text-xs px-2.5 py-1 rounded-lg border border-slate-200 bg-slate-50 hover:bg-blue-50 hover:border-blue-300 text-slate-700 hover:text-blue-700 font-medium flex items-center gap-1.5 transition disabled:opacity-50"
                    title={`Log in as ${demo.label}`}
                  >
                    <Icon size={13} className="text-slate-500" />
                    <span>{demo.label}</span>
                  </button>
                );
              })}
            </div>

            <p className="mt-5 text-center text-xs text-slate-500">
              Don't have an account?{' '}
              <Link to="/register" className="text-blue-600 font-semibold hover:underline">
                Create an account
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
