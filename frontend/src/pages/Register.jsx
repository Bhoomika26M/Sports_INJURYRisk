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
  Check
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
    if (!pwd) return { score: 0, label: '', color: 'bg-slate-200' };
    let score = 0;
    if (pwd.length >= 6) score += 1;
    if (pwd.length >= 10) score += 1;
    if (/[0-9]/.test(pwd)) score += 1;
    if (/[^A-Za-z0-9]/.test(pwd)) score += 1;

    if (score <= 1) return { score: 25, label: 'Weak', color: 'bg-rose-500' };
    if (score === 2) return { score: 50, label: 'Fair', color: 'bg-amber-500' };
    if (score === 3) return { score: 75, label: 'Good', color: 'bg-blue-500' };
    return { score: 100, label: 'Strong', color: 'bg-emerald-500' };
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
    <div className="min-h-[calc(100vh-65px)] flex items-center justify-center bg-slate-50 p-4 sm:p-6 lg:p-8">
      <div className="max-w-3xl w-full bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden my-4">
        {/* Header */}
        <div className="bg-slate-900 text-white p-6 sm:p-7 border-b border-slate-800 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <div className="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center text-white">
                <Activity size={16} />
              </div>
              <span className="font-bold tracking-tight text-white text-base">Athleti<span className="text-blue-400">Q</span></span>
            </div>
            <h1 className="text-xl font-bold">Create your account</h1>
            <p className="text-slate-400 text-xs mt-0.5">Choose your role to get access to tailored tools and analytics</p>
          </div>
          <div className="text-xs">
            <span className="text-slate-400">Already registered? </span>
            <Link to="/login" className="text-blue-400 hover:text-blue-300 font-semibold ml-1">
              Sign In &rarr;
            </Link>
          </div>
        </div>

        <div className="p-6 sm:p-8">
          {error && (
            <div className="mb-5 p-3.5 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs font-medium flex items-start gap-2.5">
              <AlertCircle size={16} className="shrink-0 mt-0.5 text-red-600" />
              <div className="flex-1">{error}</div>
            </div>
          )}

          {/* Google OAuth Sign-Up */}
          <div className="mb-6">
            <GoogleAuthButton
              role={formData.role}
              onSuccess={() => navigate('/dashboard')}
              onError={(err) => setError(err)}
            />

            <div className="relative my-5 text-center">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-slate-200" />
              </div>
              <span className="relative bg-white px-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
                Or fill out account details
              </span>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Step 1: Role Selection */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
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
                      className={`p-3 rounded-xl border text-left transition relative flex flex-col justify-between ${
                        isSelected 
                          ? 'border-blue-600 bg-blue-50/50 shadow-sm ring-1 ring-blue-500/30' 
                          : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
                          <Icon size={16} className={isSelected ? 'text-blue-600' : 'text-slate-500'} />
                          <span className={`text-xs font-bold ${isSelected ? 'text-blue-900' : 'text-slate-800'}`}>
                            {r.title}
                          </span>
                        </div>
                        {isSelected && (
                          <div className="w-4 h-4 rounded-full bg-blue-600 text-white flex items-center justify-center">
                            <Check size={10} strokeWidth={3} />
                          </div>
                        )}
                      </div>
                      <p className="text-[11px] text-slate-500 leading-tight">{r.description}</p>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Administrator Passkey Requirement */}
            {formData.role === 'administrator' && (
              <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl">
                <div className="flex items-center gap-2 text-rose-900 font-bold text-xs mb-1">
                  <Key size={14} />
                  <span>Administrator Access Key Required</span>
                </div>
                <input
                  type="password"
                  value={formData.admin_code}
                  onChange={(e) => setFormData({ ...formData, admin_code: e.target.value })}
                  placeholder="Enter administrator security passkey"
                  required
                  className="w-full px-3 py-2 text-xs bg-white border border-rose-300 rounded-lg focus:ring-2 focus:ring-rose-500 focus:outline-none"
                />
              </div>
            )}

            {/* Step 2: Account Details */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
                2. Account Details
              </label>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Full Name</label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                      <UserIcon size={15} />
                    </div>
                    <input
                      type="text"
                      autoComplete="name"
                      value={formData.full_name}
                      onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                      placeholder="e.g. Alex Rivera"
                      required
                      className="w-full pl-9 pr-3 py-2 text-xs rounded-xl border border-slate-200 focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100 transition"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Email Address</label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                      <Mail size={15} />
                    </div>
                    <input
                      type="email"
                      autoComplete="email"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      placeholder="alex@team.com"
                      required
                      className="w-full pl-9 pr-3 py-2 text-xs rounded-xl border border-slate-200 focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100 transition"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Password</label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                      <Lock size={15} />
                    </div>
                    <input
                      type={showPassword ? 'text' : 'password'}
                      autoComplete="new-password"
                      value={formData.password}
                      onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                      placeholder="At least 6 characters"
                      required
                      className="w-full pl-9 pr-9 py-2 text-xs rounded-xl border border-slate-200 focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100 transition"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600"
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                    >
                      {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                    </button>
                  </div>
                  {formData.password && (
                    <div className="mt-1 flex items-center gap-2">
                      <div className="flex-1 bg-slate-100 h-1 rounded-full overflow-hidden">
                        <div 
                          className={`h-full ${pwdStrength.color} transition-all duration-300`} 
                          style={{ width: `${pwdStrength.score}%` }} 
                        />
                      </div>
                      <span className="text-[10px] font-bold text-slate-400 uppercase">{pwdStrength.label}</span>
                    </div>
                  )}
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Confirm Password</label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                      <Lock size={15} />
                    </div>
                    <input
                      type={showPassword ? 'text' : 'password'}
                      autoComplete="new-password"
                      value={formData.confirmPassword}
                      onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                      placeholder="Repeat password"
                      required
                      className="w-full pl-9 pr-3 py-2 text-xs rounded-xl border border-slate-200 focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100 transition"
                    />
                  </div>
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2.5 px-4 rounded-xl shadow-sm transition duration-150 flex items-center justify-center gap-2 disabled:opacity-50 text-sm"
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
