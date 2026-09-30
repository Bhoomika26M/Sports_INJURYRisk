"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiClient } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

export default function AthleteDashboard() {
  const { user } = useAuth();
  const [trend, setTrend] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const athletes = await apiClient.fetchWithAuth("/athletes?page_size=1");
        if ((athletes.items || []).length === 0) return;
        const t = await apiClient.fetchWithAuth(`/analytics/athletes/${athletes.items[0].id}/trends`);
        setTrend(t);
      } catch (e: any) {
        setError(e.message);
      }
    })();
  }, []);

  const latest = trend?.points?.[0];

  return (
    <div>
      <section className="bento-hero bento-hero--yellow">
        <div>
          <span className="status-pill status-pill--muted">athlete</span>
          <h2 className="bento-hero__title" style={{ marginTop: 12 }}>Welcome, {user?.full_name}</h2>
          <p className="bento-hero__subtitle">
            {latest ? `Latest score ${latest.overall_score} (${latest.risk_category}) — ${latest.movement_type}` : "Upload your first movement video to start tracking."}
          </p>
          <div className="flex gap-3" style={{ marginTop: 20 }}>
            <Link href="/videos/upload" className="pill-btn--primary">Upload video</Link>
            <Link href="/reports" className="pill-btn--soft">My reports</Link>
          </div>
        </div>
        <div className="circle-action-btn" aria-hidden>+</div>
      </section>

      {error && <div className="status-pill status-pill--danger p-4" style={{ marginTop: 24 }}>{error}</div>}

      <section className="bento-card p-6" style={{ marginTop: 32 }}>
        <h3 className="font-semibold mb-4" style={{ color: "var(--text-primary)" }}>Risk trend</h3>
        {!trend || trend.total === 0 ? (
          <p className="text-sm" style={{ color: "var(--text-secondary)" }}>No scored videos yet.</p>
        ) : (
          <div style={{ width: "100%", height: 280 }}>
            <ResponsiveContainer>
              <LineChart data={[...trend.points].reverse()}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-hair)" />
                <XAxis dataKey="created_at" tick={{ fontSize: 10 }} tickFormatter={(v: string) => v.slice(0, 10)} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Line type="monotone" dataKey="overall_score" stroke="#163300" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
        <p className="text-xs italic mt-3" style={{ color: "var(--text-muted)" }}>{trend?.methodology_note}</p>
      </section>
    </div>
  );
}
