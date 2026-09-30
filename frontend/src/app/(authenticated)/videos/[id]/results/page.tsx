"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { apiClient } from "@/lib/api-client";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";

type Frame = {
  frame_number: number; metric_name: string; metric_value: number;
  plane: string; confidence: string; movement_phase?: string | null;
};

const COLORS = ["#163300", "#1D4ED8", "#B45309", "#6D28D9", "#0E7490", "#BE123C"];

export default function ResultsPage() {
  const { id } = useParams() as { id: string };
  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

  const [frames, setFrames] = useState<Frame[] | null>(null);
  const [risk, setRisk] = useState<any>(null);
  const [recs, setRecs] = useState<any[]>([]);
  const [insufficient, setInsufficient] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const bio = await apiClient.fetchWithAuth(`/videos/${id}/biomechanics`);
        setFrames(bio.frames || []);
        try {
          const rs = await apiClient.fetchWithAuth(`/videos/${id}/risk-score`);
          if (rs.status === "insufficient_baseline_data") {
            setInsufficient(rs);
          } else {
            setRisk(rs);
            const r = await apiClient.fetchWithAuth(`/videos/${id}/recommendations`);
            setRecs(Array.isArray(r) ? r : []);
          }
        } catch (e: any) {
          if (e.status !== 404) throw e;
        }
      } catch (e: any) {
        setError(e.message || "Failed to load results");
      }
    })();
  }, [id]);

  const { chartData, metricNames } = useMemo(() => {
    const names = [...new Set((frames || []).map((f) => f.metric_name))];
    const byFrame = new Map<number, any>();
    for (const f of frames || []) {
      if (!byFrame.has(f.frame_number)) byFrame.set(f.frame_number, { frame_number: f.frame_number });
      byFrame.get(f.frame_number)[f.metric_name] = f.metric_value;
    }
    return { chartData: [...byFrame.values()].sort((a, b) => a.frame_number - b.frame_number), metricNames: names };
  }, [frames]);

  const badgeClass =
    risk?.risk_category === "critical" ? "status-pill--danger"
    : risk?.risk_category === "high" ? "status-pill--warn"
    : risk?.risk_category === "moderate" ? "status-pill--info" : "status-pill--ok";

  if (error) return <div className="status-pill status-pill--danger p-4">{error}</div>;
  if (!frames) return <div className="bento-card p-6">Loading results…</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>Analysis Results</h1>
          <p className="text-sm" style={{ color: "var(--text-secondary)" }}>{frames.length} metric points across {metricNames.length} metrics</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Link href={`/videos/${id}`} className="pill-btn--outline text-xs">Video</Link>
          <a href={`${apiBase}/videos/${id}/biomechanics/export.csv`} className="pill-btn--outline text-xs">CSV</a>
          {risk && (<>
            <a href={`${apiBase}/videos/${id}/report.pdf`} className="pill-btn--soft text-xs">PDF</a>
            <a href={`${apiBase}/videos/${id}/report.xlsx`} className="pill-btn--primary text-xs">Excel</a>
          </>)}
        </div>
      </div>

      {risk ? (
        <section className="bento-hero bento-hero--blue">
          <div>
            <span className={`status-pill ${badgeClass}`}>{risk.risk_category} risk</span>
            <h2 className="bento-hero__title" style={{ marginTop: 12 }}>{risk.overall_score} / 100</h2>
            <p className="bento-hero__subtitle">
              {Object.entries(risk.score_breakdown || {}).map(([k, v]: any) => `${k}: ${v.points}/${v.max}`).join(" · ")}
            </p>
          </div>
        </section>
      ) : insufficient ? (
        <section className="bento-hero bento-hero--yellow">
          <div>
            <h2 className="bento-hero__title">Baseline building</h2>
            <p className="bento-hero__subtitle">
              {insufficient.have}/{insufficient.need} validated samples for {insufficient.metric_name}. Scores unlock at {insufficient.need}.
            </p>
          </div>
        </section>
      ) : (
        <section className="bento-card p-6 text-sm" style={{ color: "var(--text-secondary)" }}>
          No risk score yet for this video.
        </section>
      )}

      {risk?.methodology_note && (
        <p className="text-xs italic" style={{ color: "var(--text-muted)" }}>{risk.methodology_note}</p>
      )}

      <section className="bento-card p-6">
        <h3 className="font-semibold mb-4" style={{ color: "var(--text-primary)" }}>Metrics over time</h3>
        <div style={{ width: "100%", height: 320 }}>
          <ResponsiveContainer>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-hair)" />
              <XAxis dataKey="frame_number" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Legend />
              {metricNames.map((m, i) => (
                <Line key={m} type="monotone" dataKey={m} stroke={COLORS[i % COLORS.length]} dot={false} strokeWidth={2} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>

      {recs.length > 0 && (
        <section>
          <h3 className="text-xl font-semibold mb-4" style={{ color: "var(--text-primary)" }}>Recommendations</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {recs.map((r: any, i: number) => (
              <div key={i} className="dashed-action-card" style={{ cursor: "default" }}>
                <div className="dashed-action-card__icon-wrapper"><span>P{r.priority}</span></div>
                <div className="dashed-action-card__content">
                  <span className="dashed-action-card__title">{r.title}</span>
                  <span className="dashed-action-card__desc">[{r.category}] {r.description}</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
