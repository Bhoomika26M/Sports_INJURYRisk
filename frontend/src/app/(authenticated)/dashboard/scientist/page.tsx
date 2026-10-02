"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { useMovementTypes } from "@/lib/hooks";
import { metricLabel } from "@/lib/format";
import type { MovementAnalytics } from "@/lib/types";
import { PageHeader } from "@/components/page-header";
import { Field } from "@/components/field";
import { EmptyState, ErrorState, ListSkeleton, PageSkeleton } from "@/components/feedback";
import { StatCard } from "@/components/stat-card";

export default function ScientistDashboard() {
  const typesQ = useMovementTypes();
  const [choice, setChoice] = useState<string | null>(null);
  const selected = choice ?? typesQ.data?.[0]?.code ?? null;

  const q = useQuery({
    queryKey: ["movement-analytics", selected],
    queryFn: () => api.get<MovementAnalytics>(`/analytics/movement-types/${selected}`),
    enabled: !!selected,
  });

  if (typesQ.isPending) return <PageSkeleton rows={2} />;
  if (typesQ.isError) return <ErrorState message={typesQ.error.message} onRetry={() => typesQ.refetch()} />;

  // Front-view metrics are qualitative flags — never shown as numbers (docs/SCIENCE_CONSTRAINTS.md)
  const validated = new Set(
    typesQ.data.find((t) => t.code === selected)?.metrics.filter((m) => m.confidence === "validated").map((m) => m.metric_name),
  );
  const baselines = Object.entries(q.data?.baselines ?? {}).filter(([name]) => validated.has(name));

  return (
    <>
      <PageHeader title="Population insights" subtitle="Baselines and score distributions for each movement." />

      <div className="max-w-xs">
        <Field label="Movement">
          {(p) => (
            <select {...p} className="input" value={selected ?? ""} onChange={(e) => setChoice(e.target.value)}>
              {typesQ.data.map((t) => <option key={t.code} value={t.code}>{t.display_name}</option>)}
            </select>
          )}
        </Field>
      </div>

      {q.isPending ? (
        <ListSkeleton rows={3} />
      ) : q.isError ? (
        <ErrorState message={q.error.message} onRetry={() => q.refetch()} />
      ) : (
        <>
          <section className="grid gap-4 sm:grid-cols-3">
            <StatCard label="Videos analyzed" value={q.data.videos_analyzed} />
            <StatCard label="Typical score" value={q.data.anomaly_distribution.mean != null ? Math.round(q.data.anomaly_distribution.mean) : "—"} hint="Average across videos" />
            <StatCard label="High end" value={q.data.anomaly_distribution.p90 != null ? Math.round(q.data.anomaly_distribution.p90) : "—"} hint="90th percentile" />
          </section>

          <section className="flex flex-col gap-4">
            <h2 className="text-lg font-semibold text-ink">Baselines</h2>
            {baselines.length === 0 ? (
              <EmptyState icon="chart" title="No baselines yet">Baselines appear once there are at least 10 validated samples for this movement.</EmptyState>
            ) : (
              <ul className="grid gap-3 sm:grid-cols-2">
                {baselines.map(([name, b]) => (
                  <li key={name} className="row !justify-between">
                    <span className="font-medium text-ink">{metricLabel(name)}</span>
                    <span className="text-right text-sm text-ink-2">
                      avg <b className="text-ink">{Math.round(b.mean)}°</b> ± {Math.round(b.std)}°
                      <span className="block text-ink-3">{b.sample_size} samples</span>
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </>
  );
}
