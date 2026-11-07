"use client";

import { useState, useRef } from "react";
import type { Video, Athlete, UploadTicket } from "@/lib/types";
import { Icon } from "@/components/icons";
import { movementLabel, athleteName } from "@/lib/format";
import { CustomMovementSelect } from "@/components/custom-movement-select";
import { api, uploadFile } from "@/lib/api-client";

export interface VideoProbeInfo {
  width: number;
  height: number;
  duration: number;
  error?: string;
}

export function probeVideoFile(file: File): Promise<VideoProbeInfo> {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file);
    const v = document.createElement("video");
    v.preload = "metadata";
    v.muted = true;
    let settled = false;

    const finish = (result: VideoProbeInfo) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      URL.revokeObjectURL(url);
      v.removeAttribute("src");
      v.load();
      resolve(result);
    };

    const timer = setTimeout(() => {
      finish({ width: 0, height: 0, duration: 0 });
    }, 6000);

    v.onloadedmetadata = () => {
      const w = v.videoWidth || 0;
      const h = v.videoHeight || 0;
      const d = v.duration || 0;

      let err: string | undefined;
      if (h > 0 && h < 480) {
        err = `Resolution is ${w}x${h} (${h}p). Minimum required is 480p for reliable joint tracking.`;
      } else if (d > 0 && d < 2) {
        err = `Duration is ${d.toFixed(1)}s (minimum 2.0s required).`;
      } else if (d > 60) {
        err = `Duration is ${d.toFixed(1)}s (maximum 60.0s allowed).`;
      }
      finish({ width: w, height: h, duration: d, error: err });
    };

    v.onerror = () => {
      finish({ width: 0, height: 0, duration: 0 });
    };

    v.src = url;
  });
}

interface VideoPairSelectorProps {
  completedVideos: Video[];
  athletes: Athlete[];
  userRole?: string;
  selectedAId: string;
  selectedBId: string;
  onSelectA: (id: string) => void;
  onSelectB: (id: string) => void;
  onSwap: () => void;
  onCompare: () => void;
  onUploadSuccess: (idA: string, idB: string, labelA: string, labelB: string) => void;
  isLoading?: boolean;
}

