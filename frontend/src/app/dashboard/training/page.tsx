"use client";

export default function TrainingPlansPage() {
  const plans = [
    { title: "Knee Valgus Correction", duration: "4 Weeks", status: "Active", tasks: ["Banded Side Steps", "Single Leg Romanian Deadlifts"] },
    { title: "Core Stability Routine", duration: "Ongoing", status: "Active", tasks: ["Planks", "Russian Twists"] },
    { title: "Post-Match Recovery", duration: "1 Day", status: "Pending", tasks: ["Foam Rolling", "Light Stretching", "Cold Plunge"] }
  ];

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <h2 className="text-2xl font-bold text-white mb-6">Training & Corrective Plans</h2>

      <div className="grid gap-6">
        {plans.map((plan, i) => (
          <div key={i} className="glass-panel p-6 rounded-2xl border border-slate-800">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="text-lg font-bold text-white">{plan.title}</h3>
                <p className="text-sm text-slate-400">Duration: {plan.duration}</p>
              </div>
              <span className={`px-3 py-1 rounded-full text-xs font-medium ${plan.status === 'Active' ? 'bg-indigo-500/20 text-indigo-400' : 'bg-slate-800 text-slate-400'}`}>
                {plan.status}
              </span>
            </div>

            <div className="space-y-2">
              <p className="text-sm font-medium text-slate-300">Prescribed Exercises:</p>
              <ul className="list-disc list-inside text-slate-400 text-sm space-y-1">
                {plan.tasks.map((task, j) => (
                  <li key={j}>{task}</li>
                ))}
              </ul>
            </div>

            <button className="mt-6 w-full py-2 bg-slate-800 hover:bg-slate-700 text-white text-sm font-medium rounded-lg transition-colors">
              View Full Plan Details
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
