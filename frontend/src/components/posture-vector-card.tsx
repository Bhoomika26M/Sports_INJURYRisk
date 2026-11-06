"use client";

import { useState } from "react";
import type { VectorPostureData } from "@/lib/types";
import { Icon } from "@/components/icons";

interface PostureVectorCardProps {
  trainee: VectorPostureData;
  benchmark?: VectorPostureData;
  title?: string;
  subtitle?: string;
}

/** Draws a single skeleton inside an SVG viewport (300 x 400). */
function SkeletonFigure({
  data,
  colorScheme = "dynamic",
  opacity = 1.0,
  label,
}: {
  data: VectorPostureData;
  colorScheme?: "dynamic" | "benchmark" | "ghost_trainee";
  opacity?: number;
  label?: string;
}) {
  const lm = data.landmarks || {};
  const angles = data.angles || {};
  const faults = data.faults || [];

  const hasValgus = faults.includes("knee_valgus");
  const hasLean = faults.includes("excessive_trunk_lean");

  // Determine colors based on scheme
  let boneColor = "#10b981"; // Emerald
  let jointColor = "#059669";
  let spineColor = "#10b981";
  let valgusColor = "#10b981";

  if (colorScheme === "benchmark") {
    boneColor = "#10b981";
    jointColor = "#059669";
    spineColor = "#10b981";
    valgusColor = "#10b981";
  } else if (colorScheme === "ghost_trainee") {
    boneColor = "#f43f5e"; // Rose
    jointColor = "#e11d48";
    spineColor = hasLean ? "#f59e0b" : "#f43f5e";
    valgusColor = "#ef4444";
  } else {
    // Dynamic
    boneColor = "#10b981";
    spineColor = hasLean ? "#f59e0b" : "#10b981";
    valgusColor = hasValgus ? "#ef4444" : "#10b981";
    jointColor = hasValgus ? "#dc2626" : "#059669";
  }

  const p = (name: string): [number, number] | null => {
    const pt = lm[name];
    return pt && pt.length >= 2 ? [pt[0], pt[1]] : null;
  };

  const nose = p("nose");
  const ls = p("left_shoulder");
  const rs = p("right_shoulder");
  const ms = p("mid_shoulder");
  const le = p("left_elbow");
  const re = p("right_elbow");
  const lw = p("left_wrist");
  const rw = p("right_wrist");
  const lh = p("left_hip");
  const rh = p("right_hip");
  const mh = p("mid_hip");
  const lk = p("left_knee");
  const rk = p("right_knee");
  const la = p("left_ankle");
  const ra = p("right_ankle");

  const groundY = data.ground_y || 360;

  return (
    <g opacity={opacity}>
      {/* Plumb Line (Center of Mass reference from Mid-Shoulder) */}
      {ms && (
        <line
          x1={ms[0]}
          y1={ms[1]}
          x2={ms[0]}
          y2={groundY}
          stroke="#94a3b8"
          strokeWidth="1.2"
          strokeDasharray="3 3"
          opacity="0.6"
        />
      )}

      {/* Head */}
      {nose && (
        <circle
          cx={nose[0]}
          cy={nose[1]}
          r="14"
          fill="none"
          stroke={boneColor}
          strokeWidth="2.5"
        />
      )}

      {/* Shoulder Axis */}
      {ls && rs && (
        <line x1={ls[0]} y1={ls[1]} x2={rs[0]} y2={rs[1]} stroke={boneColor} strokeWidth="3" strokeLinecap="round" />
      )}

      {/* Spine (Mid-Shoulder to Mid-Hip) */}
      {ms && mh && (
        <line
          x1={ms[0]}
          y1={ms[1]}
          x2={mh[0]}
          y2={mh[1]}
          stroke={spineColor}
          strokeWidth="3.5"
          strokeLinecap="round"
        />
      )}

      {/* Pelvic Axis */}
      {lh && rh && (
        <line x1={lh[0]} y1={lh[1]} x2={rh[0]} y2={rh[1]} stroke={boneColor} strokeWidth="3" strokeLinecap="round" />
      )}

      {/* Left Arm */}
      {ls && le && <line x1={ls[0]} y1={ls[1]} x2={le[0]} y2={le[1]} stroke={boneColor} strokeWidth="2.5" strokeLinecap="round" />}
      {le && lw && <line x1={le[0]} y1={le[1]} x2={lw[0]} y2={lw[1]} stroke={boneColor} strokeWidth="2.5" strokeLinecap="round" />}

      {/* Right Arm */}
      {rs && re && <line x1={rs[0]} y1={rs[1]} x2={re[0]} y2={re[1]} stroke={boneColor} strokeWidth="2.5" strokeLinecap="round" />}
      {re && rw && <line x1={re[0]} y1={re[1]} x2={rw[0]} y2={rw[1]} stroke={boneColor} strokeWidth="2.5" strokeLinecap="round" />}

      {/* Left Leg */}
      {lh && lk && (
        <line
          x1={lh[0]}
          y1={lh[1]}
          x2={lk[0]}
          y2={lk[1]}
          stroke={valgusColor}
          strokeWidth="3.5"
          strokeLinecap="round"
        />
      )}
      {lk && la && (
        <line
          x1={lk[0]}
          y1={lk[1]}
          x2={la[0]}
          y2={la[1]}
          stroke={valgusColor}
          strokeWidth="3.5"
          strokeLinecap="round"
        />
      )}

      {/* Right Leg */}
      {rh && rk && (
        <line
          x1={rh[0]}
          y1={rh[1]}
          x2={rk[0]}
          y2={rk[1]}
          stroke={valgusColor}
          strokeWidth="3.5"
          strokeLinecap="round"
        />
      )}
      {rk && ra && (
        <line
          x1={rk[0]}
          y1={rk[1]}
          x2={ra[0]}
          y2={ra[1]}
          stroke={valgusColor}
          strokeWidth="3.5"
          strokeLinecap="round"
        />
      )}

      {/* Feet Base */}
      {la && <line x1={la[0] - 8} y1={la[1]} x2={la[0] + 8} y2={la[1]} stroke={boneColor} strokeWidth="2.5" />}
      {ra && <line x1={ra[0] - 8} y1={ra[1]} x2={ra[0] + 8} y2={ra[1]} stroke={boneColor} strokeWidth="2.5" />}

      {/* Joint Nodes */}
      {[ls, rs, le, re, lw, rw, lh, rh, lk, rk, la, ra].map((joint, idx) =>
        joint ? (
          <circle
            key={idx}
            cx={joint[0]}
            cy={joint[1]}
            r="4"
            fill="#ffffff"
            stroke={jointColor}
            strokeWidth="2"
          />
        ) : null
      )}

      {/* Dynamic Valgus Inward Warning Arrow if present */}
      {hasValgus && lk && colorScheme !== "benchmark" && (
        <g transform={`translate(${lk[0] + 6}, ${lk[1] - 8})`}>
          <path d="M 0 0 L 12 0 M 8 -4 L 12 0 L 8 4" stroke="#ef4444" strokeWidth="2" fill="none" />
        </g>
      )}

      {/* Angle Callout Badges */}
      {colorScheme !== "ghost_trainee" && (
        <>
          {angles.knee_flexion_left != null && lk && (
            <g transform={`translate(${lk[0] - 38}, ${lk[1] - 12})`}>
              <rect x="0" y="0" width="34" height="18" rx="4" fill="#0f172a" fillOpacity="0.85" />
              <text x="17" y="13" textAnchor="middle" fill="#38bdf8" fontSize="10" fontWeight="bold">
                {Math.round(Number(angles.knee_flexion_left))}°
              </text>
            </g>
          )}

          {angles.trunk_lean != null && ms && (
            <g transform={`translate(${ms[0] + 10}, ${ms[1] + 16})`}>
              <rect
                x="0"
                y="0"
                width="42"
                height="18"
                rx="4"
                fill={hasLean ? "#ef4444" : "#0f172a"}
                fillOpacity="0.9"
              />
              <text x="21" y="13" textAnchor="middle" fill="#ffffff" fontSize="10" fontWeight="bold">
                {Math.round(Number(angles.trunk_lean))}° lean
              </text>
            </g>
          )}
        </>
      )}

      {/* Figure Title / Label */}
      {label && (
        <text x="150" y="30" textAnchor="middle" fill="#334155" fontSize="12" fontWeight="600">
          {label}
        </text>
      )}
    </g>
  );
}

