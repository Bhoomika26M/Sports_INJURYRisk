import Link from "next/link";

export default function Home() {
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
                <h3 className="text-2xl font-bold text-white mb-2">Platform Access</h3>
                <p className="text-slate-400 text-sm">Sign in to your intelligent sports hub</p>
              </div>
              
              <form className="space-y-4">
                <div className="space-y-1">
                  <label className="text-sm font-medium text-slate-300">Email Address</label>
                  <input 
                    type="email" 
                    placeholder="coach@team.com" 
                    className="w-full px-4 py-3 bg-slate-900/50 border border-slate-700 rounded-xl focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors text-slate-100 placeholder:text-slate-600"
                    defaultValue="demo@sportsai.com"
                  />
                </div>
                
                <div className="space-y-1">
                  <label className="text-sm font-medium text-slate-300">Password</label>
                  <input 
                    type="password" 
                    placeholder="••••••••" 
                    className="w-full px-4 py-3 bg-slate-900/50 border border-slate-700 rounded-xl focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors text-slate-100 placeholder:text-slate-600"
                    defaultValue="password123"
                  />
                </div>

                <div className="flex items-center justify-between text-sm">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" className="rounded border-slate-700 bg-slate-900/50 text-indigo-500 focus:ring-indigo-500/30" />
                    <span className="text-slate-400">Remember me</span>
                  </label>
                  <a href="#" className="text-indigo-400 hover:text-indigo-300 transition-colors">Forgot password?</a>
                </div>

                <Link 
                  href="/dashboard"
                  className="block w-full py-3 px-4 bg-white text-slate-900 text-center font-bold rounded-xl hover:bg-slate-200 transition-colors mt-6"
                >
                  Sign In -&gt;
                </Link>
              </form>
            </div>
          </div>
        </div>

      </div>
    </main>
  );
}
