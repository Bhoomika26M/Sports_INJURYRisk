"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { firstName, formatDate, humanize, initials, RISK } from "@/lib/format";
import type { CoachDashboard } from "@/lib/types";
import { PageHeader } from "@/components/page-header";
import { Avatar, RiskBadge } from "@/components/badges";
import { Icon } from "@/components/icons";
import { EmptyState, ErrorState, PageSkeleton } from "@/components/feedback";
import { StatCard } from "@/components/stat-card";
import { ActionCard } from "@/components/action-card";

export default function CoachDashboard() {
  const { user } = useAuth();
  const q = useQuery({ queryKey: ["coach-dashboard"], queryFn: () => api.get<CoachDashboard>("/analytics/coach") });

  if (q.isPending) return <PageSkeleton />;
  if (q.isError) return <ErrorState message={q.error.message} onRetry={() => q.refetch()} />;

  const { overview: o, athletes } = q.data;
  const atRisk = o.high_risk_count + o.critical_risk_count;
  const sorted = [...athletes].sort(
    (a, b) => (b.latest_risk_category ? RISK[b.latest_risk_category].rank : -1) - (a.latest_risk_category ? RISK[a.latest_risk_category].rank : -1),
  );

  return (
    <>
      <PageHeader title={`Hi ${firstName(user?.full_name)}`} subtitle="Your team at a glance." />

      <section className="hero hero--blue">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">
            {atRisk > 0 ? `${atRisk} athlete${atRisk === 1 ? "" : "s"} worth a closer look` : "No one is flagged right now"}
          </h2>
          <p className="mt-1 max-w-md opacity-80">Based on the most recent analysis for each athlete.</p>
        </div>
        <Link href="/videos/upload" className="btn btn-primary shrink-0"><Icon name="upload" className="h-4 w-4" /> Analyze a video</Link>
      </section>

      <section className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Athletes" value={o.total_athletes} />
        <StatCard label="Analyses" value={o.videos_completed} hint={o.videos_processing > 0 ? `${o.videos_processing} in progress` : undefined} />
        <StatCard label="Closer look" value={atRisk} hint="High or critical" />
        <StatCard label="Average score" value={o.avg_risk_score != null ? Math.round(o.avg_risk_score) : "—"} />
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="text-lg font-semibold text-ink">Athletes</h2>
        {sorted.length === 0 ? (
          <EmptyState icon="users" title="No athletes yet" action={{ label: "Add your first athlete", href: "/athletes/new" }}>
            Add athletes, then upload their videos to see risk patterns here.
          </EmptyState>
        ) : (
          <ul className="flex flex-col gap-3">
            {sorted.map((a) => (
              <li key={a.athlete_id}>
                <Link href={`/athletes/${a.athlete_id}`} className="row">
                  <Avatar text={initials(a.name ?? humanize(a.sport))} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-semibold text-ink">{a.name ?? `${humanize(a.sport)} athlete`}</p>
                    <p className="truncate text-sm text-ink-3">{humanize(a.sport)}{a.last_assessed ? ` · assessed ${formatDate(a.last_assessed)}` : ""}</p>
                  </div>
                  {a.latest_risk_category ? <RiskBadge category={a.latest_risk_category} /> : <span className="badge badge-muted">Not assessed</span>}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="grid gap-4 sm:grid-cols-2">
        <ActionCard href="/athletes/new" icon="users" title="Add an athlete" body="Create a profile in under a minute." />
        <ActionCard href="/reports" icon="file" title="Reports" body="Download PDF, Excel or CSV." />
      </section>
    </>
  );
}
