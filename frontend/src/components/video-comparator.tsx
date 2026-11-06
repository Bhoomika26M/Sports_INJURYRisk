"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { useVideos } from "@/lib/hooks";
import { movementLabel } from "@/lib/format";
import type { BenchmarkPreset, CompareVideosResponse, Video } from "@/lib/types";
import { Icon } from "@/components/icons";
import { Spinner, ErrorState } from "@/components/feedback";
import { AuthVideo } from "@/components/auth-media";
import { PostureVectorCard } from "@/components/posture-vector-card";

interface VideoComparatorProps {
  initialVideoAId?: string;
  initialVideoBId?: string;
  onSwap?: (newA: string, newB: string) => void;
}

export function VideoComparator({
  initialVideoAId,
  initialVideoBId,
}: VideoComparatorProps) {
  const [videoAId, setVideoAId] = useState<string>(initialVideoAId || "");
  const [videoBId, setVideoBId] = useState<string>(initialVideoBId || "");
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1.0);

  // Fetch benchmark presets
  const presetsQ = useQuery({
    queryKey: ["benchmark-presets"],
    queryFn: () => api.get<{ presets: BenchmarkPreset[] }>("/videos/benchmark-presets"),
  });

  // Fetch recent completed videos for selector
  const recentVideosQ = useVideos({ page: 1, pageSize: 20 });
  const completedVideos = (recentVideosQ.data?.items ?? []).filter(
    (v: Video) => v.processing_status === "completed"
  );

  // Comparison Mutation
  const compareMutation = useMutation({
    mutationFn: (payload: { video_a_id: string; video_b_id: string; run_gemini: boolean }) =>
      api.post<CompareVideosResponse>("/videos/compare", payload),
  });

  const handleRunComparison = (aId: string, bId: string) => {
    if (!aId || !bId) return;
    compareMutation.mutate({
      video_a_id: aId,
      video_b_id: bId,
      run_gemini: true,
    });
  };

  const handleSwapRoles = () => {
    const newA = videoBId;
    const newB = videoAId;
    setVideoAId(newA);
    setVideoBId(newB);
    handleRunComparison(newA, newB);
  };

  const result = compareMutation.data;
  const isPending = compareMutation.isPending;

  // Compute preset list
  const presets = presetsQ.data?.presets ?? [];

  return (
    <div className="flex flex-col gap-8">
      {/* Selection Control Panel */}
      <section className="card p-6">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-black/5 pb-4">
          <div>
            <h2 className="text-xl font-bold tracking-tight text-ink flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-brand-light text-brand-dark">
                <Icon name="activity" className="h-4 w-4" />
              </span>
              Olympic-Grade Dual-Video Benchmark Studio
            </h2>
            <p className="mt-1 text-xs text-ink-3">
              Compare student technique directly against coach standards or textbook biomechanical models.
            </p>
          </div>

          {videoAId && videoBId && (
            <button
              type="button"
              onClick={handleSwapRoles}
              className="btn btn-outline btn-sm inline-flex items-center gap-1.5"
              title="Invert benchmark and trainee clips"
            >
              <Icon name="refresh" className="h-3.5 w-3.5" />
              <span>Swap Roles</span>
            </button>
          )}
        </div>

        <div className="mt-6 grid gap-6 sm:grid-cols-2">
          {/* Video A: Benchmark / Trainer */}
          <div className="flex flex-col gap-2">
            <label className="text-xs font-bold uppercase tracking-wider text-ink-3">
              1. Benchmark Standard (Trainer / Ideal Form)
            </label>
            <select
              value={videoAId}
              onChange={(e) => setVideoAId(e.target.value)}
              className="field text-sm"
            >
              <option value="">-- Choose Benchmark Clip --</option>
              <optgroup label="⭐ Pre-Loaded Benchmark Standards">
                {presets.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.title}
                  </option>
                ))}
              </optgroup>
              <optgroup label="📹 Analyzed Videos in Database">
                {completedVideos.map((v: Video) => (
                  <option key={v.id} value={v.id}>
                    {movementLabel(v.movement_type)} · {v.original_filename || v.id.slice(0, 8)}
                  </option>
                ))}
              </optgroup>
            </select>
          </div>

          {/* Video B: Student / Trainee */}
          <div className="flex flex-col gap-2">
            <label className="text-xs font-bold uppercase tracking-wider text-ink-3">
              2. Evaluation Target (Student / Trainee Trial)
            </label>
            <select
              value={videoBId}
              onChange={(e) => setVideoBId(e.target.value)}
              className="field text-sm"
            >
              <option value="">-- Choose Trainee Clip --</option>
              {completedVideos.map((v: Video) => (
                <option key={v.id} value={v.id}>
                  {movementLabel(v.movement_type)} · {v.original_filename || v.id.slice(0, 8)}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="mt-6 flex flex-wrap items-center justify-between gap-4 pt-4 border-t border-black/5">
          <div className="flex items-center gap-2 text-xs text-ink-3">
            <Icon name="check" className="h-4 w-4 text-brand-dark" />
            <span>Automatic inflection frame synchronization &amp; 5-layer edge case safety</span>
          </div>

          <button
            type="button"
            disabled={!videoAId || !videoBId || isPending}
            onClick={() => handleRunComparison(videoAId, videoBId)}
            className="btn btn-primary inline-flex items-center gap-2"
          >
            {isPending ? (
              <>
                <Spinner className="h-4 w-4" />
                <span>Synchronizing Kinematics...</span>
              </>
            ) : (
              <>
                <Icon name="check" className="h-4 w-4" />
                <span>Run Form Benchmark</span>
              </>
            )}
          </button>
        </div>
      </section>

      {/* Comparison Error State */}
      {compareMutation.isError && (
        <ErrorState
          message={compareMutation.error?.message || "Failed to compare videos."}
          onRetry={() => handleRunComparison(videoAId, videoBId)}
        />
      )}

      {/* Comparison Results Presentation */}
      {result && (
        <div className="flex flex-col gap-8 animate-in fade-in duration-300">
          {/* Advisory Banners */}
          {result.advisory && (
            <div
              className={`rounded-2xl p-4 flex flex-wrap items-center justify-between gap-4 border ${
                result.suggest_swap
                  ? "bg-amber-50 border-amber-200 text-amber-900 dark:bg-amber-950 dark:border-amber-800 dark:text-amber-200"
                  : result.is_identical
                  ? "bg-sky-50 border-sky-200 text-sky-900 dark:bg-sky-950 dark:border-sky-800 dark:text-sky-200"
                  : "bg-surface-2 border-black/10 text-ink"
              }`}
            >
              <div className="flex items-start gap-3">
                <span className="mt-0.5 text-base">
                  {result.suggest_swap ? "💡" : result.is_identical ? "ℹ️" : "⚠️"}
                </span>
                <p className="text-xs font-medium leading-relaxed max-w-2xl">
                  {result.advisory}
                </p>
              </div>

              {result.suggest_swap && (
                <button
                  type="button"
                  onClick={handleSwapRoles}
                  className="btn btn-primary btn-sm shrink-0"
                >
                  Swap Roles Now
                </button>
              )}
            </div>
          )}

          {/* Form Match Score Hero Card */}
          <section className="card p-6 sm:p-8 bg-gradient-to-br from-surface to-surface-2">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-ink-3">
                  Kinematic Technique Agreement
                </p>
                <div className="mt-2 flex items-baseline gap-2">
                  <span className="text-5xl font-black tracking-tight text-ink">
                    {result.form_match_score}%
                  </span>
                  <span className="text-lg font-semibold text-ink-3">
                    Form Match Score
                  </span>
                </div>
                <p className="mt-2 text-sm text-ink-2 max-w-md">
                  {result.form_match_score >= 85
                    ? "High technique agreement with the benchmark standard. Joint trajectory and depth well aligned."
                    : result.form_match_score >= 65
                    ? "Moderate technique agreement. Noted kinetic compensations in trunk lean or knee tracking."
                    : "Targeted technique correction recommended. Discrepancy observed across depth and frontal alignment."}
                </p>
              </div>

              {/* Status Badge */}
              <div className="flex flex-col items-end gap-2">
                <span
                  className={`badge text-sm px-4 py-1.5 font-bold ${
                    result.form_match_score >= 80
                      ? "badge-ok"
                      : result.form_match_score >= 60
                      ? "badge-warn"
                      : "badge-danger"
                  }`}
                >
                  {result.form_match_score >= 80
                    ? "Optimal Form"
                    : result.form_match_score >= 60
                    ? "Minor Divergence"
                    : "Corrective Focus"}
                </span>
                <span className="text-xs text-ink-3">
                  Discipline: <strong>{movementLabel(result.movement_type)}</strong>
                </span>
              </div>
            </div>
          </section>

          {/* Side-by-Side Synchronized Video Players */}
          <section className="card p-6">
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-black/5 pb-4">
              <div>
                <h3 className="font-bold text-ink">Synchronized Playback Review</h3>
                <p className="text-xs text-ink-3">
                  Locked to peak inflection frames for side-by-side motion review.
                </p>
              </div>

              {/* Playback speed controls */}
              <div className="flex items-center gap-1.5 rounded-xl bg-surface-2 p-1 text-xs font-semibold">
                {[0.25, 0.5, 1.0].map((spd) => (
                  <button
                    key={spd}
                    type="button"
                    onClick={() => setPlaybackSpeed(spd)}
                    className={`rounded-lg px-2.5 py-1 transition-all ${
                      playbackSpeed === spd
                        ? "bg-white text-ink shadow-sm font-bold"
                        : "text-ink-3 hover:text-ink"
                    }`}
                  >
                    {spd}x
                  </button>
                ))}
              </div>
            </div>

            <div className="mt-6 grid gap-6 sm:grid-cols-2">
              {/* Benchmark Player */}
              <div className="flex flex-col gap-2">
                <span className="badge badge-ok self-start text-xs">
                  Benchmark: {result.video_a_info.filename}
                </span>
                <div className="card-soft overflow-hidden rounded-2xl p-2 bg-slate-950">
                  <AuthVideo
                    path={`/videos/${result.video_a_info.id}/file`}
                    label="Benchmark Video"
                  />
                </div>
              </div>

              {/* Trainee Player */}
              <div className="flex flex-col gap-2">
                <span className="badge badge-warn self-start text-xs">
                  Trainee: {result.video_b_info.filename}
                </span>
                <div className="card-soft overflow-hidden rounded-2xl p-2 bg-slate-950">
                  <AuthVideo
                    path={`/videos/${result.video_b_info.id}/file`}
                    label="Trainee Video"
                  />
                </div>
              </div>
            </div>
          </section>

          {/* Dynamic Posture Vector Twins */}
          <PostureVectorCard
            trainee={result.vector_posture_b}
            benchmark={result.vector_posture_a}
            title="Biomechanical Posture Twin Comparison"
            subtitle="Side-by-side vector alignment at peak eccentric inflection"
          />

          {/* Kinematic Deltas Matrix */}
          <section className="card p-6">
            <h3 className="font-bold text-ink mb-1">Kinematic Discrepancy Breakdown</h3>
            <p className="text-xs text-ink-3 mb-6">
              Signed difference between Trainee (Evaluation) and Benchmark (Standard).
            </p>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-black/10 text-ink-3 font-semibold uppercase tracking-wider">
                    <th className="py-3 px-4">Biomechanical Metric</th>
                    <th className="py-3 px-4">Benchmark Form</th>
                    <th className="py-3 px-4">Trainee Form</th>
                    <th className="py-3 px-4">Discrepancy (Δ)</th>
                    <th className="py-3 px-4">Verdict</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-black/5">
                  {result.deltas.map((d) => (
                    <tr key={d.metric} className="hover:bg-black/[0.02] transition-colors">
                      <td className="py-3.5 px-4 font-medium text-ink">
                        <div>{d.label}</div>
                        <div className="text-[11px] text-ink-3 font-normal mt-0.5">{d.explanation}</div>
                      </td>
                      <td className="py-3.5 px-4 font-semibold text-ink">{d.video_a_val}</td>
                      <td className="py-3.5 px-4 font-semibold text-ink">{d.video_b_val}</td>
                      <td className="py-3.5 px-4 font-bold text-brand-dark">{d.delta}</td>
                      <td className="py-3.5 px-4">
                        <span
                          className={`badge text-[11px] ${
                            d.verdict === "better"
                              ? "badge-ok"
                              : d.verdict === "worse"
                              ? "badge-danger"
                              : "badge-muted"
                          }`}
                        >
                          {d.verdict === "better" ? "▲ Better" : d.verdict === "worse" ? "▼ Deviates" : "— Stable"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* AI Coaching Narrative & Clinical Corrective Protocols */}
          {result.gemini_coaching && (
            <section className="card p-6 bg-gradient-to-br from-brand-light/30 to-surface">
              <div className="flex items-center gap-2 mb-2">
                <span className="flex h-6 w-6 items-center justify-center rounded-md bg-brand-dark text-white">
                  <Icon name="activity" className="h-3.5 w-3.5" />
                </span>
                <h3 className="font-bold text-ink">Multimodal Biomechanical Coaching Debrief</h3>
              </div>
              <p className="text-xs text-ink-2 leading-relaxed max-w-3xl">
                {result.gemini_coaching.summary}
              </p>

              {/* Immediate Verbal Cues */}
              {result.gemini_coaching.verbal_cues.length > 0 && (
                <div className="mt-6 border-t border-black/5 pt-4">
                  <p className="stat-label text-xs">Immediate On-Field Verbal Cues</p>
                  <ul className="mt-2 grid gap-2 sm:grid-cols-2">
                    {result.gemini_coaching.verbal_cues.map((cue, idx) => (
                      <li
                        key={idx}
                        className="flex items-center gap-2 rounded-xl bg-white/70 p-3 text-xs font-semibold text-ink shadow-2xs dark:bg-slate-800"
                      >
                        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand-light text-brand-dark text-[10px]">
                          {idx + 1}
                        </span>
                        <span>&ldquo;{cue}&rdquo;</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Prescribed Clinical Corrective Drills */}
              {result.gemini_coaching.prescribed_exercises.length > 0 && (
                <div className="mt-6 border-t border-black/5 pt-4">
                  <p className="stat-label text-xs">Clinical Biomechanical Correctives</p>
                  <div className="mt-3 grid gap-3 sm:grid-cols-3">
                    {result.gemini_coaching.prescribed_exercises.map((drill, idx) => (
                      <div key={idx} className="card-soft p-4 flex flex-col justify-between">
                        <div>
                          <p className="font-bold text-ink text-xs">{drill.name}</p>
                          {drill.target && (
                            <p className="text-[11px] text-ink-3 mt-1">Target: {drill.target}</p>
                          )}
                        </div>
                        <div className="mt-3 pt-2 border-t border-black/5 flex items-center justify-between text-[11px]">
                          <span className="text-ink-3">Sets: <strong className="text-ink">{drill.sets || "3"}</strong></span>
                          <span className="text-ink-3">Reps: <strong className="text-ink">{drill.reps || "10"}</strong></span>
                          {drill.tempo && <span className="text-ink-3">Tempo: <strong className="text-ink">{drill.tempo}</strong></span>}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </section>
          )}
        </div>
      )}
    </div>
  );
}
