"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { Video, GeminiObservation } from "@/lib/types";
import { Icon } from "@/components/icons";
import { Spinner } from "@/components/feedback";
import { useToast } from "@/components/toast";

const LEVEL_TONE: Record<string, "ok" | "warn" | "danger" | "muted"> = {
  none: "ok",
  mild: "warn",
  marked: "danger",
  not_assessable: "muted",
};

interface GeminiObservationCardProps {
  video: Video;
  className?: string;
}

export function GeminiObservationCard({ video, className = "" }: GeminiObservationCardProps) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const obs: GeminiObservation | null = video.analysis?.gemini_observation ?? null;
  const [showJoints, setShowJoints] = useState(false);

  const runMutation = useMutation({
    mutationFn: async () => {
      return await api.post<GeminiObservation>(`/videos/${video.id}/ai-observe`);
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["video", video.id] });
      queryClient.invalidateQueries({ queryKey: ["videos"] });
      toast.success(`Gemini observation complete (${data.model})`);
    },
    onError: (err: Error) => {
      toast.error(err.message || "Failed to generate Gemini observation");
    },
  });

  const primaryChunk = obs?.chunks?.[0]?.analysis;
  const overall = obs?.overall;

  return (
    <section className={`card p-6 flex flex-col gap-5 ${className}`}>
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-1">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-purple-100 text-purple-700">
            <Icon name="film" className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-ink text-base">Gemini AI Multimodal Observation</h3>
              <span className="badge badge-info text-[11px]">Direct Video Observation</span>
            </div>
            <p className="text-xs text-ink-3">
              Qualitative joint tracking & heuristic risk flags directly from video
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {obs?.model && (
            <span className="badge badge-muted text-xs font-mono">
              Model: {obs.model}
            </span>
          )}
          <button
            type="button"
            onClick={() => runMutation.mutate()}
            disabled={runMutation.isPending}
            className="btn btn-secondary text-xs flex items-center gap-1.5 py-1.5 px-3"
            title={obs ? "Re-run Gemini observation on this clip" : "Run qualitative Gemini observation"}
          >
            {runMutation.isPending ? (
              <>
                <Spinner className="h-3.5 w-3.5" />
                <span>Observing clip...</span>
              </>
            ) : (
              <>
                <Icon name="refresh" className="h-3.5 w-3.5" />
                <span>{obs ? "Re-run AI" : "Run Gemini Observation"}</span>
              </>
            )}
          </button>
        </div>
      </div>

      {!obs ? (
        <div className="rounded-2xl bg-surface p-6 text-center">
          <p className="text-sm text-ink-2">
            No qualitative Gemini observation has been generated for this video yet.
          </p>
          <p className="mt-1 text-xs text-ink-3">
            Sends downscaled footage to Gemini Flash for qualitative valgus, lean, and asymmetry checks.
          </p>
          <button
            type="button"
            onClick={() => runMutation.mutate()}
            disabled={runMutation.isPending}
            className="btn btn-primary mt-4 inline-flex items-center gap-2 text-xs"
          >
            {runMutation.isPending ? <Spinner className="h-4 w-4" /> : <Icon name="play" className="h-4 w-4" />}
            Generate Qualitative Gemini Analysis
          </button>
        </div>
      ) : (
        <>
          {/* Key Heuristic Flags */}
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-ink-3 mb-2.5">
              Visual Risk Flags (Qualitative Assessment)
            </h4>
            <div className="grid gap-3 sm:grid-cols-3">
              {/* Knee Valgus */}
              <div className="rounded-2xl bg-surface p-4 flex flex-col justify-between">
                <div className="flex items-start justify-between gap-2">
                  <span className="text-xs font-medium text-ink-2">Frontal Knee Valgus</span>
                  <span className={`badge badge-${LEVEL_TONE[overall?.knee_valgus ?? primaryChunk?.knee_valgus?.level ?? "muted"]}`}>
                    {overall?.knee_valgus ?? primaryChunk?.knee_valgus?.level ?? "not assessable"}
                  </span>
                </div>
                {primaryChunk?.knee_valgus?.note && (
                  <p className="mt-2 text-xs text-ink-3 leading-relaxed">
                    {primaryChunk.knee_valgus.note}
                  </p>
                )}
              </div>

              {/* Trunk Lean */}
              <div className="rounded-2xl bg-surface p-4 flex flex-col justify-between">
                <div className="flex items-start justify-between gap-2">
                  <span className="text-xs font-medium text-ink-2">Forward/Lateral Lean</span>
                  <span className={`badge badge-${LEVEL_TONE[overall?.trunk_lean ?? primaryChunk?.trunk_lean?.level ?? "muted"]}`}>
                    {overall?.trunk_lean ?? primaryChunk?.trunk_lean?.level ?? "not assessable"}
                  </span>
                </div>
                {primaryChunk?.trunk_lean?.note && (
                  <p className="mt-2 text-xs text-ink-3 leading-relaxed">
                    {primaryChunk.trunk_lean.note}
                  </p>
                )}
              </div>

              {/* Bilateral Asymmetry */}
              <div className="rounded-2xl bg-surface p-4 flex flex-col justify-between">
                <div className="flex items-start justify-between gap-2">
                  <span className="text-xs font-medium text-ink-2">Bilateral Asymmetry</span>
                  <span className={`badge badge-${LEVEL_TONE[overall?.asymmetry ?? primaryChunk?.asymmetry?.level ?? "muted"]}`}>
                    {overall?.asymmetry ?? primaryChunk?.asymmetry?.level ?? "not assessable"}
                  </span>
                </div>
                {primaryChunk?.asymmetry?.note && (
                  <p className="mt-2 text-xs text-ink-3 leading-relaxed">
                    {primaryChunk.asymmetry.note}
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Observations Overview */}
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-2xl bg-surface p-3.5">
              <span className="text-[11px] text-ink-3">Recognized Movement</span>
              <p className="text-sm font-semibold text-ink capitalize mt-0.5">
                {primaryChunk?.movement || "Unknown"}
              </p>
            </div>
            <div className="rounded-2xl bg-surface p-3.5">
              <span className="text-[11px] text-ink-3">Camera View</span>
              <p className="text-sm font-semibold text-ink capitalize mt-0.5">
                {primaryChunk?.camera_view || "Unknown"}
              </p>
            </div>
            <div className="rounded-2xl bg-surface p-3.5">
              <span className="text-[11px] text-ink-3">Observed Repetitions</span>
              <p className="text-sm font-semibold text-ink mt-0.5">
                {primaryChunk?.reps_seen != null ? `${primaryChunk.reps_seen} reps` : "—"}
              </p>
            </div>
          </div>

          {/* Summary & Limitations */}
          {primaryChunk?.summary && (
            <div className="rounded-2xl bg-surface p-5">
              <p className="text-xs font-semibold text-ink mb-1">Visual Observation Summary</p>
              <p className="text-xs text-ink-2 leading-relaxed">{primaryChunk.summary}</p>
              {primaryChunk?.limitations && primaryChunk.limitations.length > 0 && (
                <div className="mt-3 pt-3 border-t border-hair/40">
                  <p className="text-[11px] font-semibold text-ink-3 mb-1">Observation Limitations</p>
                  <ul className="text-xs text-ink-3 space-y-0.5 list-disc list-inside">
                    {primaryChunk.limitations.map((lim, idx) => (
                      <li key={idx}>{lim}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Joint Details Toggle */}
          {primaryChunk?.joints && primaryChunk.joints.length > 0 && (
            <div>
              <button
                type="button"
                onClick={() => setShowJoints(!showJoints)}
                className="text-xs font-medium text-brand-dark flex items-center gap-1 hover:underline"
              >
                <Icon name={showJoints ? "chevron-down" : "chevron-right"} className="h-3.5 w-3.5" />
                {showJoints ? "Hide joint mobility notes" : `View joint mobility notes (${primaryChunk.joints.length} joints)`}
              </button>

              {showJoints && (
                <div className="mt-2.5 overflow-hidden rounded-2xl bg-surface">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-surface-hover text-ink-3">
                      <tr>
                        <th className="py-2.5 px-3.5 font-semibold">Joint</th>
                        <th className="py-2.5 px-3.5 font-semibold">Side</th>
                        <th className="py-2.5 px-3.5 font-semibold">Tracked</th>
                        <th className="py-2.5 px-3.5 font-semibold">Qualitative Observation</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-faint bg-white">
                      {primaryChunk.joints.map((j, i) => (
                        <tr key={i} className="hover:bg-surface-tint">
                          <td className="py-2.5 px-3.5 font-medium capitalize text-ink">{j.joint}</td>
                          <td className="py-2.5 px-3.5 text-ink-3 capitalize">{j.side}</td>
                          <td className="py-2.5 px-3.5">
                            <span className={`inline-block h-2 w-2 rounded-full ${j.visible ? "bg-ok" : "bg-danger"}`} />
                          </td>
                          <td className="py-2.5 px-3.5 text-ink-2">{j.note}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* Science Constraints Disclaimer */}
          <div className="rounded-2xl bg-surface p-3.5 flex items-start gap-2.5 text-ink-3 text-[11px]">
            <Icon name="info" className="h-4 w-4 shrink-0 text-ink-3 mt-0.5" />
            <p>
              {obs.disclaimer || "Qualitative observations by an AI model watching a downscaled video. Not measurements, not a diagnosis, not an injury prediction. Knee valgus is a visual flag only. Kept apart from the platform's pose pipeline: do not feed this into baselines or risk scores."}
            </p>
          </div>
        </>
      )}
    </section>
  );
}
