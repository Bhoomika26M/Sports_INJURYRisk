"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { useVideos, useAllAthletes } from "@/lib/hooks";
import { useAuth } from "@/lib/auth-context";
import type { Video, CompareVideosResponse } from "@/lib/types";
import { Icon } from "@/components/icons";
import { Spinner } from "@/components/feedback";
import { AuthVideo } from "@/components/auth-media";
import { VideoPairSelector } from "@/components/comparison/video-pair-selector";
import { ComparisonMetricsTable } from "@/components/comparison/comparison-metrics-table";
import { ComparisonPostureView } from "@/components/comparison/comparison-posture-view";

interface VideoComparatorProps {
  initialVideoAId?: string;
  initialVideoBId?: string;
}

export function VideoComparator({
  initialVideoAId = "",
  initialVideoBId = "",
}: VideoComparatorProps) {
  const queryClient = useQueryClient();
  const { user } = useAuth();

  const [videoAId, setVideoAId] = useState<string>(initialVideoAId);
  const [videoBId, setVideoBId] = useState<string>(initialVideoBId);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1.0);
  const [showAnnotated, setShowAnnotated] = useState<boolean>(true);

  // Background polling state for freshly uploaded clips
  const [pollingStatus, setPollingStatus] = useState<{
    isPolling: boolean;
    message: string;
    labelA: string;
    labelB: string;
    progressA: number;
    progressB: number;
    statusA: "pending" | "processing" | "completed" | "failed";
    statusB: "pending" | "processing" | "completed" | "failed";
    error: string | null;
  }>({
    isPolling: false,
    message: "",
    labelA: "",
    labelB: "",
    progressA: 0,
    progressB: 0,
    statusA: "pending",
    statusB: "pending",
    error: null,
  });

  const abortControllerRef = useRef<AbortController | null>(null);

  // Completed videos for selector
  const recentVideosQ = useVideos({ page: 1, pageSize: 50 });
  const completedVideos = (recentVideosQ.data?.items ?? []).filter(
    (v: Video) => v.processing_status === "completed"
  );

  // Athletes list for upload assignment
  const athletesQ = useAllAthletes();
  const athletes = athletesQ.data?.items ?? [];

  // Comparison mutation
  const compareMutation = useMutation({
    mutationFn: (payload: { video_a_id: string; video_b_id: string }) =>
      api.post<CompareVideosResponse>("/videos/compare", payload),
  });

  const runCompare = useCallback(
    (aId: string, bId: string) => {
      if (!aId || !bId) return;
      compareMutation.mutate({ video_a_id: aId, video_b_id: bId });
    },
    [compareMutation]
  );

  // Run initial comparison if both IDs are provided
  useEffect(() => {
    if (initialVideoAId && initialVideoBId) {
      runCompare(initialVideoAId, initialVideoBId);
    }
  }, [initialVideoAId, initialVideoBId, runCompare]);

  // Clean up any ongoing polling on unmount
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  // Polling loop for fresh uploads
  const pollCompletedClips = useCallback(
    async (idA: string, idB: string, labelA: string, labelB: string) => {
      abortControllerRef.current?.abort();
      const abortCtrl = new AbortController();
      abortControllerRef.current = abortCtrl;

      compareMutation.reset();

      setPollingStatus({
        isPolling: true,
        message: `Queuing ${labelA} and ${labelB} for pose extraction...`,
        labelA,
        labelB,
        progressA: 0,
        progressB: 0,
        statusA: "pending",
        statusB: "pending",
        error: null,
      });

      let doneA = false;
      let doneB = false;

      try {
        // Allow up to 300 attempts * 2s = 600s (10 min) for full 2-video pipeline
        for (let attempt = 0; attempt < 300; attempt++) {
          if (abortCtrl.signal.aborted) return;
          await new Promise((res) => setTimeout(res, 2000));
          if (abortCtrl.signal.aborted) return;

          const [vA, vB] = await Promise.all([
            api.get<Video>(`/videos/${idA}`),
            api.get<Video>(`/videos/${idB}`),
          ]);

          const stA = vA.processing_status;
          const stB = vB.processing_status;

          if (stA === "completed") doneA = true;
          if (stB === "completed") doneB = true;

          if (stA === "failed" || stB === "failed") {
            const errA = stA === "failed" ? `${labelA}: ${vA.error_message || "Processing failed"}` : null;
            const errB = stB === "failed" ? `${labelB}: ${vB.error_message || "Processing failed"}` : null;
            throw new Error(errA || errB || "Video processing failed");
          }

          const pctA = stA === "completed" ? 100 : (vA.progress_pct || 0);
          const pctB = stB === "completed" ? 100 : (vB.progress_pct || 0);

          const statusA: "pending" | "processing" | "completed" = doneA
            ? "completed"
            : pctA > 0
            ? "processing"
            : "pending";

          const statusB: "pending" | "processing" | "completed" = doneB
            ? "completed"
            : pctB > 0
            ? "processing"
            : "pending";

          let statusText = `Analyzing: ${labelA} (${pctA}%) • ${labelB} (${pctB}%)`;
          if (!doneA) {
            if (pctA === 0) {
              statusText = `Reference clip (${labelA}) queued for analysis • ${labelB} queued next`;
            } else {
              statusText = `Extracting pose landmarks: ${labelA} (${pctA}%) • ${labelB} queued next`;
            }
          } else if (doneA && !doneB) {
            if (pctB === 0) {
              statusText = `${labelA} analysis complete (100%) • Comparison clip (${labelB}) queued for analysis`;
            } else {
              statusText = `${labelA} analysis complete (100%) • Extracting pose landmarks: ${labelB} (${pctB}%)`;
            }
          } else if (doneA && doneB) {
            statusText = `Pose extraction complete (100%) • Generating synchronized kinematic comparison...`;
          }

          setPollingStatus((prev) => ({
            ...prev,
            progressA: pctA,
            progressB: pctB,
            statusA,
            statusB,
            message: statusText,
          }));

          if (doneA && doneB) break;
        }

        if (!doneA || !doneB) {
          throw new Error("Video processing is taking longer than expected. Please wait a moment and check the library.");
        }

        await queryClient.invalidateQueries({ queryKey: ["videos"] });
        setVideoAId(idA);
        setVideoBId(idB);
        setPollingStatus({
          isPolling: false,
          message: "",
          labelA: "",
          labelB: "",
          progressA: 100,
          progressB: 100,
          statusA: "completed",
          statusB: "completed",
          error: null,
        });

        runCompare(idA, idB);
      } catch (err) {
        if (!abortCtrl.signal.aborted) {
          setPollingStatus({
            isPolling: false,
            message: "",
            labelA: "",
            labelB: "",
            progressA: 0,
            progressB: 0,
            statusA: "failed",
            statusB: "failed",
            error: err instanceof Error ? err.message : "Processing failed",
          });
        }
      }
    },
    [compareMutation, queryClient, runCompare]
  );

  const handleSwap = () => {
    const nextA = videoBId;
    const nextB = videoAId;
    setVideoAId(nextA);
    setVideoBId(nextB);
    if (nextA && nextB) {
      runCompare(nextA, nextB);
    }
  };

  const result = compareMutation.data;
  const compareError = compareMutation.error;

  return (
    <div className="flex flex-col gap-8 max-w-6xl mx-auto">
      {/* Pair Selector Subcomponent */}
      <VideoPairSelector
        completedVideos={completedVideos}
        athletes={athletes}
        userRole={user?.role}
        selectedAId={videoAId}
        selectedBId={videoBId}
        onSelectA={setVideoAId}
        onSelectB={setVideoBId}
        onSwap={handleSwap}
        onCompare={() => runCompare(videoAId, videoBId)}
        onUploadSuccess={pollCompletedClips}
        isLoading={compareMutation.isPending || pollingStatus.isPolling}
      />

      {/* Dual Video Pose Landmark Extraction Progress HUD */}
      {pollingStatus.isPolling && (
        <section
          className="card p-6 border-2 border-brand/20 bg-surface shadow-sm rounded-2xl flex flex-col gap-5"
          aria-live="polite"
        >
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-black/5 pb-4">
            <div className="flex items-center gap-3">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-tint text-brand-dark">
                <Spinner className="h-5 w-5" />
              </span>
              <div>
                <h3 className="font-bold text-ink text-sm sm:text-base">
                  Biomechanical Pose Landmark Extraction
                </h3>
                <p className="text-xs text-ink-3">
                  MediaPipe 33-point joint tracking and kinematic calculation in progress.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 self-start sm:self-auto">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-[11px] font-semibold text-emerald-700 border border-emerald-200">
                <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                Live Engine Active
              </span>
            </div>
          </div>

          {/* Active Status Banner */}
          <div className="rounded-xl bg-brand-light/40 border border-brand/20 px-3.5 py-2.5 flex items-center gap-2 text-xs font-medium text-ink">
            <Icon name="activity" className="h-4 w-4 text-brand-dark shrink-0 animate-pulse" />
            <span>{pollingStatus.message}</span>
          </div>

          {/* Dual Progress Tracks Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Reference Video Progress Card */}
            <div className="rounded-xl border border-black/10 bg-surface-2 p-4 flex flex-col justify-between gap-3">
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-surface border border-black/5 text-ink-2">
                    <Icon name="video" className="h-3.5 w-3.5" />
                  </div>
                  <div className="min-w-0">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-ink-3 block">
                      Reference Clip
                    </span>
                    <span className="text-xs font-semibold text-ink truncate block max-w-[200px]" title={pollingStatus.labelA}>
                      {pollingStatus.labelA || "Reference Video"}
                    </span>
                  </div>
                </div>

                {pollingStatus.statusA === "completed" ? (
                  <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-bold text-emerald-800">
                    <Icon name="check" className="h-3 w-3" />
                    Ready
                  </span>
                ) : pollingStatus.statusA === "processing" ? (
                  <span className="inline-flex items-center gap-1 rounded-full bg-brand-tint px-2 py-0.5 text-[10px] font-bold text-brand-dark">
                    <Spinner className="h-2.5 w-2.5" />
                    {pollingStatus.progressA}%
                  </span>
                ) : (
                  <span className="inline-flex items-center rounded-full bg-slate-200 px-2 py-0.5 text-[10px] font-medium text-slate-700">
                    Queued
                  </span>
                )}
              </div>

              {/* Progress bar */}
              <div>
                <div className="flex justify-between items-center text-[11px] text-ink-3 mb-1.5 font-medium">
                  <span>Joint tracking & inflection detection</span>
                  <span className="font-bold text-ink">{pollingStatus.progressA}%</span>
                </div>
                <div
                  className={`progress w-full ${
                    pollingStatus.statusA === "pending" && pollingStatus.progressA === 0
                      ? "progress--indeterminate"
                      : ""
                  }`}
                  role="progressbar"
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={pollingStatus.progressA}
                >
                  <span
                    style={{
                      width: `${Math.max(
                        pollingStatus.progressA,
                        pollingStatus.statusA === "completed" ? 100 : 5
                      )}%`,
                    }}
                  />
                </div>
              </div>
            </div>

            {/* Comparison Video Progress Card */}
            <div className="rounded-xl border border-black/10 bg-surface-2 p-4 flex flex-col justify-between gap-3">
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-surface border border-black/5 text-ink-2">
                    <Icon name="video" className="h-3.5 w-3.5" />
                  </div>
                  <div className="min-w-0">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-ink-3 block">
                      Comparison Clip
                    </span>
                    <span className="text-xs font-semibold text-ink truncate block max-w-[200px]" title={pollingStatus.labelB}>
                      {pollingStatus.labelB || "Comparison Video"}
                    </span>
                  </div>
                </div>

                {pollingStatus.statusB === "completed" ? (
                  <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-bold text-emerald-800">
                    <Icon name="check" className="h-3 w-3" />
                    Ready
                  </span>
                ) : pollingStatus.statusB === "processing" ? (
                  <span className="inline-flex items-center gap-1 rounded-full bg-brand-tint px-2 py-0.5 text-[10px] font-bold text-brand-dark">
                    <Spinner className="h-2.5 w-2.5" />
                    {pollingStatus.progressB}%
                  </span>
                ) : (
                  <span className="inline-flex items-center rounded-full bg-slate-200 px-2 py-0.5 text-[10px] font-medium text-slate-700">
                    {pollingStatus.statusA === "completed" ? "Starting..." : "Queued"}
                  </span>
                )}
              </div>

              {/* Progress bar */}
              <div>
                <div className="flex justify-between items-center text-[11px] text-ink-3 mb-1.5 font-medium">
                  <span>Joint tracking & inflection detection</span>
                  <span className="font-bold text-ink">{pollingStatus.progressB}%</span>
                </div>
                <div
                  className={`progress w-full ${
                    pollingStatus.statusB === "pending" && pollingStatus.progressB === 0
                      ? "progress--indeterminate"
                      : ""
                  }`}
                  role="progressbar"
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={pollingStatus.progressB}
                >
                  <span
                    style={{
                      width: `${Math.max(
                        pollingStatus.progressB,
                        pollingStatus.statusB === "completed" ? 100 : 5
                      )}%`,
                    }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Reassurance Notice */}
          <div className="flex items-center gap-2 text-xs text-ink-3 pt-1">
            <Icon name="shield" className="h-4 w-4 text-brand-dark shrink-0" />
            <span>
              Background processing is active on the server. You can safely stay on this page or navigate to other tabs — comparison will trigger automatically once both clips finish.
            </span>
          </div>
        </section>
      )}

      {pollingStatus.error && (
        <div className="rounded-2xl border border-rose-300 bg-rose-50 p-4 text-xs text-rose-800 flex items-start gap-2">
          <Icon name="alert" className="h-4 w-4 text-rose-600 shrink-0 mt-0.5" />
          <span>{pollingStatus.error}</span>
        </div>
      )}

      {compareError && (
        <div className="rounded-2xl border border-rose-300 bg-rose-50 p-4 text-xs text-rose-800 flex items-start gap-2">
          <Icon name="alert" className="h-4 w-4 text-rose-600 shrink-0 mt-0.5" />
          <span>
            {compareError instanceof Error ? compareError.message : "Comparison request failed"}
          </span>
        </div>
      )}

      {/* Comparison Results Area */}
      {result && (
        <div className="flex flex-col gap-8">
          {/* Synchronized Dual Video Players */}
          <section className="card p-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
              <div>
                <h3 className="font-bold text-ink">Synchronized Playback</h3>
                <p className="text-xs text-ink-3">
                  Movement: {result.movement_type}
                </p>
              </div>

              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => setShowAnnotated((prev) => !prev)}
                  className="btn btn-sm btn-ghost text-xs cursor-pointer flex items-center gap-1.5"
                >
                  <Icon name="activity" className="h-3.5 w-3.5" />
                  <span>{showAnnotated ? "Annotated Pose" : "Raw Footage"}</span>
                </button>

                <div className="flex items-center gap-1 rounded-xl bg-surface-2 p-1 text-xs font-semibold">
                  {[0.5, 1.0].map((spd) => (
                    <button
                      key={spd}
                      type="button"
                      onClick={() => setPlaybackSpeed(spd)}
                      className={`rounded-lg px-2 py-0.5 cursor-pointer ${
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

            <div className="grid gap-6 sm:grid-cols-2">
              <div className="flex flex-col gap-2">
                <span className="badge badge-neutral self-start text-xs font-semibold">
                  Reference: {result.video_a_info.filename || result.video_a_info.id.slice(0, 8)}
                </span>
                <div className="card-soft overflow-hidden rounded-2xl p-2 bg-slate-950">
                  <AuthVideo
                    path={
                      showAnnotated
                        ? `/videos/${result.video_a_info.id}/annotated`
                        : `/videos/${result.video_a_info.id}/file`
                    }
                    label="Reference Video"
                  />
                </div>
              </div>

              <div className="flex flex-col gap-2">
                <span className="badge badge-neutral self-start text-xs font-semibold">
                  Comparison: {result.video_b_info.filename || result.video_b_info.id.slice(0, 8)}
                </span>
                <div className="card-soft overflow-hidden rounded-2xl p-2 bg-slate-950">
                  <AuthVideo
                    path={
                      showAnnotated
                        ? `/videos/${result.video_b_info.id}/annotated`
                        : `/videos/${result.video_b_info.id}/file`
                    }
                    label="Comparison Video"
                  />
                </div>
              </div>
            </div>
          </section>

          {/* Observed Posture Alignment Subcomponent */}
          <ComparisonPostureView
            snapshotA={result.snapshot_a}
            snapshotB={result.snapshot_b}
            labelA={`Reference (${result.video_a_info.filename || "Clip A"})`}
            labelB={`Comparison (${result.video_b_info.filename || "Clip B"})`}
          />

          {/* Kinematic Comparison Table Subcomponent */}
          <ComparisonMetricsTable
            deltas={result.deltas}
            summary={result.summary}
            caveats={result.caveats}
            referenceFilename={result.video_a_info.filename}
            comparisonFilename={result.video_b_info.filename}
          />
        </div>
      )}
    </div>
  );
}
