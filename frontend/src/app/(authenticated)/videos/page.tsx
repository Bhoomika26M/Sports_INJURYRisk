"use client";

import { useState } from "react";
import Link from "next/link";
import { useAllAthletes, useVideos } from "@/lib/hooks";
import { athleteName, cameraLabel, formatDateTime, movementLabel, VIDEO_STATUS } from "@/lib/format";
import type { Video } from "@/lib/types";
import { PageHeader } from "@/components/page-header";
import { Icon } from "@/components/icons";
import { StatusBadge } from "@/components/badges";
import { EmptyState, ErrorState, ListSkeleton } from "@/components/feedback";

const FILTERS = [
  { id: "all", label: "All", test: () => true },
  { id: "ready", label: "Ready", test: (v: Video) => v.processing_status === "completed" },
  { id: "progress", label: "In progress", test: (v: Video) => ["pending_upload", "uploaded", "processing"].includes(v.processing_status) },
  { id: "attention", label: "Needs attention", test: (v: Video) => v.processing_status === "failed" },
] as const;

const PAGE_SIZE = 20;

export default function VideosPage() {
  const [page, setPage] = useState(1);
  const [filter, setFilter] = useState<(typeof FILTERS)[number]["id"]>("all");
  const videosQ = useVideos({ page, pageSize: PAGE_SIZE });
  const athletesQ = useAllAthletes();

  const names = new Map((athletesQ.data?.items ?? []).map((a) => [a.id, athleteName(a)]));
  const active = FILTERS.find((f) => f.id === filter) ?? FILTERS[0];
  const items = (videosQ.data?.items ?? []).filter(active.test);
  const total = videosQ.data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <>
      <PageHeader
        title="Videos"
        subtitle="Every analysis in one place."
        actions={<Link href="/videos/upload" className="btn btn-primary"><Icon name="plus" className="h-4 w-4" /> New analysis</Link>}
      />

      {videosQ.isPending ? (
        <ListSkeleton />
      ) : videosQ.isError ? (
        <ErrorState message={videosQ.error.message} onRetry={() => videosQ.refetch()} />
      ) : total === 0 ? (
        <EmptyState icon="video" title="No videos yet" action={{ label: "Analyze your first video", href: "/videos/upload" }}>
          Upload a short clip of a squat, jump or run to see how the body moves.
        </EmptyState>
      ) : (
        <>
          <div className="tabs" role="tablist" aria-label="Filter videos">
            {FILTERS.map((f) => (
              <button key={f.id} role="tab" aria-selected={filter === f.id} className="tab" onClick={() => setFilter(f.id)}>{f.label}</button>
            ))}
          </div>

          {items.length === 0 ? (
            <EmptyState icon="video" title="Nothing here">No videos on this page match “{active.label}”.</EmptyState>
          ) : (
            <ul className="flex flex-col gap-3">
              {items.map((v) => {
                const st = VIDEO_STATUS[v.processing_status];
                const inFlight = v.processing_status === "processing" || v.processing_status === "uploaded";
                return (
                  <li key={v.id}>
                    <Link href={`/videos/${v.id}`} className="row">
                      <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-full ${
                        st.tone === "ok" ? "bg-brand-tint text-brand-dark" : st.tone === "danger" ? "bg-danger-bg text-danger" : "bg-white text-ink-2"}`}>
                        <Icon name={st.tone === "danger" ? "alert" : "film"} />
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="truncate font-semibold text-ink">
                          {movementLabel(v.movement_type)} · {names.get(v.athlete_id) ?? "Athlete"}
                        </p>
                        <p className="truncate text-sm text-ink-3">
                          {cameraLabel(v.camera_view)} · {formatDateTime(v.created_at)}
                        </p>
                        {inFlight && (
                          <div className="progress mt-2 max-w-[220px] !h-1.5"><span style={{ width: `${Math.max(v.progress_pct, 4)}%` }} /></div>
                        )}
                      </div>
                      <StatusBadge status={v.processing_status} />
                      <Icon name="chevron-right" className="hidden h-5 w-5 text-ink-3 sm:block" />
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}

          {pages > 1 && (
            <div className="flex items-center justify-between">
              <button className="btn btn-outline btn-sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                <Icon name="chevron-left" className="h-4 w-4" /> Previous
              </button>
              <span className="text-sm text-ink-3">Page {page} of {pages}</span>
              <button className="btn btn-outline btn-sm" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>
                Next <Icon name="chevron-right" className="h-4 w-4" />
              </button>
            </div>
          )}
        </>
      )}
    </>
  );
}
