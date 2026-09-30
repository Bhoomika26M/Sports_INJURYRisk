"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiClient } from "@/lib/api-client";

export default function AdminDashboard() {
  const [overview, setOverview] = useState<any>(null);
  const [movements, setMovements] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      apiClient.fetchWithAuth("/analytics/team-overview"),
      apiClient.fetchWithAuth("/videos/movement-types"),
    ]).then(([o, m]) => { setOverview(o); setMovements(m); })
      .catch((e: any) => setError(e.message));
  }, []);

  if (error) return <div className="status-pill status-pill--danger p-4">{error}</div>;
  if (!overview) return <div className="bento-card p-6">Loading platform overview…</div>;

  return (
    <div>
      <section className="bento-hero bento-hero--yellow">
        <div>
          <h2 className="bento-hero__title">Platform administration</h2>
          <p className="bento-hero__subtitle">
            {overview.total_athletes} athletes · {overview.total_videos} videos ·
            {overview.videos_processing} processing · {overview.videos_failed} failed
          </p>
        </div>
      </section>

      <section style={{ marginTop: 32 }}>
        <h3 className="text-xl font-semibold mb-4" style={{ color: "var(--text-primary)" }}>Movement registry</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {movements.map((m: any) => (
            <div key={m.code} className="dashed-action-card" style={{ cursor: "default" }}>
              <div className="dashed-action-card__content">
                <span className="dashed-action-card__title">{m.display_name}</span>
                <span className="dashed-action-card__desc">
                  {m.metrics.length} metrics · views: {m.camera_views.join(", ")}
                </span>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section style={{ marginTop: 32 }}>
        <div className="flex gap-3 flex-wrap">
          <Link href="/athletes" className="pill-btn--outline text-xs">Manage athletes</Link>
          <Link href="/reports" className="pill-btn--outline text-xs">All reports</Link>
          <Link href="/notifications" className="pill-btn--outline text-xs">Notifications</Link>
        </div>
      </section>
    </div>
  );
}
