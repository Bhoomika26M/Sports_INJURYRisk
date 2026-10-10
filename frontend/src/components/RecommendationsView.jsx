import React from 'react';
import { Sparkles, Dumbbell, ShieldCheck, HeartPulse, Compass, CheckCircle2, Flame, Sliders } from 'lucide-react';

export default function RecommendationsView({ injuryRisk }) {
  if (!injuryRisk) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-12 text-center space-y-3">
        <Sparkles className="w-12 h-12 text-slate-600 mx-auto animate-pulse" />
        <h3 className="text-base font-bold text-white">No Corrective Prescriptions Generated</h3>
        <p className="text-xs text-slate-400 max-w-md mx-auto">
          Run the video analysis first to generate targeted corrective exercise workflows.
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
      <div className="bg-slate-900/60 p-4 rounded-2xl border border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-cyan-400" />
            Corrective Exercise & Biomechanical Interventions
          </h2>
          <p className="text-xs text-slate-400">
            Targeted clinical protocols tailored to detected dynamic knee valgus, pelvic instability, and asymmetry.
          </p>
        </div>

        <div className="flex items-center gap-2 bg-cyan-950/40 px-3 py-1.5 rounded-xl border border-cyan-800/60 text-xs">
          <ShieldCheck className="w-4 h-4 text-cyan-400" />
          <span className="text-cyan-300 font-semibold">{exercises.length} Targeted Exercises Prescribed</span>
        </div>
      </div>

      {/* Corrective Exercise Prescription Cards */}
      <div className="space-y-3">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <Dumbbell className="w-4 h-4 text-cyan-400" />
          Prescribed Corrective Exercises
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {exercises.map((ex, idx) => (
            <div
              key={idx}
              className="bg-slate-900/70 p-5 rounded-2xl border border-slate-800 hover:border-cyan-500/40 transition-all space-y-4 flex flex-col justify-between"
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <h4 className="text-sm font-bold text-white">{ex.name}</h4>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 shrink-0">
                    {ex.difficulty}
                  </span>
                </div>

                <div className="p-2.5 rounded-xl bg-slate-950/80 border border-slate-800 space-y-1">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">Target Structure:</span>
                  <p className="text-xs font-semibold text-slate-200">{ex.target_area}</p>
                </div>

                {/* Prescription Parameters */}
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div className="p-2 rounded-lg bg-slate-950 border border-slate-800/80">
                    <span className="text-[9px] text-slate-400 block uppercase">Sets</span>
                    <span className="text-xs font-bold text-white font-mono">{ex.sets}</span>
                  </div>
                  <div className="p-2 rounded-lg bg-slate-950 border border-slate-800/80">
                    <span className="text-[9px] text-slate-400 block uppercase">Reps</span>
                    <span className="text-xs font-bold text-white font-mono">{ex.reps}</span>
                  </div>
                  <div className="p-2 rounded-lg bg-slate-950 border border-slate-800/80">
                    <span className="text-[9px] text-slate-400 block uppercase">Frequency</span>
                    <span className="text-xs font-bold text-cyan-400 font-mono">{ex.frequency}</span>
                  </div>
                </div>

                {/* Coaching Cues */}
                <div className="space-y-1.5">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">Coaching Cues:</span>
                  <ul className="space-y-1">
                    {(ex.coaching_cues || []).map((cue, cIdx) => (
                      <li key={cIdx} className="text-[11px] text-slate-300 flex items-start gap-1.5">
                        <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400 shrink-0 mt-0.5" />
                        <span>{cue}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
                <span>Equipment:</span>
                <span className="text-slate-300 font-medium">{ex.equipment}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 4 Supporting Intervention Columns */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Mobility Improvements */}
        <div className="bg-slate-900/60 p-4 rounded-2xl border border-slate-800 space-y-3">
          <div className="flex items-center gap-2">
            <Compass className="w-4 h-4 text-cyan-400" />
            <h4 className="text-xs font-bold text-white uppercase tracking-wider">Mobility Protocols</h4>
          </div>
          <ul className="space-y-2 text-xs text-slate-300">
            {mobility.map((item, i) => (
              <li key={i} className="flex items-start gap-1.5 p-2 rounded-lg bg-slate-950/60 border border-slate-800/80">
                <span className="text-cyan-400 font-bold shrink-0">•</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Strengthening Plan */}
        <div className="bg-slate-900/60 p-4 rounded-2xl border border-slate-800 space-y-3">
          <div className="flex items-center gap-2">
            <Flame className="w-4 h-4 text-purple-400" />
            <h4 className="text-xs font-bold text-white uppercase tracking-wider">Strengthening Plan</h4>
          </div>
          <ul className="space-y-2 text-xs text-slate-300">
            {strengthening.map((item, i) => (
              <li key={i} className="flex items-start gap-1.5 p-2 rounded-lg bg-slate-950/60 border border-slate-800/80">
                <span className="text-purple-400 font-bold shrink-0">•</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Recovery Planning */}
        <div className="bg-slate-900/60 p-4 rounded-2xl border border-slate-800 space-y-3">
          <div className="flex items-center gap-2">
            <HeartPulse className="w-4 h-4 text-emerald-400" />
            <h4 className="text-xs font-bold text-white uppercase tracking-wider">Recovery Strategy</h4>
          </div>
          <ul className="space-y-2 text-xs text-slate-300">
            {recovery.map((item, i) => (
              <li key={i} className="flex items-start gap-1.5 p-2 rounded-lg bg-slate-950/60 border border-slate-800/80">
                <span className="text-emerald-400 font-bold shrink-0">•</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Training Load Modifications */}
        <div className="bg-slate-900/60 p-4 rounded-2xl border border-slate-800 space-y-3">
          <div className="flex items-center gap-2">
            <Sliders className="w-4 h-4 text-amber-400" />
            <h4 className="text-xs font-bold text-white uppercase tracking-wider">Workload Modifications</h4>
          </div>
          <ul className="space-y-2 text-xs text-slate-300">
            {training.map((item, i) => (
              <li key={i} className="flex items-start gap-1.5 p-2 rounded-lg bg-slate-950/60 border border-slate-800/80">
                <span className="text-amber-400 font-bold shrink-0">•</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
