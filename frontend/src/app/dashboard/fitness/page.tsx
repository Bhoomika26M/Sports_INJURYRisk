"use client";

export default function FitnessPage() {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <h2 className="text-2xl font-bold text-white mb-6">My Fitness</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="glass-panel p-6 rounded-2xl">
          <h3 className="text-lg font-semibold text-slate-200 mb-4">Overall Conditioning</h3>
          <div className="flex items-center gap-4">
            <div className="relative w-24 h-24">
              <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                <path className="text-slate-800" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeWidth="3" />
                <path className="text-emerald-400" strokeDasharray="88, 100" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeWidth="3" />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center text-xl font-bold text-white">88%</div>
            </div>
            <div>
              <div className="text-sm text-slate-400">Status</div>
              <div className="text-lg font-medium text-emerald-400">Peak Performance</div>
            </div>
          </div>
        </div>

        <div className="glass-panel p-6 rounded-2xl">
          <h3 className="text-lg font-semibold text-slate-200 mb-4">Recent Wellness Metrics</h3>
          <ul className="space-y-4">
            <li className="flex justify-between items-center">
              <span className="text-slate-400">Average RPE</span>
              <span className="text-white font-medium">6.2 / 10</span>
            </li>
            <li className="flex justify-between items-center">
              <span className="text-slate-400">Sleep Quality</span>
              <span className="text-white font-medium">7.5 / 10</span>
            </li>
            <li className="flex justify-between items-center">
              <span className="text-slate-400">Recovery Score</span>
              <span className="text-emerald-400 font-medium">Excellent</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
