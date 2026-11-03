import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { 
  Eye, 
  EyeOff, 
  Activity, 
  ShieldAlert, 
  Award, 
  Stethoscope, 
  Microscope, 
  Key, 
  Mail, 
  Lock, 
  User as UserIcon, 
  AlertCircle,
  ArrowRight,
  Check,
  Sparkles
} from 'lucide-react';
import { GoogleAuthButton } from '../components/GoogleAuthButton';

const ROLES = [
  {
    id: 'athlete',
    title: 'Athlete',
    icon: Activity,
    description: 'Upload movement videos, track personal symmetry, and view risk scores.'
  },
  {
    id: 'coach',
    title: 'Coach',
    icon: Award,
    description: 'Monitor squad biomechanics, physical readiness, and flagged athletes.'
  },
  {
    id: 'physiotherapist',
    title: 'Physiotherapist',
    icon: Stethoscope,
    description: 'Review joint kinematics, movement anomalies, and recovery milestones.'
  },
  {
    id: 'sports_scientist',
    title: 'Sports Scientist',
    icon: Microscope,
    description: 'Analyze bilateral symmetry, angular velocities, and kinetic data.'
  },
  {
    id: 'administrator',
    title: 'Administrator',
    icon: ShieldAlert,
    description: 'Manage users, assign staff to athletes, and oversee system health.'
  }
];

