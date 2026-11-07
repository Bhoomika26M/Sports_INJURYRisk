"use client";

import { useState } from "react";
import type { PostureSnapshot } from "@/lib/types";
import { Icon } from "@/components/icons";

interface ComparisonPostureViewProps {
  snapshotA?: PostureSnapshot | null;
  snapshotB?: PostureSnapshot | null;
  labelA?: string;
  labelB?: string;
}

function SkeletonSvg({
  snapshot,
  color = "#38bdf8",
  opacity = 1.0,
}: {
  snapshot: PostureSnapshot;
  color?: string;
  opacity?: number;
}) {
  const lm = snapshot.landmarks || {};

  const getPt = (name: string): [number, number] | null => {
    const pt = lm[name];
    if (!pt || !Array.isArray(pt) || pt.length < 2) return null;
    return [pt[0], pt[1]];
  };

  const ls = getPt("left_shoulder");
  const rs = getPt("right_shoulder");
  const le = getPt("left_elbow");
  const re = getPt("right_elbow");
  const lw = getPt("left_wrist");
  const rw = getPt("right_wrist");
  const lh = getPt("left_hip");
  const rh = getPt("right_hip");
  const lk = getPt("left_knee");
  const rk = getPt("right_knee");
  const la = getPt("left_ankle");
  const ra = getPt("right_ankle");
  const nose = getPt("nose");

  const midShoulder: [number, number] | null =
    ls && rs ? [(ls[0] + rs[0]) / 2, (ls[1] + rs[1]) / 2] : null;
  const midHip: [number, number] | null =
    lh && rh ? [(lh[0] + rh[0]) / 2, (lh[1] + rh[1]) / 2] : null;

  const bones: [ [number, number] | null, [number, number] | null ][] = [
    [ls, rs],
    [ls, le],
    [le, lw],
    [rs, re],
    [re, rw],
    [midShoulder, midHip],
    [lh, rh],
    [lh, lk],
    [lk, la],
    [rh, rk],
    [rk, ra],
    [nose, midShoulder],
  ];

  return (
    <g opacity={opacity}>
      {bones.map(([p1, p2], i) => {
        if (!p1 || !p2) return null;
        return (
          <line
            key={i}
            x1={p1[0]}
            y1={p1[1]}
            x2={p2[0]}
            y2={p2[1]}
            stroke={color}
            strokeWidth="3.5"
            strokeLinecap="round"
          />
        );
      })}
      {[ls, rs, le, re, lw, rw, lh, rh, lk, rk, la, ra].map((pt, i) => {
        if (!pt) return null;
        return (
          <circle
            key={i}
            cx={pt[0]}
            cy={pt[1]}
            r="4.5"
            fill={color}
            stroke="#0f172a"
            strokeWidth="1.5"
          />
        );
      })}
      {nose && (
        <circle
          cx={nose[0]}
          cy={nose[1]}
          r="9"
          fill="none"
          stroke={color}
          strokeWidth="2.5"
        />
      )}
    </g>
  );
}

