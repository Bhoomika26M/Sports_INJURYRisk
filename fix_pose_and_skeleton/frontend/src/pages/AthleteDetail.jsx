import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { Error, fmtDate, RiskBadge, Section, Stat, Table, TrendChart } from "../components/ui.jsx";

const ACTIVITIES = ["running", "sprinting", "jumping", "squatting", "landing", "throwing", "cutting", "drill"];

export default function AthleteDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const [athlete, setAthlete] = useState(null);
  const [analyses, setAnalyses] = useState([]);
  const [videos, setVideos] = useState([]);
  const [injuries, setInjuries] = useState([]);
  const [load, setLoad] = useState([]);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [upload, setUpload] = useState({ activity: "squatting", file: null });
  const [injury, setInjury] = useState({ injury_type: "", body_part: "", injury_date: "", severity: "moderate", status: "recovered" });
  const [tl, setTl] = useState({ entry_date: new Date().toISOString().slice(0, 10), duration_min: 60, rpe: 6 });

  const refresh = () => {
    api.get(`/athletes/${id}`).then(setAthlete).catch((e) => setError(e.message));
    api.get(`/analyses?athlete_id=${id}`).then((a) => setAnalyses([...a])).catch(() => {});
    api.get(`/videos?athlete_id=${id}`).then(setVideos).catch(() => {});
    api.get(`/athletes/${id}/injuries`).then(setInjuries).catch(() => {});
    api.get(`/athletes/${id}/training-load`).then(setLoad).catch(() => {});
  };
  useEffect(refresh, [id]);
  // poll while a video is being analysed
  useEffect(() => {
    if (!videos.some((v) => ["uploaded", "processing"].includes(v.status))) return;
    const t = setTimeout(refresh, 4000);
    return () => clearTimeout(t);
  }, [videos]);

  const act = (fn, msg) => async (e) => {
    e.preventDefault();
    setError(""); setInfo("");
    try { await fn(); if (msg) setInfo(msg); refresh(); } catch (err) { setError(err.message); }
  };

  if (!athlete) return <Error message={error} />;
  const trend = [...analyses].reverse();
  const canUpload = user.role !== "sports_scientist";
  return (
    <>
      <div>
        <h1 className="text-2xl font-semibold">{athlete.full_name} <span className="text-base font-normal text-slate-500">{athlete.athlete_code}</span></h1>
        <p className="text-sm text-slate-600">{athlete.sport_type}{athlete.position ? ` · ${athlete.position}` : ""} · {athlete.age} y · {athlete.height_cm} cm · {athlete.weight_kg} kg</p>
      </div>
      <Error message={error} />
      {info && <div className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-700">{info}</div>}
      <div className="grid gap-4 sm:grid-cols-3">
        <Stat label="Latest risk" value={analyses[0]?.risk_score} hint={<RiskBadge level={analyses[0]?.risk_category} />} />
        <Stat label="Analyses" value={analyses.length} />
        <Stat label="Active injuries" value={injuries.filter((i) => i.status !== "recovered").length} />
      </div>

      {trend.length > 1 && (
        <Section title="Trend"><TrendChart labels={trend.map((a) => fmtDate(a.created_at))} series={[{ label: "Injury risk", data: trend.map((a) => a.risk_score) }, { label: "Movement quality", data: trend.map((a) => a.movement_quality) }]} /></Section>
      )}

      {canUpload && (
        <Section title="Upload movement video">
          <form className="flex flex-wrap items-end gap-3" onSubmit={act(async () => {
            if (!upload.file) throw new window.Error("Choose a video file");
            const fd = new FormData();
            fd.append("athlete_id", id); fd.append("activity", upload.activity); fd.append("file", upload.file);
            await api.upload("/videos/upload", fd);
          }, "Video uploaded — analysis is running.")}>
            <div><label className="label">Activity</label><select className="input" value={upload.activity} onChange={(e) => setUpload({ ...upload, activity: e.target.value })}>{ACTIVITIES.map((a) => <option key={a}>{a}</option>)}</select></div>
            <div><label className="label">Video (mp4 / mov / avi)</label><input className="input" type="file" accept="video/*" onChange={(e) => setUpload({ ...upload, file: e.target.files[0] })} /></div>
            <button className="btn">Upload &amp; analyse</button>
          </form>
          <p className="mt-2 text-xs text-slate-500">Tip: film the full body from the front or side, steady camera, good lighting, ≥ 15 fps.</p>
        </Section>
      )}

      <Section title="Videos & analyses">
        <Table columns={[
          { header: "Uploaded", render: (v) => fmtDate(v.created_at) }, { header: "Activity", key: "activity" }, { header: "File", key: "original_filename" },
          { header: "Status", render: (v) => (v.status === "failed" ? <span className="font-medium text-red-600">Failed: {v.error || "unknown error"}</span> : v.status === "processing" || v.status === "uploaded" ? <span className="text-blue-600">Analysing…</span> : v.status) },
          { header: "Result", render: (v) => { const a = analyses.find((x) => x.video_id === v.id); return a ? <Link className="text-blue-600" to={`/analyses/${a.id}`}>{a.risk_category} ({a.risk_score})</Link> : "—"; } },
        ]} rows={videos} />
      </Section>

      <div className="grid gap-6 lg:grid-cols-2">
        <Section title="Injury history">
          <Table columns={[{ header: "Date", key: "injury_date" }, { header: "Injury", key: "injury_type" }, { header: "Body part", key: "body_part" }, { header: "Status", key: "status" }]} rows={injuries} />
          <form className="mt-4 grid grid-cols-2 gap-2" onSubmit={act(() => api.post(`/athletes/${id}/injuries`, injury), "Injury added.")}>
            <input className="input" placeholder="Injury type" required value={injury.injury_type} onChange={(e) => setInjury({ ...injury, injury_type: e.target.value })} />
            <input className="input" placeholder="Body part (e.g. knee)" required value={injury.body_part} onChange={(e) => setInjury({ ...injury, body_part: e.target.value })} />
            <input className="input" type="date" required value={injury.injury_date} onChange={(e) => setInjury({ ...injury, injury_date: e.target.value })} />
            <select className="input" value={injury.status} onChange={(e) => setInjury({ ...injury, status: e.target.value })}><option>recovered</option><option>recovering</option><option>active</option></select>
            <button className="btn col-span-2">Add injury</button>
          </form>
        </Section>
        <Section title="Training load">
          <Table columns={[{ header: "Date", key: "entry_date" }, { header: "Minutes", key: "duration_min" }, { header: "RPE", key: "rpe" }, { header: "Load (AU)", key: "load_au" }]} rows={load.slice(0, 8)} />
          <form className="mt-4 grid grid-cols-3 gap-2" onSubmit={act(() => api.post(`/athletes/${id}/training-load`, { ...tl, duration_min: +tl.duration_min, rpe: +tl.rpe }), "Session logged.")}>
            <input className="input" type="date" required value={tl.entry_date} onChange={(e) => setTl({ ...tl, entry_date: e.target.value })} />
            <input className="input" type="number" min="1" placeholder="Minutes" value={tl.duration_min} onChange={(e) => setTl({ ...tl, duration_min: e.target.value })} />
            <input className="input" type="number" min="1" max="10" step="0.5" placeholder="RPE" value={tl.rpe} onChange={(e) => setTl({ ...tl, rpe: e.target.value })} />
            <button className="btn col-span-3">Log session</button>
          </form>
        </Section>
      </div>
    </>
  );
}
