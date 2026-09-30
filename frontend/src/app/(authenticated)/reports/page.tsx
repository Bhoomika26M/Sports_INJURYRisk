"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api-client";
import Link from "next/link";

type VideoItem = { id: string; original_filename: string; movement_type: string; processing_status: string };

export default function ReportsPage() {
  const [videos, setVideos] = useState<VideoItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiClient
      .fetchWithAuth("/videos?page_size=50")
      .then((d: any) => setVideos(d.items || []))
      .catch((e: any) => setError(e.message || "Failed to load videos"));
  }, []);

  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

  if (error) return <div className="status-pill status-pill--danger">{error}</div>;

  return (
    <div>
      <section className="bento-hero bento-hero--purple">
        <div>
          <h2 className="bento-hero__title">Reports & Export</h2>
          <p className="bento-hero__subtitle">Risk, biomechanical, and movement reports — methodology note preserved on every export.</p>
        </div>
      </section>
      <div className="bento-card" style={{ marginTop: 40, padding: "8px 0" }}>
        {videos.map((v) => (
          <div key={v.id} className="drawer-item">
            <div style={{ flex: 1 }}>
              <div className="font-semibold" style={{ color: "var(--text-primary)", fontSize: 15 }}>{v.original_filename}</div>
              <div className="text-xs capitalize" style={{ color: "var(--text-secondary)" }}>{v.movement_type} — {v.processing_status}</div>
            </div>
            <div className="flex items-center gap-2">
              <Link href={`/videos/${v.id}/results`} className="pill-btn--outline">View</Link>
              <a href={`${apiBase}/videos/${v.id}/report.pdf`} className="pill-btn--soft">PDF</a>
              <a href={`${apiBase}/videos/${v.id}/report.xlsx`} className="pill-btn--primary">Excel</a>
            </div>
          </div>
        ))}
        {videos.length === 0 && <div className="drawer-item text-sm" style={{ color: "var(--text-secondary)" }}>No videos yet — upload one to generate reports.</div>}
      </div>
    </div>
  );
}
