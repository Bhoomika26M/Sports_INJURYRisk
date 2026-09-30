"use client";

import { useState } from "react";
import { apiClient } from "@/lib/api-client";
import { useRouter, useSearchParams } from "next/navigation";

type Athlete = { id: string; full_name: string | null; sport_type: string };

type MovementType = { code: string; display_name: string; camera_views: string[] };

export default function UploadVideoPage() {
  const searchParams = useSearchParams();
  const preselectedAthleteId = searchParams.get("athlete_id");
  const router = useRouter();

  const [athletes, setAthletes] = useState<Athlete[]>([]);
  const [movementTypes, setMovementTypes] = useState<MovementType[]>([]);
  const [selectedAthleteId, setSelectedAthleteId] = useState(preselectedAthleteId || "");
  const [selectedMovementType, setSelectedMovementType] = useState("");
  const [selectedCameraView, setSelectedCameraView] = useState("sagittal");
  const [file, setFile] = useState<File | null>(null);
  const [originalFilename, setOriginalFilename] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [processing, setProcessing] = useState(false);
  const [videoId, setVideoId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [stage, setStage] = useState<"select" | "upload" | "processing" | "complete">("select");

  const loadData = async () => {
    const [athletesRes, movementTypesRes] = await Promise.all([
      apiClient.fetchWithAuth("/athletes?page_size=100"),
      apiClient.fetchWithAuth("/videos/movement-types"),
    ]);
    setAthletes(athletesRes.items || []);
    setMovementTypes(movementTypesRes);
    if (preselectedAthleteId) setSelectedAthleteId(preselectedAthleteId);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (!f.name.toLowerCase().endsWith(".mp4") && !f.name.toLowerCase().endsWith(".mov")) {
      setError("Only .mp4 or .mov files are allowed");
      return;
    }
    if (f.size > 200 * 1024 * 1024) {
      setError("File exceeds 200MB limit");
      return;
    }
    setFile(f);
    setOriginalFilename(f.name);
    setError(null);
  };

  const getAllowedViews = () => {
    const mt = movementTypes.find(m => m.code === selectedMovementType);
    return mt?.camera_views || ["sagittal", "frontal", "other"];
  };

  const handleCreateUpload = async () => {
    if (!selectedAthleteId || !selectedMovementType || !file) {
      setError("Please select athlete, movement type, and file");
      return;
    }
    setError(null);
    setUploading(true);
    setUploadProgress(0);

    try {
      // 1. Create upload URL
      const uploadRes = await apiClient.fetchWithAuth("/videos/upload-url", {
        method: "POST",
        body: JSON.stringify({
          athlete_id: selectedAthleteId,
          movement_type: selectedMovementType,
          camera_view: selectedCameraView,
          original_filename: originalFilename,
        }),
      });

      // 2. Upload file to local storage mock
      const uploadUrl = uploadRes.upload_url;
      const xhr = new XMLHttpRequest();
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) setUploadProgress(Math.round((e.loaded / e.total) * 100));
      };
      await new Promise<void>((resolve, reject) => {
        xhr.open("PUT", uploadUrl);
        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) resolve();
          else reject(new Error("Upload failed"));
        };
        xhr.onerror = () => reject(new Error("Upload failed"));
        xhr.send(file);
      });

      // 3. Confirm upload
      await apiClient.fetchWithAuth(`/videos/${uploadRes.video_id}/confirm-upload`, {
        method: "POST",
      });

      setVideoId(uploadRes.video_id);
      setStage("processing");
      setProcessing(true);
      setUploading(false);

      // Poll for completion
      pollProcessing(uploadRes.video_id);
    } catch (e: any) {
      setError(e.message || "Upload failed");
      setUploading(false);
    }
  };

  const pollProcessing = async (vid: string) => {
    const check = async () => {
      try {
        const v = await apiClient.fetchWithAuth(`/videos/${vid}`);
        if (v.processing_status === "completed") {
          setProcessing(false);
          setStage("complete");
        } else if (v.processing_status === "failed") {
          setProcessing(false);
          setStage("select");
          setError(v.error_message || "Processing failed");
        } else {
          setTimeout(check, 2000);
        }
      } catch {
        setTimeout(check, 2000);
      }
    };
    check();
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>Upload Movement Video</h1>
        <p className="text-sm" style={{ color: "var(--text-secondary)" }}>Upload a movement clip for biomechanical analysis and injury risk scoring.</p>
      </div>

      {error && <div className="status-pill status-pill--danger p-4">{error}</div>}

      {stage === "select" && (
        <form className="bento-card p-6 space-y-6" onSubmit={e => { e.preventDefault(); handleCreateUpload(); }}>
          <div>
            <label className="block text-xs font-semibold uppercase mb-1.5" style={{ color: "var(--text-muted)", letterSpacing: "0.05em" }}>
              Athlete
            </label>
            <select className="field-input" value={selectedAthleteId} onChange={e => setSelectedAthleteId(e.target.value)} required>
              <option value="">Select athlete</option>
              {athletes.map(a => <option key={a.id} value={a.id}>{a.full_name} — {a.sport_type}</option>)}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase mb-1.5" style={{ color: "var(--text-muted)", letterSpacing: "0.05em" }}>
              Movement Type
            </label>
            <select className="field-input" value={selectedMovementType} onChange={e => { setSelectedMovementType(e.target.value); setSelectedCameraView("sagittal"); }} required>
              <option value="">Select movement</option>
              {movementTypes.map(mt => <option key={mt.code} value={mt.code}>{mt.display_name}</option>)}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase mb-1.5" style={{ color: "var(--text-muted)", letterSpacing: "0.05em" }}>
              Camera View
            </label>
            <select className="field-input" value={selectedCameraView} onChange={e => setSelectedCameraView(e.target.value)} required>
              {getAllowedViews().map(v => <option key={v} value={v}>{v.charAt(0).toUpperCase() + v.slice(1)}</option>)}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase mb-1.5" style={{ color: "var(--text-muted)", letterSpacing: "0.05em" }}>
              Video File (.mp4 or .mov, max 200MB, 2-60s)
            </label>
            <input type="file" accept=".mp4,.mov" className="field-input" onChange={handleFileChange} required />
            {originalFilename && <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>{originalFilename}</p>}
          </div>

          <div className="pt-2">
            <button type="submit" disabled={!file || uploading} className="pill-btn--primary w-full justify-center">
              {uploading ? `Uploading... ${uploadProgress}%` : "Upload & Analyze"}
            </button>
          </div>
        </form>
      )}

      {stage === "processing" && (
        <div className="bento-card p-6 text-center space-y-4">
          <div className="circle-action-btn mx-auto animate-spin" style={{ width: 56, height: 56, background: "var(--brand-tint)", color: "var(--brand-text)" }}>⏳</div>
          <h3 className="text-lg font-semibold" style={{ color: "var(--text-primary)" }}>Processing Video</h3>
          <p style={{ color: "var(--text-secondary)" }}>Running YOLO tracking, MediaPipe pose estimation, and biomechanical analysis...</p>
          <div className="w-64 mx-auto h-2 bg-muted rounded-full overflow-hidden" style={{ background: "var(--bg-muted)" }}>
            <div className="h-full bg-primary transition-all duration-500" style={{ width: "0%", background: "var(--brand-primary)" }}></div>
          </div>
        </div>
      )}

      {stage === "complete" && videoId && (
        <div className="bento-card p-6 text-center space-y-4">
          <div className="circle-action-btn mx-auto" style={{ width: 56, height: 56, background: "var(--brand-tint)", color: "var(--brand-text)" }}>✓</div>
          <h3 className="text-lg font-semibold" style={{ color: "var(--text-primary)" }}>Analysis Complete!</h3>
          <p style={{ color: "var(--text-secondary)" }}>Your video has been processed and analyzed.</p>
          <div className="flex justify-center gap-3">
            <button onClick={() => router.push(`/videos/${videoId}/results`)} className="pill-btn--primary">View Results</button>
            <button onClick={() => router.push("/videos/upload")} className="pill-btn--outline">Upload Another</button>
          </div>
        </div>
      )}
    </div>
  );
}