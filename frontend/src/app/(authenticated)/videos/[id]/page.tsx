"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api-client";
import { useParams, useRouter } from "next/navigation";

type Video = {
  id: string;
  original_filename: string;
  movement_type: string;
  camera_view: string;
  processing_status: string;
  annotated_video_key?: string;
  storage_key?: string;
  error_message?: string | null;
  fps: number;
  duration_seconds: number;
};

export default function VideoDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { id } = params;

  const [video, setVideo] = useState<Video | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiClient.fetchWithAuth(`/videos/${id}`).then(setVideo).catch((e: any) => setError(e.message)).finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="bento-card p-6 flex items-center gap-3" style={{ color: "var(--text-primary)" }}><svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24" style={{ color: "var(--brand-dark)" }}><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg><span className="text-sm font-bold">Loading...</span></div>;
  if (error) return <div className="status-pill status-pill--danger p-4">{error}</div>;
  if (!video) return <div className="status-pill status-pill--danger p-4">Video not found</div>;

  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

  return (
    <div className="space-y-6">
      <div className="bento-card p-6 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="status-pill status-pill--muted">{video.movement_type}</span>
            <span className="status-pill" style={{ background: video.processing_status === "completed" ? "var(--brand-tint)" : "var(--warning-bg)", color: video.processing_status === "completed" ? "var(--brand-text)" : "var(--warning-fg)" }}>
              {video.processing_status}
            </span>
          </div>
          <h1 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>{video.original_filename}</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>
            {video.movement_type} • {video.camera_view} view • {video.duration_seconds?.toFixed(1)}s @ {video.fps?.toFixed(1)}fps
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button onClick={() => router.push(`/videos/${id}/results`)} className="pill-btn--primary" disabled={video.processing_status !== "completed"}>View Results</button>
          <a href={`${apiBase}/videos/${id}/report.pdf`} className="pill-btn--soft">PDF Report</a>
          <a href={`${apiBase}/videos/${id}/report.xlsx`} className="pill-btn--primary">Excel</a>
        </div>
      </div>

      <div className="bento-card overflow-hidden">
        <video
          src={video.annotated_video_key ? `${apiBase}/videos/${id}/file` : `${apiBase}/local-storage/${video.storage_key}`}
          controls
          className="w-full aspect-video"
          style={{ background: "var(--bg-muted)" }}
        />
      </div>

      {video.processing_status === "failed" && (
        <div className="bento-card p-6 border-red-200" style={{ color: "var(--danger-fg)" }}>
          <h3 className="font-semibold mb-1">Processing Failed</h3>
          <p className="text-sm">Error: {video.error_message || "Unknown error"}</p>
        </div>
      )}

      {video.processing_status === "processing" && (
        <div className="bento-card p-6 text-center">
          <div className="circle-action-btn mx-auto animate-spin" style={{ width: 48, height: 48, background: "var(--brand-tint)", color: "var(--brand-text)" }}>⏳</div>
          <p className="mt-2" style={{ color: "var(--text-secondary)" }}>Video is still processing...</p>
        </div>
      )}
    </div>
  );
}