export const Register = () => {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    full_name: '',
    role: 'athlete',
    admin_code: ''
  });
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  
  const { user, register } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (user) {
      navigate('/dashboard', { replace: true });
    }
  }, [user, navigate]);

  const getPasswordStrength = (pwd) => {
    if (!pwd) return { score: 0, label: '', color: 'bg-white/10' };
    let score = 0;
    if (pwd.length >= 6) score += 1;
    if (pwd.length >= 10) score += 1;
    if (/[0-9]/.test(pwd)) score += 1;
    if (/[^A-Za-z0-9]/.test(pwd)) score += 1;

    if (score <= 1) return { score: 25, label: 'Weak', color: 'bg-rose-500' };
    if (score === 2) return { score: 50, label: 'Fair', color: 'bg-amber-500' };
    if (score === 3) return { score: 75, label: 'Good', color: 'bg-purple-500' };
    return { score: 100, label: 'Strong', color: 'bg-emerald-400' };
  };

  const pwdStrength = getPasswordStrength(formData.password);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (formData.password !== formData.confirmPassword) {
      return setError('Passwords do not match');
    }
    if (formData.password.length < 6) {
      return setError('Password must be at least 6 characters long');
    }
    try {
      setError('');
      setSubmitting(true);
      const { confirmPassword: _confirmPassword, ...registerData } = formData;
      await register(registerData);
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed. Please check your information.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-65px)] flex items-center justify-center bg-[#050508] relative overflow-hidden p-4 sm:p-6 lg:p-8">
      {/* Background Ambient Glow */}
      <div className="absolute inset-0 bg-gradient-to-b from-purple-950/40 via-purple-900/25 to-[#050508] pointer-events-none" />
      <div className="absolute top-0 left-1/2 transform -translate-x-1/2 w-[110vh] h-[55vh] rounded-b-[50%] bg-purple-600/15 blur-[90px] pointer-events-none" />

      <div className="max-w-3xl w-full relative z-10 bg-[#0c0c16]/85 backdrop-blur-2xl rounded-3xl border border-white/10 shadow-[0_20px_50px_rgba(0,0,0,0.8)] overflow-hidden my-4">
        {/* Header */}
        <div className="p-6 sm:p-7 border-b border-white/10 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 bg-gradient-to-r from-purple-950/30 to-black/30">
          <div>
            <div className="flex items-center gap-2.5 mb-1.5">
              <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-purple-600 to-indigo-500 flex items-center justify-center text-white shadow-[0_0_15px_rgba(168,85,247,0.4)]">
                <Activity size={18} />
              </div>
              <span className="font-bold tracking-tight text-white text-base">Athleti<span className="text-purple-400">Q</span></span>
            </div>
            <h1 className="text-xl font-bold text-white">Create your account</h1>
            <p className="text-white/60 text-xs mt-0.5">Choose your role to get access to tailored biomechanical analytics</p>
          </div>
          <div className="text-xs">
            <span className="text-white/40">Already registered? </span>
            <Link to="/login" className="text-purple-400 hover:text-purple-300 font-semibold ml-1">
              Sign In &rarr;
            </Link>
          </div>
        </div>

        <div className="p-6 sm:p-8 space-y-6">
          {error && (
            <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs font-medium flex items-start gap-2.5">
              <AlertCircle size={16} className="shrink-0 mt-0.5 text-rose-400" />
              <div className="flex-1">{error}</div>
            </div>
          )}

          {/* Google OAuth Sign-Up */}
          <div>
            <GoogleAuthButton
              role={formData.role}
              onSuccess={() => navigate('/dashboard')}
              onError={(err) => setError(err)}
            />

            <div className="relative my-5 text-center">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-white/10" />
              </div>
              <span className="relative bg-[#0c0c16] px-3 text-[10px] font-bold uppercase tracking-wider text-white/40">
                Or fill out account details
              </span>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Step 1: Role Selection */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-purple-400 mb-2.5 flex items-center gap-1.5">
                <Sparkles size={13} />
                1. Select Your Role
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5">
                {ROLES.map((r) => {
                  const Icon = r.icon;
                  const isSelected = formData.role === r.id;
                  return (
                    <button
                      key={r.id}
                      type="button"
                      onClick={() => setFormData({ ...formData, role: r.id })}
                      className={`p-3 rounded-2xl border text-left transition relative flex flex-col justify-between ${
                        isSelected 
                          ? 'border-purple-500 bg-purple-950/40 shadow-[0_0_15px_rgba(168,85,247,0.25)] ring-1 ring-purple-500/40' 
                          : 'border-white/10 bg-white/[0.02] hover:border-white/20 hover:bg-white/[0.05]'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1.5">
                        <div className="flex items-center gap-2">
                          <Icon size={16} className={isSelected ? 'text-purple-400' : 'text-white/40'} />
                          <span className={`text-xs font-bold ${isSelected ? 'text-white' : 'text-white/80'}`}>
                            {r.title}
                          </span>
                        </div>
                        {isSelected && (
                          <div className="w-4 h-4 rounded-full bg-purple-500 text-white flex items-center justify-center shadow-[0_0_8px_rgba(168,85,247,0.6)]">
                            <Check size={10} strokeWidth={3} />
                          </div>
                        )}
                      </div>
                      <p className="text-[11px] text-white/50 leading-tight">{r.description}</p>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Administrator Passkey Requirement */}
            {formData.role === 'administrator' && (
              <div className="p-3.5 bg-rose-500/10 border border-rose-500/30 rounded-2xl">
                <div className="flex items-center gap-2 text-rose-300 font-bold text-xs mb-1.5">
                  <Key size={14} />
                  <span>Administrator Access Key Required</span>
                </div>
                <input
                  type="password"
                  value={formData.admin_code}
                  onChange={(e) => setFormData({ ...formData, admin_code: e.target.value })}
                  placeholder="Enter administrator security passkey"
                  required
                  className="w-full px-3 py-2 text-xs bg-white/5 border border-rose-500/30 rounded-xl text-white placeholder:text-white/30 focus:ring-2 focus:ring-rose-500/30 focus:outline-none"
                />
              </div>
            )}

            {/* Step 2: Account Details */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-purple-400 mb-2.5">
                2. Account Details
              </label>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                <div>
                  <label className="block text-xs font-semibold text-white/70 mb-1">Full Name</label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-white/40">
                      <UserIcon size={15} />
                    </div>
                    <input
                      type="text"
                      autoComplete="name"
                      value={formData.full_name}
                      onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                      placeholder="e.g. Alex Rivera"
                      required
                      className="w-full pl-10 pr-3 py-2 text-xs rounded-xl border border-white/10 bg-white/5 text-white placeholder:text-white/30 focus:outline-none focus:border-purple-500/50 focus:bg-white/10 focus:ring-2 focus:ring-purple-500/20 transition"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-white/70 mb-1">Email Address</label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-white/40">
                      <Mail size={15} />
                    </div>
                    <input
                      type="email"
                      autoComplete="email"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      placeholder="alex@team.com"
                      required
                      className="w-full pl-10 pr-3 py-2 text-xs rounded-xl border border-white/10 bg-white/5 text-white placeholder:text-white/30 focus:outline-none focus:border-purple-500/50 focus:bg-white/10 focus:ring-2 focus:ring-purple-500/20 transition"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-white/70 mb-1">Password</label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-white/40">
                      <Lock size={15} />
                    </div>
                    <input
                      type={showPassword ? 'text' : 'password'}
                      autoComplete="new-password"
                      value={formData.password}
                      onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                      placeholder="At least 6 characters"
                      required
                      className="w-full pl-10 pr-9 py-2 text-xs rounded-xl border border-white/10 bg-white/5 text-white placeholder:text-white/30 focus:outline-none focus:border-purple-500/50 focus:bg-white/10 focus:ring-2 focus:ring-purple-500/20 transition"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-white/40 hover:text-white"
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                    >
                      {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                    </button>
                  </div>
                  {formData.password && (
                    <div className="mt-1.5 flex items-center gap-2">
                      <div className="flex-1 bg-white/10 h-1 rounded-full overflow-hidden">
                        <div 
                          className={`h-full ${pwdStrength.color} transition-all duration-300`} 
                          style={{ width: `${pwdStrength.score}%` }} 
                        />
                      </div>
                      <span className="text-[10px] font-bold text-white/50 uppercase">{pwdStrength.label}</span>
                    </div>
                  )}
                </div>

                <div>
                  <label className="block text-xs font-semibold text-white/70 mb-1">Confirm Password</label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-white/40">
                      <Lock size={15} />
                    </div>
                    <input
                      type={showPassword ? 'text' : 'password'}
                      autoComplete="new-password"
                      value={formData.confirmPassword}
                      onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                      placeholder="Repeat password"
                      required
                      className="w-full pl-10 pr-3 py-2 text-xs rounded-xl border border-white/10 bg-white/5 text-white placeholder:text-white/30 focus:outline-none focus:border-purple-500/50 focus:bg-white/10 focus:ring-2 focus:ring-purple-500/20 transition"
                    />
                  </div>
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full bg-gradient-to-r from-purple-600 via-indigo-600 to-purple-600 hover:from-purple-500 hover:to-indigo-500 text-white font-semibold py-3 px-4 rounded-xl shadow-[0_0_20px_rgba(168,85,247,0.3)] transition duration-200 flex items-center justify-center gap-2 disabled:opacity-50 text-xs uppercase tracking-wider"
            >
              {submitting ? 'Creating account...' : `Register as ${ROLES.find(r => r.id === formData.role)?.title || 'User'}`}
              {!submitting && <ArrowRight size={15} />}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
export default Register;
