"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { useAthletes } from "@/lib/hooks";
import { firstName, formatDate, movementLabel, RISK } from "@/lib/format";
import type { AthleteTrend } from "@/lib/types";
import { PageHeader } from "@/components/page-header";
import { RiskBadge } from "@/components/badges";
import { Icon } from "@/components/icons";
import { EmptyState, ErrorState, PageSkeleton } from "@/components/feedback";
import { ActionCard } from "@/components/action-card";

export default function AthleteDashboard() {
  const { user } = useAuth();
  const athletesQ = useAthletes(1, 1);
  const athlete = athletesQ.data?.items[0];
  const trendQ = useQuery({
    queryKey: ["athlete", athlete?.id, "trend"],
    queryFn: () => api.get<AthleteTrend>(`/analytics/athletes/${athlete!.id}/trends`),
    enabled: !!athlete,
  });

  if (athletesQ.isPending) return <PageSkeleton />;
  if (athletesQ.isError) return <ErrorState message={athletesQ.error.message} onRetry={() => athletesQ.refetch()} />;

  const heading = <PageHeader title={`Hi ${firstName(user?.full_name)}`} subtitle="Here's how your movement is looking." />;

  if (!athlete) {
    return (
      <>
        {heading}
        <EmptyState icon="users" title="Your profile isn't set up yet">
          Your coach needs to create or link your athlete profile before you can upload videos and see results.
        </EmptyState>
      </>
    );
  }

  const points = [...(trendQ.data?.points ?? [])].sort((a, b) => a.created_at.localeCompare(b.created_at));
  const latest = points[points.length - 1];

  return (
    <>
      {heading}

      <section className="hero hero--green">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Ready for a new check-in?</h2>
          <p className="mt-1 max-w-md opacity-80">A short squat, jump or run clip is all it takes.</p>
        </div>
        <Link href={`/videos/upload?athlete_id=${athlete.id}`} className="btn btn-primary shrink-0"><Icon name="upload" className="h-4 w-4" /> Analyze a video</Link>
      </section>

      {trendQ.isPending ? (
        <PageSkeleton rows={1} />
      ) : trendQ.isError ? (
        <ErrorState message={trendQ.error.message} onRetry={() => trendQ.refetch()} />
      ) : !latest ? (
        <EmptyState icon="chart" title="No results yet">Once your first video is analyzed, your progress will show up here.</EmptyState>
      ) : (
        <>
          <section className="grid gap-4 sm:grid-cols-3">
            <div className="card-soft p-6 sm:col-span-1">
              <p className="stat-label">Latest score</p>
              <span className="stat-value">{Math.round(latest.overall_score)}<span className="text-lg font-semibold text-ink-3"> / 100</span></span>
              <p className="mt-2"><RiskBadge category={latest.risk_category} /></p>
              <p className="mt-2 text-sm text-ink-3">{movementLabel(latest.movement_type)} · {formatDate(latest.created_at)}</p>
              <Link href={`/videos/${latest.video_id}/results`} className="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-brand-dark underline underline-offset-4">See details <Icon name="chevron-right" className="h-4 w-4" /></Link>
            </div>
            <div className="card p-6 sm:col-span-2">
              <p className="stat-label">Score over time</p>
              {points.length < 2 ? (
                <p className="py-10 text-center text-ink-3">Analyze one more video to see a trend.</p>
              ) : (
                <div className="mt-3 h-[200px]" role="img" aria-label="Line chart of your score over time">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={points.map((p) => ({ d: formatDate(p.created_at), s: Math.round(p.overall_score) }))} margin={{ top: 8, right: 8, bottom: 0, left: -20 }}>
                      <CartesianGrid stroke="#f1f5f9" vertical={false} />
                      <XAxis dataKey="d" tick={{ fill: "#64748b", fontSize: 12 }} tickLine={false} axisLine={false} minTickGap={24} />
                      <YAxis domain={[0, 100]} tick={{ fill: "#64748b", fontSize: 12 }} tickLine={false} axisLine={false} />
                      <Tooltip formatter={(v) => [String(v), "Score"]} contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0" }} />
                      <Line type="monotone" dataKey="s" stroke="#163300" strokeWidth={2.5} dot={{ r: 3, fill: "#9fe870", stroke: "#163300" }} isAnimationActive={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          </section>
          <p className="text-sm text-ink-3">
            Scores flag movement patterns worth a closer look — they don&apos;t predict injuries. {RISK[latest.risk_category].label} risk is a pattern label, not a diagnosis.
          </p>
        </>
      )}

      <section className="grid gap-4 sm:grid-cols-2">
        <ActionCard href="/videos" icon="video" title="Your videos" body="Everything you've analyzed so far." />
        <ActionCard href={`/athletes/${athlete.id}`} icon="user" title="Your profile" body="Injuries, training and details." />
      </section>
    </>
  );
}
