"use client";

import type { MetricDelta } from "@/lib/types";
import { Icon } from "@/components/icons";

interface ComparisonMetricsTableProps {
  deltas: MetricDelta[];
  summary: string;
  caveats?: string[];
  referenceFilename?: string | null;
  comparisonFilename?: string | null;
}

function formatValue(val: number | string | null | undefined, unit?: string | null): string {
  if (val === null || val === undefined || val === "") {
    return "unavailable";
  }
  if (typeof val === "string") {
    return val;
  }
  if (unit === "deg") {
    return `${Math.round(val)}°`;
  }
  if (unit === "pct") {
    return `${val.toFixed(1)}%`;
  }
  if (unit === "m") {
    return `${val.toFixed(2)} m`;
  }
  if (unit === "s") {
    return `${val.toFixed(2)} s`;
  }
  if (unit === "deg_s") {
    return `${Math.round(val)}°/s`;
  }
  return String(val);
}

function formatDelta(delta: number | null | undefined, unit?: string | null): string {
  if (delta === null || delta === undefined) {
    return "—";
  }
  if (unit === "deg") {
    const rounded = Math.round(delta);
    return `${rounded > 0 ? "+" : ""}${rounded}°`;
  }
  if (unit === "pct") {
    return `${delta > 0 ? "+" : ""}${delta.toFixed(1)}%`;
  }
  return `${delta > 0 ? "+" : ""}${delta.toFixed(1)}`;
}

export function ComparisonMetricsTable({
  deltas,
  summary,
  caveats = [],
  referenceFilename = "Reference",
  comparisonFilename = "Comparison",
}: ComparisonMetricsTableProps) {
  return (
    <div className="flex flex-col gap-6">
      {/* Noise floor and scientific constraint note */}
      <div className="rounded-2xl border border-brand-dark/20 bg-brand-light/30 p-4 text-xs text-ink-2">
        <div className="flex items-start gap-2.5">
          <Icon name="info" className="h-4 w-4 text-brand-dark shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-semibold text-ink">
              Pose Tracking Noise Floor Notice
            </p>
            <p className="leading-relaxed">
              Differences under about 7° are within markerless pose-tracking noise (RMSE ≈ 6.5°).
              Joint angles are rounded to whole degrees. Comparisons highlight kinematic pattern
              differences rather than clinical diagnostic predictions.
            </p>
          </div>
        </div>
      </div>

      {caveats.length > 0 && (
        <div className="rounded-2xl border border-amber-300 bg-amber-50/80 p-4 text-xs text-amber-900">
          <div className="flex items-start gap-2.5">
            <Icon name="alert" className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">Coverage Caveats</p>
              <ul className="mt-1 list-disc pl-4 space-y-0.5">
                {caveats.map((c, idx) => (
                  <li key={idx}>{c}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Metrics Table */}
      <section className="card p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
          <div>
            <h3 className="font-bold text-ink">Kinematic Comparison</h3>
            <p className="text-xs text-ink-3">
              Parameter-by-parameter delta between Reference and Comparison clips.
            </p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-black/5 text-ink-3">
                <th className="pb-3 font-semibold uppercase tracking-wider">Kinematic Parameter</th>
                <th className="pb-3 font-semibold uppercase tracking-wider">Reference ({referenceFilename || "Clip A"})</th>
                <th className="pb-3 font-semibold uppercase tracking-wider">Comparison ({comparisonFilename || "Clip B"})</th>
                <th className="pb-3 font-semibold uppercase tracking-wider">Delta (Δ)</th>
                <th className="pb-3 font-semibold uppercase tracking-wider">Verdict</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-black/5">
              {deltas.map((item, idx) => (
                <tr key={idx} className="hover:bg-black/2 transition-colors">
                  <td className="py-3 font-semibold text-ink">
                    <div>{item.label}</div>
                    {item.reason && (
                      <div className="text-[11px] font-normal text-ink-3 mt-0.5 max-w-xs">
                        {item.reason}
                      </div>
                    )}
                  </td>
                  <td className="py-3 font-medium text-ink-2">
                    {formatValue(item.video_a, item.unit)}
                  </td>
                  <td className="py-3 font-bold text-ink">
                    {formatValue(item.video_b, item.unit)}
                  </td>
                  <td className="py-3 font-mono font-medium">
                    {formatDelta(item.delta, item.unit)}
                  </td>
                  <td className="py-3 font-semibold">
                    {item.verdict === "within_noise" && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-700 font-medium">
                        <Icon name="check" className="h-3 w-3 text-slate-500" />
                        <span>Within noise (&lt; 7°)</span>
                      </span>
                    )}
                    {item.verdict === "higher" && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-xs text-amber-800 font-medium border border-amber-200">
                        <Icon name="activity" className="h-3 w-3 text-amber-600" />
                        <span>Higher</span>
                      </span>
                    )}
                    {item.verdict === "lower" && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-sky-50 px-2 py-0.5 text-xs text-sky-800 font-medium border border-sky-200">
                        <Icon name="activity" className="h-3 w-3 text-sky-600" />
                        <span>Lower</span>
                      </span>
                    )}
                    {item.verdict === "not_comparable" && (
                      <span className="text-ink-4 italic">Not comparable</span>
                    )}
                    {item.verdict === "no_verdict" && (
                      <span className="text-ink-3 font-normal">Recorded</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Deterministic Kinematic Summary */}
      <section className="card p-6 bg-surface-2 border border-black/5">
        <div className="flex items-center gap-2 mb-2">
          <Icon name="activity" className="h-4 w-4 text-brand-dark" />
          <h4 className="font-bold text-ink text-sm">Deterministic Kinematic Summary</h4>
        </div>
        <p className="text-xs text-ink-2 leading-relaxed whitespace-pre-line">
          {summary}
        </p>
      </section>
    </div>
  );
}
