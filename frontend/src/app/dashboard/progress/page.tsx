"use client";

export default function ProgressPage() {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <h2 className="text-2xl font-bold text-white mb-6">My Progress</h2>

      <div className="glass-panel p-8 rounded-2xl">
        <h3 className="text-lg font-semibold text-slate-200 mb-6">Risk Score Over Time</h3>

        <div className="h-64 flex items-end justify-between gap-2 border-b border-l border-slate-800 p-4 pt-10 relative">
          {/* Simulated chart bars */}
          {[45, 40, 38, 30, 35, 25, 20, 18, 15, 12].map((height, i) => (
            <div key={i} className="w-full bg-indigo-500/50 hover:bg-indigo-400 transition-colors rounded-t-sm relative group" style={{ height: `${height}%` }}>
              <div className="absolute -top-8 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 bg-slate-800 text-xs px-2 py-1 rounded text-white transition-opacity">
                {height}
              </div>
            </div>
          ))}

          <div className="absolute top-2 left-4 text-xs text-slate-500">Risk Score (Lower is better)</div>
        </div>
        <div className="flex justify-between mt-2 text-xs text-slate-500 px-4">
          <span>10 Weeks Ago</span>
          <span>Today</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
        <div className="glass-panel p-6 rounded-2xl bg-gradient-to-br from-emerald-900/20 to-transparent border-emerald-500/20">
          <h4 className="text-emerald-400 font-medium mb-2">Great Job!</h4>
          <p className="text-sm text-slate-300">Your knee valgus metrics have improved by 40% over the last month.</p>
        </div>
        <div className="glass-panel p-6 rounded-2xl bg-gradient-to-br from-amber-900/20 to-transparent border-amber-500/20">
          <h4 className="text-amber-400 font-medium mb-2">Area of Focus</h4>
          <p className="text-sm text-slate-300">Core stability metrics show slight decline. Focus on your new training plan.</p>
        </div>
      </div>
    </div>
  );
}
