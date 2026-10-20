import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import { api } from "../api.js";
import { BarChart, Error, fmtDate, RiskBadge, Section, Stat, Table, TrendChart } from "../components/ui.jsx";

const ENDPOINT = {
  athlete: "/dashboards/athlete", coach: "/dashboards/coach", physiotherapist: "/dashboards/physiotherapist",
  sports_scientist: "/dashboards/scientist", administrator: "/dashboards/admin",
};

const teamColumns = [
  { header: "Athlete", render: (r) => <Link className="text-blue-600" to={`/athletes/${r.athlete_id}`}>{r.name}</Link> },
  { header: "Sport", key: "sport" },
  { header: "Risk", render: (r) => <RiskBadge level={r.risk_category} /> },
  { header: "Score", key: "risk_score" },
  { header: "Movement quality", key: "movement_quality" },
  { header: "Last analysis", render: (r) => fmtDate(r.last_analysis) },
];

function AthleteView({ d }) {
  if (!d.latest) return <Section title="Welcome"><p className="text-sm text-slate-600">No analysis yet. Open <Link className="text-blue-600" to="/athletes">Athletes</Link>, select your profile and upload a movement video.</p></Section>;
  const rec = d.recommendations || {};
  return (
    <>
      <div className="grid gap-4 sm:grid-cols-4">
        <Stat label="Injury risk score" value={d.latest.risk_score} hint={<RiskBadge level={d.latest.risk_category} />} />
        <Stat label="Movement quality" value={d.latest.movement_quality} />
        <Stat label="Overall health" value={d.latest.scores?.overall_health} />
        <Stat label="Change vs previous" value={d.progress ? `${d.progress.risk_change > 0 ? "+" : ""}${d.progress.risk_change}` : "—"} hint="risk score" />
      </div>
      <Section title="Risk & performance trends">
        <TrendChart labels={d.risk_trend.map((p) => p.date)} series={[
          { label: "Injury risk", data: d.risk_trend.map((p) => p.risk_score) },
          { label: "Movement quality", data: d.performance_trend.map((p) => p.movement_quality) },
        ]} />
      </Section>
      <Section title="Top injury risks">
        <Table columns={[{ header: "Category", render: (r) => r.category.replace(/_/g, " ") }, { header: "Level", render: (r) => <RiskBadge level={r.level} /> }, { header: "Score", key: "score" }]} rows={d.latest.top_risks} />
      </Section>
      <Section title="Exercise recommendations" action={<Link className="text-sm text-blue-600" to={`/analyses/${d.latest.analysis_id}`}>Full report →</Link>}>
        <ul className="list-disc space-y-1 pl-5 text-sm">{(rec.corrective_exercises || []).slice(0, 4).map((c) => <li key={c.issue}><b>{c.title}</b>: {c.exercises.map((e) => e.name).join(", ")}</li>)}</ul>
      </Section>
      <Section title="Recent movement analysis reports">
        <Table columns={[{ header: "Date", render: (r) => fmtDate(r.created_at) }, { header: "Activity", key: "activity" }, { header: "Risk", render: (r) => <RiskBadge level={r.risk_category} /> }, { header: "", render: (r) => <Link className="text-blue-600" to={`/analyses/${r.analysis_id}`}>Open</Link> }]} rows={d.recent_reports} />
      </Section>
    </>
  );
}

function CoachView({ d }) {
  const o = d.team_overview, dist = o.risk_distribution;
  return (
    <>
      <div className="grid gap-4 sm:grid-cols-4">
        <Stat label="Athletes" value={o.athletes} hint={`${o.assessed} assessed`} />
        <Stat label="Avg movement quality" value={o.average_movement_quality} />
        <Stat label="High risk" value={dist.high} />
        <Stat label="Critical" value={dist.critical} />
      </div>
      <Section title="Team risk overview"><BarChart labels={Object.keys(dist)} data={Object.values(dist)} label="Athletes" /></Section>
      <Section title="Athletes (highest risk first)"><Table columns={teamColumns} rows={d.athletes} /></Section>
      <Section title="Training recommendations"><Table columns={[{ header: "Athlete", key: "athlete" }, { header: "Risk", render: (r) => <RiskBadge level={r.risk_category} /> }, { header: "Recommendation", key: "recommendation" }]} rows={d.training_recommendations} /></Section>
    </>
  );
}

