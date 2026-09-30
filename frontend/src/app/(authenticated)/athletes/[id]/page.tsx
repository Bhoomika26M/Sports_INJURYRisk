"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api-client";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";

type Athlete = {
  id: string;
  full_name: string | null;
  sport_type: string;
  position: string | null;
  date_of_birth: string;
  height_cm: number | null;
  weight_kg: number | null;
  dominant_side: string | null;
  age: number | null;
  user_id: string | null;
  coach_id: string | null;
};

type Injury = {
  id: string;
  injury_type: string;
  body_part: string;
  injury_date: string;
  recovery_date: string | null;
  severity: string | null;
  notes: string | null;
};

type TrainingLoad = {
  id: string;
  entry_date: string;
  session_type: string | null;
  duration_minutes: number | null;
  rpe: number | null;
  session_load: number | null;
  notes: string | null;
};

export default function AthleteDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [athlete, setAthlete] = useState<Athlete | null>(null);
  const [injuries, setInjuries] = useState<Injury[]>([]);
  const [trainingLoads, setTrainingLoads] = useState<TrainingLoad[]>([]);
  const [acwr, setAcwr] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"profile" | "injuries" | "training" | "videos">("profile");

  const load = async () => {
    try {
      const [a, i, t, ac] = await Promise.all([
        apiClient.fetchWithAuth(`/athletes/${id}`),
        apiClient.fetchWithAuth(`/athletes/${id}/injuries`),
        apiClient.fetchWithAuth(`/athletes/${id}/training-load`),
        apiClient.fetchWithAuth(`/athletes/${id}/acwr`),
      ]);
      setAthlete(a);
      setInjuries(i.items || []);
      setTrainingLoads(t.items || []);
      setAcwr(ac);
    } catch (e: any) {
      setError(e.message || "Failed to load athlete");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [id]);

  const handleDelete = async (type: "injury" | "training", itemId: string) => {
    if (!confirm(`Delete this ${type} record?`)) return;
    try {
      await apiClient.fetchWithAuth(`/athletes/${id}/${type === "injury" ? "injuries" : "training-load"}/${itemId}`, { method: "DELETE" });
      load();
    } catch (e: any) {
      alert(e.message || "Failed to delete");
    }
  };

  if (loading) return <div className="bento-card p-6 flex items-center gap-3" style={{ color: "var(--text-primary)" }}><svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24" style={{ color: "var(--brand-dark)" }}><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg><span className="text-sm font-bold">Loading...</span></div>;
  if (error) return <div className="status-pill status-pill--danger p-4">{error}</div>;
  if (!athlete) return <div className="status-pill status-pill--danger p-4">Athlete not found</div>;

  return (
    <div className="space-y-6">
      <div className="bento-card p-6 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="status-pill status-pill--muted">{athlete.sport_type}</span>
            <span className="text-xs font-bold" style={{ color: "var(--text-muted)" }}>Athlete Profile</span>
          </div>
          <h1 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>{athlete.full_name || "Unnamed Athlete"}</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>Age: {athlete.age ?? "—"} • {athlete.sport_type} • {athlete.position || "No position"}</p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Link href={`/athletes/${id}/edit`} className="pill-btn--outline text-xs">Edit Profile</Link>
          <Link href={`/videos/upload?athlete_id=${id}`} className="pill-btn--primary text-xs">Upload Video</Link>
        </div>
      </div>

      <div className="flex gap-2 border-b" style={{ borderColor: "var(--border-faint)" }}>
        {["profile", "injuries", "training", "videos"].map((tab) => (
          <button key={tab} onClick={() => setActiveTab(tab as any)} className={`px-4 py-3 text-sm font-medium transition-colors ${activeTab === tab ? "border-b-2" : "border-b-2 border-transparent"} ${activeTab === tab ? "text-primary" : "text-muted"}`} style={{ borderColor: activeTab === tab ? "var(--brand-primary)" : "transparent", color: activeTab === tab ? "var(--text-primary)" : "var(--text-muted)" }}>
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {activeTab === "profile" && athlete && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bento-card p-6">
            <h3 className="font-semibold mb-4" style={{ color: "var(--text-primary)" }}>Physical Details</h3>
            <dl className="space-y-3">
              <div className="grid grid-cols-2 gap-2"><dt className="text-xs font-semibold uppercase" style={{ color: "var(--text-muted)" }}>Height</dt><dd style={{ color: "var(--text-primary)" }}>{athlete.height_cm ? `${athlete.height_cm} cm` : "—"}</dd></div>
              <div className="grid grid-cols-2 gap-2"><dt className="text-xs font-semibold uppercase" style={{ color: "var(--text-muted)" }}>Weight</dt><dd style={{ color: "var(--text-primary)" }}>{athlete.weight_kg ? `${athlete.weight_kg} kg` : "—"}</dd></div>
              <div className="grid grid-cols-2 gap-2"><dt className="text-xs font-semibold uppercase" style={{ color: "var(--text-muted)" }}>Dominant Side</dt><dd style={{ color: "var(--text-primary)" }}>{athlete.dominant_side || "—"}</dd></div>
              <div className="grid grid-cols-2 gap-2"><dt className="text-xs font-semibold uppercase" style={{ color: "var(--text-muted)" }}>Date of Birth</dt><dd style={{ color: "var(--text-primary)" }}>{athlete.date_of_birth}</dd></div>
              <div className="grid grid-cols-2 gap-2"><dt className="text-xs font-semibold uppercase" style={{ color: "var(--text-muted)" }}>Age</dt><dd style={{ color: "var(--text-primary)" }}>{athlete.age !== null ? `${athlete.age} yrs` : "—"}</dd></div>
            </dl>
          </div>
          <div className="bento-card p-6">
            <h3 className="font-semibold mb-4" style={{ color: "var(--text-primary)" }}>ACWR (Acute:Chronic Workload Ratio)</h3>
            {acwr?.acwr ? (
              <div className="space-y-3">
                <div className="flex justify-between"><span className="text-xs font-semibold uppercase" style={{ color: "var(--text-muted)" }}>ACWR</span><span className="font-bold text-lg" style={{ color: acwr.flagged ? "var(--danger-fg)" : "var(--text-primary)" }}>{acwr.acwr}</span></div>
                <div className="flex justify-between"><span className="text-xs" style={{ color: "var(--text-muted)" }}>Acute Load (7d)</span><span style={{ color: "var(--text-primary)" }}>{acwr.acute_load}</span></div>
                <div className="flex justify-between"><span className="text-xs" style={{ color: "var(--text-muted)" }}>Chronic Load (28d avg × 7)</span><span style={{ color: "var(--text-primary)" }}>{acwr.chronic_load}</span></div>
                <div className="status-pill" style={{ background: acwr.flagged ? "var(--warning-bg)" : "var(--brand-tint)", color: acwr.flagged ? "var(--warning-fg)" : "var(--brand-text)" }}>
                  {acwr.flagged ? "⚠ Elevated — reduce load this week" : "✓ Within normal range"}
                </div>
              </div>
            ) : (
              <p className="text-sm" style={{ color: "var(--text-secondary)" }}>{acwr?.message || "Insufficient training load data (need ≥7 days with session_load)"}</p>
            )}
          </div>
        </div>
      )}

      {activeTab === "injuries" && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="font-semibold" style={{ color: "var(--text-primary)" }}>Injury History</h3>
            <button className="pill-btn--primary text-xs" onClick={() => router.push(`/athletes/${id}/injuries/new`)}>Add Injury</button>
          </div>
          {injuries.length === 0 ? (
            <div className="bento-card p-6 text-center" style={{ color: "var(--text-secondary)" }}>No injury records yet.</div>
          ) : (
            <div className="bento-card overflow-hidden">
              <table className="w-full">
                <thead>
                  <tr className="border-b" style={{ borderColor: "var(--border-faint)" }}>
                    <th className="text-left p-4 text-xs font-semibold uppercase" style={{ color: "var(--text-muted)" }}>Injury Type</th>
                    <th className="text-left p-4 text-xs font-semibold uppercase" style={{ color: "var(--text-muted)" }}>Body Part</th>
                    <th className="text-left p-4 text-xs font-semibold uppercase" style={{ color: "var(--text-muted)" }}>Date</th>
                    <th className="text-left p-4 text-xs font-semibold uppercase" style={{ color: "var(--text-muted)" }}>Severity</th>
                    <th className="text-right p-4 text-xs font-semibold uppercase" style={{ color: "var(--text-muted)" }}>Actions</th>
                  </tr>
                  </thead>
                  <tbody>
                    {injuries.map((inj) => (
                      <tr key={inj.id} className="border-b hover:bg-muted transition-colors" style={{ borderColor: "var(--border-faint)" }}>
                        <td className="p-4 font-medium" style={{ color: "var(--text-primary)" }}>{inj.injury_type}</td>
                        <td className="p-4 text-sm" style={{ color: "var(--text-secondary)" }}>{inj.body_part}</td>
                        <td className="p-4 text-sm" style={{ color: "var(--text-secondary)" }}>{inj.injury_date}</td>
                        <td className="p-4"><span className="status-pill" style={{ background: inj.severity === "severe" ? "var(--danger-bg)" : inj.severity === "moderate" ? "var(--warning-bg)" : "var(--brand-tint)", color: inj.severity === "severe" ? "var(--danger-fg)" : inj.severity === "moderate" ? "var(--warning-fg)" : "var(--brand-text)" }}>{inj.severity || "—"}</span></td>
                        <td className="p-4 text-right"><button onClick={() => handleDelete("injury", inj.id)} className="text-xs" style={{ color: "var(--danger-fg)" }}>Delete</button></td>
                      </tr>
                    ))}
                  </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === "training" && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="font-semibold" style={{ color: "var(--text-primary)" }}>Training Load</h3>
            <button className="pill-btn--primary text-xs" onClick={() => router.push(`/athletes/${id}/training-load/new`)}>Add Entry</button>
          </div>
          {trainingLoads.length === 0 ? (
            <div className="bento-card p-6 text-center" style={{ color: "var(--text-secondary)" }}>No training load entries yet.</div>
          ) : (
            <div className="bento-card overflow-hidden">
              <table className="w-full">
                <thead>
                  <tr className="border-b" style={{ borderColor: "var(--border-faint)" }}>
                    <th className="text-left p-4 text-xs font-semibold uppercase" style={{ color: "var(--text-muted)" }}>Date</th>
                    <th className="text-left p-4 text-xs font-semibold uppercase" style={{ color: "var(--text-muted)" }}>Session Type</th>
                    <th className="text-left p-4 text-xs font-semibold uppercase" style={{ color: "var(--text-muted)" }}>Duration</th>
                    <th className="text-left p-4 text-xs font-semibold uppercase" style={{ color: "var(--text-muted)" }}>RPE</th>
                    <th className="text-left p-4 text-xs font-semibold uppercase" style={{ color: "var(--text-muted)" }}>Load</th>
                    <th className="text-right p-4 text-xs font-semibold uppercase" style={{ color: "var(--text-muted)" }}>Actions</th>
                  </tr>
                  </thead>
                  <tbody>
                    {trainingLoads.map((t) => (
                      <tr key={t.id} className="border-b hover:bg-muted transition-colors" style={{ borderColor: "var(--border-faint)" }}>
                        <td className="p-4 text-sm" style={{ color: "var(--text-primary)" }}>{t.entry_date}</td>
                        <td className="p-4 text-sm" style={{ color: "var(--text-secondary)" }}>{t.session_type || "—"}</td>
                        <td className="p-4 text-sm" style={{ color: "var(--text-primary)" }}>{t.duration_minutes ?? "—"} min</td>
                        <td className="p-4 text-sm" style={{ color: "var(--text-primary)" }}>{t.rpe ?? "—"}</td>
                        <td className="p-4 text-sm" style={{ color: "var(--text-primary)" }}>{t.session_load ?? "—"}</td>
                        <td className="p-4 text-right"><button onClick={() => handleDelete("training", t.id)} className="text-xs" style={{ color: "var(--danger-fg)" }}>Delete</button></td>
                      </tr>
                    ))}
                  </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === "videos" && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="font-semibold" style={{ color: "var(--text-primary)" }}>Videos</h3>
            <Link href={`/videos/upload?athlete_id=${id}`} className="pill-btn--primary text-xs">Upload Video</Link>
          </div>
          <div className="bento-card p-6 text-center" style={{ color: "var(--text-secondary)" }}>Video list coming soon — use the athlete filter on the Videos page.</div>
        </div>
      )}
    </div>
  );
}