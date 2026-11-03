import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion, AnimatePresence, useMotionValue, useTransform } from 'framer-motion';
import { 
  Mail, 
  Lock, 
  Eye, 
  EyeOff, 
  ArrowRight, 
  Activity, 
  Award, 
  Stethoscope, 
  ShieldAlert,
  AlertCircle,
  Sparkles
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { GoogleAuthButton } from '../components/GoogleAuthButton';
import { cn } from "@/lib/utils";

const DEMO_ROLES = [
  { id: 'coach', label: 'Coach Miller', email: 'coach.miller@athletics.org', password: 'Coach123!', icon: Award, desc: 'Assigned squad view' },
  { id: 'athlete', label: 'Marcus (Athlete)', email: 'marcus.vance@athletics.org', password: 'Athlete123!', icon: Activity, desc: 'Jump trial & risk' },
  { id: 'physiotherapist', label: 'Dr. Chen (Physio)', email: 'dr.chen@sportsmed.org', password: 'Physio123!', icon: Stethoscope, desc: 'Rehab protocols' },
  { id: 'administrator', label: 'Admin', email: 'admin@athletiq.com', password: 'Admin123!', icon: ShieldAlert, desc: 'Full system control' },
];

function Input({ className, type, ...props }) {
  return (
    <input
      type={type}
      className={cn(
        "flex h-10 w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-white/30 outline-none transition-all duration-300",
        "focus:border-purple-500/50 focus:bg-white/10 focus:ring-2 focus:ring-purple-500/20",
        className
      )}
      {...props}
    />
  );
}

export const Login = () => {
  const [showPassword, setShowPassword] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [focusedInput, setFocusedInput] = useState(null);
  const [rememberMe, setRememberMe] = useState(false);

  const { user, login, loginOAuth } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (user) {
      navigate('/dashboard', { replace: true });
    }
  }, [user, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password) {
      setError("Please enter both email and password.");
      return;
    }
    try {
      setError("");
      setIsLoading(true);
      await login(email, password);
    } catch (err) {
      setError(err.response?.data?.detail || "Invalid email or password. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickFill = async (demo) => {
    setEmail(demo.email);
    setPassword(demo.password);
    try {
      setError("");
      setIsLoading(true);
      await login(demo.email, demo.password);
    } catch (_err) {
      // Fallback to oauth/demo token if password fails
      try {
        await loginOAuth({
          provider: 'demo',
          email: demo.email,
          full_name: demo.label,
          role: demo.id
        });
      } catch (innerErr) {
        setError(innerErr.response?.data?.detail || `Failed to sign in as ${demo.label}`);
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-65px)] w-full bg-[#050508] relative overflow-hidden flex items-center justify-center p-4 sm:p-6 lg:p-8">
      {/* Background gradient effect - vibrant dark purple & obsidian */}
      <div className="absolute inset-0 bg-gradient-to-b from-purple-950/40 via-purple-900/30 to-[#050508]" />

      {/* Subtle noise texture overlay */}
      <div 
        className="absolute inset-0 opacity-[0.03] mix-blend-soft-light pointer-events-none" 
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`,
          backgroundSize: '200px 200px'
        }}
      />

      {/* Top radial ambient glow */}
      <div className="absolute top-0 left-1/2 transform -translate-x-1/2 w-[120vh] h-[60vh] rounded-b-[50%] bg-purple-600/15 blur-[90px] pointer-events-none" />
      <motion.div 
        className="absolute top-0 left-1/2 transform -translate-x-1/2 w-[90vh] h-[50vh] rounded-b-full bg-purple-500/20 blur-[70px] pointer-events-none"
        animate={{ 
          opacity: [0.15, 0.35, 0.15],
          scale: [0.97, 1.03, 0.97]
        }}
        transition={{ 
          duration: 7, 
          repeat: Infinity,
          repeatType: "mirror"
        }}
      />

      {/* Animated glow spots */}
      <div className="absolute left-1/4 top-1/4 w-80 h-80 bg-purple-500/10 rounded-full blur-[100px] animate-pulse pointer-events-none" />
      <div className="absolute right-1/4 bottom-1/4 w-80 h-80 bg-indigo-500/10 rounded-full blur-[100px] animate-pulse delay-1000 pointer-events-none" />

      {/* Static Sign-in Card Container */}
      <div className="w-full max-w-md relative z-10">
        <div className="relative group">
            {/* Card glow effect */}
            <motion.div 
              className="absolute -inset-[1px] rounded-3xl opacity-0 group-hover:opacity-80 transition-opacity duration-700"
              animate={{
                boxShadow: [
                  "0 0 15px 2px rgba(168,85,247,0.15)",
                  "0 0 25px 6px rgba(168,85,247,0.25)",
                  "0 0 15px 2px rgba(168,85,247,0.15)"
                ],
                opacity: [0.3, 0.6, 0.3]
              }}
              transition={{ 
                duration: 4, 
                repeat: Infinity, 
                ease: "easeInOut", 
                repeatType: "mirror" 
              }}
            />

            {/* Traveling perimeter light beam effect */}
            <div className="absolute -inset-[1px] rounded-3xl overflow-hidden pointer-events-none">
              <motion.div 
                className="absolute top-0 left-0 h-[3px] w-[50%] bg-gradient-to-r from-transparent via-purple-300 to-transparent opacity-80"
                animate={{ 
                  left: ["-50%", "100%"],
                  opacity: [0.4, 0.9, 0.4]
                }}
                transition={{ 
                  left: { duration: 2.8, ease: "easeInOut", repeat: Infinity, repeatDelay: 1 },
                  opacity: { duration: 1.4, repeat: Infinity, repeatType: "mirror" }
                }}
              />
              <motion.div 
                className="absolute top-0 right-0 h-[50%] w-[3px] bg-gradient-to-b from-transparent via-purple-300 to-transparent opacity-80"
                animate={{ 
                  top: ["-50%", "100%"],
                  opacity: [0.4, 0.9, 0.4]
                }}
                transition={{ 
                  top: { duration: 2.8, ease: "easeInOut", repeat: Infinity, repeatDelay: 1, delay: 0.7 },
                  opacity: { duration: 1.4, repeat: Infinity, repeatType: "mirror", delay: 0.7 }
                }}
              />
              <motion.div 
                className="absolute bottom-0 right-0 h-[3px] w-[50%] bg-gradient-to-r from-transparent via-purple-300 to-transparent opacity-80"
                animate={{ 
                  right: ["-50%", "100%"],
                  opacity: [0.4, 0.9, 0.4]
                }}
                transition={{ 
                  right: { duration: 2.8, ease: "easeInOut", repeat: Infinity, repeatDelay: 1, delay: 1.4 },
                  opacity: { duration: 1.4, repeat: Infinity, repeatType: "mirror", delay: 1.4 }
                }}
              />
              <motion.div 
                className="absolute bottom-0 left-0 h-[50%] w-[3px] bg-gradient-to-b from-transparent via-purple-300 to-transparent opacity-80"
                animate={{ 
                  bottom: ["-50%", "100%"],
                  opacity: [0.4, 0.9, 0.4]
                }}
                transition={{ 
                  bottom: { duration: 2.8, ease: "easeInOut", repeat: Infinity, repeatDelay: 1, delay: 2.1 },
                  opacity: { duration: 1.4, repeat: Infinity, repeatType: "mirror", delay: 2.1 }
                }}
              />
            </div>

            {/* Glass Card Background */}
            <div className="relative bg-[#0b0b12]/85 backdrop-blur-2xl rounded-3xl p-6 sm:p-8 border border-white/10 shadow-[0_20px_50px_rgba(0,0,0,0.8)] overflow-hidden">
              {/* Subtle inner grid pattern */}
              <div 
                className="absolute inset-0 opacity-[0.03] pointer-events-none" 
                style={{
                  backgroundImage: `linear-gradient(135deg, white 0.5px, transparent 0.5px), linear-gradient(45deg, white 0.5px, transparent 0.5px)`,
                  backgroundSize: '24px 24px'
                }}
              />

              {/* Logo and Header */}
              <div className="text-center space-y-1.5 mb-6">
                <motion.div
                  initial={{ scale: 0.5, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ type: "spring", duration: 0.8 }}
                  className="mx-auto w-12 h-12 rounded-2xl bg-gradient-to-tr from-purple-600 via-purple-500 to-indigo-500 flex items-center justify-center relative overflow-hidden shadow-[0_0_20px_rgba(168,85,247,0.5)] border border-purple-300/30"
                >
                  <Activity size={24} className="text-white relative z-10" />
                  <div className="absolute inset-0 bg-gradient-to-br from-white/20 to-transparent opacity-60" />
                </motion.div>

                <motion.h1
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.15 }}
                  className="text-2xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-b from-white via-white/90 to-white/70"
                >
                  Welcome to Athleti<span className="text-purple-400">Q</span>
                </motion.h1>
                
                <motion.p
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.25 }}
                  className="text-white/60 text-xs"
                >
                  Computer vision movement screening & clinical injury risk analytics
                </motion.p>
              </div>

              {/* Error Alert */}
              {error && (
                <div className="mb-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                  <AlertCircle size={15} className="shrink-0 text-rose-400" />
                  <span>{error}</span>
                </div>
              )}

              {/* Authentication Form */}
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-3">
                  {/* Email Input */}
                  <div className="relative">
                    <Mail className={`absolute left-3.5 top-3 w-4 h-4 transition-colors duration-200 ${
                      focusedInput === "email" ? 'text-purple-400' : 'text-white/40'
                    }`} />
                    <Input
                      type="email"
                      placeholder="Email address"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      onFocus={() => setFocusedInput("email")}
                      onBlur={() => setFocusedInput(null)}
                      className="pl-10"
                      required
                    />
                  </div>

                  {/* Password Input */}
                  <div className="relative">
                    <Lock className={`absolute left-3.5 top-3 w-4 h-4 transition-colors duration-200 ${
                      focusedInput === "password" ? 'text-purple-400' : 'text-white/40'
                    }`} />
                    <Input
                      type={showPassword ? "text" : "password"}
                      placeholder="Password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      onFocus={() => setFocusedInput("password")}
                      onBlur={() => setFocusedInput(null)}
                      className="pl-10 pr-10"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)} 
                      className="absolute right-3.5 top-3 text-white/40 hover:text-white transition-colors"
                      aria-label={showPassword ? "Hide password" : "Show password"}
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {/* Remember Me */}
                <div className="flex items-center justify-between text-xs text-white/60 pt-0.5">
                  <label className="flex items-center gap-2 cursor-pointer hover:text-white/80 transition-colors">
                    <input
                      type="checkbox"
                      checked={rememberMe}
                      onChange={(e) => setRememberMe(e.target.checked)}
                      className="rounded border border-white/20 bg-white/5 accent-purple-600 focus:ring-0 w-3.5 h-3.5"
                    />
                    <span>Remember me</span>
                  </label>
                  <span className="text-purple-400 hover:text-purple-300 transition-colors cursor-pointer">
                    Forgot password?
                  </span>
                </div>

                {/* Submit Button with Purple Beam Accent */}
                <motion.button
                  whileHover={{ scale: 1.01 }}
                  whileTap={{ scale: 0.99 }}
                  type="submit"
                  disabled={isLoading}
                  className="w-full relative group/btn mt-2"
                >
                  <div className="absolute -inset-[0.5px] bg-gradient-to-r from-purple-600 via-indigo-600 to-purple-600 rounded-xl opacity-70 group-hover/btn:opacity-100 blur-[2px] transition duration-300" />
                  
                  <div className="relative bg-gradient-to-r from-purple-600 to-indigo-600 text-white font-semibold h-11 rounded-xl transition duration-200 flex items-center justify-center gap-2 text-xs uppercase tracking-wider shadow-lg">
                    {isLoading ? (
                      <div className="w-4 h-4 border-2 border-white/80 border-t-transparent rounded-full animate-spin" />
                    ) : (
                      <>
                        <span>Sign In</span>
                        <ArrowRight size={14} className="group-hover/btn:translate-x-1 transition-transform" />
                      </>
                    )}
                  </div>
                </motion.button>
              </form>

              {/* Divider */}
              <div className="relative my-5 flex items-center">
                <div className="flex-grow border-t border-white/10" />
                <span className="mx-3 text-[10px] uppercase tracking-wider text-white/40 font-semibold">
                  Or continue with
                </span>
                <div className="flex-grow border-t border-white/10" />
              </div>

              {/* Google Sign In */}
              <div className="mb-5">
                <GoogleAuthButton
                  role="athlete"
                  onSuccess={() => navigate('/dashboard')}
                  onError={(err) => setError(err)}
                />
              </div>

              {/* Quick Demo Access Pills */}
              <div className="pt-4 border-t border-white/10">
                <div className="flex items-center justify-between mb-2.5">
                  <span className="text-[10px] uppercase tracking-wider font-bold text-purple-400 flex items-center gap-1.5">
                    <Sparkles size={12} />
                    Quick Demo Credentials
                  </span>
                  <span className="text-[10px] text-white/40">1-click login</span>
                </div>
                
                <div className="grid grid-cols-2 gap-2">
                  {DEMO_ROLES.map((demo) => {
                    const Icon = demo.icon;
                    return (
                      <button
                        key={demo.id}
                        type="button"
                        onClick={() => handleQuickFill(demo)}
                        disabled={isLoading}
                        className="p-2 rounded-xl border border-white/10 bg-white/[0.03] hover:bg-purple-950/40 hover:border-purple-500/40 text-left transition flex items-center gap-2 group/card disabled:opacity-50"
                        title={demo.desc}
                      >
                        <div className="w-6 h-6 rounded-lg bg-white/5 group-hover/card:bg-purple-500/20 text-purple-300 flex items-center justify-center shrink-0 transition">
                          <Icon size={12} />
                        </div>
                        <div className="min-w-0 flex-1">
                          <span className="text-[11px] font-bold text-white block truncate">{demo.label}</span>
                          <span className="text-[9px] text-white/40 block truncate">{demo.desc}</span>
                        </div>
                      </button>
                    );
                  })}
                </div>

                {/* Sign up Link */}
                <p className="text-center text-xs text-white/60 mt-5">
                  Don't have an account?{' '}
                  <Link to="/register" className="text-purple-400 hover:text-purple-300 font-semibold transition">
                    Register
                  </Link>
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
  );
};
export default Login;
