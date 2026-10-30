import React from 'react';
import { Sparkles, Dumbbell, ShieldCheck, HeartPulse, Compass, CheckCircle2, Flame, Sliders } from 'lucide-react';

export default function RecommendationsView({ injuryRisk }) {
  if (!injuryRisk) {
    return (
      <div className="bg-white border border-slate-200 rounded-xl p-12 text-center space-y-3 shadow-xs">
        <Sparkles className="w-12 h-12 text-slate-400 mx-auto" />
        <h3 className="text-base font-bold text-slate-900">No Exercise Suggestions Available</h3>
        <p className="text-xs text-slate-500 max-w-md mx-auto">
          Run pose analysis first to generate rule-based exercise suggestions for review.
        </p>
      </div>
    );
  }

  const recs = injuryRisk.corrective_recommendations || {};
  const exercises = recs.exercises || [];
  const mobility = recs.mobility_suggestions || [];
  const strengthening = recs.strengthening_plan || [];
  const recovery = recs.recovery_planning || [];
  const training = recs.training_modifications || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-teal-700" />
            Exercise Suggestions from Screening
          </h2>
          <p className="text-xs text-slate-500">
            Exercise suggestions based on the available screening results. Review them with a qualified professional before use.
          </p>
        </div>

        <div className="flex items-center gap-2 bg-teal-50 px-3 py-1.5 rounded-lg border border-teal-200 text-xs">
          <ShieldCheck className="w-4 h-4 text-teal-700" />
          <span className="text-teal-800 font-semibold">{exercises.length} Exercise Suggestions</span>
        </div>
      </div>

      {/* Corrective Exercise Prescription Cards */}
      <div className="space-y-3">
        <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
          <Dumbbell className="w-4 h-4 text-teal-700" />
          Suggested Exercises
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {exercises.map((ex, idx) => (
            <div
              key={idx}
              className="bg-white p-5 rounded-xl border border-slate-200 hover:border-slate-300 shadow-xs transition-colors space-y-4 flex flex-col justify-between"
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <h4 className="text-sm font-bold text-slate-900">{ex.name}</h4>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 shrink-0">
                    {ex.difficulty}
                  </span>
                </div>

                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 space-y-1">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">Target Structure:</span>
                  <p className="text-xs font-semibold text-slate-800">{ex.target_area}</p>
                </div>

                {/* Prescription Parameters */}
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div className="p-2 rounded-lg bg-slate-50 border border-slate-200">
                    <span className="text-[9px] text-slate-500 block uppercase">Sets</span>
                    <span className="text-xs font-bold text-slate-900 font-mono">{ex.sets}</span>
                  </div>
                  <div className="p-2 rounded-lg bg-slate-50 border border-slate-200">
                    <span className="text-[9px] text-slate-500 block uppercase">Reps</span>
                    <span className="text-xs font-bold text-slate-900 font-mono">{ex.reps}</span>
                  </div>
                  <div className="p-2 rounded-lg bg-slate-50 border border-slate-200">
                    <span className="text-[9px] text-slate-500 block uppercase">Frequency</span>
                    <span className="text-xs font-bold text-teal-800 font-mono">{ex.frequency}</span>
                  </div>
                </div>

                {/* Coaching Cues */}
                <div className="space-y-1.5">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">Coaching Cues:</span>
                  <ul className="space-y-1">
                    {(ex.coaching_cues || []).map((cue, cIdx) => (
                      <li key={cIdx} className="text-[11px] text-slate-700 flex items-start gap-1.5">
                        <CheckCircle2 className="w-3.5 h-3.5 text-teal-700 shrink-0 mt-0.5" />
                        <span>{cue}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
                <span>Equipment:</span>
                <span className="text-slate-800 font-medium">{ex.equipment}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 4 Supporting Intervention Columns */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Mobility Improvements */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-3">
          <div className="flex items-center gap-2">
            <Compass className="w-4 h-4 text-teal-700" />
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Mobility Protocols</h4>
          </div>
          <ul className="space-y-2 text-xs text-slate-700">
            {mobility.map((item, i) => (
              <li key={i} className="flex items-start gap-1.5 p-2 rounded-lg bg-slate-50 border border-slate-200">
                <span className="text-teal-700 font-bold shrink-0">•</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Strengthening Plan */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-3">
          <div className="flex items-center gap-2">
            <Flame className="w-4 h-4 text-slate-700" />
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Strengthening Plan</h4>
          </div>
          <ul className="space-y-2 text-xs text-slate-700">
            {strengthening.map((item, i) => (
              <li key={i} className="flex items-start gap-1.5 p-2 rounded-lg bg-slate-50 border border-slate-200">
                <span className="text-slate-700 font-bold shrink-0">•</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Recovery Planning */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-3">
          <div className="flex items-center gap-2">
            <HeartPulse className="w-4 h-4 text-emerald-700" />
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Recovery Strategy</h4>
          </div>
          <ul className="space-y-2 text-xs text-slate-700">
            {recovery.map((item, i) => (
              <li key={i} className="flex items-start gap-1.5 p-2 rounded-lg bg-slate-50 border border-slate-200">
                <span className="text-emerald-700 font-bold shrink-0">•</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Training Load Modifications */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-3">
          <div className="flex items-center gap-2">
            <Sliders className="w-4 h-4 text-amber-700" />
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Workload Modifications</h4>
          </div>
          <ul className="space-y-2 text-xs text-slate-700">
            {training.map((item, i) => (
              <li key={i} className="flex items-start gap-1.5 p-2 rounded-lg bg-slate-50 border border-slate-200">
                <span className="text-amber-700 font-bold shrink-0">•</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
