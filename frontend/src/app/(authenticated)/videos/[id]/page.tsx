"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiClient, fetchAsObjectUrl } from "@/lib/api-client";

type VideoDetails = {
  id: string;
  processing_status: string;
  error_message?: string;
  progress_pct: number;
  thumbnail_key?: string;
  original_filename: string;
  movement_type: string;
  created_at: string;
};

export default function VideoStatusPage() {
  const { id } = useParams() as { id: string };
  const router = useRouter();
  const [video, setVideo] = useState<VideoDetails | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [thumbnailUrl, setThumbnailUrl] = useState<string | null>(null);

  // Hook 1: Poll status
  useEffect(() => {
    let interval: NodeJS.Timeout;

    async function pollStatus() {
      try {
        const res = await apiClient.fetchWithAuth(`/videos/${id}`);
        setVideo(res);
        
        if (res.thumbnail_key && !thumbnailUrl) {
          const url = await fetchAsObjectUrl(`/videos/${id}/thumbnail`);
          setThumbnailUrl(url);
        }

        if (res.processing_status === "completed") {
          router.replace(`/videos/${id}/results`);
        }
      } catch (err: any) {
        setError(err.message || "Failed to fetch video status");
      }
    }

    // Initial poll
    pollStatus();

    // Poll every 4 seconds as per spec
    interval = setInterval(pollStatus, 4000);

    return () => clearInterval(interval);
  }, [id, router, thumbnailUrl]);

  // Hook 2: Cleanup object URL on unmount (MUST BE BEFORE ANY EARLY RETURN)
  useEffect(() => {
    return () => {
      if (thumbnailUrl) URL.revokeObjectURL(thumbnailUrl);
    };
  }, [thumbnailUrl]);

  if (error) {
    return (
      <div className="max-w-2xl mx-auto space-y-4">
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm p-5 rounded-2xl flex items-center gap-3">
          <svg className="w-5 h-5 text-red-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <div className="font-semibold">Error Loading Video</div>
            <div className="text-xs text-red-600 mt-0.5">{error}</div>
          </div>
        </div>
      </div>
    );
  }

  if (!video) {
    return (
      <div className="max-w-2xl mx-auto py-20 flex items-center justify-center">
        <div className="neu-card p-6 rounded-2xl flex items-center gap-3 text-slate-700">
          <svg className="animate-spin h-5 w-5 text-blue-600" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span className="text-sm font-medium">Fetching video processing status...</span>
        </div>
      </div>
    );
  }

  const isProcessing = video.processing_status === "queued" || video.processing_status === "processing";
  const isFailed = video.processing_status === "failed";

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900">
            Video Processing
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            {video.original_filename} • <span className="capitalize font-medium text-slate-700">{video.movement_type}</span>
          </p>
        </div>
        <span className={`text-xs font-bold uppercase tracking-wider px-3 py-1 rounded-full ${
          isFailed
            ? "bg-red-50 text-red-700 border border-red-200"
            : "bg-blue-50 text-blue-700 border border-blue-200"
        }`}>
          {video.processing_status.replace("_", " ")}
        </span>
      </div>

      <div 
        className="bg-white rounded-2xl border-2 border-slate-300 overflow-hidden"
        style={{ boxShadow: "6px 6px 16px rgba(148, 163, 184, 0.38), -6px -6px 16px rgba(255, 255, 255, 0.95)" }}
      >
        {/* Video Thumbnail area */}
        <div className="aspect-video bg-slate-900 relative flex items-center justify-center">
          {thumbnailUrl ? (
            <img 
              src={thumbnailUrl} 
              alt="Video Thumbnail"
              className="w-full h-full object-cover"
              onError={(e) => { e.currentTarget.style.display = 'none'; }}
            />
          ) : (
            <div className="text-center text-slate-400 space-y-2">
              <svg className="w-12 h-12 mx-auto text-slate-500 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
              <div className="text-xs font-semibold text-slate-400">Processing video frames...</div>
            </div>
          )}
        </div>

        {/* Status details & Progress */}
        <div className="p-6 sm:p-8 space-y-6">
          {isFailed ? (
            <div className="bg-red-50 border-2 border-red-200 text-red-800 text-sm p-4 rounded-xl space-y-1">
              <div className="font-bold flex items-center gap-2">
                <svg className="w-4 h-4 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
                <span>Processing Error</span>
              </div>
              <p className="text-xs text-red-700 pl-6 font-medium">{video.error_message || "An unexpected error occurred during analysis."}</p>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex justify-between items-center text-xs font-black text-slate-700">
                <span className="uppercase tracking-wider">Analysis Progress</span>
                <span className="text-blue-600 font-black">{video.progress_pct}%</span>
              </div>

              <div className="w-full bg-slate-100 border-2 border-slate-300 rounded-full h-4 overflow-hidden p-0.5">
                <div 
                  className="bg-blue-600 h-full rounded-full transition-all duration-700 shadow-sm" 
                  style={{ width: `${Math.max(8, video.progress_pct)}%` }}
                />
              </div>

              <div className="flex items-center gap-2 text-xs font-semibold text-slate-600 pt-2">
                <svg className="w-4 h-4 text-blue-600 animate-spin shrink-0" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span>Estimating body keypoints (MediaPipe Pose + YOLOv8) and calculating joint angles...</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
