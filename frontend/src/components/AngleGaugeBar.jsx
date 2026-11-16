import React from 'react';

/**
 * Normative reference database for joint kinematics in strength & athletic training
 * Units: Degrees (°)
 */
export const JOINT_NORMATIVES = {
  squat: {
    knee: {
      min: 70,
      max: 125,
      optimal_min: 90,
      optimal_max: 115,
      unit: '°',
      label: 'Knee Flexion (ROM)',
      description: 'Ideal depth reaches at least 90° for full gluteus & quadriceps engagement without excessive patellofemoral shearing.',
    },
    hip: {
      min: 65,
      max: 110,
      optimal_min: 75,
      optimal_max: 95,
      unit: '°',
      label: 'Hip Flexion (ROM)',
      description: 'Controlled hip hinge preserving neutral lumbar lordosis while achieving parallel femur alignment.',
    },
    trunk: {
      min: 0,
      max: 45,
      optimal_min: 15,
      optimal_max: 32,
      unit: '°',
      label: 'Trunk Lean Angle',
      description: 'Excessive lean (>35°) multiplies shear moment on L4-S1 lumbar discs. Torso should stay broadly parallel to tibias.',
    },
    symmetry: {
      min: 0,
      max: 5,
      optimal_min: 0,
      optimal_max: 4,
      unit: '°',
      label: 'Bilateral Symmetry Tolerance',
      description: 'Difference between left and right limb angles. Differences >5° cause uneven joint contact pressures.',
    },
  },
  default: {
    knee: { min: 60, max: 130, optimal_min: 80, optimal_max: 120, unit: '°', label: 'Knee Angle' },
    hip: { min: 50, max: 120, optimal_min: 70, optimal_max: 105, unit: '°', label: 'Hip Angle' },
    trunk: { min: 0, max: 40, optimal_min: 10, optimal_max: 30, unit: '°', label: 'Trunk Lean' },
    symmetry: { min: 0, max: 5, optimal_min: 0, optimal_max: 4, unit: '°', label: 'Limb Symmetry' },
  },
};

/**
 * Renders an interactive, visual angle gauge showing where the athlete's
 * measurement lands compared to Recommended Normal ranges.
 */
export const AngleGaugeBar = ({ joint = 'knee', currentVal = 0, romVal = null, activity = 'squat' }) => {
  const norms = (JOINT_NORMATIVES[activity] && JOINT_NORMATIVES[activity][joint]) || JOINT_NORMATIVES.default[joint] || JOINT_NORMATIVES.default.knee;

  const displayVal = typeof currentVal === 'number' ? currentVal : 0;
  const optMin = norms.optimal_min ?? 0;
  const optMax = norms.optimal_max ?? 100;
  const rangeMin = norms.min ?? 0;
  const rangeMax = norms.max ?? 140;

  // Status computation
  let status = 'normal'; // 'under' | 'normal' | 'excess'
  if (displayVal < optMin) {
    status = 'under';
  } else if (displayVal > optMax) {
    status = 'excess';
  }

  // Calculate percentage within overall display domain (padding slightly)
  const domainMin = Math.max(0, rangeMin - 15);
  const domainMax = rangeMax + 20;
  const totalRange = domainMax - domainMin;

  const getPercent = (v) => Math.min(100, Math.max(0, ((v - domainMin) / totalRange) * 100));

  const valPercent = getPercent(displayVal);
  const optMinPercent = getPercent(optMin);
  const optMaxPercent = getPercent(optMax);

  return (
    <div className="bg-surface p-3 rounded-lg border border-border text-xs">
      <div className="flex items-center justify-between mb-1.5">
        <span className="font-semibold text-text-primary capitalize flex items-center gap-1.5">
          {norms.label || joint}
        </span>
        <div className="flex items-center gap-1.5">
          <span className="font-mono font-bold text-sm text-text-primary">
            {displayVal.toFixed(1)}{norms.unit}
          </span>
          <span
            className={`px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider ${
              status === 'normal'
                ? 'bg-emerald-100 text-emerald-800'
                : status === 'excess'
                ? 'bg-rose-100 text-rose-800'
                : 'bg-amber-100 text-amber-800'
            }`}
          >
            {status === 'normal' ? 'Normal / Optimal' : status === 'excess' ? 'Beyond Recommended (High)' : 'Below Target'}
          </span>
        </div>
      </div>

      {/* Visual Range Bar */}
      <div className="relative w-full h-3.5 bg-gray-200 rounded-full overflow-hidden my-2">
        {/* Recommended Optimal Zone */}
        <div
          className="absolute top-0 bottom-0 bg-emerald-400/50 border-x border-emerald-600/40"
          style={{ left: `${optMinPercent}%`, width: `${optMaxPercent - optMinPercent}%` }}
          title={`Recommended Target: ${optMin}° - ${optMax}°`}
        />
        {/* Athlete Value Pin */}
        <div
          className={`absolute top-0 bottom-0 w-2.5 rounded-full transform -translate-x-1/2 shadow-md transition-all duration-300 ${
            status === 'normal' ? 'bg-emerald-600 ring-2 ring-emerald-300' : 'bg-red-600 ring-2 ring-red-300'
          }`}
          style={{ left: `${valPercent}%` }}
        />
      </div>

      <div className="flex justify-between text-[11px] text-text-secondary">
        <span>{domainMin}°</span>
        <span className="text-emerald-700 font-medium">
          Target: {optMin}°–{optMax}°
        </span>
        <span>{domainMax}°</span>
      </div>

      {norms.description && (
        <p className="mt-1 text-[11px] text-gray-500 leading-tight">
          {norms.description}
        </p>
      )}
    </div>
  );
};

export default AngleGaugeBar;
