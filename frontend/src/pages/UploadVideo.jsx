import React, { useState } from 'react';
import { UploadCloud, FileVideo, Info, CheckCircle2, AlertCircle } from 'lucide-react';

export default function UploadVideo() {
  const [movementType, setMovementType] = useState('jump_landing');
  const [cameraView, setCameraView] = useState('frontal');
  const [selectedFile, setSelectedFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setUploadSuccess(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!selectedFile) return;

    setIsUploading(true);
    // Simulated upload lifecycle
    setTimeout(() => {
      setIsUploading(false);
      setUploadSuccess(true);
    }, 1200);
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Upload Movement Video</h1>
        <p className="text-slate-400 text-sm mt-1">
          Submit high-framerate athletic trial footage for markerless pose estimation and injury risk scoring.
        </p>
      </div>

      <div className="glass-card rounded-2xl p-6 sm:p-8 space-y-6">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Movement Type Selector */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              1. Movement Protocol
            </label>
            <div className="grid grid-cols-3 gap-3">
              {[
                { id: 'squat', label: 'Squat', desc: 'Mobility & depth' },
                { id: 'jump_landing', label: 'Jump Landing', desc: 'ACL & impact valgus' },
                { id: 'running', label: 'Running Gait', desc: 'Hamstring & cadence' },
              ].map((m) => (
                <button
                  type="button"
                  key={m.id}
                  onClick={() => setMovementType(m.id)}
                  className={`p-3.5 rounded-xl text-left border transition-all ${
                    movementType === m.id
                      ? 'bg-emerald-500/10 border-emerald-500/50 text-white'
                      : 'bg-slate-900/50 border-slate-800 text-slate-400 hover:border-slate-700'
                  }`}
                >
                  <p className="font-semibold text-sm leading-snug">{m.label}</p>
                  <p className="text-xs text-slate-500 mt-0.5">{m.desc}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Camera View Angle */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              2. Camera Angle / Perspective
            </label>
            <div className="grid grid-cols-3 gap-3">
              {[
                { id: 'frontal', label: 'Frontal (Coronal)', desc: 'Knee valgus & tilt' },
                { id: 'sagittal', label: 'Sagittal (Lateral)', desc: 'Flexion & pelvic tilt' },
                { id: 'oblique', label: 'Oblique (45°)', desc: 'General observation' },
              ].map((c) => (
                <button
                  type="button"
                  key={c.id}
                  onClick={() => setCameraView(c.id)}
                  className={`p-3 rounded-xl text-left border transition-all ${
                    cameraView === c.id
                      ? 'bg-emerald-500/10 border-emerald-500/50 text-white'
                      : 'bg-slate-900/50 border-slate-800 text-slate-400 hover:border-slate-700'
                  }`}
                >
                  <p className="font-medium text-sm">{c.label}</p>
                  <p className="text-xs text-slate-500 mt-0.5">{c.desc}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Dropzone File Input */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              3. Video File (MP4, MOV, AVI)
            </label>
            <div className="border-2 border-dashed border-slate-700 hover:border-emerald-500/50 rounded-2xl p-8 text-center transition-colors bg-slate-900/40 relative">
              <input
                type="file"
                accept="video/mp4,video/quicktime,video/x-msvideo"
                onChange={handleFileChange}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              />
              <div className="flex flex-col items-center justify-center space-y-3 pointer-events-none">
                <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center text-emerald-400">
                  <UploadCloud className="w-6 h-6" />
                </div>
                {selectedFile ? (
                  <div>
                    <p className="text-sm font-semibold text-white flex items-center gap-1.5">
                      <FileVideo className="w-4 h-4 text-emerald-400" /> {selectedFile.name}
                    </p>
                    <p className="text-xs text-slate-500 mt-1">
                      {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • Ready to dispatch
                    </p>
                  </div>
                ) : (
                  <div>
                    <p className="text-sm font-medium text-slate-300">
                      Drag & drop your recording here, or <span className="text-emerald-400 underline">browse</span>
                    </p>
                    <p className="text-xs text-slate-500 mt-1">
                      Recommended: 60 FPS or 120 FPS high-speed video up to 200MB
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Guidelines Banner */}
          <div className="flex items-start gap-3 bg-slate-900/80 border border-slate-800 p-4 rounded-xl text-xs text-slate-400">
            <Info className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-slate-300">Capture Best Practice:</span> Ensure the athlete’s whole body is framed with at least 15% clearance above head and below feet. Avoid dark backgrounds with dark clothing to maximize landmark contrast.
            </div>
          </div>

          {/* Success Banner */}
          {uploadSuccess && (
            <div className="flex items-center gap-3 bg-emerald-500/10 border border-emerald-500/30 p-4 rounded-xl text-xs text-emerald-400">
              <CheckCircle2 className="w-5 h-5 shrink-0" />
              <div>
                <p className="font-semibold text-sm">Upload Registered Successfully!</p>
                <p className="text-emerald-500/80 mt-0.5">
                  The video was registered for asynchronous pose estimation & biomechanical processing.
                </p>
              </div>
            </div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={!selectedFile || isUploading}
            className={`w-full py-3 px-4 rounded-xl font-semibold text-sm flex items-center justify-center transition-all ${
              !selectedFile || isUploading
                ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
                : 'bg-emerald-500 hover:bg-emerald-400 text-slate-950 shadow-lg shadow-emerald-500/20'
            }`}
          >
            {isUploading ? 'Dispatching to ML Pipeline...' : 'Upload & Start Biomechanical Analysis'}
          </button>
        </form>
      </div>
    </div>
  );
}
