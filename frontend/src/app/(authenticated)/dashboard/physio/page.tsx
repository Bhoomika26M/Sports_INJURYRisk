"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { firstName, formatDate, humanize, initials } from "@/lib/format";
import type { CoachDashboard } from "@/lib/types";
import { PageHeader } from "@/components/page-header";
import { Avatar, RiskBadge } from "@/components/badges";
import { EmptyState, ErrorState, PageSkeleton } from "@/components/feedback";
import { ActionCard } from "@/components/action-card";

export default function PhysioDashboard() {
  const { user } = useAuth();
  const q = useQuery({ queryKey: ["coach-dashboard"], queryFn: () => api.get<CoachDashboard>("/analytics/coach") });

  if (q.isPending) return <PageSkeleton />;
  if (q.isError) return <ErrorState message={q.error.message} onRetry={() => q.refetch()} />;

  const flagged = q.data.athletes.filter((a) => a.latest_risk_category === "high" || a.latest_risk_category === "critical");

  return (
    <>
      <PageHeader title={`Hi ${firstName(user?.full_name)}`} subtitle="Athletes whose latest movement pattern deserves attention." />

      <section className="hero hero--purple">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">
            {flagged.length === 0 ? "All clear for now" : `${flagged.length} flagged · ${q.data.athletes.length} under observation`}
          </h2>
          <p className="mt-1 max-w-md opacity-80">Flags are pattern signals to look into, not diagnoses.</p>
        </div>
      </section>

      {flagged.length === 0 ? (
        <EmptyState icon="check" title="No one is flagged">Nobody currently shows a high or critical pattern.</EmptyState>
      ) : (
        <ul className="flex flex-col gap-3">
          {flagged.map((a) => (
            <li key={a.athlete_id}>
              <Link href={`/athletes/${a.athlete_id}`} className="row">
                <Avatar text={initials(a.name ?? humanize(a.sport))} />
                <div className="min-w-0 flex-1">
                  <p className="truncate font-semibold text-ink">{a.name ?? `${humanize(a.sport)} athlete`}</p>
                  <p className="truncate text-sm text-ink-3">{humanize(a.sport)}{a.last_assessed ? ` · assessed ${formatDate(a.last_assessed)}` : ""}</p>
                </div>
                {a.latest_risk_category && <RiskBadge category={a.latest_risk_category} />}
              </Link>
            </li>
          ))}
        </ul>
      )}

      <section className="grid gap-4 sm:grid-cols-2">
        <ActionCard href="/athletes" icon="users" title="All athletes" body="Browse everyone's profile." />
        <ActionCard href="/videos" icon="video" title="Videos" body="Review recent analyses." />
      </section>
    </>
  );
}
