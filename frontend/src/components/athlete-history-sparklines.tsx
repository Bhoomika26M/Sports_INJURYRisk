"use client";

import { useQuery } from "@tanstack/react-query";
import { Line, LineChart, ResponsiveContainer, Tooltip } from "recharts";
import { api } from "@/lib/api-client";
import { Icon } from "@/components/icons";
import { formatDate } from "@/lib/format";

interface HistoryVideo {
  video_id: string;
  created_at: string;
  movement_type: string;
  camera_view: string;
  quality_grade?: string | null;
  coverage_caveat: boolean;
  metrics: Record<string, number | string | null>;
}

interface AthleteHistoryResponse {
  athlete_id: string;
  movement_type?: string | null;
  total_videos: number;
  videos: HistoryVideo[];
}

export function AthleteHistorySparklines({ athleteId }: { athleteId: string }) {
  const historyQ = useQuery({
    queryKey: ["athlete", athleteId, "history"],
    queryFn: () => api.get<AthleteHistoryResponse>(`/athletes/${athleteId}/history`),
  });

  const videos = [...(historyQ.data?.videos ?? [])].reverse(); // chronological for chart
  if (videos.length < 2) return null;

  // Extract trend data for sagittal joint angles
  const kneeFlexionData = videos
    .map((v) => {
      const val = v.metrics?.knee_flexion_angle_left ?? v.metrics?.knee_flexion_depth;
      return {
        date: formatDate(v.created_at),
        value: typeof val === "number" ? Math.round(val) : null,
      };
    })
    .filter((d) => d.value !== null);

  const trunkLeanData = videos
    .map((v) => {
      const val = v.metrics?.trunk_lean_angle ?? v.metrics?.trunk_lean;
      return {
        date: formatDate(v.created_at),
        value: typeof val === "number" ? Math.round(val) : null,
      };
    })
    .filter((d) => d.value !== null);

  return (
    <section className="card p-6 flex flex-col gap-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-black/5 pb-3">
        <div>
          <h3 className="font-bold text-ink">Within-Athlete Longitudinal Trends</h3>
          <p className="text-xs text-ink-3">
            Self-referenced kinematic progression across {videos.length} completed sessions.
          </p>
        </div>
        <span className="badge badge-neutral text-xs font-medium self-start sm:self-auto">
          Baseline ({videos.length} sessions)
        </span>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {kneeFlexionData.length >= 2 && (
          <div className="rounded-2xl border border-black/10 bg-surface-2 p-4 flex flex-col justify-between">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-ink">Knee Flexion Depth (Left)</span>
              <span className="text-xs font-mono font-bold text-emerald-700">
                {kneeFlexionData[kneeFlexionData.length - 1].value}°
              </span>
            </div>
            <div className="h-16 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={kneeFlexionData}>
                  <Tooltip
                    content={({ payload }) => {
                      if (!payload || !payload.length) return null;
                      const d = payload[0].payload;
                      return (
                        <div className="rounded-lg bg-slate-900 px-2 py-1 text-[11px] text-white font-mono">
                          {d.date}: {d.value}°
                        </div>
                      );
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke="#10b981"
                    strokeWidth={2.5}
                    dot={{ r: 3, fill: "#10b981" }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {trunkLeanData.length >= 2 && (
          <div className="rounded-2xl border border-black/10 bg-surface-2 p-4 flex flex-col justify-between">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-ink">Trunk Lean Angle</span>
              <span className="text-xs font-mono font-bold text-cyan-700">
                {trunkLeanData[trunkLeanData.length - 1].value}°
              </span>
            </div>
            <div className="h-16 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trunkLeanData}>
                  <Tooltip
                    content={({ payload }) => {
                      if (!payload || !payload.length) return null;
                      const d = payload[0].payload;
                      return (
                        <div className="rounded-lg bg-slate-900 px-2 py-1 text-[11px] text-white font-mono">
                          {d.date}: {d.value}°
                        </div>
                      );
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke="#0284c7"
                    strokeWidth={2.5}
                    dot={{ r: 3, fill: "#0284c7" }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
