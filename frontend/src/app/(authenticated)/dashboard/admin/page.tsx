"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { useMovementTypes } from "@/lib/hooks";
import { cameraLabel } from "@/lib/format";
import type { TeamOverview } from "@/lib/types";
import { PageHeader } from "@/components/page-header";
import { ErrorState, PageSkeleton } from "@/components/feedback";
import { StatCard } from "@/components/stat-card";
import { ActionCard } from "@/components/action-card";

export default function AdminDashboard() {
  const q = useQuery({ queryKey: ["team-overview"], queryFn: () => api.get<TeamOverview>("/analytics/team-overview") });
  const typesQ = useMovementTypes();

  if (q.isPending) return <PageSkeleton />;
  if (q.isError) return <ErrorState message={q.error.message} onRetry={() => q.refetch()} />;
  const o = q.data;

  return (
    <>
      <PageHeader title="Overview" subtitle="How the whole platform is doing." />

      <section className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Athletes" value={o.total_athletes} />
        <StatCard label="Videos" value={o.total_videos} />
        <StatCard label="Analyzed" value={o.videos_completed} hint={o.videos_processing > 0 ? `${o.videos_processing} in progress` : undefined} />
        <StatCard label="Needs attention" value={o.videos_failed} hint="Failed to process" />
      </section>

      {typesQ.data && (
        <section className="flex flex-col gap-4">
          <h2 className="text-lg font-semibold text-ink">Supported movements</h2>
          <ul className="grid gap-3 sm:grid-cols-2">
            {typesQ.data.map((t) => (
              <li key={t.code} className="row !justify-between">
                <span className="font-medium text-ink">{t.display_name}</span>
                <span className="text-sm text-ink-3">{t.camera_views.map(cameraLabel).join(" · ")} · {t.metrics.length} metrics</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="grid gap-4 sm:grid-cols-3">
        <ActionCard href="/athletes" icon="users" title="Athletes" body="Browse profiles." />
        <ActionCard href="/videos" icon="video" title="Videos" body="Recent analyses." />
        <ActionCard href="/reports" icon="file" title="Reports" body="Exports." />
      </section>
    </>
  );
}
