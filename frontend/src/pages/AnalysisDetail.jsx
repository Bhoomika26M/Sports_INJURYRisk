import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import { BarChart, Error, fmtDate, RiskBadge, Section, Stat, Table } from "../components/ui.jsx";
import SkeletonPlayer from "../components/SkeletonPlayer.jsx";

const REPORT_TYPES = [["injury_risk", "Injury risk"], ["biomechanical", "Biomechanical"], ["movement", "Movement analysis"], ["performance", "Performance"], ["rehabilitation", "Rehabilitation"]];

export default function AnalysisDetail() {
  const { id } = useParams();
  const [a, setA] = useState(null);
  const [error, setError] = useState("");
  const [report, setReport] = useState({ report_type: "injury_risk", file_format: "pdf" });
  const [busy, setBusy] = useState(false);

  useEffect(() => { api.get(`/analyses/${id}`).then(setA).catch((e) => setError(e.message)); }, [id]);

  const generate = async () => {
    setBusy(true); setError("");
    try {
      const r = await api.post(`/reports/generate?analysis_id=${id}&report_type=${report.report_type}&file_format=${report.file_format}`);
      await api.download(`/reports/${r.id}/download`, `${report.report_type}_report.${report.file_format}`);
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };

  if (!a) return <Error message={error} />;
  const rec = a.recommendations || {};
  const comps = a.scores?.risk?.components || a.scores?.components || {};
  return (
    <>
      <div>
        <Link className="text-sm text-blue-600" to={`/athletes/${a.athlete_id}`}>← Athlete</Link>
        <h1 className="text-2xl font-semibold capitalize">{a.activity} analysis <RiskBadge level={a.risk_category} /></h1>
        <p className="text-sm text-slate-500">{fmtDate(a.created_at)}</p>
      </div>
      <Error message={error} />
      <div className="grid gap-4 sm:grid-cols-4">
        <Stat label="Injury risk" value={a.risk_score} />
        <Stat label="Movement quality" value={a.movement_quality} />
        <Stat label="Biomech. efficiency" value={a.scores?.biomechanical_efficiency} />
        <Stat label="Fatigue risk" value={a.scores?.fatigue_risk} />
      </div>

      <Section title="Movement tracking"><SkeletonPlayer videoId={a.video_id} /></Section>

      <Section title="Injury risk by category">
        <BarChart horizontal labels={a.injury_risks.map((r) => r.category.replace(/_/g, " "))} data={a.injury_risks.map((r) => r.score)} label="Risk score" />
        <Table columns={[{ header: "Category", render: (r) => r.category.replace(/_/g, " ") }, { header: "Level", render: (r) => <RiskBadge level={r.level} /> }, { header: "Score", key: "score" }, { header: "Main drivers", render: (r) => r.drivers.map((d) => d.driver).join(", ") }]} rows={a.injury_risks} />
      </Section>

      {Object.keys(comps).length > 0 && (
        <Section title="Weighted risk components"><BarChart labels={Object.keys(comps).map((k) => k.replace(/_/g, " "))} data={Object.values(comps)} label="Component score" color="#059669" /></Section>
      )}

      <Section title="Biomechanical deviations">
        <Table columns={[{ header: "Finding", key: "label" }, { header: "Issue", key: "issue" }, { header: "Level", render: (d) => <RiskBadge level={d.level === "normal" ? "low" : d.level} /> }]} rows={a.deviations} />
      </Section>

      <Section title="Movement anomalies">
        <pre className="max-h-64 overflow-auto rounded bg-slate-50 p-3 text-xs">{JSON.stringify(a.anomalies, null, 2)}</pre>
      </Section>

      <Section title="Corrective recommendations">
        {(rec.corrective_exercises || []).map((c) => (
          <div key={c.issue} className="mb-3">
            <h3 className="text-sm font-semibold">{c.title} <span className="font-normal text-slate-500">({c.category}, {c.priority} priority)</span></h3>
            <p className="text-xs text-slate-500">{c.evidence}</p>
            <ul className="list-disc pl-5 text-sm">{c.exercises.map((e) => <li key={e.name}><b>{e.name}</b> — {e.prescription}. <span className="text-slate-500">{e.purpose}</span></li>)}</ul>
          </div>
        ))}
        <h3 className="mt-2 text-sm font-semibold">Training modifications</h3>
        <ul className="list-disc pl-5 text-sm">{(rec.training_modifications || []).map((t) => <li key={t}>{t}</li>)}</ul>
        <h3 className="mt-2 text-sm font-semibold">Recovery plan</h3>
        <ul className="list-disc pl-5 text-sm">{(rec.recovery_plan || []).map((t) => <li key={t}>{t}</li>)}</ul>
        {rec.clinical_referral_suggested && <p className="mt-2 rounded bg-orange-50 p-2 text-sm text-orange-800">A clinical assessment by a physiotherapist or doctor is suggested.</p>}
        <p className="mt-3 text-xs text-slate-500">{rec.disclaimer}</p>
      </Section>

      <Section title="Export report">
        <div className="flex flex-wrap items-end gap-3">
          <select className="input w-auto" value={report.report_type} onChange={(e) => setReport({ ...report, report_type: e.target.value })}>{REPORT_TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
          <select className="input w-auto" value={report.file_format} onChange={(e) => setReport({ ...report, file_format: e.target.value })}><option value="pdf">PDF</option><option value="xlsx">Excel</option></select>
          <button className="btn" disabled={busy} onClick={generate}>{busy ? "Generating…" : "Generate & download"}</button>
        </div>
      </Section>
    </>
  );
}
