"use client";

import { useState } from "react";
import type { VectorPostureData } from "@/lib/types";
import { Icon } from "@/components/icons";

interface PostureVectorCardProps {
  trainee: VectorPostureData;
  benchmark?: VectorPostureData | null;
  title?: string;
  subtitle?: string;
}

/**
 * Renders an SVG stick figure from normalized coordinates.
 * Features:
 * - Visibility gating (occluded joints with <0.5 visibility omitted/dimmed)
 * - View-discipline awareness (sagittal lateral profile vs frontal alignment)
 * - Reference alignment and plumb line from mid-shoulder to ground
 * - Joint angle arcs and badges
 */
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
  const vis = data.visibilities || {};

  const isSagittal = data.camera_view === "sagittal" || data.camera_view === "side";
  const visibleSide = data.visible_side || (isSagittal ? "right" : "both");

  // Visibility threshold gate (< 0.5 is occluded/unreliable per SCIENCE_CONSTRAINTS)
  const isVis = (name: string, fallback = 1.0): boolean => {
    return vis[name] !== undefined ? vis[name] >= 0.5 : fallback >= 0.5;
  };

  const hasValgus = !isSagittal && faults.includes("knee_valgus");
  const hasLean = faults.includes("excessive_trunk_lean");

  // Key joints
  const nose = lm.nose;
  const ls = lm.left_shoulder;
  const rs = lm.right_shoulder;
  const le = lm.left_elbow;
  const re = lm.right_elbow;
  const lw = lm.left_wrist;
  const rw = lm.right_wrist;
  const lh = lm.left_hip;
  const rh = lm.right_hip;
  const lk = lm.left_knee;
  const rk = lm.right_knee;
  const la = lm.left_ankle;
  const ra = lm.right_ankle;
  const ms = lm.mid_shoulder || (ls && rs ? [(ls[0] + rs[0]) / 2, (ls[1] + rs[1]) / 2] : ls || rs);
  const mh = lm.mid_hip || (lh && rh ? [(lh[0] + rh[0]) / 2, (lh[1] + rh[1]) / 2] : lh || rh);

  const groundY = data.ground_y || 360;

  // Color selection
  let boneColor = "#38bdf8"; // Cyan
  let jointColor = "#ffffff";
  let spineColor = "#38bdf8";
  let valgusColor = "#38bdf8";

  if (colorScheme === "benchmark") {
    boneColor = "#10b981"; // Emerald
    jointColor = "#ecfdf5";
    spineColor = "#10b981";
    valgusColor = "#10b981";
  } else if (colorScheme === "ghost_trainee") {
    boneColor = "#f43f5e"; // Rose
    jointColor = "#fff1f2";
    spineColor = "#f43f5e";
    valgusColor = "#f43f5e";
  } else {
    // Dynamic fault highlighting
    if (hasLean) {
      spineColor = "#f59e0b"; // Amber warning
    }
    if (hasValgus) {
      valgusColor = "#ef4444"; // Red fault
    }
  }

  // Determine which side is foreground/visible for sagittal views
  const showLeftLeg = isSagittal ? visibleSide === "left" || (isVis("left_knee") && isVis("left_ankle")) : isVis("left_knee");
  const showRightLeg = isSagittal ? visibleSide === "right" || (isVis("right_knee") && isVis("right_ankle")) : isVis("right_knee");
  const leftLegDimmed = isSagittal && visibleSide === "right";
  const rightLegDimmed = isSagittal && visibleSide === "left";

  const showLeftArm = isVis("left_elbow");
  const showRightArm = isVis("right_elbow");

  // Primary knee for badge placement
  const primaryKnee = visibleSide === "right" ? (rk || lk) : (lk || rk);
  const displayDepth = Math.round(
    Number(
      angles.knee_flexion ??
      (visibleSide === "right" ? (angles.knee_flexion_right ?? angles.knee_flexion_left) : (angles.knee_flexion_left ?? angles.knee_flexion_right)) ??
      90
    )
  );

  return (
    <g opacity={opacity}>
      {/* Plumb Line (Center of Mass reference from Mid-Shoulder) */}
      {ms && (
        <line
          x1={ms[0]}
          y1={ms[1]}
          x2={ms[0]}
          y2={groundY}
          stroke="#64748b"
          strokeWidth="1.2"
          strokeDasharray="4 4"
          opacity="0.7"
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
          strokeWidth="2.8"
        />
      )}

      {/* Shoulder Axis (only in frontal or if both shoulders visible) */}
      {ls && rs && (!isSagittal || (isVis("left_shoulder") && isVis("right_shoulder"))) && (
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
      {lh && rh && (!isSagittal || (isVis("left_hip") && isVis("right_hip"))) && (
        <line x1={lh[0]} y1={lh[1]} x2={rh[0]} y2={rh[1]} stroke={boneColor} strokeWidth="3" strokeLinecap="round" />
      )}

      {/* Left Arm */}
      {showLeftArm && ls && le && (
        <line
          x1={ls[0]}
          y1={ls[1]}
          x2={le[0]}
          y2={le[1]}
          stroke={boneColor}
          strokeWidth="2.5"
          strokeLinecap="round"
          opacity={isSagittal && visibleSide === "right" ? 0.35 : 1}
        />
      )}
      {showLeftArm && isVis("left_wrist") && le && lw && (
        <line
          x1={le[0]}
          y1={le[1]}
          x2={lw[0]}
          y2={lw[1]}
          stroke={boneColor}
          strokeWidth="2.5"
          strokeLinecap="round"
          opacity={isSagittal && visibleSide === "right" ? 0.35 : 1}
        />
      )}

      {/* Right Arm */}
      {showRightArm && rs && re && (
        <line
          x1={rs[0]}
          y1={rs[1]}
          x2={re[0]}
          y2={re[1]}
          stroke={boneColor}
          strokeWidth="2.5"
          strokeLinecap="round"
          opacity={isSagittal && visibleSide === "left" ? 0.35 : 1}
        />
      )}
      {showRightArm && isVis("right_wrist") && re && rw && (
        <line
          x1={re[0]}
          y1={re[1]}
          x2={rw[0]}
          y2={rw[1]}
          stroke={boneColor}
          strokeWidth="2.5"
          strokeLinecap="round"
          opacity={isSagittal && visibleSide === "left" ? 0.35 : 1}
        />
      )}

      {/* Left Leg */}
      {showLeftLeg && lh && lk && (
        <line
          x1={lh[0]}
          y1={lh[1]}
          x2={lk[0]}
          y2={lk[1]}
          stroke={leftLegDimmed ? "#64748b" : valgusColor}
          strokeWidth={leftLegDimmed ? "2.5" : "3.5"}
          strokeDasharray={leftLegDimmed ? "4 2" : undefined}
          strokeLinecap="round"
          opacity={leftLegDimmed ? 0.45 : 1}
        />
      )}
      {showLeftLeg && lk && la && (
        <line
          x1={lk[0]}
          y1={lk[1]}
          x2={la[0]}
          y2={la[1]}
          stroke={leftLegDimmed ? "#64748b" : valgusColor}
          strokeWidth={leftLegDimmed ? "2.5" : "3.5"}
          strokeDasharray={leftLegDimmed ? "4 2" : undefined}
          strokeLinecap="round"
          opacity={leftLegDimmed ? 0.45 : 1}
        />
      )}

      {/* Right Leg */}
      {showRightLeg && rh && rk && (
        <line
          x1={rh[0]}
          y1={rh[1]}
          x2={rk[0]}
          y2={rk[1]}
          stroke={rightLegDimmed ? "#64748b" : boneColor}
          strokeWidth={rightLegDimmed ? "2.5" : "3.5"}
          strokeDasharray={rightLegDimmed ? "4 2" : undefined}
          strokeLinecap="round"
          opacity={rightLegDimmed ? 0.45 : 1}
        />
      )}
      {showRightLeg && rk && ra && (
        <line
          x1={rk[0]}
          y1={rk[1]}
          x2={ra[0]}
          y2={ra[1]}
          stroke={rightLegDimmed ? "#64748b" : boneColor}
          strokeWidth={rightLegDimmed ? "2.5" : "3.5"}
          strokeDasharray={rightLegDimmed ? "4 2" : undefined}
          strokeLinecap="round"
          opacity={rightLegDimmed ? 0.45 : 1}
        />
      )}

      {/* Feet Base */}
      {showLeftLeg && la && lm.left_foot_index && isVis("left_foot_index") && (
        <line
          x1={la[0]}
          y1={la[1]}
          x2={lm.left_foot_index[0]}
          y2={lm.left_foot_index[1]}
          stroke={leftLegDimmed ? "#64748b" : boneColor}
          strokeWidth="2.5"
          strokeLinecap="round"
          opacity={leftLegDimmed ? 0.45 : 1}
        />
      )}
      {showRightLeg && ra && lm.right_foot_index && isVis("right_foot_index") && (
        <line
          x1={ra[0]}
          y1={ra[1]}
          x2={lm.right_foot_index[0]}
          y2={lm.right_foot_index[1]}
          stroke={rightLegDimmed ? "#64748b" : boneColor}
          strokeWidth="2.5"
          strokeLinecap="round"
          opacity={rightLegDimmed ? 0.45 : 1}
        />
      )}

      {/* Joint Nodes (White circular nodes for visible points) */}
      {[
        { pt: ls, visName: "left_shoulder" },
        { pt: rs, visName: "right_shoulder" },
        { pt: le, visName: "left_elbow" },
        { pt: re, visName: "right_elbow" },
        { pt: lw, visName: "left_wrist" },
        { pt: rw, visName: "right_wrist" },
        { pt: lh, visName: "left_hip" },
        { pt: rh, visName: "right_hip" },
        { pt: lk, visName: "left_knee" },
        { pt: rk, visName: "right_knee" },
        { pt: la, visName: "left_ankle" },
        { pt: ra, visName: "right_ankle" },
      ].map(({ pt, visName }, i) =>
        pt && isVis(visName) ? (
          <circle
            key={i}
            cx={pt[0]}
            cy={pt[1]}
            r={i >= 6 ? "4" : "3.2"}
            fill={i === 8 && hasValgus && colorScheme !== "benchmark" ? "#ef4444" : jointColor}
            stroke={jointColor}
            strokeWidth="1.8"
            opacity={
              isSagittal && ((visibleSide === "right" && visName.startsWith("left")) || (visibleSide === "left" && visName.startsWith("right")))
                ? 0.45
                : 1
            }
          />
        ) : null
      )}

      {/* Dynamic Valgus Inward Warning Arrow if present (frontal view only) */}
      {hasValgus && lk && colorScheme !== "benchmark" && (
        <g transform={`translate(${lk[0] + 6}, ${lk[1] - 8})`}>
          <path d="M 0 0 L 12 0 M 8 -4 L 12 0 L 8 4" stroke="#ef4444" strokeWidth="2" fill="none" />
        </g>
      )}

      {/* Angle Callout Badges */}
      {colorScheme !== "ghost_trainee" && (
        <>
          {primaryKnee && (
            <g transform={`translate(${primaryKnee[0] + (visibleSide === "right" ? 8 : -44)}, ${primaryKnee[1] - 12})`}>
              <rect x="0" y="0" width="38" height="18" rx="4" fill="#0f172a" fillOpacity="0.9" stroke="#38bdf8" strokeWidth="0.8" />
              <text x="19" y="13" textAnchor="middle" fill="#38bdf8" fontSize="10" fontWeight="bold">
                {displayDepth}°
              </text>
            </g>
          )}

          {angles.trunk_lean != null && ms && (
            <g transform={`translate(${ms[0] + 10}, ${ms[1] + 16})`}>
              <rect
                x="0"
                y="0"
                width="48"
                height="18"
                rx="4"
                fill={hasLean ? "#7f1d1d" : "#0f172a"}
                fillOpacity="0.9"
                stroke={hasLean ? "#ef4444" : "#64748b"}
                strokeWidth="0.8"
              />
              <text x="24" y="13" textAnchor="middle" fill="#ffffff" fontSize="10" fontWeight="bold">
                {Math.round(Number(angles.trunk_lean))}° lean
              </text>
            </g>
          )}
        </>
      )}

      {/* Figure Title / Label */}
      {label && (
        <text x="150" y="30" textAnchor="middle" fill="#94a3b8" fontSize="12" fontWeight="600">
          {label}
        </text>
      )}
    </g>
  );
}

export function PostureVectorCard({
  trainee,
  benchmark,
  title = "Biomechanical Posture Twin Comparison",
  subtitle = "Inflection Frame Kinematics & Alignment Standard",
}: PostureVectorCardProps) {
  const [viewMode, setViewMode] = useState<"side_by_side" | "ghost_overlay">("side_by_side");

  const isSagittal = trainee?.camera_view === "sagittal" || trainee?.camera_view === "side";
  const visibleSide = trainee?.visible_side || (isSagittal ? "right" : "both");

  const faults = trainee?.faults || [];
  const hasValgus = !isSagittal && faults.includes("knee_valgus");
  const hasLean = faults.includes("excessive_trunk_lean");

  const traineeDepth = Math.round(
    Number(
      trainee?.angles?.knee_flexion ??
      (visibleSide === "right" ? (trainee?.angles?.knee_flexion_right ?? trainee?.angles?.knee_flexion_left) : (trainee?.angles?.knee_flexion_left ?? trainee?.angles?.knee_flexion_right)) ??
      90
    )
  );
  const traineeLean = Math.round(Number(trainee?.angles?.trunk_lean ?? 15));

  const benchmarkDepth = Math.round(
    Number(
      benchmark?.angles?.knee_flexion ??
      (benchmark?.visible_side === "right" ? (benchmark?.angles?.knee_flexion_right ?? benchmark?.angles?.knee_flexion_left) : (benchmark?.angles?.knee_flexion_left ?? benchmark?.angles?.knee_flexion_right)) ??
      95
    )
  );
  const benchmarkLean = Math.round(Number(benchmark?.angles?.trunk_lean ?? 15));

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
              className={`rounded-lg px-3 py-1.5 transition-all cursor-pointer ${viewMode === "side_by_side"
                  ? "bg-white text-ink shadow-sm font-bold"
                  : "text-ink-3 hover:text-ink"
                }`}
            >
              Side-by-Side
            </button>
            <button
              type="button"
              onClick={() => setViewMode("ghost_overlay")}
              className={`rounded-lg px-3 py-1.5 transition-all cursor-pointer ${viewMode === "ghost_overlay"
                  ? "bg-white text-ink shadow-sm font-bold"
                  : "text-ink-3 hover:text-ink"
                }`}
            >
              Ghost Overlay
            </button>
          </div>
        )}
      </div>

      {/* SVG Canvas Stage */}
      <div className="mt-6 flex flex-col items-center">
        {viewMode === "side_by_side" || !benchmark ? (
            <div className={`w-full max-w-3xl ${benchmark ? "grid grid-cols-1 gap-6 sm:grid-cols-2" : "flex justify-center"}`}>
              {/* Trainee Figure Card */}
              <div className="flex flex-col items-center rounded-2xl bg-[#091122] border border-slate-800 p-5 shadow-sm">
                <span className="mb-3 inline-flex items-center gap-1.5 rounded-full bg-amber-500/15 border border-amber-500/30 px-3 py-1 text-xs font-semibold text-amber-300">
                  <span className="h-2 w-2 rounded-full bg-amber-400 animate-pulse" />
                  Observed Posture (Your Clip)
                </span>

                <div className="w-full flex justify-center py-1">
                  <svg viewBox="0 0 300 400" className="h-68 w-full max-w-[240px]">
                    {/* Ground Line */}
                    <line x1="20" y1="360" x2="280" y2="360" stroke="#334155" strokeWidth="2" strokeDasharray="4 4" />
                    <SkeletonFigure data={trainee} colorScheme="dynamic" />
                  </svg>
                </div>

                <div className="mt-3 flex items-center justify-around w-full border-t border-slate-800/80 pt-3 text-xs text-slate-300">
                  <span>
                    Flexion Depth: <strong className="text-cyan-400 font-bold ml-1">{traineeDepth}°</strong>
                  </span>
                  <span>•</span>
                  <span>
                    Torso Lean: <strong className="text-amber-400 font-bold ml-1">{traineeLean}°</strong>
                  </span>
                </div>
              </div>

              {/* Benchmark Figure Card */}
              {benchmark && (
                <div className="flex flex-col items-center rounded-2xl bg-[#091122] border border-slate-800 p-5 shadow-sm">
                  <span className="mb-3 inline-flex items-center gap-1.5 rounded-full bg-emerald-500/15 border border-emerald-500/30 px-3 py-1 text-xs font-semibold text-emerald-300">
                    <span className="h-2 w-2 rounded-full bg-emerald-400" />
                    Target Movement Alignment
                  </span>

                  <div className="w-full flex justify-center py-1">
                    <svg viewBox="0 0 300 400" className="h-68 w-full max-w-[240px]">
                      {/* Ground Line */}
                      <line x1="20" y1="360" x2="280" y2="360" stroke="#334155" strokeWidth="2" strokeDasharray="4 4" />
                      <SkeletonFigure data={benchmark} colorScheme="benchmark" />
                    </svg>
                  </div>

                  <div className="mt-3 flex items-center justify-around w-full border-t border-slate-800/80 pt-3 text-xs text-slate-300">
                    <span>
                      Target Depth: <strong className="text-emerald-400 font-bold ml-1">{benchmarkDepth}°</strong>
                    </span>
                    <span>•</span>
                    <span>
                      Target Lean: <strong className="text-emerald-400 font-bold ml-1">{benchmarkLean}°</strong>
                    </span>
                  </div>
                </div>
              )}
            </div>
            ) : (
            /* Ghost Overlay View */
            <div className="flex flex-col items-center rounded-2xl bg-[#091122] border border-slate-800 p-6 shadow-sm w-full max-w-md">
              <div className="mb-4 flex items-center gap-4 text-xs font-semibold">
                <span className="inline-flex items-center gap-1.5 text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-2.5 py-1 rounded-full">
                  <span className="h-2 w-2 rounded-full bg-emerald-400" />
                  Benchmark Standard
                </span>
                <span className="inline-flex items-center gap-1.5 text-rose-400 bg-rose-500/10 border border-rose-500/30 px-2.5 py-1 rounded-full">
                  <span className="h-2 w-2 rounded-full bg-rose-400" />
                  Your Form (Superimposed)
                </span>
              </div>

              <div className="w-full flex justify-center py-2">
                <svg viewBox="0 0 300 400" className="h-76 w-full max-w-[280px]">
                  <line x1="20" y1="360" x2="280" y2="360" stroke="#334155" strokeWidth="2" strokeDasharray="4 4" />
                  {/* Benchmark Layer (Green, semi-transparent) */}
                  <SkeletonFigure data={benchmark} colorScheme="benchmark" opacity={0.45} />
                  {/* Trainee Layer (Red, prominent) */}
                  <SkeletonFigure data={trainee} colorScheme="ghost_trainee" opacity={0.9} />
                </svg>
              </div>

              <p className="mt-3 text-center text-xs text-slate-400 max-w-sm">
                Notice the divergence between the green target alignment and the red trainee pose at peak inflection.
              </p>
            </div>
        )}

            {/* Fault Highlights & Actionable Guidance Strip */}
            <div className="mt-6 w-full border-t border-black/5 pt-4">
              <p className="stat-label text-xs uppercase tracking-wider text-slate-500 font-bold">
                Biomechanical Key Findings
              </p>
              <div className="mt-2.5 flex flex-wrap gap-2.5">
                {isSagittal ? (
                  <>
                    {/* Sagittal Depth Findings */}
                    {traineeDepth <= 92 ? (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-emerald-50 border border-emerald-200 text-emerald-800">
                        <Icon name="check" className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                        <span>Parallel Depth: Full functional range reached ({traineeDepth}°)</span>
                      </span>
                    ) : traineeDepth <= 115 ? (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-sky-50 border border-sky-200 text-sky-800">
                        <Icon name="info" className="h-3.5 w-3.5 text-sky-600 shrink-0" />
                        <span>Working Depth: Moderate flexion range ({traineeDepth}°)</span>
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-amber-50 border border-amber-200 text-amber-800">
                        <Icon name="alert" className="h-3.5 w-3.5 text-amber-600 shrink-0" />
                        <span>Partial Depth: High inflection turnaround ({traineeDepth}°)</span>
                      </span>
                    )}

                    {/* Sagittal Torso Lean */}
                    {hasLean ? (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-amber-50 border border-amber-200 text-amber-800">
                        <Icon name="alert" className="h-3.5 w-3.5 text-amber-600 shrink-0" />
                        <span>Excessive Trunk Lean: Forward inclination &gt; 35° ({traineeLean}°)</span>
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-emerald-50 border border-emerald-200 text-emerald-800">
                        <Icon name="check" className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                        <span>Upright Torso: Controlled lumbar incline ({traineeLean}°)</span>
                      </span>
                    )}

                    {/* View Angle Methodology Note */}
                    <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-slate-100 border border-slate-200 text-slate-700">
                      <Icon name="info" className="h-3.5 w-3.5 text-slate-500 shrink-0" />
                      <span>Lateral Profile: Sagittal view (frontal valgus not assessable)</span>
                    </span>
                  </>
                ) : (
                  <>
                    {/* Frontal Camera View Alignment */}
                    {hasValgus ? (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-rose-50 border border-rose-200 text-rose-800">
                        <Icon name="alert" className="h-3.5 w-3.5 text-rose-600 shrink-0" />
                        <span>Knee Dynamic Valgus: Medial collapse during descent</span>
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-emerald-50 border border-emerald-200 text-emerald-800">
                        <Icon name="check" className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                        <span>Frontal Alignment: Knees tracked over feet</span>
                      </span>
                    )}

                    {hasLean ? (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-amber-50 border border-amber-200 text-amber-800">
                        <Icon name="alert" className="h-3.5 w-3.5 text-amber-600 shrink-0" />
                        <span>Lateral Spine Shift: Torso lateral deviation detected</span>
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-emerald-50 border border-emerald-200 text-emerald-800">
                        <Icon name="check" className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                        <span>Spine Alignment: Centered thoracic posture</span>
                      </span>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>
    </div>
      );
}
