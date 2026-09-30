"use client";

export default function SettingsPage() {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <h2 className="text-2xl font-bold text-white mb-6">Settings</h2>

      <div className="glass-panel p-6 rounded-2xl space-y-6 border border-slate-800">
        <div>
          <h3 className="text-lg font-semibold text-slate-200 mb-4">Notifications</h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-white font-medium">Email Alerts</div>
                <div className="text-xs text-slate-400">Receive reports when new risk anomalies are detected</div>
              </div>
              <div className="w-12 h-6 bg-indigo-500 rounded-full relative cursor-pointer">
                <div className="w-4 h-4 bg-white rounded-full absolute right-1 top-1"></div>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <div>
                <div className="text-white font-medium">Daily Wellness Reminder</div>
                <div className="text-xs text-slate-400">Push notification to enter RPE and Sleep Data</div>
              </div>
              <div className="w-12 h-6 bg-indigo-500 rounded-full relative cursor-pointer">
                <div className="w-4 h-4 bg-white rounded-full absolute right-1 top-1"></div>
              </div>
            </div>
          </div>
        </div>

        <div className="border-t border-slate-800 pt-6">
          <h3 className="text-lg font-semibold text-slate-200 mb-4">Account</h3>
          <div className="space-y-4">
            <button className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white text-sm font-medium rounded-lg transition-colors">
              Change Password
            </button>
            <button className="px-4 py-2 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 text-sm font-medium rounded-lg transition-colors ml-4 border border-rose-500/20">
              Delete Account
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
