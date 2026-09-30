"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api-client";
import Link from "next/link";

type VideoItem = {
  id: string; original_filename: string; movement_type: string; processing_status: string;
};

export default function ReportsPage() {
  const [videos, setVideos] = useState<VideoItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

  useEffect(() => {
    apiClient.fetchWithAuth("/videos?page_size=50")
      .then((d: any) => setVideos(d.items || []))
      .catch((e: any) => setError(e.message || "Failed to load videos"));
  }, []);

  if (error) return <div className="status-pill status-pill--danger p-4">{error}</div>;

  return (
    <div>
      <section className="bento-hero bento-hero--purple">
        <div>
          <h2 className="bento-hero__title">Reports & Export</h2>
          <p className="bento-hero__subtitle">Methodology note preserved on every export. PDF for sharing, Excel for analysis, CSV for raw frames.</p>
        </div>
      </section>

      <div className="bento-card" style={{ marginTop: 32, padding: "8px 0" }}>
        {videos.length === 0 && (
          <div className="drawer-item text-sm" style={{ color: "var(--text-secondary)" }}>
            No videos yet — <Link href="/videos/upload" className="underline" style={{ color: "var(--brand-dark)" }}>upload one</Link> to generate reports.
          </div>
        )}
        {videos.map((v) => (
          <div key={v.id} className="drawer-item">
            <div style={{ flex: 1 }}>
              <div className="font-semibold" style={{ color: "var(--text-primary)", fontSize: 15 }}>{v.original_filename}</div>
              <div className="text-xs capitalize mt-1" style={{ color: "var(--text-secondary)" }}>
                {v.movement_type} — {v.processing_status}
              </div>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <Link href={`/videos/${v.id}/results`} className="pill-btn--outline text-xs">View</Link>
              {v.processing_status === "completed" && (<>
                <a href={`${apiBase}/videos/${v.id}/report.pdf`} className="pill-btn--soft text-xs">PDF</a>
                <a href={`${apiBase}/videos/${v.id}/report.xlsx`} className="pill-btn--primary text-xs">Excel</a>
              </>)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
