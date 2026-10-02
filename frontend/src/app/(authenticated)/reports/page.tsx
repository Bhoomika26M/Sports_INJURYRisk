"use client";

import Link from "next/link";
import { useAllAthletes, useVideos } from "@/lib/hooks";
import { athleteName, formatDateTime, movementLabel } from "@/lib/format";
import { PageHeader } from "@/components/page-header";
import { DownloadButton } from "@/components/download-button";
import { EmptyState, ErrorState, ListSkeleton } from "@/components/feedback";

export default function ReportsPage() {
  const q = useVideos({ pageSize: 50 });
  const athletesQ = useAllAthletes();
  const names = new Map((athletesQ.data?.items ?? []).map((a) => [a.id, athleteName(a)]));
  const ready = (q.data?.items ?? []).filter((v) => v.processing_status === "completed");

  return (
    <>
      <PageHeader title="Reports" subtitle="Download any finished analysis as PDF, Excel or CSV." />

      {q.isPending ? (
        <ListSkeleton />
      ) : q.isError ? (
        <ErrorState message={q.error.message} onRetry={() => q.refetch()} />
      ) : ready.length === 0 ? (
        <EmptyState icon="file" title="No reports yet" action={{ label: "Analyze a video", href: "/videos/upload" }}>
          Reports appear here once a video has finished analyzing.
        </EmptyState>
      ) : (
        <>
          <ul className="flex flex-col gap-3">
            {ready.map((v) => (
              <li key={v.id} className="row !flex-col !items-stretch sm:!flex-row sm:!items-center">
                <div className="min-w-0 flex-1">
                  <p className="truncate font-semibold text-ink">{movementLabel(v.movement_type)} · {names.get(v.athlete_id) ?? "Athlete"}</p>
                  <p className="text-sm text-ink-3">{formatDateTime(v.created_at)}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Link href={`/videos/${v.id}/results`} className="btn btn-ghost btn-sm">View</Link>
                  <DownloadButton path={`/videos/${v.id}/report.pdf`} filename={`report-${v.id}.pdf`} label="PDF" variant="soft" />
                  <DownloadButton path={`/videos/${v.id}/report.xlsx`} filename={`report-${v.id}.xlsx`} label="Excel" />
                  <DownloadButton path={`/videos/${v.id}/biomechanics/export.csv`} filename={`video-${v.id}.csv`} label="CSV" />
                </div>
              </li>
            ))}
          </ul>
          {q.data.total > 50 && <p className="text-sm text-ink-3">Showing the 50 most recent videos. Older ones are under Videos.</p>}
        </>
      )}
    </>
  );
}
