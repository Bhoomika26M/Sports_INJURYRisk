"use client";

import { useState, useMemo } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { useVideos } from "@/lib/hooks";
import { movementLabel } from "@/lib/format";
import type { BenchmarkPreset, CompareVideosResponse, Video } from "@/lib/types";
import { Icon } from "@/components/icons";
import { Spinner, ErrorState } from "@/components/feedback";
import { AuthVideo } from "@/components/auth-media";
import { PostureVectorCard } from "@/components/posture-vector-card";
import { CustomVideoSelect, VideoSelectionPreview, type CustomVideoSelectOption } from "@/components/custom-video-select";

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
  const [showPoseSkeleton, setShowPoseSkeleton] = useState<boolean>(true);

  // Fetch benchmark presets
  const presetsQ = useQuery({
    queryKey: ["benchmark-presets"],
    queryFn: () => api.get<{ presets: BenchmarkPreset[] }>("/videos/benchmark-presets"),
  });

  // Fetch recent completed videos for selector
  const recentVideosQ = useVideos({ page: 1, pageSize: 30 });
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
  const presets = useMemo(() => presetsQ.data?.presets ?? [], [presetsQ.data?.presets]);

  // Selected Option Objects for Preview Cards
  const selectedOptionA: CustomVideoSelectOption | null = useMemo(() => {
    const p = presets.find((x) => x.id === videoAId);
    if (p) {
      return {
        id: p.id,
        title: p.title,
        movement_type: p.movement_type,
        camera_view: p.camera_view,
        duration_seconds: p.duration_seconds,
        is_preset: true,
        is_textbook: p.is_textbook,
      };
    }
    const v = completedVideos.find((x: Video) => x.id === videoAId);
    if (v) {
      return {
        id: v.id,
        title: `${movementLabel(v.movement_type)} · ${v.original_filename || v.id.slice(0, 8)}`,
        movement_type: v.movement_type,
        camera_view: v.camera_view,
        duration_seconds: v.duration_seconds ?? undefined,
        is_preset: false,
      };
    }
    return null;
  }, [videoAId, presets, completedVideos]);

  const selectedOptionB: CustomVideoSelectOption | null = useMemo(() => {
    const v = completedVideos.find((x: Video) => x.id === videoBId);
    if (v) {
      return {
        id: v.id,
        title: `${movementLabel(v.movement_type)} · ${v.original_filename || v.id.slice(0, 8)}`,
        movement_type: v.movement_type,
        camera_view: v.camera_view,
        duration_seconds: v.duration_seconds ?? undefined,
        is_preset: false,
      };
    }
    const p = presets.find((x) => x.id === videoBId);
    if (p) {
      return {
        id: p.id,
        title: p.title,
        movement_type: p.movement_type,
        camera_view: p.camera_view,
        duration_seconds: p.duration_seconds,
        is_preset: true,
        is_textbook: p.is_textbook,
      };
    }
    return null;
  }, [videoBId, presets, completedVideos]);

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
              className="btn btn-outline btn-sm inline-flex items-center gap-1.5 cursor-pointer"
              title="Invert benchmark and trainee clips"
            >
              <Icon name="refresh" className="h-3.5 w-3.5" />
              <span>Swap Roles</span>
            </button>
          )}
        </div>

        {/* Dropdown Selectors Grid */}
        <div className="mt-6 grid gap-6 sm:grid-cols-2">
          {/* Video A: Benchmark / Trainer */}
          <CustomVideoSelect
            label="1. Benchmark Standard (Trainer / Ideal Form)"
            value={videoAId}
            onChange={(val) => setVideoAId(val)}
            presets={presets}
            videos={completedVideos}
            placeholder="Choose benchmark or standard clip..."
          />

          {/* Video B: Student / Trainee */}
          <CustomVideoSelect
            label="2. Evaluation Target (Student / Trainee Trial)"
            value={videoBId}
            onChange={(val) => setVideoBId(val)}
            presets={presets}
            videos={completedVideos}
            placeholder="Choose trainee clip to evaluate..."
          />
        </div>

        {/* Real-time Video Previews */}
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <VideoSelectionPreview
            option={selectedOptionA}
            label="Benchmark Clip"
          />
          <VideoSelectionPreview
            option={selectedOptionB}
            label="Evaluation Target"
          />
        </div>

        <div className="mt-6 flex flex-wrap items-center justify-between gap-4 pt-4 border-t border-black/5">
          <div className="flex items-center gap-2 text-xs text-ink-3">
            <Icon name="check" className="h-4 w-4 text-brand-dark" />
            <span>Biomechanical inflection synchronization &amp; 5-layer edge case safety</span>
          </div>

          <button
            type="button"
            disabled={!videoAId || !videoBId || isPending}
            onClick={() => handleRunComparison(videoAId, videoBId)}
            className="btn btn-primary inline-flex items-center gap-2 cursor-pointer shadow-sm hover:shadow"
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
                  ? "bg-amber-50 border-amber-200 text-amber-900"
                  : result.is_identical
                  ? "bg-sky-50 border-sky-200 text-sky-900"
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
                    ? "Moderate technique agreement. Focus on joint angles and balance callouts below."
                    : "Substantial divergence from benchmark standard. Prioritize the clinical corrective protocols."}
                </p>
              </div>

              <div className="flex flex-col items-end gap-2">
                <span
                  className={`badge text-sm font-bold px-3 py-1 ${
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

          {/* Side-by-Side Synchronized Video Players with Pose Skeleton Toggle */}
          <section className="card p-6">
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-black/5 pb-4">
              <div>
                <h3 className="font-bold text-ink">Synchronized Playback Review</h3>
                <p className="text-xs text-ink-3">
                  Locked to peak inflection frames for side-by-side motion review.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                {/* Pose Overlay Switcher */}
                <div className="flex items-center rounded-xl bg-surface-2 p-1 text-xs font-semibold">
                  <button
                    type="button"
                    onClick={() => setShowPoseSkeleton(true)}
                    className={`rounded-lg px-2.5 py-1 transition-all cursor-pointer flex items-center gap-1.5 ${
                      showPoseSkeleton
                        ? "bg-white text-emerald-800 shadow-sm font-bold"
                        : "text-ink-3 hover:text-ink"
                    }`}
                  >
                    <span className="h-2 w-2 rounded-full bg-emerald-500" />
                    <span>Pose Tracking Skeleton (Green Dots)</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowPoseSkeleton(false)}
                    className={`rounded-lg px-2.5 py-1 transition-all cursor-pointer flex items-center gap-1.5 ${
                      !showPoseSkeleton
                        ? "bg-white text-ink shadow-sm font-bold"
                        : "text-ink-3 hover:text-ink"
                    }`}
                  >
                    <span>Clean Camera</span>
                  </button>
                </div>

                {/* Playback speed controls */}
                <div className="flex items-center gap-1.5 rounded-xl bg-surface-2 p-1 text-xs font-semibold">
                  {[0.25, 0.5, 1.0].map((spd) => (
                    <button
                      key={spd}
                      type="button"
                      onClick={() => setPlaybackSpeed(spd)}
                      className={`rounded-lg px-2.5 py-1 transition-all cursor-pointer ${
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
            </div>

            <div className="mt-6 grid gap-6 sm:grid-cols-2">
              {/* Benchmark Player */}
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <span className="badge badge-ok self-start text-xs">
                    Benchmark: {result.video_a_info.filename}
                  </span>
                  {showPoseSkeleton && (
                    <span className="text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md flex items-center gap-1">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                      Green Pose Skeleton Active
                    </span>
                  )}
                </div>
                <div className="card-soft overflow-hidden rounded-2xl p-2 bg-slate-950">
                  <AuthVideo
                    path={
                      showPoseSkeleton
                        ? `/videos/${result.video_a_info.id}/annotated`
                        : `/videos/${result.video_a_info.id}/file`
                    }
                    label="Benchmark Video"
                  />
                </div>
              </div>

              {/* Trainee Player */}
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <span className="badge badge-warn self-start text-xs">
                    Trainee: {result.video_b_info.filename}
                  </span>
                  {showPoseSkeleton && (
                    <span className="text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md flex items-center gap-1">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                      Green Pose Skeleton Active
                    </span>
                  )}
                </div>
                <div className="card-soft overflow-hidden rounded-2xl p-2 bg-slate-950">
                  <AuthVideo
                    path={
                      showPoseSkeleton
                        ? `/videos/${result.video_b_info.id}/annotated`
                        : `/videos/${result.video_b_info.id}/file`
                    }
                    label="Trainee Video"
                  />
                </div>
              </div>
            </div>
          </section>

          {/* Dynamic Vector Posture Twin Comparison */}
          <PostureVectorCard
            trainee={result.vector_posture_b}
            benchmark={result.vector_posture_a}
            title="Biomechanical Posture Twin Comparison"
            subtitle="Side-by-side vector alignment at peak eccentric inflection"
          />

          {/* Kinematic Deltas Table */}
          <section className="card p-6">
            <h3 className="font-bold text-ink mb-1">Kinematic Disparity Analysis</h3>
            <p className="text-xs text-ink-3 mb-6">
              Parameter-by-parameter delta between benchmark standard and trainee execution.
            </p>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-black/5 text-ink-3">
                    <th className="pb-3 font-semibold uppercase tracking-wider">Kinematic Parameter</th>
                    <th className="pb-3 font-semibold uppercase tracking-wider">Benchmark Standard</th>
                    <th className="pb-3 font-semibold uppercase tracking-wider">Trainee Execution</th>
                    <th className="pb-3 font-semibold uppercase tracking-wider">Disparity (Δ)</th>
                    <th className="pb-3 font-semibold uppercase tracking-wider">Clinical Impact</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-black/5">
                  {result.deltas.map((item, idx) => (
                    <tr key={idx} className="hover:bg-black/2 transition-colors">
                      <td className="py-3 font-semibold text-ink">
                        <div>{item.label}</div>
                        <div className="text-[11px] font-normal text-ink-3 mt-0.5 max-w-xs">{item.explanation}</div>
                      </td>
                      <td className="py-3 font-medium text-ink-2">{item.video_a_val}</td>
                      <td className="py-3 font-bold text-ink">{item.video_b_val}</td>
                      <td className="py-3 font-bold">
                        <span
                          className={`inline-block px-2 py-0.5 rounded text-xs ${
                            item.verdict === "better"
                              ? "bg-emerald-100 text-emerald-800"
                              : item.verdict === "worse"
                              ? "bg-rose-100 text-rose-800"
                              : "bg-slate-100 text-slate-700"
                          }`}
                        >
                          {item.delta}
                        </span>
                      </td>
                      <td className="py-3 capitalize font-semibold">
                        {item.verdict === "better" && <span className="text-emerald-600">✓ Aligned</span>}
                        {item.verdict === "worse" && <span className="text-rose-600">⚠️ Divergent</span>}
                        {item.verdict === "neutral" && <span className="text-slate-500">— Equivalent</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* AI Coaching Narrative & Clinical Corrective Protocols — High Contrast UI */}
          {result.gemini_coaching && (
            <section className="card p-6 sm:p-8 bg-white border border-slate-200/90 shadow-xs">
              <div className="flex items-center gap-2.5 mb-3">
                <span className="flex h-7 w-7 items-center justify-center rounded-xl bg-brand-light text-brand-dark">
                  <Icon name="activity" className="h-4 w-4" />
                </span>
                <h3 className="text-lg font-bold text-slate-900">
                  Multimodal Biomechanical Coaching Debrief
                </h3>
              </div>

              <p className="text-sm sm:text-base text-slate-700 leading-relaxed max-w-3xl font-normal">
                {result.gemini_coaching.summary}
              </p>

              {/* Immediate Verbal Cues — High Contrast Clean Design */}
              {result.gemini_coaching.verbal_cues.length > 0 && (
                <div className="mt-8 border-t border-slate-100 pt-6">
                  <p className="stat-label text-xs uppercase tracking-wider text-slate-500 font-bold mb-3">
                    Immediate On-Field Verbal Cues
                  </p>
                  <ul className="grid gap-3 sm:grid-cols-2">
                    {result.gemini_coaching.verbal_cues.map((cue, idx) => (
                      <li
                        key={idx}
                        className="flex items-start gap-3 rounded-2xl bg-slate-50/80 border border-slate-200/80 p-4 shadow-2xs hover:border-brand-dark/30 transition-colors"
                      >
                        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-light text-brand-dark text-xs font-bold mt-0.5">
                          {idx + 1}
                        </span>
                        <span className="text-sm font-semibold text-slate-900 leading-snug">
                          &ldquo;{cue}&rdquo;
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Prescribed Clinical Corrective Drills */}
              {result.gemini_coaching.prescribed_exercises.length > 0 && (
                <div className="mt-8 border-t border-slate-100 pt-6">
                  <p className="stat-label text-xs uppercase tracking-wider text-slate-500 font-bold mb-3">
                    Clinical Biomechanical Correctives
                  </p>
                  <div className="grid gap-4 sm:grid-cols-3">
                    {result.gemini_coaching.prescribed_exercises.map((drill, idx) => (
                      <div
                        key={idx}
                        className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs flex flex-col justify-between hover:border-slate-300 transition-colors"
                      >
                        <div>
                          <p className="font-bold text-slate-900 text-sm">
                            {drill.name}
                          </p>
                          {drill.target && (
                            <p className="text-xs text-brand-dark font-medium mt-1 bg-brand-light/30 px-2 py-0.5 rounded-md inline-block">
                              Target: {drill.target}
                            </p>
                          )}
                        </div>
                        <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
                          <span className="text-slate-500">
                            Sets: <strong className="text-slate-900 font-bold">{drill.sets || "3"}</strong>
                          </span>
                          <span className="text-slate-500">
                            Reps: <strong className="text-slate-900 font-bold">{drill.reps || "10"}</strong>
                          </span>
                          {drill.tempo && (
                            <span className="text-slate-500">
                              Tempo: <strong className="text-slate-900 font-bold">{drill.tempo}</strong>
                            </span>
                          )}
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
