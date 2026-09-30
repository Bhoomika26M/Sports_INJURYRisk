"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiClient } from "@/lib/api-client";

export default function CoachDashboard() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiClient.fetchWithAuth("/analytics/coach")
      .then(setData)
      .catch((e: any) => setError(e.message));
  }, []);

  if (error) return <div className="status-pill status-pill--danger p-4">{error}</div>;
  if (!data) return <div className="bento-card p-6">Loading team overview…</div>;

  const o = data.overview;

  return (
    <div>
      <section className="bento-hero bento-hero--blue">
        <div>
          <h2 className="bento-hero__title">Team overview</h2>
          <p className="bento-hero__subtitle">
            {o.total_athletes} athletes · {o.videos_completed}/{o.total_videos} videos completed ·
            avg risk {o.avg_risk_score ?? "—"} · {o.high_risk_count + o.critical_risk_count} high/critical
          </p>
        </div>
      </section>

      <section className="grid grid-cols-2 md:grid-cols-4 gap-6" style={{ marginTop: 32 }}>
        {[["Low", o.low_risk_count, "status-pill--ok"], ["Moderate", o.moderate_risk_count, "status-pill--info"],
          ["High", o.high_risk_count, "status-pill--warn"], ["Critical", o.critical_risk_count, "status-pill--danger"],
        ].map(([label, count, cls]) => (
          <div key={label as string} className="bento-account-card">
            <span className="bento-account-card__label">{label}</span>
            <span className="bento-account-card__amount">{count as number}</span>
            <span className={`status-pill ${cls}`}>{label} risk athletes</span>
          </div>
        ))}
      </section>

      <section className="bento-card" style={{ marginTop: 32, padding: "8px 0" }}>
        {(data.athletes || []).map((a: any) => (
          <div key={a.athlete_id} className="drawer-item">
            <div style={{ flex: 1 }}>
              <div className="font-semibold" style={{ color: "var(--text-primary)", fontSize: 15 }}>{a.name || "Unnamed"} · {a.sport}</div>
              <div className="text-xs mt-1" style={{ color: "var(--text-secondary)" }}>
                {a.latest_risk_score != null ? `Latest ${a.latest_risk_score} (${a.latest_risk_category})` : "Not yet assessed"}
              </div>
            </div>
            <Link href={`/athletes/${a.athlete_id}`} className="pill-btn--outline text-xs">Open</Link>
          </div>
        ))}
        {(data.athletes || []).length === 0 && (
          <div className="drawer-item text-sm" style={{ color: "var(--text-secondary)" }}>No athletes yet.</div>
        )}
      </section>
    </div>
  );
}
