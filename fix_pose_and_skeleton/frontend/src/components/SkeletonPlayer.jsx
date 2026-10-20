import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";

// Plays the uploaded video with the detected skeleton drawn on top.
// If the browser cannot play the video's codec, the skeleton still animates on its own.
export default function SkeletonPlayer({ videoId }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [pose, setPose] = useState(null);
  const [src, setSrc] = useState(null);
  const [playable, setPlayable] = useState(true);
  const [error, setError] = useState("");
  const fallbackStart = useRef(null);

  useEffect(() => {
    let url;
    api.get(`/videos/${videoId}/pose`).then(setPose).catch((e) => setError(e.message));
    api.blobUrl(`/videos/${videoId}/file`).then((u) => { url = u; setSrc(u); }).catch(() => setPlayable(false));
    return () => url && URL.revokeObjectURL(url);
  }, [videoId]);

  useEffect(() => {
    if (!pose) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    const names = pose.joint_names;
    const idx = Object.fromEntries(names.map((n, i) => [n, i]));
    const totalFrames = pose.frames.length;
    let raf;

    const draw = () => {
      const video = videoRef.current;
      const w = canvas.clientWidth, h = canvas.clientHeight;
      if (canvas.width !== w) canvas.width = w;
      if (canvas.height !== h) canvas.height = h;
      ctx.clearRect(0, 0, w, h);

      let t;
      if (playable && video && video.readyState >= 2) t = video.currentTime;
      else {
        if (fallbackStart.current === null) fallbackStart.current = performance.now();
        t = ((performance.now() - fallbackStart.current) / 1000) % (totalFrames / pose.fps);
      }
      const f = pose.frames[Math.min(totalFrames - 1, Math.max(0, Math.round(t * pose.fps)))];
      if (f) {
        ctx.lineWidth = 3;
        ctx.strokeStyle = "#22d3ee";
        for (const [a, b] of pose.edges) {
          const pa = f[idx[a]], pb = f[idx[b]];
          if (pa[0] == null || pb[0] == null) continue;
          ctx.beginPath(); ctx.moveTo(pa[0] * w, pa[1] * h); ctx.lineTo(pb[0] * w, pb[1] * h); ctx.stroke();
        }
        for (const p of f) {
          if (p[0] == null) continue;
          ctx.beginPath(); ctx.arc(p[0] * w, p[1] * h, 5, 0, Math.PI * 2);
          ctx.fillStyle = "#ffffff"; ctx.fill();
          ctx.lineWidth = 2; ctx.strokeStyle = "#2563eb"; ctx.stroke();
          ctx.strokeStyle = "#22d3ee";
        }
      }
      raf = requestAnimationFrame(draw);
    };
    raf = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(raf);
  }, [pose, playable]);

  if (error) return <p className="text-sm text-slate-500">Movement tracking is not available: {error}</p>;
  return (
    <div>
      <div className="relative mx-auto max-w-2xl overflow-hidden rounded-lg bg-slate-900">
        {playable && src ? (
          <video ref={videoRef} src={src} controls loop muted playsInline className="block w-full"
            onError={() => setPlayable(false)} />
        ) : (
          <div className="aspect-video w-full" />
        )}
        <canvas ref={canvasRef} className="pointer-events-none absolute inset-0 h-full w-full" />
      </div>
      {!playable && (
        <p className="mt-2 text-center text-xs text-slate-500">
          This browser cannot play the video format, so only the tracked skeleton is shown.
        </p>
      )}
      <p className="mt-2 text-center text-xs text-slate-500">White dots are the tracked joints: head, shoulders, elbows, wrists, hips, knees, ankles and feet.</p>
    </div>
  );
}
