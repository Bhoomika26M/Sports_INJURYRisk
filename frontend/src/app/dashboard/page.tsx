export default function DashboardHome() {
  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      
      {/* Top Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="glass-panel p-6 rounded-2xl">
          <div className="text-sm font-medium text-slate-400 mb-1">Team Overall Risk Score</div>
          <div className="text-3xl font-bold text-white flex items-end gap-2">
            28<span className="text-lg text-green-400">/ 100</span>
          </div>
          <div className="text-xs text-green-400 mt-2 flex items-center gap-1">
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" /></svg>
            -12% from last week
          </div>
        </div>
        
        <div className="glass-panel p-6 rounded-2xl">
          <div className="text-sm font-medium text-slate-400 mb-1">High Risk Athletes</div>
          <div className="text-3xl font-bold text-white">
            2
          </div>
          <div className="text-xs text-rose-400 mt-2 flex items-center gap-1">
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>
            +1 since yesterday
          </div>
        </div>

        <div className="glass-panel p-6 rounded-2xl">
          <div className="text-sm font-medium text-slate-400 mb-1">Videos Analyzed</div>
          <div className="text-3xl font-bold text-white">
            143
          </div>
          <div className="text-xs text-indigo-400 mt-2 flex items-center gap-1">
            <span>Last 7 days</span>
          </div>
        </div>

        <div className="glass-panel p-6 rounded-2xl border-indigo-500/30 bg-indigo-500/5 cursor-pointer hover:bg-indigo-500/10 transition-colors group">
          <div className="h-full flex flex-col items-center justify-center text-indigo-400 group-hover:text-indigo-300">
            <svg className="w-8 h-8 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            <span className="font-medium">Upload New Video</span>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column - Athletes List */}
        <div className="lg:col-span-2 space-y-6">
          <div className="glass-panel rounded-2xl p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-bold text-white">Athlete Risk Assessment</h3>
              <button className="text-sm text-indigo-400 hover:text-indigo-300 font-medium">View All</button>
            </div>
            
            <div className="space-y-4">
              {/* Athlete Item 1 */}
              <div className="flex items-center justify-between p-4 rounded-xl bg-slate-900/50 border border-slate-800 hover:border-slate-700 transition-colors cursor-pointer">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center font-bold text-slate-300">MS</div>
                  <div>
                    <div className="font-medium text-white">Michael Smith</div>
                    <div className="text-xs text-slate-400">Point Guard • Knee Valgus Detected</div>
                  </div>
                </div>
                <div className="flex items-center gap-6">
                  <div className="text-right">
                    <div className="text-sm font-bold text-rose-400">84/100 Risk</div>
                    <div className="text-xs text-slate-500">Critical</div>
                  </div>
                  <div className="w-2 h-10 rounded-full bg-rose-500/20 relative">
                    <div className="absolute bottom-0 w-full bg-rose-500 rounded-full" style={{ height: '84%' }}></div>
                  </div>
                </div>
              </div>

              {/* Athlete Item 2 */}
              <div className="flex items-center justify-between p-4 rounded-xl bg-slate-900/50 border border-slate-800 hover:border-slate-700 transition-colors cursor-pointer">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center font-bold text-slate-300">DJ</div>
                  <div>
                    <div className="font-medium text-white">David Johnson</div>
                    <div className="text-xs text-slate-400">Shooting Guard • Minor Fatigue</div>
                  </div>
                </div>
                <div className="flex items-center gap-6">
                  <div className="text-right">
                    <div className="text-sm font-bold text-amber-400">42/100 Risk</div>
                    <div className="text-xs text-slate-500">Moderate</div>
                  </div>
                  <div className="w-2 h-10 rounded-full bg-amber-500/20 relative">
                    <div className="absolute bottom-0 w-full bg-amber-500 rounded-full" style={{ height: '42%' }}></div>
                  </div>
                </div>
              </div>

              {/* Athlete Item 3 */}
              <div className="flex items-center justify-between p-4 rounded-xl bg-slate-900/50 border border-slate-800 hover:border-slate-700 transition-colors cursor-pointer">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center font-bold text-slate-300">EW</div>
                  <div>
                    <div className="font-medium text-white">Ethan Williams</div>
                    <div className="text-xs text-slate-400">Power Forward • Optimal Form</div>
                  </div>
                </div>
                <div className="flex items-center gap-6">
                  <div className="text-right">
                    <div className="text-sm font-bold text-emerald-400">12/100 Risk</div>
                    <div className="text-xs text-slate-500">Low</div>
                  </div>
                  <div className="w-2 h-10 rounded-full bg-emerald-500/20 relative">
                    <div className="absolute bottom-0 w-full bg-emerald-500 rounded-full" style={{ height: '12%' }}></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column - Breakdown */}
        <div className="space-y-6">
          <div className="glass-panel rounded-2xl p-6">
            <h3 className="text-lg font-bold text-white mb-6">Recent Video Analysis</h3>
            
            <div className="aspect-video bg-slate-900 rounded-xl relative overflow-hidden group mb-4 border border-slate-800">
              {/* Fake Video Thumbnail / AI Overlay */}
              <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1546519638-68e109498ffc?q=80&w=2090&auto=format&fit=crop')] bg-cover bg-center opacity-40 mix-blend-luminosity"></div>
              
              {/* Simulated skeleton overlay */}
              <div className="absolute top-[20%] left-[45%] w-2 h-2 bg-green-400 rounded-full animate-pulse shadow-[0_0_10px_#4ade80]"></div>
              <div className="absolute top-[40%] left-[40%] w-2 h-2 bg-green-400 rounded-full animate-pulse shadow-[0_0_10px_#4ade80]"></div>
              <div className="absolute top-[40%] left-[50%] w-2 h-2 bg-green-400 rounded-full animate-pulse shadow-[0_0_10px_#4ade80]"></div>
              <div className="absolute top-[60%] left-[38%] w-2 h-2 bg-rose-500 rounded-full animate-pulse shadow-[0_0_10px_#f43f5e]"></div>
              
              {/* Connecting lines simulated */}
              <div className="absolute top-[21%] left-[45%] w-[1px] h-[20%] bg-green-400/50 transform -rotate-12 origin-top"></div>
              
              <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-slate-950/40">
                <button className="w-12 h-12 bg-indigo-600 rounded-full flex items-center justify-center text-white shadow-lg hover:bg-indigo-500 transition-colors cursor-pointer z-10">
                  <svg className="w-6 h-6 ml-1" fill="currentColor" viewBox="0 0 20 20"><path d="M4 4l12 6-12 6z"/></svg>
                </button>
              </div>
              
              {/* Status Badge */}
              <div className="absolute top-3 right-3 px-2.5 py-1 bg-rose-500/20 border border-rose-500/50 text-rose-400 text-xs font-bold rounded-lg backdrop-blur-sm">
                Anomaly Detected
              </div>
            </div>
            
            <div className="space-y-3">
              <div className="flex justify-between items-center text-sm">
                <span className="text-slate-400">Athlete</span>
                <span className="text-white font-medium">Michael Smith</span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-slate-400">Movement</span>
                <span className="text-white font-medium">Squat Jump</span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-slate-400">Issue Found</span>
                <span className="text-rose-400 font-medium">Valgus Collapse (Left)</span>
              </div>
              
              <button className="w-full mt-4 py-2 bg-slate-800 hover:bg-slate-700 text-white text-sm font-medium rounded-lg transition-colors border border-slate-700">
                View Detailed Report
              </button>
            </div>
          </div>
        </div>
      </div>
      
    </div>
  );
}
