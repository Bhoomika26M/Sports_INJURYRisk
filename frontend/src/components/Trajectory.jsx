import { useEffect, useMemo, useState } from "react";
import { api } from "../api.js";

const label = (n) => n.replace(/_/g, " ");

// Shows where one joint travelled during the clip: its path in the frame, and its height over time.
export default function Trajectory({ videoId }) {
  const [pose, setPose] = useState(null);
  const [joint, setJoint] = useState("right_knee");
  const [error, setError] = useState("");

  useEffect(() => { api.get(`/videos/${videoId}/pose`).then(setPose).catch((e) => setError(e.message)); }, [videoId]);

  const pts = useMemo(() => {
    if (!pose) return [];
    const j = pose.joint_names.indexOf(joint);
    return pose.frames.map((f, t) => ({ t, x: f[j]?.[0], y: f[j]?.[1] })).filter((p) => p.x != null && p.y != null);
  }, [pose, joint]);

  if (error) return <p className="text-sm text-slate-500">Trajectory is not available: {error}</p>;
  if (!pose) return <p className="text-sm text-slate-500">Loading…</p>;
  if (pts.length < 2) return <p className="text-sm text-slate-500">This joint was not tracked long enough to draw a path.</p>;

  const xs = pts.map((p) => p.x), ys = pts.map((p) => p.y);
  const [minX, maxX, minY, maxY] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  const pad = 0.04;
  const w = Math.max(maxX - minX, 0.05) + pad * 2, h = Math.max(maxY - minY, 0.05) + pad * 2;
  const vx = minX - pad, vy = minY - pad;
  const n = pts.length - 1;
  const seconds = (pts[pts.length - 1].t - pts[0].t) / pose.fps;

  // height over time: up is positive, so flip y
  const T = pts.map((p, i) => `${(i / n) * 300},${(1 - (maxY - p.y) / Math.max(maxY - minY, 1e-6)) * 90 + 5}`).join(" ");
  const sw = Math.max(w, h) / 90;

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <label className="label !mb-0">Joint</label>
        <select className="input w-auto" value={joint} onChange={(e) => setJoint(e.target.value)}>
          {pose.joint_names.map((n) => <option key={n} value={n}>{label(n)}</option>)}
        </select>
        <span className="text-sm text-slate-500">
          Up and down: {((maxY - minY) * 100).toFixed(0)}% of frame height · Side to side: {((maxX - minX) * 100).toFixed(0)}% of frame width · {seconds.toFixed(1)} s tracked
        </span>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Path in the frame</div>
          <svg viewBox={`${vx} ${vy} ${w} ${h}`} className="w-full rounded-xl bg-slate-50 ring-1 ring-slate-200" style={{ aspectRatio: `${w} / ${h}`, maxHeight: 320 }} role="img" aria-label={`Path of the ${label(joint)}`}>
            {pts.slice(1).map((p, i) => (
              <line key={i} x1={pts[i].x} y1={pts[i].y} x2={p.x} y2={p.y} stroke={`hsl(${210 - (i / n) * 40} 85% ${70 - (i / n) * 30}%)`} strokeWidth={sw} strokeLinecap="round" />
            ))}
            <circle cx={pts[0].x} cy={pts[0].y} r={sw * 2.2} fill="#10b981" stroke="white" strokeWidth={sw * 0.6} />
            <circle cx={pts[n].x} cy={pts[n].y} r={sw * 2.2} fill="#ef4444" stroke="white" strokeWidth={sw * 0.6} />
          </svg>
          <p className="mt-1 text-xs text-slate-500"><span className="text-emerald-600">●</span> start · <span className="text-red-500">●</span> end · colour darkens with time</p>
        </div>
        <div>
          <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Height over time</div>
          <svg viewBox="0 0 300 100" preserveAspectRatio="none" className="h-40 w-full rounded-xl bg-slate-50 ring-1 ring-slate-200 md:h-full md:max-h-80" role="img" aria-label={`Height of the ${label(joint)} over time`}>
            <polyline points={T} fill="none" stroke="#2563eb" strokeWidth="1.6" vectorEffect="non-scaling-stroke" strokeLinejoin="round" />
          </svg>
          <p className="mt-1 text-xs text-slate-500">Each peak and dip is one repetition. Even peaks mean steady technique.</p>
        </div>
      </div>
    </div>
  );
}
