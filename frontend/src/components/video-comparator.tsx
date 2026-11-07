"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { useVideos, useAllAthletes } from "@/lib/hooks";
import { useAuth } from "@/lib/auth-context";
import type { Video, CompareVideosResponse } from "@/lib/types";
import { Icon } from "@/components/icons";
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
    progressA: number;
    progressB: number;
    error: string | null;
  }>({
    isPolling: false,
    message: "",
    progressA: 0,
    progressB: 0,
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

      setPollingStatus({
        isPolling: true,
        message: "Processing video pose landmarks...",
        progressA: 10,
        progressB: 10,
        error: null,
      });

      let doneA = false;
      let doneB = false;

      try {
        for (let attempt = 0; attempt < 60; attempt++) {
          if (abortCtrl.signal.aborted) return;
          await new Promise((res) => setTimeout(res, 2000));
          if (abortCtrl.signal.aborted) return;

          const [vA, vB] = await Promise.all([
            api.get<Video>(`/videos/${idA}`),
            api.get<Video>(`/videos/${idB}`),
          ]);

          if (vA.processing_status === "completed") doneA = true;
          if (vB.processing_status === "completed") doneB = true;

          if (vA.processing_status === "failed" || vB.processing_status === "failed") {
            const errA = vA.processing_status === "failed" ? `${labelA}: ${vA.error_message || "Processing failed"}` : null;
            const errB = vB.processing_status === "failed" ? `${labelB}: ${vB.error_message || "Processing failed"}` : null;
            throw new Error(errA || errB || "Video processing failed");
          }

          const pctA = vA.progress_pct ?? (doneA ? 100 : Math.min(95, 10 + attempt * 2));
          const pctB = vB.progress_pct ?? (doneB ? 100 : Math.min(95, 10 + attempt * 2));

          setPollingStatus((prev) => ({
            ...prev,
            progressA: pctA,
            progressB: pctB,
            message: `Analyzing pose landmarks: ${labelA} (${pctA}%) • ${labelB} (${pctB}%)`,
          }));

          if (doneA && doneB) break;
        }

        await queryClient.invalidateQueries({ queryKey: ["videos"] });
        setVideoAId(idA);
        setVideoBId(idB);
        setPollingStatus({
          isPolling: false,
          message: "",
          progressA: 0,
          progressB: 0,
          error: null,
        });

        runCompare(idA, idB);
      } catch (err) {
        if (!abortCtrl.signal.aborted) {
          setPollingStatus({
            isPolling: false,
            message: "",
            progressA: 0,
            progressB: 0,
            error: err instanceof Error ? err.message : "Processing failed",
          });
        }
      }
    },
    [queryClient, runCompare]
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
        isLoading={compareMutation.isPending}
      />

      {/* Polling / Processing Banner */}
      {pollingStatus.isPolling && (
        <div
          className="rounded-2xl border border-brand-dark/20 bg-brand-light/30 p-5 space-y-3"
          aria-live="polite"
        >
          <div className="flex items-center gap-2.5 text-ink font-semibold">
            <Icon name="activity" className="h-4 w-4 text-brand-dark animate-pulse" />
            <span>{pollingStatus.message}</span>
          </div>
          <p className="text-xs text-ink-3">
            Pose extraction runs asynchronously. You can remain on this page while MediaPipe extracts joint kinematics.
          </p>
        </div>
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
