"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { login, register, googleLogin } from "@/lib/api";

export default function Home() {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("demo@sportsai.com");
  const [password, setPassword] = useState("password123");
  const [role, setRole] = useState("Athlete");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const router = useRouter();

  const handleGoogleAuth = async () => {
    const userEmail = prompt("Enter your Google Email for Demo Login:", "user@gmail.com");
    if (!userEmail) return;
    
    setLoading(true);
    setError("");
    try {
      const data = await googleLogin(userEmail, role);
      localStorage.setItem("token", data.access_token);
      router.push("/dashboard");
    } catch (err) {
      setError("Google Login failed");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    
    try {
      if (isLogin) {
        const data = await login(email, password);
        localStorage.setItem("token", data.access_token);
        router.push("/dashboard");
      } else {
        await register(email, password, role);
        const data = await login(email, password);
        localStorage.setItem("token", data.access_token);
        router.push("/dashboard");
      }
    } catch (err) {
      if (err instanceof Error) {
        if (err.message.toLowerCase().includes("failed to fetch")) {
          setError("Cannot connect to server. Please ensure the backend is running.");
        } else {
          setError(err.message || "An error occurred. Please try again.");
        }
      } else {
        setError("An error occurred. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex-grow flex flex-col items-center justify-center relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] rounded-full bg-indigo-600/20 blur-[120px]" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] rounded-full bg-pink-600/20 blur-[120px]" />
      
      <div className="z-10 w-full max-w-5xl px-6 py-20 flex flex-col md:flex-row items-center gap-12">
        
        {/* Left column: Hero content */}
        <div className="flex-1 space-y-8 text-center md:text-left">
          <div className="inline-block px-4 py-1.5 rounded-full border border-indigo-500/30 bg-indigo-500/10 text-indigo-300 text-sm font-medium tracking-wide">
            AI-Powered Biomechanics
          </div>
          
          <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight">
            Predict &amp; Prevent <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-pink-500">
              Sports Injuries
            </span>
          </h1>
          
          <p className="text-lg md:text-xl text-slate-400 max-w-xl mx-auto md:mx-0">
            Advanced pose estimation and biomechanical analysis to identify risks before injuries happen. Trusted by top athletes, coaches, and medical teams.
          </p>
          
          <div className="flex flex-col sm:flex-row items-center gap-4 pt-4 justify-center md:justify-start">
            <Link 
              href="/dashboard"
              className="px-8 py-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold transition-all shadow-[0_0_20px_rgba(79,70,229,0.4)] hover:shadow-[0_0_30px_rgba(79,70,229,0.6)] hover:-translate-y-0.5 w-full sm:w-auto text-center"
            >
              Enter Dashboard
            </Link>
            <button className="px-8 py-4 rounded-xl border border-slate-700 hover:border-slate-500 bg-slate-800/50 hover:bg-slate-800 text-white font-medium transition-all w-full sm:w-auto">
              View Demo
            </button>
          </div>
        </div>

        {/* Right column: Login / Feature card */}
        <div className="flex-1 w-full max-w-md">
          <div className="glass-panel p-8 rounded-2xl relative group">
            <div className="absolute inset-0 bg-gradient-to-b from-indigo-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 rounded-2xl pointer-events-none" />
            
            <div className="relative z-10 space-y-6">
              <div className="text-center">
                <h3 className="text-2xl font-bold text-white mb-2">{isLogin ? "Platform Access" : "Create Account"}</h3>
                <p className="text-slate-400 text-sm">{isLogin ? "Sign in to your intelligent sports hub" : "Join the sports injury prevention platform"}</p>
              </div>
              
              <form className="space-y-4" onSubmit={handleSubmit}>
                {error && <div className="text-rose-500 text-sm font-medium">{error}</div>}
                <div className="space-y-1">
                  <label className="text-sm font-medium text-slate-300">Email Address</label>
                  <input 
                    type="email" 
                    placeholder="coach@team.com" 
                    className="w-full px-4 py-3 bg-slate-900/50 border border-slate-700 rounded-xl focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors text-slate-100 placeholder:text-slate-600"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </div>
                
                <div className="space-y-1">
                  <label className="text-sm font-medium text-slate-300">Password</label>
                  <div className="relative">
                    <input 
                      type={showPassword ? "text" : "password"} 
                      placeholder="••••••••" 
                      className="w-full px-4 py-3 bg-slate-900/50 border border-slate-700 rounded-xl focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors text-slate-100 placeholder:text-slate-600"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                    />
                    <button 
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-300 text-sm font-medium"
                    >
                      {showPassword ? "Hide" : "Show"}
                    </button>
                  </div>
                </div>

                {!isLogin && (
                  <div className="space-y-1">
                    <label className="text-sm font-medium text-slate-300">Role</label>
                    <select 
                      className="w-full px-4 py-3 bg-slate-900/50 border border-slate-700 rounded-xl focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors text-slate-100 appearance-none"
                      value={role}
                      onChange={(e) => setRole(e.target.value)}
                    >
                      <option value="Athlete">Athlete</option>
                      <option value="Coach">Coach</option>
                      <option value="Physiotherapist">Physiotherapist</option>
                      <option value="Sports Scientist">Sports Scientist</option>
                      <option value="Administrator">Administrator</option>
                    </select>
                  </div>
                )}

                {isLogin && (
                  <div className="flex items-center justify-between text-sm">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input type="checkbox" className="rounded border-slate-700 bg-slate-900/50 text-indigo-500 focus:ring-indigo-500/30" />
                      <span className="text-slate-400">Remember me</span>
                    </label>
                    <a href="#" className="text-indigo-400 hover:text-indigo-300 transition-colors">Forgot password?</a>
                  </div>
                )}

                <button 
                  type="submit"
                  disabled={loading}
                  className="block w-full py-3 px-4 bg-white text-slate-900 text-center font-bold rounded-xl hover:bg-slate-200 transition-colors mt-6 disabled:opacity-50"
                >
                  {loading ? (isLogin ? "Signing In..." : "Creating Account...") : (isLogin ? "Sign In ->" : "Sign Up ->")}
                </button>

                <div className="mt-4 flex items-center justify-between">
                  <hr className="w-full border-slate-700" />
                  <span className="px-3 text-slate-400 text-sm">or</span>
                  <hr className="w-full border-slate-700" />
                </div>

                <button
                  type="button"
                  onClick={handleGoogleAuth}
                  className="w-full py-3 px-4 bg-slate-800 border border-slate-700 text-white font-semibold rounded-xl hover:bg-slate-700 transition-colors flex items-center justify-center gap-3 mt-4"
                >
                  <svg className="w-5 h-5" viewBox="0 0 24 24">
                    <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                  </svg>
                  {isLogin ? "Sign In with Google" : "Register with Google"}
                </button>
              </form>
              
              <div className="text-center mt-4">
                <button 
                  onClick={() => setIsLogin(!isLogin)} 
                  className="text-sm text-indigo-400 hover:text-indigo-300 transition-colors"
                >
                  {isLogin ? "Need an account? Register" : "Already have an account? Sign in"}
                </button>
              </div>
            </div>
          </div>
        </div>

      </div>
    </main>
  );
}
