"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { useAthlete, useVideo } from "@/lib/hooks";
import { cameraLabel, canManageAthletes, formatDateTime, formatDuration, movementLabel, processingFailureHelp } from "@/lib/format";
import { BackLink } from "@/components/back-link";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/badges";
import { AuthVideo } from "@/components/auth-media";
import { ConfirmDialog } from "@/components/dialog";
import { Icon } from "@/components/icons";
import { ErrorState, PageSkeleton, Spinner } from "@/components/feedback";
import { useToast } from "@/components/toast";

export default function VideoDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const queryClient = useQueryClient();
  const toast = useToast();
  const { user } = useAuth();
  const videoQ = useVideo(id);
  const v = videoQ.data;
  const athleteQ = useAthlete(v?.athlete_id ?? "");
  const [source, setSource] = useState<"annotated" | "original">("annotated");
  const [confirmDelete, setConfirmDelete] = useState(false);

  const del = useMutation({
    mutationFn: () => api.del(`/videos/${id}`),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: ["video", id] });
      queryClient.invalidateQueries({ queryKey: ["videos"] });
      toast.success("Video deleted.");
      router.replace("/videos");
    },
    onError: (e) => {
      setConfirmDelete(false);
      toast.error(e instanceof Error ? e.message : "We couldn't delete that video.");
    },
  });

  if (videoQ.isPending) return <PageSkeleton rows={2} />;
  if (videoQ.isError || !v) {
    const notFound = videoQ.error instanceof ApiError && videoQ.error.status === 404;
    return (
      <>
        <BackLink href="/videos">All videos</BackLink>
        <ErrorState
          title={notFound ? "Video not found" : "Couldn't load this video"}
          message={notFound ? "It may have been deleted, or you may not have access to it." : (videoQ.error?.message ?? "Please try again.")}
          onRetry={notFound ? undefined : () => videoQ.refetch()}
        />
      </>
    );
  }

  const hasAnnotated = !!v.annotated_video_key;
  const effective = hasAnnotated ? source : "original";
  const athleteName = athleteQ.data?.full_name || "Athlete";
  const details: [string, string][] = [
    ["Movement", movementLabel(v.movement_type)],
    ["Camera", cameraLabel(v.camera_view)],
    ["Length", formatDuration(v.duration_seconds)],
    ["Quality", v.resolution_width ? `${v.resolution_width}×${v.resolution_height}${v.fps ? ` · ${Math.round(v.fps)} fps` : ""}` : "—"],
    ["Uploaded", formatDateTime(v.created_at)],
  ];

  return (
    <>
      <PageHeader
        back={<BackLink href="/videos">All videos</BackLink>}
        title={`${movementLabel(v.movement_type)} · ${athleteName}`}
        subtitle={<StatusBadge status={v.processing_status} />}
        actions={
          <>
            {v.processing_status === "completed" && (
              <Link href={`/videos/${v.id}/results`} className="btn btn-primary">See results <Icon name="chevron-right" className="h-4 w-4" /></Link>
            )}
            {canManageAthletes(user?.role) && (
              <button onClick={() => setConfirmDelete(true)} className="btn btn-ghost text-danger hover:!bg-danger-bg">
                <Icon name="trash" className="h-4 w-4" /> Delete
              </button>
            )}
          </>
        }
      />

      {v.processing_status === "completed" ? (
        <section className="flex flex-col gap-4">
          <AuthVideo
            key={effective}
            path={effective === "annotated" ? `/videos/${v.id}/annotated` : `/videos/${v.id}/file`}
            label={effective === "annotated" ? "Video with body tracking overlay" : "Original video"}
          />
          {hasAnnotated && (
            <div className="tabs" role="tablist" aria-label="Video version">
              <button role="tab" className="tab" aria-selected={source === "annotated"} onClick={() => setSource("annotated")}>With tracking</button>
              <button role="tab" className="tab" aria-selected={source === "original"} onClick={() => setSource("original")}>Original</button>
            </div>
          )}
        </section>
      ) : v.processing_status === "failed" ? (
        <div className="card p-8 text-center" role="alert">
          <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-danger-bg text-danger"><Icon name="alert" className="h-7 w-7" /></span>
          <h2 className="mt-5 text-xl font-semibold text-ink">We couldn&apos;t analyze this video</h2>
          <p className="mx-auto mt-2 max-w-md text-ink-2">{processingFailureHelp(v.error_code, v.error_message)}</p>
          <Link href={`/videos/upload?athlete_id=${v.athlete_id}`} className="btn btn-primary mt-6">Try another video</Link>
        </div>
      ) : (
        <div className="card p-8 text-center">
          <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-brand-tint text-brand-dark"><Spinner className="h-6 w-6" /></span>
          <h2 className="mt-5 text-xl font-semibold text-ink">
            {v.processing_status === "pending_upload" ? "Waiting for the upload to finish" : "Analyzing movement"}
          </h2>
          <p className="mt-1 text-ink-2">{v.progress_pct > 0 ? `${v.progress_pct}% complete` : "This page updates by itself."}</p>
          <div className={`progress mx-auto mt-6 max-w-md ${v.progress_pct === 0 ? "progress--indeterminate" : ""}`}><span style={{ width: `${Math.max(v.progress_pct, 4)}%` }} /></div>
        </div>
      )}

      <section className="card-soft p-6 sm:p-8">
        <dl className="grid grid-cols-2 gap-x-6 gap-y-5 sm:grid-cols-3">
          <div>
            <dt className="stat-label">Athlete</dt>
            <dd className="mt-1 font-medium text-ink">
              <Link href={`/athletes/${v.athlete_id}`} className="underline underline-offset-4 hover:text-brand-dark">{athleteName}</Link>
            </dd>
          </div>
          {details.map(([k, val]) => (
            <div key={k}>
              <dt className="stat-label">{k}</dt>
              <dd className="mt-1 font-medium text-ink">{val}</dd>
            </div>
          ))}
        </dl>
      </section>

      <ConfirmDialog
        open={confirmDelete}
        onClose={() => setConfirmDelete(false)}
        onConfirm={() => del.mutate()}
        busy={del.isPending}
        title="Delete this video?"
        message="The video and its analysis will be removed for good. This can't be undone."
        confirmLabel="Delete video"
      />
    </>
  );
}