export function PostureVectorCard({
  trainee,
  benchmark,
  title = "Biomechanical Posture Twin",
  subtitle = "Inflection Frame Kinematics & Alignment Standard",
}: PostureVectorCardProps) {
  const [viewMode, setViewMode] = useState<"side_by_side" | "ghost_overlay">("side_by_side");

  const faults = trainee?.faults || [];
  const hasValgus = faults.includes("knee_valgus");
  const hasLean = faults.includes("excessive_trunk_lean");

  return (
    <div className="card p-6">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-black/5 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand-light text-brand-dark">
              <Icon name="activity" className="h-4 w-4" />
            </span>
            <h3 className="text-lg font-bold tracking-tight text-ink">{title}</h3>
          </div>
          <p className="mt-1 text-xs text-ink-3">{subtitle}</p>
        </div>

        {/* View Mode Toggle */}
        {benchmark && (
          <div className="flex items-center rounded-xl bg-surface-2 p-1 text-xs font-semibold">
            <button
              type="button"
              onClick={() => setViewMode("side_by_side")}
              className={`rounded-lg px-3 py-1.5 transition-all ${
                viewMode === "side_by_side"
                  ? "bg-white text-ink shadow-sm font-bold"
                  : "text-ink-3 hover:text-ink"
              }`}
            >
              Side-by-Side
            </button>
            <button
              type="button"
              onClick={() => setViewMode("ghost_overlay")}
              className={`rounded-lg px-3 py-1.5 transition-all ${
                viewMode === "ghost_overlay"
                  ? "bg-white text-ink shadow-sm font-bold"
                  : "text-ink-3 hover:text-ink"
              }`}
            >
              Ghost Overlay
            </button>
          </div>
        )}
      </div>

      {/* SVG Canvas Area */}
      <div className="mt-6 flex flex-col items-center">
        {viewMode === "side_by_side" || !benchmark ? (
          <div className="grid w-full max-w-2xl grid-cols-1 gap-6 sm:grid-cols-2">
            {/* Trainee Figure */}
            <div className="flex flex-col items-center rounded-2xl border border-black/5 bg-slate-900/5 p-4 dark:bg-slate-900">
              <span className="mb-2 inline-flex items-center gap-1.5 rounded-full bg-slate-200 px-2.5 py-0.5 text-[11px] font-semibold text-slate-700 dark:bg-slate-800 dark:text-slate-200">
                <span className="h-2 w-2 rounded-full bg-amber-500" />
                Observed Posture (Your Clip)
              </span>
              <svg viewBox="0 0 300 400" className="h-64 w-full max-w-[240px]">
                {/* Ground Line */}
                <line x1="20" y1="360" x2="280" y2="360" stroke="#cbd5e1" strokeWidth="2" strokeDasharray="4 4" />
                <SkeletonFigure data={trainee} colorScheme="dynamic" />
              </svg>
              <div className="mt-2 flex flex-wrap justify-center gap-2 text-[11px]">
                <span className="text-ink-3">Depth: <strong className="text-ink">{Math.round(trainee.angles.knee_flexion_left ?? 0)}°</strong></span>
                <span className="text-ink-3">Lean: <strong className="text-ink">{Math.round(trainee.angles.trunk_lean ?? 0)}°</strong></span>
              </div>
            </div>

            {/* Benchmark Figure */}
            {benchmark && (
              <div className="flex flex-col items-center rounded-2xl border border-black/5 bg-slate-900/5 p-4 dark:bg-slate-900">
                <span className="mb-2 inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200">
                  <span className="h-2 w-2 rounded-full bg-emerald-500" />
                  Target Movement Alignment
                </span>
                <svg viewBox="0 0 300 400" className="h-64 w-full max-w-[240px]">
                  {/* Ground Line */}
                  <line x1="20" y1="360" x2="280" y2="360" stroke="#cbd5e1" strokeWidth="2" strokeDasharray="4 4" />
                  <SkeletonFigure data={benchmark} colorScheme="benchmark" />
                </svg>
                <div className="mt-2 flex flex-wrap justify-center gap-2 text-[11px]">
                  <span className="text-ink-3">Target Depth: <strong className="text-ink">{Math.round(benchmark.angles.knee_flexion_left ?? 98)}°</strong></span>
                  <span className="text-ink-3">Target Lean: <strong className="text-ink">{Math.round(benchmark.angles.trunk_lean ?? 18)}°</strong></span>
                </div>
              </div>
            )}
          </div>
        ) : (
          /* Ghost Overlay View */
          <div className="flex flex-col items-center rounded-2xl border border-black/5 bg-slate-900/5 p-6 dark:bg-slate-900">
            <div className="mb-3 flex items-center gap-4 text-xs font-semibold">
              <span className="inline-flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400">
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
                Benchmark Standard
              </span>
              <span className="inline-flex items-center gap-1.5 text-rose-500">
                <span className="h-2.5 w-2.5 rounded-full bg-rose-500" />
                Your Form (Superimposed)
              </span>
            </div>
            <svg viewBox="0 0 300 400" className="h-72 w-full max-w-[280px]">
              <line x1="20" y1="360" x2="280" y2="360" stroke="#cbd5e1" strokeWidth="2" strokeDasharray="4 4" />
              {/* Benchmark Layer (Green, semi-transparent) */}
              <SkeletonFigure data={benchmark} colorScheme="benchmark" opacity={0.5} />
              {/* Trainee Layer (Red, prominent) */}
              <SkeletonFigure data={trainee} colorScheme="ghost_trainee" opacity={0.9} />
            </svg>
            <p className="mt-3 text-center text-xs text-ink-3 max-w-sm">
              Notice the divergence between the green target alignment and the red trainee pose at peak inflection.
            </p>
          </div>
        )}

        {/* Fault Highlights & Actionable Guidance Strip */}
        <div className="mt-6 w-full border-t border-black/5 pt-4">
          <p className="stat-label text-xs">Biomechanical Key Findings</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {hasValgus ? (
              <span className="badge badge-danger text-xs">
                ⚠️ Knee Dynamic Valgus: Medial collapse during descent
              </span>
            ) : (
              <span className="badge badge-ok text-xs">
                ✓ Frontal Alignment: Knees stacked over feet
              </span>
            )}

            {hasLean ? (
              <span className="badge badge-warn text-xs">
                ⚠️ Excessive Trunk Lean: Forward torso inclination &gt; 35°
              </span>
            ) : (
              <span className="badge badge-ok text-xs">
                ✓ Upright Torso: Controlled lumbar posture
              </span>
            )}

            {trainee?.angles?.knee_flexion_left != null && Number(trainee.angles.knee_flexion_left) < 80 && (
              <span className="badge badge-info text-xs">
                ℹ️ Depth: Partial depth reached ({Math.round(Number(trainee.angles.knee_flexion_left))}°)
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