export function VideoPairSelector({
  completedVideos,
  athletes,
  userRole,
  selectedAId,
  selectedBId,
  onSelectA,
  onSelectB,
  onSwap,
  onCompare,
  onUploadSuccess,
  isLoading = false,
}: VideoPairSelectorProps) {
  const [mode, setMode] = useState<"library" | "upload">("library");

  // Fresh upload states
  const [fileA, setFileA] = useState<File | null>(null);
  const [fileB, setFileB] = useState<File | null>(null);
  const [movement, setMovement] = useState<string>("auto");
  const [athleteId, setAthleteId] = useState<string>("");
  const [probeA, setProbeA] = useState<VideoProbeInfo | null>(null);
  const [probeB, setProbeB] = useState<VideoProbeInfo | null>(null);
  const [errorA, setErrorA] = useState<string | null>(null);
  const [errorB, setErrorB] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progressA, setProgressA] = useState(0);
  const [progressB, setProgressB] = useState(0);
  const [statusMessage, setStatusMessage] = useState<string>("");

  const inputARef = useRef<HTMLInputElement>(null);
  const inputBRef = useRef<HTMLInputElement>(null);

  // Pre-flight validation on file select
  const handleFileA = async (file: File | null) => {
    setFileA(file);
    setErrorA(null);
    if (!file) {
      setProbeA(null);
      return;
    }
    const info = await probeVideoFile(file);
    setProbeA(info);
    if (info.error) {
      setErrorA(`${file.name}: ${info.error}`);
    }
  };

  const handleFileB = async (file: File | null) => {
    setFileB(file);
    setErrorB(null);
    if (!file) {
      setProbeB(null);
      return;
    }
    const info = await probeVideoFile(file);
    setProbeB(info);
    if (info.error) {
      setErrorB(`${file.name}: ${info.error}`);
    }
  };

  // Upload and start processing
  const handleUpload = async () => {
    if (!fileA || !fileB) return;
    if (userRole !== "athlete" && !athleteId) {
      return;
    }
    if (probeA?.error || probeB?.error) {
      return;
    }

    setUploading(true);
    setStatusMessage("Requesting upload permissions...");
    try {
      const cameraView = movement === "auto" ? "auto" : "sagittal";

      const [ticketA, ticketB] = await Promise.all([
        api.post<UploadTicket>("/videos/upload-url", {
          athlete_id: athleteId || undefined,
          movement_type: movement,
          camera_view: cameraView,
          original_filename: fileA.name,
        }),
        api.post<UploadTicket>("/videos/upload-url", {
          athlete_id: athleteId || undefined,
          movement_type: movement,
          camera_view: cameraView,
          original_filename: fileB.name,
        }),
      ]);

      setStatusMessage("Uploading both video files in parallel...");
      await Promise.all([
        uploadFile(ticketA.upload_url, fileA, {
          onProgress: (loaded, total) => {
            setProgressA(Math.round((loaded / total) * 100));
          },
        }),
        uploadFile(ticketB.upload_url, fileB, {
          onProgress: (loaded, total) => {
            setProgressB(Math.round((loaded / total) * 100));
          },
        }),
      ]);

      setStatusMessage("Confirming and queuing background analysis...");
      const [confA, confB] = await Promise.allSettled([
        api.post(`/videos/${ticketA.video_id}/confirm-upload`),
        api.post(`/videos/${ticketB.video_id}/confirm-upload`),
      ]);

      if (confA.status === "rejected" || confB.status === "rejected") {
        const errA = confA.status === "rejected" ? `${fileA.name}: Validation failed on server` : null;
        const errB = confB.status === "rejected" ? `${fileB.name}: Validation failed on server` : null;
        if (errA) setErrorA(errA);
        if (errB) setErrorB(errB);
        throw new Error(errA || errB || "Upload confirmation failed");
      }

      onUploadSuccess(ticketA.video_id, ticketB.video_id, fileA.name, fileB.name);
      setUploading(false);
    } catch (err) {
      setUploading(false);
      setStatusMessage(err instanceof Error ? err.message : "Upload failed");
    }
  };

  const isAthleteRequired = userRole !== "athlete";
  const canUpload =
    fileA &&
    fileB &&
    (!isAthleteRequired || !!athleteId) &&
    !errorA &&
    !errorB &&
    !uploading &&
    !isLoading;

  return (
    <div className="card p-6 flex flex-col gap-6">
      {/* Header and Mode switcher */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-black/5 pb-4">
        <div>
          <h2 className="text-lg font-bold text-ink">Form Comparison Studio</h2>
          <p className="text-xs text-ink-3">
            Compare two video performances with synchronized inflection analysis.
          </p>
        </div>

        <div className="flex items-center gap-1.5 rounded-xl bg-surface-2 p-1 text-xs font-semibold self-start sm:self-auto">
          <button
            type="button"
            onClick={() => setMode("library")}
            className={`rounded-lg px-3 py-1 cursor-pointer transition-all flex items-center gap-1.5 ${mode === "library"
                ? "bg-white text-ink shadow-sm font-bold"
                : "text-ink-3 hover:text-ink"
              }`}
          >
            <Icon name="folder" className="h-3.5 w-3.5" />
            <span>Select from Library</span>
          </button>
          <button
            type="button"
            onClick={() => setMode("upload")}
            className={`rounded-lg px-3 py-1 cursor-pointer transition-all flex items-center gap-1.5 ${mode === "upload"
                ? "bg-white text-ink shadow-sm font-bold"
                : "text-ink-3 hover:text-ink"
              }`}
          >
            <Icon name="upload" className="h-3.5 w-3.5" />
            <span>Upload 2 Fresh Videos</span>
          </button>
        </div>
      </div>

      {mode === "library" ? (
        /* Library Mode */
        <div className="flex flex-col gap-6">
          <div className="grid gap-4 sm:grid-cols-2">
            {/* Reference Video A */}
            <div className="flex flex-col gap-2">
              <label className="text-xs font-semibold text-ink flex items-center justify-between">
                <span>1. Reference Video (Standard)</span>
                {selectedAId && (
                  <span className="text-[11px] font-normal text-brand-dark">Selected</span>
                )}
              </label>
              <select
                value={selectedAId}
                onChange={(e) => onSelectA(e.target.value)}
                className="input input-sm text-xs rounded-xl"
              >
                <option value="">Select a completed video...</option>
                {completedVideos.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.original_filename || v.id.slice(0, 8)} ({movementLabel(v.movement_type)}, {v.camera_view})
                  </option>
                ))}
              </select>
            </div>

            {/* Comparison Video B */}
            <div className="flex flex-col gap-2">
              <label className="text-xs font-semibold text-ink flex items-center justify-between">
                <span>2. Comparison Video</span>
                {selectedBId && (
                  <span className="text-[11px] font-normal text-brand-dark">Selected</span>
                )}
              </label>
              <select
                value={selectedBId}
                onChange={(e) => onSelectB(e.target.value)}
                className="input input-sm text-xs rounded-xl"
              >
                <option value="">Select a completed video...</option>
                {completedVideos.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.original_filename || v.id.slice(0, 8)} ({movementLabel(v.movement_type)}, {v.camera_view})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex items-center justify-between pt-2">
            <button
              type="button"
              onClick={onSwap}
              disabled={!selectedAId && !selectedBId}
              className="btn btn-sm btn-ghost cursor-pointer flex items-center gap-1.5"
            >
              <Icon name="refresh" className="h-3.5 w-3.5" />
              <span>Swap Reference & Comparison</span>
            </button>

            <button
              type="button"
              onClick={onCompare}
              disabled={!selectedAId || !selectedBId || isLoading}
              className="btn btn-sm btn-primary cursor-pointer flex items-center gap-1.5"
            >
              <Icon name="activity" className="h-3.5 w-3.5" />
              <span>{isLoading ? "Running Comparison..." : "Run Comparison"}</span>
            </button>
          </div>
        </div>
      ) : (
        /* Fresh Upload Mode */
        <div className="flex flex-col gap-5">
          {/* Athlete Selector */}
          {isAthleteRequired && (
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-ink">
                Athlete Profile (Required)
              </label>
              <select
                value={athleteId}
                onChange={(e) => setAthleteId(e.target.value)}
                className="input input-sm text-xs rounded-xl"
              >
                <option value="">Select athlete from roster...</option>
                {athletes.map((a) => (
                  <option key={a.id} value={a.id}>
                    {athleteName(a)} ({a.sport_type || "General"})
                  </option>
                ))}
              </select>
              {!athleteId && (
                <p className="text-[11px] text-amber-700">
                  Please select an athlete from your roster to associate these clips with.
                </p>
              )}
            </div>
          )}

          {/* Movement Discipline */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-ink">
              Movement Discipline
            </label>
            <CustomMovementSelect value={movement} onChange={setMovement} />
          </div>

          {/* 2 File Pickers */}
          <div className="grid gap-4 sm:grid-cols-2">
            {/* File A */}
            <div className="rounded-2xl border border-black/10 bg-surface-2 p-4 flex flex-col gap-2">
              <span className="text-xs font-bold text-ink">1. Reference Video File</span>
              <input
                ref={inputARef}
                type="file"
                accept="video/mp4,video/quicktime,video/webm"
                className="hidden"
                onChange={(e) => handleFileA(e.target.files?.[0] || null)}
              />
              <button
                type="button"
                onClick={() => inputARef.current?.click()}
                className="btn btn-sm btn-outline text-xs cursor-pointer flex items-center justify-center gap-2"
              >
                <Icon name="upload" className="h-3.5 w-3.5" />
                <span>{fileA ? fileA.name : "Choose Reference Clip"}</span>
              </button>
              {errorA && (
                <p className="text-[11px] text-rose-700 flex items-start gap-1 mt-1 font-medium">
                  <Icon name="alert" className="h-3.5 w-3.5 text-rose-600 shrink-0 mt-0.5" />
                  <span>{errorA}</span>
                </p>
              )}
            </div>

            {/* File B */}
            <div className="rounded-2xl border border-black/10 bg-surface-2 p-4 flex flex-col gap-2">
              <span className="text-xs font-bold text-ink">2. Comparison Video File</span>
              <input
                ref={inputBRef}
                type="file"
                accept="video/mp4,video/quicktime,video/webm"
                className="hidden"
                onChange={(e) => handleFileB(e.target.files?.[0] || null)}
              />
              <button
                type="button"
                onClick={() => inputBRef.current?.click()}
                className="btn btn-sm btn-outline text-xs cursor-pointer flex items-center justify-center gap-2"
              >
                <Icon name="upload" className="h-3.5 w-3.5" />
                <span>{fileB ? fileB.name : "Choose Comparison Clip"}</span>
              </button>
              {errorB && (
                <p className="text-[11px] text-rose-700 flex items-start gap-1 mt-1 font-medium">
                  <Icon name="alert" className="h-3.5 w-3.5 text-rose-600 shrink-0 mt-0.5" />
                  <span>{errorB}</span>
                </p>
              )}
            </div>
          </div>

          {/* Upload Progress HUD */}
          {uploading && (
            <div
              className="rounded-2xl border border-brand-dark/20 bg-brand-light/30 p-4 text-xs space-y-2"
              aria-live="polite"
            >
              <div className="flex items-center gap-2 text-ink font-semibold">
                <Icon name="activity" className="h-4 w-4 text-brand-dark animate-pulse" />
                <span>{statusMessage}</span>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="flex justify-between text-[11px] text-ink-3 mb-1">
                    <span>{fileA?.name || "Reference"}</span>
                    <span>{progressA}%</span>
                  </div>
                  <div className="h-1.5 w-full bg-black/10 rounded-full overflow-hidden">
                    <div className="h-full bg-brand-dark rounded-full transition-all duration-300" style={{ width: `${progressA}%` }} />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-[11px] text-ink-3 mb-1">
                    <span>{fileB?.name || "Comparison"}</span>
                    <span>{progressB}%</span>
                  </div>
                  <div className="h-1.5 w-full bg-black/10 rounded-full overflow-hidden">
                    <div className="h-full bg-brand-dark rounded-full transition-all duration-300" style={{ width: `${progressB}%` }} />
                  </div>
                </div>
              </div>
            </div>
          )}

          <div className="pt-2">
            <button
              type="button"
              onClick={handleUpload}
              disabled={!canUpload}
              className="btn btn-sm btn-primary cursor-pointer flex items-center gap-2 w-full justify-center disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Icon name="activity" className={`h-4 w-4 ${isLoading ? "animate-pulse" : ""}`} />
              <span>{isLoading ? "Analysis in Progress..." : "Upload & Analyze Form"}</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}