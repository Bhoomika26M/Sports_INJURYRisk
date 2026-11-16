import React, { useState } from 'react';
import BiomechanicalStickFigure from './BiomechanicalStickFigure';

const SEVERITY_BADGES = {
  low: 'bg-emerald-50 text-emerald-800 border-emerald-300',
  moderate: 'bg-amber-50 text-amber-800 border-amber-300',
  high: 'bg-orange-50 text-orange-900 border-orange-300',
  critical: 'bg-rose-50 text-rose-900 border-rose-300',
};

const SEVERITY_DOT = {
  low: 'bg-emerald-500',
  moderate: 'bg-amber-500',
  high: 'bg-orange-500',
  critical: 'bg-rose-600',
};

/**
 * FindingCard: Rich, highly digestible breakdown of a single injury risk finding.
 * Caters to both non-technical athletes (plain language, visual stick figures, simple cues)
 * and coaches / physiotherapists (clinical terms, anatomy, precise calculations & tolerance).
 */
export const FindingCard = ({ finding, index, activityType = 'squat', keypointsData = null }) => {
  const [expandedSection, setExpandedSection] = useState('overview'); // 'overview' | 'calculations' | 'anatomy'

  const severity = finding.severity || 'moderate';
  const musclesOver = finding.muscles_overactive || [];
  const musclesUnder = finding.muscles_underactive || [];
  const primaryMuscles = finding.muscles?.primary || [];
  const stabilizers = finding.muscles?.stabilizers || [];

  return (
    <div className="bg-white rounded-xl border border-gray-200/90 shadow-sm overflow-hidden transition-all hover:shadow-md">
      {/* Header Banner */}
      <div className="p-4 sm:p-5 bg-gradient-to-r from-gray-50/80 via-white to-gray-50/40 border-b border-gray-100 flex flex-wrap items-start justify-between gap-3">
        <div className="flex-1 min-w-[240px]">
          <div className="flex items-center gap-2 mb-1.5">
            <span className={`w-2.5 h-2.5 rounded-full ${SEVERITY_DOT[severity] || 'bg-gray-400'} animate-pulse`} />
            <span className="text-xs font-mono font-semibold uppercase tracking-wider text-gray-500">
              Finding #{index + 1} • {finding.body_parts?.join(', ') || 'Kinematic System'}
            </span>
          </div>
          <h3 className="text-lg sm:text-xl font-bold text-gray-900 leading-snug">
            {finding.issue}
          </h3>
          {finding.scientific_term && (
            <div className="mt-1.5 inline-flex items-center gap-1.5 px-2.5 py-1 bg-indigo-50/80 border border-indigo-100 rounded-md">
              <span className="text-[11px] font-bold text-indigo-900 uppercase tracking-wide">
                Clinical Pathology:
              </span>
              <span className="text-xs font-mono text-indigo-700 font-semibold">
                {finding.scientific_term}
              </span>
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          <span className={`px-3 py-1.5 text-xs font-bold rounded-full border uppercase tracking-wider ${SEVERITY_BADGES[severity] || ''}`}>
            {severity} Risk
          </span>
        </div>
      </div>

      <div className="p-4 sm:p-6 space-y-6">
        {/* 1. ATHLETE-FRIENDLY TRANSLATION: What went wrong & Predicted injury */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 rounded-xl bg-amber-50/70 border border-amber-200/70">
            <div className="flex items-center gap-2 mb-1.5">
              <span className="p-1 bg-amber-200/80 text-amber-900 rounded">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </span>
              <h4 className="text-xs font-bold uppercase tracking-wider text-amber-900">
                What Was Done Wrong (Movement Flaw)
              </h4>
            </div>
            <p className="text-sm text-amber-950 font-medium leading-relaxed">
              {finding.rationale}
            </p>
            {finding.mechanism && (
              <p className="text-xs text-amber-800/90 mt-2 pt-2 border-t border-amber-200/60 leading-normal">
                <span className="font-semibold text-amber-900">Impact: </span>
                {finding.mechanism}
              </p>
            )}
          </div>

          <div className="p-4 rounded-xl bg-rose-50/70 border border-rose-200/70">
            <div className="flex items-center gap-2 mb-1.5">
              <span className="p-1 bg-rose-200/80 text-rose-900 rounded">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </span>
              <h4 className="text-xs font-bold uppercase tracking-wider text-rose-900">
                Injury Predicted If Uncorrected
              </h4>
            </div>
            {finding.structures_at_risk?.length > 0 ? (
              <ul className="text-sm text-rose-950 space-y-1 mt-1">
                {finding.structures_at_risk.map((struct, idx) => (
                  <li key={idx} className="flex items-start gap-1.5 font-medium">
                    <span className="text-rose-500 font-bold">•</span>
                    <span>{struct}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-rose-900 font-medium">
                Musculoskeletal fatigue and compensatory overload across secondary stabilizers.
              </p>
            )}
          </div>
        </div>

        {/* 2. VISUAL STICK FIGURE COMPARISON: Flawed vs Correct Movement */}
        <BiomechanicalStickFigure
          finding={finding}
          activityType={activityType}
          keypointsData={keypointsData}
        />

        {/* 3. TECHNICAL CALCULATIONS & METRICS (Coach / Physio View) */}
        {finding.evidence?.length > 0 && (
          <div className="p-4 bg-gray-50 rounded-xl border border-gray-200">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold uppercase tracking-wider text-gray-700">
                  Technical Calculations & Threshold Violations
                </span>
                <span className="text-[10px] font-mono bg-gray-200 text-gray-700 px-1.5 py-0.5 rounded">
                  Kinematic Measurements
                </span>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead>
                  <tr className="border-b border-gray-200 text-gray-500 uppercase tracking-wider">
                    <th className="py-2 pr-4 font-semibold">Biomechanical Metric</th>
                    <th className="py-2 px-4 font-semibold text-right">Detected Value</th>
                    <th className="py-2 px-4 font-semibold text-center">Threshold / Norm</th>
                    <th className="py-2 pl-4 font-semibold text-right">Evaluation</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {finding.evidence.map((ev, i) => {
                    const isExceeded = ev.metric.includes('asymmetry') || ev.metric.includes('max') || ev.metric.includes('mean');
                    const cleanMetric = ev.metric.replace(/_/g, ' ');

                    return (
                      <tr key={i} className="hover:bg-white/80 transition-colors">
                        <td className="py-2.5 pr-4 font-medium text-gray-800 capitalize">
                          {cleanMetric}
                        </td>
                        <td className="py-2.5 px-4 font-mono font-bold text-gray-900 text-right">
                          {typeof ev.value === 'number' ? ev.value : '—'} {ev.unit}
                        </td>
                        <td className="py-2.5 px-4 text-center font-mono text-gray-600">
                          {ev.metric.includes('asymmetry') ? '≤ 5.0 °' : 'Within physiological range'}
                        </td>
                        <td className="py-2.5 pl-4 text-right">
                          <span className={`inline-flex px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                            ev.value > 5 && ev.metric.includes('asymmetry')
                              ? 'bg-red-100 text-red-800'
                              : 'bg-emerald-100 text-emerald-800'
                          }`}>
                            {ev.value > 5 && ev.metric.includes('asymmetry') ? 'Beyond Recommended' : 'Measured'}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* 4. ANATOMICAL BREAKDOWN: Overactive vs Underactive Muscles */}
        {(musclesOver.length > 0 || musclesUnder.length > 0 || primaryMuscles.length > 0) && (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 text-xs">
            {musclesOver.length > 0 && (
              <div className="p-3 rounded-lg bg-orange-50/80 border border-orange-200">
                <span className="font-bold text-orange-950 uppercase tracking-wider block mb-1">
                  Overactive / Dominant (Tight/Guarding)
                </span>
                <p className="text-orange-900 font-medium">
                  {musclesOver.join('; ')}
                </p>
                <span className="text-[10px] text-orange-700/80 mt-1 block">
                  Action: Foam roll / release & lengthen
                </span>
              </div>
            )}

            {musclesUnder.length > 0 && (
              <div className="p-3 rounded-lg bg-blue-50/80 border border-blue-200">
                <span className="font-bold text-blue-950 uppercase tracking-wider block mb-1">
                  Underactive / Inhibited (Weak/Sluggish)
                </span>
                <p className="text-blue-900 font-medium">
                  {musclesUnder.join('; ')}
                </p>
                <span className="text-[10px] text-blue-700/80 mt-1 block">
                  Action: Activate & strengthen progressively
                </span>
              </div>
            )}

            {stabilizers.length > 0 && (
              <div className="p-3 rounded-lg bg-purple-50/80 border border-purple-200">
                <span className="font-bold text-purple-950 uppercase tracking-wider block mb-1">
                  Joint Stabilizers
                </span>
                <p className="text-purple-900 font-medium">
                  {stabilizers.join('; ')}
                </p>
                <span className="text-[10px] text-purple-700/80 mt-1 block">
                  Action: Unilateral balance & proprioception
                </span>
              </div>
            )}
          </div>
        )}

        {/* 5. STEPS TO MITIGATE & CORRECT */}
        {finding.recommended_actions?.length > 0 && (
          <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200">
            <div className="flex items-center gap-2 mb-2">
              <span className="p-1 bg-emerald-200/80 text-emerald-900 rounded">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </span>
              <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-950">
                Actionable Steps to Mitigate Risk & Fix Form
              </h4>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2">
              {finding.recommended_actions.map((act, i) => (
                <div key={i} className="flex items-start gap-2 text-xs font-medium text-emerald-950 bg-white/70 p-2.5 rounded-lg border border-emerald-100">
                  <span className="w-5 h-5 rounded-full bg-emerald-600 text-white flex items-center justify-center text-[10px] font-bold flex-shrink-0">
                    {i + 1}
                  </span>
                  <span>{act}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default FindingCard;
