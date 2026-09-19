"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/api-client";

type Athlete = {
  id: string;
  user_id: string | null;
  sport_type: string;
  position?: string | null;
  full_name?: string | null;
};

export default function UploadVideoPage() {
  const router = useRouter();
  const [athletes, setAthletes] = useState<Athlete[]>([]);
  const [selectedAthlete, setSelectedAthlete] = useState("");
  const [movementType, setMovementType] = useState("squat");
  const [cameraView, setCameraView] = useState("sagittal");
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadAthletes() {
      try {
        const res = await apiClient.fetchWithAuth("/athletes");
        setAthletes(res.items || []);
        if (res.items && res.items.length > 0) {
          setSelectedAthlete(res.items[0].id);
        }
      } catch (err: any) {
        console.error("Failed to load athletes", err);
        setError(err.message || "Failed to load athlete list");
      }
    }
    loadAthletes();
  }, []);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !selectedAthlete) return;

    if (file.size > 200 * 1024 * 1024) {
      setError("File exceeds 200MB limit.");
      return;
    }

    try {
      setUploading(true);
      setError(null);
      setProgress(0);

      // 1. Get presigned upload URL
      const { upload_url, video_id } = await apiClient.fetchWithAuth("/videos/upload-url", {
        method: "POST",
        body: JSON.stringify({
          athlete_id: selectedAthlete,
          movement_type: movementType,
          camera_view: cameraView,
          original_filename: file.name,
          content_type: file.type || "video/mp4",
        }),
      });

      // 2. Upload file to storage with Bearer auth
      const token = await apiClient.ensureToken();
      await new Promise<void>((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable) {
            setProgress(Math.round((event.loaded * 100) / event.total));
          }
        };
        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve();
          } else {
            reject(new Error(`Storage upload failed (${xhr.status}: ${xhr.statusText || 'Unauthorized'})`));
          }
        };
        xhr.onerror = () => reject(new Error("Network error during upload"));
        xhr.open("PUT", upload_url, true);
        if (token) {
          xhr.setRequestHeader("Authorization", `Bearer ${token}`);
        }
        xhr.send(file);
      });

      // 3. Confirm upload with backend
      await apiClient.fetchWithAuth(`/videos/${video_id}/confirm-upload`, {
        method: "POST",
      });

      // 4. Redirect to status page
      router.push(`/videos/${video_id}`);
    } catch (err: any) {
      setError(err.message || "Failed to upload video");
      setUploading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-slate-900">
          Upload Movement Video
        </h1>
        <p className="text-xs sm:text-sm font-medium text-slate-600 mt-1">
          Upload athlete movement video for pose tracking, joint kinematics, and heuristic risk analysis.
        </p>
      </div>

      {error && (
        <div className="bg-red-50 border-2 border-red-300 text-red-800 text-sm p-4 rounded-xl flex items-center gap-3 font-semibold">
          <svg className="w-5 h-5 text-red-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>{error}</span>
        </div>
      )}

      <form 
        onSubmit={handleUpload} 
        className="bg-white rounded-2xl p-6 sm:p-8 border-2 border-slate-300 shadow-md space-y-6"
        style={{ boxShadow: "6px 6px 16px rgba(148, 163, 184, 0.38), -6px -6px 16px rgba(255, 255, 255, 0.95)" }}
      >
        <div>
          <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
            Select Athlete
          </label>
          <select 
            value={selectedAthlete} 
            onChange={e => setSelectedAthlete(e.target.value)}
            disabled={uploading}
            className="w-full bg-slate-50 border-2 border-slate-300 text-slate-900 font-semibold rounded-xl p-3.5 text-sm focus:bg-white focus:border-blue-600 focus:outline-none focus:ring-4 focus:ring-blue-500/20 transition-all"
          >
            {athletes.map(a => {
              const label = a.full_name
                ? `${a.full_name} (${a.sport_type}${a.position ? ` · ${a.position}` : ""})`
                : `${a.sport_type}${a.position ? ` · ${a.position}` : ""} (ID: ${a.id.slice(0, 8)})`;
              return (
                <option key={a.id} value={a.id}>
                  {label}
                </option>
              );
            })}
          </select>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
              Movement Type
            </label>
            <select 
              value={movementType} 
              onChange={e => setMovementType(e.target.value)}
              disabled={uploading}
              className="w-full bg-slate-50 border-2 border-slate-300 text-slate-900 font-semibold rounded-xl p-3.5 text-sm focus:bg-white focus:border-blue-600 focus:outline-none focus:ring-4 focus:ring-blue-500/20 transition-all"
            >
              <option value="squat">Squat</option>
              <option value="deadlift">Deadlift</option>
              <option value="jump">Jump</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
              Camera View
            </label>
            <select 
              value={cameraView} 
              onChange={e => setCameraView(e.target.value)}
              disabled={uploading}
              className="w-full bg-slate-50 border-2 border-slate-300 text-slate-900 font-semibold rounded-xl p-3.5 text-sm focus:bg-white focus:border-blue-600 focus:outline-none focus:ring-4 focus:ring-blue-500/20 transition-all"
            >
              <option value="sagittal">Sagittal (Side View)</option>
              <option value="frontal">Frontal (Front/Back)</option>
              <option value="other">Other</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
            Video File (MP4, MOV)
          </label>
          <div className="rounded-xl p-6 flex flex-col items-center justify-center text-center border-2 border-dashed border-slate-300 bg-slate-50 hover:border-blue-500 hover:bg-blue-50/20 relative group cursor-pointer transition-all">
            <input 
              type="file" 
              accept="video/mp4,video/quicktime"
              onChange={e => setFile(e.target.files?.[0] || null)}
              disabled={uploading}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            />
            <div className="w-12 h-12 rounded-2xl bg-white border-2 border-slate-200 shadow-sm flex items-center justify-center text-blue-600 mb-2 group-hover:scale-110 transition-transform">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>
            {file ? (
              <div>
                <span className="text-sm font-extrabold text-slate-900">{file.name}</span>
                <p className="text-xs font-bold text-blue-600 mt-0.5">{(file.size / (1024 * 1024)).toFixed(1)} MB (Ready)</p>
              </div>
            ) : (
              <div>
                <span className="text-sm font-bold text-blue-600">Click to choose video</span>
                <span className="text-sm font-medium text-slate-600"> or drag and drop</span>
                <p className="text-xs font-medium text-slate-500 mt-1">MP4 or MOV up to 200MB (minimum 480p resolution)</p>
              </div>
            )}
          </div>
        </div>

        <div className="pt-2">
          <button 
            type="submit" 
            disabled={uploading || !file || !selectedAthlete}
            className="w-full bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-extrabold py-4 px-6 rounded-xl text-base shadow-lg shadow-blue-600/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            {uploading ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Uploading & Processing...
              </span>
            ) : (
              "Upload & Analyze"
            )}
          </button>
        </div>

        {uploading && (
          <div className="pt-2 space-y-2">
            <div className="flex justify-between text-xs font-extrabold text-slate-700">
              <span>Uploading to storage...</span>
              <span className="text-blue-600">{progress}%</span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-3 overflow-hidden">
              <div 
                className="bg-blue-600 h-full rounded-full transition-all duration-300" 
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}
      </form>
    </div>
  );
}
