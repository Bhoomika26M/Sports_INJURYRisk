"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api-client";

const MOVEMENTS = ["squatting", "landing", "running", "sprinting", "jumping", "throwing", "cutting"];

export default function ScientistDashboard() {
  const [selected, setSelected] = useState("squatting");
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setData(null);
    apiClient.fetchWithAuth(`/analytics/movement-types/${selected}`)
      .then(setData)
      .catch((e: any) => setError(e.message));
  }, [selected]);

  return (
    <div>
      <section className="bento-hero bento-hero--blue">
        <div>
          <h2 className="bento-hero__title">Biomechanical analytics</h2>
          <p className="bento-hero__subtitle">Population baselines and anomaly distributions per movement type.</p>
          <div className="flex gap-2 flex-wrap" style={{ marginTop: 16 }}>
            {MOVEMENTS.map((m) => (
              <button key={m} onClick={() => setSelected(m)}
                className={m === selected ? "pill-btn--primary text-xs" : "pill-btn--outline text-xs"}>
                {m}
              </button>
            ))}
          </div>
        </div>
      </section>

      {error && <div className="status-pill status-pill--danger p-4" style={{ marginTop: 24 }}>{error}</div>}

      <section className="grid grid-cols-1 md:grid-cols-2 gap-6" style={{ marginTop: 32 }}>
        <div className="bento-account-card">
          <span className="bento-account-card__label">Videos analyzed · {selected}</span>
          <span className="bento-account-card__amount">{data ? data.videos_analyzed : "—"}</span>
          <span className="text-sm" style={{ color: "var(--text-secondary)" }}>
            {data ? `Anomaly mean ${data.anomaly_distribution.mean ?? "—"} · p90 ${data.anomaly_distribution.p90 ?? "—"}` : "Loading…"}
          </span>
        </div>
        <div className="bento-card p-6">
          <h3 className="font-semibold mb-3" style={{ color: "var(--text-primary)" }}>Baselines</h3>
          {!data ? <p className="text-sm" style={{ color: "var(--text-secondary)" }}>Loading…</p> :
            Object.keys(data.baselines).length === 0 ? <p className="text-sm" style={{ color: "var(--text-secondary)" }}>No baselines yet. A baseline needs at least 5 completed videos from at least 3 athletes.</p> :
            <div className="space-y-2">
              {Object.entries(data.baselines).map(([name, b]: any) => (
                <div key={name} className="flex justify-between text-sm">
                  <span style={{ color: "var(--text-primary)" }}>{name}</span>
                  <span style={{ color: "var(--text-secondary)" }}>
                    {b.sufficient
                      ? `μ ${b.mean} · σ ${b.std} · ${b.video_count} videos / ${b.athlete_count} athletes (${b.sample_size} frames)`
                      : `not enough data yet · ${b.video_count} videos / ${b.athlete_count} athletes`}
                  </span>
                </div>
              ))}
            </div>}
        </div>
      </section>
    </div>
  );
}
