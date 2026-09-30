"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiClient } from "@/lib/api-client";

export default function PhysioDashboard() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiClient.fetchWithAuth("/analytics/coach")
      .then(setData)
      .catch((e: any) => setError(e.message));
  }, []);

  if (error) return <div className="status-pill status-pill--danger p-4">{error}</div>;
  if (!data) return <div className="bento-card p-6">Loading rehabilitation overview…</div>;

  const flagged = (data.athletes || []).filter((a: any) =>
    a.latest_risk_category === "high" || a.latest_risk_category === "critical");

  return (
    <div>
      <section className="bento-hero bento-hero--purple">
        <div>
          <h2 className="bento-hero__title">Rehabilitation tracking</h2>
          <p className="bento-hero__subtitle">
            {flagged.length} athletes flagged high/critical · {data.athletes.length} under observation
          </p>
        </div>
      </section>

      <section className="bento-card" style={{ marginTop: 32, padding: "8px 0" }}>
        {flagged.map((a: any) => (
          <div key={a.athlete_id} className="drawer-item">
            <div style={{ flex: 1 }}>
              <div className="flex items-center gap-2">
                <span className="font-semibold" style={{ color: "var(--text-primary)", fontSize: 15 }}>{a.name || "Unnamed"}</span>
                <span className="status-pill status-pill--warn">{a.latest_risk_category} · {a.latest_risk_score}</span>
              </div>
              <div className="text-xs mt-1" style={{ color: "var(--text-secondary)" }}>
                {a.sport} · last assessed {a.last_assessed ? a.last_assessed.slice(0, 10) : "never"}
              </div>
            </div>
            <Link href={`/athletes/${a.athlete_id}`} className="pill-btn--outline text-xs">Review</Link>
          </div>
        ))}
        {flagged.length === 0 && (
          <div className="drawer-item text-sm" style={{ color: "var(--text-secondary)" }}>No athletes currently flagged. All clear.</div>
        )}
      </section>
    </div>
  );
}