function PhysioView({ d }) {
  return (
    <>
      <Section title="Injury risk monitoring"><Table columns={teamColumns} rows={d.injury_risk_monitoring} /></Section>
      <Section title="Rehabilitation tracking"><Table columns={[{ header: "Athlete", key: "athlete" }, { header: "Injury", key: "injury" }, { header: "Body part", key: "body_part" }, { header: "Status", key: "status" }, { header: "Days since", key: "days_since_injury" }]} rows={d.rehabilitation_tracking} /></Section>
      <Section title="Movement correction analytics"><BarChart horizontal labels={d.movement_correction_analytics.map((x) => x.issue.replace(/_/g, " "))} data={d.movement_correction_analytics.map((x) => x.athletes_affected)} label="Athletes affected" color="#d97706" /></Section>
      <Section title="Recovery reports"><Table columns={[{ header: "Athlete", key: "athlete" }, { header: "Risk", render: (r) => <RiskBadge level={r.risk_category} /> }, { header: "Referral", render: (r) => (r.referral_suggested ? "Suggested" : "—") }, { header: "Plan", render: (r) => r.recovery_plan[0] }]} rows={d.recovery_reports} /></Section>
    </>
  );
}

function ScientistView({ d }) {
  const ins = d.injury_prediction_insights;
  return (
    <>
      <div className="grid gap-4 sm:grid-cols-2"><Stat label="Athletes" value={d.dataset.athletes} /><Stat label="Analyses" value={d.dataset.analyses} /></div>
      <Section title="Team performance trends (weekly mean risk)"><TrendChart labels={d.team_performance_trends.map((w) => w.week)} series={[{ label: "Mean risk score", data: d.team_performance_trends.map((w) => w.mean_risk_score) }]} /></Section>
      <Section title="Injury prediction insights">
        <BarChart labels={Object.keys(ins.mean_score_by_category).map((k) => k.replace(/_/g, " "))} data={Object.values(ins.mean_score_by_category)} label="Mean risk score" />
        <h3 className="mt-4 text-sm font-semibold">Most common risk drivers</h3>
        <Table columns={[{ header: "Driver", key: "driver" }, { header: "Occurrences", key: "count" }]} rows={ins.most_common_drivers} />
      </Section>
      <Section title="Biomechanical analytics by activity">
        <Table columns={[{ header: "Activity", key: "activity" }, { header: "Analyses", key: "analyses" }, { header: "Knee valgus (°)", key: "knee_valgus_peak_deg" }, { header: "Trunk lean (°)", key: "trunk_lean_max_deg" }, { header: "Pelvic drop (°)", key: "hip_stability_pelvic_drop_deg" }, { header: "Alignment", key: "joint_alignment_score" }]} rows={Object.entries(d.biomechanical_analytics).map(([activity, v]) => ({ activity, ...v }))} />
      </Section>
    </>
  );
}

function AdminView({ d }) {
  return (
    <>
      <div className="grid gap-4 sm:grid-cols-4">
        <Stat label="Users" value={d.users.total} /><Stat label="Athletes" value={d.platform.athletes} />
        <Stat label="Videos" value={d.platform.videos} /><Stat label="Analyses" value={d.platform.analyses} />
      </div>
      <Section title="System">
        <p className="text-sm">Database: <b>{d.system.database_ok ? "OK" : "Unreachable"}</b> · Uploads {d.system.uploads_mb} MB · Reports {d.system.reports_mb} MB</p>
        <h3 className="mt-3 text-sm font-semibold">Recent failed videos</h3>
        <Table columns={[{ header: "Video", key: "video_id" }, { header: "Athlete", key: "athlete_id" }, { header: "Error", key: "error" }]} rows={d.system.recent_failed_videos} empty="No failures." />
      </Section>
      <Section title="Users by role"><BarChart labels={Object.keys(d.users.by_role)} data={Object.values(d.users.by_role)} label="Users" /></Section>
      <p className="text-sm"><Link className="text-blue-600" to="/admin">Manage users →</Link></p>
    </>
  );
}

export default function Dashboard() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { api.get(ENDPOINT[user.role]).then(setData).catch((e) => setError(e.message)); }, [user.role]);

  const View = { athlete: AthleteView, coach: CoachView, physiotherapist: PhysioView, sports_scientist: ScientistView, administrator: AdminView }[user.role];
  return (
    <>
      <h1 className="text-2xl font-semibold capitalize">{user.role.replace("_", " ")} dashboard</h1>
      {user.role === "athlete" && error.includes("athlete profile") ? (
        <Section title="Set up your profile"><p className="text-sm">Create your athlete profile on the <Link className="text-blue-600" to="/athletes">Athletes</Link> page to get started.</p></Section>
      ) : (
        <>
          <Error message={error} />
          {data && <View d={data} />}
        </>
      )}
    </>
  );
}
