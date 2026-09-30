"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api-client";
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
};

export default function AthletesPage() {
  const [athletes, setAthletes] = useState<Athlete[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const data = await apiClient.fetchWithAuth(`/athletes?page=${page}&page_size=${pageSize}`);
      setAthletes(data.items || []);
      setTotal(data.total || 0);
    } catch (e: any) {
      setError(e.message || "Failed to load athletes");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [page]);

  if (error) return <div className="status-pill status-pill--danger p-4">{error}</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>Athletes</h1>
          <p className="text-sm" style={{ color: "var(--text-secondary)" }}>Manage athlete profiles, injury history, and training load.</p>
        </div>
        <Link href="/athletes/new" className="pill-btn--primary">Add Athlete</Link>
      </div>

      {loading ? (
        <div className="bento-card p-6 flex items-center gap-3" style={{ color: "var(--text-primary)" }}>
          <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24" style={{ color: "var(--brand-dark)" }}>
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span className="text-sm font-bold">Loading athletes...</span>
        </div>
      ) : athletes.length === 0 ? (
        <div className="bento-card p-6 text-center" style={{ color: "var(--text-secondary)" }}>
          No athletes yet. <Link href="/athletes/new" className="underline" style={{ color: "var(--brand-dark)" }}>Add your first athlete</Link>.
        </div>
      ) : (
        <>
          <div className="bento-card overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b" style={{ borderColor: "var(--border-faint)" }}>
                  <th className="text-left p-4 text-xs font-semibold uppercase" style={{ color: "var(--text-muted)", letterSpacing: "0.05em" }}>Athlete</th>
                  <th className="text-left p-4 text-xs font-semibold uppercase" style={{ color: "var(--text-muted)", letterSpacing: "0.05em" }}>Sport</th>
                  <th className="text-left p-4 text-xs font-semibold uppercase" style={{ color: "var(--text-muted)", letterSpacing: "0.05em" }}>Age</th>
                  <th className="text-left p-4 text-xs font-semibold uppercase" style={{ color: "var(--text-muted)", letterSpacing: "0.05em" }}>Last Risk</th>
                  <th className="text-right p-4 text-xs font-semibold uppercase" style={{ color: "var(--text-muted)", letterSpacing: "0.05em" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {athletes.map((a) => (
                  <tr key={a.id} className="border-b hover:bg-muted transition-colors" style={{ borderColor: "var(--border-faint)" }}>
                    <td className="p-4">
                      <div className="font-medium" style={{ color: "var(--text-primary)" }}>{a.full_name || "Unnamed"}</div>
                      <div className="text-xs" style={{ color: "var(--text-muted)" }}>{a.position || "No position"}</div>
                    </td>
                    <td className="p-4 text-sm" style={{ color: "var(--text-secondary)" }}>{a.sport_type}</td>
                    <td className="p-4 text-sm" style={{ color: "var(--text-secondary)" }}>{a.age !== null ? `${a.age} yrs` : "—"}</td>
                    <td className="p-4">
                      <span className="status-pill status-pill--muted">Not assessed</span>
                    </td>
                    <td className="p-4 text-right">
                      <Link href={`/athletes/${a.id}`} className="pill-btn--outline text-xs">View</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {total > pageSize && (
            <div className="flex items-center justify-center gap-2 mt-6">
              <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="pill-btn--outline text-xs">Previous</button>
              <span className="text-sm" style={{ color: "var(--text-secondary)" }}>Page {page} of {Math.ceil(total / pageSize)}</span>
              <button onClick={() => setPage(p => p + 1)} disabled={page * pageSize >= total} className="pill-btn--outline text-xs">Next</button>
            </div>
          )}
        </>
      )}
    </div>
  );
}