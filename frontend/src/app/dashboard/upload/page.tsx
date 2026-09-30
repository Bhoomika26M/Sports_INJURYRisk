"use client";

import { useState } from "react";
import { uploadVideo } from "@/lib/api";

const ACTIVITIES = [
  "Running",
  "Sprinting",
  "Jumping",
  "Squatting",
  "Landing",
  "Throwing",
  "Cutting Movements",
  "Sport-Specific Drills"
];

export default function VideoUploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [activity, setActivity] = useState<string>("Squatting");
  const [surfaceType, setSurfaceType] = useState<string>("Unknown");
  const [footwear, setFootwear] = useState<string>("Unknown");
  const [rpe, setRpe] = useState<number>(5);
  const [sleepQuality, setSleepQuality] = useState<number>(5);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<any>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("Please select a video file first.");
      return;
    }

    setUploading(true);
    setError("");
    setResult(null);

    try {
      const token = localStorage.getItem("token");
      if (!token) throw new Error("No authorization token found");

      const response = await uploadVideo(token, file, activity, surfaceType, footwear, rpe, sleepQuality);
      setResult(response);
    } catch (err: any) {
      setError(err.message || "An error occurred during video upload and processing.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white">Video Upload & Processing Engine</h2>
        <p className="text-slate-400 text-sm mt-1">Upload athlete footage for AI-powered biomechanical analysis.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Upload Form */}
        <div className="glass-panel p-8 rounded-2xl">
          <form onSubmit={handleUpload} className="space-y-6">

            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-300">Supported Activity</label>
              <select
                value={activity}
                onChange={(e) => setActivity(e.target.value)}
                className="w-full px-4 py-3 bg-slate-900/50 border border-slate-700 rounded-xl focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-slate-100 outline-none transition-all appearance-none"
              >
                {ACTIVITIES.map((act) => (
                  <option key={act} value={act}>{act}</option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-300">Surface Type</label>
                <select
                  value={surfaceType}
                  onChange={(e) => setSurfaceType(e.target.value)}
                  className="w-full px-4 py-3 bg-slate-900/50 border border-slate-700 rounded-xl focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-slate-100 outline-none transition-all appearance-none"
                >
                  <option value="Unknown">Unknown</option>
                  <option value="Grass">Grass</option>
                  <option value="Artificial Turf">Artificial Turf</option>
                  <option value="Hardwood">Hardwood</option>
                  <option value="Track">Track</option>
                </select>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-300">Footwear</label>
                <select
                  value={footwear}
                  onChange={(e) => setFootwear(e.target.value)}
                  className="w-full px-4 py-3 bg-slate-900/50 border border-slate-700 rounded-xl focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-slate-100 outline-none transition-all appearance-none"
                >
                  <option value="Unknown">Unknown</option>
                  <option value="Cleats">Cleats</option>
                  <option value="Running Shoes">Running Shoes</option>
                  <option value="Barefoot">Barefoot</option>
                  <option value="Court Shoes">Court Shoes</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-300">RPE (1-10)</label>
                <input
                  type="number"
                  min="1" max="10"
                  value={rpe}
                  onChange={(e) => setRpe(parseInt(e.target.value))}
                  className="w-full px-4 py-3 bg-slate-900/50 border border-slate-700 rounded-xl focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-slate-100 outline-none transition-all"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-300">Sleep Quality (1-10)</label>
                <input
                  type="number"
                  min="1" max="10"
                  value={sleepQuality}
                  onChange={(e) => setSleepQuality(parseInt(e.target.value))}
                  className="w-full px-4 py-3 bg-slate-900/50 border border-slate-700 rounded-xl focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-slate-100 outline-none transition-all"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-300">Video File</label>
              <div className="border-2 border-dashed border-slate-700 rounded-xl p-8 text-center hover:border-indigo-500 transition-colors bg-slate-900/30">
                <input
                  type="file"
                  accept="video/mp4,video/quicktime"
                  onChange={handleFileChange}
                  className="hidden"
                  id="video-upload"
                />
                <label htmlFor="video-upload" className="cursor-pointer flex flex-col items-center">
                  <svg className="w-10 h-10 text-indigo-400 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                  <span className="text-white font-medium mb-1">
                    {file ? file.name : "Click to browse or drag and drop"}
                  </span>
                  <span className="text-xs text-slate-500">MP4 or MOV (Max 50MB)</span>
                </label>
              </div>
            </div>

            {error && (
              <div className="p-4 rounded-xl bg-rose-500/20 border border-rose-500/50 text-rose-400 text-sm font-medium">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={uploading || !file}
              className="w-full py-4 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl transition-all shadow-[0_0_20px_rgba(79,70,229,0.3)] disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {uploading ? (
                <>
                  <svg className="animate-spin h-5 w-5 text-white" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Processing Engine Running...
                </>
              ) : "Process Video"}
            </button>
          </form>
        </div>

        {/* Results Panel */}
        <div className="glass-panel p-8 rounded-2xl flex flex-col">
          <h3 className="text-lg font-bold text-white mb-6 border-b border-slate-800 pb-4">Analysis Results</h3>

          {result ? (
            <div className="space-y-6 flex-1">
              <div className="aspect-video bg-slate-950 rounded-xl overflow-hidden border border-slate-700 relative">
                <video
                  controls
                  className="w-full h-full object-contain"
                  src={`http://127.0.0.1:8000${result.processed_url}`}
                />
                <div className="absolute top-3 left-3 px-2 py-1 bg-black/60 backdrop-blur-md rounded border border-white/10 text-xs text-white flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-green-500"></span>
                  Motion Enhanced
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-900/50 p-4 rounded-xl border border-slate-800">
                  <div className="text-xs text-slate-500 uppercase font-semibold mb-1">Activity Analyzed</div>
                  <div className="text-lg font-medium text-white">{result.analytics.activity_analyzed}</div>
                </div>
                <div className="bg-slate-900/50 p-4 rounded-xl border border-slate-800">
                  <div className="text-xs text-slate-500 uppercase font-semibold mb-1">Risk Score</div>
                  <div className={`text-xl font-bold ${result.analytics.risk_score > 30 ? 'text-rose-400' : 'text-emerald-400'}`}>
                    {result.analytics.risk_score} <span className="text-sm font-normal text-slate-500">/ 100</span>
                  </div>
                  <div className="text-xs mt-1 text-slate-400">Risk Level: <span className="text-white font-medium">{result.analytics.risk_level}</span></div>
                </div>
              </div>

              <div className="bg-slate-900/50 p-4 rounded-xl border border-slate-800 space-y-3">
                <div className="text-xs text-slate-500 uppercase font-semibold">Biomechanical Findings</div>
                {result.analytics.risk_flags.map((flag: string, idx: number) => (
                  <div key={idx} className="flex items-start gap-3">
                    <svg className="w-5 h-5 text-amber-500 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <span className="text-slate-200 text-sm">{flag}</span>
                  </div>
                ))}
              </div>

              <div className="text-xs text-slate-500 text-center pt-2">
                Processed {result.analytics.frame_count} frames at {Math.round(result.analytics.fps)} FPS
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-slate-500 text-center">
              <svg className="w-16 h-16 mb-4 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
              <p>Upload a video to see frame extraction, <br />motion enhancement, and risk detection results.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