export function ComparisonPostureView({
  snapshotA,
  snapshotB,
  labelA = "Reference",
  labelB = "Comparison",
}: ComparisonPostureViewProps) {
  const [mode, setMode] = useState<"side_by_side" | "overlay">("side_by_side");

  const hasA = snapshotA && Object.keys(snapshotA.landmarks || {}).length > 0;
  const hasB = snapshotB && Object.keys(snapshotB.landmarks || {}).length > 0;

  if (!hasA && !hasB) {
    return (
      <div className="card p-6 text-center text-xs text-ink-3">
        <Icon name="alert" className="h-6 w-6 mx-auto mb-2 text-ink-4" />
        <p className="font-semibold text-ink">No pose data captured</p>
        <p className="mt-1">
          Neither video had sufficient tracked pose frames at the detected movement inflection.
        </p>
      </div>
    );
  }

  return (
    <div className="card p-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
        <div>
          <h3 className="font-bold text-ink">Observed Posture Alignment</h3>
          <p className="text-xs text-ink-3">
            Real pose landmarks captured at movement inflection frame.
          </p>
        </div>

        {hasA && hasB && (
          <div className="flex items-center gap-1.5 rounded-xl bg-surface-2 p-1 text-xs font-semibold self-start sm:self-auto">
            <button
              type="button"
              onClick={() => setMode("side_by_side")}
              className={`rounded-lg px-3 py-1 cursor-pointer transition-all ${
                mode === "side_by_side"
                  ? "bg-white text-ink shadow-sm font-bold"
                  : "text-ink-3 hover:text-ink"
              }`}
            >
              Side-by-Side
            </button>
            <button
              type="button"
              onClick={() => setMode("overlay")}
              className={`rounded-lg px-3 py-1 cursor-pointer transition-all ${
                mode === "overlay"
                  ? "bg-white text-ink shadow-sm font-bold"
                  : "text-ink-3 hover:text-ink"
              }`}
            >
              Superimposed Overlay
            </button>
          </div>
        )}
      </div>

      {mode === "side_by_side" || !hasA || !hasB ? (
        <div className="grid gap-6 sm:grid-cols-2">
          {/* Reference Card */}
          <div className="flex flex-col items-center rounded-2xl bg-slate-950 border border-slate-800 p-5 shadow-xs">
            <div className="flex items-center justify-between w-full mb-3">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-cyan-500/15 border border-cyan-500/30 px-3 py-1 text-xs font-semibold text-cyan-300">
                <span className="h-2 w-2 rounded-full bg-cyan-400" />
                {labelA}
              </span>
              {snapshotA?.frame_number != null && (
                <span className="text-[11px] text-slate-400 font-mono">
                  Frame #{snapshotA.frame_number}
                </span>
              )}
            </div>

            {hasA && snapshotA ? (
              <svg viewBox="0 0 300 400" className="h-64 w-full max-w-[240px]">
                <line x1="20" y1="360" x2="280" y2="360" stroke="#334155" strokeWidth="2" strokeDasharray="4 4" />
                <SkeletonSvg snapshot={snapshotA} color="#38bdf8" />
              </svg>
            ) : (
              <div className="h-64 flex flex-col items-center justify-center text-xs text-slate-400">
                <Icon name="alert" className="h-5 w-5 mb-2 text-slate-500" />
                <span>No pose data for Reference</span>
              </div>
            )}
          </div>

          {/* Comparison Card */}
          <div className="flex flex-col items-center rounded-2xl bg-slate-950 border border-slate-800 p-5 shadow-xs">
            <div className="flex items-center justify-between w-full mb-3">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-500/15 border border-amber-500/30 px-3 py-1 text-xs font-semibold text-amber-300">
                <span className="h-2 w-2 rounded-full bg-amber-400" />
                {labelB}
              </span>
              {snapshotB?.frame_number != null && (
                <span className="text-[11px] text-slate-400 font-mono">
                  Frame #{snapshotB.frame_number}
                </span>
              )}
            </div>

            {hasB && snapshotB ? (
              <svg viewBox="0 0 300 400" className="h-64 w-full max-w-[240px]">
                <line x1="20" y1="360" x2="280" y2="360" stroke="#334155" strokeWidth="2" strokeDasharray="4 4" />
                <SkeletonSvg snapshot={snapshotB} color="#f59e0b" />
              </svg>
            ) : (
              <div className="h-64 flex flex-col items-center justify-center text-xs text-slate-400">
                <Icon name="alert" className="h-5 w-5 mb-2 text-slate-500" />
                <span>No pose data for Comparison</span>
              </div>
            )}
          </div>
        </div>
      ) : (
        /* Overlay View */
        <div className="flex flex-col items-center rounded-2xl bg-slate-950 border border-slate-800 p-6 shadow-xs max-w-md mx-auto w-full">
          <div className="mb-4 flex items-center gap-4 text-xs font-semibold">
            <span className="inline-flex items-center gap-1.5 text-cyan-400 bg-cyan-500/10 border border-cyan-500/30 px-2.5 py-1 rounded-full">
              <span className="h-2 w-2 rounded-full bg-cyan-400" />
              {labelA} (Cyan)
            </span>
            <span className="inline-flex items-center gap-1.5 text-amber-400 bg-amber-500/10 border border-amber-500/30 px-2.5 py-1 rounded-full">
              <span className="h-2 w-2 rounded-full bg-amber-400" />
              {labelB} (Amber)
            </span>
          </div>

          <svg viewBox="0 0 300 400" className="h-72 w-full max-w-[280px]">
            <line x1="20" y1="360" x2="280" y2="360" stroke="#334155" strokeWidth="2" strokeDasharray="4 4" />
            {snapshotA && <SkeletonSvg snapshot={snapshotA} color="#38bdf8" opacity={0.5} />}
            {snapshotB && <SkeletonSvg snapshot={snapshotB} color="#f59e0b" opacity={0.9} />}
          </svg>

          <p className="mt-3 text-center text-xs text-slate-400">
            Superimposed posture twin at the detected inflection point.
          </p>
        </div>
      )}
    </div>
  );
}
